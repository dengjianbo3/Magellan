"""
Red Flag Scan Agent - 风险红旗扫描Agent
用于快速判断模式下的风险识别
"""
from typing import Dict, Any, List
import httpx
from ..llm_helper import llm_helper


class RedFlagAgent:
    """风险红旗扫描Agent - 识别明显的投资风险"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速扫描风险红旗

        Args:
            target: 分析目标信息

        Returns:
            风险扫描结果
        """
        company_name = target.get('company_name', '')
        description = target.get('description', '')

        # Step 1: 搜索负面信息
        search_results = await self._search_negative_info(company_name)

        # Step 2: 构建prompt
        prompt = self._build_prompt(company_name, description, search_results)

        # Step 3: 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        # Step 4: 标准化结果
        return self._normalize_result(result)

    async def _search_negative_info(self, company_name: str) -> list:
        """搜索负面信息"""
        if not company_name:
            return []

        # 搜索负面关键词
        query = f"{company_name} 争议 问题 风险 诉讼"

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
            print(f"[RedFlagAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        company_name: str,
        description: str,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到明显负面信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        prompt = f"""你是一位谨慎的风险分析专家,专注于识别早期投资的风险红旗。

**项目信息**:
- 公司: {company_name}
- 描述: {description}

**搜索到的信息**:
{search_text}

**任务**: 扫描以下风险红旗:
1. 法律风险 (诉讼、合规问题)
2. 团队风险 (创始人信誉问题、团队不稳定)
3. 商业模式风险 (不可行、不合规)
4. 市场风险 (政策限制、巨头垄断)
5. 技术风险 (技术不成熟、专利纠纷)

**输出格式**(严格JSON):
{{
  "red_flags": [
    "发现XX法律诉讼",
    "商业模式依赖灰色地带"
  ],
  "severity": "high",
  "risk_areas": ["法律风险", "合规风险"],
  "recommendation": "建议深入法律尽调",
  "summary": "发现2个高风险红旗,需谨慎"
}}

注意:
- red_flags: 发现的红旗列表
- severity: "low" | "medium" | "high"
- 如无红旗, red_flags返回空数组[]
- 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "red_flags": ["自动扫描失败,建议人工排查"],
                "severity": "medium",
                "risk_areas": ["未知"],
                "recommendation": "需人工风险评估",
                "summary": "风险扫描未完成"
            }

        return {
            "red_flags": llm_result.get("red_flags", []),
            "severity": llm_result.get("severity", "low"),
            "risk_areas": llm_result.get("risk_areas", []),
            "recommendation": llm_result.get("recommendation", "继续评估"),
            "summary": llm_result.get("summary", "风险扫描完成")
        }
