import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

from .shipit_request import ShipitAPIError, ShipitRequest

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    shipit_api_key = fields.Char(
        string="ShipIT API key",
        config_parameter="shipit.api_key",
        help="Set the API key to connect to ShipIT",
    )
    shipit_environment = fields.Selection(
        [("prod", "Production"), ("test", "Test")],
        string="ShipIT environment",
        config_parameter="shipit.environment",
        default="prod",
        help="Environment to use for ShipIT API calls.",
    )
    shipit_timeout_seconds = fields.Integer(
        string="ShipIT API timeout",
        config_parameter="shipit.timeout_seconds",
        default=30,
        help="How long to wait for responses before timing out.",
    )
    shipit_reseller_id = fields.Integer(
        string="ShipIT reseller ID",
        config_parameter="shipit.reseller_id",
        default=57,
        help="Reseller ID to use in ShipIT API calls."
        "We urge users to use reseller ID 57 of Futural Oy "
        "to support the continued development of the integration.",
    )

    def action_shipit_sync_shipping_methods(self):
        self.ensure_one()
        sync_result = self._shipit_sync_service_options(raise_on_error=True)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("ShipIT services updated"),
                "message": _("Synchronized %s services.", sync_result["total"]),
                "sticky": False,
            },
        }

    def _shipit_sync_service_options(self, raise_on_error=True):
        shipit_request = ShipitRequest(
            api_key=self.shipit_api_key,
            prod=self.shipit_environment == "prod",
            timeout=self.shipit_timeout_seconds,
        )
        try:
            methods = shipit_request.list_methods()
        except ShipitAPIError as error:
            if raise_on_error:
                raise UserError(
                    _("Fetching ShipIT services failed:\n%(message)s")
                    % {"message": str(error)}
                ) from error
            return {"total": 0}

        DeliveryCarrier = (
            self.env["delivery.carrier"].sudo().with_context(active_test=False)
        )
        services = []
        for method in methods:
            # Create or update carriers
            carrier = self.shipit_upsert_carrier(method)
            if carrier:
                services.append(carrier)

        contracts = shipit_request.carrier_contracts()
        for contract in contracts:
            # Activate the carriers that have active contracts
            carrier = DeliveryCarrier.search(
                [("shipit_service_code", "=", contract["service"])]
            )
            if carrier and contract["status"] == "active":
                carrier.active = True

        return {
            "total": len(services),
        }

    def shipit_upsert_carrier(self, service_vals):
        """
        Create or update a delivery.carrier based on ShipIT service data
        """
        service_name = service_vals.get("name")
        service_code = service_vals.get("serviceId")
        delivery_type = service_vals.get("carrierId")

        if not delivery_type:
            _logger.warning(
                "Skipping ShipIT service with missing carrierId: %s", service_name
            )
            return False

        DeliveryCarrier = (
            self.env["delivery.carrier"].sudo().with_context(active_test=False)
        )
        AdditionalService = self.env["shipit.additional.service"].sudo()

        carrier = DeliveryCarrier.search(
            [
                ("shipit_service_code", "=", service_code),
                ("delivery_type", "=", delivery_type),
            ],
            limit=1,
        )

        config = self.env["ir.config_parameter"].sudo()
        prod_environment = config.get_param("shipit.environment") == "prod"

        vals = {
            "name": service_name,
            "product_id": self.env.ref(
                "delivery_shipit.product_product_delivery_shipit"
            ).id,
            "prod_environment": prod_environment,
        }

        if service_vals.get("supportedCountries"):
            countries = self.env["res.country"].search(
                [("code", "in", service_vals["supportedCountries"])]
            )
            if countries:
                vals["country_ids"] = [(6, 0, countries.ids)]

        additional_services = []

        if service_vals.get("fragile"):
            fragile_service = AdditionalService.search(
                [("code", "=", "fragile")], limit=1
            )
            if not fragile_service:
                fragile_service = AdditionalService.create(
                    {"code": "fragile", "name": "Fragile"}
                )
            additional_services.append((4, fragile_service.id))

        for additional_service_name in service_vals.get("additionalServices", []):
            additional_service = AdditionalService.search(
                [("code", "=", additional_service_name)], limit=1
            )
            if not additional_service:
                additional_service = AdditionalService.create(
                    {
                        "code": additional_service_name,
                        "name": additional_service_name,
                    }
                )
            additional_services.append((4, additional_service.id))

        if additional_services:
            vals["shipit_allowed_additional_service_ids"] = additional_services

        if not carrier:
            vals.update(
                {
                    "active": False,
                    "delivery_type": delivery_type,
                    "shipit_service_code": service_code,
                }
            )
            carrier = DeliveryCarrier.create(vals)
        else:
            carrier.write(vals)

        return carrier
