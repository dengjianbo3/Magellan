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
from ..quick_agents import (
    ValuationQuickAgent,
    FundamentalsAgent,
    TechnicalAnalysisAgent,
    DataFetcherAgent
)
from ...agents.financial_expert_agent import FinancialExpertAgent


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
        # Service URLs (必须在super().__init__之前定义,因为_init_agent_pool会被调用)
        self.LLM_GATEWAY_URL = "http://llm_gateway:8003"
        self.WEB_SEARCH_URL = "http://web_search_service:8010"
        self.USER_SERVICE_URL = "http://user_service:8008"

        super().__init__(
            scenario=InvestmentScenario.PUBLIC_MARKET,
            session_id=session_id,
            request=request,
            websocket=websocket
        )
        self.scenario_name = "公开市场投资"

    def _init_agent_pool(self) -> Dict[str, Any]:
        """
        初始化公开市场投资场景的专业Agent池
        """
        return {
            "valuation_expert": ValuationQuickAgent(web_search_url=self.WEB_SEARCH_URL),
            "fundamental_analyst": FundamentalsAgent(web_search_url=self.WEB_SEARCH_URL),
            "technical_analyst": TechnicalAnalysisAgent(web_search_url=self.WEB_SEARCH_URL),
            "data_fetcher": DataFetcherAgent(),
            "financial_expert": FinancialExpertAgent(
                web_search_url=self.WEB_SEARCH_URL,
                llm_gateway_url=self.LLM_GATEWAY_URL
            ),
        }

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

        # 检查必填字段
        if not target.get('ticker'):
            raise ValueError("缺少股票代码 (ticker)")

        return True

    async def _synthesize_quick_judgment(self) -> QuickJudgmentResult:
        """
        综合快速判断结果 (公开市场投资)

        Quick Mode Workflow:
        1. valuation_check: 估值检查
        2. fundamentals_check: 基本面检查
        3. technical_check: 技术面检查
        4. quick_judgment: 快速综合判断

        评分权重:
        - 估值: 35%
        - 基本面: 30%
        - 技术面: 20%
        - 市场情绪: 15%
        """
        # Mock实现
        valuation_score = self.results.get('valuation_check', {}).get('score', 0.5)
        fundamentals_score = self.results.get('fundamentals_check', {}).get('score', 0.5)
        technical_score = self.results.get('technical_check', {}).get('score', 0.5)
        sentiment_score = 0.5  # Mock

        # 加权计算总分
        overall_score = (
            valuation_score * 0.35 +
            fundamentals_score * 0.30 +
            technical_score * 0.20 +
            sentiment_score * 0.15
        )

        # 确定推荐
        if overall_score >= 0.75:
            recommendation = RecommendationType.BUY
            verdict = "估值合理,基本面良好,建议买入"
            confidence = 0.75
        elif overall_score >= 0.6:
            recommendation = RecommendationType.FURTHER_DD
            verdict = "需要进一步分析市场时机"
            confidence = 0.6
        else:
            recommendation = RecommendationType.PASS
            verdict = "估值偏高或基本面转弱,暂不建议"
            confidence = 0.65

        key_positive = []
        key_concern = []
        red_flags = []

        if valuation_score >= 0.7:
            key_positive.append("估值合理")
        elif valuation_score < 0.5:
            red_flags.append("估值偏高")

        if fundamentals_score >= 0.7:
            key_positive.append("基本面稳健")
        elif fundamentals_score < 0.5:
            key_concern.append("基本面转弱")

        if technical_score >= 0.7:
            key_positive.append("技术面良好")

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
                "valuation": round(valuation_score, 2),
                "fundamentals": round(fundamentals_score, 2),
                "technical": round(technical_score, 2),
                "sentiment": round(sentiment_score, 2),
                "overall": round(overall_score, 2)
            },
            next_steps={
                "recommended_action": "建仓" if recommendation == RecommendationType.BUY else ("观望" if recommendation == RecommendationType.FURTHER_DD else "回避"),
                "focus_areas": [
                    "详细估值模型",
                    "财报深度分析",
                    "行业对比",
                    "市场时机把握"
                ] if recommendation != RecommendationType.PASS else []
            }
        )

    async def _synthesize_final_report(self) -> Dict[str, Any]:
        """
        综合生成公开市场投资分析报告
        """
        # Mock实现
        return {
            "scenario": InvestmentScenario.PUBLIC_MARKET.value,
            "ticker": self.request.target.get('ticker'),
            "analysis_depth": self.request.config.depth.value,
            "final_recommendation": "BUY",
            "overall_score": 0.78,
            "sections": {
                "valuation": {
                    "score": 0.80,
                    "summary": "PE估值合理,处于历史中位"
                },
                "fundamentals": {
                    "score": 0.75,
                    "summary": "营收增长稳定,利润率改善"
                },
                "technical": {
                    "score": 0.70,
                    "summary": "突破关键阻力位,趋势向好"
                }
            }
        }
