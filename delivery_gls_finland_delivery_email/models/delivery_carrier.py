from odoo import models


class DeliveryCarrier(models.Model):

    _inherit = "delivery.carrier"

    def _gls_finland_map_record(self, picking):
        email = (
            picking.partner_id.email_delivery
            or (picking.sale_id and picking.sale_id.partner_id.email_delivery)
            or ""
        )

        return email
