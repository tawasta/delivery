import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    #picking_order_autoadd_services_gls_finland_service_ids
    picking_autoadd_default = fields.Many2many(
        "gls.finland.service",
        relation="delivery_gls_carrier_default_services_service_ids",
        string="Add services to picking order when created from sale order",
    )
    #picking_order_autoadd_if_customer_email_services_gls_finland_service_ids
    picking_autoadd_email = fields.Many2many(
        "gls.finland.service",
        relation="delivery_gls_carrier_if_email_default_services_service_ids",
        string="""Add services to picking order when created from sale
        order if customer has email set""",
    )

    #picking_order_autoadd_when_chosen_services_gls_finland_service_ids
    picking_autoadd_chosen = fields.Many2many(
        "gls.finland.service",
        relation="delivery_gls_carrier_when_chosen_default_services_service_ids",
        string="Overwrite services to picking order when this carrier is chosen",
    )
