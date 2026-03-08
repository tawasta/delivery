from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    shipit_shipment_id = fields.Char(
        string="ShipIT shipment ID",
        copy=False,
    )
    shipit_tracking_codes = fields.Char(
        string="ShipIT tracking codes",
        copy=False,
    )
    shipit_tracking_url = fields.Char(
        string="ShipIT tracking URL",
        copy=False,
    )
    shipit_label_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="ShipIT label attachment",
        copy=False,
    )
    shipit_payload = fields.Text(
        string="ShipIT payload",
        copy=False,
    )
    shipit_response = fields.Text(
        string="ShipIT response",
        copy=False,
    )
    shipit_last_error = fields.Text(
        string="ShipIT last error",
        copy=False,
    )
    shipit_delivery_done = fields.Boolean(
        default=False,
        copy=False,
    )

    def _shipit_send_before_validate(self):
        shipit_pickings = self.filtered(
            lambda p: p.carrier_id.delivery_type == "shipit"
            and not p.shipit_delivery_done
            and not p.shipit_shipment_id
        )

        for picking in shipit_pickings:
            values = picking.carrier_id.shipit_send_shipping(picking)
            tracking_number = values and values[0].get("tracking_number")

            if tracking_number and not picking.carrier_tracking_ref:
                picking.carrier_tracking_ref = tracking_number

            picking.shipit_delivery_done = True

    def button_validate(self):
        self._shipit_send_before_validate()
        return super().button_validate()
