from odoo import api, fields, models


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    fixed_price_with_tax = fields.Float(
        string="Price with tax", compute="_compute_price_with_tax"
    )

    @api.depends("fixed_price")
    def _compute_price_with_tax(self):
        for record in self:
            if record.product_id.taxes_id:
                taxes = 0
                for tax in record.product_id.taxes_id:
                    taxes = (
                        taxes
                        + tax.compute_all(record.fixed_price).get("taxes")[0]["amount"]
                    )

                record.fixed_price_with_tax = record.fixed_price + taxes
            else:
                record.fixed_price_with_tax = record.fixed_price
