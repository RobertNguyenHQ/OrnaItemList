import httpx

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"


class WebCodexTransport:

    def __init__(self, base_url: str):
        self.base_url = base_url
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "User-Agent": USER_AGENT,
            },
        )

    def _build_header(self, referer: str | None = None):
        _header = {}
        if referer:
            _header['Referer'] = str

        return _header

    def request(self, path: str, **kwargs):
        headers = self._build_header()

        return self._client.request(
            method="GET",
            url=path,
            headers=headers,
            **kwargs
        )

    def close(self):
        self._client.close()
