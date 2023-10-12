import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class GlsFinlandService(models.Model):

    _name = "gls.finland.service"
    _description = "GLS Finland service"

    name = fields.Char("Service name")
    code = fields.Char("Service code")
