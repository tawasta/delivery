from odoo import fields, models


class StockMove(models.Model):

    _inherit = "stock.move"

    # A helper field for packages
    shipping_weight = fields.Float(string="Shipping Weight", related="weight")

    # TODO: smarter/editable contents
    contents = fields.Char(
        string="Contents",
        related="product_id.name",
    )
