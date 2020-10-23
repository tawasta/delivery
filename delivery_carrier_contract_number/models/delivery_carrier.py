from odoo import fields, models


class DeliveryCarrier(models.Model):

    _inherit = 'delivery.carrier'

    contract_number = fields.Char(
        string="Contract Number"
    )
