from odoo import api, fields, models


class StockPicking(models.Model):

    _inherit = "stock.picking"

    contents = fields.Text(
        string="Package contents",
        help="Package contents description for the shipper/recipient",
        compute="_compute_contents",
        store=True
    )
    gls_finland_uuid = fields.Char(
        "GLS Finland UUID",
        help="Unique identifier for a GLS Finland delivery",
    )

    @api.depends("origin")
    def _compute_contents(self):
        for record in self:
            contents = False
            if not record.contents:
                contents = record.origin

            record.contents = contents


