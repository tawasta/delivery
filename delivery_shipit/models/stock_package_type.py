from odoo import api, fields, models

from .delivery_carrier import SHIPIT_CARRIERS


class StockPackageType(models.Model):
    _inherit = "stock.package.type"

    shipit_package_type = fields.Selection(
        string="ShipIT Package Type",
        selection=[
            ("PACKAGE", "Package"),
            ("PALLET[EUR-PALLET]", "EUR-pallet"),
            ("PALLET[TEHOLAVA]", "Pallet (80x60)"),
            ("PALLET-NON-STACKABLE", "Pallet (non-stackable)"),
            ("PALLET", "Pallet"),
            ("PALLET[FIN-LAVA]", "Pallet (120x100)"),
            ("TROLLEY", "Trolley"),
            ("TIRES", "Tyres"),
            ("DOCUMENT", "Document"),
        ],
    )

    shipit_is_carrier = fields.Boolean(
        compute="_compute_shipit_is_carrier",
    )

    package_carrier_type = fields.Selection(
        selection_add=SHIPIT_CARRIERS,
        ondelete={carrier[0]: "set default" for carrier in SHIPIT_CARRIERS},
    )

    @api.depends("package_carrier_type")
    def _compute_shipit_is_carrier(self):
        carriers = [carrier[0] for carrier in SHIPIT_CARRIERS]
        for record in self:
            carrier_type = record.package_carrier_type
            record.shipit_is_carrier = carrier_type and carrier_type in carriers

    @api.onchange("shipit_package_type")
    def _onchange_shipit_package_type(self):
        for record in self:
            record.shipper_package_code = record.shipit_package_type
