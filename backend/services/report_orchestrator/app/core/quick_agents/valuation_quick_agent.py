"""
Valuation Quick Agent - 估值快速评估Agent
用于公开市场投资的估值快速评估
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class ValuationQuickAgent:
    """估值快速评估Agent - 用于公开市场投资"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速评估股票估值

        Args:
            target: 分析目标,包含:
                - ticker: 股票代码
                - company_name: 公司名称
                - current_price: 当前价格(可选)

        Returns:
            估值评估结果
        """
        ticker = target.get('ticker', '')
        company_name = target.get('company_name', '')
        current_price = target.get('current_price')

        # 搜索估值信息
        search_results = await self._search_valuation_info(ticker, company_name)

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

    async def _search_valuation_info(self, ticker: str, company_name: str) -> list:
        """搜索估值信息"""
        if not ticker and not company_name:
            return []

        query = f"{ticker} PE PB 估值 价格目标"

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
            print(f"[ValuationQuickAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        ticker: str,
        company_name: str,
        current_price,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到估值相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        price_text = f"{current_price}元" if current_price else "未提供"

        prompt = f"""你是一位资深的股票估值分析师,专注于快速评估上市公司估值水平。

**股票信息**:
- 代码: {ticker}
- 公司: {company_name}
- 当前价格: {price_text}

**搜索结果**:
{search_text}

**任务**: 快速评估估值水平,关注:
1. PE/PB ratio 相对历史水平
2. 相对行业平均水平
3. 绝对估值合理性
4. 机构目标价

**输出格式**(严格JSON):
{{
  "score": 0.70,
  "pe_ratio": "PE 25倍,略高于行业均值",
  "pb_ratio": "PB 3.5倍,处于合理区间",
  "valuation_level": "fair",
  "target_price": "机构一致目标价120元",
  "concerns": ["估值略偏高"],
  "summary": "估值处于合理偏高水平"
}}

注意:
- score: 0-1评分(越低越高估)
- valuation_level: "high"(高估)/"fair"(合理)/"low"(低估)
- 如果数据不足,在concerns中说明
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "pe_ratio": "数据不足",
                "pb_ratio": "数据不足",
                "valuation_level": "unknown",
                "target_price": "无",
                "concerns": ["自动分析失败"],
                "summary": "估值评估未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "pe_ratio": llm_result.get("pe_ratio", "待评估"),
            "pb_ratio": llm_result.get("pb_ratio", "待评估"),
            "valuation_level": llm_result.get("valuation_level", "unknown"),
            "target_price": llm_result.get("target_price", "无"),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "估值评估完成")
        }
