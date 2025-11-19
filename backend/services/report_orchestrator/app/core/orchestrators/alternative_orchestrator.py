"""
Alternative Investment Orchestrator (另类投资协调器)

场景: Crypto/DeFi/NFT等另类资产投资分析
关注点: 技术基础、社区、代币经济学、风险
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
    TechFoundationAgent,
    TokenomicsAgent,
    CommunityActivityAgent
)
from ...agents.crypto_analyst_agent import CryptoAnalystAgent


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
        # Service URLs (必须在super().__init__之前定义,因为_init_agent_pool会被调用)
        self.LLM_GATEWAY_URL = "http://llm_gateway:8003"
        self.WEB_SEARCH_URL = "http://web_search_service:8010"
        self.USER_SERVICE_URL = "http://user_service:8008"

        super().__init__(
            scenario=InvestmentScenario.ALTERNATIVE,
            session_id=session_id,
            request=request,
            websocket=websocket
        )
        self.scenario_name = "另类投资"

    def _init_agent_pool(self) -> Dict[str, Any]:
        """
        初始化另类投资场景的专业Agent池
        """
        return {
            "tech_analyst": TechFoundationAgent(web_search_url=self.WEB_SEARCH_URL),
            "tokenomics_expert": TokenomicsAgent(web_search_url=self.WEB_SEARCH_URL),
            "community_analyzer": CommunityActivityAgent(web_search_url=self.WEB_SEARCH_URL),
            "crypto_analyst": CryptoAnalystAgent(
                web_search_url=self.WEB_SEARCH_URL,
                llm_gateway_url=self.LLM_GATEWAY_URL
            ),
        }

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

        Quick Mode Workflow:
        1. tech_foundation_check: 技术基础检查
        2. tokenomics_check: 代币经济学检查
        3. community_check: 社区检查
        4. risk_scan: 风险扫描
        5. quick_judgment: 快速综合判断

        评分权重:
        - 技术基础: 30%
        - 代币经济学: 25%
        - 社区: 25%
        - 团队: 20%
        """
        # Mock实现
        tech_score = self.results.get('tech_foundation_check', {}).get('score', 0.5)
        tokenomics_score = self.results.get('tokenomics_check', {}).get('score', 0.5)
        community_score = self.results.get('community_check', {}).get('score', 0.5)
        team_score = 0.5  # Mock

        # 加权计算总分
        overall_score = (
            tech_score * 0.30 +
            tokenomics_score * 0.25 +
            community_score * 0.25 +
            team_score * 0.20
        )

        # 另类投资风险较高,标准更严格
        if overall_score >= 0.80:
            recommendation = RecommendationType.BUY
            verdict = "项目基本面扎实,可以考虑投资"
            confidence = 0.70  # 即使推荐,信心也相对保守
        elif overall_score >= 0.65:
            recommendation = RecommendationType.FURTHER_DD
            verdict = "项目有潜力但风险较高,需深入研究"
            confidence = 0.55
        else:
            recommendation = RecommendationType.PASS
            verdict = "基本面或风险因素不理想,不建议投资"
            confidence = 0.75

        key_positive = []
        key_concern = []
        red_flags = []

        if tech_score >= 0.7:
            key_positive.append("技术架构稳健")
        elif tech_score < 0.5:
            red_flags.append("技术风险较高")

        if tokenomics_score >= 0.7:
            key_positive.append("代币经济学设计合理")
        elif tokenomics_score < 0.5:
            red_flags.append("代币经济学存在问题")

        if community_score >= 0.7:
            key_positive.append("社区活跃度高")
        elif community_score < 0.5:
            key_concern.append("社区活跃度不足")

        # 另类投资特有的风险提示
        red_flags.append("市场波动性极高")
        red_flags.append("监管政策不确定")

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
                "tech": round(tech_score, 2),
                "tokenomics": round(tokenomics_score, 2),
                "community": round(community_score, 2),
                "team": round(team_score, 2),
                "overall": round(overall_score, 2)
            },
            next_steps={
                "recommended_action": "小仓位试水" if recommendation == RecommendationType.BUY else ("继续观察" if recommendation == RecommendationType.FURTHER_DD else "回避"),
                "focus_areas": [
                    "智能合约审计报告",
                    "团队背景调查",
                    "社区情绪分析",
                    "竞品对比",
                    "风险控制策略"
                ] if recommendation != RecommendationType.PASS else []
            }
        )

    async def _synthesize_final_report(self) -> Dict[str, Any]:
        """
        综合生成另类投资分析报告
        """
        # Mock实现
        return {
            "scenario": InvestmentScenario.ALTERNATIVE.value,
            "asset_type": self.request.target.get('asset_type'),
            "project_name": self.request.target.get('project_name', 'Unknown'),
            "analysis_depth": self.request.config.depth.value,
            "final_recommendation": "FURTHER_DD",
            "overall_score": 0.68,
            "risk_level": "HIGH",
            "sections": {
                "tech_analysis": {
                    "score": 0.70,
                    "summary": "技术架构合理,但缺乏审计"
                },
                "tokenomics": {
                    "score": 0.65,
                    "summary": "代币分配尚可,需关注解锁时间表"
                },
                "community": {
                    "score": 0.72,
                    "summary": "社区活跃,但存在炒作成分"
                },
                "risk_assessment": {
                    "score": 0.45,
                    "summary": "高风险项目,市场波动大,监管不确定"
                }
            }
        }
