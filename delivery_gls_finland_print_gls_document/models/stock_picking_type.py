from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    auto_print_gls_document = fields.Boolean(
        "Auto Print GLS document",
        help="""If this checkbox is ticked, Odoo will automatically
             print the GLS document of a picking when it is validated.""",
    )

    def _get_autoprint_report_actions(self):
        report_actions = super()._get_autoprint_report_actions()

        pickings_to_print = self.filtered(
            lambda p: p.picking_type_id.auto_print_gls_document
        )
        if pickings_to_print:
            pickings_to_print.print_gls_document()

        return report_actions
