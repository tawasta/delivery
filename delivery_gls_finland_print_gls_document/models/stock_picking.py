from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def print_gls_document(self):
        attachments = self.env["ir.attachment"]

        for picking in self:
            domain = [
                ("res_model", "=", "stock.picking"),
                ("res_id", "=", picking.id),
            ]

            attachs = (
                self.env["ir.attachment"]
                .search(domain)
                .filtered(lambda x: x.type == "binary")
            )
            attachments |= attachs

        attach_url = []

        for attach in attachments:
            parameter_model = self.env["ir.config_parameter"]

            base_url = parameter_model.sudo().get_param("web.base.url").rstrip("/")
            url = "{}/web/content/{}?download=1".format(
                base_url,
                attach.id,
            )

            attach_url.append(
                {
                    "type": "ir.actions.act_url",
                    "url": url,
                    "target": "current",
                }
            )

        return {"type": "ir.actions.act_multi", "actions": attach_url}
