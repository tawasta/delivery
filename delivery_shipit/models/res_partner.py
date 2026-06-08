from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    shipit_customer_number_posti = fields.Char(
        string="Posti Customer Number",
        help="Posti customer number for ShipIT integration",
    )

    shipit_customer_number_itellalog = fields.Char(
        string="Itella Customer Number",
        help="Itella Logistics customer number for ShipIT integration",
    )

    shipit_customer_number_kaukokiito = fields.Char(
        string="Kaukokiito Customer Number",
        help="Kaukokiito customer number for ShipIT integration",
    )

    shipit_customer_number_kl = fields.Char(
        string="DB SCHENKERsystem Customer Number",
        help="DB SCHENKERsystem customer number for ShipIT integration",
    )

    shipit_customer_number_sbtlfi = fields.Char(
        string="DB SCHENKERsystem Freight Customer Number",
        help="DB SCHENKERsystem Freight customer number for ShipIT integration",
    )

    shipit_customer_number_sbtlfiexp = fields.Char(
        string="DB SCHENKERparcel Customer Number",
        help="DB SCHENKERparcel customer number for ShipIT integration",
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
