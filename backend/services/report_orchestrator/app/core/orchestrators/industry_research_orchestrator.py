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
from ..quick_agents import (
    MarketSizeAgent,
    CompetitionLandscapeAgent,
    TrendAnalysisAgent,
    OpportunityScanAgent,
    IndustryResearcherAgent
)


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
        # Service URLs (必须在super().__init__之前定义,因为_init_agent_pool会被调用)
        self.LLM_GATEWAY_URL = "http://llm_gateway:8003"
        self.WEB_SEARCH_URL = "http://web_search_service:8010"
        self.USER_SERVICE_URL = "http://user_service:8008"

        super().__init__(
            scenario=InvestmentScenario.INDUSTRY_RESEARCH,
            session_id=session_id,
            request=request,
            websocket=websocket
        )
        self.scenario_name = "行业研究"

    def _init_agent_pool(self) -> Dict[str, Any]:
        """
        初始化行业研究场景的专业Agent池
        """
        return {
            "market_analyst": MarketSizeAgent(web_search_url=self.WEB_SEARCH_URL),
            "competition_analyst": CompetitionLandscapeAgent(web_search_url=self.WEB_SEARCH_URL),
            "trend_researcher": TrendAnalysisAgent(web_search_url=self.WEB_SEARCH_URL),
            "opportunity_scanner": OpportunityScanAgent(web_search_url=self.WEB_SEARCH_URL),
            "industry_researcher": IndustryResearcherAgent(web_search_url=self.WEB_SEARCH_URL),
        }

    async def _validate_target(self) -> bool:
        """
        验证行业研究目标

        必填:
        - industry_name: 行业名称 (如: 人工智能, 新能源汽车)
        - research_topic: 研究主题 (如: 2024年AI芯片市场趋势)

        可选:
        - geo_scope: 地域范围 (global, china, us, etc)
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

        if not target.get('research_topic'):
            raise ValueError("缺少研究主题 (research_topic)")

        return True

    async def _synthesize_quick_judgment(self) -> QuickJudgmentResult:
        """
        综合快速判断结果 (行业研究)

        Quick Mode Workflow:
        1. market_size_check: 市场规模检查
        2. competition_landscape: 竞争格局分析
        3. trend_analysis: 趋势分析
        4. opportunity_scan: 机会扫描
        5. quick_summary: 快速总结

        评分权重:
        - 市场规模与增长: 30%
        - 竞争格局: 25%
        - 技术趋势: 25%
        - 投资机会: 20%
        """
        # Mock实现
        market_score = self.results.get('market_size_check', {}).get('score', 0.5)
        competition_score = self.results.get('competition_landscape', {}).get('score', 0.5)
        trend_score = self.results.get('trend_analysis', {}).get('score', 0.5)
        opportunity_score = self.results.get('opportunity_scan', {}).get('score', 0.5)

        # 加权计算总分
        overall_score = (
            market_score * 0.30 +
            competition_score * 0.25 +
            trend_score * 0.25 +
            opportunity_score * 0.20
        )

        # 行业研究的"推荐"含义不同
        if overall_score >= 0.75:
            recommendation = RecommendationType.BUY
            verdict = "行业前景优秀,建议重点关注投资机会"
            confidence = 0.80
        elif overall_score >= 0.60:
            recommendation = RecommendationType.FURTHER_DD
            verdict = "行业有潜力,建议深入研究细分赛道"
            confidence = 0.70
        else:
            recommendation = RecommendationType.PASS
            verdict = "行业增长放缓或竞争过度,谨慎投资"
            confidence = 0.75

        key_positive = []
        key_concern = []
        red_flags = []

        if market_score >= 0.7:
            key_positive.append("市场规模大且增长快")
        elif market_score < 0.5:
            key_concern.append("市场增长放缓")

        if competition_score >= 0.7:
            key_positive.append("竞争格局清晰,有头部机会")
        elif competition_score < 0.5:
            red_flags.append("竞争过度激烈")

        if trend_score >= 0.7:
            key_positive.append("技术趋势向好")
        elif trend_score < 0.5:
            key_concern.append("技术路线不确定")

        if opportunity_score >= 0.7:
            key_positive.append("存在明确投资机会")

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
                "market": round(market_score, 2),
                "competition": round(competition_score, 2),
                "trend": round(trend_score, 2),
                "opportunity": round(opportunity_score, 2),
                "overall": round(overall_score, 2)
            },
            next_steps={
                "recommended_action": "深入研究头部标的" if recommendation == RecommendationType.BUY else ("继续跟踪行业动态" if recommendation == RecommendationType.FURTHER_DD else "转向其他赛道"),
                "focus_areas": [
                    "细分赛道深度分析",
                    "头部公司对比",
                    "投资时机判断",
                    "风险因素研究"
                ] if recommendation != RecommendationType.PASS else [
                    "寻找替代赛道"
                ]
            }
        )

    async def _synthesize_final_report(self) -> Dict[str, Any]:
        """
        综合生成行业研究报告
        """
        # Mock实现
        return {
            "scenario": InvestmentScenario.INDUSTRY_RESEARCH.value,
            "industry_name": self.request.target.get('industry_name'),
            "research_topic": self.request.target.get('research_topic'),
            "analysis_depth": self.request.config.depth.value,
            "final_recommendation": "BUY",
            "overall_score": 0.82,
            "sections": {
                "market_analysis": {
                    "score": 0.85,
                    "summary": "市场规模达1000亿,年增长30%"
                },
                "competition": {
                    "score": 0.78,
                    "summary": "形成三大头部,中尾部机会丰富"
                },
                "trend_analysis": {
                    "score": 0.80,
                    "summary": "AI+行业融合加速,技术路线清晰"
                },
                "investment_opportunities": {
                    "score": 0.85,
                    "summary": "识别5个高潜力细分赛道"
                }
            },
            "key_findings": [
                "行业处于快速增长期",
                "政策支持力度大",
                "技术成熟度提升",
                "头部公司估值合理"
            ],
            "recommended_targets": [
                "细分赛道A的头部公司",
                "垂直领域B的创新企业",
                "上下游产业链关键环节"
            ]
        }
