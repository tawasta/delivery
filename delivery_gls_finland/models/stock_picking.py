from odoo import api, fields, models


class StockPicking(models.Model):

    _inherit = "stock.picking"

    contents = fields.Text(
        string="Package contents",
        help="Package contents description for the shipper/recipient",
    )
    gls_finland_uuid = fields.Char(
        "GLS Finland UUID",
        help="Unique identifier for a GLS Finland delivery",
    )
    shipment_info = fields.Char(
        "Shipment info",
        help="Information text for the shipment",
        size=40
    )
    parcels = fields.Integer(
        "Parcels",
        help="How many parcels are in the shipment"
    )

    @api.depends("origin")
    def _compute_contents(self):
        for record in self:
            contents = False
            if not record.contents:
                contents = record.origin

            record.contents = contents

    def _get_gls_finland_picking_weight(self):
        # Helper for getting picking weight, to allow overriding
        self.ensure_one()

        weight = self.shipping_weight or self.weight

        return weight
