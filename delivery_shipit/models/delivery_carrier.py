import base64
import io
import json
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .shipit_request import ShipitAPIError, ShipitRequest

try:
    from pdfminer.high_level import extract_text as extract_pdf_text
except Exception:  # pragma: no cover - optional dependency in runtime image
    extract_pdf_text = None

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"
    _shipit_service_code_aliases = {
        "po2103": "posti.po2103",
        "mh80": "mh.mh80",
    }

    delivery_type = fields.Selection(
        selection_add=[("shipit", "ShipIT")],
        ondelete={"shipit": "set default"},
    )
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
    shipit_use_default_dimensions = fields.Boolean(
        string="Use default dimensions",
        default=False,
        help="Use default shipment dimensions, if packages are not used",
    )
    shipit_default_length_cm = fields.Float(string="Default package length (cm)")
    shipit_default_width_cm = fields.Float(string="Default package width (cm)")
    shipit_default_height_cm = fields.Float(string="Default package height (cm)")
    shipit_require_pickup_point = fields.Boolean(
        string="Require pickup point",
        help="Require pickup point selection before creating shipment.",
        default=False,
    )

    shipit_allow_fragile = fields.Boolean(
        string="Allow fragile",
        help="If shipments can be marked as fragile",
        default=False,
    )

    def _get_shipit_config(self):
        config_parameters = self.env["ir.config_parameter"].sudo()
        return {
            "prod": self.prod_environment,
            "api_key": config_parameters.get_param("shipit.api_key"),
            "timeout": int(config_parameters.get_param("shipit.timeout_seconds", 30)),
        }

    def shipit_upsert_carrier(self, service_vals):
        service_name = service_vals.get("name")
        service_code = service_vals.get("service_id")
        # TODO: Logos might be interesting to use for website
        # service_logo = service_vals.get("raw", {}).get("logo")
        raw = service_vals.get("raw", {})

        carrier = self.search(
            [
                ("shipit_service_code", "=", service_code),
                ("delivery_type", "=", "shipit"),
            ],
            limit=1,
        )

        environment = (
            self.env["ir.config_parameter"].sudo().get_param("shipit.environment")
        )

        vals = {
            "name": service_name,
            "product_id": self.env.ref(
                "delivery_shipit.product_product_delivery_shipit"
            ).id,
            "prod_environment": environment,
        }

        if raw.get("supportedCountries"):
            countries = self.env["res.country"].search(
                [("code", "in", raw["supportedCountries"])]
            )
            if countries:
                vals["country_ids"] = [(6, 0, countries.ids)]

        if raw.get("fragile"):
            vals["shipit_allow_fragile"] = True

        if not carrier:
            vals.update(
                {
                    "delivery_type": "shipit",
                    "shipit_service_code": service_code,
                }
            )
            carrier = self.create(vals)
        else:
            carrier.write(vals)

        return carrier

    @api.model
    def _shipit_normalize_service_ids(self, service_ids):
        if not service_ids:
            return []

        if isinstance(service_ids, str):
            values = [value.strip() for value in service_ids.split(",")]
        elif isinstance(service_ids, list | tuple):
            values = [str(value).strip() for value in service_ids if value]
        else:
            values = [str(service_ids).strip()]

        normalized = []
        seen = set()
        for value in values:
            if not value:
                continue
            code = self._shipit_service_code_aliases.get(value.lower(), value.lower())
            if code not in seen:
                seen.add(code)
                normalized.append(code)
        return normalized

    def _shipit_get_service_codes(self):
        self.ensure_one()
        return self._shipit_normalize_service_ids(self.shipit_service_code)

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

    def _shipit_get_parcels(self, picking):
        parcels = []

        if picking.package_ids:
            for package in picking.package_ids:
                # We have packages, use them
                # TODO: Whan if all lines are not packaged?

                package_type = package.package_type_id
                # TODO: Dimension conversion?
                # Package dimensions are mm by default, but are they always?
                # ShipIT expects cm

                length_mm = package_type.packaging_length
                width_mm = package_type.width
                height_mm = package_type.height

                parcels.append(
                    {
                        # TODO: Configurable package type
                        "type": "PACKAGE",
                        "weight": package.shipping_weight or package.weight,
                        "length": length_mm / 10 if length_mm else 0,
                        "width": width_mm / 10 if width_mm else 0,
                        "height": height_mm / 10 if height_mm else 0,
                        "copies": 1,
                    }
                )
        else:
            # No packages. We'll just create a single parcel
            # with the total weight and optional default dimensions.

            # TODO: picking-spesific manual dimensions
            parcel_vals = {
                "type": "PACKAGE",
                "weight": picking.shipping_weight or picking.weight,
                "copies": 1,
            }

            if self.shipit_use_default_dimensions:
                parcel_vals.update(
                    {
                        "length": self.shipit_default_length_cm,
                        "width": self.shipit_default_width_cm,
                        "height": self.shipit_default_height_cm,
                    }
                )

            parcels.append(parcel_vals)

        return parcels

    def _shipit_get_additional_services(self, picking):
        services = {}
        if picking.shipit_fragile:
            services["fragile"] = True
        return services

    def _shipit_validate_required_fields(self, picking, sender, receiver):
        missing_fields = []
        if not self.shipit_service_code:
            missing_fields.append(_("Carrier ShipIT service ID"))

        required_sender_fields = {
            _("Sender name"): sender.get("name"),
            _("Sender street"): sender.get("address"),
            _("Sender postal code"): sender.get("postcode"),
            _("Sender city"): sender.get("city"),
            _("Sender country code"): sender.get("country"),
            _("Sender email"): sender.get("email"),
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

        if picking.shipping_weight <= 0 and picking.weight <= 0:
            missing_fields.append(_("Shipment weight"))

        if self.shipit_require_pickup_point and not picking.shipit_pickup_point_id:
            missing_fields.append(_("Pickup point ID"))

        if (
            picking.shipit_pickup_point_service_id
            and not picking.shipit_pickup_point_id
        ):
            missing_fields.append(
                _("Pickup point service ID requires pickup point selection")
            )

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

        self._shipit_validate_required_fields(picking, sender, receiver)

        parcels = self._shipit_get_parcels(picking)
        additional_services = self._shipit_get_additional_services(picking)

        payload = {
            "reference": picking.origin or picking.name,
            "sender": sender,
            "receiver": receiver,
            "parcels": parcels,
            "serviceId": self.shipit_service_code,
            "externalId": picking.name,
            "sendOrderConfirmationEmail": False,
            "additionalServices": additional_services,
        }

        config_parameters = self.env["ir.config_parameter"].sudo()
        payload["resellerId"] = int(config_parameters.get_param("shipit.reseller_id"))

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

    @staticmethod
    def _shipit_parse_decimal(value):
        if value in [None, False, ""]:
            return False
        if isinstance(value, int | float):
            return float(value)

        if not isinstance(value, str):
            return False

        normalized = value.replace("\xa0", " ").replace("€", "").strip()
        normalized = re.sub(r"[^0-9,.\- ]", "", normalized).replace(" ", "")
        if not normalized:
            return False

        if "," in normalized and "." in normalized:
            if normalized.rfind(",") > normalized.rfind("."):
                normalized = normalized.replace(".", "").replace(",", ".")
            else:
                normalized = normalized.replace(",", "")
        elif "," in normalized:
            normalized = normalized.replace(",", ".")

        try:
            return float(normalized)
        except Exception:
            return False

    def _shipit_extract_exact_price_from_receipt_text(self, text):
        if not text:
            return False

        patterns = [
            r"Hinta\s*alv\.?\s*0\s*%[^\d]{0,80}([0-9]+[.,][0-9]{2})",
            r"Summa\s*\(veroton\)[^\d]{0,80}([0-9]+[.,][0-9]{2})",
            r"Subtotal[^\d]{0,80}([0-9]+[.,][0-9]{2})",
            r"Amount\s*(?:excl\.?|excluding|without)\s*VAT[^\d]{0,80}([0-9]+[.,][0-9]{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                amount = self._shipit_parse_decimal(match.group(1))
                if amount not in [False, None]:
                    return amount

        row_match = re.search(
            r"\n1\s*\n([0-9]+[.,][0-9]{2})\s*€?\s*\n[0-9]+(?:[.,][0-9]+)?\s*%\s*\n([0-9]+[.,][0-9]{2})\s*€?",
            text,
            flags=re.IGNORECASE,
        )
        if row_match:
            amount = self._shipit_parse_decimal(row_match.group(1))
            if amount not in [False, None]:
                return amount

        return False

    def _shipit_extract_exact_price_from_receipt(self, receipt_url, shipit_request):
        if not receipt_url:
            return False

        try:
            receipt_data = shipit_request.download_document(receipt_url)
        except ShipitAPIError:
            return False

        if not receipt_data:
            return False

        text = ""
        if receipt_data.startswith(b"%PDF") and extract_pdf_text:
            try:
                text = extract_pdf_text(io.BytesIO(receipt_data))
            except Exception:
                text = ""
        if not text:
            text = receipt_data.decode("utf-8", errors="ignore")

        return self._shipit_extract_exact_price_from_receipt_text(text)

    def _shipit_extract_exact_price(self, response_bundle, shipit_request):
        direct_price = self._shipit_find_value(
            response_bundle,
            {
                "price",
                "cost",
                "amountExcludingVat",
                "amountExclVat",
                "subtotal",
                "net",
            },
        )
        parsed_direct_price = self._shipit_parse_decimal(direct_price)
        if parsed_direct_price not in [False, None]:
            return parsed_direct_price

        receipt_url = self._shipit_find_value(
            response_bundle,
            {"receipt", "receiptUrl", "receiptURL", "receipt_document_url"},
        )
        receipt_url = self._shipit_extract_first_url(receipt_url)
        return self._shipit_extract_exact_price_from_receipt(
            receipt_url, shipit_request
        )

    def _shipit_get_latest_known_exact_price(self):
        self.ensure_one()
        recent_pickings = self.env["stock.picking"].search(
            [
                ("carrier_id", "=", self.id),
                ("shipit_shipment_id", "!=", False),
                ("state", "=", "done"),
            ],
            order="id desc",
            limit=10,
        )
        if not recent_pickings:
            return False

        shipit_request = ShipitRequest(**self._get_shipit_config())
        for picking in recent_pickings:
            if picking.carrier_price:
                return float(picking.carrier_price)
            if not picking.shipit_response:
                continue
            try:
                response_bundle = json.loads(picking.shipit_response)
            except Exception:
                continue
            exact_price = self._shipit_extract_exact_price(
                response_bundle, shipit_request
            )
            if exact_price not in [False, None]:
                return exact_price

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
        receipt_url_value = self._shipit_find_value(
            response, {"receipt", "receiptUrl", "receiptURL"}
        )

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
            "receipt_url": self._shipit_extract_first_url(receipt_url_value),
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
        result = []

        _logger.info("ShipIT send_shipping for %s pickings", len(pickings))

        for picking in pickings:
            values = self.shipit_send_picking(picking)
            result.append(values)

        return result

    def shipit_send_picking(self, picking):
        shipit_request = ShipitRequest(**self._get_shipit_config())

        values = {
            "exact_price": 0,
            "tracking_number": False,
        }
        picking.shipit_last_error = False
        if self.debug_logging:
            picking.shipit_payload = False
            picking.shipit_response = False

        payload = self._shipit_build_payload(picking)
        if self.debug_logging:
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
        if parsed["receipt_url"]:
            response_bundle["receipt_document_url"] = parsed["receipt_url"]

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
            and self._shipit_get_fixed_config_values()["shipit_label_endpoint_template"]
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

        exact_price = self._shipit_extract_exact_price(response_bundle, shipit_request)
        if exact_price not in [False, None]:
            values["exact_price"] = exact_price

        if self.debug_logging:
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

        return values

    def shipit_rate_shipment(self, order):
        self.ensure_one()

        price = self.fixed_price or 0.0
        if not price:
            latest_price = self._shipit_get_latest_known_exact_price()
            if latest_price not in [False, None]:
                price = latest_price
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
