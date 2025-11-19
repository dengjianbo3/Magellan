"""
Fundamentals Agent - 基本面评估Agent
用于公开市场投资的基本面快速评估
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class FundamentalsAgent:
    """基本面评估Agent - 用于公开市场投资"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速评估基本面

        Args:
            target: 分析目标,包含:
                - ticker: 股票代码
                - company_name: 公司名称
                - industry: 行业

        Returns:
            基本面评估结果
        """
        ticker = target.get('ticker', '')
        company_name = target.get('company_name', '')
        industry = target.get('industry', '')

        # 搜索基本面信息
        search_results = await self._search_fundamentals(ticker, company_name)

        # 构建prompt
        prompt = self._build_prompt(
            ticker,
            company_name,
            industry,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result)

    async def _search_fundamentals(self, ticker: str, company_name: str) -> list:
        """搜索基本面信息"""
        if not ticker and not company_name:
            return []

        query = f"{ticker} 财报 业绩 营收 利润"

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
            print(f"[FundamentalsAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        ticker: str,
        company_name: str,
        industry: str,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到基本面相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        prompt = f"""你是一位资深的基本面分析师,专注于上市公司财务质量评估。

**股票信息**:
- 代码: {ticker}
- 公司: {company_name}
- 行业: {industry}

**搜索结果**:
{search_text}

**任务**: 快速评估基本面,关注:
1. 营收增长趋势
2. 利润率水平
3. ROE(净资产收益率)
4. 财务稳健性

**输出格式**(严格JSON):
{{
  "score": 0.80,
  "revenue_growth": "营收同比增长25%,增速稳健",
  "profit_margin": "毛利率45%,净利率18%,盈利能力强",
  "roe": "ROE 20%,高于行业平均",
  "financial_stability": "资产负债率适中,现金流健康",
  "concerns": ["原材料成本上涨压力"],
  "summary": "基本面优秀,盈利能力强劲"
}}

注意:
- score: 0-1评分
- 数据尽量具体,包含数字
- 如果数据不足,在concerns中说明
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "revenue_growth": "数据不足",
                "profit_margin": "数据不足",
                "roe": "数据不足",
                "financial_stability": "待评估",
                "concerns": ["自动分析失败"],
                "summary": "基本面评估未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "revenue_growth": llm_result.get("revenue_growth", "待评估"),
            "profit_margin": llm_result.get("profit_margin", "待评估"),
            "roe": llm_result.get("roe", "待评估"),
            "financial_stability": llm_result.get("financial_stability", "待评估"),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "基本面评估完成")
        }
