from thecodexclient.api import TheCodexAPI

from .endpoint import Endpoint
from .transport import TheCodexTransport

BASE_URL = "https://playorna.com"


class TheCodexClient:

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        transport = TheCodexTransport(self.base_url)
        self._transport = transport

        # API
        self.api = TheCodexAPI(self._transport)

    def request(self, endpoint: Endpoint, **kwargs):
        return self._transport.request(
            endpoint=endpoint,
            **kwargs,
        )

    def close(self):
        self._transport.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
