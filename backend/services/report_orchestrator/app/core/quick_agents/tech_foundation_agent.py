"""
Tech Foundation Agent - 技术基础评估Agent
用于另类投资(Web3/加密货币)的技术基础快速评估
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class TechFoundationAgent:
    """技术基础评估Agent - 用于另类投资"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速评估技术基础

        Args:
            target: 分析目标,包含:
                - project_name: 项目名称
                - symbol: 代币符号
                - blockchain: 所在区块链
                - description: 项目描述

        Returns:
            技术基础评估结果
        """
        project_name = target.get('project_name', '')
        symbol = target.get('symbol', '')
        blockchain = target.get('blockchain', '')
        description = target.get('description', '')

        # 搜索技术信息
        search_results = await self._search_tech_info(project_name, symbol)

        # 构建prompt
        prompt = self._build_prompt(
            project_name,
            symbol,
            blockchain,
            description,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result)

    async def _search_tech_info(self, project_name: str, symbol: str) -> list:
        """搜索技术信息"""
        if not project_name and not symbol:
            return []

        query = f"{project_name} 技术 架构 审计 安全"

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
            print(f"[TechFoundationAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        project_name: str,
        symbol: str,
        blockchain: str,
        description: str,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到技术相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        prompt = f"""你是一位资深的区块链技术专家,专注于Web3项目技术基础评估。

**项目信息**:
- 项目名称: {project_name}
- 代币符号: {symbol}
- 区块链: {blockchain}
- 项目描述: {description}

**搜索结果**:
{search_text}

**任务**: 快速评估技术基础,关注:
1. 技术架构设计(共识机制、扩展性等)
2. 安全性(是否有审计、历史漏洞)
3. 技术创新性
4. 代码质量和开发活跃度

**输出格式**(严格JSON):
{{
  "score": 0.80,
  "architecture_quality": "采用PoS共识,分片技术,扩展性强",
  "security_audit": "已通过CertiK和SlowMist审计,无重大漏洞",
  "innovation_level": "技术创新度高,引入零知识证明",
  "code_quality": "GitHub活跃,代码质量优秀",
  "concerns": ["主网上线时间较短"],
  "summary": "技术基础扎实,安全性较高"
}}

注意:
- score: 0-1评分
- 尽量提供具体的技术细节
- 安全审计非常重要,务必关注
- concerns: 技术风险点(1-2条)
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "architecture_quality": "待评估",
                "security_audit": "待评估",
                "innovation_level": "待评估",
                "code_quality": "待评估",
                "concerns": ["自动分析失败"],
                "summary": "技术基础评估未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "architecture_quality": llm_result.get("architecture_quality", "待评估"),
            "security_audit": llm_result.get("security_audit", "待评估"),
            "innovation_level": llm_result.get("innovation_level", "待评估"),
            "code_quality": llm_result.get("code_quality", "待评估"),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "技术基础评估完成")
        }
