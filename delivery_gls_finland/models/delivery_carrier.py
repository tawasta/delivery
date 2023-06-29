import logging
import uuid

from odoo import _, fields, models

from .gls_finland_request import GlsFinlandRequest

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):

    _inherit = "delivery.carrier"

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
    gls_finland_service_code = fields.Selection(
        string="GLS service",
        help="GLS Finland service code",
        selection=[
            ("11028", "AddOnInsuranceService"),
            ("11047", "ShopReturnService"),
            ("11055", "ShopDeliveryService"),
            ("11069", "FlexDeliveryService"),
            ("90000", "Email preadvice"),
        ],
    )

    # region Business methods
    def _get_gls_finland_config(self):
        config = {
            "api_key": self.gls_finland_api_key,
            "prod": self.prod_environment,
        }
        return config

    def _gls_finland_map_record(self, picking):
        mode = "production" if self.prod_environment else "test"
        picking.gls_finland_uuid = str(uuid.uuid4())

        contents = picking.contents or picking.origin or ""

        values = {
            "api": {
                "uuid": picking.gls_finland_uuid,
                "version": 2.1,
                "mode": mode,
                "sourcesystem": "Tawasta Odoo",
            },
            "order": {
                "glscustno": self.gls_finland_customer_number or "",
                "labeltype": "label",
            },
            "deladdr": self._get_gls_finland_address(picking.partner_id),
            "shipment": {
                "contents": contents,
                # "donotstack": "",
                "glsproduct": self.gls_finland_product_code,
                # "inco": "",
                "info": picking.shipment_info or "",
                "shipperref": picking.origin or "",
                "totalweight": picking._get_gls_finland_picking_weight(),
            },
        }

        transport_units = []
        if picking.parcels:
            # Manual parcel amount will override packages

            # A simplified weight: shipping weight distributed to parcels
            weight = picking._get_gls_finland_picking_weight() / picking.parcels

            # Create x parcels, where x is parcel amount
            for x in range(0, picking.parcels):
                transport_units.append({"contents": contents, "weight": weight})

        elif picking.package_ids:
            for package in picking.package_ids:
                package_values = {
                    # TODO: package-specific contents
                    "contents": contents,
                    "weight": package.shipping_weight or package.weight,
                }
                if package.packaging_id:
                    package_values.update(
                        {
                            "height": package.packaging_id.height,
                            "length": package.packaging_id.packaging_length,
                            "width": package.packaging_id.width,
                        }
                    )

                transport_units.append(package_values)
        else:
            # The whole picking is a one package
            transport_units.append(
                {
                    "contents": contents,
                    "weight": picking.shipping_weight or picking.weight,
                }
            )

        values["transportunits"] = transport_units

        if self.gls_finland_service_code:
            values["services"] = [{"service": self.gls_finland_service_code}]

        return values

    def _get_gls_finland_address(self, partner):
        """
        Get Address from a partner
        """
        commercial_partner = partner.commercial_partner_id

        address = {
            "addrtype": "business" if commercial_partner.is_company else "private",
            # Name is required, and there should never be a situation where it is missing
            "name1": partner.commercial_company_name or "",
            # Province is not used in API yet
            # "province": ""[0:40],
            # "provincecode": ""[0:3],
            # Street is mandatory
            "street1": partner.street[0:40],
        }

        # Contact name
        contact_name = partner.name or commercial_partner.name
        if contact_name:
            address["contactname"] = contact_name[0:40]

        # Country
        if partner.country_id.code:
            address["country"] = partner.country_id.code or ""

        # Email
        partner_email = partner.email or commercial_partner.email
        if partner_email:
            address["email"] = partner_email[0:255]

        # TODO: eori

        # Mobile
        partner_mobile = partner.mobile or commercial_partner.mobile
        if partner_mobile:
            address["mobile"] = partner_mobile[0:40]

        # TODO: name2

        # City
        if partner.city:
            address["postaddr"] = partner.city[0:40]

        # ZIP code
        if partner.zip:
            address["zipcode"] = partner.zip[0:10]

        # Street 2
        if partner.street2:
            address["street2"] = partner.street2[0:40]

        # Telephone
        partner_telephone = partner.phone or commercial_partner.phone
        if partner_telephone:
            address["telephone"] = partner_telephone[0:40]

        # VAT
        partner_vat = partner.vat or commercial_partner.vat
        if partner_vat:
            address["vatid"] = partner_vat[0:17]

        return address

    # endregion

    # region Business methods
    def gls_finland_send_shipping(self, pickings):
        gls_request = GlsFinlandRequest(**self._get_gls_finland_config())
        result = []
        for picking in pickings:
            values = dict(
                shipment=self._gls_finland_map_record(picking),
                tracking_number=False,
                exact_price=0,
            )

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
                for transportunit in transportunits:
                    trackingno = transportunit.get("glstrackingno")

                values["tracking_number"] = trackingno

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
        # TODO: tracking url with tracking number
        url = "https://gls-group.com/FI/en/parcel-tracking"

        return url

    # endregion
