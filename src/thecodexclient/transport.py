import hashlib
import hmac
import time

import httpx

from .endpoint import Endpoint

CODEX_CLIENT = "android/1.0.5"
CODEX_SECRET = b"ornasharedcodex"
USER_AGENT = "okhttp/4.12.0"


class TheCodexTransport:

    def __init__(self, base_url: str):
        self.base_url = base_url
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "User-Agent": "okhttp/4.12.0",
            },
        )

    def _build_header(self, path: str):
        client = CODEX_CLIENT
        secret = CODEX_SECRET
        timestamp = str(int(time.time()))
        message = f"{timestamp}\n{path}\n{client}".encode()
        signature = hmac.new(
            secret,
            message,
            hashlib.sha256,
        ).hexdigest()

        return {
            "X-Codex-Client": client,
            "X-Codex-Timestamp": timestamp,
            "X-Codex-Signature": signature,
        }

    def request(self, endpoint: Endpoint, **kwargs):
        headers = self._build_header(endpoint.path)
        request_headers = kwargs.pop("headers", None)
        if request_headers:
            headers.update(request_headers)

        return self._client.request(
            method=endpoint.method,
            url=endpoint.path,
            headers=headers,
            **kwargs
        )

    def close(self):
        self._client.close()
