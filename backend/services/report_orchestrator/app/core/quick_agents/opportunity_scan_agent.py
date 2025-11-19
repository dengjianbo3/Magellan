"""
Opportunity Scan Agent - 机会扫描Agent
用于行业研究的投资机会快速扫描
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class OpportunityScanAgent:
    """机会扫描Agent - 用于行业研究"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速扫描投资机会

        Args:
            target: 分析目标,包含:
                - industry_name: 行业名称
                - investment_stage: 投资阶段偏好(可选)
                - focus_area: 关注领域(可选)

        Returns:
            机会扫描结果
        """
        industry_name = target.get('industry_name', '')
        investment_stage = target.get('investment_stage', '')
        focus_area = target.get('focus_area', '')

        # 搜索投资机会信息
        search_results = await self._search_opportunities(industry_name)

        # 构建prompt
        prompt = self._build_prompt(
            industry_name,
            investment_stage,
            focus_area,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result)

    async def _search_opportunities(self, industry_name: str) -> list:
        """搜索投资机会信息"""
        if not industry_name:
            return []

        query = f"{industry_name} 投资机会 细分赛道 创新"

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
            print(f"[OpportunityScanAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        industry_name: str,
        investment_stage: str,
        focus_area: str,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到投资机会相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        stage_text = f" - 投资阶段: {investment_stage}" if investment_stage else ""
        focus_text = f" - 关注领域: {focus_area}" if focus_area else ""

        prompt = f"""你是一位资深的投资机会分析师,专注于发现行业中的投资机会。

**研究对象**:
- 行业: {industry_name}{stage_text}{focus_text}

**搜索结果**:
{search_text}

**任务**: 快速扫描投资机会,关注:
1. 有潜力的细分赛道
2. 创新突破点
3. 价值洼地
4. 投资时机

**输出格式**(严格JSON):
{{
  "score": 0.80,
  "opportunities": [
    {{
      "name": "AI+医疗诊断",
      "potential": "high",
      "description": "AI辅助诊断市场快速增长,渗透率低",
      "rationale": "技术成熟,政策支持,刚需市场"
    }},
    {{
      "name": "智能硬件出海",
      "potential": "medium",
      "description": "国内供应链优势,海外需求旺盛",
      "rationale": "成本优势,品牌建设机会"
    }}
  ],
  "sub_sectors": ["AI医疗", "智能硬件", "SaaS软件"],
  "innovations": ["大模型应用", "边缘计算", "碳中和技术"],
  "timing_assessment": "当前处于布局窗口期,未来1-2年爆发",
  "concerns": ["竞争可能加剧"],
  "summary": "多个细分赛道有投资价值,建议重点关注AI医疗"
}}

注意:
- score: 0-1评分(基于机会质量和数量)
- opportunities: 列出2-3个具体机会
- potential: "high"/"medium"/"low"
- sub_sectors: 有潜力的细分赛道
- innovations: 创新突破点
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "opportunities": [],
                "sub_sectors": [],
                "innovations": [],
                "timing_assessment": "待评估",
                "concerns": ["自动分析失败"],
                "summary": "机会扫描未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "opportunities": llm_result.get("opportunities", []),
            "sub_sectors": llm_result.get("sub_sectors", []),
            "innovations": llm_result.get("innovations", []),
            "timing_assessment": llm_result.get("timing_assessment", "待评估"),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "机会扫描完成")
        }
