from odoo import api, fields, models


class StockPicking(models.Model):

    _inherit = "stock.picking"

    carrier_delivery_type = fields.Text(
        string="Delivery type",
        compute="_compute_carrier_delivery_type",
        store=True,
    )

    @api.depends("carrier_id")
    @api.onchange("carrier_id")
    def _compute_carrier_delivery_type(self):
        for record in self:
            if record.carrier_id:
                options = dict(self.carrier_id._fields['delivery_type'].selection)
                delivery_type = options[record.carrier_id.delivery_type]
                record.carrier_delivery_type = delivery_type
            else:
                record.carrier_delivery_type = False


