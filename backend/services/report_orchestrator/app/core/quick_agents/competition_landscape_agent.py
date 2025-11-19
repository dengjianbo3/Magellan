"""
Competition Landscape Agent - 竞争格局分析Agent
用于行业研究的竞争格局快速分析
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class CompetitionLandscapeAgent:
    """竞争格局分析Agent - 用于行业研究"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速分析竞争格局

        Args:
            target: 分析目标,包含:
                - industry_name: 行业名称
                - region: 地区(可选)
                - focus_segment: 细分领域(可选)

        Returns:
            竞争格局分析结果
        """
        industry_name = target.get('industry_name', '')
        region = target.get('region', '中国')
        focus_segment = target.get('focus_segment', '')

        # 搜索竞争格局信息
        search_results = await self._search_competition(industry_name, region)

        # 构建prompt
        prompt = self._build_prompt(
            industry_name,
            region,
            focus_segment,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result)

    async def _search_competition(self, industry_name: str, region: str) -> list:
        """搜索竞争格局信息"""
        if not industry_name:
            return []

        query = f"{industry_name} 竞争格局 主要玩家 市场份额 {region}"

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
            print(f"[CompetitionLandscapeAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        industry_name: str,
        region: str,
        focus_segment: str,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到竞争格局相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        segment_text = f" - 细分领域: {focus_segment}" if focus_segment else ""

        prompt = f"""你是一位资深的行业竞争分析师,专注于竞争格局和市场结构分析。

**研究对象**:
- 行业: {industry_name}
- 地区: {region}{segment_text}

**搜索结果**:
{search_text}

**任务**: 快速分析竞争格局,关注:
1. 主要玩家和市场份额
2. 市场集中度(CR3/CR5/HHI)
3. 进入壁垒高低
4. 竞争态势(蓝海/红海)

**输出格式**(严格JSON):
{{
  "score": 0.70,
  "top_players": [
    {{"name": "公司A", "market_share": "30%", "strength": "技术领先"}},
    {{"name": "公司B", "market_share": "20%", "strength": "渠道优势"}},
    {{"name": "公司C", "market_share": "15%", "strength": "价格优势"}}
  ],
  "market_concentration": "CR3=65%,市场较为集中,寡头竞争格局",
  "entry_barriers": "进入壁垒中等,需要技术和资金投入",
  "competitive_intensity": "竞争激烈,价格战频繁",
  "concerns": ["竞争过度,利润率承压"],
  "summary": "市场集中度较高,头部效应明显"
}}

注意:
- score: 0-1评分(基于市场吸引力,竞争越激烈分越低)
- top_players: 列出前3-5名玩家
- 市场集中度用CR3或CR5表示
- entry_barriers影响新进入者威胁
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "top_players": [],
                "market_concentration": "数据不足",
                "entry_barriers": "待评估",
                "competitive_intensity": "待评估",
                "concerns": ["自动分析失败"],
                "summary": "竞争格局分析未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "top_players": llm_result.get("top_players", []),
            "market_concentration": llm_result.get("market_concentration", "待评估"),
            "entry_barriers": llm_result.get("entry_barriers", "待评估"),
            "competitive_intensity": llm_result.get("competitive_intensity", "待评估"),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "竞争格局分析完成")
        }
