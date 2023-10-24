from odoo import models


class StockImmediateTransfer(models.TransientModel):

    _inherit = "stock.immediate.transfer"

    def process(self):
        res = super(StockImmediateTransfer, self).process()
        pickings = self.pick_ids.sorted(key=lambda t: t.id).print_gls_document()

        if pickings:
            return res, pickings
        return res
