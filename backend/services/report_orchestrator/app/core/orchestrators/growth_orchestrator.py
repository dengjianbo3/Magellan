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

        Quick Mode Workflow:
        1. financial_health_check: 财务健康检查
        2. growth_assessment: 增长潜力评估
        3. market_position_check: 市场地位检查
        4. quick_judgment: 快速综合判断

        评分权重:
        - 财务健康度: 40%
        - 增长潜力: 35%
        - 市场地位: 25%
        """
        # Mock实现 - 实际需要LLM分析
        financial_score = self.results.get('financial_health_check', {}).get('score', 0.5)
        growth_score = self.results.get('growth_assessment', {}).get('score', 0.5)
        market_score = self.results.get('market_position_check', {}).get('score', 0.5)

        # 加权计算总分
        overall_score = (
            financial_score * 0.40 +
            growth_score * 0.35 +
            market_score * 0.25
        )

        # 确定推荐
        if overall_score >= 0.75:
            recommendation = RecommendationType.BUY
            verdict = "财务健康,增长强劲,建议投资"
            confidence = 0.8
        elif overall_score >= 0.6:
            recommendation = RecommendationType.FURTHER_DD
            verdict = "财务稳健但需要深入了解增长策略"
            confidence = 0.65
        else:
            recommendation = RecommendationType.PASS
            verdict = "财务或增长数据不理想,暂不建议投资"
            confidence = 0.7

        # 构建关键发现
        key_positive = []
        key_concern = []
        red_flags = []

        if financial_score >= 0.7:
            key_positive.append("财务健康度良好")
        elif financial_score < 0.5:
            key_concern.append("财务健康度需要改善")

        if growth_score >= 0.7:
            key_positive.append("增长潜力强劲")
        elif growth_score < 0.5:
            red_flags.append("增长放缓风险")

        if market_score >= 0.7:
            key_positive.append("市场地位稳固")
        elif market_score < 0.5:
            key_concern.append("市场竞争激烈")

        # 计算用时
        judgment_time = f"{int((datetime.now() - self.start_time).total_seconds() // 60)}分{int((datetime.now() - self.start_time).total_seconds() % 60)}秒"

        return QuickJudgmentResult(
            recommendation=recommendation,
            confidence=confidence,
            judgment_time=judgment_time,
            summary={
                "verdict": verdict,
                "key_positive": key_positive,
                "key_concern": key_concern,
                "red_flags": red_flags
            },
            scores={
                "financial": round(financial_score, 2),
                "growth": round(growth_score, 2),
                "market": round(market_score, 2),
                "overall": round(overall_score, 2)
            },
            next_steps={
                "recommended_action": "进行标准尽调" if recommendation == RecommendationType.FURTHER_DD else ("深入投资" if recommendation == RecommendationType.BUY else "暂缓投资"),
                "focus_areas": [
                    "详细财务建模",
                    "增长驱动因素分析",
                    "竞争优势验证",
                    "管理团队访谈"
                ] if recommendation != RecommendationType.PASS else []
            },
            is_mock=True
        )

    async def _synthesize_final_report(self) -> Dict[str, Any]:
        """
        综合生成成长期投资分析报告 (Standard/Comprehensive模式)

        Standard Mode Workflow (6-7步):
        1. 财务深度分析
        2. 增长驱动因素分析
        3. 市场竞争分析
        4. 运营效率评估
        5. 管理团队评估
        6. 风险评估
        7. 估值分析
        """
        # Mock实现
        return {
            "scenario": InvestmentScenario.GROWTH.value,
            "company_name": self.request.target.get('company_name'),
            "stage": self.request.target.get('stage'),
            "analysis_depth": self.request.config.depth.value,
            "final_recommendation": "FURTHER_DD",
            "overall_score": 0.72,
            "sections": {
                "financial_analysis": {
                    "score": 0.75,
                    "summary": "财务状况良好,收入增长稳定"
                },
                "growth_analysis": {
                    "score": 0.70,
                    "summary": "增长驱动因素清晰,市场空间充足"
                },
                "market_analysis": {
                    "score": 0.68,
                    "summary": "市场地位稳固,但竞争加剧"
                },
                "risk_assessment": {
                    "score": 0.65,
                    "summary": "主要风险为市场竞争和增长放缓"
                }
            },
            "next_steps": [
                "财务建模和估值分析",
                "管理团队尽调",
                "客户访谈"
            ],
            "is_mock": True
        }
