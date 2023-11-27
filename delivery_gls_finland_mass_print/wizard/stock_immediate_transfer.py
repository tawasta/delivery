from odoo import models


class StockImmediateTransfer(models.TransientModel):

    _inherit = "stock.immediate.transfer"

    def process(self):
        res = super(StockImmediateTransfer, self).process()
        pickings = (
            self.pick_ids.sorted(key=lambda t: t.id)
            .filtered(lambda x: not x.mass_transfer_done)
            .print_gls_document()
        )

        close_window = {"type": "ir.actions.act_window_close"}

        receipts = [
            p
            for p in self.pick_ids
            if p.picking_type_id and p.picking_type_id.code == "incoming"
        ]

        if receipts:
            return {
                "type": "ir.actions.act_multi",
                "actions": [close_window],
            }

        if pickings:
            return {
                "type": "ir.actions.act_multi",
                "actions": [res, pickings, close_window],
            }

        return res
