"""
Team Quick Check Agent - 团队快速评估Agent
用于快速判断模式下的团队背景检查
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class TeamQuickAgent:
    """团队快速评估Agent - 轻量级实现用于快速判断"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速评估团队

        Args:
            target: 分析目标信息,包含:
                - company_name: 公司名称
                - stage: 融资阶段
                - description: 公司描述
                - team_members: 团队成员列表(可选)

        Returns:
            团队评估结果
        """
        company_name = target.get('company_name', '')
        description = target.get('description', '')
        team_members = target.get('team_members', [])

        # Step 1: 搜索创始人/团队信息
        search_results = await self._search_team_background(company_name, team_members)

        # Step 2: 构建prompt并调用LLM
        prompt = self._build_prompt(company_name, description, team_members, search_results)

        # Step 3: 调用LLM进行分析
        result = await llm_helper.call(prompt, response_format="json")

        # Step 4: 标准化返回格式
        return self._normalize_result(result)

    async def _search_team_background(
        self,
        company_name: str,
        team_members: list
    ) -> list:
        """搜索团队背景信息"""
        if not company_name:
            return []

        # 构建搜索查询
        if team_members:
            # 如果有团队成员信息,搜索创始人
            query = f"{company_name} 创始人 {' '.join(team_members[:2])} 背景"
        else:
            query = f"{company_name} 创始团队 背景"

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
            print(f"[TeamQuickAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        company_name: str,
        description: str,
        team_members: list,
        search_results: list
    ) -> str:
        """构建LLM分析提示词"""

        # 格式化搜索结果
        search_text = "未找到相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        team_info = "未提供" if not team_members else ", ".join(team_members)

        prompt = f"""你是一位资深的投资人,专注于早期项目的团队评估。

**项目信息**:
- 公司名称: {company_name}
- 项目描述: {description}
- 团队成员: {team_info}

**搜索到的团队信息**:
{search_text}

**任务**: 基于以上信息快速评估团队,关注:
1. 创始人背景是否匹配项目方向
2. 团队是否有相关行业经验
3. 是否有创业经历或技术背景
4. 团队完整度(技术+商业+产品)

**输出格式**(严格JSON):
{{
  "team_score": 0.75,
  "highlights": ["创始人有10年AI经验", "CTO来自Google"],
  "concerns": ["商业团队较弱"],
  "summary": "团队技术实力强,但需补充商业人才"
}}

注意:
- team_score: 0-1之间的评分
- highlights: 亮点列表(最多3条)
- concerns: 关注点列表(最多3条)
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化返回结果"""
        # 如果LLM返回有错误,提供默认值
        if "error" in llm_result:
            return {
                "score": 0.5,
                "team_score": 0.5,
                "highlights": [],
                "concerns": ["LLM分析失败,需人工评估"],
                "summary": "自动分析未完成"
            }

        # 确保必要字段存在
        return {
            "score": llm_result.get("team_score", 0.5),
            "team_score": llm_result.get("team_score", 0.5),
            "highlights": llm_result.get("highlights", []),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "团队评估完成")
        }
