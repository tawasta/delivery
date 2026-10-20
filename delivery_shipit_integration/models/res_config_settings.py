from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    shipit_api_key = fields.Char(related="company_id.shipit_api_key", readonly=False)

    shipit_environment = fields.Selection(
        related="company_id.shipit_environment", readonly=False
    )
    shipit_timeout_seconds = fields.Integer(
        related="company_id.shipit_timeout_seconds",
        readonly=False,
    )
    shipit_reseller_id = fields.Integer(
        related="company_id.shipit_reseller_id", readonly=False
    )

    def action_shipit_sync_shipping_methods(self):
        return self.env.company.action_shipit_sync_shipping_methods()
