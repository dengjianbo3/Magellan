"""
Web Search Tool - 统一网络搜索工具
通过 SearchRouter 智能路由到 Tavily 或 DuckDuckGo

Agent使用 priority 参数声明搜索需求：
- realtime: 实时数据（股价、突发新闻）→ Tavily
- critical: 关键决策数据 → Tavily
- normal: 一般背景信息 → DuckDuckGo（失败回退Tavily）
"""
from typing import Any, Dict
from .tool import Tool
from .search_router import unified_search


class WebSearchTool(Tool):
    """
    统一网络搜索工具
    
    自动根据 priority 参数路由到最合适的搜索源
    """

    def __init__(self, max_results: int = 5):
        """
        Args:
            max_results: 默认返回结果数量
        """
        super().__init__(
            name="web_search",
            description="""Search the internet for information.

Use the 'priority' parameter to indicate search importance:
- "realtime": Realtime data (stock prices, breaking news) - uses premium search
- "critical": Critical investment decision data - uses premium search  
- "normal": Background info (company history, team bios) - uses free search

Examples:
- Search latest BTC price: priority="realtime"
- Search NVIDIA Q3 earnings for analysis: priority="critical"
- Search company founder background: priority="normal"

Supports time filtering:
- topic: "general" or "news"
- time_range: "day", "week", "month", "year"
"""
        )
        self.max_results = max_results

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        执行网络搜索
        
        Args:
            query: 搜索查询
            **kwargs:
                - priority: "realtime" / "critical" / "normal" (default)
                - max_results: 最大结果数
                - topic: "general" or "news"
                - time_range: "day", "week", "month", "year"
        
        Returns:
            搜索结果
        """
        priority = kwargs.get("priority", "normal")
        max_results = kwargs.get("max_results", self.max_results)
        topic = kwargs.get("topic", "general")
        time_range = kwargs.get("time_range", None)
        
        # 通过 SearchRouter 统一路由
        result = await unified_search(
            query=query,
            priority=priority,
            max_results=max_results,
            topic=topic,
            time_range=time_range
        )
        
        return result

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
                        "description": "Search query - be specific and clear"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Search priority: 'realtime'(stock prices, breaking news), 'critical'(key decision data), 'normal'(background info)",
                        "enum": ["realtime", "critical", "normal"],
                        "default": "normal"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": self.max_results
                    },
                    "topic": {
                        "type": "string",
                        "description": "Search topic: 'general' or 'news'",
                        "enum": ["general", "news"],
                        "default": "general"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time filter: 'day', 'week', 'month', 'year'",
                        "enum": ["day", "week", "month", "year"]
                    }
                },
                "required": ["query"]
            }
        }
