import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    allowed_package_ids = fields.Many2many(
        comodel_name="stock.quant.package",
        relation="stock_picking_allowed_package_rel",
        column1="picking_id",
        column2="package_id",
        string="Allowed packages",
        help="Packages that can be used for this delivery",
    )

    def _helper_create_package(self, package_type_id, shipping_weight=None):
        """
        Create a new package with the given package type and return it.
        """
        self.ensure_one()
        _logger.debug(
            f"Creating a new package "
            f"with package_type_id={package_type_id.id} "
            f"and shipping_weight={shipping_weight}"
        )

        QuantPackage = self.env["stock.quant.package"]
        # Default package values
        package_vals = {
            "package_type_id": package_type_id.id,
        }

        if shipping_weight is not None:
            package_vals["shipping_weight"] = shipping_weight

        package = QuantPackage.create(package_vals)
        _logger.debug("Created a new package: %s", package.name)
        return package

    def _helper_finalize_package(self, package):
        self.ensure_one()
        # Finalize the package
        _logger.debug("Finalizing package %s", package.name)
        # TODO: allow overwriting shipping weight
        # package.write({"shipping_weight": })
        self.allowed_package_ids = [(4, package.id)]

        return package

    def _helper_distribute_items_into_packages(
        self,
        move_lines,
        package_type_id,
        items_per_package,
        shipping_weight=None,
    ):
        # Create the first package
        current_package = self._helper_create_package(
            package_type_id=package_type_id,
            shipping_weight=shipping_weight,
        )

        # Initialize the current package room
        current_package_room = items_per_package

        # If there are existing move lines, put them into packages
        for line in move_lines:
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
                current_package = self._helper_create_package(
                    package_type_id=package_type_id,
                    shipping_weight=shipping_weight,
                )
                current_package_room = items_per_package
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
                current_package = self._helper_create_package(
                    package_type_id=package_type_id,
                    shipping_weight=shipping_weight,
                )
                current_package_room = items_per_package

        self._helper_finalize_package(current_package)
        self._post_put_in_pack_hook(current_package)
