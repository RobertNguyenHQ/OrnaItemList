from . import endpoint
from .transport import TheCodexTransport

DEFAULT_LANGUAGE = 'en'


class TheCodexAPI:

    def __init__(self, transport: TheCodexTransport):
        self._transport = transport

    def database(self, *, lang: str | None = None, etag: str | None = None):
        _headers = {}
        _params = {"lang": DEFAULT_LANGUAGE}

        if lang:
            _params["lang"] = lang

        if etag:
            _headers["If-None-Match"] = etag

        return self._transport.request(
            endpoint=endpoint.DATABASE,
            params=_params,
            headers=_headers
        )

    def live(self, *, lang: str | None = None):
        _params = {"lang": DEFAULT_LANGUAGE}

        if lang:
            _params["lang"] = lang

        return self._transport.request(
            endpoint=endpoint.LIVE,
            params=_params,
        )
