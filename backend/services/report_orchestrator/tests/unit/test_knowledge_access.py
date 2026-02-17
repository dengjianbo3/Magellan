import pytest

from app.services import knowledge_access


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

        async def post(self, url, json, headers=None):
            recorder["url"] = url
            recorder["json"] = json
            recorder["headers"] = headers
            return _FakeResponse(payload)

    return _FakeAsyncClient


@pytest.mark.asyncio
async def test_search_knowledge_base_unifies_payload_and_result(monkeypatch):
    recorder = {}
    payload = {
        "query": "robotics",
        "results": [
            {"text": "A", "metadata": {"title": "DocA"}, "score": 0.9},
            {"content": "B", "metadata": {}, "source": "DocB", "score": 0.7},
        ],
    }
    monkeypatch.setattr(
        knowledge_access.httpx,
        "AsyncClient",
        _fake_async_client_factory(payload, recorder),
    )

    result = await knowledge_access.search_knowledge_base(
        "http://internal_knowledge_service:8009",
        query="robotics",
        top_k=5,
        use_reranking=False,
        timeout=12.0,
    )

    assert recorder["url"] == "http://internal_knowledge_service:8009/search"
    assert recorder["json"]["limit"] == 5
    assert recorder["json"]["top_k"] == 5
    assert recorder["json"]["use_reranking"] is False
    assert recorder["headers"] is None
    assert result["count"] == 2
    assert result["results"][0]["content"] == "A"
    assert result["results"][0]["source"] == "DocA"
    assert result["results"][1]["source"] == "DocB"


@pytest.mark.asyncio
async def test_search_knowledge_base_forwards_auth_token_from_context(monkeypatch):
    recorder = {}
    payload = {"query": "q", "results": []}
    monkeypatch.setattr(
        knowledge_access.httpx,
        "AsyncClient",
        _fake_async_client_factory(payload, recorder),
    )
    monkeypatch.setattr(knowledge_access, "get_current_access_token", lambda: "tok-123")

    await knowledge_access.search_knowledge_base(
        "http://internal_knowledge_service:8009",
        query="q",
    )

    assert recorder["headers"] == {"Authorization": "Bearer tok-123"}
