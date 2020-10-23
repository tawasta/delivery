from odoo import models, fields


class ProductPackaging(models.Model):

    _inherit = 'product.packaging'

    dimension_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Dimension UoM',
        help='''Common unit of measure for dimensions (WxHxL)'''
    )
