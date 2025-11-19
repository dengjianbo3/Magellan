"""
Community Activity Agent - 社区活跃度评估Agent
用于另类投资(Web3/加密货币)的社区活跃度快速评估
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class CommunityActivityAgent:
    """社区活跃度评估Agent - 用于另类投资"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速评估社区活跃度

        Args:
            target: 分析目标,包含:
                - project_name: 项目名称
                - symbol: 代币符号
                - twitter_handle: Twitter账号(可选)
                - discord_url: Discord链接(可选)

        Returns:
            社区活跃度评估结果
        """
        project_name = target.get('project_name', '')
        symbol = target.get('symbol', '')
        twitter_handle = target.get('twitter_handle', '')

        # 搜索社区信息
        search_results = await self._search_community_info(project_name, symbol)

        # 构建prompt
        prompt = self._build_prompt(
            project_name,
            symbol,
            twitter_handle,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result)

    async def _search_community_info(self, project_name: str, symbol: str) -> list:
        """搜索社区信息"""
        if not project_name and not symbol:
            return []

        query = f"{project_name} 社区 Twitter Discord GitHub"

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
            print(f"[CommunityActivityAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        project_name: str,
        symbol: str,
        twitter_handle: str,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到社区相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        twitter_text = f"@{twitter_handle}" if twitter_handle else "未提供"

        prompt = f"""你是一位资深的Web3社区分析专家,专注于评估项目的社区健康度。

**项目信息**:
- 项目名称: {project_name}
- 代币符号: {symbol}
- Twitter账号: {twitter_text}

**搜索结果**:
{search_text}

**任务**: 快速评估社区活跃度,关注:
1. 社交媒体活跃度(Twitter、Discord成员数、互动率)
2. 开发者活动(GitHub commits、贡献者)
3. 持币地址数和分布
4. 社区氛围和质量

**输出格式**(严格JSON):
{{
  "score": 0.80,
  "social_engagement": "Twitter 50万粉丝,互动率高,Discord 10万成员活跃",
  "developer_activity": "GitHub活跃,周均30+ commits,核心贡献者20+",
  "holder_count": "持币地址15万,分布较分散",
  "community_quality": "社区氛围积极,有多个活跃建设者",
  "concerns": ["近期社交媒体热度下降"],
  "summary": "社区活跃度高,开发持续进行"
}}

注意:
- score: 0-1评分
- 尽量提供具体数字
- 开发者活动很重要,体现项目持续性
- 持币地址分布影响价格稳定性
- concerns: 社区风险点(1-2条)
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "social_engagement": "待评估",
                "developer_activity": "待评估",
                "holder_count": "待评估",
                "community_quality": "待评估",
                "concerns": ["自动分析失败"],
                "summary": "社区活跃度评估未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "social_engagement": llm_result.get("social_engagement", "待评估"),
            "developer_activity": llm_result.get("developer_activity", "待评估"),
            "holder_count": llm_result.get("holder_count", "待评估"),
            "community_quality": llm_result.get("community_quality", "待评估"),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "社区活跃度评估完成")
        }
