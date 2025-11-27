"""
Public Market Investment Orchestrator (公开市场投资协调器)

场景: 上市公司股票/ETF投资分析
关注点: 估值、技术分析、基本面、市场情绪
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


class PublicMarketInvestmentOrchestrator(BaseOrchestrator):
    """
    公开市场投资Orchestrator

    适用场景:
    - 上市公司股票分析
    - ETF分析
    - 指数分析

    分析重点:
    - 估值 (35%)
    - 基本面 (30%)
    - 技术面 (20%)
    - 市场情绪 (15%)
    """

    def __init__(self, session_id: str, request: Any, websocket: Any = None):
        super().__init__(
            scenario=InvestmentScenario.PUBLIC_MARKET,
            session_id=session_id,
            request=request,
            websocket=websocket
        )
        self.scenario_name = "公开市场投资"

        # Phase 2: Agents now loaded from AgentRegistry, no need for service URLs here

    async def _validate_target(self) -> bool:
        """
        验证公开市场投资目标

        必填:
        - ticker: 股票代码 (如: AAPL, TSLA)

        可选:
        - exchange: 交易所 (NASDAQ, NYSE, etc)
        - asset_type: 资产类型 (stock, etf, index)
        """
        await self._send_status(
            "initializing",
            f"正在验证{self.scenario_name}分析目标..."
        )

        target = self.request.target

        # Support 'stock_code' from frontend (alias to ticker)
        if not target.get('ticker') and target.get('stock_code'):
            target['ticker'] = target.get('stock_code')

        # 检查必填字段
        if not target.get('ticker'):
            raise ValueError("缺少股票代码 (ticker)")

        return True

    async def _synthesize_quick_judgment(self) -> QuickJudgmentResult:
        """
        综合快速判断结果 (公开市场投资)
        """
        from app.agents.report_synthesizer_agent import synthesize_report
        from ...models.analysis_models import QuickJudgmentResult, RecommendationType

        # Prepare context
        context = {
            "scenario": "public-market-investment",
            "target": self.request.target,
            "config": self.request.config.dict(),
            "financial_analysis": {
                **self.results.get("valuation_check", {}),
                **self.results.get("fundamentals_check", {}),
                # Map score
                "financial_score": self.results.get("fundamentals_check", {}).get("fundamentals_score", 0)
            },
            "tech_assessment": self.results.get("technical_check", {}),
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
                "valuation": scores_breakdown.get("financial", 0), # Using financial score as proxy
                "fundamentals": scores_breakdown.get("financial", 0),
                "technical": scores_breakdown.get("tech", 0),
                "sentiment": 0.5, # Mock for now
                "overall": report.get("investment_score", 0)
            },
            next_steps={
                "recommended_action": report.get("next_steps", ["建议进一步分析"])[0] if report.get("next_steps") else "待定",
                "focus_areas": report.get("next_steps", [])[1:]
            }
        )

    async def _synthesize_final_report(self) -> Dict[str, Any]:
        """
        综合生成公开市场投资分析报告
        """
        # Import synthesizer
        from app.agents.report_synthesizer_agent import synthesize_report

        # Prepare context for synthesizer
        # Map workflow specific step IDs to standard keys
        context = {
            "scenario": "public-market-investment",
            "target": self.request.target,
            "config": self.request.config.dict(),
            
            # Map step results
            "financial_analysis": {
                **self.results.get("fundamental_analysis", {}),
                # Valuation check often done separately or part of fundamentals
                "valuation_level": self.results.get("valuation_check", {}),
            },
            "market_analysis": {
                **self.results.get("industry_comparison", {}),
                "market_score": self.results.get("technical_analysis", {}).get("technical_score", 0) # Using technical score as proxy for 'market timing/momentum'
            },
            "tech_assessment": self.results.get("technical_analysis", {}), # Technical analysis
            "risk_assessment": self.results.get("risk_assessment", {}),
            
            # Raw results access
            **self.results
        }

        # Call synthesizer
        report = await synthesize_report(context, quick_mode=False)
        
        return report
