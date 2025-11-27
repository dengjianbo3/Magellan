"""
Scenario Workflow Templates
定义5个投资场景的workflow模板 (快速/标准/深度模式)
"""

from typing import Dict, List
from app.models.analysis_models import WorkflowStepTemplate, ScenarioWorkflow


# ============ 场景1: 早期投资 ============

EARLY_STAGE_QUICK = [
    WorkflowStepTemplate(
        id="team_quick_check",
        name="团队快速验证",
        required=True,
        agent="team_evaluator",
        quick_mode=True,
        expected_duration=60,
        expected_output=["team_score", "key_members_background"]
    ),
    WorkflowStepTemplate(
        id="market_opportunity",
        name="市场机会初判",
        required=True,
        agent="market_analyst",
        quick_mode=True,
        expected_duration=90,
        expected_output=["market_size_estimate", "market_attractiveness"]
    ),
    WorkflowStepTemplate(
        id="red_flag_scan",
        name="红旗检查",
        required=True,
        agent="risk_assessor",
        quick_mode=True,
        expected_duration=60,
        expected_output=["red_flags", "critical_issues"]
    ),
    WorkflowStepTemplate(
        id="quick_judgment",
        name="快速综合判断",
        required=True,
        agent="orchestrator",
        expected_duration=30,
        expected_output=["recommendation", "confidence", "next_steps"]
    )
]

EARLY_STAGE_STANDARD = [
    WorkflowStepTemplate(
        id="bp_parsing",
        name="BP解析",
        required=False,
        agent="market_analyst",
        condition="target.get('bp_file_id') is not None",
        inputs=["bp_file_id"],
        expected_output=["structured_bp", "business_model", "financials"]
    ),
    WorkflowStepTemplate(
        id="team_deep_investigation",
        name="团队深度调查",
        required=True,
        agent="team_evaluator",
        inputs=["team_members", "company_name"],
        expected_output=["team_analysis", "founder_background", "experience_match"]
    ),
    WorkflowStepTemplate(
        id="market_validation",
        name="市场验证",
        required=True,
        agent="market_analyst",
        inputs=["industry", "bp_data"],
        data_sources=["web_search", "industry_reports"],
        expected_output=["market_size", "competition", "market_trends"]
    ),
    WorkflowStepTemplate(
        id="business_model_assessment",
        name="商业模式评估",
        required=True,
        agent="financial_expert",
        inputs=["bp_data", "market_analysis"],
        expected_output=["unit_economics", "revenue_model", "scalability"]
    ),
    WorkflowStepTemplate(
        id="cross_validation",
        name="信息交叉验证",
        required=True,
        agent="risk_assessor",
        inputs=["all_previous"],
        expected_output=["inconsistencies", "red_flags"]
    ),
    WorkflowStepTemplate(
        id="report_synthesis",
        name="生成投资备忘录",
        required=True,
        agent="report_synthesizer",
        inputs=["all_previous"],
        expected_output=["recommendation", "investment_score", "key_risks", "next_steps", "preliminary_im"]
    )
]


# ============ 场景2: 成长期投资 ============

GROWTH_QUICK = [
    WorkflowStepTemplate(
        id="financial_health_check",
        name="财务健康检查",
        required=True,
        agent="financial_expert",
        quick_mode=True,
        expected_duration=90,
        expected_output=["cash_position", "runway", "profitability_path"]
    ),
    WorkflowStepTemplate(
        id="growth_assessment",
        name="增长潜力评估",
        required=True,
        agent="market_analyst",
        quick_mode=True,
        expected_duration=60,
        expected_output=["growth_score", "growth_drivers", "scalability"]
    ),
    WorkflowStepTemplate(
        id="market_position_check",
        name="市场地位检查",
        required=True,
        agent="market_analyst",
        quick_mode=True,
        expected_duration=60,
        expected_output=["market_position", "competitive_advantage", "market_share"]
    ),
    WorkflowStepTemplate(
        id="quick_judgment",
        name="快速投资判断",
        required=True,
        agent="orchestrator",
        expected_duration=30,
        expected_output=["recommendation", "confidence"]
    )
]

GROWTH_STANDARD = [
    WorkflowStepTemplate(
        id="financial_analysis",
        name="财务深度分析",
        required=True,
        agent="financial_expert",
        inputs=["financial_file_id", "annual_revenue"],
        expected_output=["detailed_financials", "unit_economics", "margin_analysis"]
    ),
    WorkflowStepTemplate(
        id="growth_quality_assessment",
        name="增长质量评估",
        required=True,
        agent="market_analyst",
        inputs=["financials", "company_name"],
        expected_output=["growth_drivers", "customer_retention", "market_share"]
    ),
    WorkflowStepTemplate(
        id="competitive_analysis",
        name="竞争优势分析",
        required=True,
        agent="market_analyst",
        inputs=["company_name", "industry"],
        data_sources=["web_search", "competitor_data"],
        expected_output=["competitive_moat", "differentiation", "market_position"]
    ),
    WorkflowStepTemplate(
        id="valuation_modeling",
        name="估值建模",
        required=True,
        agent="financial_expert",
        inputs=["financials", "growth_metrics"],
        expected_output=["valuation_range", "dcf_model", "comparable_multiples"]
    ),
    WorkflowStepTemplate(
        id="report_synthesis",
        name="生成投资分析报告",
        required=True,
        agent="report_synthesizer",
        inputs=["all_previous"],
        expected_output=["roi_scenarios", "exit_timeline", "risk_adjusted_return", "final_report"]
    )
]


# ============ 场景3: 公开市场投资 ============

PUBLIC_MARKET_QUICK = [
    WorkflowStepTemplate(
        id="valuation_check",
        name="估值检查",
        required=True,
        agent="financial_expert",
        quick_mode=True,
        data_sources=["yahoo_finance"],
        expected_duration=60,
        expected_output=["valuation_level", "pe_ratio", "price_target"]
    ),
    WorkflowStepTemplate(
        id="fundamentals_check",
        name="基本面检查",
        required=True,
        agent="financial_expert",
        quick_mode=True,
        expected_duration=90,
        expected_output=["fundamentals_score", "revenue_growth", "profit_margin"]
    ),
    WorkflowStepTemplate(
        id="technical_check",
        name="技术面检查",
        required=True,
        agent="market_analyst",
        quick_mode=True,
        expected_duration=60,
        expected_output=["technical_score", "trend", "support_resistance"]
    ),
    WorkflowStepTemplate(
        id="quick_judgment",
        name="快速投资判断",
        required=True,
        agent="orchestrator",
        expected_duration=30,
        expected_output=["recommendation", "confidence"]
    )
]

PUBLIC_MARKET_STANDARD = [
    WorkflowStepTemplate(
        id="data_collection",
        name="数据获取",
        required=True,
        agent="financial_expert",
        data_sources=["yahoo_finance", "sec_edgar"],
        expected_output=["stock_data", "financials", "company_info"]
    ),
    WorkflowStepTemplate(
        id="fundamental_analysis",
        name="基本面分析",
        required=True,
        agent="financial_expert",
        inputs=["financials", "company_info"],
        expected_output=["valuation", "financial_health", "growth_metrics"]
    ),
    WorkflowStepTemplate(
        id="technical_analysis",
        name="技术面分析",
        required=False,
        agent="financial_expert",
        condition="config.get('depth') == 'comprehensive'",
        inputs=["stock_data"],
        expected_output=["technical_signals", "price_targets", "support_resistance"]
    ),
    WorkflowStepTemplate(
        id="industry_comparison",
        name="行业对比",
        required=True,
        agent="market_analyst",
        inputs=["company_info", "financials"],
        expected_output=["peer_comparison", "industry_position", "market_share"]
    ),
    WorkflowStepTemplate(
        id="risk_assessment",
        name="风险评估",
        required=True,
        agent="risk_assessor",
        inputs=["all_previous"],
        expected_output=["risk_factors", "risk_score", "scenario_analysis"]
    ),
    WorkflowStepTemplate(
        id="report_synthesis",
        name="生成投资建议书",
        required=True,
        agent="report_synthesizer",
        inputs=["all_previous"],
        expected_output=["recommendation", "target_price", "confidence", "time_horizon", "final_report"]
    )
]


# ============ 场景4: 另类投资 ============

ALTERNATIVE_QUICK = [
    WorkflowStepTemplate(
        id="tech_foundation_check",
        name="技术基础检查",
        required=True,
        agent="tech_specialist",
        quick_mode=True,
        data_sources=["github", "web_search"],
        expected_duration=60,
        expected_output=["tech_score", "architecture_quality", "security_audit"]
    ),
    WorkflowStepTemplate(
        id="tokenomics_check",
        name="代币经济学检查",
        required=True,
        agent="financial_expert",
        quick_mode=True,
        expected_duration=90,
        expected_output=["tokenomics_score", "distribution", "inflation_model"]
    ),
    WorkflowStepTemplate(
        id="community_check",
        name="社区活跃度检查",
        required=True,
        agent="market_analyst",
        quick_mode=True,
        expected_duration=60,
        expected_output=["community_score", "social_engagement", "holder_count"]
    ),
    WorkflowStepTemplate(
        id="quick_judgment",
        name="快速投资判断",
        required=True,
        agent="orchestrator",
        expected_duration=30,
        expected_output=["recommendation", "risk_level"]
    )
]

ALTERNATIVE_STANDARD = [
    WorkflowStepTemplate(
        id="token_identification",
        name="代币识别",
        required=True,
        agent="market_analyst",
        inputs=["symbol", "contract_address"],
        data_sources=["coingecko", "etherscan"],
        expected_output=["token_info", "token_type", "chain_info"]
    ),
    WorkflowStepTemplate(
        id="onchain_analysis",
        name="链上数据分析",
        required=True,
        agent="tech_specialist",
        data_sources=["etherscan", "dune_analytics"],
        inputs=["contract_address"],
        expected_output=["holder_distribution", "transaction_volume", "whale_activity"]
    ),
    WorkflowStepTemplate(
        id="project_research",
        name="项目研究",
        required=True,
        agent="market_analyst",
        inputs=["token_info", "project_name"],
        data_sources=["web_search", "github", "discord"],
        expected_output=["tech_overview", "team_background", "roadmap"]
    ),
    WorkflowStepTemplate(
        id="tokenomics_analysis",
        name="代币经济学分析",
        required=True,
        agent="financial_expert",
        inputs=["token_info", "onchain_data"],
        expected_output=["supply_dynamics", "inflation_rate", "value_accrual"]
    ),
    WorkflowStepTemplate(
        id="community_assessment",
        name="社区评估",
        required=True,
        agent="market_analyst",
        data_sources=["twitter", "discord", "telegram"],
        expected_output=["community_size", "engagement", "sentiment"]
    ),
    WorkflowStepTemplate(
        id="risk_assessment",
        name="风险评估",
        required=True,
        agent="risk_assessor",
        inputs=["all_previous"],
        expected_output=["technical_risks", "regulatory_risks", "market_risks"]
    ),
    WorkflowStepTemplate(
        id="report_synthesis",
        name="生成投资分析报告",
        required=True,
        agent="report_synthesizer",
        inputs=["all_previous"],
        expected_output=["recommendation", "entry_price", "stop_loss", "position_size", "final_report"]
    )
]


# ============ 场景5: 行业/市场研究 ============

INDUSTRY_RESEARCH_QUICK = [
    WorkflowStepTemplate(
        id="market_size_check",
        name="市场规模检查",
        required=True,
        agent="market_analyst",
        quick_mode=True,
        data_sources=["web_search", "industry_reports"],
        expected_duration=90,
        expected_output=["market_size_estimate", "growth_rate", "tam"]
    ),
    WorkflowStepTemplate(
        id="competition_landscape",
        name="竞争格局分析",
        required=True,
        agent="market_analyst",
        quick_mode=True,
        expected_duration=90,
        expected_output=["top_players", "market_concentration", "entry_barriers"]
    ),
    WorkflowStepTemplate(
        id="trend_analysis",
        name="趋势分析",
        required=True,
        agent="market_analyst",
        quick_mode=True,
        expected_duration=60,
        expected_output=["key_trends", "tech_direction", "policy_support"]
    ),
    WorkflowStepTemplate(
        id="opportunity_scan",
        name="机会扫描",
        required=True,
        agent="market_analyst",
        quick_mode=True,
        expected_duration=60,
        expected_output=["opportunities", "sub_sectors", "innovations"]
    ),
    WorkflowStepTemplate(
        id="quick_summary",
        name="快速总结",
        required=True,
        agent="orchestrator",
        expected_duration=30,
        expected_output=["investment_opportunities", "key_insights"]
    )
]

INDUSTRY_RESEARCH_STANDARD = [
    WorkflowStepTemplate(
        id="market_definition",
        name="市场定义",
        required=True,
        agent="market_analyst",
        inputs=["industry_name", "research_topic"],
        expected_output=["market_boundaries", "segments", "value_chain"]
    ),
    WorkflowStepTemplate(
        id="market_sizing",
        name="市场规模测算",
        required=True,
        agent="market_analyst",
        data_sources=["industry_reports", "government_data", "web_search"],
        expected_output=["tam_sam_som", "historical_growth", "future_projections"]
    ),
    WorkflowStepTemplate(
        id="growth_drivers_analysis",
        name="增长驱动力分析",
        required=True,
        agent="market_analyst",
        inputs=["market_data"],
        expected_output=["key_drivers", "barriers", "catalysts"]
    ),
    WorkflowStepTemplate(
        id="competitive_landscape",
        name="竞争格局分析",
        required=True,
        agent="market_analyst",
        data_sources=["web_search", "company_databases"],
        expected_output=["key_players", "market_structure", "competitive_dynamics"]
    ),
    WorkflowStepTemplate(
        id="report_synthesis",
        name="生成行业研究报告",
        required=True,
        agent="report_synthesizer",
        inputs=["all_previous"],
        expected_output=["opportunity_areas", "attractive_segments", "entry_strategies", "final_report"]
    ),
    WorkflowStepTemplate(
        id="roundtable_discussion",
        name="专家圆桌讨论",
        required=False,
        agent="roundtable",
        condition="config.get('depth') == 'comprehensive'",
        inputs=["all_previous"],
        expected_output=["expert_insights", "consensus_view", "debate_points"]
    )
]


# ============ Registry: 场景workflow注册表 ============

SCENARIO_WORKFLOWS: Dict[str, ScenarioWorkflow] = {
    "early-stage-investment": ScenarioWorkflow(
        name="早期投资分析",
        orchestrator="EarlyStageInvestmentOrchestrator",
        quick_mode_workflow=EARLY_STAGE_QUICK,
        standard_workflow=EARLY_STAGE_STANDARD
    ),

    "growth-investment": ScenarioWorkflow(
        name="成长期投资分析",
        orchestrator="GrowthInvestmentOrchestrator",
        quick_mode_workflow=GROWTH_QUICK,
        standard_workflow=GROWTH_STANDARD
    ),

    "public-market-investment": ScenarioWorkflow(
        name="公开市场投资分析",
        orchestrator="PublicMarketInvestmentOrchestrator",
        quick_mode_workflow=PUBLIC_MARKET_QUICK,
        standard_workflow=PUBLIC_MARKET_STANDARD
    ),

    "alternative-investment": ScenarioWorkflow(
        name="另类投资分析",
        orchestrator="AlternativeInvestmentOrchestrator",
        quick_mode_workflow=ALTERNATIVE_QUICK,
        standard_workflow=ALTERNATIVE_STANDARD
    ),

    "industry-research": ScenarioWorkflow(
        name="行业/市场研究",
        orchestrator="IndustryResearchOrchestrator",
        quick_mode_workflow=INDUSTRY_RESEARCH_QUICK,
        standard_workflow=INDUSTRY_RESEARCH_STANDARD
    )
}


def get_workflow(scenario: str, depth: str = "standard") -> List[WorkflowStepTemplate]:
    """
    获取场景对应的workflow

    Args:
        scenario: 投资场景
        depth: 分析深度 (quick/standard/comprehensive)

    Returns:
        WorkflowStepTemplate列表
    """
    if scenario not in SCENARIO_WORKFLOWS:
        raise ValueError(f"Unknown scenario: {scenario}")

    workflow_config = SCENARIO_WORKFLOWS[scenario]

    if depth == "quick":
        return workflow_config.quick_mode_workflow
    elif depth == "standard":
        return workflow_config.standard_workflow
    elif depth == "comprehensive":
        # 深度模式: 使用标准workflow + 额外步骤
        if workflow_config.comprehensive_workflow:
            return workflow_config.comprehensive_workflow
        else:
            # 默认返回标准workflow (所有步骤都执行)
            return workflow_config.standard_workflow
    else:
        raise ValueError(f"Unknown depth: {depth}")