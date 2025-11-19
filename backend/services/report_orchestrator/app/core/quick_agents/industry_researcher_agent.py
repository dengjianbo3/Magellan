"""
Industry Researcher Agent - 行业定义和价值链分析Agent
用于行业研究的市场边界定义和价值链分析
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class IndustryResearcherAgent:
    """行业定义分析Agent - 用于市场边界定义和价值链分析"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        行业定义和价值链分析

        Args:
            target: 分析目标,包含:
                - industry_name: 行业名称
                - research_topic: 研究主题
                - geo_scope: 地理范围 (可选)

        Returns:
            行业定义分析结果
        """
        industry_name = target.get('industry_name', '')
        research_topic = target.get('research_topic', industry_name)
        geo_scope = target.get('geo_scope', 'global')

        # 搜索行业信息
        search_results = await self._search_industry_info(
            industry_name,
            research_topic,
            geo_scope
        )

        # 构建prompt
        prompt = self._build_prompt(
            industry_name,
            research_topic,
            geo_scope,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result, industry_name)

    async def _search_industry_info(
        self,
        industry_name: str,
        research_topic: str,
        geo_scope: str
    ) -> list:
        """搜索行业定义相关信息"""
        if not industry_name:
            return []

        # 构建多个搜索查询
        queries = [
            f"{industry_name} 行业定义 产业链 价值链",
            f"{research_topic} 市场边界 细分领域",
            f"{industry_name} 上下游 生态"
        ]

        all_results = []
        for query in queries[:2]:  # 限制搜索次数
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.web_search_url}/search",
                        json={"query": query, "max_results": 2}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        all_results.extend(data.get("results", []))
            except Exception as e:
                print(f"[IndustryResearcherAgent] Search failed: {e}")

        return all_results[:5]  # 最多返回5条结果

    def _build_prompt(
        self,
        industry_name: str,
        research_topic: str,
        geo_scope: str,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到行业相关信息,请基于通用知识分析"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('title', '')}: {r.get('content', '')[:200]}..."
                for r in search_results[:5]
            ])

        geo_text = {
            'global': '全球',
            'china': '中国',
            'us': '美国',
            'europe': '欧洲',
            'asia': '亚洲'
        }.get(geo_scope, '全球')

        prompt = f"""你是一位资深的行业研究专家,专注于行业定义和价值链分析。

**研究对象**:
- 行业: {industry_name}
- 研究主题: {research_topic}
- 地理范围: {geo_text}

**参考信息**:
{search_text}

**任务**: 定义行业边界和价值链,需要明确:
1. 行业边界定义 - 什么属于该行业,什么不属于
2. 市场细分领域 - 主要的子行业/子领域
3. 价值链结构 - 上游、中游、下游的关键环节
4. 核心参与者类型 - 不同价值链环节的玩家类型

**输出格式**(严格JSON):
{{
  "market_boundaries": "清晰定义该行业的市场边界,包括核心业务范围和排除领域",
  "segments": [
    "细分领域1: 简要说明",
    "细分领域2: 简要说明",
    "细分领域3: 简要说明"
  ],
  "value_chain": {{
    "upstream": "上游环节描述,如原材料供应、技术研发等",
    "midstream": "中游环节描述,如生产制造、平台服务等",
    "downstream": "下游环节描述,如销售渠道、终端用户等"
  }},
  "key_player_types": [
    "玩家类型1: 如技术提供商",
    "玩家类型2: 如平台运营商",
    "玩家类型3: 如终端服务商"
  ],
  "industry_characteristics": "该行业的3-5个关键特征,如技术密集型、资本密集型、规模效应等",
  "summary": "100字内总结该行业的核心定义和价值链特点"
}}

注意:
- market_boundaries要明确包含和排除的边界
- segments至少3个细分领域
- value_chain的上中下游要清晰
- key_player_types至少3种类型
- summary要简洁有力
"""
        return prompt

    def _normalize_result(
        self,
        llm_result: Dict[str, Any],
        industry_name: str
    ) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "market_boundaries": f"{industry_name}行业边界定义待完善",
                "segments": ["待分析"],
                "value_chain": {
                    "upstream": "待分析",
                    "midstream": "待分析",
                    "downstream": "待分析"
                },
                "key_player_types": ["待分析"],
                "industry_characteristics": "待分析",
                "summary": "行业定义分析未完成,请人工补充"
            }

        return {
            "market_boundaries": llm_result.get(
                "market_boundaries",
                "行业边界待定义"
            ),
            "segments": llm_result.get("segments", ["待分析"]),
            "value_chain": llm_result.get("value_chain", {
                "upstream": "待分析",
                "midstream": "待分析",
                "downstream": "待分析"
            }),
            "key_player_types": llm_result.get("key_player_types", ["待分析"]),
            "industry_characteristics": llm_result.get(
                "industry_characteristics",
                "待分析"
            ),
            "summary": llm_result.get("summary", "行业定义分析完成")
        }
