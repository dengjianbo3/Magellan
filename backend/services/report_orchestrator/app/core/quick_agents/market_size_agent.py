"""
Market Size Agent - 市场规模评估Agent
用于行业研究的市场规模快速评估
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class MarketSizeAgent:
    """市场规模评估Agent - 用于行业研究"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速评估市场规模

        Args:
            target: 分析目标,包含:
                - industry_name: 行业名称
                - region: 地区(可选,如"中国"、"全球")
                - year: 年份(可选)

        Returns:
            市场规模评估结果
        """
        industry_name = target.get('industry_name', '')
        region = target.get('region', '中国')
        year = target.get('year', '2024')

        # 搜索市场规模信息
        search_results = await self._search_market_size(industry_name, region, year)

        # 构建prompt
        prompt = self._build_prompt(
            industry_name,
            region,
            year,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result)

    async def _search_market_size(self, industry_name: str, region: str, year: str) -> list:
        """搜索市场规模信息"""
        if not industry_name:
            return []

        query = f"{industry_name} 市场规模 TAM 增长率 {region} {year}"

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
            print(f"[MarketSizeAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        industry_name: str,
        region: str,
        year: str,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到市场规模相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        prompt = f"""你是一位资深的行业研究分析师,专注于市场规模和增长潜力评估。

**研究对象**:
- 行业: {industry_name}
- 地区: {region}
- 年份: {year}

**搜索结果**:
{search_text}

**任务**: 快速评估市场规模,关注:
1. TAM(总可及市场规模)
2. SAM(可服务市场规模)
3. 市场增长率(CAGR)
4. 市场成熟度

**输出格式**(严格JSON):
{{
  "score": 0.85,
  "tam": "全球市场规模1000亿美元,中国市场300亿美元",
  "sam": "可服务市场约150亿美元",
  "growth_rate": "年复合增长率25%,处于高速增长期",
  "market_maturity": "市场处于成长期,渗透率约20%",
  "concerns": ["市场竞争加剧"],
  "summary": "市场规模大,增长快速,投资价值高"
}}

注意:
- score: 0-1评分(基于市场吸引力)
- 尽量提供具体数字和来源年份
- TAM和SAM要区分清楚
- growth_rate越高越好,但要合理
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "tam": "数据不足",
                "sam": "数据不足",
                "growth_rate": "待评估",
                "market_maturity": "待评估",
                "concerns": ["自动分析失败"],
                "summary": "市场规模评估未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "tam": llm_result.get("tam", "待评估"),
            "sam": llm_result.get("sam", "待评估"),
            "growth_rate": llm_result.get("growth_rate", "待评估"),
            "market_maturity": llm_result.get("market_maturity", "待评估"),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "市场规模评估完成")
        }
