"""
MCP Tools for Roundtable Discussion Agents
为圆桌讨论专家提供的 MCP 工具集
"""
import os
import httpx
from typing import Any, Dict, List, Optional
from .tool import Tool


class TavilySearchTool(Tool):
    """
    Tavily 网络搜索工具 (MCP方式)

    通过 Web Search Service 调用 Tavily API
    """

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010",
        max_results: int = 3
    ):
        """
        Args:
            web_search_url: Web Search Service 的 URL
            max_results: 最大搜索结果数
        """
        super().__init__(
            name="tavily_search",
            description="搜索互联网获取最新信息、新闻、市场数据等。适用于需要实时信息、行业动态、公司新闻的场景。"
        )
        self.web_search_url = web_search_url
        self.max_results = max_results

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        执行网络搜索

        Args:
            query: 搜索查询
            **kwargs: 其他参数（如 max_results）

        Returns:
            搜索结果
        """
        max_results = kwargs.get("max_results", self.max_results)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.web_search_url}/search",
                    json={
                        "query": query,
                        "max_results": max_results
                    }
                )
                response.raise_for_status()
                result = response.json()

                # 格式化结果为易读的文本
                results = result.get("results", [])
                if not results:
                    return {
                        "success": True,
                        "summary": f"未找到关于'{query}'的相关信息",
                        "results": []
                    }

                # 构建摘要
                summary_parts = [f"找到 {len(results)} 条关于'{query}'的搜索结果:\n"]
                for i, res in enumerate(results, 1):
                    summary_parts.append(
                        f"\n{i}. {res['title']}\n"
                        f"   来源: {res['url']}\n"
                        f"   内容: {res['content'][:200]}..."
                    )

                return {
                    "success": True,
                    "summary": "".join(summary_parts),
                    "results": results,
                    "query": query
                }

        except Exception as e:
            print(f"[TavilySearchTool] Search failed: {e}")
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

    elif agent_role in ["FinancialExpert", "财务专家"]:
        # 财务专家需要公开数据和财务报表
        tools.append(PublicDataTool())
        tools.append(YahooFinanceTool())  # 添加财报数据工具
        tools.append(SECEdgarTool())      # 添加SEC官方财报工具

    elif agent_role in ["TeamEvaluator", "团队评估"]:
        # 团队评估专家需要搜索团队背景
        pass  # 主要使用 Tavily 搜索

    elif agent_role in ["RiskAssessor", "风险评估"]:
        # 风险评估专家需要搜索风险信息和查看SEC披露的风险因素
        tools.append(SECEdgarTool())  # 添加SEC工具查看8-K重大事件和10-K风险因素

    elif agent_role in ["TechSpecialist", "技术专家"]:
        # 技术专家主要使用搜索工具
        pass  # 主要使用 Tavily 搜索

    elif agent_role in ["LegalAdvisor", "法律顾问"]:
        # 法律顾问主要使用搜索工具查询法规
        pass  # 主要使用 Tavily 搜索

    # 知识库工具 - 所有专家都可以使用
    tools.append(KnowledgeBaseTool())

    return tools
