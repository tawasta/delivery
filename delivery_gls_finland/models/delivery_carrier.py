import logging
import uuid

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from .gls_finland_request import GlsFinlandRequest

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):

    _inherit = "delivery.carrier"

    # region Fields
    delivery_type = fields.Selection(
        selection_add=[("gls_finland", "GLS Finland")],
        ondelete={"gls_finland": "set default"},
    )
    gls_finland_api_key = fields.Char(
        string="GLS Finland API key",
    )
    gls_finland_customer_number = fields.Char(
        string="GLS Finland Customer number",
    )
    gls_finland_product_code = fields.Selection(
        string="GLS product",
        help="GLS Finland product code",
        selection=[
            ("10000", "EuroBusinessParcel"),
            ("10013", "EuroBusinessFreight"),
            ("10015", "GlobalBusinessParcel"),
            ("10010", "GlobalExpressParcel"),
        ],
    )
    gls_label_type = fields.Selection(
        string="Label type",
        selection=[
            ("A4", "A4, one label per page"),
            ("A4FIT", "A4, two labels per page"),
            ("A5", "A5, one label per page"),
            ("label", "Sticker"),
            ("glslabel", "Sticker with embedded logo"),
            ("none", "None"),
        ],
        default="label",
        required=True,
    )
    gls_finland_service_ids = fields.Many2many(
        string="GLS services", comodel_name="gls.finland.service"
    )
    # endregion

    # region Helpers
    def _get_gls_finland_config(self):
        config = {
            "api_key": self.gls_finland_api_key,
            "prod": self.prod_environment,
        }
        return config

    def _gls_finland_map_record(self, picking):
        mode = "production" if self.prod_environment else "test"

        if picking.gls_finland_uuid:
            # GLS UUID is already set, if we are sending a batch shipment
            gls_uuid = picking.gls_finland_uuid
            pickings = picking.search([("gls_finland_uuid", "=", gls_uuid)])

            if len(pickings.mapped("partner_id")) > 1:
                raise ValidationError(
                    _("Trying to confirm pickings with different delivery addresses")
                )
        else:
            gls_uuid = str(uuid.uuid4())
            picking.gls_finland_uuid = gls_uuid
            pickings = picking

        # Get contents and other information from multiple pickings
        contents = ", ".join(
            [p.contents or "" for p in pickings if p.contents is not False]
        )
        info = ", ".join(
            [p.shipment_info or "" for p in pickings if p.shipment_info is not False]
        )
        origin = ", ".join([p.origin or "" for p in pickings if p.origin is not False])
        parcels = sum([p.parcels or 0 for p in pickings])
        totalweight = pickings._get_gls_finland_picking_weight()

        values = {
            "api": {
                "uuid": gls_uuid,
                "version": 2.1,
                "mode": mode,
                "sourcesystem": "Tawasta Odoo",
            },
            "order": {
                "glscustno": self.gls_finland_customer_number or "",
                "labeltype": self.gls_label_type,
            },
            "deladdr": self._get_gls_finland_address(picking.partner_id),
            "shipment": {
                "contents": contents,
                # "donotstack": "",
                "glsproduct": self.gls_finland_product_code,
                # "inco": "",
                "info": info,
                "shipperref": origin,
                "totalweight": totalweight,
            },
        }

        gls_incoterms = [
            p.sale_id.incoterm.gls_finland_incoterm for p in pickings if p.sale_id
        ]
        if len(gls_incoterms) > 1:
            raise ValidationError(_("Trying to use multiple incoterms on a shipment!"))
        elif gls_incoterms:
            # Incoterm is only used in non-EU shipments.
            # It can be always sent, but will be ignored in EU shipments
            values["shipment"]["inco"] = gls_incoterms[0]

        transport_units = []
        if parcels > 0:
            # Manual parcel amount will override packages

            # A simplified weight: shipping weight distributed to parcels
            weight = totalweight / parcels

            # Create x parcels, where x is parcel amount
            for _x in range(0, parcels):
                transport_units.append({"contents": contents, "weight": weight})
        else:
            # The whole picking is a one package
            transport_units.append(
                {
                    "contents": contents,
                    "weight": totalweight,
                }
            )

        # TODO: using packages is kind of complicated, so it's disabled.
        #  Before re-allowing, consider these
        #  - What if every line is not packaged?
        #  - What if package includes other products, not on this picking
        # if picking.package_ids:
        #     for package in picking.package_ids:
        #         package_values = {
        #             # TODO: package-specific contents
        #             "contents": contents,
        #             "weight": package.shipping_weight or package.weight,
        #         }
        #         if package.packaging_id:
        #             package_values.update(
        #                 {
        #                     "height": package.packaging_id.height,
        #                     "length": package.packaging_id.packaging_length,
        #                     "width": package.packaging_id.width,
        #                 }
        #             )
        #
        #         transport_units.append(package_values)

        values["transportunits"] = transport_units

        # Add GLS Finland service codes
        services = []
        for gls_service in picking.gls_finland_service_ids:
            service = {"service": gls_service.code}

            if gls_service.code == "90000":
                # Email Pre-advice
                partner_email = self._get_email_pre_advice_email(picking)
                service["email"] = partner_email

            services.append(service)

        if services:
            values["services"] = services

        return values

    def _get_email_pre_advice_email(self, picking):
        # Helper for getting email pre-advice email
        email = (
            picking.partner_id.email
            or picking.partner_id.commercial_partner_id.email
            or ""
        )

        return email

    def _get_gls_finland_address(self, partner):
        """
        Get Address from a partner
        """
        commercial_partner = partner.commercial_partner_id

        name1 = partner.commercial_company_name or partner.name

        address = {
            "addrtype": "business" if commercial_partner.is_company else "private",
            # Name is required, and there should never be a situation where it is missing
            "name1": name1[0:40],
            # Province is not used in API yet
            # "province": ""[0:40],
            # "provincecode": ""[0:3],
            # Street is mandatory
            "street1": partner.street and partner.street[0:40],
        }

        # Contact name
        contact_name = partner.name or commercial_partner.name or ""
        if contact_name:
            address["contactname"] = contact_name[0:40]

        # Country
        if partner.country_id.code:
            address["country"] = partner.country_id.code or ""

        # Email
        partner_email = partner.email or commercial_partner.email or ""
        if partner_email:
            address["email"] = partner_email[0:255]

        # TODO: eori

        # Mobile
        partner_mobile = partner.mobile or commercial_partner.mobile or ""
        if partner_mobile:
            address["mobile"] = partner_mobile[0:40]

        # TODO: name2

        # City
        if partner.city:
            address["postaddr"] = partner.city and partner.city[0:40]

        # ZIP code
        if partner.zip:
            address["zipcode"] = partner.zip and partner.zip[0:10]

        # Street 2
        if partner.street2:
            address["street2"] = partner.street2 and partner.street2[0:40]

        # Telephone
        partner_telephone = partner.phone or commercial_partner.phone or ""
        if partner_telephone:
            address["telephone"] = partner_telephone[0:40]

        # VAT
        partner_vat = partner.vat or commercial_partner.vat or ""
        if partner_vat:
            address["vatid"] = partner_vat[0:17]

        return address

    # endregion

    # region API Calls
    def gls_finland_send_shipping(self, pickings):
        gls_request = GlsFinlandRequest(**self._get_gls_finland_config())
        result = []

        for picking in pickings:
            if picking.gls_finland_uuid:
                # This shipment may be already sent. Just copy information from another picking
                sent_picking = picking.search(
                    [
                        ("gls_finland_uuid", "=", picking.gls_finland_uuid),
                        ("carrier_tracking_ref", "!=", False),
                    ],
                    limit=1,
                )

                if sent_picking:
                    picking.gls_finland_tracking_codes = (
                        sent_picking.gls_finland_tracking_codes
                    )
                    values = dict(
                        tracking_number=sent_picking.carrier_tracking_ref,
                        exact_price=0,
                    )
                    result.append(values)

                    # Copy attachments from sent picking (to get PDF-labels)
                    attachments = (
                        self.env["ir.attachment"]
                        .sudo()
                        .search(
                            [
                                ("res_id", "=", sent_picking.id),
                                ("res_model", "=", "stock.picking"),
                            ]
                        )
                    )
                    for attachment in attachments:
                        attachment.copy()
                        attachment.res_id = picking.id
                    continue

            # Normal functionality, when there is no existing picking
            values = dict(
                shipment=self._gls_finland_map_record(picking),
                tracking_number=False,
                exact_price=0,
            )
            _logger.info(_("Using shipment values {}").format(values))

            try:
                response = gls_request._send_shipping([values["shipment"]])
            except Exception as e:
                raise e

            _logger.info(_("Sent picking {}".format(picking.name)))
            if not response:
                result.append(values)
                continue

            if response:
                info = response[0]
                transportunits = info.get("transportunits")

                if len(transportunits) > 1:
                    _logger.warning(
                        _("Multiple transport units received. This is not supported!")
                    )

                tracking_codes = ""
                for transportunit in transportunits:
                    trackingno = transportunit.get("glstrackingno")
                    tracking_codes += _("{},").format(trackingno)

                # Strip the last comma
                tracking_codes = tracking_codes.rstrip(",")

                values["tracking_number"] = trackingno
                # Add all tracking codes as a comma-separated list
                picking.gls_finland_tracking_codes = tracking_codes

                # Filename is usually "Label_12345678.pdf"
                filename = "{}_{}.pdf".format(picking.name, trackingno)

                self.env["ir.attachment"].sudo().create(
                    {
                        "name": filename,
                        "datas": info.get("labelpdf"),
                        "type": "binary",
                        "res_model": "stock.picking",
                        "res_id": picking.id,
                    }
                )

            result.append(values)

        return result

    def gls_finland_cancel_shipment(self, pickings):
        gls_request = GlsFinlandRequest(**self._get_gls_finland_config())
        for p in pickings.filtered("carrier_tracking_ref"):
            try:
                gls_request._cancel_shipment(p.carrier_tracking_ref)
            except Exception as e:
                raise e

        # TODO: delete attachments

        return True

    def gls_finland_get_tracking_link(self, picking):
        # TODO: selectable language
        lang = "en"
        if lang == "en":
            url = "https://gls-group.eu/FI/en/parcel-tracking?match="
        else:
            url = "https://gls-group.eu/FI/fi/laehetysseuranta?match="

        if picking.gls_finland_tracking_codes:
            url += picking.gls_finland_tracking_codes

        return url

    # endregion
