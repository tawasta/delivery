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
                ci = sale_order.carrier_id
                # Add services to picking order when created from sale order if
                # customer has email set
                if (
                    sale_order["partner_id"]
                    and sale_order["partner_id"]["email"]
                    and ci.picking_autoadd_email
                ):
                    picking.gls_finland_service_ids = ci.picking_autoadd_email
                # Add services to picking order when created from sale order
                elif ci.picking_autoadd_default:
                    ci = sale_order.carrier_id
                    picking.gls_finland_service_ids = ci.picking_autoadd_default
        return picking

    def write(self, vals):
        # Overwrite services to picking order when this carrier is chosen
        if "carrier_id" in list(vals.keys()):
            delivery_carrier = self.env["delivery.carrier"].search(
                [("id", "=", vals["carrier_id"])]
            )
            dc = delivery_carrier
            if len(dc.picking_autoadd_chosen) > 0:
                vals["gls_finland_service_ids"] = dc.picking_autoadd_chosen

        return super().write(vals)
