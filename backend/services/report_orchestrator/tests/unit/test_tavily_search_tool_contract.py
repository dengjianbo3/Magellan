import pytest

from app.core.roundtable.mcp_tools import TavilySearchTool


class _FakeMCPClient:
    async def call_tool(self, server_name: str, tool_name: str, **params):
        assert server_name == "web-search"
        assert tool_name == "search"
        return {
            "success": True,
            "result": {
                "summary": "ok",
                "query": params.get("query"),
                "results": [
                    {
                        "title": "R1",
                        "url": "https://example.com/r1",
                        "content": "result content",
                        "published_date": "2026-02-14",
                    }
                ],
            },
            "error": None,
        }


@pytest.mark.asyncio
async def test_tavily_search_tool_flattens_mcp_envelope():
    tool = TavilySearchTool(mcp_client=_FakeMCPClient())
    result = await tool.execute("acme")

    assert result["success"] is True
    assert result["summary"] == "ok"
    assert result["results"][0]["content"] == "result content"
    assert result["results"][0]["published_date"] == "2026-02-14"
    assert result["results"][0]["body"] == "result content"
    assert result["results"][0]["date"] == "2026-02-14"
