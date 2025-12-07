"""
MCP 工具桥接器
将 MCP 服务包装为 Agent 可用的 Tool 接口
"""
from typing import Any, Dict, List, Optional
from .tool import Tool
from .mcp_services.financial_data_service import (
    FinancialDataService,
    get_financial_data_service
)
from .mcp_services.company_intelligence_service import (
    CompanyIntelligenceService,
    get_company_intelligence_service
)


class MCPFinancialDataTool(Tool):
    """
    MCP Financial Data Tool

    Get stock quotes, K-line, financial reports via MCP service
    """

    def __init__(self, service: FinancialDataService = None):
        super().__init__(
            name="mcp_financial_data",
            description="""Get financial market data via MCP service.

Features:
- Real-time stock quotes (action=quote)
- Historical K-line data (action=kline)
- Financial statements (action=financial)
- Market overview (action=overview)

Supported markets:
- A-shares (cn_a): Shanghai, Shenzhen, Beijing Stock Exchange
- HK stocks (cn_hk)
- US stocks (us)

Examples:
- Get Moutai quote: symbol=600519, action=quote
- Get Tencent K-line: symbol=00700, market=cn_hk, action=kline"""
        )
        self.service = service or get_financial_data_service()

    async def execute(
        self,
        symbol: str = None,
        action: str = "quote",
        market: str = None,
        period: str = "daily",
        limit: int = 100,
        report_type: str = "income",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行金融数据查询

        Args:
            symbol: 股票代码
            action: 操作类型 (quote/kline/financial/overview)
            market: 市场 (cn_a/cn_hk/us)
            period: K线周期 (daily/weekly/monthly)
            limit: K线数据条数
            report_type: 财报类型 (income/balance/cashflow)

        Returns:
            查询结果
        """
        try:
            if action == "quote":
                if not symbol:
                    return {"success": False, "error": "请提供股票代码", "summary": "获取行情需要指定股票代码"}
                return await self.service.get_quote(symbol, market)

            elif action == "kline":
                if not symbol:
                    return {"success": False, "error": "请提供股票代码", "summary": "获取K线需要指定股票代码"}
                return await self.service.get_kline(symbol, period, limit, market)

            elif action == "financial":
                if not symbol:
                    return {"success": False, "error": "请提供股票代码", "summary": "获取财报需要指定股票代码"}
                return await self.service.get_financial_report(symbol, report_type)

            elif action == "overview":
                return await self.service.get_market_overview(market or "cn_a")

            else:
                return {
                    "success": False,
                    "error": f"不支持的操作: {action}",
                    "summary": f"请使用支持的操作: quote, kline, financial, overview"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"MCP金融数据查询失败: {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码，如 600519(茅台), 00700(腾讯), AAPL(苹果)"
                    },
                    "action": {
                        "type": "string",
                        "description": "操作类型",
                        "enum": ["quote", "kline", "financial", "overview"],
                        "default": "quote"
                    },
                    "market": {
                        "type": "string",
                        "description": "市场类型 (不指定则自动检测)",
                        "enum": ["cn_a", "cn_hk", "us"]
                    },
                    "period": {
                        "type": "string",
                        "description": "K线周期 (仅action=kline时有效)",
                        "enum": ["daily", "weekly", "monthly"],
                        "default": "daily"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "K线数据条数 (仅action=kline时有效)",
                        "default": 100
                    },
                    "report_type": {
                        "type": "string",
                        "description": "财报类型 (仅action=financial时有效)",
                        "enum": ["income", "balance", "cashflow"],
                        "default": "income"
                    }
                },
                "required": []
            }
        }


class MCPCompanyIntelligenceTool(Tool):
    """
    MCP Company Intelligence Tool

    Get company registration, shareholders, executives, risk info via MCP service
    """

    def __init__(self, service: CompanyIntelligenceService = None):
        super().__init__(
            name="mcp_company_intelligence",
            description="""Get company information via MCP service.

Features:
- Company basic info (action=basic): Business registration, legal representative, registered capital
- Shareholder info (action=shareholders): Equity structure, shareholding ratio
- Executive info (action=executives): Management team, founders
- Legal litigation (action=legal): Lawsuits, enforcement, dishonesty
- Investment info (action=investments): External investments, subsidiaries
- Risk info (action=risk): Comprehensive risk assessment
- Full profile (action=profile): Complete company analysis

Examples:
- Query ByteDance basic info: company=ByteDance, action=basic
- Query Alibaba risk: company=Alibaba, action=risk"""
        )
        self.service = service or get_company_intelligence_service()

    async def execute(
        self,
        company: str = None,
        action: str = "basic",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行企业信息查询

        Args:
            company: 企业名称
            action: 操作类型 (basic/shareholders/executives/legal/investments/risk/profile)

        Returns:
            查询结果
        """
        if not company:
            return {
                "success": False,
                "error": "请提供企业名称",
                "summary": "企业信息查询需要指定企业名称"
            }

        try:
            if action == "basic":
                return await self.service.get_company_basic_info(company)

            elif action == "shareholders":
                return await self.service.get_shareholders(company)

            elif action == "executives":
                return await self.service.get_executives(company)

            elif action == "legal":
                return await self.service.get_legal_cases(company)

            elif action == "investments":
                return await self.service.get_investments(company)

            elif action == "risk":
                return await self.service.get_risk_info(company)

            elif action == "profile":
                return await self.service.get_full_profile(company)

            else:
                return {
                    "success": False,
                    "error": f"不支持的操作: {action}",
                    "summary": f"请使用支持的操作: basic, shareholders, executives, legal, investments, risk, profile"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"MCP企业信息查询失败: {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "企业名称，如 '字节跳动', '阿里巴巴集团'"
                    },
                    "action": {
                        "type": "string",
                        "description": "查询类型",
                        "enum": ["basic", "shareholders", "executives", "legal", "investments", "risk", "profile"],
                        "default": "basic"
                    }
                },
                "required": ["company"]
            }
        }


def create_mcp_tools() -> List[Tool]:
    """
    创建所有MCP工具实例

    Returns:
        MCP工具列表
    """
    return [
        MCPFinancialDataTool(),
        MCPCompanyIntelligenceTool()
    ]


def get_mcp_tool_for_agent(agent_role: str) -> List[Tool]:
    """
    根据Agent角色获取适合的MCP工具

    Args:
        agent_role: Agent角色名称

    Returns:
        适合该角色的MCP工具列表
    """
    tools = []

    # 金融数据工具 - 市场分析师和财务专家
    if agent_role in ["MarketAnalyst", "市场分析师", "FinancialExpert", "财务专家"]:
        tools.append(MCPFinancialDataTool())

    # 企业信息工具 - 团队评估师和风险评估师
    if agent_role in ["TeamEvaluator", "团队评估", "RiskAssessor", "风险评估"]:
        tools.append(MCPCompanyIntelligenceTool())

    return tools
