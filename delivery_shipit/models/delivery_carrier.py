import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("shipit", "ShipIT")],
        ondelete={"shipit": "set default"},
    )
    shipit_api_key = fields.Char(string="ShipIT API key")
    shipit_reseller_id = fields.Char(string="ShipIT reseller ID")
    shipit_service_code = fields.Char(string="ShipIT service code")
    shipit_label_format = fields.Selection(
        string="ShipIT label format",
        selection=[
            ("PDF_A4", "PDF A4"),
            ("PDF_A6", "PDF A6"),
            ("ZPL", "ZPL"),
        ],
        default="PDF_A4",
        required=True,
    )
    shipit_default_length_cm = fields.Float(string="Default package length (cm)")
    shipit_default_width_cm = fields.Float(string="Default package width (cm)")
    shipit_default_height_cm = fields.Float(string="Default package height (cm)")

    def shipit_send_shipping(self, pickings):
        _logger.info(
            "ShipIT send_shipping placeholder invoked for %s pickings",
            len(pickings),
        )
        raise UserError(
            _(
                "ShipIT shipment creation is not implemented yet. "
                "This will be added in the next commit."
            )
        )

    def shipit_get_tracking_link(self, picking):
        return False

    def shipit_cancel_shipment(self, pickings):
        raise UserError(
            _(
                "ShipIT shipment cancellation is not implemented yet. "
                "This will be added in a later phase."
            )
        )
