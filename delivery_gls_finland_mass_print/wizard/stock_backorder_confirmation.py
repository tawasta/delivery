from odoo import models


class StockBackorderConfirmation(models.TransientModel):

    _inherit = "stock.backorder.confirmation"

    def process(self):
        res = super(StockBackorderConfirmation, self).process()
        pickings = self.pick_ids.sorted(key=lambda t: t.id).print_gls_document()

        close_window = {"type": "ir.actions.act_window_close"}

        if pickings:
            return {"type": "ir.actions.act_multi", "actions": [pickings, close_window]}

        return {
            "type": "ir.actions.act_multi",
            "actions": [res, close_window],
        }

    def process_cancel_backorder(self):
        res = super(StockBackorderConfirmation, self).process_cancel_backorder()
        pickings = self.pick_ids.sorted(key=lambda t: t.id).print_gls_document()

        close_window = {"type": "ir.actions.act_window_close"}

        if pickings:
            return {"type": "ir.actions.act_multi", "actions": [pickings, close_window]}

        return {
            "type": "ir.actions.act_multi",
            "actions": [res, close_window],
        }
