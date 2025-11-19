"""
Growth Potential Agent - 增长潜力评估Agent
用于成长期投资的增长潜力快速评估
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class GrowthPotentialAgent:
    """增长潜力评估Agent - 用于成长期投资"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速评估增长潜力

        Args:
            target: 分析目标,包含:
                - company_name: 公司名称
                - stage: 融资阶段
                - industry: 行业
                - description: 公司描述

        Returns:
            增长潜力评估结果
        """
        company_name = target.get('company_name', '')
        industry = target.get('industry', '')
        description = target.get('description', '')

        # 搜索增长相关信息
        search_results = await self._search_growth_info(company_name)

        # 构建prompt
        prompt = self._build_prompt(
            company_name,
            industry,
            description,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result)

    async def _search_growth_info(self, company_name: str) -> list:
        """搜索增长相关信息"""
        if not company_name:
            return []

        query = f"{company_name} 增长 扩张 市场份额"

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
            print(f"[GrowthPotentialAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        company_name: str,
        industry: str,
        description: str,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到增长相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        prompt = f"""你是一位资深的成长型投资分析师,专注于评估公司的增长潜力。

**公司信息**:
- 公司: {company_name}
- 行业: {industry}
- 描述: {description}

**搜索结果**:
{search_text}

**任务**: 快速评估增长潜力,关注:
1. 增长驱动因素(产品创新、市场扩张等)
2. 市场扩张能力和速度
3. 增长的可持续性
4. 规模化能力

**输出格式**(严格JSON):
{{
  "score": 0.80,
  "growth_drivers": ["产品创新强", "市场需求旺盛", "运营效率高"],
  "scalability": "规模化能力强,边际成本递减",
  "sustainability": "增长可持续,有护城河",
  "concerns": ["依赖单一市场"],
  "summary": "增长潜力大,具备规模化基础"
}}

注意:
- score: 0-1评分
- growth_drivers: 增长驱动因素列表(2-3条)
- scalability: 规模化能力描述
- sustainability: 可持续性评估
- concerns: 关注点(1-2条)
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "growth_drivers": [],
                "scalability": "待评估",
                "sustainability": "待评估",
                "concerns": ["自动分析失败"],
                "summary": "增长潜力评估未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "growth_drivers": llm_result.get("growth_drivers", []),
            "scalability": llm_result.get("scalability", "待评估"),
            "sustainability": llm_result.get("sustainability", "待评估"),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "增长潜力评估完成")
        }
