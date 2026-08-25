import logging
from math import ceil

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    delivery_type = fields.Selection(
        related="picking_id.delivery_type",
    )

    helper_package_count = fields.Integer(
        string="Packages",
        help="Auto-create this many packages",
        compute="_compute_helper_package_count",
        default=1,
    )

    helper_items_per_package = fields.Integer(
        string="Items per package",
        help="Split the items in this move evenly across the packages",
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

    helper_package_help_text = fields.Html(
        help="Help text for the package weight",
        compute="_compute_helper_package_help_text",
    )

    helper_allow_auto_packaging = fields.Boolean(
        string="Allow automatic packaging",
        compute="_compute_helper_package_help_text",
    )

    # TODO: Allowed packages does nothing yet
    allowed_package_ids = fields.Many2many(
        comodel_name="stock.quant.package",
        related="picking_id.allowed_package_ids",
    )

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

    @api.onchange("helper_package_type_id")
    def _compute_helper_items_per_package(self):
        for rec in self:
            # TODO: package/item-spesific defaults for items per package
            rec.helper_items_per_package = (
                rec.product_uom_qty if rec.product_uom_qty else 1
            )

    @api.onchange("helper_package_type_id", "helper_items_per_package")
    def _compute_helper_package_count(self):
        for rec in self:
            rec.helper_package_count = (
                ceil(rec.product_uom_qty / rec.helper_items_per_package)
                if rec.helper_items_per_package
                else 1
            )

    @api.onchange("helper_package_type_id")
    def _onchange_helper_package_type_id(self):
        for rec in self:
            # TODO: package/item-spesific defaults for items per package
            rec.helper_items_per_package = (
                rec.product_uom_qty if rec.product_uom_qty else 1
            )

    @api.depends(
        "helper_package_type_id",
        "helper_items_per_package",
    )
    def _compute_helper_package_help_text(self):
        for rec in self:
            if rec.product_uom_qty > sum(rec.move_line_ids.mapped("quantity")):
                rec.helper_allow_auto_packaging = False
                help_text = _(
                    "<span class='text-danger'>"
                    "There are more items to pack than there are available. "
                    "Please ensure that there are enough items in stock "
                    "before continuing with automatic packaging.</span>"
                )
            else:
                rec.helper_allow_auto_packaging = True
                help_text = _(
                    "Packing <b>%(item_count)s</b> item(s) "
                    "into <b>%(package_count)s</b> package(s).<br/> "
                    "Packing <b>%(items_per_package)s</b> items per package.<br/> "
                    "Using <b>%(package_type)s</b> as the package type.<br/> "
                    "Total item weight is "
                    "<b>%(total_weight)s</b> <b>%(weight_uom)s</b>.<br/> ",
                    item_count=rec.product_uom_qty,
                    package_count=rec.helper_package_count,
                    items_per_package=rec.helper_items_per_package,
                    package_type=rec.helper_package_type_id.name or _("Unknown"),
                    total_weight=rec.weight,
                    weight_uom=rec.helper_package_weight_uom_name or "",
                )

            rec.helper_package_help_text = help_text

    def action_auto_create_packages(self):
        self.ensure_one()

        if self.helper_items_per_package < 1:
            raise ValidationError(
                _("Items per package must be greater than or equal to 1.")
            )
        # Create the first package
        current_package = self._helper_create_package()

        # Initialize the current package room
        current_package_room = self.helper_items_per_package

        # If there are existing move lines, put them into packages
        for line in self.move_line_ids:
            _logger.debug("Current package: %s", current_package.name)
            if line.result_package_id:
                # Already packed, skip this line
                _logger.debug(
                    "Line already packed in package %s, skipping",
                    line.result_package_id.name,
                )
                continue

            while line.quantity > current_package_room:
                _logger.debug(
                    "Quantity %s exceeds current package room %s. Splitting line",
                    line.quantity,
                    current_package_room,
                )
                # If the line is too big for the current package, split it
                new_line = line.copy()
                new_line.quantity = line.quantity - current_package_room
                line.quantity = current_package_room
                _logger.debug("New line quantity %s", new_line.quantity)
                _logger.debug("Original line quantity %s", line.quantity)

                # Fill the current package
                if current_package_room > 0:
                    line.result_package_id = current_package

                # Create a new package for the remaining items
                _logger.debug("Creating new package for remaining items")
                self._helper_finalize_package(current_package)
                current_package = self._helper_create_package()
                current_package_room = self.helper_items_per_package
                line = new_line

            # Put this line into the current package
            _logger.debug(
                "Putting line quantity %s into package %s",
                line.quantity,
                current_package.name,
            )
            line.result_package_id = current_package
            current_package_room -= line.quantity
            if current_package_room <= 0:
                # If the current package is full, create a new one
                _logger.debug("Current package is full, creating a new package")
                self._helper_finalize_package(current_package)
                current_package = self._helper_create_package()
                current_package_room = self.helper_items_per_package

        self._helper_finalize_package(current_package)
        self.write({"helper_package_type_id": False})

    def _helper_create_package(self):
        QuantPackage = self.env["stock.quant.package"]
        # Default package values
        package_vals = {
            "package_type_id": self.helper_package_type_id.id,
        }
        package = QuantPackage.create(package_vals)
        _logger.debug("Created a new package: %s", package.name)
        return package

    def _helper_finalize_package(self, package):
        # Finalize the package
        _logger.debug("Finalizing package %s", package.name)
        # TODO: allow overwriting shipping weight
        # package.write({"shipping_weight": })
        self.picking_id.allowed_package_ids = [(4, package.id)]

        return package
