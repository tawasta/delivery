from odoo import models, fields, api


class PurchaseOrder(models.Model):

    _inherit = 'purchase.order'

    @api.model
    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        res['carrier_id'] = self.carrier_id and self.carrier_id.id or False
        return res

    carrier_id = fields.Many2one(
        comodel_name='delivery.carrier',
        string="Carrier"
    )
