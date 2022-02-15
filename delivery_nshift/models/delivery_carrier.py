import logging
from odoo import fields
from odoo import models
from odoo import _
from odoo.exceptions import ValidationError
from .nshift_request import NshiftRequest

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):

    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("nshift", "nShift")],
        ondelete={"nshift": "set default"},
    )
    nshift_carrier_id = fields.Many2one(
        string="Carrier/service",
        comodel_name="delivery.carrier.nshift",
    )

    nshift_username = fields.Char(
        string="Username/ID",
        required=True,
        help="16 uppercase characters",
    )

    nshift_password = fields.Char(
        string="Password/Secret ID",
        required=True,
        help="24 uppercase characters",
    )

    nshift_customer_id = fields.Char(
        string="Customer ID",
    )

    def map_record(self, picking):
        values = {
            "orderNo": picking.origin,
            "senderReference": picking.name,
            "sender": self._get_nshift_address(picking.company_id.partner_id),
            "senderPartners": [
                {
                    "id": self.nshift_carrier_id.partner_code,
                    "custNo": self.nshift_carrier_id.customer_number,
                }
            ],
            "receiver": self._get_nshift_address(picking.partner_id),
            "service": {"id": self.nshift_carrier_id.service_code},
            "parcels": self._get_nshift_parcels(picking),
            "receiverReference": picking.sale_id.client_order_ref or "",
        }

        return values

    # region Helper functions
    def get_pdf_config(self):
        """ Return PDF config """
        # TODO: configurable PDF config

        return dict(
            target4XOffset=0,
            target2YOffset=0,
            target1Media="laser-ste",
            target1YOffset=0,
            target3YOffset=0,
            target2Media="laser-a4",
            target4YOffset=0,
            target4Media=False,
            target3XOffset=0,
            target3Media=False,
            target1XOffset=0,
            target2XOffset=0,
        )

    def _get_nshift_config(self):
        config = {
            "username": self.nshift_username,
            "password": self.nshift_password,
            "prod": self.prod_environment,
            "customer_number": self.nshift_carrier_id.customer_number,
            "partner_code": self.nshift_carrier_id.partner_code,
            "service_code": self.nshift_carrier_id.service_code,
            "customer_id": self.nshift_customer_id,
        }
        return config

    def _get_nshift_address(self, partner):
        """
        Get Address from a partner
        """

        address = dict(
            name=partner.name or "",
            address1=partner.street or "",
            address2=partner.street2 or "",
            zipcode=partner.zip or "",
            city=partner.city or "",
            country=partner.country_id.code or "",
            phone=partner.phone or partner.mobile or "",
            email=partner.email or "",
        )

        return address

    def _get_nshift_parcels(self, picking):
        """
        Get parcels information
        """

        parcels_list = []

        if picking.nshift_packages == "one":
            # The whole picking is a one package
            packages = picking
        elif picking.nshift_packages == "row":
            if not picking.has_packages:
                # Each move line is a package
                packages = picking.move_lines
            else:
                # Each package is a package
                if picking.move_line_ids.filtered(
                    lambda ml: ml.result_package_id is False
                ):
                    # Mixing packaged and non-packaged lines is not supported yet.
                    # We could go through packages and non-packaged lines,
                    # but this is currently prohibited for simplicity
                    raise ValidationError(
                        _(
                            "Mixing packaged and non-packaged lines is not supported."
                            " Please put everything in packs."
                        )
                    )

                packages = picking.package_ids
        else:
            raise ValidationError(_("Please select nShift packaging logic"))

        for package in packages:
            parcels_list.append(
                {
                    "copies": 1,
                    "weight": package.shipping_weight or package.weight,
                    "contents": package.contents,
                    "valuePerParcel": True,
                    "volume": package.volume,
                }
            )

        return parcels_list

    # endregion

    # region Business methods
    def action_nshift_get_carriers(self):
        nshift_request = NshiftRequest(**self._get_nshift_config())

        try:
            response = nshift_request._get_carriers()
        except Exception as e:
            raise (e)

        nshift = self.env["delivery.carrier.nshift"]

        for carrier in response:
            values = {
                "partner_code": carrier.get("id"),
                "carrier_name": carrier.get("description"),
            }
            for service in carrier.get("services"):
                values["name"] = service.get("description")
                values["service_code"] = service.get("id")
                existing_carrier = nshift.search(
                    [("service_code", "=", values["service_code"])]
                )

                if existing_carrier:
                    existing_carrier.sudo().write(values)
                else:
                    nshift.sudo().create(values)

        # TODO: deactivate removed carriers

    def nshift_send_shipping(self, pickings):
        nshift_request = NshiftRequest(**self._get_nshift_config())
        result = []
        for picking in pickings:
            values = dict(
                shipment=self.map_record(picking),
                pdfConfig=self.get_pdf_config(),
                tracking_number=False,
                exact_price=0,
            )

            try:
                response = nshift_request._send_shipping(values)
            except Exception as e:
                raise (e)
            finally:
                _logger.info(_("Sent picking {}".format(picking.name)))
            if not response:
                result.append(values)
                continue

            if response:
                values["tracking_number"] = response[0].get("id")

            for shipment in response:
                for parcel in shipment.get("parcels", []):
                    parcel_number = parcel.get("parcelNo")
                    if parcel_number:
                        picking.message_post(
                            body=_("Adding parcel '{}' to shipment").format(
                                parcel_number
                            )
                        )

                for pdf in shipment.get("pdfs", []):
                    # Filename is usually "Label_12345678.pdf"
                    filename = "{}_{}.pdf".format(
                        pdf.get("description", "File"), pdf.get("id", "unknown")
                    )

                    self.env["ir.attachment"].sudo().create(
                        {
                            "name": filename,
                            "datas": pdf.get("pdf"),
                            "type": "binary",
                            "res_model": "stock.picking",
                            "res_id": picking.id,
                        }
                    )

            result.append(values)

        return result

    def nshift_cancel_shipment(self, pickings):
        nshift_request = NshiftRequest(**self._get_nshift_config())
        for p in pickings.filtered("carrier_tracking_ref"):
            try:
                nshift_request._cancel_shipment(p.carrier_tracking_ref)
            except Exception as e:
                raise (e)

        # TODO: delete attachments

        return True

    def nshift_get_tracking_link(self, picking):
        url = "https://www.unifaunonline.com/ext.uo.{region}.{language}.track?apiKey={apikey}&order={reference}".format(
            region="fi",
            language="fi",
            apikey=self.nshift_username,
            reference=picking.carrier_tracking_ref,
        )
        # TODO: customizable region and language
        #  https://help.unifaun.com/uo-se/en/integrations/unifaun-track---trace.html

        # TODO: reference should probably be "shipmentNo", not "id". Needs testing

        return url

    # endregion
