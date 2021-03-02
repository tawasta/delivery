from odoo import models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    def _create_delivery_line(self, carrier, price_unit):
        res = super()._create_delivery_line(carrier, price_unit)

        res.company_id = self.company_id.id

        return res
