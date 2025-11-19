"""
Financial Health Check Agent - 财务健康检查Agent
用于成长期投资的财务快速评估
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class FinancialHealthAgent:
    """财务健康评估Agent - 用于成长期投资"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速评估财务健康度

        Args:
            target: 分析目标,包含:
                - company_name: 公司名称
                - stage: 融资阶段
                - annual_revenue: 年收入(可选)
                - growth_rate: 增长率(可选)

        Returns:
            财务健康评估结果
        """
        company_name = target.get('company_name', '')
        annual_revenue = target.get('annual_revenue')
        growth_rate = target.get('growth_rate')
        stage = target.get('stage', '')

        # 搜索财务相关信息
        search_results = await self._search_financial_info(company_name, stage)

        # 构建prompt
        prompt = self._build_prompt(
            company_name,
            stage,
            annual_revenue,
            growth_rate,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result)

    async def _search_financial_info(self, company_name: str, stage: str) -> list:
        """搜索财务信息"""
        if not company_name:
            return []

        query = f"{company_name} {stage} 融资 收入 财务 2024"

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
            print(f"[FinancialHealthAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        company_name: str,
        stage: str,
        annual_revenue,
        growth_rate,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到财务相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        revenue_text = f"{annual_revenue}万元" if annual_revenue else "未提供"
        growth_text = f"{growth_rate}%" if growth_rate else "未知"

        prompt = f"""你是一位资深的财务分析师,专注于成长期公司的财务健康评估。

**公司信息**:
- 公司: {company_name}
- 阶段: {stage}
- 年收入: {revenue_text}
- 增长率: {growth_text}

**搜索结果**:
{search_text}

**任务**: 快速评估财务健康度,关注:
1. 收入规模是否与融资阶段匹配
2. 现金流状况
3. 盈利能力或单位经济模型
4. 资金使用效率

**输出格式**(严格JSON):
{{
  "score": 0.75,
  "revenue_assessment": "收入规模{revenue_text},符合{stage}阶段预期",
  "cash_flow": "需关注现金流",
  "profitability": "单位经济模型健康",
  "concerns": ["烧钱速度较快"],
  "summary": "财务健康度良好,但需关注现金流"
}}

注意:
- score: 0-1评分
- 如果收入未提供,在concerns中指出"缺少财务数据"
- 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "revenue_assessment": "数据不足",
                "cash_flow": "待评估",
                "profitability": "待评估",
                "concerns": ["自动分析失败"],
                "summary": "财务评估未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "revenue_assessment": llm_result.get("revenue_assessment", "待评估"),
            "cash_flow": llm_result.get("cash_flow", "待评估"),
            "profitability": llm_result.get("profitability", "待评估"),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "财务评估完成")
        }
