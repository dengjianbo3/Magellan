"""
Agent Tools Module
Agent 工具模块

提供所有 Agent 可用的工具集
"""

# 从现有实现导入工具
from app.core.roundtable.tool import Tool
from app.core.roundtable.analysis_tools import (
    TavilySearchTool,
    InternalKnowledgeTool,
    create_tavily_search_tool,
    create_internal_knowledge_tool
)
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

    # MCP工具
    "MCPFinancialDataTool",
    "MCPCompanyIntelligenceTool",
    "create_mcp_tools",
    "get_mcp_tool_for_agent",
]
