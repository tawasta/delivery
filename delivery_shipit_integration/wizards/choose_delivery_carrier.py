from odoo import _, api, models


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = "choose.delivery.carrier"

    @api.onchange("carrier_id", "total_weight")
    def _onchange_carrier_id(self):
        result = super()._onchange_carrier_id()
        if self.carrier_id and self.delivery_type == "shipit":
            vals = self._get_shipment_rate()
            if vals.get("error_message"):
                return {
                    "warning": {
                        "title": _("%(carrier)s Error", carrier=self.carrier_id.name),
                        "message": vals["error_message"],
                        "type": "notification",
                    }
                }
        return result
