from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    shipit_is_carrier = fields.Boolean(
        compute="_compute_shipit_is_carrier",
    )
    shipit_shipment_id = fields.Char(
        string="Shipit shipment ID",
        copy=False,
    )
    shipit_tracking_codes = fields.Char(
        string="Shipit tracking codes",
        copy=False,
    )
    shipit_tracking_url = fields.Char(
        string="Shipit tracking URL",
        copy=False,
    )
    shipit_label_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Shipit label attachment",
        copy=False,
    )
    shipit_payload = fields.Text(
        string="Shipit payload",
        copy=False,
    )
    shipit_response = fields.Text(
        string="Shipit response",
        copy=False,
    )
    shipit_last_error = fields.Text(
        string="Shipit last error",
        copy=False,
    )
    shipit_delivery_done = fields.Boolean(
        default=False,
        copy=False,
    )

    @api.depends("carrier_id")
    def _compute_shipit_is_carrier(self):
        for picking in self:
            if picking.carrier_id:
                picking.shipit_is_carrier = picking.carrier_id._shipit_is_carrier()
            else:
                picking.shipit_is_carrier = False

    def action_shipit_send_shipping(self):
        shipit_pickings = self.filtered(
            lambda p: p.carrier_id.shipit_service_code is not False
            and p.picking_type_code == "outgoing"
            and not p.shipit_delivery_done
            and not p.shipit_shipment_id
            and p.state not in ("done", "cancel")
        )

        for picking in shipit_pickings:
            values = picking.carrier_id.shipit_send_shipping(picking)
            tracking_number = values and values[0].get("tracking_number")

            if tracking_number and not picking.carrier_tracking_ref:
                picking.carrier_tracking_ref = tracking_number

            picking.shipit_delivery_done = True

    def button_validate(self):
        res = super().button_validate()

        if len(self) == 1 and self.shipit_label_attachment_id:
            attachment = self.shipit_label_attachment_id
            url = f"/web/content/{attachment.id}?download=true"

            attachment = self.shipit_label_attachment_id

            return {
                "type": "ir.actions.act_url",
                "url": url,
                "name": attachment.name,
                "target": "new",
            }

        return res

    def action_print_shipit_label(self):
        for rec in self:
            if rec.shipit_label_attachment_id:
                attachment = self.shipit_label_attachment_id
                url = f"/web/content/{attachment.id}?download=true"

                attachment = self.shipit_label_attachment_id

                return {
                    "type": "ir.actions.act_url",
                    "url": url,
                    "name": attachment.name,
                    "target": "new",
                }
