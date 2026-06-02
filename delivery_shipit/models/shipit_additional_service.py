from odoo import fields, models


class ShipitAdditionalService(models.Model):
    _name = "shipit.additional.service"
    _description = "ShipIT additional service"
    _order = "name asc, id asc"

    code = fields.Char(required=True)
    name = fields.Char(required=True)

    _sql_constraints = [
        (
            "shipit_additional_service_code_uniq",
            "unique(code)",
            "Service code must be unique.",
        ),
    ]
