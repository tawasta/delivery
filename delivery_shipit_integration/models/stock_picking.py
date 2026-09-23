from odoo import _, api, fields, models


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
        string="Shipit Additional Services",
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
        string="Shipit shipment ID",
        copy=False,
    )
    shipit_tracking_codes = fields.Char(
        string="Shipit tracking codes",
        copy=False,
    )
    shipit_tracking_url = fields.Char(
        string="Shipit tracking URL",
        copy=False,
    )
    shipit_label_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Shipit label attachment",
        copy=False,
    )
    shipit_pickup_point_id = fields.Char(
        string="Shipit pickup point ID",
        copy=False,
    )
    shipit_pickup_point_name = fields.Char(
        string="Shipit pickup point name",
        copy=False,
    )
    shipit_pickup_point_address = fields.Char(
        string="Shipit pickup point address",
        copy=False,
    )
    shipit_pickup_point_zipcode = fields.Char(
        string="Shipit pickup point ZIP",
        copy=False,
    )
    shipit_pickup_point_city = fields.Char(
        string="Shipit pickup point city",
        copy=False,
    )
    shipit_pickup_point_country_code = fields.Char(
        string="Shipit pickup point country",
        copy=False,
    )
    shipit_pickup_point_service_id = fields.Char(
        string="Shipit pickup point service ID",
        copy=False,
    )
    shipit_payload = fields.Text(
        string="Shipit payload",
        copy=False,
    )
    shipit_response = fields.Text(
        string="Shipit response",
        copy=False,
    )
    shipit_last_error = fields.Text(
        string="Shipit last error",
        copy=False,
    )
    shipit_delivery_done = fields.Boolean(
        default=False,
        copy=False,
    )

    # Compability field for making maintaining multiple versions of module easier
    shipit_package_ids = fields.Many2many(
        "stock.package", compute="_compute_shipit_packages", string="Packages"
    )

    # Compability function for making maintaining multiple versions of module easier
    @api.depends("move_line_ids", "move_line_ids.result_package_id")
    def _compute_shipit_packages(self):
        counts = dict(
            self.env["stock.move.line"]._read_group(
                domain=[
                    ("picking_id", "in", self.ids),
                    ("result_package_id", "!=", False),
                ],
                groupby=["picking_id"],
                aggregates=["__count"],
            )
        )
        self.fetch(["move_line_ids"])
        self.move_line_ids.fetch(["result_package_id"])
        for picking in self:
            packs = set()
            if counts.get(picking, 0):
                for move_line in picking.move_line_ids:
                    if move_line.result_package_id:
                        packs.add(move_line.result_package_id.id)
            picking.shipit_package_ids = list(packs)

    @api.depends("carrier_id")
    def _compute_shipit_additional_service_ids(self):
        for picking in self:
            picking.shipit_additional_service_ids = (
                picking.carrier_id.shipit_default_additional_service_ids
            )

    @api.depends("carrier_id")
    def _compute_shipit_is_carrier(self):
        for picking in self:
            if picking.carrier_id:
                picking.shipit_is_carrier = picking.carrier_id._shipit_is_carrier()
            else:
                picking.shipit_is_carrier = False

    def action_open_shipit_pickup_point_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Shipit pickup points"),
            "res_model": "shipit.pickup.point.wizard",
            "view_mode": "form",
            "view_id": self.env.ref(
                "delivery_shipit_integration.view_shipit_pickup_point_wizard"
            ).id,
            "target": "new",
            "context": {
                "active_model": "stock.picking",
                "active_id": self.id,
            },
        }

    def button_validate(self):
        return super().button_validate()

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

    def action_print_shipit_label(self):
        self.ensure_one()
        if self.shipit_label_attachment_id:
            attachment = self.shipit_label_attachment_id
            url = f"/web/content/{attachment.id}?download=true"

            attachment = self.shipit_label_attachment_id

            return {
                "type": "ir.actions.act_url",
                "url": url,
                "name": attachment.name,
                "target": "new",
            }
