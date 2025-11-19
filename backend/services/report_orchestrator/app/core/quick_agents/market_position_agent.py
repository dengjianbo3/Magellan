"""
Market Position Agent - 市场地位评估Agent
用于成长期投资的市场地位快速评估
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class MarketPositionAgent:
    """市场地位评估Agent - 用于成长期投资"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速评估市场地位

        Args:
            target: 分析目标,包含:
                - company_name: 公司名称
                - industry: 行业
                - competitors: 竞争对手(可选)

        Returns:
            市场地位评估结果
        """
        company_name = target.get('company_name', '')
        industry = target.get('industry', '')
        competitors = target.get('competitors', [])

        # 搜索市场地位信息
        search_results = await self._search_market_position(company_name)

        # 构建prompt
        prompt = self._build_prompt(
            company_name,
            industry,
            competitors,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result)

    async def _search_market_position(self, company_name: str) -> list:
        """搜索市场地位信息"""
        if not company_name:
            return []

        query = f"{company_name} 竞争对手 市场地位 行业排名"

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
            print(f"[MarketPositionAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        company_name: str,
        industry: str,
        competitors: list,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到市场地位相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        competitors_text = "未提供" if not competitors else ", ".join(competitors)

        prompt = f"""你是一位资深的行业分析师,专注于评估公司的市场竞争地位。

**公司信息**:
- 公司: {company_name}
- 行业: {industry}
- 主要竞争对手: {competitors_text}

**搜索结果**:
{search_text}

**任务**: 快速评估市场地位,关注:
1. 竞争优势(技术、品牌、成本等)
2. 市场份额和排名
3. 品牌影响力
4. 竞争壁垒

**输出格式**(严格JSON):
{{
  "score": 0.75,
  "competitive_advantage": "技术领先,用户体验好",
  "market_share": "细分市场前3名,份额约15%",
  "brand_strength": "品牌认知度较高,口碑好",
  "barriers": ["技术壁垒", "网络效应"],
  "concerns": ["大厂竞争压力"],
  "summary": "市场地位稳固,有一定竞争优势"
}}

注意:
- score: 0-1评分
- competitive_advantage: 竞争优势描述
- market_share: 市场份额估计
- brand_strength: 品牌实力评估
- barriers: 竞争壁垒列表(1-3条)
- concerns: 关注点(1-2条)
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "competitive_advantage": "待评估",
                "market_share": "未知",
                "brand_strength": "待评估",
                "barriers": [],
                "concerns": ["自动分析失败"],
                "summary": "市场地位评估未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "competitive_advantage": llm_result.get("competitive_advantage", "待评估"),
            "market_share": llm_result.get("market_share", "未知"),
            "brand_strength": llm_result.get("brand_strength", "待评估"),
            "barriers": llm_result.get("barriers", []),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "市场地位评估完成")
        }
