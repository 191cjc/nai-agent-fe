"""All backend tests must stay offline, including tests added later."""

import httpx
import pytest


@pytest.fixture(autouse=True)
def no_live_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*_args, **_kwargs):
        raise AssertionError("Live HTTP requests are forbidden in automated tests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", reject)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", reject)
