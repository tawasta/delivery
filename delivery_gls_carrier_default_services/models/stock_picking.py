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
                # Add services to picking order when created from sale order if
                # customer has email set
                if (
                    sale_order["partner_id"]
                    and sale_order["partner_id"]["email"]
                    and (
    sale_order
    .carrier_id
    .picking_order_autoadd_if_customer_email_services_gls_finland_service_ids
                        )
                ):
                    picking.gls_finland_service_ids = (
    sale_order
    .carrier_id
    .picking_order_autoadd_if_customer_email_services_gls_finland_service_ids
                )
                # Add services to picking order when created from sale order
                elif (
    sale_order
    .carrier_id
    .picking_order_autoadd_services_gls_finland_service_ids
                ):
                    picking.gls_finland_service_ids = (
        sale_order
        .carrier_id
        .picking_order_autoadd_services_gls_finland_service_ids
                    )
        return picking

    def write(self, vals):
        # Overwrite services to picking order when this carrier is chosen
        if "carrier_id" in list(vals.keys()):
            delivery_carrier = self.env["delivery.carrier"].search(
                [("id", "=", vals["carrier_id"])]
            )
            if (
                len(
    delivery_carrier
    .picking_order_autoadd_when_chosen_services_gls_finland_service_ids
                )
                > 0
            ):
                vals["gls_finland_service_ids"] = (
    delivery_carrier
    .picking_order_autoadd_when_chosen_services_gls_finland_service_ids
                    )

        return super().write(vals)
