from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    shipit_is_carrier = fields.Boolean(
        compute="_compute_shipit_is_carrier",
    )
    shipit_shipment_id = fields.Char(
        string="ShipIT shipment ID",
        copy=False,
    )
    shipit_tracking_codes = fields.Char(
        string="ShipIT tracking codes",
        copy=False,
    )
    shipit_tracking_url = fields.Char(
        string="ShipIT tracking URL",
        copy=False,
    )
    shipit_label_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="ShipIT label attachment",
        copy=False,
    )
    shipit_pickup_point_id = fields.Char(
        string="ShipIT pickup point ID",
        copy=False,
    )
    shipit_pickup_point_name = fields.Char(
        string="ShipIT pickup point name",
        copy=False,
    )
    shipit_pickup_point_address = fields.Char(
        string="ShipIT pickup point address",
        copy=False,
    )
    shipit_pickup_point_zipcode = fields.Char(
        string="ShipIT pickup point ZIP",
        copy=False,
    )
    shipit_pickup_point_city = fields.Char(
        string="ShipIT pickup point city",
        copy=False,
    )
    shipit_pickup_point_country_code = fields.Char(
        string="ShipIT pickup point country",
        copy=False,
    )
    shipit_pickup_point_service_id = fields.Char(
        string="ShipIT pickup point service ID",
        copy=False,
    )
    shipit_payload = fields.Text(
        string="ShipIT payload",
        copy=False,
    )
    shipit_response = fields.Text(
        string="ShipIT response",
        copy=False,
    )
    shipit_last_error = fields.Text(
        string="ShipIT last error",
        copy=False,
    )
    shipit_delivery_done = fields.Boolean(
        default=False,
        copy=False,
    )

    @api.depends("carrier_id")
    def _compute_shipit_is_carrier(self):
        for picking in self:
            picking.shipit_is_carrier = picking.carrier_id.delivery_type == "shipit"

    def _shipit_send_before_validate(self):
        shipit_pickings = self.filtered(
            lambda p: p.carrier_id.delivery_type == "shipit"
            and p.picking_type_code == "outgoing"
            and not p.shipit_delivery_done
            and not p.shipit_shipment_id
            and p.state not in ("done", "cancel")
        )

        for picking in shipit_pickings:
            values = picking.carrier_id.shipit_send_shipping(picking)
            tracking_number = values and values[0].get("tracking_number")

            if tracking_number and not picking.carrier_tracking_ref:
                picking.carrier_tracking_ref = tracking_number

            picking.shipit_delivery_done = True

    def button_validate(self):
        self._shipit_send_before_validate()
        return super().button_validate()

    def action_open_shipit_pickup_point_wizard(self):
        self.ensure_one()

        if self.carrier_id.delivery_type != "shipit":
            raise UserError(
                _("ShipIT pickup point search is available only for ShipIT carrier.")
            )

        view = self.env.ref("delivery_shipit.view_shipit_pickup_point_wizard")
        return {
            "type": "ir.actions.act_window",
            "name": _("ShipIT pickup points"),
            "res_model": "shipit.pickup.point.wizard",
            "view_mode": "form",
            "view_id": view.id,
            "target": "new",
            "context": {
                "active_model": "stock.picking",
                "active_id": self.id,
            },
        }
