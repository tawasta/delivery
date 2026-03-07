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
    def __init__(self, api_key=None, prod=False, timeout=30):
        api_env = "prod" if prod else "test"
        self.api_key = api_key or ""
        self.base_url = SHIPIT_API_BASE_URL[api_env]
        self.timeout = timeout

    def _get_endpoint_url(self, endpoint):
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"

    def _get_headers(self):
        return {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _parse_response_content(self, response):
        try:
            return response.json()
        except Exception:
            return response.text

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
        return self._parse_response_content(response)

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
        return self._parse_response_content(response)

    def create_shipment(self, payload):
        endpoints = ["shipments", "create-shipment"]
        last_error = None

        for endpoint in endpoints:
            endpoint_url = self._get_endpoint_url(endpoint)
            try:
                return self._post(endpoint_url, payload=payload)
            except ShipitAPIError as error:
                if error.status_code == 404:
                    last_error = error
                    continue
                raise

        if last_error:
            raise last_error

        raise ShipitAPIError(_("Unable to create shipment."))

    def cancel_shipment(self, shipment_id):
        endpoint = self._get_endpoint_url(f"shipments/{shipment_id}")
        return self._delete(endpoint)
