# backend/services/report_orchestrator/app/agents/risk_agent.py
"""
Risk Agent for generating DD question lists.
风险 Agent，用于生成尽职调查问题清单
"""
import httpx
import json
import re
from typing import List, Dict, Any
from ..models.dd_models import (
    TeamAnalysisOutput, 
    MarketAnalysisOutput, 
    BPStructuredData,
    DDQuestion
)


class RiskAgent:
    """Agent for generating DD questions"""
    
    def __init__(self, llm_gateway_url: str):
        self.llm_gateway_url = llm_gateway_url
    
    async def generate_dd_questions(
        self,
        team_analysis: TeamAnalysisOutput,
        market_analysis: MarketAnalysisOutput,
        bp_data: BPStructuredData
    ) -> List[DDQuestion]:
        """
        Generate DD question list based on analysis results.
        
        Steps:
        1. Identify weak points from analyses
        2. Build comprehensive prompt
        3. Call LLM to generate questions
        4. Parse and categorize questions
        
        Args:
            team_analysis: Team analysis results
            market_analysis: Market analysis results
            bp_data: Structured BP data
        
        Returns:
            List of DDQuestion objects (15-20 questions)
        """
        # Step 1: Identify weak points
        weak_points = self._identify_weak_points(team_analysis, market_analysis, bp_data)
        
        # Step 2: Build prompt
        prompt = self._build_question_generation_prompt(
            team_analysis,
            market_analysis,
            bp_data,
            weak_points
        )
        
        # Step 3: Call LLM
        llm_response = await self._call_llm(prompt)
        
        # Step 4: Parse and return
        return self._parse_llm_response(llm_response)
    
    def _identify_weak_points(
        self,
        team_analysis: TeamAnalysisOutput,
        market_analysis: MarketAnalysisOutput,
        bp_data: BPStructuredData
    ) -> Dict[str, List[str]]:
        """Identify weak points and gaps in BP"""
        weak_points = {
            "team": [],
            "market": [],
            "product": [],
            "financial": [],
            "general": []
        }
        
        # Team weak points
        if team_analysis and team_analysis.concerns:
            weak_points["team"].extend(team_analysis.concerns)
        if team_analysis and team_analysis.experience_match_score < 6.0:
            weak_points["team"].append("团队整体经验匹配度偏低")

        # Market weak points
        if market_analysis and market_analysis.red_flags:
            weak_points["market"].extend(market_analysis.red_flags)
        if not bp_data.market_size_tam:
            weak_points["market"].append("BP 未提供市场规模数据")
        
        # Product weak points
        if not bp_data.core_technology:
            weak_points["product"].append("BP 未明确说明核心技术")
        if not bp_data.competitive_advantages:
            weak_points["product"].append("BP 未清晰阐述竞争优势")
        
        # Financial weak points
        if not bp_data.financial_projections or len(bp_data.financial_projections) == 0:
            weak_points["financial"].append("BP 缺少详细的财务预测")
        if bp_data.funding_request and not bp_data.use_of_funds:
            weak_points["financial"].append("BP 未说明融资资金的具体用途")
        
        return weak_points
    
    def _build_question_generation_prompt(
        self,
        team_analysis: TeamAnalysisOutput,
        market_analysis: MarketAnalysisOutput,
        bp_data: BPStructuredData,
        weak_points: Dict[str, List[str]]
    ) -> str:
        """Build prompt for generating DD questions"""
        
        # Format weak points
        weak_points_text = []
        for category, points in weak_points.items():
            if points:
                weak_points_text.append(f"**{category.upper()}**:")
                for point in points:
                    weak_points_text.append(f"  - {point}")
        weak_points_formatted = "\n".join(weak_points_text) if weak_points_text else "暂无明显薄弱点"
        
        prompt = f"""你是一位经验丰富的投资负责人，即将与 {bp_data.company_name} 的创始人进行深度访谈。

**背景信息**:

【团队分析】
{team_analysis.summary if team_analysis else '未进行团队分析'}
- 经验匹配度: {team_analysis.experience_match_score if team_analysis else 'N/A'}/10
- 担忧点: {', '.join(team_analysis.concerns) if team_analysis and team_analysis.concerns else '无'}

【市场分析】
{market_analysis.summary if market_analysis else '未进行市场分析'}
- 市场验证: {market_analysis.market_validation if market_analysis else 'N/A'}
- 风险: {', '.join(market_analysis.red_flags) if market_analysis and market_analysis.red_flags else '无'}

【BP 关键数据】
- 融资金额: {bp_data.funding_request or '未提供'}
- 估值: {bp_data.current_valuation or '未提供'}
- 团队规模: {len(bp_data.team)} 人
- 竞品: {', '.join(bp_data.competitors) if bp_data.competitors else '未提供'}

【识别的薄弱环节】
{weak_points_formatted}

**任务**: 生成 15-20 个有针对性的 DD 问题，帮助投委会做出决策。

**问题要求**:
1. 具体且可验证（如："请提供 CTO 的论文列表"，而非"介绍一下技术团队"）
2. 针对 BP 中的薄弱环节或可疑数据
3. 涵盖 Team/Market/Product/Financial/Risk 五大类
4. 优先级分为 High/Medium/Low
5. 每个问题说明为什么要问（reasoning）
6. 尽量关联 BP 的具体页码或章节

**输出格式**: 严格的 JSON 数组（不要包含 markdown 标记）：

[
  {{
    "category": "Team",
    "question": "BP 提到 CTO 李四是'AI 领域专家'，请提供其博士期间的研究方向、发表论文列表，以及工业界落地项目案例。",
    "reasoning": "'AI 专家'描述宽泛，需验证技术能力是否匹配产品需求（NLP/知识图谱）。",
    "priority": "High",
    "bp_reference": "第 5 页，CTO 介绍"
  }},
  {{
    "category": "Market",
    "question": "...",
    "reasoning": "...",
    "priority": "High",
    "bp_reference": "..."
  }}
]

生成至少 15 个问题，确保每个类别都有覆盖。
"""
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM Gateway"""
        async with httpx.AsyncClient(timeout=180.0) as client:
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
    
    def _parse_llm_response(self, llm_response: str) -> List[DDQuestion]:
        """Parse LLM response into DDQuestion list"""
        try:
            # Try direct parsing
            data = json.loads(llm_response)
        except json.JSONDecodeError:
            # Try markdown extraction
            match = re.search(r"```json\n(.*)\n```", llm_response, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    return self._create_fallback_questions()
            else:
                return self._create_fallback_questions()
        
        # Validate and create DDQuestion objects
        questions = []
        for item in data:
            try:
                question = DDQuestion(
                    category=item.get("category", "General"),
                    question=item.get("question", ""),
                    reasoning=item.get("reasoning", ""),
                    priority=item.get("priority", "Medium"),
                    bp_reference=item.get("bp_reference")
                )
                questions.append(question)
            except Exception as e:
                print(f"Warning: Failed to parse question: {e}")
                continue
        
        # Ensure minimum number of questions
        if len(questions) < 5:
            questions.extend(self._create_fallback_questions())
        
        return questions[:20]  # Max 20 questions
    
    def _create_fallback_questions(self) -> List[DDQuestion]:
        """Create basic fallback questions"""
        return [
            DDQuestion(
                category="Team",
                question="请提供所有核心团队成员的详细履历和过往项目经验。",
                reasoning="验证团队执行能力",
                priority="High"
            ),
            DDQuestion(
                category="Market",
                question="请提供市场规模的具体数据来源和计算方法。",
                reasoning="验证市场假设的合理性",
                priority="High"
            ),
            DDQuestion(
                category="Product",
                question="请提供产品的核心技术文档和知识产权情况。",
                reasoning="验证技术壁垒",
                priority="High"
            ),
            DDQuestion(
                category="Financial",
                question="请详细说明融资资金的使用计划和各项预算明细。",
                reasoning="确保资金使用合理",
                priority="Medium"
            ),
            DDQuestion(
                category="Risk",
                question="请说明公司面临的主要风险以及应对策略。",
                reasoning="全面了解风险意识",
                priority="Medium"
            )
        ]
    
    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results for display"""
        if not results:
            return "未找到相关信息"
        
        return "\n".join([
            f"• {r.get('content', '')[:150]}..."
            for r in results[:5]
        ])
