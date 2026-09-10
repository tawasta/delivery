from odoo import fields, models


class ShipitPickupPointWizardLine(models.TransientModel):
    _name = "shipit.pickup.point.wizard.line"
    _description = "Shipit pickup point wizard line"
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
    service_id = fields.Char(
        string="Service ID",
    )
    service_name = fields.Char(
        string="Service",
    )
    carrier_name = fields.Char()
    distance_kilometers = fields.Float()

    def action_select_point(self):
        self.ensure_one()
        self.wizard_id.selected_line_id = self
        return self.wizard_id._get_action()
