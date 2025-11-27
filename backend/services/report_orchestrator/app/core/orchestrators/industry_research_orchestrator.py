"""
Industry Research Orchestrator (行业研究协调器)

场景: 系统性行业/市场研究
关注点: 行业趋势、竞争格局、投资机会、风险因素
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from .base_orchestrator import BaseOrchestrator
from ...models.analysis_models import (
    InvestmentScenario,
    AnalysisDepth,
    QuickJudgmentResult,
    RecommendationType
)
# Phase 2: All agents now loaded from AgentRegistry
# Legacy imports removed


class IndustryResearchOrchestrator(BaseOrchestrator):
    """
    行业研究Orchestrator

    适用场景:
    - 行业趋势分析
    - 细分赛道研究
    - 投资机会挖掘
    - 竞争格局分析

    分析重点:
    - 市场规模与增长 (30%)
    - 竞争格局 (25%)
    - 技术趋势 (25%)
    - 投资机会 (20%)
    """

    def __init__(self, session_id: str, request: Any, websocket: Any = None):
        super().__init__(
            scenario=InvestmentScenario.INDUSTRY_RESEARCH,
            session_id=session_id,
            request=request,
            websocket=websocket
        )
        self.scenario_name = "行业研究"

        # Phase 2: Agents now loaded from AgentRegistry, no need for service URLs here

    async def _validate_target(self) -> bool:
        """
        验证行业研究目标

        必填:
        - industry_name: 行业名称 (如: 人工智能, 新能源汽车)

        可选:
        - research_topic: 研究主题 (如: 2024年AI芯片市场趋势)
        - sub_sector: 细分领域 (如: AI推理芯片)
        - region: 地域范围 (如: china, global, us等)
        - geo_scope: 地域范围（已废弃，使用region）
        - key_questions: 关键问题列表
        """
        await self._send_status(
            "initializing",
            f"正在验证{self.scenario_name}分析目标..."
        )

        target = self.request.target

        # 检查必填字段
        if not target.get('industry_name'):
            raise ValueError("缺少行业名称 (industry_name)")

        # research_topic 如果没有提供，从其他字段生成
        if not target.get('research_topic'):
            # 尝试从 sub_sector 和 region 生成 research_topic
            industry_name = target.get('industry_name', '')
            sub_sector = target.get('sub_sector', '')
            region = target.get('region', target.get('geo_scope', ''))

            # 构建研究主题
            topic_parts = [industry_name]
            if sub_sector:
                topic_parts.append(sub_sector)
            if region:
                region_name = {'china': '中国', 'global': '全球', 'us': '美国'}.get(region, region)
                topic_parts.append(f"{region_name}市场")
            else:
                topic_parts.append("市场分析")

            # 设置生成的research_topic
            target['research_topic'] = " - ".join(topic_parts)

        return True

    async def _synthesize_quick_judgment(self) -> QuickJudgmentResult:
        """
        综合快速判断结果 (行业研究)
        """
        from app.agents.report_synthesizer_agent import synthesize_report
        from ...models.analysis_models import QuickJudgmentResult, RecommendationType

        # Retrieve results using step IDs from workflows.yaml (strings "1", "2", "3")
        market_result = self._safe_to_dict(self.results.get("1"))
        tech_result = self._safe_to_dict(self.results.get("2"))
        financial_result = self._safe_to_dict(self.results.get("3"))

        # Prepare context
        context = {
            "scenario": "industry-research",
            "target": self.request.target,
            "config": self.request.config.dict(),
            "market_analysis": {
                **market_result,
                "market_score": market_result.get("score", 0) # Assuming result has score or similar
            },
            "tech_assessment": tech_result,
            "financial_analysis": financial_result,
            **self.results
        }

        # Call synthesizer in quick mode
        report = await synthesize_report(context, quick_mode=True)

        # Map to QuickJudgmentResult
        rec_map = {
            "invest": RecommendationType.BUY,
            "observe": RecommendationType.FURTHER_DD,
            "reject": RecommendationType.PASS
        }
        recommendation = rec_map.get(report.get("overall_recommendation", "observe"), RecommendationType.FURTHER_DD)
        
        conf_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
        confidence = conf_map.get(report.get("confidence_level", "medium"), 0.7)

        scores_breakdown = report.get("scores_breakdown", {})

        return QuickJudgmentResult(
            recommendation=recommendation,
            confidence=confidence,
            judgment_time=self._calculate_elapsed_time(),
            summary={
                "verdict": report.get("summary", ""),
                "key_positive": report.get("key_findings", [])[:3],
                "key_concern": [f for f in report.get("key_findings", []) if "风险" in f or "不足" in f],
                "red_flags": []
            },
            scores={
                "market": scores_breakdown.get("market", 0),
                "competition": scores_breakdown.get("market", 0), # Proxy
                "trend": scores_breakdown.get("tech", 0),
                "opportunity": scores_breakdown.get("financial", 0),
                "overall": report.get("investment_score", 0)
            },
            next_steps={
                "recommended_action": report.get("next_steps", ["建议进一步分析"])[0] if report.get("next_steps") else "待定",
                "focus_areas": report.get("next_steps", [])[1:]
            }
        )

    def _safe_to_dict(self, data: Any) -> Dict[str, Any]:
        """Helper to convert Pydantic models or dicts to dict and UNWRAP wrapper objects"""
        if data is None:
            return {}
        
        # 1. Convert outer object to dict
        result = {}
        if hasattr(data, 'model_dump'):
            result = data.model_dump()
        elif hasattr(data, 'dict'):
            result = data.dict()
        elif isinstance(data, dict):
            result = data
        else:
            return {} # Unknown type
        
        # 2. Unwrap 'analysis' field if present (Common Agent Wrapper pattern)
        if "analysis" in result:
            analysis_obj = result["analysis"]
            
            # CASE A: Analysis is a String (Markdown report)
            if isinstance(analysis_obj, str):
                print(f"[IndustryOrchestrator] 'analysis' is a STRING. Wrapping as summary.", flush=True)
                # Create a synthetic dict structure
                analysis_content = {
                    "summary": analysis_obj, 
                    "raw_output": analysis_obj
                }
                # Inject score from wrapper if missing
                if "score" in result:
                    analysis_content["score"] = result["score"]
                return analysis_content

            # CASE B: Analysis is a Structured Object (Dict or Pydantic)
            analysis_content = {}
            if hasattr(analysis_obj, 'model_dump'):
                analysis_content = analysis_obj.model_dump()
            elif hasattr(analysis_obj, 'dict'):
                analysis_content = analysis_obj.dict()
            elif isinstance(analysis_obj, dict):
                analysis_content = analysis_obj
            
            if analysis_content:
                print(f"[IndustryOrchestrator] Unwrapping structured 'analysis' field", flush=True)
                # Inject score from wrapper if missing in analysis
                if "score" in result and "score" not in analysis_content:
                    analysis_content["score"] = result["score"]
                return analysis_content

        return result

    async def _synthesize_final_report(self) -> Dict[str, Any]:
        """
        综合生成行业研究报告
        """
        # Import synthesizer
        from app.agents.report_synthesizer_agent import synthesize_report
        import json
        
        # DEBUG LOGGING
        try:
            results_debug = json.dumps(self.results, default=str, ensure_ascii=False, indent=2)
            print(f"[IndustryOrchestrator] FULL RESULTS DUMP:\n{results_debug}", flush=True)
        except Exception as e:
            print(f"[IndustryOrchestrator] Failed to dump results: {e}", flush=True)

        # Ensure target has a name for the report cover AND persistence
        if not self.request.target.get('company_name'):
            industry = self.request.target.get('industry_name', '行业研究')
            self.request.target['company_name'] = industry

        # Retrieve results using step IDs from workflows.yaml (strings "1", "2", "3")
        market_result = self._safe_to_dict(self.results.get("1"))
        tech_result = self._safe_to_dict(self.results.get("2"))
        financial_result = self._safe_to_dict(self.results.get("3"))
        
        # --- Map specific agent fields to generic 'summary' for Synthesizer extraction ---
        
        # Financial Agent returns 'business_model_assessment', map to 'summary'
        if not financial_result.get("summary") and financial_result.get("business_model_assessment"):
            financial_result["summary"] = financial_result["business_model_assessment"]
            
        # Tech Agent might return 'tech_foundation_check' -> 'summary'
        if not tech_result.get("summary") and "tech_foundation_check" in tech_result:
            check = tech_result["tech_foundation_check"]
            if isinstance(check, dict) and check.get("summary"):
                tech_result["summary"] = check.get("summary")
        
        print(f"[IndustryOrchestrator] Extracted Results:", flush=True)
        print(f"  - Market keys: {list(market_result.keys())}", flush=True)
        print(f"  - Tech keys: {list(tech_result.keys())}", flush=True)
        print(f"  - Financial keys: {list(financial_result.keys())}", flush=True)

        # Prepare context for synthesizer
        context = {
            "scenario": InvestmentScenario.INDUSTRY_RESEARCH.value,
            "target": self.request.target,
            "config": self.request.config.dict(),
            
            # Map results from workflow steps to standard keys expected by synthesizer
            "market_analysis": {
                **market_result,
                "market_size_estimate": market_result.get("market_validation", "N/A"), 
                "growth_rate": market_result.get("growth_potential", "N/A"),
            },
            "tech_assessment": {
                 **tech_result,
                 "tech_score": tech_result.get("tech_score", 80)
            },
            "financial_analysis": financial_result,
            
            # Risk often distributed; synthesize risks from all components
            "risk_assessment": {
                 "red_flags": (
                     market_result.get("red_flags", []) + 
                     tech_result.get("risks", []) +
                     financial_result.get("risks", [])
                 ),
                 "risk_score": 75 # Placeholder
            },
            # Include raw results for robust access
            **self.results
        }
        
        # Call synthesizer
        report = await synthesize_report(context, quick_mode=False)
        
        return report
