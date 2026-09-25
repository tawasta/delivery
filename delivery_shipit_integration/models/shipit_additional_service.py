from odoo import fields, models


class ShipitAdditionalService(models.Model):
    _name = "shipit.additional.service"
    _description = "Shipit additional service"
    _order = "name asc, id asc"
    _unique_code = models.Constraint('UNIQUE(code)', 'Service code must be unique!')

    code = fields.Char(required=True)
    name = fields.Char(required=True)
