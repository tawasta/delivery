from odoo import models, fields


class StockQuantPackage(models.Model):

    _inherit = 'stock.quant.package'

    # w/h/l are defined in the product.packaging model, create related fields
    # so that the info can be shown in Physical Package treeview

    width = fields.Integer(
        related='packaging_id.width',
        string='Width',
        readonly=True
    )

    height = fields.Integer(
        related='packaging_id.height',
        string='Height',
        readonly=True
    )

    length = fields.Integer(
        related='packaging_id.length',
        string='Length',
        readonly=True
    )

    dimension_uom_id = fields.Many2one(
        related='packaging_id.dimension_uom_id',
        string='UoM',
        readonly=True
    )
