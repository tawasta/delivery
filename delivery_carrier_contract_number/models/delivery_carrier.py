# -*- coding: utf-8 -*-
from odoo import models, fields


class DeliveryCarrier(models.Model):

    _inherit = 'delivery.carrier'

    contract_number = fields.Char(
        string="Contract Number"
    )
