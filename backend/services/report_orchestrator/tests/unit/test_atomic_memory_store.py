import pytest

from app.core.memory.noop_store import NoopMemoryStore
from app.core.memory.interface import format_memory_hits


@pytest.mark.asyncio
async def test_noop_memory_store_agent_roundtrip():
    store = NoopMemoryStore()
    user_id = "u-1"
    agent_id = "market-analyst"

    await store.add_agent_memory(
        user_id=user_id,
        agent_id=agent_id,
        content="BTC funding rate turned negative while OI dropped sharply.",
        metadata={"source": "test"},
        collection="episodic",
    )

    hits = await store.query_agent_memory(
        user_id=user_id,
        agent_id=agent_id,
        query="BTC funding rate negative",
        top_k=3,
        collection="episodic",
    )
    assert hits
    assert "funding rate" in hits[0].content.lower()
    rendered = format_memory_hits(hits)
    assert "Memory 1" in rendered


@pytest.mark.asyncio
async def test_noop_memory_store_scope_isolated():
    store = NoopMemoryStore()
    await store.add_agent_memory(
        user_id="user-a",
        agent_id="leader",
        content="User A memory",
        metadata={},
        collection="episodic",
    )
    await store.add_agent_memory(
        user_id="user-b",
        agent_id="leader",
        content="User B memory",
        metadata={},
        collection="episodic",
    )

    hits_a = await store.query_agent_memory(
        user_id="user-a",
        agent_id="leader",
        query="User A",
        top_k=5,
        collection="episodic",
    )
    hits_b = await store.query_agent_memory(
        user_id="user-b",
        agent_id="leader",
        query="User B",
        top_k=5,
        collection="episodic",
    )
    assert hits_a and "user a" in hits_a[0].content.lower()
    assert hits_b and "user b" in hits_b[0].content.lower()


@pytest.mark.asyncio
async def test_noop_memory_store_shared_evidence_roundtrip():
    store = NoopMemoryStore()
    await store.add_shared_evidence(
        user_id="u-shared",
        content="ETF inflow turned positive for 3 consecutive sessions.",
        metadata={"source": "search_router"},
    )
    hits = await store.query_shared_evidence(
        user_id="u-shared",
        query="ETF inflow positive",
        top_k=2,
    )
    assert hits
    assert "etf inflow" in hits[0].content.lower()
