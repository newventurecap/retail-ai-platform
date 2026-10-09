"""Base client for business APIs: auth, retries, timeouts, logging."""

import logging
import time
from collections.abc import Callable

import httpx
from retail_ai.observability import traced_span

log = logging.getLogger(__name__)
_RETRY_STATUS = {429, 500, 502, 503, 504}


class ApiError(Exception):
    def __init__(self, status_code: int, body: str):
        super().__init__(f"API error {status_code}: {body[:200]}")
        self.status_code = status_code


class ApiClient:
    def __init__(
        self,
        base_url: str,
        *,
        token_provider: Callable[[], str] | None = None,
        max_retries: int = 3,
        backoff: float = 0.5,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._http = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)
        self._token_provider = token_provider
        self._max_retries = max_retries
        self._backoff = backoff
        self._sleep = sleep

    def request(self, method: str, path: str, **kwargs) -> dict:
        headers = kwargs.pop("headers", {})
        if self._token_provider:
            headers["Authorization"] = f"Bearer {self._token_provider()}"
        with traced_span("api.request", **{"http.method": method, "http.path": path}):
            for attempt in range(self._max_retries + 1):
                try:
                    resp = self._http.request(method, path, headers=headers, **kwargs)
                except httpx.TransportError:
                    if attempt == self._max_retries:
                        raise
                    log.warning("transport error, retrying", extra={"path": path, "attempt": attempt})
                else:
                    if resp.status_code not in _RETRY_STATUS or attempt == self._max_retries:
                        break
                    log.warning(
                        "retryable status",
                        extra={"path": path, "status": resp.status_code, "attempt": attempt},
                    )
                self._sleep(self._backoff * 2**attempt)
        log.info("api call", extra={"method": method, "path": path, "status": resp.status_code})
        if resp.status_code >= 400:
            raise ApiError(resp.status_code, resp.text)
        return resp.json() if resp.content else {}

    def get(self, path: str, **kw) -> dict:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> dict:
        return self.request("POST", path, **kw)
