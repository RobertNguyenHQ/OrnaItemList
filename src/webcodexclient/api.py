from .params import DataParams
from .transport import WebCodexTransport

DEFAULT_LANGUAGE = 'en'
ENDPOINT_DATA = '/codex/data/'


class WebCodexAPI:

    def __init__(self, transport: WebCodexTransport):
        self._transport = transport

        self.lang = DEFAULT_LANGUAGE

    def data(self, params: DataParams | None = None):
        _params: DataParams = {"lang": self.lang}
        if params:
            _params.update(params)

        return self._transport.request(
            path=ENDPOINT_DATA,
            params=_params,
        )
