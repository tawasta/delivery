# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    @api.multi
    def _compute_quant_package_ids(self):
        for picking in self:
            picking.quant_package_ids = [line.result_package_id.id
                                         for line
                                         in picking.pack_operation_product_ids]

    quant_package_ids = fields.Many2many(
        compute=_compute_quant_package_ids,
        comodel_name='stock.quant.package',
        string='Physical packages',
        store=False
    )
