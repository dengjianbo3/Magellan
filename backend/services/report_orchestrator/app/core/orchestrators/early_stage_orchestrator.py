"""
EarlyStageInvestmentOrchestrator - 早期投资场景协调器
继承BaseOrchestrator,实现早期投资(Angel/Seed/Series A)的分析逻辑
"""

from typing import Dict, Any, List, Optional
from fastapi import WebSocket

from app.models.analysis_models import (
    AnalysisRequest,
    InvestmentScenario,
    EarlyStageTarget
)
from app.core.orchestrators.base_orchestrator import BaseOrchestrator
from app.core.quick_agents import TeamQuickAgent, MarketQuickAgent, RedFlagAgent


class EarlyStageInvestmentOrchestrator(BaseOrchestrator):
    """
    早期投资场景协调器

    核心关注:
    - 团队能力 (40%)
    - 市场机会 (35%)
    - 产品创新 (25%)
    """

    def __init__(
        self,
        session_id: str,
        request: AnalysisRequest,
        websocket: Optional[WebSocket] = None
    ):
        super().__init__(
            scenario=InvestmentScenario.EARLY_STAGE,
            session_id=session_id,
            request=request,
            websocket=websocket
        )

        # 解析early-stage specific target
        self.target: EarlyStageTarget = EarlyStageTarget(**request.target)

        # Service URLs (从环境变量获取,暂时硬编码)
        self.LLM_GATEWAY_URL = "http://llm_gateway:8003"
        self.WEB_SEARCH_URL = "http://web_search_service:8010"
        self.USER_SERVICE_URL = "http://user_service:8008"

    def _init_agent_pool(self) -> Dict[str, Any]:
        """
        初始化早期投资场景的专业Agent池
        """
        # Phase 3: 实现真实的快速判断Agent
        return {
            "team_evaluator": TeamQuickAgent(web_search_url=self.WEB_SEARCH_URL),
            "market_analyst": MarketQuickAgent(web_search_url=self.WEB_SEARCH_URL),
            "risk_assessor": RedFlagAgent(web_search_url=self.WEB_SEARCH_URL),
        }

    async def _validate_target(self) -> bool:
        """
        验证早期投资目标

        验证项:
        1. 公司名称不为空
        2. 如果有BP文件,验证文件存在性
        3. 融资阶段合法性
        """
        # 1. 公司名称检查
        if not self.target.company_name:
            return False

        # 2. BP文件检查 (如果提供)
        if self.target.bp_file_id:
            # TODO: 验证文件是否存在于/var/uploads
            import os
            file_path = f"/var/uploads/{self.target.bp_file_id}"
            if not os.path.exists(file_path):
                raise ValueError(f"BP文件不存在: {self.target.bp_file_id}")

        # 3. 融资阶段检查
        valid_stages = ["angel", "seed", "pre-a", "series-a"]
        if self.target.stage.lower() not in valid_stages:
            raise ValueError(f"不支持的融资阶段: {self.target.stage}")

        return True

    async def _is_special_case(self) -> bool:
        """
        判断是否为特殊情况

        特殊情况:
        - 没有BP文件
        - 团队成员列表为空
        """
        if not self.target.bp_file_id:
            return True
        if not self.target.team_members or len(self.target.team_members) == 0:
            return True
        return False

    async def _adjust_for_special_case(
        self,
        workflow: List
    ) -> List:
        """
        调整workflow应对特殊情况

        调整策略:
        - 如果没有BP文件,跳过BP解析步骤,改为网络搜索
        - 如果没有团队信息,加强网络搜索步骤
        """
        # 移除BP解析步骤(如果没有文件)
        if not self.target.bp_file_id:
            workflow = [s for s in workflow if s.id != "bp_parsing"]

        return workflow

    async def _synthesize_final_report(self) -> Dict[str, Any]:
        """
        综合生成早期投资分析报告

        核心逻辑:
        1. 提取各步骤结果
        2. 计算综合评分 (团队40% + 市场35% + 产品25%)
        3. 生成投资建议 (INVEST/FURTHER_DD/PASS)
        4. 生成投资备忘录
        """
        # 1. 提取关键结果
        team_analysis = self.results.get("team_deep_investigation", {})
        market_analysis = self.results.get("market_validation", {})
        business_model = self.results.get("business_model_assessment", {})
        cross_validation = self.results.get("cross_validation", {})

        # 2. 计算评分 (默认0.5,如果无数据)
        team_score = team_analysis.get("team_score", 0.5)
        market_score = market_analysis.get("market_attractiveness", 0.5)
        product_score = business_model.get("innovation_score", 0.5)

        # 综合评分
        overall_score = (
            team_score * 0.4 +
            market_score * 0.35 +
            product_score * 0.25
        )

        # 3. 生成建议
        red_flags = cross_validation.get("red_flags", [])

        if len(red_flags) > 0 and overall_score < 0.6:
            recommendation = "PASS"
            reasoning = f"发现{len(red_flags)}个红旗,综合评分{overall_score:.2f}低于投资门槛"
        elif overall_score >= 0.7:
            recommendation = "INVEST"
            reasoning = f"综合评分{overall_score:.2f},建议投资"
        elif overall_score >= 0.5:
            recommendation = "FURTHER_DD"
            reasoning = f"综合评分{overall_score:.2f},建议进行更深入的尽调"
        else:
            recommendation = "PASS"
            reasoning = f"综合评分{overall_score:.2f},不符合投资标准"

        # 4. 提取关键发现
        key_findings = self._extract_key_findings()

        # 5. 生成next steps
        next_steps = self._generate_next_steps(recommendation, red_flags)

        # 6. 构建报告
        report = {
            "scenario": "early-stage-investment",
            "company_name": self.target.company_name,
            "stage": self.target.stage,
            "recommendation": recommendation,
            "investment_score": overall_score,
            "confidence": self._calculate_confidence(),

            "summary": {
                "verdict": reasoning,
                "key_strengths": key_findings.get("strengths", []),
                "key_concerns": key_findings.get("concerns", []),
                "red_flags": red_flags
            },

            "scores": {
                "team": team_score,
                "market": market_score,
                "product": product_score,
                "overall": overall_score
            },

            "detailed_analysis": {
                "team_assessment": team_analysis,
                "market_opportunity": market_analysis,
                "business_model": business_model,
                "risk_factors": cross_validation
            },

            "next_steps": next_steps,

            "generated_at": self._get_current_time(),
            "elapsed_time": self._calculate_elapsed_time()
        }

        return report

    def _extract_key_findings(self) -> Dict[str, List[str]]:
        """
        从各步骤结果中提取关键发现
        """
        strengths = []
        concerns = []

        # 从team analysis提取
        team_data = self.results.get("team_deep_investigation", {})
        if team_data.get("team_score", 0) >= 0.7:
            strengths.append("团队背景优秀,经验匹配度高")
        elif team_data.get("team_score", 0) < 0.5:
            concerns.append("团队经验不足或背景不匹配")

        # 从market analysis提取
        market_data = self.results.get("market_validation", {})
        market_size = market_data.get("market_size", {})
        if isinstance(market_size, dict) and market_size.get("tam", 0) > 1000000000:  # > $1B
            strengths.append(f"目标市场规模大 (TAM: ${market_size.get('tam', 0)/1e9:.1f}B)")

        # 从business model提取
        biz_model = self.results.get("business_model_assessment", {})
        if biz_model.get("scalability", "") == "high":
            strengths.append("商业模式可扩展性强")

        return {
            "strengths": strengths,
            "concerns": concerns
        }

    def _generate_next_steps(
        self,
        recommendation: str,
        red_flags: List[str]
    ) -> Dict[str, Any]:
        """
        根据建议生成后续步骤
        """
        if recommendation == "INVEST":
            return {
                "recommended_action": "准备投资条款清单 (Term Sheet)",
                "focus_areas": [
                    "确定投资金额和估值",
                    "准备法律文件",
                    "安排管理团队正式会议"
                ],
                "timeline": "1-2周"
            }
        elif recommendation == "FURTHER_DD":
            focus_areas = ["深入团队背景调查", "客户访谈验证需求"]
            if len(red_flags) > 0:
                focus_areas.append(f"解决红旗问题: {', '.join(red_flags[:2])}")

            return {
                "recommended_action": "进行标准尽职调查",
                "focus_areas": focus_areas,
                "estimated_time": "2-4周"
            }
        else:  # PASS
            return {
                "recommended_action": "放弃投资机会",
                "reasoning": "不符合投资标准",
                "alternative": "可考虑后续轮次再评估" if recommendation == "PASS" else None
            }

    def _calculate_confidence(self) -> float:
        """
        计算结论的置信度

        考虑因素:
        - 数据完整度
        - 结果一致性
        - 交叉验证结果
        """
        # Phase 1简单实现
        data_completeness = len(self.results) / 6  # 假设6个步骤
        return min(data_completeness * 0.9, 0.95)  # 最高0.95

    def _get_current_time(self) -> str:
        """获取当前时间ISO格式"""
        from datetime import datetime
        return datetime.now().isoformat()

    # ============ 快速判断模式专用方法 ============

    async def _synthesize_quick_judgment(self) -> Dict[str, Any]:
        """
        早期投资快速判断

        核心逻辑:
        - 团队快查: 创始人背景是否匹配
        - 市场初判: TAM是否够大 (>$1B)
        - 红旗检查: 是否有明显问题
        """
        team_data = self.results.get("team_quick_check", {})
        market_data = self.results.get("market_opportunity", {})
        red_flags_data = self.results.get("red_flag_scan", {})

        team_score = team_data.get("team_score", 0.5)
        market_score = market_data.get("market_attractiveness", 0.5)
        red_flags = red_flags_data.get("red_flags", [])

        # 决策逻辑
        overall_score = (team_score + market_score) / 2

        if len(red_flags) > 0:
            recommendation = "PASS"
            verdict = f"发现{len(red_flags)}个红旗,建议放弃"
        elif overall_score >= 0.7 and team_score >= 0.7:
            recommendation = "BUY"
            verdict = f"团队优秀,市场机会明确,建议投资"
        elif overall_score >= 0.5:
            recommendation = "FURTHER_DD"
            verdict = f"有潜力但需要更多信息,建议标准尽调"
        else:
            recommendation = "PASS"
            verdict = f"综合评分{overall_score:.2f}较低,不建议投资"

        return {
            "recommendation": recommendation,
            "confidence": overall_score,
            "judgment_time": self._calculate_elapsed_time(),
            "summary": {
                "verdict": verdict,
                "key_positive": team_data.get("highlights", []),
                "key_concern": red_flags,
                "red_flags": red_flags
            },
            "scores": {
                "team": team_score,
                "market": market_score,
                "overall": overall_score
            },
            "next_steps": {
                "recommended_action": "进行标准尽调" if recommendation == "FURTHER_DD" else None,
                "focus_areas": [
                    "深入验证团队背景",
                    "市场规模数据验证",
                    "竞品分析"
                ] if recommendation == "FURTHER_DD" else []
            }
        }
