from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    freight_payer_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Freight payer",
    )
    freight_payer_type = fields.Selection(
        string="Payment type",
        related="freight_payer_partner_id.shipit_payer_type",
        store=True,
        copy=False,
        readonly=False,
    )
    shipit_freight_payer_supported = fields.Boolean(
        related="carrier_id.shipit_freight_payer_supported",
    )

    shipit_additional_service_ids = fields.Many2many(
        string="ShipIT Additional Services",
        comodel_name="shipit.additional.service",
        compute="_compute_shipit_additional_service_ids",
        store=True,
        readonly=False,
        relation="stock_picking_shipit_additional_service_rel",
    )
    shipit_allowed_additional_service_ids = fields.Many2many(
        comodel_name="shipit.additional.service",
        related="carrier_id.shipit_allowed_additional_service_ids",
        relation="stock_picking_shipit_allowed_additional_service_rel",
    )

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
    def _compute_shipit_additional_service_ids(self):
        for picking in self:
            picking.shipit_additional_service_ids = (
                picking.carrier_id.shipit_default_additional_service_ids
            )

    @api.depends("carrier_id")
    def _compute_shipit_is_carrier(self):
        for picking in self:
            picking.shipit_is_carrier = picking.carrier_id._shipit_is_carrier()

    def action_shipit_send_shipping(self):
        shipit_pickings = self.filtered(
            lambda p: p.carrier_id.shipit_service_code is not False
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
        res = super().button_validate()

        if len(self) == 1 and self.shipit_label_attachment_id:
            attachment = self.shipit_label_attachment_id
            url = f"/web/content/{attachment.id}?download=true"

            attachment = self.shipit_label_attachment_id

            return {
                "type": "ir.actions.act_url",
                "url": url,
                "name": attachment.name,
                "target": "new",
            }

        return res

    def action_open_shipit_pickup_point_wizard(self):
        self.ensure_one()

        if not self.carrier_id.shipit_service_code:
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

    def action_clear_shipit_pickup_point(self):
        self.ensure_one()

        self.write(
            {
                "shipit_pickup_point_id": False,
                "shipit_pickup_point_name": False,
                "shipit_pickup_point_address": False,
                "shipit_pickup_point_zipcode": False,
                "shipit_pickup_point_city": False,
                "shipit_pickup_point_country_code": False,
                "shipit_pickup_point_service_id": False,
            }
        )
        return True
