from odoo import fields, models


class DeliveryEstimatedTimeRule(models.Model):
    _name = "delivery.estimated.time.rule"
    _description = "Estimated Delivery Time Rule"
    _order = "country_id, id"

    name = fields.Char(required=True)
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="Destination Country",
        ondelete="restrict",
        help="Leave empty to define a fallback rule used when no rule "
        "matches the destination country.",
    )
    base_min_days = fields.Integer(
        help="Base minimum number of days the delivery takes to reach "
        "the destination.",
    )
    base_max_days = fields.Integer(
        help="Base maximum number of days the delivery takes to reach "
        "the destination.",
    )
    active = fields.Boolean(default=True)
