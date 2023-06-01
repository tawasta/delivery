import logging

import requests

from odoo import _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

GLS_FINLAND_API_URL = {
    "test": "https://api.gls.fi/api/shipping/",
    "prod": "https://api.gls.fi/api/shipping/",
}


class GlsFinlandRequest:
    def __init__(
        self,
        api_key=None,
        prod=False,
    ):
        api_env = "prod" if prod else "test"
        self.url = GLS_FINLAND_API_URL[api_env]
        self.api_key = api_key

    # region Request helpers
    def _validate_response(self, response):
        status_code = response.status_code

        _logger.debug("Response headers: {}".format(response.headers))
        _logger.debug("Response status code: {}".format(status_code))
        _logger.debug("Response content: {}".format(response.text))
        # Go through most common error codes
        # 200 = OK
        # 201 = Created (e.g. POST requests)
        # 204 = No content (e.g. DELETE requests, if no error occurs)
        if status_code not in [200, 201, 204]:

            msg = _("Error {} in request: {}\n").format(status_code, response.reason)

            # Go through some common errors
            if status_code == 400:
                msg += _("\nInvalid client request")
            if status_code == 401:
                msg += _("\nYou should check your API Key")
            elif status_code == 403:
                msg += _("\nYou should check your API Key")
            elif status_code == 404:
                msg += _("\nCheck your API URL or try again later")
            elif status_code == 500:
                msg += _(
                    "\nThe API server can not be reached. You should try again later"
                )

            raise ValidationError(msg)

        return True

    def _get_endpoint_url(self, endpoint):
        """
        Return endpoint URL
        """
        # Remove extra slash, if given
        endpoint = endpoint.lstrip("/")

        # Add ending slash, if missing
        if endpoint[-1:] != "/":
            endpoint = "{}/".format(endpoint)
        return "{}{}".format(self.url, endpoint)

    def _get_headers(self):
        headers = {
            "X-API-Key": self.api_key,
            "Content-type": "application/json",
            "Accept": "application/json",
        }

        return headers

    def _get(self, endpoint, **kwargs):
        """
        Authenticate and make a get request
        """
        _logger.debug(_("Making a get request to '%s'") % endpoint)
        response = requests.get(endpoint, **kwargs)

        self._validate_response(response)

        return response.json()

    def _post(self, endpoint, values=None, params=None, **kwargs):
        """
        Authenticate and make a post request
        """
        headers = self._get_headers()

        _logger.debug(_("Making a post request to '{}'".format(endpoint)))
        _logger.debug(_("Using headers {}".format(headers)))
        _logger.debug(_("Using values {}".format(values)))

        response = requests.post(
            url=endpoint, json=values, params=params, headers=headers, **kwargs
        )

        self._validate_response(response)

        return response.json()

    def _delete(self, endpoint, **kwargs):
        """
        Authenticate and make a delete request
        """
        headers = self._get_headers()

        _logger.debug(_("Making a delete request to '{}'").format(endpoint))

        response = requests.delete(url=endpoint, headers=headers, **kwargs)

        self._validate_response(response)

        return response

    # endregion

    # region API Calls
    def _send_shipping(self, values):
        """
        Post a new shipment
        """

        endpoint = self._get_endpoint_url("create-shipment")
        params = {}
        _logger.debug("_send_shipping: {}".format(values))
        return self._post(endpoint, values, params)

    def _cancel_shipment(self, shipment_id):
        """
        Delete a shipment
        """
        endpoint = self._get_endpoint_url("cancel-shipment")

        if endpoint:
            # TODO: not implemented on the API
            raise ValidationError(
                _("Cancelling shipments is not supported by GLS Finland API.\n")
                + _("You will need to cancel the shipment from website portal")
            )

        return self._delete(endpoint)

    # endregion
