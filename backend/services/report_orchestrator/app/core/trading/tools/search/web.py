"""
Web Search Tool

Uses Tavily API for real-time web search.
"""

from typing import List
import os
import logging

from ..base import BaseTool, ToolResult, ToolParameter, ToolCategory

logger = logging.getLogger(__name__)


class TavilySearchTool(BaseTool):
    """
    Web search using Tavily API.
    
    Useful for getting latest news, market analysis, and real-time information.
    """
    
    name = "tavily_search"
    description = "Search the web for latest news and information. Use for market news, economic data, and analysis."
    category = ToolCategory.SEARCH
    
    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="Search query (e.g., 'Bitcoin BTC market news today')",
                required=True
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Maximum number of results to return",
                required=False,
                default=5
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute web search."""
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 5)
        
        if not query:
            return ToolResult.error_result(
                "Query is required",
                self.name
            )
        
        if not self.api_key:
            return ToolResult.error_result(
                "TAVILY_API_KEY not configured",
                self.name
            )
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                        "include_answer": True,
                        "search_depth": "basic"
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    results = []
                    for item in data.get("results", [])[:max_results]:
                        results.append({
                            "title": item.get("title", ""),
                            "content": item.get("content", "")[:300],
                            "url": item.get("url", ""),
                            "score": item.get("score", 0)
                        })
                    
                    return ToolResult.success_result({
                        "query": query,
                        "answer": data.get("answer", ""),
                        "results": results,
                        "result_count": len(results)
                    }, self.name)
                else:
                    return ToolResult.error_result(
                        f"Search failed with status {response.status_code}",
                        self.name
                    )
                    
        except Exception as e:
            logger.error(f"Search error: {e}")
            return ToolResult.error_result(str(e), self.name)
