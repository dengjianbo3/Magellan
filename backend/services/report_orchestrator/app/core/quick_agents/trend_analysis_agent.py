"""
Trend Analysis Agent - 趋势分析Agent
用于行业研究的趋势快速分析
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class TrendAnalysisAgent:
    """趋势分析Agent - 用于行业研究"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速分析行业趋势

        Args:
            target: 分析目标,包含:
                - industry_name: 行业名称
                - time_horizon: 时间跨度(可选,如"短期"、"中长期")

        Returns:
            趋势分析结果
        """
        industry_name = target.get('industry_name', '')
        time_horizon = target.get('time_horizon', '中长期')

        # 搜索趋势信息
        search_results = await self._search_trends(industry_name)

        # 构建prompt
        prompt = self._build_prompt(
            industry_name,
            time_horizon,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result)

    async def _search_trends(self, industry_name: str) -> list:
        """搜索趋势信息"""
        if not industry_name:
            return []

        query = f"{industry_name} 趋势 技术路线 政策"

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
            print(f"[TrendAnalysisAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        industry_name: str,
        time_horizon: str,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到趋势相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        prompt = f"""你是一位资深的行业趋势分析师,专注于识别关键趋势和未来方向。

**研究对象**:
- 行业: {industry_name}
- 时间跨度: {time_horizon}

**搜索结果**:
{search_text}

**任务**: 快速分析行业趋势,关注:
1. 关键趋势(技术、消费、商业模式等)
2. 技术发展方向
3. 政策支持力度
4. 驱动因素和阻碍因素

**输出格式**(严格JSON):
{{
  "score": 0.85,
  "key_trends": [
    {{"trend": "AI驱动自动化", "impact": "high", "description": "AI技术加速渗透,提升效率"}},
    {{"trend": "订阅制普及", "impact": "medium", "description": "商业模式向SaaS转型"}},
    {{"trend": "监管趋严", "impact": "medium", "description": "合规成本上升"}}
  ],
  "tech_direction": "云原生、边缘计算成为主流技术路线",
  "policy_support": "政府大力扶持,出台多项补贴政策",
  "drivers": ["技术突破", "需求增长", "政策支持"],
  "barriers": ["成本较高", "人才短缺"],
  "summary": "行业处于上升期,多重利好因素"
}}

注意:
- score: 0-1评分(基于趋势积极性)
- key_trends: 列出2-4个关键趋势
- impact: "high"/"medium"/"low"
- 区分驱动因素和阻碍因素
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "key_trends": [],
                "tech_direction": "待评估",
                "policy_support": "待评估",
                "drivers": [],
                "barriers": [],
                "summary": "趋势分析未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "key_trends": llm_result.get("key_trends", []),
            "tech_direction": llm_result.get("tech_direction", "待评估"),
            "policy_support": llm_result.get("policy_support", "待评估"),
            "drivers": llm_result.get("drivers", []),
            "barriers": llm_result.get("barriers", []),
            "summary": llm_result.get("summary", "趋势分析完成")
        }
