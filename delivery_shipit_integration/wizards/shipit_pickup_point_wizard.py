import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.shipit_request import ShipitAPIError

_logger = logging.getLogger(__name__)


class ShipitPickupPointWizard(models.TransientModel):
    _name = "shipit.pickup.point.wizard"
    _description = "Shipit pickup point wizard"

    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        required=True,
    )

    postcode = fields.Char(
        required=True,
    )

    country_code = fields.Char(
        default="FI",
        required=True,
        readonly=True,
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

    pickup_point_limit = fields.Integer(
        default=10,
        required=True,
        readonly=True,
    )

    line_ids = fields.One2many(
        comodel_name="shipit.pickup.point.wizard.line",
        inverse_name="wizard_id",
    )

    selected_line_id = fields.Many2one(
        comodel_name="shipit.pickup.point.wizard.line",
        string="Selected pickup point",
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
        result.setdefault("picking_id", picking.id)
        result.setdefault("postcode", postcode)
        result["country_code"] = self.country_code or "FI"
        result["pickup_point_limit"] = self.pickup_point_limit
        return result

    def _get_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Shipit pickup points"),
            "res_model": self._name,
            "view_mode": "form",
            "view_id": self.env.ref(
                "delivery_shipit_integration.view_shipit_pickup_point_wizard"
            ).id,
            "target": "new",
            "res_id": self.id,
        }

    def action_search_points(self):
        self.ensure_one()

        carrier = self.picking_id.carrier_id
        if carrier.shipit_service_code is False:
            raise UserError(
                _("Shipit pickup point search is only available for Shipit carrier.")
            )

        shipit_request = self.env.company.shipit_request()

        try:
            points = shipit_request.search_service_points(
                postcode=self.postcode,
                country_code=self.country_code,
                service_ids=[self.picking_id.carrier_id.shipit_service_code],
                point_type=self.point_type,
                limit=self.pickup_point_limit,
            )
        except ShipitAPIError as error:
            raise UserError(
                _(
                    "Shipit pickup point search failed for %(name)s:\n%(message)s",
                    {
                        "name": self.picking_id.name,
                        "message": str(error),
                    },
                )
            ) from error

        lines = []
        for point in points:
            service_id = str(point.get("service_id") or "").strip()
            lines.append(
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
                        "service_id": service_id,
                        "service_name": point.get("carrier") or service_id,
                        "carrier_name": point.get("carrier") or "",
                        "distance_kilometers": point.get("distance_kilometers") or 0.0,
                    },
                )
            )

        self.write({"line_ids": [(5, 0, 0)] + lines, "selected_line_id": False})

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
