import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

class StockPutInPack(models.TransientModel):
    _inherit = "stock.put.in.pack"

    shipit_allowed_package_type_ids = fields.Many2many(
        comodel_name="stock.package.type",
        string="Shipit Allowed Package Types",
        compute="_compute_shipit_allowed_package_type_ids",
        help="Allowed package types to use in shipments."
        "If left empty, all available package types are allowed.",
    )

    def _compute_shipit_allowed_package_type_ids(self):
        for line in self.move_line_ids:
            _logger.error("HERE: ")
            _logger.error(self.move_line_ids[0].picking_id)

