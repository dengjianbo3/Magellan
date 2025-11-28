# backend/services/report_orchestrator/app/agents/market_analysis_agent.py
"""
Market Analysis Agent for Market Due Diligence (MDD).
市场分析 Agent，用于市场尽职调查
"""
import httpx
import json
import re
from typing import Dict, Any, List
from ..models.dd_models import MarketAnalysisOutput


class MarketAnalysisAgent:
    """Agent for analyzing market and competition"""

    def __init__(
        self,
        web_search_url: str,
        internal_knowledge_url: str,
        llm_gateway_url: str = "http://llm_gateway:8003"
    ):
        self.web_search_url = web_search_url
        self.internal_knowledge_url = internal_knowledge_url
        self.llm_gateway_url = llm_gateway_url
        # V4: EventBus for real-time updates (set by caller)
        self.event_bus = None

    async def analyze(
        self,
        bp_market_info: Dict[str, Any],
        company_name: str
    ) -> MarketAnalysisOutput:
        """
        Analyze market based on BP claims and external validation.

        Steps:
        1. Validate market size claims
        2. Search for competitive information
        3. Query internal knowledge base
        4. Call LLM for comprehensive analysis
        5. Parse and return results

        Args:
            bp_market_info: Market information from BP
            company_name: Company name

        Returns:
            MarketAnalysisOutput with analysis results
        """
        # V4: Publish thinking event
        if self.event_bus:
            await self.event_bus.publish_thinking(
                agent_name="Market Agent",
                message="正在验证市场规模数据...",
                progress=0.2
            )

        # Step 1: Search for market validation
        market_search_results = await self._search_market_data(bp_market_info)

        # V4: Publish searching event
        if self.event_bus:
            await self.event_bus.publish_searching(
                agent_name="Market Agent",
                query=f"{bp_market_info.get('target_market', '')} 竞争格局",
                progress=0.4
            )

        # Step 2: Search for competitive info
        competitor_search_results = await self._search_competitors(bp_market_info)

        # V4: Publish analyzing event
        if self.event_bus:
            await self.event_bus.publish_analyzing(
                agent_name="Market Agent",
                message="正在查询内部项目库...",
                progress=0.6
            )

        # Step 3: Query internal knowledge
        internal_insights = await self._query_internal_knowledge(bp_market_info)
        
        # Step 4: Build prompt and call LLM
        prompt = self._build_analysis_prompt(
            bp_market_info,
            company_name,
            market_search_results,
            competitor_search_results,
            internal_insights
        )
        
        analysis_result = await self._call_llm(prompt)
        
        # Step 5: Parse and return
        return self._parse_llm_response(analysis_result, bp_market_info)
    
    async def _search_market_data(self, bp_market_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for market size and trend data"""
        target_market = bp_market_info.get("target_market", "")
        market_size = bp_market_info.get("market_size_tam", "")
        
        if not target_market:
            return []
        
        query = f"{target_market} 市场规模 趋势 2024"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.web_search_url}/search",
                    json={"query": query, "max_results": 5}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("results", [])
            except Exception as e:
                print(f"Warning: Market search failed: {e}")
        
        return []
    
    async def _search_competitors(self, bp_market_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for competitor information"""
        competitors = bp_market_info.get("competitors", [])
        
        if not competitors:
            return []
        
        # Search for first 2-3 competitors
        query = " vs ".join(competitors[:3])
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.web_search_url}/search",
                    json={"query": query, "max_results": 5}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("results", [])
            except Exception as e:
                print(f"Warning: Competitor search failed: {e}")
        
        return []
    
    async def _query_internal_knowledge(self, bp_market_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query internal knowledge base for similar projects"""
        target_market = bp_market_info.get("target_market", "")
        
        if not target_market:
            return []
        
        query = f"{target_market} 赛道 投资 项目"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.internal_knowledge_url}/search",
                    json={"query": query, "limit": 3}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("results", [])
            except Exception as e:
                print(f"Warning: Internal knowledge query failed: {e}")
        
        return []
    
    def _build_analysis_prompt(
        self,
        bp_market_info: Dict[str, Any],
        company_name: str,
        market_search_results: List[Dict[str, Any]],
        competitor_search_results: List[Dict[str, Any]],
        internal_insights: List[Dict[str, Any]]
    ) -> str:
        """Build LLM prompt for market analysis"""
        
        target_market = bp_market_info.get("target_market", "未知")
        market_size = bp_market_info.get("market_size_tam", "未提供")
        competitors = bp_market_info.get("competitors", [])
        
        # Format search results
        market_data_text = self._format_search_results(market_search_results)
        competitor_data_text = self._format_search_results(competitor_search_results)
        
        # Format internal insights
        internal_text = "暂无相关历史项目"
        if internal_insights:
            internal_text = "\n".join([
                f"• {insight.get('content', '')[:200]}..."
                for insight in internal_insights[:3]
            ])
        
        prompt = f"""你是一位资深的行业分析师，专注于市场尽职调查（Market Due Diligence, MDD）。

**任务**: 验证 {company_name} 的 BP 中的市场假设，分析竞争格局。

**BP 声称的市场信息**:
- 目标市场: {target_market}
- 市场规模 (TAM): {market_size}
- 竞品: {', '.join(competitors) if competitors else '未提供'}

**网络搜索到的市场数据**:
{market_data_text}

**竞品搜索结果**:
{competitor_data_text}

**内部历史洞察**:
{internal_text}

**分析要求**:
1. 验证 BP 中的市场规模是否合理（有无夸大？数据来源可靠吗？）
2. 评估市场的增长潜力
3. 分析竞争格局（巨头威胁、差异化空间）
4. 识别市场风险和红旗
5. 发现市场机会

**输出格式**: 请严格按照以下 JSON 格式输出：

{{
  "summary": "市场整体评价（150-250字）",
  "market_validation": "BP 中的市场规模 {market_size} 验证结果...",
  "growth_potential": "增长潜力评估...",
  "competitive_landscape": "竞争格局分析...",
  "red_flags": [
    "风险1",
    "风险2"
  ],
  "opportunities": [
    "机会1",
    "机会2"
  ],
  "data_sources": [
    "36氪报道",
    "艾瑞咨询"
  ]
}}

**注意**: 
- 如果 BP 未提供市场规模，请在 red_flags 中指出
- 如果发现市场数据夸大，必须在 market_validation 中明确说明
- 竞争分析要客观，既要看到威胁也要看到机会
"""
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM Gateway for analysis"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.llm_gateway_url}/chat",
                    json={
                        "history": [
                            {"role": "user", "parts": [prompt]}
                        ]
                    }
                )

                if response.status_code != 200:
                    raise Exception(f"LLM Gateway returned {response.status_code}")

                result = response.json()
                return result.get("content", "")
            except httpx.RemoteProtocolError as e:
                print(f"[Market Agent] LLM server disconnected: {e}", flush=True)
                # 返回一个简化的响应,避免整个流程崩溃
                return """```json
{
    "summary": "由于LLM服务暂时不可用，无法完成完整的市场分析。建议稍后重试或使用备用分析方法。",
    "market_validation": "LLM服务不可用",
    "growth_potential": "待评估",
    "competitive_landscape": "待分析",
    "red_flags": ["LLM服务连接失败，无法完成自动化分析"],
    "opportunities": []
}
```"""
            except httpx.TimeoutException as e:
                print(f"[Market Agent] LLM request timeout: {e}", flush=True)
                return """```json
{
    "summary": "LLM请求超时，无法完成市场分析。",
    "market_validation": "分析超时",
    "growth_potential": "待评估",
    "competitive_landscape": "待分析",
    "red_flags": ["分析请求超时"],
    "opportunities": []
}
```"""
    
    def _parse_llm_response(
        self,
        llm_response: str,
        bp_market_info: Dict[str, Any]
    ) -> MarketAnalysisOutput:
        """Parse LLM response and create MarketAnalysisOutput"""
        try:
            # Try to parse JSON
            data = json.loads(llm_response)
        except json.JSONDecodeError:
            # Try markdown extraction
            match = re.search(r"```json\n(.*)\n```", llm_response, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    return self._create_fallback_analysis(bp_market_info)
            else:
                return self._create_fallback_analysis(bp_market_info)
        
        return MarketAnalysisOutput(
            summary=data.get("summary", "市场分析未能生成"),
            market_validation=data.get("market_validation", "无法验证"),
            growth_potential=data.get("growth_potential", "未知"),
            competitive_landscape=data.get("competitive_landscape", "需要进一步研究"),
            red_flags=data.get("red_flags", []),
            opportunities=data.get("opportunities", []),
            data_sources=data.get("data_sources", ["BP 市场章节"])
        )
    
    def _create_fallback_analysis(self, bp_market_info: Dict[str, Any]) -> MarketAnalysisOutput:
        """Create fallback analysis when LLM parsing fails"""
        target_market = bp_market_info.get("target_market", "未知市场")
        
        return MarketAnalysisOutput(
            summary=f"{target_market} 市场需要进一步研究",
            market_validation="数据不足，无法验证",
            growth_potential="需要更多数据",
            competitive_landscape="需要进一步分析竞品",
            red_flags=["LLM 分析失败，建议人工分析"],
            opportunities=[],
            data_sources=["BP 市场章节"]
        )
    
    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results for prompt"""
        if not results:
            return "未找到相关信息"
        
        formatted = []
        for r in results[:5]:
            content = r.get("content", "")
            url = r.get("url", "")
            formatted.append(f"• {content[:200]}... (来源: {url})")
        
        return "\n".join(formatted)
