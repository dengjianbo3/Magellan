import httpx
import pytest

from app.core.roundtable.serper_tool import SerperSearchTool


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _fake_async_client_factory(payload):
    class _FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers, json):
            return _FakeResponse(payload)

    return _FakeAsyncClient


@pytest.mark.asyncio
async def test_serper_tool_returns_normalized_result_contract(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    payload = {
        "organic": [
            {
                "title": "T1",
                "link": "https://example.com/t1",
                "snippet": "snippet body",
                "date": "2026-02-10",
            }
        ]
    }
    monkeypatch.setattr(httpx, "AsyncClient", _fake_async_client_factory(payload))

    tool = SerperSearchTool()
    result = await tool.execute("acme", search_type="text", max_results=1)

    assert result["success"] is True
    assert result["results"][0]["content"] == "snippet body"
    assert result["results"][0]["published_date"] == "2026-02-10"
    assert result["results"][0]["body"] == "snippet body"
    assert result["results"][0]["date"] == "2026-02-10"
