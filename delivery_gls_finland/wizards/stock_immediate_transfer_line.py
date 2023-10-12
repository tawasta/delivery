from odoo import fields, models


class StockImmediateTransferLine(models.TransientModel):

    _inherit = "stock.immediate.transfer.line"

    carrier_id = fields.Many2one(
        comodel_name="delivery.carrier", related="picking_id.carrier_id"
    )
