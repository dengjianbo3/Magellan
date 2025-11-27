"""
Growth Investment Orchestrator (成长期投资协调器)

场景: Series B+ 公司的成长期投资分析
关注点: 财务数据、增长率、市场扩张、运营效率
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


class GrowthInvestmentOrchestrator(BaseOrchestrator):
    """
    成长期投资Orchestrator

    适用场景:
    - Series B/C/D/E 融资
    - Pre-IPO 公司

    分析重点:
    - 财务健康度 (40%)
    - 增长潜力 (35%)
    - 市场地位 (25%)
    """

    def __init__(self, session_id: str, request: Any, websocket: Any = None):
        super().__init__(
            scenario=InvestmentScenario.GROWTH,
            session_id=session_id,
            request=request,
            websocket=websocket
        )
        self.scenario_name = "成长期投资"

        # Phase 2: Agents now loaded from AgentRegistry, no need for service URLs here

    async def _validate_target(self) -> bool:
        """
        验证成长期投资目标

        必填:
        - company_name: 公司名称
        - stage: 融资阶段 (series-b, series-c, series-d, series-e, pre-ipo)

        可选:
        - annual_revenue: 年收入
        - growth_rate: 增长率
        - financial_file_id: 财务报表文件ID
        """
        await self._send_status(
            "initializing",
            f"正在验证{self.scenario_name}分析目标..."
        )

        target = self.request.target

        # 检查必填字段
        if not target.get('company_name'):
            raise ValueError("缺少公司名称 (company_name)")

        if not target.get('stage'):
            raise ValueError("缺少融资阶段 (stage)")

        # 验证stage是否合法
        valid_stages = ['series-b', 'series-c', 'series-d', 'series-e', 'pre-ipo']
        if target.get('stage') not in valid_stages:
            raise ValueError(f"不支持的融资阶段: {target.get('stage')}, 请选择: {', '.join(valid_stages)}")

        return True

    async def _synthesize_quick_judgment(self) -> QuickJudgmentResult:
        """
        综合快速判断结果 (成长期投资)
        """
        from app.agents.report_synthesizer_agent import synthesize_report
        from ...models.analysis_models import QuickJudgmentResult, RecommendationType

        # Prepare context
        context = {
            "scenario": "growth-investment",
            "target": self.request.target,
            "config": self.request.config.dict(),
            "financial_analysis": self.results.get("financial_health_check", {}),
            "market_analysis": {
                **self.results.get("growth_assessment", {}),
                **self.results.get("market_position_check", {}),
                # Map growth score to market score
                "market_score": self.results.get("growth_assessment", {}).get("score", 0)
            },
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
                "red_flags": [] # Growth quick mode might not have explicit red flag step
            },
            scores={
                "financial": scores_breakdown.get("financial", 0),
                "growth": scores_breakdown.get("market", 0), # Using market score as proxy for growth
                "market": scores_breakdown.get("market", 0),
                "overall": report.get("investment_score", 0)
            },
            next_steps={
                "recommended_action": report.get("next_steps", ["建议进一步分析"])[0] if report.get("next_steps") else "待定",
                "focus_areas": report.get("next_steps", [])[1:]
            }
        )

    async def _synthesize_final_report(self) -> Dict[str, Any]:
        """
        综合生成成长期投资分析报告
        """
        # Import synthesizer
        from app.agents.report_synthesizer_agent import synthesize_report

        # Prepare context for synthesizer
        # Map workflow specific step IDs to standard keys
        context = {
            "scenario": "growth-investment",
            "target": self.request.target,
            "config": self.request.config.dict(),
            
            # Map step results
            "financial_analysis": {
                **self.results.get("financial_analysis", {}),
                **self.results.get("valuation_modeling", {}),
                # Growth specific metrics
                "financial_score": self.results.get("financial_analysis", {}).get("financial_score", 0),
            },
            "market_analysis": {
                **self.results.get("growth_quality_assessment", {}),
                **self.results.get("competitive_analysis", {}),
                # Map growth score to market score concept for synthesizer
                "market_score": self.results.get("growth_quality_assessment", {}).get("growth_score", 0),
                "opportunities": self.results.get("growth_quality_assessment", {}).get("growth_drivers", [])
            },
            # Raw results access
            **self.results
        }

        # Call synthesizer
        report = await synthesize_report(context, quick_mode=False)
        
        return report
