import logging

import requests

from odoo import _

_logger = logging.getLogger(__name__)

SHIPIT_API_BASE_URL = {
    "test": "https://apitest.shipit.ax/v1",
    "prod": "https://api.shipit.ax/v1",
}


class ShipitAPIError(Exception):
    def __init__(self, message, status_code=None, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ShipitRequest:
    def __init__(
        self,
        api_key=None,
        prod=False,
        timeout=30,
        base_url=None,
        auth_mode="x_shipit_key",
        create_endpoints=None,
        cancel_endpoint_template=None,
        label_endpoint_template=None,
    ):
        api_env = "prod" if prod else "test"
        self.api_key = api_key or ""
        self.base_url = (base_url or SHIPIT_API_BASE_URL[api_env]).rstrip("/")
        self.auth_mode = auth_mode or "x_shipit_key"
        self.create_endpoints = self._parse_create_endpoints(create_endpoints)
        self.cancel_endpoint_template = (
            cancel_endpoint_template.strip() if cancel_endpoint_template else ""
        )
        self.label_endpoint_template = (
            label_endpoint_template.strip() if label_endpoint_template else ""
        )
        self.timeout = timeout

    def _parse_create_endpoints(self, create_endpoints):
        if not create_endpoints:
            return ["shipment"]

        if isinstance(create_endpoints, str):
            values = [endpoint.strip() for endpoint in create_endpoints.split(",")]
            endpoints = [endpoint.lstrip("/") for endpoint in values if endpoint]
        elif isinstance(create_endpoints, list | tuple):
            endpoints = [
                str(endpoint).strip().lstrip("/")
                for endpoint in create_endpoints
                if endpoint
            ]
        else:
            endpoints = ["shipment"]

        if "shipment" not in endpoints:
            endpoints.append("shipment")

        return endpoints

    def _get_endpoint_url(self, endpoint):
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"

    def _get_headers(self):
        mode = (self.auth_mode or "x_shipit_key").strip()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-SHIPIT-KEY": self.api_key,
        }

        if mode in ["both", "x_api_key"]:
            headers["X-API-Key"] = self.api_key

        if mode in ["both", "bearer"]:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    def _parse_response_content(self, response):
        try:
            return response.json()
        except Exception:
            return response.text

    def _raise_if_api_payload_error(self, content):
        if not isinstance(content, dict):
            return

        has_error = content.get("error")
        status_value = content.get("status")
        success_value = content.get("success")

        is_error_status = status_value in [0, "0", False] or success_value is False
        if not has_error and not is_error_status:
            return

        if isinstance(has_error, dict):
            error_message = has_error.get("message") or ""
            error_code = has_error.get("code")
        else:
            error_message = str(has_error or "")
            error_code = None

        if not error_message:
            error_message = _("ShipIT API returned an error response.")

        if error_code not in [None, ""]:
            error_message = _("[Code %(code)s] %(message)s") % {
                "code": error_code,
                "message": error_message,
            }

        raise ShipitAPIError(
            message=error_message,
            response_body=content,
        )

    def _validate_response(self, response):
        if response.status_code in [200, 201, 202, 204]:
            return True

        content = self._parse_response_content(response)
        msg = _("Error %(status_code)s in ShipIT API request: %(reason)s") % {
            "status_code": response.status_code,
            "reason": response.reason,
        }

        if response.status_code in [401, 403]:
            msg += _("\nCheck ShipIT API key and permissions.")
        elif response.status_code == 404:
            msg += _("\nEndpoint not found.")
        elif response.status_code == 422:
            msg += _("\nRequest validation failed.")
        elif response.status_code >= 500:
            msg += _("\nShipIT API server error.")

        raise ShipitAPIError(
            message=msg,
            status_code=response.status_code,
            response_body=content,
        )

    def _post(self, endpoint, payload=None, params=None):
        headers = self._get_headers()

        _logger.debug("ShipIT POST endpoint=%s payload=%s", endpoint, payload)

        try:
            response = requests.post(
                url=endpoint,
                json=payload,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise ShipitAPIError(
                _("ShipIT API request failed: %(message)s") % {"message": str(error)}
            ) from error

        self._validate_response(response)
        content = self._parse_response_content(response)
        self._raise_if_api_payload_error(content)
        return content

    def _put(self, endpoint, payload=None, params=None):
        headers = self._get_headers()

        _logger.debug("ShipIT PUT endpoint=%s payload=%s", endpoint, payload)

        try:
            response = requests.put(
                url=endpoint,
                json=payload,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise ShipitAPIError(
                _("ShipIT API request failed: %(message)s") % {"message": str(error)}
            ) from error

        self._validate_response(response)
        content = self._parse_response_content(response)
        self._raise_if_api_payload_error(content)
        return content

    def _get(self, endpoint, params=None):
        headers = self._get_headers()
        try:
            response = requests.get(
                url=endpoint,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise ShipitAPIError(
                _("ShipIT API request failed: %(message)s") % {"message": str(error)}
            ) from error

        self._validate_response(response)
        content = self._parse_response_content(response)
        self._raise_if_api_payload_error(content)
        return content

    def _delete(self, endpoint):
        headers = self._get_headers()
        try:
            response = requests.delete(
                url=endpoint,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise ShipitAPIError(
                _("ShipIT API request failed: %(message)s") % {"message": str(error)}
            ) from error
        self._validate_response(response)
        content = self._parse_response_content(response)
        self._raise_if_api_payload_error(content)
        return content

    def create_shipment(self, payload):
        endpoints = self.create_endpoints
        last_error = None

        for endpoint in endpoints:
            endpoint_url = self._get_endpoint_url(endpoint)
            try:
                return self._put(endpoint_url, payload=payload)
            except ShipitAPIError as error:
                error_message = str(error).lower()
                method_not_supported = (
                    "method is not supported" in error_message
                    or "method not allowed" in error_message
                )
                if error.status_code in [404, 405] or method_not_supported:
                    last_error = error
                    continue
                raise

        if last_error:
            raise last_error

        raise ShipitAPIError(_("Unable to create shipment."))

    def cancel_shipment(self, shipment_id):
        if not self.cancel_endpoint_template:
            raise ShipitAPIError(_("ShipIT cancel endpoint is not configured."))

        try:
            endpoint = self.cancel_endpoint_template.format(shipment_id=shipment_id)
        except Exception as error:
            raise ShipitAPIError(
                _("Invalid ShipIT cancel endpoint template: %(message)s")
                % {"message": str(error)}
            ) from error

        endpoint = self._get_endpoint_url(endpoint)
        return self._delete(endpoint)

    def get_label(self, shipment_id):
        if not self.label_endpoint_template:
            raise ShipitAPIError(_("ShipIT label endpoint is not configured."))

        try:
            endpoint = self.label_endpoint_template.format(shipment_id=shipment_id)
        except Exception as error:
            raise ShipitAPIError(
                _("Invalid ShipIT label endpoint template: %(message)s")
                % {"message": str(error)}
            ) from error

        endpoint = self._get_endpoint_url(endpoint)
        return self._get(endpoint)

    def download_document(self, document_url):
        headers = self._get_headers()
        try:
            response = requests.get(
                url=document_url,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise ShipitAPIError(
                _("ShipIT document download failed: %(message)s")
                % {"message": str(error)}
            ) from error

        self._validate_response(response)
        return response.content
