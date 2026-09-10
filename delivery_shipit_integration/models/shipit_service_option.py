from odoo import fields, models


class ShipitServiceOption(models.Model):
    # TODO: What's the point of this model?
    # Can it be completely removed?
    # It was used in shipit.pickup.point.wizard,
    # but it seems redundant with shipit_service_code

    _name = "shipit.service.option"
    _description = "Shipit service option"
    _order = "sequence asc, id asc"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    carrier_name = fields.Char()
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        (
            "shipit_service_option_code_uniq",
            "unique(code)",
            "Service code must be unique.",
        ),
    ]

    def name_get(self):
        result = []
        for record in self:
            label = record.name or record.code or ""
            if record.carrier_name:
                label = f"{record.carrier_name} - {label}"
            if record.code:
                label = f"{label} ({record.code})"
            result.append((record.id, label))
        return result
