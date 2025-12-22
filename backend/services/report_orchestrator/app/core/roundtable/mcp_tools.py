"""
MCP Tools for Roundtable Discussion Agents
为圆桌讨论专家提供的 MCP 工具集
"""
import os
from typing import Any, Dict, List, Optional
from .tool import Tool
from .mcp_client import MCPClient


# 全局 MCP Client 实例 (懒加载)
_mcp_client: Optional[MCPClient] = None

def get_mcp_client() -> MCPClient:
    """获取全局 MCP Client 实例"""
    global _mcp_client
    if _mcp_client is None:
        # 加载 MCP 配置 (绝对路径或相对路径)
        config_path = os.path.join(
            os.path.dirname(__file__),
            "../../../config/mcp_config.yaml"
        )
        # 规范化路径
        config_path = os.path.abspath(config_path)
        print(f"[get_mcp_client] Loading MCP config from: {config_path}")
        _mcp_client = MCPClient(config_path=config_path)
    return _mcp_client


class TavilySearchTool(Tool):
    """
    Tavily 网络搜索工具 (MCP方式)

    通过 MCP Client 调用 Web Search Service
    支持时间过滤功能
    """

    def __init__(
        self,
        max_results: int = 3,
        mcp_client: Optional[MCPClient] = None
    ):
        """
        Args:
            max_results: Maximum search results
            mcp_client: MCP Client instance (optional, defaults to global instance)
        """
        super().__init__(
            name="tavily_search",
            description="""Search the internet for latest information, news, market data, etc.
Supports time filtering:
- topic: Set to "news" to search news, use with days parameter
- time_range: "day"(24h), "week"(7d), "month"(30d), "year"(1y)
- days: Use with topic="news", e.g., 3 means last 3 days

Example: Search news from last week, set time_range="week" or topic="news" with days=7"""
        )
        self.max_results = max_results
        self.mcp_client = mcp_client or get_mcp_client()

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Execute web search

        Args:
            query: Search query
            **kwargs: Other parameters
                - max_results: Maximum number of results
                - topic: "general" or "news"
                - time_range: "day", "week", "month", "year"
                - days: Number of days (only valid when topic="news")

        Returns:
            Search results
        """
        max_results = kwargs.get("max_results", self.max_results)
        topic = kwargs.get("topic", "general")
        time_range = kwargs.get("time_range", None)
        days = kwargs.get("days", None)

        try:
            # Prepare MCP call parameters
            params = {
                "query": query,
                "max_results": max_results,
                "topic": topic
            }

            # Add time filtering if specified
            if time_range and time_range in ["day", "week", "month", "year"]:
                params["time_range"] = time_range

            if days and topic == "news":
                params["days"] = days

            # Call web-search service search tool via MCP Client
            result = await self.mcp_client.call_tool(
                server_name="web-search",
                tool_name="search",
                **params
            )

            # MCP response already contains success, summary, results
            return result

        except Exception as e:
            print(f"[TavilySearchTool] MCP call failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"Error searching '{query}': {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        """Return tool schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, should be specific and clear questions or keywords"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": self.max_results
                    },
                    "topic": {
                        "type": "string",
                        "description": "Search topic: 'general'(general search) or 'news'(news search, can use with days)",
                        "enum": ["general", "news"],
                        "default": "general"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range filter: 'day'(24h), 'week'(7d), 'month'(30d), 'year'(1y)",
                        "enum": ["day", "week", "month", "year"]
                    },
                    "days": {
                        "type": "integer",
                        "description": "Search content from last N days (only valid when topic='news')"
                    }
                },
                "required": ["query"]
            }
        }


class PublicDataTool(Tool):
    """
    Public Data Query Tool (MCP)

    Get public company data via External Data Service
    """

    def __init__(
        self,
        external_data_url: str = "http://external_data_service:8006"
    ):
        """
        Args:
            external_data_url: External Data Service URL
        """
        super().__init__(
            name="get_public_company_data",
            description="Get public data of listed companies, including basic info, financial data, stock price info, etc. Only applicable to publicly listed companies."
        )
        self.external_data_url = external_data_url

    async def execute(self, company_name: str, **kwargs) -> Dict[str, Any]:
        """
        Get public company data

        Args:
            company_name: Company name or stock symbol
            **kwargs: Other parameters

        Returns:
            Company data
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.external_data_url}/public_data/{company_name}"
                )

                if response.status_code == 404:
                    return {
                        "success": False,
                        "summary": f"Public data for company '{company_name}' not found. May be a private company or incorrect name."
                    }

                response.raise_for_status()
                data = response.json()

                # Format summary
                summary_parts = [f"Public data for company '{company_name}':\n"]

                if "basic_info" in data:
                    info = data["basic_info"]
                    summary_parts.append(
                        f"\nBasic Info:\n"
                        f"  - Full Name: {info.get('full_name', 'N/A')}\n"
                        f"  - Industry: {info.get('industry', 'N/A')}\n"
                        f"  - Founded: {info.get('founded', 'N/A')}\n"
                        f"  - Headquarters: {info.get('headquarters', 'N/A')}\n"
                    )

                if "financial_data" in data:
                    fin = data["financial_data"]
                    summary_parts.append(
                        f"\nFinancial Data:\n"
                        f"  - Revenue: {fin.get('revenue', 'N/A')}\n"
                        f"  - Net Income: {fin.get('net_income', 'N/A')}\n"
                        f"  - Market Cap: {fin.get('market_cap', 'N/A')}\n"
                    )

                return {
                    "success": True,
                    "summary": "".join(summary_parts),
                    "data": data
                }

        except Exception as e:
            print(f"[PublicDataTool] Query failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"Error querying data for '{company_name}': {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        """Return tool schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Company name or stock symbol"
                    }
                },
                "required": ["company_name"]
            }
        }


class KnowledgeBaseTool(Tool):
    """
    Internal Knowledge Base Query Tool (MCP)

    Query uploaded documents and knowledge via Internal Knowledge Service
    """

    def __init__(
        self,
        knowledge_service_url: str = "http://internal_knowledge_service:8009"
    ):
        """
        Args:
            knowledge_service_url: Internal Knowledge Service URL
        """
        super().__init__(
            name="search_knowledge_base",
            description="Search internal knowledge base for relevant documents and information. Suitable for querying uploaded BPs, research reports, internal documents, etc."
        )
        self.knowledge_service_url = knowledge_service_url

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search knowledge base

        Args:
            query: Search query
            **kwargs: Other parameters (e.g., top_k)

        Returns:
            Search results
        """
        top_k = kwargs.get("top_k", 3)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.knowledge_service_url}/search",
                    json={
                        "query": query,
                        "top_k": top_k
                    }
                )
                response.raise_for_status()
                result = response.json()

                documents = result.get("documents", [])
                if not documents:
                    return {
                        "success": True,
                        "summary": f"No relevant content found in knowledge base for '{query}'.",
                        "documents": []
                    }

                # Build summary
                summary_parts = [f"Found {len(documents)} relevant items in knowledge base for '{query}':\n"]
                for i, doc in enumerate(documents, 1):
                    summary_parts.append(
                        f"\n{i}. {doc.get('source', 'Unknown')}\n"
                        f"   Content: {doc.get('content', '')[:200]}...\n"
                        f"   Relevance: {doc.get('score', 0):.2f}"
                    )

                return {
                    "success": True,
                    "summary": "".join(summary_parts),
                    "documents": documents,
                    "query": query
                }

        except Exception as e:
            print(f"[KnowledgeBaseTool] Search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"Error searching knowledge base for '{query}': {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        """Return tool schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query content"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Return top K most relevant results",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }


from .yahoo_finance_tool import YahooFinanceTool
from .sec_edgar_tool import SECEdgarTool
from .akshare_tool import AkShareTool

# Phase 1 增强工具
from .enhanced_tools import (
    ChinaMarketDataTool,
    CompanyRegistryTool,
    GitHubAnalyzerTool,
    PatentSearchTool,
    SentimentMonitorTool
)

# Phase 2 分析计算工具
from .analysis_tools import (
    DCFCalculatorTool,
    ComparableAnalysisTool,
    RiskScoringTool,
    ComplianceCheckerTool,
    SummaryChartTool
)

# Phase 3 MCP工具桥接
from .mcp_tool_bridge import (
    MCPFinancialDataTool,
    MCPCompanyIntelligenceTool,
    get_mcp_tool_for_agent
)

# Phase 4 高级工具
from .advanced_tools import (
    PersonBackgroundTool,
    RegulationSearchTool,
    MultiExchangeTool,
    OrderbookAnalyzerTool,
    BlackSwanScannerTool
)


# 工具工厂函数
def create_mcp_tools_for_agent(agent_role: str) -> List[Tool]:
    """
    根据 Agent 角色创建合适的 MCP 工具集

    Args:
        agent_role: Agent 角色名称

    Returns:
        工具列表
    """
    # 基础工具 - 所有专家都可以使用
    tools = []

    # Tavily 搜索 - 所有专家都可以使用
    tools.append(TavilySearchTool())

    # 根据角色添加特定工具
    if agent_role in ["MarketAnalyst", "市场分析师"]:
        # 市场分析师需要公开数据和搜索
        tools.append(PublicDataTool())
        tools.append(YahooFinanceTool())  # 添加股票市场数据工具
        tools.append(SECEdgarTool())      # 添加SEC官方数据工具
        tools.append(AkShareTool())       # A股市场数据 (免费)
        tools.append(ChinaMarketDataTool())  # Phase 1: 中国市场数据 (A股/港股)
        tools.append(MCPFinancialDataTool()) # Phase 3: MCP金融数据服务

    elif agent_role in ["FinancialExpert", "财务专家"]:
        # 财务专家需要公开数据和财务报表
        tools.append(PublicDataTool())
        tools.append(YahooFinanceTool())  # 添加财报数据工具
        tools.append(SECEdgarTool())      # 添加SEC官方财报工具
        tools.append(AkShareTool())       # A股财务数据 (免费)
        tools.append(ChinaMarketDataTool())  # Phase 1: 中国市场数据 (财务分析)
        tools.append(DCFCalculatorTool())      # Phase 2: DCF估值计算
        tools.append(ComparableAnalysisTool()) # Phase 2: 可比公司分析
        tools.append(MCPFinancialDataTool())   # Phase 3: MCP金融数据服务

    elif agent_role in ["TeamEvaluator", "团队评估"]:
        # 团队评估专家需要搜索团队背景和企业信息
        tools.append(CompanyRegistryTool())       # Phase 1: 企业工商信息查询
        tools.append(MCPCompanyIntelligenceTool()) # Phase 3: MCP企业信息服务
        tools.append(PersonBackgroundTool())      # Phase 4: 人员背景调查

    elif agent_role in ["RiskAssessor", "风险评估"]:
        # 风险评估专家需要搜索风险信息和查看SEC披露的风险因素
        tools.append(SECEdgarTool())  # 添加SEC工具查看8-K重大事件和10-K风险因素
        tools.append(SentimentMonitorTool())  # Phase 1: 舆情监控和负面信息追踪
        tools.append(RiskScoringTool())       # Phase 2: 风险量化评分模型
        tools.append(MCPCompanyIntelligenceTool()) # Phase 3: MCP企业信息（风险查询）
        tools.append(BlackSwanScannerTool())  # Phase 4: 黑天鹅事件扫描

    elif agent_role in ["TechSpecialist", "技术专家"]:
        # 技术专家需要分析技术栈和专利
        tools.append(GitHubAnalyzerTool())  # Phase 1: GitHub项目分析
        tools.append(PatentSearchTool())    # Phase 1: 专利检索

    elif agent_role in ["LegalAdvisor", "法律顾问"]:
        # 法律顾问需要搜索法规和专利信息
        tools.append(PatentSearchTool())       # Phase 1: 专利检索 (知识产权相关)
        tools.append(ComplianceCheckerTool())  # Phase 2: 合规性检查清单
        tools.append(RegulationSearchTool())   # Phase 4: 法规检索工具

    elif agent_role in ["TechnicalAnalyst", "技术分析师"]:
        # 技术分析师需要加密货币市场数据
        tools.append(YahooFinanceTool())       # 免费: 股票价格和技术数据
        tools.append(MultiExchangeTool())      # Phase 4: 多交易所数据
        tools.append(OrderbookAnalyzerTool())  # Phase 4: 订单簿分析

    elif agent_role in ["Leader", "主持人", "Moderator"]:
        # Leader需要汇总和报告生成工具
        tools.append(SummaryChartTool())  # Phase 2: 汇总图表生成

    # ========== Phase 2 新增 Agent 工具配置 ==========

    elif agent_role in ["MacroEconomist", "宏观经济分析师"]:
        # 宏观经济分析师需要宏观数据和市场趋势
        tools.append(YahooFinanceTool())       # 免费: 市场指数和宏观数据
        tools.append(AkShareTool())            # 免费: A股宏观数据
        tools.append(ChinaMarketDataTool())    # 中国市场宏观数据

    elif agent_role in ["ESGAnalyst", "ESG分析师"]:
        # ESG分析师需要企业可持续发展信息
        tools.append(YahooFinanceTool())       # 免费: 公司ESG评分
        tools.append(SECEdgarTool())           # 免费: SEC ESG披露文件
        tools.append(CompanyRegistryTool())    # 企业合规信息

    elif agent_role in ["SentimentAnalyst", "情绪分析师"]:
        # 情绪分析师需要舆情和市场情绪数据
        tools.append(YahooFinanceTool())       # 免费: 新闻和市场数据
        tools.append(SentimentMonitorTool())   # 舆情监控
        tools.append(AkShareTool())            # 免费: A股龙虎榜等情绪指标

    elif agent_role in ["QuantStrategist", "量化策略师"]:
        # 量化策略师需要技术分析和量化工具
        tools.append(YahooFinanceTool())       # 免费: 历史数据
        tools.append(AkShareTool())            # 免费: A股量化数据
        tools.append(MultiExchangeTool())      # 多交易所数据
        tools.append(OrderbookAnalyzerTool())  # 订单簿分析

    elif agent_role in ["DealStructurer", "交易结构师"]:
        # 交易结构师需要估值和交易结构工具
        tools.append(YahooFinanceTool())       # 免费: 估值数据
        tools.append(SECEdgarTool())           # 免费: SEC交易披露
        tools.append(DCFCalculatorTool())      # DCF估值
        tools.append(ComparableAnalysisTool()) # 可比公司分析

    elif agent_role in ["MAAdvisor", "并购顾问"]:
        # 并购顾问需要企业信息和估值工具
        tools.append(YahooFinanceTool())       # 免费: 目标公司财务
        tools.append(SECEdgarTool())           # 免费: SEC并购披露 (8-K)
        tools.append(CompanyRegistryTool())    # 企业工商信息
        tools.append(DCFCalculatorTool())      # DCF估值
        tools.append(ComparableAnalysisTool()) # 可比公司分析
        tools.append(MCPCompanyIntelligenceTool()) # 企业情报

    # 知识库工具 - 所有专家都可以使用
    tools.append(KnowledgeBaseTool())

    return tools
