from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"

    delivery_type = fields.Selection(
        related="picking_id.delivery_type",
    )

    helper_product_count = fields.Float(
        string="Items to pack",
        help="Number of items to pack",
        store=True,
        compute="_compute_helper_product_count",
        readonly=False,
        digits="Product Unit of Measure",
        copy=False,
    )

    helper_package_count = fields.Integer(
        string="Packages",
        help="Auto-create this many packages",
        default=1,
        copy=False,
    )

    helper_package_type_id = fields.Many2one(
        comodel_name="stock.package.type",
        string="Package Type",
        help="Use this package type when auto-creating packages",
        copy=False,
    )

    helper_package_base_weight = fields.Float(
        string="Package weight",
        compute="_compute_helper_package_base_weight",
    )
    helper_package_weight_uom_name = fields.Char(
        compute="_compute_helper_package_base_weight",
    )
    helper_package_shipping_weight = fields.Float(
        string="Shipping weight",
        help="Shipping weight of one package",
        compute="_compute_helper_package_shipping_weight",
        store=True,
        readonly=False,
        copy=False,
    )
    helper_package_help_text = fields.Html(
        help="Help text for the package weight",
        compute="_compute_helper_package_help_text",
    )

    @api.constrains("helper_package_count")
    def _check_helper_package_count(self):
        for rec in self:
            if rec.helper_package_count < 1:
                raise UserError(_("Package count must be greater than or equal to 1."))
            if rec.helper_package_count > rec.product_uom_qty:
                raise UserError(_("Can't have more packages than items to pack."))

    @api.depends("helper_package_type_id", "move_line_ids")
    def _compute_helper_product_count(self):
        for rec in self:
            packed_lines = rec.move_line_ids.filtered(lambda ml: ml.result_package_id)
            packed_qty = sum(packed_lines.mapped("quantity"))
            rec.helper_product_count = rec.product_uom_qty - packed_qty

    @api.depends("helper_package_count", "helper_package_type_id")
    def _compute_helper_package_base_weight(self):
        for rec in self:
            # Package type weight (not including items)
            rec.helper_package_base_weight = (
                rec.helper_package_type_id.base_weight or 0.0
            )
            rec.helper_package_weight_uom_name = (
                rec.helper_package_type_id.weight_uom_name
            )

    @api.depends("helper_package_count", "helper_package_type_id")
    def _compute_helper_package_shipping_weight(self):
        for rec in self:
            total_weight = rec.weight or 0.0
            package_count = rec.helper_package_count or 1
            item_weight = total_weight / package_count
            # Items weight
            rec.helper_package_shipping_weight = (
                rec.helper_package_base_weight + item_weight
            )

    @api.depends(
        "helper_package_count",
        "helper_product_count",
        "helper_package_type_id",
        "helper_package_shipping_weight",
    )
    def _compute_helper_package_help_text(self):
        for rec in self:
            help_text = _(
                "Packing <b>%(product_count)s</b> item(s) "
                "into <b>%(package_count)s</b> package(s).<br/> "
                "Using <b>%(package_type)s</b> as the package type.<br/> "
                "Total item weight is "
                "<b>%(total_weight)s</b> <b>%(weight_uom)s</b>.<br/> "
                "Using a shipping weight of "
                "<b>%(shipping_weight)s</b> <b>%(weight_uom)s</b> per package."
            ) % {
                "product_count": rec.helper_product_count,
                "package_count": rec.helper_package_count,
                "package_type": rec.helper_package_type_id.name or _("Unknown"),
                "total_weight": rec.weight,
                "weight_uom": rec.helper_package_weight_uom_name or "",
                "shipping_weight": round(rec.helper_package_shipping_weight, 2),
            }
            rec.helper_package_help_text = help_text

    def action_auto_create_packages(self):
        QuantPackage = self.env["stock.quant.package"]

        for move in self:
            # Make a desired amount of packages.
            # Share the items in the move evenly across the packages.
            # TODO: Option to share items in a different way, e.g. by weight or volume.
            item_qty = int(move.helper_product_count / move.helper_package_count)
            product_count = move.helper_product_count

            # Remove the existing move line without a package
            if move.move_line_ids:
                move.move_line_ids.filtered(
                    lambda ml: not ml.result_package_id
                ).unlink()

            # As the qty is simplified to an integer,
            # we might have some items left over.
            # Add them to the last package.
            items_packed = 0
            for i in range(move.helper_package_count):
                items_packed += item_qty
                # Add the leftover items to the last package
                if i == move.helper_package_count - 1:
                    item_qty += product_count - items_packed

                package = QuantPackage.create(
                    {
                        "package_type_id": move.helper_package_type_id.id,
                        "shipping_weight": move.helper_package_shipping_weight,
                    }
                )
                move.move_line_ids.create(
                    {
                        "result_package_id": package.id,
                        "product_id": move.product_id.id,
                        "quantity": item_qty,
                        "product_uom_id": move.product_uom.id,
                    }
                )

            move._compute_helper_product_count()
            move.helper_package_count = 1
