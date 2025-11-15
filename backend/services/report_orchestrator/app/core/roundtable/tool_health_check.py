"""
Tool Health Check System
工具健康检查系统

在启动时验证所有MCP工具是否可用
"""
import asyncio
import logging
import os
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)


class ToolHealthCheck:
    """工具健康检查"""

    @staticmethod
    async def check_tavily() -> Dict[str, Any]:
        """检查Tavily Search是否可用"""
        try:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                return {
                    "status": "unavailable",
                    "reason": "TAVILY_API_KEY not configured"
                }

            # 尝试简单搜索测试
            from ..roundtable.mcp_tools import TavilySearchTool
            tool = TavilySearchTool()
            result = await tool.execute(query="test", max_results=1)

            if result.get("success"):
                return {"status": "available", "details": "API key valid"}
            else:
                return {
                    "status": "error",
                    "reason": result.get("error", "Unknown error")
                }

        except Exception as e:
            return {"status": "error", "reason": str(e)}

    @staticmethod
    async def check_yahoo_finance() -> Dict[str, Any]:
        """检查Yahoo Finance是否可用"""
        try:
            from ..roundtable.mcp_tools import YahooFinanceTool
            tool = YahooFinanceTool()

            # 测试获取Apple股价
            result = await tool.execute(symbol="AAPL", action="price")

            if result.get("success"):
                return {"status": "available", "details": "Can fetch stock data"}
            else:
                return {
                    "status": "error",
                    "reason": result.get("error", "Unknown error")
                }

        except Exception as e:
            return {"status": "error", "reason": str(e)}

    @staticmethod
    async def check_sec_edgar() -> Dict[str, Any]:
        """检查SEC EDGAR是否可用"""
        try:
            # 测试访问SEC.gov
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://www.sec.gov",
                    headers={"User-Agent": "Magellan AI test@example.com"}
                )

                if response.status_code == 200:
                    return {
                        "status": "available",
                        "details": "SEC.gov reachable, 30 tickers supported"
                    }
                else:
                    return {
                        "status": "degraded",
                        "reason": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            return {"status": "error", "reason": str(e)}

    @staticmethod
    async def check_knowledge_base() -> Dict[str, Any]:
        """检查Knowledge Base是否可用"""
        try:
            # 检查Qdrant连接
            qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{qdrant_url}/collections")

                if response.status_code == 200:
                    data = response.json()
                    collections = data.get("result", {}).get("collections", [])
                    kb_exists = any(c.get("name") == "knowledge_base" for c in collections)

                    if kb_exists:
                        return {
                            "status": "available",
                            "details": "Knowledge base collection exists"
                        }
                    else:
                        return {
                            "status": "degraded",
                            "reason": "Knowledge base collection not found"
                        }
                else:
                    return {
                        "status": "error",
                        "reason": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            return {"status": "error", "reason": str(e)}

    @staticmethod
    async def check_llm_gateway() -> Dict[str, Any]:
        """检查LLM Gateway是否可用"""
        try:
            llm_gateway_url = os.getenv("LLM_GATEWAY_URL", "http://llm_gateway:8003")
            async with httpx.AsyncClient(timeout=5.0) as client:
                # 尝试访问health endpoint
                response = await client.get(f"{llm_gateway_url}/health")

                if response.status_code == 200:
                    return {
                        "status": "available",
                        "details": "LLM Gateway healthy"
                    }
                else:
                    return {
                        "status": "degraded",
                        "reason": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            return {"status": "error", "reason": str(e)}

    @staticmethod
    async def check_all_tools() -> Dict[str, Dict[str, Any]]:
        """检查所有工具健康状态"""
        logger.info("[ToolHealthCheck] Starting health check for all tools...")

        # 并行检查所有工具
        results = await asyncio.gather(
            ToolHealthCheck.check_tavily(),
            ToolHealthCheck.check_yahoo_finance(),
            ToolHealthCheck.check_sec_edgar(),
            ToolHealthCheck.check_knowledge_base(),
            ToolHealthCheck.check_llm_gateway(),
            return_exceptions=True
        )

        tool_names = [
            "tavily_search",
            "yahoo_finance",
            "sec_edgar",
            "knowledge_base",
            "llm_gateway"
        ]

        health_status = {}
        for i, (tool_name, result) in enumerate(zip(tool_names, results)):
            if isinstance(result, Exception):
                health_status[tool_name] = {
                    "status": "error",
                    "reason": f"Health check exception: {str(result)}"
                }
            else:
                health_status[tool_name] = result

        # 记录结果
        for tool_name, status in health_status.items():
            status_str = status.get("status", "unknown")
            if status_str == "available":
                logger.info(f"[ToolHealthCheck] ✅ {tool_name}: Available - {status.get('details', '')}")
            elif status_str == "degraded":
                logger.warning(f"[ToolHealthCheck] ⚠️  {tool_name}: Degraded - {status.get('reason', '')}")
            else:
                logger.error(f"[ToolHealthCheck] ❌ {tool_name}: Unavailable - {status.get('reason', '')}")

        # 统计
        available = sum(1 for s in health_status.values() if s.get("status") == "available")
        total = len(health_status)
        logger.info(f"[ToolHealthCheck] Health check complete: {available}/{total} tools available")

        return health_status


# 便捷函数
async def run_health_check() -> Dict[str, Dict[str, Any]]:
    """运行健康检查并返回结果"""
    return await ToolHealthCheck.check_all_tools()


if __name__ == "__main__":
    # 测试脚本
    async def main():
        print("\n🏥 Running Tool Health Check...\n")
        results = await run_health_check()

        print("\n" + "="*80)
        print("HEALTH CHECK RESULTS")
        print("="*80)

        for tool_name, status in results.items():
            status_icon = {
                "available": "✅",
                "degraded": "⚠️ ",
                "error": "❌",
                "unavailable": "❌"
            }.get(status.get("status"), "❓")

            print(f"\n{status_icon} {tool_name.upper()}")
            print(f"   Status: {status.get('status')}")
            if "details" in status:
                print(f"   Details: {status['details']}")
            if "reason" in status:
                print(f"   Reason: {status['reason']}")

        print("\n" + "="*80)

    asyncio.run(main())
