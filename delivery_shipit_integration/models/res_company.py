import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

from .shipit_request import ShipitAPIError, ShipitRequest

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    shipit_api_key = fields.Char(
        string="Shipit API key",
        help="Set the API key to connect to Shipit",
    )

    shipit_environment = fields.Selection(
        [("prod", "Production"), ("test", "Test")],
        string="Shipit environment",
        default="prod",
        help="Environment to use for Shipit API calls.",
    )

    shipit_timeout_seconds = fields.Integer(
        string="Shipit API timeout",
        default=30,
        help="How long to wait for responses before timing out.",
    )

    shipit_reseller_id = fields.Integer(
        string="Shipit reseller ID",
        default=57,
        help="Reseller ID to use in Shipit API calls."
        "We urge users to use reseller ID 57 of Futural Oy "
        "to support the continued development of the integration.",
    )

    def shipit_request(self, timeout=30):
        # TODO: Optimize so that when this function is called again, same instance
        # of the ShipitRequest is returned so it does not need to be initialized
        # every time
        return ShipitRequest(
            api_key=self.shipit_api_key,
            prod=self.shipit_environment == "prod",
            timeout=timeout if timeout else self.shipit_timeout_seconds,
        )

    def action_shipit_sync_shipping_methods(self):
        self.ensure_one()
        sync_result = self._shipit_sync_service_options(raise_on_error=True)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Shipit services updated"),
                "message": _("Synchronized %s services.", sync_result["total"]),
                "sticky": False,
            },
        }

    def _shipit_sync_service_options(self, raise_on_error=True):
        try:
            methods = self.shipit_request().list_methods()
        except ShipitAPIError as error:
            if raise_on_error:
                raise UserError(
                    _("Fetching Shipit services failed:\n%(message)s")
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

        contracts = self.shipit_request().carrier_contracts()
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
        service_name = service_vals.get("name")
        service_code = service_vals.get("serviceId")
        delivery_type = service_vals.get("carrierId")
        current_company_id = self.env.company.id

        if not delivery_type:
            _logger.warning(
                "Skipping Shipit service with missing carrierId: %s", service_name
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
                ("company_id", "=", current_company_id),
            ],
            limit=1,
        )

        prod_environment = self.shipit_environment == "prod"

        shipping_product = self.env["product.product"].search(
            [("default_code", "=", "shipit"), ("company_id", "=", current_company_id)],
            limit=1,
        )
        if len(shipping_product) == 0:
            self.env["product.product"].create(
                {
                    "name": "Shipit Delivery",
                    "default_code": "shipit",
                    "type": "service",
                    # "categ_id": delivery.product_category_deliveries,
                    "sale_ok": False,
                    "purchase_ok": False,
                    "list_price": 0,
                    "invoice_policy": "order",
                    "company_id": current_company_id,
                }
            )
            shipping_product = self.env["product.product"].search(
                [
                    ("default_code", "=", "shipit"),
                    ("company_id", "=", current_company_id),
                ],
                limit=1,
            )

        vals = {
            "name": service_name,
            "product_id": shipping_product.id,
            "prod_environment": prod_environment,
            "company_id": current_company_id,
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
