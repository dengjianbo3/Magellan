"""
Market Quick Check Agent - 市场机会快速评估Agent
用于快速判断模式下的市场机会分析
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class MarketQuickAgent:
    """市场快速评估Agent - 用于快速判断市场机会"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速评估市场机会

        Args:
            target: 分析目标信息

        Returns:
            市场评估结果
        """
        company_name = target.get('company_name', '')
        description = target.get('description', '')
        industry = target.get('industry', '')

        # Step 1: 搜索市场信息
        search_results = await self._search_market_info(company_name, description, industry)

        # Step 2: 构建prompt并调用LLM
        prompt = self._build_prompt(company_name, description, industry, search_results)

        # Step 3: 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        # Step 4: 标准化结果
        return self._normalize_result(result)

    async def _search_market_info(
        self,
        company_name: str,
        description: str,
        industry: str
    ) -> list:
        """搜索市场相关信息"""
        # 构建搜索查询
        if industry:
            query = f"{industry} 市场规模 趋势 2024"
        else:
            query = f"{company_name} {description} 市场 赛道"

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
            print(f"[MarketQuickAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        company_name: str,
        description: str,
        industry: str,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到相关市场数据"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        prompt = f"""你是一位资深的行业分析师,专注于早期投资的市场评估。

**项目信息**:
- 公司: {company_name}
- 描述: {description}
- 行业: {industry if industry else '未知'}

**市场搜索结果**:
{search_text}

**任务**: 快速判断市场机会,关注:
1. 市场规模是否足够大 (TAM > $1B)
2. 市场增长趋势
3. 是否有巨头垄断
4. 当前痛点是否明确

**输出格式**(严格JSON):
{{
  "market_attractiveness": 0.70,
  "tam_estimate": "$5B+",
  "growth_trend": "快速增长",
  "pain_points": ["现有解决方案复杂", "成本高"],
  "threats": ["大厂可能进入"],
  "summary": "市场规模大且增长快,但需关注竞争"
}}

注意:
- market_attractiveness: 0-1评分
- tam_estimate: TAM估值(如"$5B+")
- 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "market_attractiveness": 0.5,
                "tam_estimate": "未知",
                "growth_trend": "待评估",
                "pain_points": [],
                "threats": ["自动分析失败"],
                "summary": "市场评估未完成"
            }

        return {
            "score": llm_result.get("market_attractiveness", 0.5),
            "market_attractiveness": llm_result.get("market_attractiveness", 0.5),
            "tam_estimate": llm_result.get("tam_estimate", "未知"),
            "growth_trend": llm_result.get("growth_trend", "待评估"),
            "pain_points": llm_result.get("pain_points", []),
            "threats": llm_result.get("threats", []),
            "summary": llm_result.get("summary", "市场评估完成")
        }
