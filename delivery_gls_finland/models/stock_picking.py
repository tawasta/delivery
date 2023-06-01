from odoo import api, fields, models


class StockPicking(models.Model):

    _inherit = "stock.picking"

    volume = fields.Float(string="Volume", compute="_compute_volume", copy=False)

    contents = fields.Text(
        string="Package contents",
        help="Package contents description for the shipper/recipient",
    )
    gls_finland_uuid = fields.Char(
        "GLS Finland UUID",
        help="Unique identifier for a GLS Finland delivery",
    )

    @api.depends("product_id", "move_lines")
    def _compute_volume(self):
        for picking in self:
            picking.volume = sum(
                move.volume for move in picking.move_lines if move.state != "cancel"
            )
