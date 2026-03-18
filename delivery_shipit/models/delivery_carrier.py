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
            ("x_shipit_key", "X-SHIPIT-KEY"),
            ("both", "X-SHIPIT-KEY + Bearer + X-API-Key"),
            ("bearer", "Bearer (legacy)"),
            ("x_api_key", "X-API-Key (legacy)"),
        ],
        default="x_shipit_key",
        required=True,
    )
    shipit_create_endpoints = fields.Char(
        string="ShipIT create endpoints",
        default="shipment",
        help="Comma-separated endpoint paths used for create shipment PUT call.",
    )
    shipit_cancel_endpoint_template = fields.Char(
        string="ShipIT cancel endpoint template",
        help="Optional endpoint template for cancellation call.",
    )
    shipit_label_endpoint_template = fields.Char(
        string="ShipIT label endpoint template",
        help="Optional endpoint template for legacy label fetch fallback.",
    )
    shipit_timeout_seconds = fields.Integer(
        string="ShipIT timeout (seconds)",
        default=30,
    )
    shipit_store_debug_payloads = fields.Boolean(
        string="Store ShipIT debug payloads",
        help="Store request/response payloads to picking debug fields.",
        default=False,
    )
    shipit_reseller_id = fields.Char(string="ShipIT reseller ID")
    shipit_service_code = fields.Char(
        string="ShipIT service ID",
        help="ShipIT v1 serviceId, e.g. posti.po2103",
    )
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
            "label_endpoint_template": self.shipit_label_endpoint_template,
            "timeout": max(1, self.shipit_timeout_seconds or 30),
        }

    def _shipit_get_sender_partner(self, picking):
        warehouse_partner = picking.picking_type_id.warehouse_id.partner_id
        return warehouse_partner or picking.company_id.partner_id

    def _shipit_get_email(self, partner):
        if not partner:
            return ""
        commercial_partner = partner.commercial_partner_id
        partner_delivery_email = getattr(partner, "email_delivery", False)
        commercial_delivery_email = getattr(commercial_partner, "email_delivery", False)
        return (
            partner_delivery_email
            or partner.email
            or commercial_delivery_email
            or commercial_partner.email
            or ""
        )

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
                "email": "",
                "phone": "",
                "address": "",
                "city": "",
                "postcode": "",
                "country": "",
                "address2": "",
                "state": "",
                "isCompany": False,
                "contactPerson": "",
                "vatNumber": "",
                "eoriNumber": "",
            }

        commercial_partner = partner.commercial_partner_id
        country = partner.country_id.code or commercial_partner.country_id.code or ""
        state = (
            partner.state_id.code
            or partner.state_id.name
            or commercial_partner.state_id.code
            or commercial_partner.state_id.name
            or ""
        )
        return {
            "name": partner.commercial_company_name
            or partner.name
            or commercial_partner.name
            or "",
            "email": self._shipit_get_email(partner),
            "phone": self._shipit_get_phone(partner),
            "address": partner.street or commercial_partner.street or "",
            "city": partner.city or commercial_partner.city or "",
            "postcode": partner.zip or commercial_partner.zip or "",
            "country": country,
            "address2": partner.street2 or commercial_partner.street2 or "",
            "state": state,
            "isCompany": bool(
                partner.is_company
                or commercial_partner.is_company
                or partner.commercial_company_name
            ),
            "contactPerson": partner.name or commercial_partner.name or "",
            "vatNumber": partner.vat or commercial_partner.vat or "",
            "eoriNumber": "",
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

    def _shipit_validate_required_fields(self, picking, sender, receiver, weight):
        missing_fields = []

        if not self.shipit_api_key:
            missing_fields.append(_("Carrier ShipIT API key"))
        if not self.shipit_reseller_id:
            missing_fields.append(_("Carrier ShipIT reseller ID"))
        if not self.shipit_service_code:
            missing_fields.append(_("Carrier ShipIT service ID"))

        required_sender_fields = {
            _("Sender name"): sender.get("name"),
            _("Sender street"): sender.get("address"),
            _("Sender postal code"): sender.get("postcode"),
            _("Sender city"): sender.get("city"),
            _("Sender country code"): sender.get("country"),
        }
        for label, value in required_sender_fields.items():
            if not value:
                missing_fields.append(label)

        required_recipient_fields = {
            _("Recipient name"): receiver.get("name"),
            _("Recipient street"): receiver.get("address"),
            _("Recipient postal code"): receiver.get("postcode"),
            _("Recipient city"): receiver.get("city"),
            _("Recipient country code"): receiver.get("country"),
            _("Recipient email"): receiver.get("email"),
            _("Recipient phone"): receiver.get("phone"),
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
        receiver = self._shipit_map_address(recipient_partner)
        weight = self._shipit_get_picking_weight(picking)
        dimensions = self._shipit_get_package_dimensions(picking)

        self._shipit_validate_required_fields(picking, sender, receiver, weight)

        payload = {
            "reference": picking.origin or picking.name,
            "sender": sender,
            "receiver": receiver,
            "parcels": [
                {
                    "type": "PACKAGE",
                    "weight": weight,
                    "length": dimensions["length"],
                    "width": dimensions["width"],
                    "height": dimensions["height"],
                    "copies": 1,
                }
            ],
            "serviceId": self.shipit_service_code,
            "externalId": picking.name,
            "sendOrderConfirmationEmail": False,
        }

        reseller_id = (self.shipit_reseller_id or "").strip()
        try:
            payload["resellerId"] = int(reseller_id)
        except ValueError:
            payload["resellerId"] = reseller_id

        if picking.shipit_pickup_point_id:
            payload["pickupId"] = picking.shipit_pickup_point_id
            if picking.shipit_pickup_point_service_id:
                payload["serviceId"] = picking.shipit_pickup_point_service_id

        return payload

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

    def _shipit_extract_first_url(self, value):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item:
                    return item
            return False
        if isinstance(value, str):
            return value
        return False

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

        tracking_url_value = self._shipit_find_value(
            response,
            {"trackingUrl", "trackingURL", "tracking_link", "trackingUrls"},
        )
        label_url_value = self._shipit_find_value(response, {"freightDoc"})

        return {
            "shipment_id": self._shipit_find_value(
                response,
                {
                    "shipmentNumber",
                    "shipmentId",
                    "shipment_id",
                    "shipmentNo",
                    "id",
                    "orderId",
                },
            ),
            "tracking_codes": tracking_codes,
            "tracking_url": self._shipit_extract_first_url(tracking_url_value),
            "label_data": self._shipit_extract_label_data(response),
            "label_url": self._shipit_extract_first_url(label_url_value),
        }

    def _shipit_normalize_attachment_data(self, label_data):
        if not label_data:
            return False

        if isinstance(label_data, bytes):
            return base64.b64encode(label_data).decode("utf-8")

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
            if self.shipit_store_debug_payloads:
                picking.shipit_payload = False
                picking.shipit_response = False

            payload = self._shipit_build_payload(picking)
            if self.shipit_store_debug_payloads:
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

            response_bundle = {"create_shipment": response}
            parsed = self._shipit_parse_response(response)
            tracking_codes = parsed["tracking_codes"]
            label_data = parsed["label_data"]

            if parsed["shipment_id"]:
                picking.shipit_shipment_id = str(parsed["shipment_id"])
            if tracking_codes:
                picking.shipit_tracking_codes = tracking_codes
                values["tracking_number"] = tracking_codes.split(",")[0]
            if parsed["tracking_url"]:
                picking.shipit_tracking_url = parsed["tracking_url"]

            if not label_data and parsed["label_url"]:
                try:
                    label_data = shipit_request.download_document(parsed["label_url"])
                    response_bundle["label_document_url"] = parsed["label_url"]
                except ShipitAPIError as error:
                    _logger.info(
                        "ShipIT label document download skipped for %s: %s",
                        picking.name,
                        str(error),
                    )

            if (
                not label_data
                and parsed["shipment_id"]
                and self.shipit_label_endpoint_template
            ):
                try:
                    label_response = shipit_request.get_label(parsed["shipment_id"])
                    response_bundle["label"] = label_response
                    label_data = self._shipit_extract_label_data(label_response)
                except ShipitAPIError as error:
                    _logger.info(
                        "ShipIT label fetch fallback skipped for %s: %s",
                        picking.name,
                        str(error),
                    )

            if self.shipit_store_debug_payloads:
                if isinstance(response_bundle, dict | list):
                    picking.shipit_response = json.dumps(response_bundle, indent=2)
                else:
                    picking.shipit_response = str(response_bundle)

            if label_data:
                self._shipit_create_label_attachment(
                    picking=picking,
                    label_data=label_data,
                    tracking_code=values["tracking_number"],
                )

            result.append(values)

        return result

    def shipit_rate_shipment(self, order):
        self.ensure_one()

        price = self.fixed_price or 0.0
        return {
            "success": True,
            "price": price,
            "error_message": False,
            "warning_message": False,
        }

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
