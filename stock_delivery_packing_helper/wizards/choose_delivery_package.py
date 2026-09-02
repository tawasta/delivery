from math import ceil

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ChooseDeliveryPackage(models.TransientModel):
    _inherit = "choose.delivery.package"

    total_weight = fields.Float(
        help="Total weight of the shipment",
        compute="_compute_total_weight",
    )
    package_count = fields.Integer(default=1)
    package_base_weight = fields.Float(
        help="Weight of one package",
        compute="_compute_package_base_weight",
    )
    package_weight_uom_name = fields.Char(
        help="Unit of measure for the package weight",
        compute="_compute_package_base_weight",
        readonly=True,
    )
    package_shipping_weight = fields.Float(
        help="Shipping weight of one package",
        compute="_compute_package_shipping_weight",
        store=True,
        readonly=False,
    )
    package_help_text = fields.Html(
        help="Help text for the package weight",
        compute="_compute_package_help_text",
    )

    @api.constrains("package_count")
    def _check_package_count(self):
        for rec in self:
            if rec.package_count < 1:
                raise ValidationError(
                    _("Package count must be greater than or equal to 1.")
                )

    @api.depends("delivery_package_type_id", "picking_id")
    def _compute_total_weight(self):
        for rec in self:
            move_line_ids = rec.picking_id._package_move_lines(
                batch_pack=self.env.context.get("batch_pack")
            )

            total_weight = 0
            for ml in move_line_ids:
                qty = ml.product_uom_id._compute_quantity(
                    ml.quantity, ml.product_id.uom_id
                )
                total_weight += qty * ml.product_id.weight

            rec.total_weight = total_weight

    @api.depends("delivery_package_type_id")
    def _compute_package_base_weight(self):
        for rec in self:
            rec.package_base_weight = rec.delivery_package_type_id.base_weight or 0.0
            rec.package_weight_uom_name = rec.delivery_package_type_id.weight_uom_name

    @api.depends("delivery_package_type_id", "package_count", "picking_id")
    def _compute_package_shipping_weight(self):
        for rec in self:
            item_weight = rec.total_weight / rec.package_count
            rec.package_shipping_weight = round(
                rec.package_base_weight + item_weight, 2
            )

    @api.depends(
        "delivery_package_type_id",
        "package_count",
        "picking_id",
        "shipping_weight",
        "package_shipping_weight",
    )
    def _compute_package_help_text(self):
        for rec in self:
            help_text = _(
                "Making <b>%(count)s</b> package(s) using <b>%(package_type)s</b> "
                "with a total weight of <b>%(total_weight)s</b> <b>%(uom)s</b>.<br/>"
                "Using shipping weight of "
                "<b>%(shipping_weight)s</b> <b>%(uom)s</b> per package."
            ) % {
                "count": rec.package_count,
                "package_type": rec.delivery_package_type_id.name or _("Unknown"),
                "total_weight": rec.total_weight,
                "uom": rec.weight_uom_name,
                "shipping_weight": rec.package_shipping_weight,
            }
            rec.package_help_text = help_text

    def action_put_in_pack(self):
        if self.package_count == 1:
            return super().action_put_in_pack()

        # Share move lines into packages
        move_lines = self.picking_id.move_line_ids_without_package
        if not move_lines:
            raise ValidationError(
                _("There are no move lines to pack. Please check the picking.")
            )

        total_qty = sum(move_lines.mapped("quantity"))
        items_per_package = ceil(total_qty / self.package_count)

        self.picking_id._helper_distribute_items_into_packages(
            move_lines=move_lines,
            package_type_id=self.delivery_package_type_id,
            items_per_package=items_per_package,
            shipping_weight=self.package_shipping_weight,
        )
