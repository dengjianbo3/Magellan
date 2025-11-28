# backend/services/report_orchestrator/app/agents/team_analysis_agent.py
"""
Team Analysis Agent for Team Due Diligence (TDD).
团队分析 Agent，用于团队尽职调查
"""
import httpx
import json
import re
from typing import List, Dict, Any
from ..models.dd_models import TeamMember, TeamAnalysisOutput


class TeamAnalysisAgent:
    """Agent for analyzing startup team"""

    def __init__(self, external_data_url: str, web_search_url: str, llm_gateway_url: str = "http://llm_gateway:8003"):
        self.external_data_url = external_data_url
        self.web_search_url = web_search_url
        self.llm_gateway_url = llm_gateway_url
        # V4: EventBus for real-time updates (set by caller)
        self.event_bus = None
    
    async def analyze(
        self,
        bp_team_info: List[TeamMember],
        company_name: str
    ) -> TeamAnalysisOutput:
        """
        Analyze team based on BP info and external data.

        Steps:
        1. Gather external data (company info, web search)
        2. Build comprehensive context
        3. Call LLM for analysis
        4. Parse and validate output

        Args:
            bp_team_info: Team members from BP
            company_name: Company name

        Returns:
            TeamAnalysisOutput with analysis results
        """
        # V4: Publish thinking event
        if self.event_bus:
            await self.event_bus.publish_thinking(
                agent_name="Team Agent",
                message=f"正在搜索团队背景信息...",
                progress=0.2
            )

        # Step 1: Gather external data
        web_search_results = await self._search_team_background(bp_team_info, company_name)

        # V4: Publish analyzing event
        if self.event_bus:
            await self.event_bus.publish_analyzing(
                agent_name="Team Agent",
                message=f"正在分析团队经验和背景...",
                progress=0.5
            )

        # Step 2: Build context
        context = self._build_context(bp_team_info, web_search_results)

        # Step 3: Call LLM for analysis
        prompt = self._build_analysis_prompt(context, bp_team_info, company_name)
        analysis_result = await self._call_llm(prompt)

        # V4: Publish progress event
        if self.event_bus:
            await self.event_bus.publish_progress(
                agent_name="Team Agent",
                message="正在解析分析结果...",
                progress=0.9
            )

        # Step 4: Parse and return
        return self._parse_llm_response(analysis_result, bp_team_info)
    
    async def _search_team_background(
        self, 
        team_members: List[TeamMember],
        company_name: str
    ) -> List[Dict[str, Any]]:
        """Search for team background information using Web Search Service"""
        all_results = []
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Search for each key team member
            for member in team_members[:3]:  # Limit to top 3 members to save time
                query = f"{member.name} {company_name} {member.title} background"
                
                try:
                    response = await client.post(
                        f"{self.web_search_url}/search",
                        json={"query": query, "max_results": 3}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("results", [])
                        all_results.extend([
                            {
                                "member_name": member.name,
                                "title": r.get("title", ""),
                                "url": r.get("url", ""),
                                "content": r.get("content", ""),
                                "score": r.get("score", 0.0)
                            }
                            for r in results
                        ])
                except Exception as e:
                    print(f"Warning: Web search failed for {member.name}: {e}")
                    continue
        
        return all_results
    
    def _build_context(
        self,
        bp_team_info: List[TeamMember],
        web_search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build comprehensive context for analysis"""
        return {
            "bp_team_count": len(bp_team_info),
            "bp_team_members": [
                {
                    "name": m.name,
                    "title": m.title,
                    "background": m.background
                }
                for m in bp_team_info
            ],
            "web_search_results": web_search_results,
            "has_external_validation": len(web_search_results) > 0
        }
    
    def _build_analysis_prompt(
        self,
        context: Dict[str, Any],
        bp_team_info: List[TeamMember],
        company_name: str
    ) -> str:
        """Build LLM prompt for team analysis"""
        
        # Format BP team info
        bp_team_text = "\n".join([
            f"- {m.name} ({m.title}): {m.background}"
            for m in bp_team_info
        ])
        
        # Format web search results
        web_results_text = "未找到相关网络信息"
        if len(context["web_search_results"]) > 0:
            web_results_text = "\n".join([
                f"• [{r['member_name']}] {r['content'][:200]}... (来源: {r['url']})"
                for r in context["web_search_results"][:5]
            ])
        
        prompt = f"""你是一位资深的风险投资分析师，专注于团队尽职调查（Team Due Diligence, TDD）。

**任务**: 分析 {company_name} 的创业团队，评估其执行项目的能力。

**BP 中的团队信息**:
{bp_team_text}

**网络搜索验证结果**:
{web_results_text}

**分析要求**:
1. 综合评估团队的整体实力（200-300字）
2. 识别团队的 3-5 个核心优势
3. 指出 2-4 个潜在担忧或需要验证的点
4. 给出经验匹配度评分（0-10分，10分为完美匹配项目需求）
5. 列出关键发现（如：发现创始人有过失败创业经历、团队成员来自同一家公司等）
6. 说明使用的数据来源

**输出格式**: 请严格按照以下 JSON 格式输出（不要包含 markdown 代码块标记）：

{{
  "summary": "团队整体评价文字...",
  "strengths": [
    "优势1",
    "优势2",
    "优势3"
  ],
  "concerns": [
    "担忧1",
    "担忧2"
  ],
  "experience_match_score": 7.5,
  "key_findings": [
    "发现1",
    "发现2"
  ],
  "data_sources": [
    "BP 第 5-6 页团队介绍",
    "网络搜索结果"
  ]
}}

**注意事项**:
- experience_match_score 必须是 0-10 之间的数字
- 如果信息不足，请在 concerns 中说明
- 优势和担忧要具体，避免空泛
- 必须严格遵循 JSON 格式
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
                    raise Exception(f"LLM Gateway returned {response.status_code}: {response.text}")

                result = response.json()
                return result.get("content", "")
            except httpx.RemoteProtocolError as e:
                print(f"[Team Agent] LLM server disconnected: {e}", flush=True)
                return """```json
{
    "summary": "由于LLM服务暂时不可用，无法完成完整的团队分析。",
    "strengths": [],
    "concerns": ["LLM服务连接失败"],
    "experience_match_score": 5.0
}
```"""
            except httpx.TimeoutException as e:
                print(f"[Team Agent] LLM request timeout: {e}", flush=True)
                return """```json
{
    "summary": "LLM请求超时，无法完成团队分析。",
    "strengths": [],
    "concerns": ["分析请求超时"],
    "experience_match_score": 5.0
}
```"""
    
    def _parse_llm_response(
        self,
        llm_response: str,
        bp_team_info: List[TeamMember]
    ) -> TeamAnalysisOutput:
        """Parse LLM response and create TeamAnalysisOutput"""
        try:
            # Try to parse JSON directly
            data = json.loads(llm_response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            match = re.search(r"```json\n(.*)\n```", llm_response, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    # If parsing fails completely, return fallback
                    return self._create_fallback_analysis(bp_team_info)
            else:
                # No JSON found, return fallback
                return self._create_fallback_analysis(bp_team_info)
        
        # Validate and create output
        return TeamAnalysisOutput(
            summary=data.get("summary", "团队分析未能生成"),
            strengths=data.get("strengths", []),
            concerns=data.get("concerns", []),
            experience_match_score=float(data.get("experience_match_score", 5.0)),
            key_findings=data.get("key_findings", []),
            data_sources=data.get("data_sources", ["BP 团队章节"])
        )
    
    def _create_fallback_analysis(self, bp_team_info: List[TeamMember]) -> TeamAnalysisOutput:
        """Create a basic fallback analysis when LLM parsing fails"""
        summary = f"团队由 {len(bp_team_info)} 名核心成员组成。"
        if len(bp_team_info) > 0:
            summary += f"CEO {bp_team_info[0].name} 负责整体战略。"
        
        strengths = ["团队成员背景互补"]
        concerns = ["需要进一步验证团队成员的具体项目经历"]
        
        return TeamAnalysisOutput(
            summary=summary,
            strengths=strengths,
            concerns=concerns,
            experience_match_score=5.0,
            key_findings=["LLM 分析失败，使用降级方案"],
            data_sources=["BP 团队章节"]
        )
    
    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results for prompt"""
        if not results:
            return "未找到相关信息"
        
        formatted = []
        for r in results[:5]:  # Top 5 results
            formatted.append(
                f"• [{r.get('member_name', 'Unknown')}] {r.get('content', '')[:150]}..."
            )
        
        return "\n".join(formatted)
