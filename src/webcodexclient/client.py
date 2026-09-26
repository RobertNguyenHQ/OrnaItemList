from .api import WebCodexAPI
from .transport import WebCodexTransport

BASE_URL = "https://playorna.com"


class WebCodexClient:

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        transport = WebCodexTransport(self.base_url)
        self._transport = transport

        self.api = WebCodexAPI(self._transport)

    def close(self):
        self._transport.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
