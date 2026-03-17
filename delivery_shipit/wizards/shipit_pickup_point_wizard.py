from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.shipit_request import ShipitAPIError, ShipitRequest


class ShipitPickupPointWizard(models.TransientModel):
    _name = "shipit.pickup.point.wizard"
    _description = "ShipIT pickup point wizard"

    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        required=True,
    )
    postcode = fields.Char(
        required=True,
    )
    country_code = fields.Char(
        required=True,
    )
    service_ids = fields.Char(
        string="Service IDs",
        required=True,
        help="Comma-separated ShipIT serviceId values used for pickup point search.",
    )
    point_type = fields.Selection(
        selection=[
            ("service_point", "Service point"),
            ("parcel_locker", "Parcel locker"),
            ("outdoor_parcel_locker", "Outdoor parcel locker"),
            ("letter_box", "Letter box"),
        ],
        default="service_point",
        required=True,
    )
    limit = fields.Integer(
        default=10,
    )
    line_ids = fields.One2many(
        comodel_name="shipit.pickup.point.wizard.line",
        inverse_name="wizard_id",
    )
    selected_line_id = fields.Many2one(
        comodel_name="shipit.pickup.point.wizard.line",
        string="Selected pickup point",
    )
    search_count = fields.Integer(
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)

        if self.env.context.get("active_model") != "stock.picking":
            return result

        active_id = self.env.context.get("active_id")
        picking = self.env["stock.picking"].browse(active_id).exists()
        if not picking:
            return result

        receiver_partner = picking.partner_id
        commercial_partner = receiver_partner.commercial_partner_id
        postcode = receiver_partner.zip or commercial_partner.zip or ""
        country_code = (
            receiver_partner.country_id.code or commercial_partner.country_id.code or ""
        )
        result.setdefault("picking_id", picking.id)
        result.setdefault("postcode", postcode)
        result.setdefault("country_code", country_code)
        result.setdefault("service_ids", picking.carrier_id.shipit_service_code or "")
        return result

    def _get_action(self):
        self.ensure_one()
        view = self.env.ref("delivery_shipit.view_shipit_pickup_point_wizard")
        return {
            "type": "ir.actions.act_window",
            "name": _("ShipIT pickup points"),
            "res_model": self._name,
            "view_mode": "form",
            "view_id": view.id,
            "target": "new",
            "res_id": self.id,
        }

    def action_search_points(self):
        self.ensure_one()

        carrier = self.picking_id.carrier_id
        if carrier.delivery_type != "shipit":
            raise UserError(
                _("ShipIT pickup point search is only available for ShipIT carrier.")
            )

        shipit_request = ShipitRequest(**carrier._get_shipit_config())

        try:
            points = shipit_request.search_service_points(
                postcode=self.postcode,
                country_code=self.country_code,
                service_ids=self.service_ids,
                point_type=self.point_type,
                limit=self.limit,
            )
        except ShipitAPIError as error:
            raise UserError(
                _("ShipIT pickup point search failed for %(name)s:\n%(message)s")
                % {
                    "name": self.picking_id.name,
                    "message": str(error),
                }
            ) from error

        lines = [
            (
                0,
                0,
                {
                    "point_id": str(point.get("id") or ""),
                    "name": point.get("name") or "",
                    "address": point.get("address") or "",
                    "zipcode": point.get("zipcode") or "",
                    "city": point.get("city") or "",
                    "country_code": point.get("country_code") or "",
                    "service_id": point.get("service_id") or "",
                    "carrier_name": point.get("carrier") or "",
                    "distance_kilometers": point.get("distance_kilometers") or 0.0,
                },
            )
            for point in points
        ]

        self.write(
            {
                "line_ids": [(5, 0, 0)] + lines,
                "selected_line_id": False,
                "search_count": len(lines),
            }
        )

        if self.line_ids:
            self.selected_line_id = self.line_ids[0]

        return self._get_action()

    def action_apply_selected_point(self):
        self.ensure_one()
        if not self.selected_line_id:
            raise UserError(_("Select a pickup point first."))

        selected = self.selected_line_id
        self.picking_id.write(
            {
                "shipit_pickup_point_id": selected.point_id,
                "shipit_pickup_point_name": selected.name,
                "shipit_pickup_point_address": selected.address,
                "shipit_pickup_point_zipcode": selected.zipcode,
                "shipit_pickup_point_city": selected.city,
                "shipit_pickup_point_country_code": selected.country_code,
                "shipit_pickup_point_service_id": selected.service_id,
            }
        )
        return {"type": "ir.actions.act_window_close"}


class ShipitPickupPointWizardLine(models.TransientModel):
    _name = "shipit.pickup.point.wizard.line"
    _description = "ShipIT pickup point wizard line"
    _order = "distance_kilometers asc, id asc"

    wizard_id = fields.Many2one(
        comodel_name="shipit.pickup.point.wizard",
        required=True,
        ondelete="cascade",
    )
    point_id = fields.Char(
        string="Pickup ID",
        required=True,
    )
    name = fields.Char(
        required=True,
    )
    address = fields.Char()
    zipcode = fields.Char()
    city = fields.Char()
    country_code = fields.Char()
    service_id = fields.Char()
    carrier_name = fields.Char()
    distance_kilometers = fields.Float()

    def action_select_point(self):
        self.ensure_one()
        self.wizard_id.selected_line_id = self
        return self.wizard_id._get_action()
