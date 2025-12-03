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
            max_results: 最大搜索结果数
            mcp_client: MCP Client 实例 (可选，默认使用全局实例)
        """
        super().__init__(
            name="tavily_search",
            description="""搜索互联网获取最新信息、新闻、市场数据等。
支持时间过滤:
- topic: 设为"news"可搜索新闻，配合days参数限制天数
- time_range: "day"(24小时), "week"(7天), "month"(30天), "year"(1年)
- days: 配合topic="news"使用，指定天数如3表示最近3天

示例: 搜索最近一周的新闻，设置time_range="week"或topic="news"且days=7"""
        )
        self.max_results = max_results
        self.mcp_client = mcp_client or get_mcp_client()

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        执行网络搜索

        Args:
            query: 搜索查询
            **kwargs: 其他参数
                - max_results: 最大返回结果数量
                - topic: "general" 或 "news"
                - time_range: "day", "week", "month", "year"
                - days: 天数 (仅topic="news"时有效)

        Returns:
            搜索结果
        """
        max_results = kwargs.get("max_results", self.max_results)
        topic = kwargs.get("topic", "general")
        time_range = kwargs.get("time_range", None)
        days = kwargs.get("days", None)

        try:
            # 准备 MCP 调用参数
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

            # 通过 MCP Client 调用 web-search 服务的 search 工具
            result = await self.mcp_client.call_tool(
                server_name="web-search",
                tool_name="search",
                **params
            )

            # MCP 响应已经包含 success, summary, results
            return result

        except Exception as e:
            print(f"[TavilySearchTool] MCP call failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"搜索'{query}'时出现错误: {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        """返回工具的 Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询内容，应该是具体明确的问题或关键词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数量",
                        "default": self.max_results
                    },
                    "topic": {
                        "type": "string",
                        "description": "搜索主题: 'general'(通用搜索) 或 'news'(新闻搜索，可配合days参数)",
                        "enum": ["general", "news"],
                        "default": "general"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "时间范围过滤: 'day'(24小时), 'week'(7天), 'month'(30天), 'year'(1年)",
                        "enum": ["day", "week", "month", "year"]
                    },
                    "days": {
                        "type": "integer",
                        "description": "搜索最近N天的内容 (仅当topic='news'时有效)"
                    }
                },
                "required": ["query"]
            }
        }


class PublicDataTool(Tool):
    """
    公开数据查询工具 (MCP方式)

    通过 External Data Service 获取上市公司公开数据
    """

    def __init__(
        self,
        external_data_url: str = "http://external_data_service:8006"
    ):
        """
        Args:
            external_data_url: External Data Service 的 URL
        """
        super().__init__(
            name="get_public_company_data",
            description="获取上市公司的公开数据，包括基本信息、财务数据、股价信息等。仅适用于已上市的公司。"
        )
        self.external_data_url = external_data_url

    async def execute(self, company_name: str, **kwargs) -> Dict[str, Any]:
        """
        获取公司公开数据

        Args:
            company_name: 公司名称或股票代码
            **kwargs: 其他参数

        Returns:
            公司数据
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.external_data_url}/public_data/{company_name}"
                )

                if response.status_code == 404:
                    return {
                        "success": False,
                        "summary": f"未找到公司'{company_name}'的公开数据，可能是未上市公司或公司名称不正确。"
                    }

                response.raise_for_status()
                data = response.json()

                # 格式化摘要
                summary_parts = [f"公司'{company_name}'的公开数据:\n"]

                if "basic_info" in data:
                    info = data["basic_info"]
                    summary_parts.append(
                        f"\n基本信息:\n"
                        f"  - 公司全称: {info.get('full_name', 'N/A')}\n"
                        f"  - 行业: {info.get('industry', 'N/A')}\n"
                        f"  - 成立时间: {info.get('founded', 'N/A')}\n"
                        f"  - 总部: {info.get('headquarters', 'N/A')}\n"
                    )

                if "financial_data" in data:
                    fin = data["financial_data"]
                    summary_parts.append(
                        f"\n财务数据:\n"
                        f"  - 营收: {fin.get('revenue', 'N/A')}\n"
                        f"  - 净利润: {fin.get('net_income', 'N/A')}\n"
                        f"  - 市值: {fin.get('market_cap', 'N/A')}\n"
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
                "summary": f"查询'{company_name}'数据时出现错误: {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        """返回工具的 Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "公司名称或股票代码"
                    }
                },
                "required": ["company_name"]
            }
        }


class KnowledgeBaseTool(Tool):
    """
    内部知识库查询工具 (MCP方式)

    通过 Internal Knowledge Service 查询已上传的文档和知识
    """

    def __init__(
        self,
        knowledge_service_url: str = "http://internal_knowledge_service:8009"
    ):
        """
        Args:
            knowledge_service_url: Internal Knowledge Service 的 URL
        """
        super().__init__(
            name="search_knowledge_base",
            description="在内部知识库中搜索相关文档和信息。适用于查询已上传的BP、研究报告、内部文档等。"
        )
        self.knowledge_service_url = knowledge_service_url

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        搜索知识库

        Args:
            query: 搜索查询
            **kwargs: 其他参数（如 top_k）

        Returns:
            搜索结果
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
                        "summary": f"知识库中未找到关于'{query}'的相关内容。",
                        "documents": []
                    }

                # 构建摘要
                summary_parts = [f"在知识库中找到 {len(documents)} 条关于'{query}'的相关内容:\n"]
                for i, doc in enumerate(documents, 1):
                    summary_parts.append(
                        f"\n{i}. {doc.get('source', 'Unknown')}\n"
                        f"   内容: {doc.get('content', '')[:200]}...\n"
                        f"   相关度: {doc.get('score', 0):.2f}"
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
                "summary": f"搜索知识库'{query}'时出现错误: {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        """返回工具的 Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询内容"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回最相关的K个结果",
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
