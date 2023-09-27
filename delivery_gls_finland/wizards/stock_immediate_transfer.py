import uuid

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockImmediateTransfer(models.TransientModel):

    _inherit = "stock.immediate.transfer"

    parcels = fields.Integer(
        "Parcels",
        compute="_compute_parcels",
    )
    total_weight = fields.Float(
        "Total weight",
        compute="_compute_total_weight",
    )
    gls_shipment_allowed = fields.Boolean(
        "GLS Shipment allowed", compute="_compute_gls_shipment_allowed"
    )

    @api.onchange(
        "immediate_transfer_line_ids", "immediate_transfer_line_ids.to_immediate"
    )
    def _compute_parcels(self):
        pickings_to_do = self.env["stock.picking"]
        for line in self.immediate_transfer_line_ids:
            if line.to_immediate is True:
                pickings_to_do |= line.picking_id

        self.parcels = sum(pickings_to_do.mapped("parcels"))

    @api.onchange(
        "immediate_transfer_line_ids", "immediate_transfer_line_ids.to_immediate"
    )
    def _compute_total_weight(self):
        pickings_to_do = self.env["stock.picking"]
        for line in self.immediate_transfer_line_ids:
            if line.to_immediate is True:
                pickings_to_do |= line.picking_id

        self.total_weight = pickings_to_do._get_gls_finland_picking_weight()

    @api.onchange(
        "immediate_transfer_line_ids", "immediate_transfer_line_ids.to_immediate"
    )
    def _compute_gls_shipment_allowed(self):
        pickings_to_do = self.env["stock.picking"]
        for line in self.immediate_transfer_line_ids:
            if line.to_immediate is True:
                pickings_to_do |= line.picking_id

        gls_pickings = pickings_to_do.filtered(
            lambda p: p.carrier_id.delivery_type == "gls_finland"
        )

        if len(gls_pickings.mapped("partner_id")) > 1:
            self.gls_shipment_allowed = False
        else:
            self.gls_shipment_allowed = True

        if not self.gls_shipment_allowed:
            msg = _("Trying to send GLS shipment to multiple destinations!")
            raise ValidationError(msg)

    def process(self):
        pickings_to_do = self.env["stock.picking"]
        pickings_not_to_do = self.env["stock.picking"]
        for line in self.immediate_transfer_line_ids:
            if line.to_immediate is True:
                pickings_to_do |= line.picking_id
            else:
                pickings_not_to_do |= line.picking_id

        # Set UUID here to send all pickings in one shipping
        pickings_to_do.write({"gls_finland_uuid": str(uuid.uuid4())})

        return super().process()
