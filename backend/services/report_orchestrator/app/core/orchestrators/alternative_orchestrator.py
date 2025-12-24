"""
Alternative Investment Orchestrator (另类投资协调器)

场景: Crypto/DeFi/NFT等另类资产投资分析
关注点: 技术基础、社区、代币经济学、风险
"""

from typing import Dict, Any

from .base_orchestrator import BaseOrchestrator
from ...models.analysis_models import (
    InvestmentScenario,
    QuickJudgmentResult
)
# Phase 2: All agents now loaded from AgentRegistry
# Legacy imports removed


class AlternativeInvestmentOrchestrator(BaseOrchestrator):
    """
    另类投资Orchestrator

    适用场景:
    - 加密货币 (BTC, ETH, etc)
    - DeFi协议
    - NFT项目
    - Web3项目

    分析重点:
    - 技术基础 (30%)
    - 代币经济学 (25%)
    - 社区活跃度 (25%)
    - 团队背景 (20%)
    """

    def __init__(self, session_id: str, request: Any, websocket: Any = None):
        super().__init__(
            scenario=InvestmentScenario.ALTERNATIVE,
            session_id=session_id,
            request=request,
            websocket=websocket
        )
        self.scenario_name = "另类投资"

        # Phase 2: Agents now loaded from AgentRegistry, no need for service URLs here

    async def _validate_target(self) -> bool:
        """
        验证另类投资目标

        必填:
        - asset_type: 资产类型 (crypto, defi, nft, web3)

        可选:
        - symbol: 代币符号 (如: BTC, ETH)
        - contract_address: 合约地址
        - chain: 区块链 (ethereum, bsc, solana, etc)
        - project_name: 项目名称
        """
        await self._send_status(
            "initializing",
            f"正在验证{self.scenario_name}分析目标..."
        )

        target = self.request.target

        # 检查必填字段
        if not target.get('asset_type'):
            raise ValueError("缺少资产类型 (asset_type)")

        # 验证asset_type
        valid_types = ['crypto', 'defi', 'nft', 'web3']
        if target.get('asset_type') not in valid_types:
            raise ValueError(f"不支持的资产类型: {target.get('asset_type')}, 请选择: {', '.join(valid_types)}")

        return True

    async def _synthesize_quick_judgment(self) -> QuickJudgmentResult:
        """
        综合快速判断结果 (另类投资)
        """
        from app.agents.report_synthesizer_agent import synthesize_report
        from ...models.analysis_models import QuickJudgmentResult, RecommendationType

        # Prepare context
        context = {
            "scenario": "alternative-investment",
            "target": self.request.target,
            "config": self.request.config.dict(),
            "tech_assessment": self.results.get("tech_foundation_check", {}),
            "financial_analysis": self.results.get("tokenomics_check", {}),
            "market_analysis": self.results.get("community_check", {}),
            "risk_assessment": self.results.get("risk_scan", {}),
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
                "red_flags": self.results.get("risk_scan", {}).get("red_flags", [])
            },
            scores={
                "tech": scores_breakdown.get("tech", 0),
                "tokenomics": scores_breakdown.get("financial", 0),
                "community": scores_breakdown.get("market", 0),
                "team": 0.5, # Mock
                "overall": report.get("investment_score", 0)
            },
            next_steps={
                "recommended_action": report.get("next_steps", ["建议进一步分析"])[0] if report.get("next_steps") else "待定",
                "focus_areas": report.get("next_steps", [])[1:]
            }
        )

    async def _synthesize_final_report(self) -> Dict[str, Any]:
        """
        综合生成另类投资分析报告
        """
        # Import synthesizer
        from app.agents.report_synthesizer_agent import synthesize_report

        # Prepare context for synthesizer
        # Map workflow specific step IDs to standard keys
        context = {
            "scenario": "alternative-investment",
            "target": self.request.target,
            "config": self.request.config.dict(),
            
            # Map step results
            "tech_assessment": {
                **self.results.get("tech_foundation_check", {}),
                **self.results.get("onchain_analysis", {}),
                # Map tech score
                "tech_score": self.results.get("tech_foundation_check", {}).get("score", 0)
            },
            "market_analysis": {
                **self.results.get("community_assessment", {}), # Community is market in crypto
                **self.results.get("project_research", {}),
                # Map community score to market score concept
                "market_score": self.results.get("community_assessment", {}).get("community_score", 0)
            },
            "financial_analysis": {
                **self.results.get("tokenomics_analysis", {}),
                # Tokenomics is financials
                "financial_score": self.results.get("tokenomics_check", {}).get("score", 0)
            },
            "risk_assessment": self.results.get("risk_assessment", {}),
            
            # Raw results access
            **self.results
        }

        # Call synthesizer
        report = await synthesize_report(context, quick_mode=False)
        
        return report
