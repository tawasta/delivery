from odoo import models


class GlsDeliveryWizard(models.TransientModel):
    _inherit = "gls.delivery.wizard"

    def process(self):
        res = super().process()

        close_window = {"type": "ir.actions.act_window_close"}

        print_gls_action = self.picking_ids.sudo().print_gls_document()

        return {
            "type": "ir.actions.act_multi",
            "actions": [res, print_gls_action, close_window],
        }
