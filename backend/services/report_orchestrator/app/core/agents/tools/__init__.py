"""
Agent Tools Module
Agent 工具模块

提供所有 Agent 可用的工具集
"""

# 从现有实现导入工具
from app.core.roundtable.tool import Tool
from app.core.roundtable.enhanced_tools import (
    YahooFinanceTool,
    SECEdgarTool,
    create_yahoo_finance_tool,
    create_sec_edgar_tool
)
from app.core.roundtable.mcp_tool_bridge import (
    MCPFinancialDataTool,
    MCPCompanyIntelligenceTool,
    create_mcp_tools,
    get_mcp_tool_for_agent
)
from app.core.roundtable.mcp_tools import TavilySearchTool, KnowledgeBaseTool
from app.core.roundtable.serper_tool import SerperSearchTool

from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Backward-compat alias: historical name used across some prompts/config.
InternalKnowledgeTool = KnowledgeBaseTool


def create_tavily_search_tool(max_results: int = 3) -> TavilySearchTool:
    return TavilySearchTool(max_results=max_results)


def create_internal_knowledge_tool(knowledge_service_url: Optional[str] = None) -> KnowledgeBaseTool:
    return KnowledgeBaseTool(knowledge_service_url=knowledge_service_url)


class AnalysisToolkit:
    """
    分析工具包 - 为分析Agent提供统一的工具调用接口
    """

    def __init__(self):
        """初始化工具包"""
        self.search_tool = SerperSearchTool(max_results=5)
        self.finance_tool = YahooFinanceTool()
        logger.info("📦 AnalysisToolkit initialized")

    async def search_news(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """搜索相关新闻"""
        try:
            return await self.search_tool.execute(query=query, max_results=max_results, search_type="news")
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def search_web(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """执行通用网页搜索"""
        try:
            return await self.search_tool.execute(query=query, max_results=max_results, search_type="text")
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_stock_price(self, symbol: str) -> Dict[str, Any]:
        """获取股票当前价格"""
        try:
            return await self.finance_tool.execute(action="price", symbol=symbol)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_financials(self, symbol: str, statement: str = "income") -> Dict[str, Any]:
        """获取财务报表"""
        try:
            return await self.finance_tool.execute(action="financials", symbol=symbol, statement=statement)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_company_info(self, symbol: str) -> Dict[str, Any]:
        """获取公司基本信息"""
        try:
            return await self.finance_tool.execute(action="info", symbol=symbol)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_valuation(self, symbol: str) -> Dict[str, Any]:
        """获取估值指标"""
        try:
            return await self.finance_tool.execute(action="valuation", symbol=symbol)
        except Exception as e:
            return {"success": False, "error": str(e)}


# 单例
_toolkit: Optional[AnalysisToolkit] = None


def get_analysis_toolkit() -> AnalysisToolkit:
    """获取分析工具包单例"""
    global _toolkit
    if _toolkit is None:
        _toolkit = AnalysisToolkit()
    return _toolkit


__all__ = [
    # 基础工具类
    "Tool",

    # 分析工具
    "TavilySearchTool",
    "InternalKnowledgeTool",
    "create_tavily_search_tool",
    "create_internal_knowledge_tool",

    # 增强工具
    "YahooFinanceTool",
    "SECEdgarTool",
    "create_yahoo_finance_tool",
    "create_sec_edgar_tool",
    "SerperSearchTool",

    # MCP工具
    "MCPFinancialDataTool",
    "MCPCompanyIntelligenceTool",
    "create_mcp_tools",
    "get_mcp_tool_for_agent",

    # 工具包
    "AnalysisToolkit",
    "get_analysis_toolkit",
]
