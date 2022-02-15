from odoo import fields, models, api


class StockMove(models.Model):

    _inherit = "stock.move"

    volume = fields.Float(
        compute="_compute_volume",
        store=True,
    )

    # A helper field for packages
    shipping_weight = fields.Float(string="Shipping Weight", related="weight")

    # TODO: smarter/editable contents
    contents = fields.Char(
        string="Contents",
        related="product_id.name",
    )

    @api.depends("product_id", "product_uom_qty", "product_uom")
    def _compute_volume(self):
        for move in self.filtered(lambda moves: moves.product_id.volume > 0.00):
            move.volume = move.product_qty * move.product_id.volume
