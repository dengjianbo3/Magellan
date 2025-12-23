"""
DuckDuckGo Search Tool
免费网络搜索工具 - 作为默认搜索源

使用 duckduckgo-search 包，完全免费无API Key
"""
import asyncio
from typing import Any, Dict
from .tool import Tool


class DuckDuckGoSearchTool(Tool):
    """
    DuckDuckGo 免费搜索工具
    
    特点：
    - 完全免费，无API Key
    - 支持通用搜索和新闻搜索
    - 支持时间范围过滤
    - 支持地区设置
    """

    def __init__(self, max_results: int = 5):
        """
        Args:
            max_results: 默认返回结果数量
        """
        super().__init__(
            name="duckduckgo_search",
            description="""Free web search using DuckDuckGo.
Supports general search and news search.
Use this for background information, company profiles, general queries.
For realtime/critical data, use web_search with priority="realtime" instead."""
        )
        self.max_results = max_results
        self._ddgs = None

    def _get_ddgs(self):
        """Lazy load DDGS client"""
        if self._ddgs is None:
            try:
                from duckduckgo_search import DDGS
                self._ddgs = DDGS()
            except ImportError:
                raise ImportError(
                    "duckduckgo-search not installed. "
                    "Run: pip install duckduckgo-search"
                )
        return self._ddgs

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        执行DuckDuckGo搜索
        
        Args:
            query: 搜索查询
            **kwargs:
                - max_results: 最大结果数
                - search_type: "text" (默认) 或 "news"
                - time_range: "d"(天), "w"(周), "m"(月), "y"(年)
                - region: 区域代码，如 "cn-zh", "us-en"
        
        Returns:
            搜索结果
        """
        max_results = kwargs.get("max_results", self.max_results)
        search_type = kwargs.get("search_type", "text")
        time_range = kwargs.get("time_range", None)
        region = kwargs.get("region", "wt-wt")  # 默认全球
        
        try:
            ddgs = self._get_ddgs()
            
            # 在线程池中执行同步搜索
            loop = asyncio.get_event_loop()
            
            if search_type == "news":
                results = await loop.run_in_executor(
                    None,
                    lambda: list(ddgs.news(
                        keywords=query,
                        region=region,
                        timelimit=time_range,
                        max_results=max_results
                    ))
                )
            else:
                results = await loop.run_in_executor(
                    None,
                    lambda: list(ddgs.text(
                        keywords=query,
                        region=region,
                        timelimit=time_range,
                        max_results=max_results
                    ))
                )
            
            if not results:
                return {
                    "success": True,
                    "summary": f"No results found for '{query}'",
                    "results": [],
                    "source": "duckduckgo"
                }
            
            # 格式化结果
            formatted_results = []
            summary_parts = [f"Found {len(results)} results for '{query}':\n"]
            
            for i, r in enumerate(results, 1):
                if search_type == "news":
                    formatted_results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "body": r.get("body", ""),
                        "date": r.get("date", ""),
                        "source": r.get("source", "")
                    })
                    summary_parts.append(
                        f"\n{i}. [{r.get('source', 'News')}] {r.get('title', '')}\n"
                        f"   Date: {r.get('date', 'N/A')}\n"
                        f"   {r.get('body', '')[:150]}...\n"
                    )
                else:
                    formatted_results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "body": r.get("body", "")
                    })
                    summary_parts.append(
                        f"\n{i}. {r.get('title', '')}\n"
                        f"   URL: {r.get('href', '')}\n"
                        f"   {r.get('body', '')[:150]}...\n"
                    )
            
            return {
                "success": True,
                "summary": "".join(summary_parts),
                "results": formatted_results,
                "source": "duckduckgo",
                "query": query
            }
            
        except ImportError as e:
            return {
                "success": False,
                "error": str(e),
                "summary": "DuckDuckGo search unavailable: package not installed",
                "fallback_needed": True
            }
        except Exception as e:
            print(f"[DuckDuckGoSearchTool] Search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"DuckDuckGo search failed for '{query}': {str(e)}",
                "fallback_needed": True
            }

    def to_schema(self) -> Dict[str, Any]:
        """返回工具schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": self.max_results
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Search type: 'text' or 'news'",
                        "enum": ["text", "news"],
                        "default": "text"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time filter: 'd'(day), 'w'(week), 'm'(month), 'y'(year)",
                        "enum": ["d", "w", "m", "y"]
                    }
                },
                "required": ["query"]
            }
        }
