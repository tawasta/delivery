from odoo import fields, models


class AccountIncoterms(models.Model):

    _inherit = "account.incoterms"

    gls_finland_incoterm = fields.Selection(
        [
            ("INCO10", "Incoterm 10 (DDP)"),
            ("INCO20", "Incoterm 20 (DAP"),
            ("INCO30", "Incoterm 30 (DDP, VAT unpaid)"),
            ("INCO40", "Incoterm 40 (DAP, cleared)"),
            ("INCO50", "Incoterm 50 (DDP)"),
            ("INCO18", "Incoterm 18 (DDP, VAT Registration Scheme)"),
        ],
        string="GLS Finland Incoterm",
    )
