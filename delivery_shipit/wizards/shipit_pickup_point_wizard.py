from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.shipit_request import ShipitAPIError, ShipitRequest

PICKUP_POINT_COUNTRY_CODE = "FI"
PICKUP_POINT_LIMIT = 10


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
        default=PICKUP_POINT_COUNTRY_CODE,
        required=True,
        readonly=True,
    )
    service_option_ids = fields.Many2many(
        comodel_name="shipit.service.option",
        string="Service IDs",
        required=True,
        help="ShipIT serviceId values used for pickup point search.",
    )
    available_service_option_ids = fields.Many2many(
        comodel_name="shipit.service.option",
        compute="_compute_available_service_option_ids",
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
        default=PICKUP_POINT_LIMIT,
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
        result.setdefault("picking_id", picking.id)
        result.setdefault("postcode", postcode)
        result["country_code"] = PICKUP_POINT_COUNTRY_CODE
        result["limit"] = PICKUP_POINT_LIMIT
        carrier_service_ids = picking.carrier_id._shipit_get_service_codes()
        if carrier_service_ids:
            service_options = self.env["shipit.service.option"].search(
                [("code", "in", carrier_service_ids)]
            )
            if service_options:
                result.setdefault("service_option_ids", [(6, 0, service_options.ids)])
        return result

    @api.depends("picking_id")
    def _compute_available_service_option_ids(self):
        service_model = self.env["shipit.service.option"]
        all_options = service_model.search([])

        for wizard in self:
            carrier_codes = wizard.picking_id.carrier_id._shipit_get_service_codes()
            if carrier_codes:
                wizard.available_service_option_ids = service_model.search(
                    [("code", "in", carrier_codes)]
                )
            else:
                wizard.available_service_option_ids = all_options

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

    # TODO: Could we use onchange for usability?
    # @api.onchange("postcode", "service_option_ids", "point_type")
    def action_search_points(self):
        self.ensure_one()

        carrier = self.picking_id.carrier_id
        if carrier.shipit_service_code is False:
            raise UserError(
                _("ShipIT pickup point search is only available for ShipIT carrier.")
            )

        shipit_request = ShipitRequest(**carrier._get_shipit_config())

        try:
            points = shipit_request.search_service_points(
                postcode=self.postcode,
                country_code=PICKUP_POINT_COUNTRY_CODE,
                service_ids=self.service_option_ids.mapped("code"),
                point_type=self.point_type,
                limit=PICKUP_POINT_LIMIT,
            )
        except ShipitAPIError as error:
            raise UserError(
                _("ShipIT pickup point search failed for %(name)s:\n%(message)s")
                % {
                    "name": self.picking_id.name,
                    "message": str(error),
                }
            ) from error

        service_ids = {
            str(point.get("service_id") or "").strip()
            for point in points
            if point.get("service_id")
        }
        service_name_by_code = {}
        if service_ids:
            service_options = self.env["shipit.service.option"].search(
                [("code", "in", list(service_ids))]
            )
            service_name_by_code = {
                service_option.code: service_option.name
                for service_option in service_options
                if service_option.code
            }

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
                        "service_name": service_name_by_code.get(service_id)
                        or point.get("carrier")
                        or service_id,
                        "carrier_name": point.get("carrier") or "",
                        "distance_kilometers": point.get("distance_kilometers") or 0.0,
                    },
                )
            )

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
