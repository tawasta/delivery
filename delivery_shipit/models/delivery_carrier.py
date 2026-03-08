import base64
import json
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from .shipit_request import ShipitAPIError, ShipitRequest

_logger = logging.getLogger(__name__)

DEFAULT_LENGTH_CM = 15.0
DEFAULT_WIDTH_CM = 11.0
DEFAULT_HEIGHT_CM = 3.0


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("shipit", "ShipIT")],
        ondelete={"shipit": "set default"},
    )
    shipit_api_key = fields.Char(string="ShipIT API key")
    shipit_api_base_url = fields.Char(
        string="ShipIT API base URL",
        help="Optional override for ShipIT API base URL.",
    )
    shipit_auth_mode = fields.Selection(
        string="ShipIT auth mode",
        selection=[
            ("both", "Bearer + X-API-Key"),
            ("bearer", "Bearer only"),
            ("x_api_key", "X-API-Key only"),
        ],
        default="both",
        required=True,
    )
    shipit_create_endpoints = fields.Char(
        string="ShipIT create endpoints",
        default="shipments,create-shipment",
        help="Comma-separated endpoint paths used for create shipment call.",
    )
    shipit_cancel_endpoint_template = fields.Char(
        string="ShipIT cancel endpoint template",
        default="shipments/{shipment_id}",
        help="Endpoint template used for cancellation call.",
    )
    shipit_timeout_seconds = fields.Integer(
        string="ShipIT timeout (seconds)",
        default=30,
    )
    shipit_reseller_id = fields.Char(string="ShipIT reseller ID")
    shipit_service_code = fields.Char(string="ShipIT service code")
    shipit_label_format = fields.Selection(
        string="ShipIT label format",
        selection=[
            ("PDF_A4", "PDF A4"),
            ("PDF_A6", "PDF A6"),
            ("ZPL", "ZPL"),
        ],
        default="PDF_A4",
        required=True,
    )
    shipit_default_length_cm = fields.Float(string="Default package length (cm)")
    shipit_default_width_cm = fields.Float(string="Default package width (cm)")
    shipit_default_height_cm = fields.Float(string="Default package height (cm)")

    def _get_shipit_config(self):
        return {
            "api_key": self.shipit_api_key,
            "prod": self.prod_environment,
            "base_url": (self.shipit_api_base_url or "").strip() or None,
            "auth_mode": self.shipit_auth_mode,
            "create_endpoints": self.shipit_create_endpoints,
            "cancel_endpoint_template": self.shipit_cancel_endpoint_template,
            "timeout": max(1, self.shipit_timeout_seconds or 30),
        }

    def _shipit_get_sender_partner(self, picking):
        warehouse_partner = picking.picking_type_id.warehouse_id.partner_id
        return warehouse_partner or picking.company_id.partner_id

    def _shipit_get_email(self, partner):
        if not partner:
            return ""
        commercial_partner = partner.commercial_partner_id
        return partner.email or commercial_partner.email or ""

    def _shipit_get_phone(self, partner):
        if not partner:
            return ""
        commercial_partner = partner.commercial_partner_id
        return (
            partner.mobile
            or partner.phone
            or commercial_partner.mobile
            or commercial_partner.phone
            or ""
        )

    def _shipit_map_address(self, partner):
        if not partner:
            return {
                "name": "",
                "contactName": "",
                "street1": "",
                "street2": "",
                "postalCode": "",
                "city": "",
                "countryCode": "",
                "email": "",
                "phone": "",
            }

        commercial_partner = partner.commercial_partner_id
        return {
            "name": partner.commercial_company_name
            or partner.name
            or commercial_partner.name
            or "",
            "contactName": partner.name or commercial_partner.name or "",
            "street1": partner.street or "",
            "street2": partner.street2 or "",
            "postalCode": partner.zip or "",
            "city": partner.city or "",
            "countryCode": partner.country_id.code or "",
            "email": self._shipit_get_email(partner),
            "phone": self._shipit_get_phone(partner),
        }

    def _shipit_get_picking_weight(self, picking):
        weight = picking.shipping_weight or picking.weight or 0.0

        if not weight:
            weight = sum(
                (move.product_uom_qty or 0.0) * (move.product_id.weight or 0.0)
                for move in picking.move_ids_without_package
            )

        return float(weight or 0.0)

    def _shipit_get_package_dimensions(self, picking):
        values = {
            "length": self.shipit_default_length_cm or DEFAULT_LENGTH_CM,
            "width": self.shipit_default_width_cm or DEFAULT_WIDTH_CM,
            "height": self.shipit_default_height_cm or DEFAULT_HEIGHT_CM,
        }

        for package in picking.package_ids:
            packaging = package.packaging_id
            if not packaging:
                continue

            if packaging.packaging_length:
                values["length"] = packaging.packaging_length
            if packaging.width:
                values["width"] = packaging.width
            if packaging.height:
                values["height"] = packaging.height
            break

        return values

    def _shipit_validate_required_fields(self, picking, sender, recipient, weight):
        missing_fields = []

        if not self.shipit_api_key:
            missing_fields.append(_("Carrier ShipIT API key"))
        if not self.shipit_reseller_id:
            missing_fields.append(_("Carrier ShipIT reseller ID"))
        if not self.shipit_service_code:
            missing_fields.append(_("Carrier ShipIT service code"))

        required_sender_fields = {
            _("Sender name"): sender.get("name"),
            _("Sender street"): sender.get("street1"),
            _("Sender postal code"): sender.get("postalCode"),
            _("Sender city"): sender.get("city"),
            _("Sender country code"): sender.get("countryCode"),
        }
        for label, value in required_sender_fields.items():
            if not value:
                missing_fields.append(label)

        required_recipient_fields = {
            _("Recipient name"): recipient.get("name"),
            _("Recipient street"): recipient.get("street1"),
            _("Recipient postal code"): recipient.get("postalCode"),
            _("Recipient city"): recipient.get("city"),
            _("Recipient country code"): recipient.get("countryCode"),
            _("Recipient email"): recipient.get("email"),
            _("Recipient phone"): recipient.get("phone"),
        }
        for label, value in required_recipient_fields.items():
            if not value:
                missing_fields.append(label)

        if weight <= 0:
            missing_fields.append(_("Shipment weight"))

        if not missing_fields:
            return True

        details = "\n".join([f"- {field_name}" for field_name in missing_fields])
        msg = _("Missing required ShipIT data for picking %(name)s:\n%(details)s") % {
            "name": picking.name,
            "details": details,
        }
        raise ValidationError(msg)

    def _shipit_build_payload(self, picking):
        sender_partner = self._shipit_get_sender_partner(picking)
        recipient_partner = picking.partner_id

        sender = self._shipit_map_address(sender_partner)
        recipient = self._shipit_map_address(recipient_partner)
        weight = self._shipit_get_picking_weight(picking)
        dimensions = self._shipit_get_package_dimensions(picking)

        self._shipit_validate_required_fields(picking, sender, recipient, weight)

        shipment = {
            "resellerId": self.shipit_reseller_id,
            "serviceCode": self.shipit_service_code,
            "reference": picking.origin or picking.name,
            "sender": sender,
            "recipient": recipient,
            "label": {"format": self.shipit_label_format},
            "parcels": [
                {
                    "weight": weight,
                    "length": dimensions["length"],
                    "width": dimensions["width"],
                    "height": dimensions["height"],
                }
            ],
        }

        return {"shipments": [shipment]}

    @classmethod
    def _shipit_find_value(cls, value, keys):
        if isinstance(value, dict):
            for key, field_value in value.items():
                if key in keys and field_value not in [None, "", [], {}]:
                    return field_value
            for field_value in value.values():
                found = cls._shipit_find_value(field_value, keys)
                if found not in [None, "", [], {}]:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = cls._shipit_find_value(item, keys)
                if found not in [None, "", [], {}]:
                    return found

        return None

    def _shipit_extract_label_data(self, response):
        label_data = self._shipit_find_value(
            response,
            {
                "label",
                "labelBase64",
                "labelData",
                "labelPDF",
                "labelPdf",
                "labelpdf",
            },
        )
        if isinstance(label_data, dict):
            label_data = label_data.get("data") or label_data.get("content")
        if isinstance(label_data, list):
            label_data = label_data[0] if label_data else False
        return label_data if isinstance(label_data, str) else False

    def _shipit_parse_response(self, response):
        tracking_value = self._shipit_find_value(
            response,
            {
                "tracking",
                "trackingCode",
                "trackingNo",
                "trackingNumber",
                "tracking_number",
                "trackingcode",
            },
        )

        if isinstance(tracking_value, list):
            tracking_codes = ",".join([str(code) for code in tracking_value if code])
        elif tracking_value:
            tracking_codes = str(tracking_value)
        else:
            tracking_codes = False

        return {
            "shipment_id": self._shipit_find_value(
                response,
                {"id", "shipmentId", "shipment_id", "shipmentNo"},
            ),
            "tracking_codes": tracking_codes,
            "tracking_url": self._shipit_find_value(
                response,
                {"trackingUrl", "trackingURL", "tracking_link"},
            ),
            "label_data": self._shipit_extract_label_data(response),
        }

    def _shipit_normalize_attachment_data(self, label_data):
        if not label_data:
            return False

        normalized = label_data
        if normalized.startswith("data:") and "," in normalized:
            normalized = normalized.split(",", 1)[1]

        try:
            base64.b64decode(normalized, validate=True)
            return normalized
        except Exception:
            return base64.b64encode(normalized.encode("utf-8")).decode("utf-8")

    def _shipit_create_label_attachment(self, picking, label_data, tracking_code):
        normalized_data = self._shipit_normalize_attachment_data(label_data)
        if not normalized_data:
            return False

        extension = "zpl" if self.shipit_label_format == "ZPL" else "pdf"
        file_ref = tracking_code or picking.name
        filename = f"{picking.name}_{file_ref}.{extension}"

        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .create(
                {
                    "name": filename,
                    "datas": normalized_data,
                    "type": "binary",
                    "res_model": "stock.picking",
                    "res_id": picking.id,
                }
            )
        )
        picking.shipit_label_attachment_id = attachment.id
        return attachment

    def shipit_send_shipping(self, pickings):
        self.ensure_one()
        shipit_request = ShipitRequest(**self._get_shipit_config())
        result = []

        _logger.info("ShipIT send_shipping for %s pickings", len(pickings))

        for picking in pickings:
            values = {
                "exact_price": 0,
                "tracking_number": False,
            }
            picking.shipit_last_error = False
            picking.shipit_response = False

            payload = self._shipit_build_payload(picking)
            picking.shipit_payload = json.dumps(payload, indent=2)

            try:
                response = shipit_request.create_shipment(payload)
            except ShipitAPIError as error:
                picking.shipit_last_error = str(error)
                raise UserError(
                    _("ShipIT API error for %(name)s:\n%(message)s")
                    % {
                        "name": picking.name,
                        "message": str(error),
                    }
                ) from error

            if isinstance(response, dict | list):
                picking.shipit_response = json.dumps(response, indent=2)
            else:
                picking.shipit_response = str(response)

            parsed = self._shipit_parse_response(response)
            tracking_codes = parsed["tracking_codes"]

            if parsed["shipment_id"]:
                picking.shipit_shipment_id = str(parsed["shipment_id"])
            if tracking_codes:
                picking.shipit_tracking_codes = tracking_codes
                values["tracking_number"] = tracking_codes.split(",")[0]
            if parsed["tracking_url"]:
                picking.shipit_tracking_url = parsed["tracking_url"]
            if parsed["label_data"]:
                self._shipit_create_label_attachment(
                    picking=picking,
                    label_data=parsed["label_data"],
                    tracking_code=values["tracking_number"],
                )

            result.append(values)

        return result

    def shipit_get_tracking_link(self, picking):
        if picking.shipit_tracking_url:
            return picking.shipit_tracking_url
        return False

    def shipit_cancel_shipment(self, pickings):
        self.ensure_one()
        shipit_request = ShipitRequest(**self._get_shipit_config())

        for picking in pickings:
            if not picking.shipit_shipment_id:
                continue
            try:
                shipit_request.cancel_shipment(picking.shipit_shipment_id)
            except ShipitAPIError as error:
                raise UserError(
                    _("ShipIT cancel failed for %(name)s:\n%(message)s")
                    % {
                        "name": picking.name,
                        "message": str(error),
                    }
                ) from error

        return True
