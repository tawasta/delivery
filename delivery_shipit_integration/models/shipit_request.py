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
    ):
        api_env = "prod" if prod else "test"
        self.api_key = api_key or ""
        self.base_url = SHIPIT_API_BASE_URL[api_env]
        self.auth_mode = "x_shipit_key"
        self.create_endpoints = ["shipment"]
        self.cancel_endpoint_template = "shipments/{shipment_id}"
        self.label_endpoint_template = "shipments/{shipment_id}/label"
        self.timeout = timeout

    def _get_endpoint_url(self, endpoint):
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"

    def _get_headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-SHIPIT-KEY": self.api_key,
        }

        if self.auth_mode == "x_api_key":
            headers["X-API-Key"] = self.api_key

        if self.auth_mode == "bearer":
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
            error_message = _("Shipit API returned an error response.")

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
        msg = _("Error %(status_code)s in Shipit API request: %(reason)s") % {
            "status_code": response.status_code,
            "reason": response.reason,
        }

        if response.status_code in [401, 403]:
            msg += _("\nCheck Shipit API key and permissions.")
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

        _logger.debug("Shipit POST endpoint=%s payload=%s", endpoint, payload)

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
                _("Shipit API request failed: %(message)s") % {"message": str(error)}
            ) from error

        self._validate_response(response)
        content = self._parse_response_content(response)
        self._raise_if_api_payload_error(content)
        return content

    def _put(self, endpoint, payload=None, params=None):
        headers = self._get_headers()

        _logger.debug("Shipit PUT endpoint=%s payload=%s", endpoint, payload)

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
                _("Shipit API request failed: %(message)s") % {"message": str(error)}
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
                _("Shipit API request failed: %(message)s") % {"message": str(error)}
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
                _("Shipit API request failed: %(message)s") % {"message": str(error)}
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
        _logger.warning(
            "Shipit cancel is not implemented. Shipment ID: %s", shipment_id
        )

        return

    def get_label(self, shipment_id):
        if not self.label_endpoint_template:
            raise ShipitAPIError(_("Shipit label endpoint is not configured."))

        try:
            endpoint = self.label_endpoint_template.format(shipment_id=shipment_id)
        except Exception as error:
            raise ShipitAPIError(
                _("Invalid Shipit label endpoint template: %(message)s")
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
                _("Shipit document download failed: %(message)s")
                % {"message": str(error)}
            ) from error

        self._validate_response(response)
        return response.content

    def _normalize_service_ids(self, service_ids):
        if not service_ids:
            return []

        if isinstance(service_ids, str):
            values = [service_id.strip() for service_id in service_ids.split(",")]
            return [service_id for service_id in values if service_id]

        if isinstance(service_ids, list | tuple):
            return [str(service_id).strip() for service_id in service_ids if service_id]

        return [str(service_ids).strip()]

    @staticmethod
    def _normalize_service_point(point):
        if not isinstance(point, dict):
            return {}

        return {
            "id": point.get("id"),
            "name": point.get("name"),
            "address": point.get("address1"),
            "zipcode": point.get("zipcode"),
            "city": point.get("city"),
            "country_code": point.get("countryCode"),
            "service_id": point.get("serviceId"),
            "carrier": point.get("carrier"),
            "distance_meters": point.get("distanceInMeters"),
            "distance_kilometers": point.get("distanceInKilometers"),
            "latitude": point.get("latitude"),
            "longitude": point.get("longitude"),
            "metadata": point.get("metadata"),
            "raw": point,
        }

    def list_methods(self):
        """
        List all available shipping methods
        """
        endpoint = self._get_endpoint_url("list-methods")
        content = self._get(endpoint)

        return content

    def carrier_contracts(self):
        """
        List all available carrier contracts
        """
        endpoint = self._get_endpoint_url("carrier-contracts")
        content = self._get(endpoint)

        return content

    def search_service_points(
        self,
        postcode,
        country_code,
        service_ids,
        point_type="service_point",
        limit=None,
        latitude=None,
        longitude=None,
        exclude_outdoor_lockers=False,
    ):
        service_ids = self._normalize_service_ids(service_ids)
        if not service_ids:
            raise ShipitAPIError(_("Shipit service point search requires service IDs."))

        payload = {
            "postcode": str(postcode or "").strip(),
            "country": str(country_code or "").strip(),
            "serviceId": service_ids,
            "type": point_type or "service_point",
        }

        if not payload["postcode"] or not payload["country"]:
            raise ShipitAPIError(
                _("Shipit service point search requires postcode and country.")
            )

        if limit:
            payload["limit"] = int(limit)

        if latitude not in [None, ""] and longitude not in [None, ""]:
            payload["latitude"] = float(latitude)
            payload["longitude"] = float(longitude)

        if exclude_outdoor_lockers:
            payload["excludeOutdoorLockers"] = True

        endpoint = self._get_endpoint_url("agents")
        content = self._post(endpoint, payload=payload)

        if not isinstance(content, dict):
            return []

        locations = content.get("locations")
        if not isinstance(locations, list):
            return []

        return [self._normalize_service_point(point) for point in locations if point]
