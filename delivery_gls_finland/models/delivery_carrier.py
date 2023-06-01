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
                "contents": picking.contents or "",
                # "donotstack": "",
                "glsproduct": self.gls_finland_product_code,
                # "inco": "",
                "info": picking.comment or "",
                "shipperref": picking.origin or "",
                "totalweight": picking.shipping_weight or picking.weight,
            },
        }

        # TODO: support for packages
        for package in picking:
            values["transportunits"] = [
                {
                    "contents": package.contents or "",
                    "weight": package.shipping_weight or package.weight,
                    # "height": 30,
                    # "length": 40,
                    # "width": 30
                }
            ]

        if self.gls_finland_service_code:
            values["services"] = [{"service": self.gls_finland_service_code}]

        return values

    def _get_gls_finland_address(self, partner):
        """
        Get Address from a partner
        """

        address = {
            "addrtype": "business" if partner.is_company else "personal",
            "contactname": partner.name or "",
            "country": partner.country_id.code or "",
            "email": partner.email or "",
            # "eori": "",
            "mobile": partner.mobile or "",
            "name1": partner.commercial_company_name or "",
            # "name2": "",
            "postaddr": partner.city or "",
            "zipcode": partner.zip or "",
            "province": "string",
            "provincecode": "str",
            "street1": partner.street or "",
            "street2": partner.street2 or "",
            "telephone": partner.phone or "",
            "vatid": partner.vat or "",
        }

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
