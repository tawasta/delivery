from odoo import fields, models


class DeliveryCarrierNshift(models.Model):

    _name = "delivery.carrier.nshift"

    active = fields.Boolean(default=True)
    name = fields.Char(string="Service name")
    carrier_name = fields.Char("Carrier name")
    partner_code = fields.Char(
        string="Partner code", help="Partner code for this carrier"
    )
    service_code = fields.Char(
        string="Service code", help="Service code for this carrier"
    )
    customer_number = fields.Char(
        string="Customer number", help="Your customer number for this carrier"
    )
