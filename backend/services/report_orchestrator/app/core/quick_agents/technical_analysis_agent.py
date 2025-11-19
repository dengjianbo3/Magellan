"""
Technical Analysis Agent - 技术面评估Agent
用于公开市场投资的技术面快速评估
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class TechnicalAnalysisAgent:
    """技术面评估Agent - 用于公开市场投资"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速评估技术面

        Args:
            target: 分析目标,包含:
                - ticker: 股票代码
                - company_name: 公司名称
                - current_price: 当前价格(可选)

        Returns:
            技术面评估结果
        """
        ticker = target.get('ticker', '')
        company_name = target.get('company_name', '')
        current_price = target.get('current_price')

        # 搜索技术面信息
        search_results = await self._search_technical_info(ticker, company_name)

        # 构建prompt
        prompt = self._build_prompt(
            ticker,
            company_name,
            current_price,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result)

    async def _search_technical_info(self, ticker: str, company_name: str) -> list:
        """搜索技术面信息"""
        if not ticker and not company_name:
            return []

        query = f"{ticker} 技术分析 股价走势"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.web_search_url}/search",
                    json={"query": query, "max_results": 3}
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("results", [])
        except Exception as e:
            print(f"[TechnicalAnalysisAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        ticker: str,
        company_name: str,
        current_price,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到技术面相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        price_text = f"{current_price}元" if current_price else "未提供"

        prompt = f"""你是一位资深的技术分析师,专注于股票走势和技术指标分析。

**股票信息**:
- 代码: {ticker}
- 公司: {company_name}
- 当前价格: {price_text}

**搜索结果**:
{search_text}

**任务**: 快速评估技术面,关注:
1. 价格趋势(上升/下降/横盘)
2. 支撑位和阻力位
3. 成交量和动量
4. 技术指标信号

**输出格式**(严格JSON):
{{
  "score": 0.75,
  "trend": "up",
  "support_level": "支撑位100元",
  "resistance_level": "阻力位120元",
  "momentum": "MACD金叉,动量向上",
  "volume_analysis": "成交量放大,资金流入",
  "concerns": ["短期涨幅较大,注意回调"],
  "summary": "技术面偏强,趋势向上"
}}

注意:
- score: 0-1评分
- trend: "up"(上升)/"down"(下降)/"sideways"(横盘)
- 尽量提供具体价位
- 如果数据不足,在concerns中说明
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "trend": "unknown",
                "support_level": "未知",
                "resistance_level": "未知",
                "momentum": "待评估",
                "volume_analysis": "待评估",
                "concerns": ["自动分析失败"],
                "summary": "技术面评估未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "trend": llm_result.get("trend", "unknown"),
            "support_level": llm_result.get("support_level", "未知"),
            "resistance_level": llm_result.get("resistance_level", "未知"),
            "momentum": llm_result.get("momentum", "待评估"),
            "volume_analysis": llm_result.get("volume_analysis", "待评估"),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "技术面评估完成")
        }
