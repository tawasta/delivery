import requests
import logging
import json

from odoo import _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

NSHIFT_API_URL = {
    "test": "https://api.unifaun.com/rs-extapi/v1",
    "prod": "https://api.unifaun.com/rs-extapi/v1",
}


class NshiftRequest:
    def __init__(
        self,
        username=None,
        password=None,
        prod=False,
        customer_number=None,
        partner_code=None,
        service_code=None,
        customer_id=None,
    ):
        api_env = "prod" if prod else "test"
        self.url = NSHIFT_API_URL[api_env]
        self.username = username
        self.password = password
        self.customer_number = customer_number
        self.partner_code = partner_code
        self.service_code = service_code
        self.customer_id = customer_id

    # region Request helpers
    def _validate_response(self, response):
        status_code = response.status_code

        _logger.debug("Response status code: {}".format(status_code))
        _logger.debug("Response content: {}".format(response.text))

        # Go through most common error codes
        # 200 = OK
        # 201 = Created (e.g. POST requests)
        # 204 = No content (e.g. DELETE requests, if no error occurs)
        if status_code not in [200, 201, 204]:

            msg = _("Error {} in request: {}\n").format(status_code, response.reason)

            # Go through some common errors
            if status_code == 401:
                msg += _("\nYou should check your username and password")
            elif status_code == 403:
                msg += _("\nYou should check your API permissions")
            elif status_code == 404:
                msg += _("\nCheck your API URL or try again later")
            elif status_code == 500:
                msg += _(
                    "\nThe API server can not be reached. You should try again later"
                )

            if response.text:
                res_json = json.loads(response.text)

                for res in res_json:
                    field = res.get("field", "")
                    if not field:
                        field = "Error"

                    error = "{}: {}".format(field, res.get("message", ""))
                    msg += "\n{}".format(error)

            raise ValidationError(msg)

        return True

    def _get_endpoint_url(self, endpoint):
        """
        Return endpoint URL
        """
        return "{}/{}".format(self.url, endpoint)

    def _get_headers(self):
        auth_token = "{}-{}".format(self.username, self.password)

        headers = {
            "Authorization": "Bearer " + auth_token,
            "Content-type": "application/json",
            "Accept": "application/json",
        }

        return headers

    def _auth(self):
        """
        Authenticate against Unifaun REST API
        """
        session = requests.Session()
        session.auth = (self.username, self.password)

        return session

    def _get(self, endpoint, **kwargs):
        """
        Authenticate and make a get request
        """
        session = self._auth()

        _logger.debug(_("Making a get request to '%s'") % endpoint)
        response = session.get(endpoint, **kwargs)

        self._validate_response(response)

        return json.loads(response.text)

    def _post(self, endpoint, values=None, params=None, **kwargs):
        """
        Authenticate and make a post request
        """
        headers = self._get_headers()

        _logger.debug(
            _("Making a post request to '%s' using values %s") % (endpoint, values)
        )
        response = requests.post(
            url=endpoint, json=values, params=params, headers=headers, **kwargs
        )

        self._validate_response(response)

        return json.loads(response.text)

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
    def api_get_zipcode_info(self, zip, countryCode):
        params = {
            "zip": zip,
            "countryCode": countryCode,
        }

        endpoint = self._get_endpoint_url("addresses/zipcodes")

        return self._get(endpoint, params=params)

    def _get_carriers(self):
        """
        Get all carriers and their services
        """
        endpoint = self._get_endpoint_url("meta/lists/partners")

        return self._get(endpoint)

    def _send_shipping(self, values):
        """
        Post a new shipment
        """

        endpoint = self._get_endpoint_url("shipments")

        # Return PDF in response
        params = {"returnFile": True}

        return self._post(endpoint, values, params)

    def _cancel_shipment(self, shipment_id):
        """
        Delete a shipment
        """
        endpoint = self._get_endpoint_url("shipments/{}".format(shipment_id))

        return self._delete(endpoint)

    # endregion
