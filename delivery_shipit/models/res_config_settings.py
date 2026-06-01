from odoo import _, fields, models
from odoo.exceptions import UserError

from .shipit_request import ShipitAPIError, ShipitRequest


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    shipit_api_key = fields.Char(
        config_parameter="shipit.api_key",
        help="Set the API key to connect to ShipIT",
    )
    shipit_environment = fields.Selection(
        [("prod", "Production"), ("test", "Test")],
        config_parameter="shipit.environment",
        default="prod",
        help="Environment to use for ShipIT API calls.",
    )
    shipit_timeout_seconds = fields.Integer(
        config_parameter="shipit.timeout_seconds",
        default=30,
        help="How long to wait for ShipIT API responses before timing out.",
    )
    shipit_reseller_id = fields.Integer(
        config_parameter="shipit.reseller_id",
        string="ShipIT reseller ID",
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

        delivery_carrier = self.env["delivery.carrier"].sudo()
        for method in methods:
            delivery_carrier.shipit_upsert_carrier(method)

        return {
            "total": len(methods),
        }
