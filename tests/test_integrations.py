import httpx
import pytest
from retail_ai.integrations import ApiClient, ApiError


def make(handler, **kw):
    return ApiClient("https://api.test", transport=httpx.MockTransport(handler), sleep=lambda s: None, **kw)


def test_adds_bearer_token():
    seen = {}

    def handler(req):
        seen["auth"] = req.headers["Authorization"]
        return httpx.Response(200, json={"ok": True})

    assert make(handler, token_provider=lambda: "tok").get("/orders/1") == {"ok": True}
    assert seen["auth"] == "Bearer tok"


def test_retries_then_succeeds():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(503) if len(calls) < 3 else httpx.Response(200, json={"n": 3})

    assert make(handler).get("/x") == {"n": 3} and len(calls) == 3


def test_gives_up_after_max_retries():
    with pytest.raises(ApiError) as e:
        make(lambda req: httpx.Response(500, text="down"), max_retries=2).get("/x")
    assert e.value.status_code == 500


def test_client_error_not_retried():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(404, text="nope")

    with pytest.raises(ApiError):
        make(handler).get("/x")
    assert len(calls) == 1


def test_retries_transport_errors():
    calls = []

    def handler(req):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, json={})

    make(handler).get("/x")
    assert len(calls) == 2
