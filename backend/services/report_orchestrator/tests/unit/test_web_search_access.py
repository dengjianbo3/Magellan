import pytest

from app.services import web_search_access


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _fake_async_client_factory(payload, recorder):
    class _FakeAsyncClient:
        def __init__(self, timeout):
            recorder["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            recorder["url"] = url
            recorder["json"] = json
            return _FakeResponse(payload)

    return _FakeAsyncClient


@pytest.mark.asyncio
async def test_search_web_builds_payload_and_normalizes_results(monkeypatch):
    recorder = {}
    payload = {
        "results": [
            {"title": "R1", "url": "https://a", "content": "A", "score": 0.9, "published_date": "2026-01-01"},
            {"title": "R2", "url": "https://b", "content": "B"},
        ]
    }
    monkeypatch.setattr(
        web_search_access.httpx,
        "AsyncClient",
        _fake_async_client_factory(payload, recorder),
    )

    result = await web_search_access.search_web(
        "http://web_search_service:8010",
        query="robotics market",
        max_results=8,
        topic="news",
        days=7,
        timeout=12.0,
    )

    assert recorder["url"] == "http://web_search_service:8010/search"
    assert recorder["json"]["query"] == "robotics market"
    assert recorder["json"]["max_results"] == 8
    assert recorder["json"]["topic"] == "news"
    assert recorder["json"]["days"] == 7
    assert len(result) == 2
    assert result[0]["score"] == 0.9
    assert result[1]["score"] == 0.0
