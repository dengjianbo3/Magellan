import httpx
import pytest

from app.services.trading_system import TradingSystem


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = b"{}"

    def json(self):
        return self._payload


def _fake_async_client_factory(response: _FakeResponse):
    class _FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            return response

    return _FakeAsyncClient


@pytest.mark.asyncio
async def test_check_tavily_health_false_when_degraded_and_search_fails(monkeypatch):
    monkeypatch.setenv("WEB_SEARCH_URL", "http://web_search_service:8010")
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        _fake_async_client_factory(_FakeResponse(payload={"status": "degraded"})),
    )

    async def _failing_search(*args, **kwargs):
        raise RuntimeError("search unavailable")

    monkeypatch.setattr("app.services.trading_system.shared_search_web", _failing_search)

    system = TradingSystem()
    assert await system._check_tavily_health() is False


@pytest.mark.asyncio
async def test_check_tavily_health_true_when_health_ok(monkeypatch):
    monkeypatch.setenv("WEB_SEARCH_URL", "http://web_search_service:8010")
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        _fake_async_client_factory(_FakeResponse(payload={"status": "ok"})),
    )

    called = {"search": False}

    async def _search_stub(*args, **kwargs):
        called["search"] = True
        return []

    monkeypatch.setattr("app.services.trading_system.shared_search_web", _search_stub)

    system = TradingSystem()
    assert await system._check_tavily_health() is True
    assert called["search"] is False
