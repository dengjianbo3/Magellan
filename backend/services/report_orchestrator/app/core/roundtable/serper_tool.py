"""
Serper Search Tool - L1层Google搜索工具
使用Serper.dev API (Google搜索结果)

用于 critical 优先级查询
"""
import os
import httpx
from typing import Any, Dict
from .tool import Tool


class SerperSearchTool(Tool):
    """
    Serper.dev Google 搜索工具
    
    特点：
    - 基于Google搜索，质量高
    - $50/月无限次 或 免费2500次/月
    - 支持通用搜索和新闻搜索
    """

    def __init__(self, max_results: int = 5):
        """
        Args:
            max_results: 默认返回结果数量
        """
        super().__init__(
            name="serper_search",
            description="""Google search using Serper.dev API.
High-quality search results powered by Google.
Use this for critical investment analysis data."""
        )
        self.max_results = max_results
        self.api_key = os.getenv("SERPER_API_KEY")
        
    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        执行Serper搜索
        
        Args:
            query: 搜索查询
            **kwargs:
                - max_results: 最大结果数
                - search_type: "text" (默认) 或 "news"
        
        Returns:
            搜索结果
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "SERPER_API_KEY not configured",
                "summary": "Serper search unavailable: API key not set",
                "fallback_needed": True
            }
        
        max_results = kwargs.get("max_results", self.max_results)
        search_type = kwargs.get("search_type", "text")
        
        # 选择API端点
        if search_type == "news":
            url = "https://google.serper.dev/news"
        else:
            url = "https://google.serper.dev/search"
        
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": max_results
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
            
            # 解析结果
            results = []
            if search_type == "news":
                items = data.get("news", [])[:max_results]
            else:
                items = data.get("organic", [])[:max_results]
            
            if not items:
                return {
                    "success": True,
                    "summary": f"No results found for '{query}'",
                    "results": [],
                    "source": "serper"
                }
            
            # 格式化结果
            formatted_results = []
            summary_parts = [f"Found {len(items)} results for '{query}':\n"]
            
            for i, item in enumerate(items, 1):
                formatted_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "body": item.get("snippet", ""),
                    "date": item.get("date")
                })
                
                date_info = f" ({item.get('date')})" if item.get("date") else ""
                summary_parts.append(
                    f"\n{i}. {item.get('title', '')}{date_info}\n"
                    f"   URL: {item.get('link', '')}\n"
                    f"   {item.get('snippet', '')[:150]}...\n"
                )
            
            return {
                "success": True,
                "summary": "".join(summary_parts),
                "results": formatted_results,
                "source": "serper",
                "query": query
            }
            
        except httpx.HTTPStatusError as e:
            print(f"[SerperSearchTool] HTTP error: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"Serper search failed: HTTP {e.response.status_code}",
                "fallback_needed": True
            }
        except Exception as e:
            print(f"[SerperSearchTool] Search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"Serper search failed for '{query}': {str(e)}",
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
                    }
                },
                "required": ["query"]
            }
        }
