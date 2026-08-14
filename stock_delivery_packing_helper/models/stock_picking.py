from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    allowed_package_ids = fields.Many2many(
        comodel_name="stock.quant.package",
        relation="stock_picking_allowed_package_rel",
        column1="picking_id",
        column2="package_id",
        string="Allowed packages",
        help="Packages that can be used for this delivery",
    )
