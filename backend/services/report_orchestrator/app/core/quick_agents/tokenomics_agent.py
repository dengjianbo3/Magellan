"""
Tokenomics Agent - 代币经济学评估Agent
用于另类投资(Web3/加密货币)的代币经济学快速评估
"""
from typing import Dict, Any
import httpx
from ..llm_helper import llm_helper


class TokenomicsAgent:
    """代币经济学评估Agent - 用于另类投资"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010"
    ):
        self.web_search_url = web_search_url

    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速评估代币经济学

        Args:
            target: 分析目标,包含:
                - project_name: 项目名称
                - symbol: 代币符号
                - total_supply: 总供应量(可选)
                - market_cap: 市值(可选)

        Returns:
            代币经济学评估结果
        """
        project_name = target.get('project_name', '')
        symbol = target.get('symbol', '')
        total_supply = target.get('total_supply')
        market_cap = target.get('market_cap')

        # 搜索代币经济学信息
        search_results = await self._search_tokenomics(symbol, project_name)

        # 构建prompt
        prompt = self._build_prompt(
            project_name,
            symbol,
            total_supply,
            market_cap,
            search_results
        )

        # 调用LLM
        result = await llm_helper.call(prompt, response_format="json")

        return self._normalize_result(result)

    async def _search_tokenomics(self, symbol: str, project_name: str) -> list:
        """搜索代币经济学信息"""
        if not symbol and not project_name:
            return []

        query = f"{symbol} tokenomics 代币分配 经济模型"

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
            print(f"[TokenomicsAgent] Search failed: {e}")

        return []

    def _build_prompt(
        self,
        project_name: str,
        symbol: str,
        total_supply,
        market_cap,
        search_results: list
    ) -> str:
        """构建分析提示词"""

        search_text = "未找到代币经济学相关信息"
        if search_results:
            search_text = "\n".join([
                f"• {r.get('content', '')[:150]}..."
                for r in search_results[:3]
            ])

        supply_text = f"{total_supply}" if total_supply else "未提供"
        cap_text = f"{market_cap}" if market_cap else "未提供"

        prompt = f"""你是一位资深的加密货币经济学专家,专注于代币经济模型评估。

**项目信息**:
- 项目名称: {project_name}
- 代币符号: {symbol}
- 总供应量: {supply_text}
- 市值: {cap_text}

**搜索结果**:
{search_text}

**任务**: 快速评估代币经济学,关注:
1. 代币分配(团队、投资人、社区占比)
2. 通胀模型(增发机制、解锁计划)
3. 代币实用性(使用场景、价值捕获)
4. 激励机制设计

**输出格式**(严格JSON):
{{
  "score": 0.75,
  "distribution": "社区占比60%,团队15%锁仓2年,分配合理",
  "inflation_model": "通缩模型,年通胀率3%,有销毁机制",
  "utility": "治理、质押、手续费支付,实用性强",
  "incentive_design": "质押年化10%,激励机制良好",
  "concerns": ["早期投资人即将解锁"],
  "summary": "代币经济学设计合理,有价值捕获"
}}

注意:
- score: 0-1评分
- 代币分配非常重要,关注团队和VC占比
- 解锁计划影响抛压,需要关注
- concerns: 代币经济学风险点(1-2条)
- summary: 50字内总结
"""
        return prompt

    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果"""
        if "error" in llm_result:
            return {
                "score": 0.5,
                "distribution": "待评估",
                "inflation_model": "待评估",
                "utility": "待评估",
                "incentive_design": "待评估",
                "concerns": ["自动分析失败"],
                "summary": "代币经济学评估未完成"
            }

        return {
            "score": llm_result.get("score", 0.5),
            "distribution": llm_result.get("distribution", "待评估"),
            "inflation_model": llm_result.get("inflation_model", "待评估"),
            "utility": llm_result.get("utility", "待评估"),
            "incentive_design": llm_result.get("incentive_design", "待评估"),
            "concerns": llm_result.get("concerns", []),
            "summary": llm_result.get("summary", "代币经济学评估完成")
        }
