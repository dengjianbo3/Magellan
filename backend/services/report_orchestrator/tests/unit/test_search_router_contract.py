import pytest

from app.core.roundtable.search_router import SearchRouter


class _NoopCache:
    async def get(self, query, priority, search_params=None):
        return None

    async def set(self, query, priority, result, search_params=None):
        return True


class _CacheHitOldFormat:
    async def get(self, query, priority, search_params=None):
        return {
            "success": True,
            "results": [
                {
                    "title": "Cached Title",
                    "url": "https://cached.example",
                    "body": "cached body",
                    "date": "2026-02-01",
                }
            ],
        }

    async def set(self, query, priority, result, search_params=None):
        return True


@pytest.mark.asyncio
async def test_search_router_normalizes_provider_results(monkeypatch):
    router = SearchRouter()
    router._cache = _NoopCache()

    async def _fake_ddg(query, **kwargs):
        return {
            "success": True,
            "results": [
                {
                    "title": "T1",
                    "url": "https://a.example",
                    "body": "old body payload",
                    "date": "2026-01-15",
                }
            ],
            "source": "duckduckgo",
        }

    monkeypatch.setattr(router, "_search_with_ddg", _fake_ddg)

    result = await router.search("acme info", priority="normal")

    assert result["success"] is True
    assert result["query"] == "acme info"
    assert result["routed_source"] == "duckduckgo"
    assert result["results"][0]["content"] == "old body payload"
    assert result["results"][0]["published_date"] == "2026-01-15"
    # backward compatibility aliases
    assert result["results"][0]["body"] == "old body payload"
    assert result["results"][0]["date"] == "2026-01-15"


@pytest.mark.asyncio
async def test_search_router_normalizes_cached_results():
    router = SearchRouter()
    router._cache = _CacheHitOldFormat()

    result = await router.search("cached query", priority="normal")

    assert result["success"] is True
    assert result["from_cache"] is True
    assert result["results"][0]["content"] == "cached body"
    assert result["results"][0]["published_date"] == "2026-02-01"


@pytest.mark.asyncio
async def test_search_router_passes_search_context_into_cache():
    router = SearchRouter()

    recorder = {}

    class _RecorderCache:
        async def get(self, query, priority, search_params=None):
            recorder["get"] = {
                "query": query,
                "priority": priority,
                "search_params": search_params,
            }
            return None

        async def set(self, query, priority, result, search_params=None):
            recorder["set"] = {
                "query": query,
                "priority": priority,
                "search_params": search_params,
            }
            return True

    router._cache = _RecorderCache()

    async def _fake_ddg(query, **kwargs):
        return {"success": True, "results": []}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(router, "_search_with_ddg", _fake_ddg)

    try:
        await router.search(
            "acme context",
            priority="normal",
            topic="news",
            time_range="week",
            max_results=3,
            days=7,
        )
    finally:
        monkeypatch.undo()

    assert recorder["get"]["search_params"]["topic"] == "news"
    assert recorder["get"]["search_params"]["time_range"] == "week"
    assert recorder["set"]["search_params"]["days"] == 7
    assert recorder["set"]["search_params"]["max_results"] == 3


@pytest.mark.asyncio
async def test_search_router_dedup_respects_context(monkeypatch):
    router = SearchRouter()
    router._cache = _NoopCache()

    calls = {"ddg": 0}

    class _SimpleDedup:
        def __init__(self):
            self.store = {}

        def find_similar(self, query, session_id, context=None):
            key = (session_id, str(sorted((context or {}).items())))
            return self.store.get(key)

        def add(self, query, session_id, result, context=None):
            key = (session_id, str(sorted((context or {}).items())))
            self.store[key] = result

    router._dedup = _SimpleDedup()

    async def _fake_ddg(query, **kwargs):
        calls["ddg"] += 1
        return {"success": True, "results": [{"title": "X", "url": "", "content": ""}]}

    monkeypatch.setattr(router, "_search_with_ddg", _fake_ddg)

    await router.search("same query", priority="normal", session_id="s1", topic="general")
    await router.search("same query", priority="normal", session_id="s1", topic="general")
    await router.search("same query", priority="normal", session_id="s1", topic="news")

    # first call executes search, second dedup hits, third should not dedup due context mismatch
    assert calls["ddg"] == 2
