import pytest

from app.agents import market_analysis_agent
from app.agents.market_analysis_agent import MarketAnalysisAgent


@pytest.mark.asyncio
async def test_query_internal_knowledge_skips_when_disabled(monkeypatch):
    called = {"value": False}

    async def _fake_search(*args, **kwargs):
        called["value"] = True
        return {"results": []}

    monkeypatch.setattr(market_analysis_agent, "shared_search_knowledge_base", _fake_search)

    agent = MarketAnalysisAgent(
        web_search_url="http://web-search",
        internal_knowledge_url="http://internal-knowledge",
        llm_gateway_url="http://llm-gateway",
        knowledge_enabled=False,
    )
    results = await agent._query_internal_knowledge({"target_market": "AI"})

    assert results == []
    assert called["value"] is False


@pytest.mark.asyncio
async def test_query_internal_knowledge_forwards_category(monkeypatch):
    recorder = {}

    async def _fake_search(knowledge_service_url, **kwargs):
        recorder["knowledge_service_url"] = knowledge_service_url
        recorder["kwargs"] = kwargs
        return {"results": [{"content": "ok"}]}

    monkeypatch.setattr(market_analysis_agent, "shared_search_knowledge_base", _fake_search)

    agent = MarketAnalysisAgent(
        web_search_url="http://web-search",
        internal_knowledge_url="http://internal-knowledge",
        llm_gateway_url="http://llm-gateway",
        knowledge_enabled=True,
        knowledge_category="market",
    )
    results = await agent._query_internal_knowledge({"target_market": "AI"})

    assert len(results) == 1
    assert recorder["knowledge_service_url"] == "http://internal-knowledge"
    assert recorder["kwargs"]["category"] == "market"


@pytest.mark.asyncio
async def test_query_internal_knowledge_treats_all_as_no_filter(monkeypatch):
    recorder = {}

    async def _fake_search(knowledge_service_url, **kwargs):
        recorder["kwargs"] = kwargs
        return {"results": []}

    monkeypatch.setattr(market_analysis_agent, "shared_search_knowledge_base", _fake_search)

    agent = MarketAnalysisAgent(
        web_search_url="http://web-search",
        internal_knowledge_url="http://internal-knowledge",
        knowledge_enabled=True,
        knowledge_category="all",
    )
    await agent._query_internal_knowledge({"target_market": "AI"})

    assert recorder["kwargs"]["category"] is None
