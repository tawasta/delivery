from odoo import api
from odoo import fields, models


class StockPicking(models.Model):

    _inherit = "stock.picking"

    volume = fields.Float(string="Volume", compute="_compute_volume", copy=False)

    contents = fields.Text(
        string="Package contents",
        help="Package contents description for the shipper/recipient",
    )

    nshift_packages = fields.Selection(
        string="Packages",
        selection=[
            ("one", "One package for the whole delivery"),
            ("row", "Multiple packages"),
        ],
        default="row",
    )

    @api.depends("product_id", "move_lines")
    def _compute_volume(self):
        for picking in self:
            picking.volume = sum(
                move.volume for move in picking.move_lines if move.state != "cancel"
            )
