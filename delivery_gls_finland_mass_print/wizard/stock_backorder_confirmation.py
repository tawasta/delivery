from odoo import models


class StockBackorderConfirmation(models.TransientModel):

    _inherit = "stock.backorder.confirmation"

    def process(self):
        res = super(StockBackorderConfirmation, self).process()
        pickings = self.pick_ids.sorted(key=lambda t: t.id).print_gls_document()

        if pickings:
            return pickings
        return res

    def process_cancel_backorder(self):
        res = super(StockBackorderConfirmation, self).process_cancel_backorder()
        pickings = self.pick_ids.sorted(key=lambda t: t.id).print_gls_document()

        if pickings:
            return pickings
        return res
