from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    result_package_type_id = fields.Many2one(
        comodel_name="stock.package.type",
        related="result_package_id.package_type_id",
    )
