from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    estimated_delivery_time = fields.Many2one(
        comodel_name="delivery.estimated.time.rule",
        help="Select estimated delivery time",
        string="Estimated Delivery Time Base",
        compute="_compute_estimated_delivery_time",
        store=True,
        readonly=False,
    )

    estimated_delivery_time_exceptions = fields.Many2many(
        comodel_name="delivery.estimated.time.exceptions",
        help="Select estimated delivery time exceptions",
    )

    delivery_time_range = fields.Char(
        compute="_compute_delivery_time_range",
        string="Estimated Delivery Time",
        help="Estimated delivery time range for the order.",
    )

    @api.depends("partner_shipping_id.country_id")
    def _compute_estimated_delivery_time(self):
        """Match the delivery time rule for the shipping address country."""
        for order in self:
            order.estimated_delivery_time = order._match_estimated_delivery_rule()

    def _match_estimated_delivery_rule(self):
        """Return the active rule for the shipping country, or the fallback.

        When several rules share the same country, the one with the lowest
        id wins. Falls back to the rule with an empty country; if neither
        exists, returns an empty recordset so the field stays empty.
        """
        rules = self.env["delivery.estimated.time.rule"]
        country = self.partner_shipping_id.country_id
        if country:
            rule = rules.search([("country_id", "=", country.id)], limit=1)
            if rule:
                return rule
        return rules.search([("country_id", "=", False)], limit=1)

    @api.depends(
        "estimated_delivery_time.base_min_days",
        "estimated_delivery_time.base_max_days",
        "estimated_delivery_time_exceptions.days",
    )
    def _compute_delivery_time_range(self):
        for order in self:
            if order.estimated_delivery_time:
                min_days = order.estimated_delivery_time.base_min_days
                max_days = order.estimated_delivery_time.base_max_days

                for exception in order.estimated_delivery_time_exceptions:
                    min_days += exception.days
                    max_days += exception.days

                if min_days == max_days:
                    order.delivery_time_range = _("%(min)s days") % {"min": min_days}
                else:
                    order.delivery_time_range = _("%(min)s-%(max)s days") % {
                        "min": min_days,
                        "max": max_days,
                    }
            else:
                order.delivery_time_range = _("N/A")
