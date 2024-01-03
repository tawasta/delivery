from odoo import models


class DeliveryCarrier(models.Model):

    _inherit = "delivery.carrier"

    def _get_email_pre_advice_email(self, picking):
        email = (
            picking.partner_id.email_delivery
            or (picking.sale_id and picking.sale_id.partner_id.email_delivery)
            or ""
        )

        return email
