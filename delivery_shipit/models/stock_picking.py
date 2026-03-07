from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    shipit_shipment_id = fields.Char(
        string="ShipIT shipment ID",
        copy=False,
    )
    shipit_tracking_codes = fields.Char(
        string="ShipIT tracking codes",
        copy=False,
    )
    shipit_payload = fields.Text(
        string="ShipIT payload",
        copy=False,
    )
    shipit_last_error = fields.Text(
        string="ShipIT last error",
        copy=False,
    )
