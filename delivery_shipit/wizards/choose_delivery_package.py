from odoo import api, fields, models


class ChooseDeliveryPackage(models.TransientModel):
    _inherit = "choose.delivery.package"

    allowed_package_type_ids = fields.Many2many(
        comodel_name="stock.package.type",
        string="Allowed Package Types",
        compute="_compute_allowed_package_type_ids",
    )

    @api.depends("picking_id")
    def _compute_allowed_package_type_ids(self):
        """
        Compute the allowed package types based on the selected carrier.

        TODO: I really dislike overriding the delivery_package_type_id domain,
        but I don't see a better way to do this while keeping the possibility
        to have delivery.carrier specific package types.

        We might want to come up with a better solution, or separate this functionality
        to a standalone module to avoid forcing the change to all users.
        """
        for record in self:
            picking = record.picking_id
            carrier = picking.carrier_id if picking else None
            if carrier._shipit_is_carrier() and carrier.shipit_allowed_package_type_ids:
                record.allowed_package_type_ids = (
                    carrier.shipit_allowed_package_type_ids
                )
            else:
                record.allowed_package_type_ids = self.env["stock.package.type"].search(
                    [
                        (
                            "package_carrier_type",
                            "=",
                            carrier.delivery_type if carrier else None,
                        )
                    ]
                )
