import pytest

from app.core.roundtable import mcp_tools
from app.core.roundtable.mcp_tools import KnowledgeBaseTool


@pytest.mark.asyncio
async def test_knowledge_base_tool_prefers_results_contract(monkeypatch):
    async def _fake_search(knowledge_service_url, **kwargs):
        assert knowledge_service_url == "http://internal_knowledge_service:8009"
        assert kwargs["query"] == "ai infra"
        assert kwargs["top_k"] == 5
        return {
            "query": "ai infra",
            "results": [
                {
                    "content": "Infra spending increased.",
                    "metadata": {"title": "Q4 note"},
                    "source": "Q4 note",
                    "score": 0.81,
                }
            ],
            "count": 1,
        }

    monkeypatch.setattr(mcp_tools, "shared_search_knowledge_base", _fake_search)

    tool = KnowledgeBaseTool("http://internal_knowledge_service:8009")
    result = await tool.execute("ai infra", top_k=5)

    assert result["success"] is True
    assert len(result["results"]) == 1
    assert len(result["documents"]) == 1
    assert "Q4 note" in result["summary"]


@pytest.mark.asyncio
async def test_knowledge_base_tool_falls_back_to_legacy_documents(monkeypatch):
    async def _fake_search(*args, **kwargs):
        return {
            "query": "legacy",
            "results": [
                {"content": "legacy doc", "source": "legacy-source", "score": 0.5, "metadata": {}}
            ],
            "count": 1,
        }

    monkeypatch.setattr(mcp_tools, "shared_search_knowledge_base", _fake_search)

    tool = KnowledgeBaseTool("http://internal_knowledge_service:8009")
    result = await tool.execute("legacy")

    assert result["success"] is True
    assert len(result["results"]) == 1
    assert result["documents"][0]["source"] == "legacy-source"


@pytest.mark.asyncio
async def test_knowledge_base_tool_skips_search_when_disabled(monkeypatch):
    called = {"value": False}

    async def _fake_search(*args, **kwargs):
        called["value"] = True
        return {"query": "q", "results": []}

    monkeypatch.setattr(mcp_tools, "shared_search_knowledge_base", _fake_search)

    tool = KnowledgeBaseTool("http://internal_knowledge_service:8009", enabled=False)
    result = await tool.execute("q")

    assert result["success"] is True
    assert result["disabled"] is True
    assert result["results"] == []
    assert called["value"] is False


@pytest.mark.asyncio
async def test_knowledge_base_tool_forwards_category(monkeypatch):
    recorder = {}

    async def _fake_search(knowledge_service_url, **kwargs):
        recorder["knowledge_service_url"] = knowledge_service_url
        recorder["kwargs"] = kwargs
        return {"query": "market", "results": []}

    monkeypatch.setattr(mcp_tools, "shared_search_knowledge_base", _fake_search)

    tool = KnowledgeBaseTool(
        "http://internal_knowledge_service:8009",
        enabled=True,
        default_category="market",
    )
    await tool.execute("market")

    assert recorder["knowledge_service_url"] == "http://internal_knowledge_service:8009"
    assert recorder["kwargs"]["category"] == "market"
