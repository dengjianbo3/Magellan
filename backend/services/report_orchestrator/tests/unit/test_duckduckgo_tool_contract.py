import pytest

from app.core.roundtable.duckduckgo_tool import DuckDuckGoSearchTool


class _FakeDDGS:
    def text(self, keywords, region, timelimit, max_results):
        return [
            {
                "title": "Text Result",
                "href": "https://example.com/text",
                "body": "text body",
            }
        ]

    def news(self, keywords, region, timelimit, max_results):
        return [
            {
                "title": "News Result",
                "url": "https://example.com/news",
                "body": "news body",
                "date": "2026-02-12",
                "source": "Example News",
            }
        ]


@pytest.mark.asyncio
async def test_duckduckgo_text_result_normalized_contract(monkeypatch):
    tool = DuckDuckGoSearchTool()
    monkeypatch.setattr(tool, "_get_ddgs", lambda: _FakeDDGS())

    result = await tool.execute("acme text", search_type="text", max_results=1)

    assert result["success"] is True
    assert result["results"][0]["content"] == "text body"
    assert result["results"][0]["published_date"] is None
    assert result["results"][0]["body"] == "text body"
    assert result["results"][0]["date"] is None


@pytest.mark.asyncio
async def test_duckduckgo_news_result_normalized_contract(monkeypatch):
    tool = DuckDuckGoSearchTool()
    monkeypatch.setattr(tool, "_get_ddgs", lambda: _FakeDDGS())

    result = await tool.execute("acme news", search_type="news", max_results=1)

    assert result["success"] is True
    assert result["results"][0]["content"] == "news body"
    assert result["results"][0]["published_date"] == "2026-02-12"
    assert result["results"][0]["body"] == "news body"
    assert result["results"][0]["date"] == "2026-02-12"
