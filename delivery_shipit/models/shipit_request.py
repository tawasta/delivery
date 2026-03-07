SHIPIT_API_BASE_URL = {
    "test": "https://apitest.shipit.ax/v1",
    "prod": "https://api.shipit.ax/v1",
}


class ShipitRequest:
    def __init__(self, api_key=None, prod=False):
        api_env = "prod" if prod else "test"
        self.api_key = api_key or ""
        self.base_url = SHIPIT_API_BASE_URL[api_env]
