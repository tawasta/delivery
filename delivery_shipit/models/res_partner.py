from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    shipit_customer_number = fields.Char(
        string="ShipIT Customer Number", help="Customer number for ShipIT integration"
    )
    shipit_payer_type = fields.Selection(
        string="ShipIT payer type",
        selection=[
            ("consignor", "Sender pays"),
            ("consignee", "Receiver pays"),
            ("other", "Third party pays"),
        ],
        default="consignor",
    )
