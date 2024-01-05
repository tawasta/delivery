from odoo import fields, models


class ResPartner(models.Model):

    _inherit = "res.partner"

    email_delivery = fields.Char(string="Delivery Email", copy=False, store=True)
