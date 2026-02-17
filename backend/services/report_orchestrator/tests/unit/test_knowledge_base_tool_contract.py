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
