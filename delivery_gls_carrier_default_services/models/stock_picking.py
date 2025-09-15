import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model_create_multi
    def create(self, values_list):
        pickings = super().create(values_list)
        for picking in pickings:
            sale_order = self.env["sale.order"].search([("name", "=", picking.origin)])
            if sale_order.carrier_id:
                # If customer has email and carrier has services
                if (
                    sale_order["partner_id"]
                    and sale_order["partner_id"]["email"]
                    and sale_order.carrier_id.picking_order_autoadd_if_customer_email_services_gls_finland_service_ids
                ):
                    picking.gls_finland_service_ids = sale_order.carrier_id.picking_order_autoadd_if_customer_email_services_gls_finland_service_ids
                # If carrier has services
                elif sale_order.carrier_id.picking_order_autoadd_services_gls_finland_service_ids:
                    picking.gls_finland_service_ids = sale_order.carrier_id.picking_order_autoadd_services_gls_finland_service_ids
        return picking
