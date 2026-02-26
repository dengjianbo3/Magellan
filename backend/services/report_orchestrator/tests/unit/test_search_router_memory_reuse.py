import pytest

from app.core.memory.interface import MemoryHit
from app.core.roundtable.search_router import SearchRouter


class _FakeMemoryStore:
    async def query_shared_evidence(self, user_id: str, query: str, top_k: int = 3):
        return [
            MemoryHit(
                content="Stored evidence: BTC ETF net inflow recovered this week.",
                score=0.92,
                metadata={"source": "unit_test", "title": "ETF Flow Update", "url": "https://example.com"},
                collection="shared:evidence",
            )
        ]

    async def add_shared_evidence(self, user_id: str, content: str, metadata=None):
        return "fake-id"


@pytest.mark.asyncio
async def test_search_router_reuses_memory_before_external_search():
    router = SearchRouter()
    router._memory_store = _FakeMemoryStore()

    result = await router.search(
        query="BTC ETF flow latest",
        priority="normal",
        user_id="user-test",
    )

    assert result.get("success") is True
    assert result.get("from_memory") is True
    assert result.get("routed_source") == "atomic_memory"
    assert result.get("results")
