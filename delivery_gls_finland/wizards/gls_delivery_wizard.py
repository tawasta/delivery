import uuid

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class GlsDeliveryWizard(models.TransientModel):
    _name = "gls.delivery.wizard"
    _description = "Gls Delivery wizard"

    picking_ids = fields.Many2many("stock.picking")
    parcels = fields.Integer(
        "Parcels",
        compute="_compute_parcels",
    )
    total_weight = fields.Float(
        "Total weight",
        compute="_compute_total_weight",
    )
    gls_consolidated_shipment = fields.Boolean(
        string="Consolidated GLS shipment",
        help="Send all GLS transfer as one shipment",
        default=False,
    )

    def _compute_parcels(self):
        self.parcels = sum(self.picking_ids.mapped("parcels"))

    def _compute_total_weight(self):
        self.total_weight = self.picking_ids._get_gls_finland_picking_weight()

    def process(self):
        # Set UUID here to send all pickings in one shipping
        if self.gls_consolidated_shipment:
            self.picking_ids.sudo().write(
                {
                    "gls_finland_uuid": str(uuid.uuid4()),
                }
            )

        self.picking_ids.sudo().write({"gls_delivery_done": True})

        return self.picking_ids.sudo().button_validate()
