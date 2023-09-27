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
    gls_finland_tracking_codes = fields.Char(
        "GLS tracking codes",
    )

    shipment_info = fields.Char(
        "Shipment info", help="Information text for the shipment", size=40
    )
    parcels = fields.Integer("Parcels", help="How many parcels are in the shipment")

    gls_finland_service_ids = fields.Many2many(
        string="GLS services",
        comodel_name="gls.finland.service",
        compute="_compute_gls_finland_service_ids",
        store=True,
    )

    @api.depends("origin")
    def _compute_contents(self):
        for record in self:
            contents = False
            if not record.contents:
                contents = record.origin

            record.contents = contents

    @api.depends("carrier_id")
    def _compute_gls_finland_service_ids(self):
        for record in self:
            if record.carrier_id:
                record.gls_finland_service_ids = (
                    record.carrier_id.gls_finland_service_ids
                )
            else:
                record.gls_finland_service_ids = False

    def _get_gls_finland_picking_weight(self):
        # Helper for getting picking weight, to allow overriding
        self.ensure_one()

        weight = self.shipping_weight or self.weight

        return weight
