from odoo import fields, models


class DeliveryEstimatedTimeExceptions(models.Model):
    _name = "delivery.estimated.time.exceptions"
    _description = "Estimated Delivery Time Exceptions"

    name = fields.Char(required=True)
    days = fields.Integer(
        help="Number of days for the estimated delivery time exception.",
    )
    active = fields.Boolean(default=True)
