"""
Analysis Module V2 - 统一数据模型
支持5个投资场景 (Scheme A: 投资场景分类)
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============ 枚举定义 ============

class InvestmentScenario(str, Enum):
    """投资场景枚举 (Scheme A)"""
    EARLY_STAGE = "early-stage-investment"
    GROWTH = "growth-investment"
    PUBLIC_MARKET = "public-market-investment"
    ALTERNATIVE = "alternative-investment"
    INDUSTRY_RESEARCH = "industry-research"


class AnalysisDepth(str, Enum):
    """分析深度"""
    QUICK = "quick"          # 3-5分钟 (快速判断)
    STANDARD = "standard"    # 30-45分钟 (标准分析)
    COMPREHENSIVE = "comprehensive"  # 1-2小时 (深度分析)


class InvestmentStyle(str, Enum):
    """投资风格"""
    VALUE = "value"
    GROWTH = "growth"
    MOMENTUM = "momentum"
    CONTRARIAN = "contrarian"


class DecisionMode(str, Enum):
    """Orchestrator决策模式"""
    FIXED = "fixed"              # 固定workflow
    INTELLIGENT = "intelligent"  # 每步LLM决策
    HYBRID = "hybrid"            # 混合模式 (推荐)


class RecommendationType(str, Enum):
    """推荐类型 (用于快速判断)"""
    BUY = "BUY"                  # 建议投资
    PASS = "PASS"                # 不建议投资
    FURTHER_DD = "FURTHER_DD"    # 建议深入尽调


# ============ Target Models (5个场景的目标对象) ============

class EarlyStageTarget(BaseModel):
    """早期投资分析目标"""
    company_name: str = Field(..., description="公司名称")
    stage: str = Field(..., description="融资阶段: angel/seed/pre-a/series-a")
    industry: Optional[str] = Field(None, description="所属行业")
    bp_file_id: Optional[str] = Field(None, description="BP文件ID")
    team_members: List[Dict[str, str]] = Field(default_factory=list, description="团队成员列表")
    founded_year: Optional[int] = Field(None, description="成立年份")


class GrowthTarget(BaseModel):
    """成长期投资分析目标"""
    company_name: str = Field(..., description="公司名称")
    stage: str = Field(..., description="融资阶段: series-b/c/d/e/pre-ipo")
    industry: Optional[str] = Field(None, description="所属行业")
    financial_file_id: Optional[str] = Field(None, description="财务数据文件ID")
    annual_revenue: Optional[float] = Field(None, description="年营收(USD)")
    growth_rate: Optional[float] = Field(None, description="增长率")


class PublicMarketTarget(BaseModel):
    """公开市场投资分析目标"""
    ticker: str = Field(..., description="股票代码,如AAPL, NVDA")
    exchange: Optional[str] = Field(None, description="交易所,自动识别")
    asset_type: str = Field("stock", description="资产类型: stock/etf/reit")


class AlternativeTarget(BaseModel):
    """另类投资分析目标"""
    asset_type: str = Field(..., description="资产类型: crypto/defi/nft/web3")
    symbol: Optional[str] = Field(None, description="代币符号,如BTC, ETH")
    contract_address: Optional[str] = Field(None, description="智能合约地址")
    chain: Optional[str] = Field("ethereum", description="区块链网络")
    project_name: Optional[str] = Field(None, description="项目名称")


class IndustryResearchTarget(BaseModel):
    """行业/市场研究目标"""
    industry_name: str = Field(..., description="行业名称,如'AI芯片'")
    research_topic: str = Field(..., description="研究主题")
    geo_scope: Optional[str] = Field("global", description="地理范围: global/us/china/eu")
    key_questions: List[str] = Field(default_factory=list, description="关键问题列表")


# ============ 统一分析请求 ============

class AnalysisConfig(BaseModel):
    """分析配置"""
    depth: AnalysisDepth = AnalysisDepth.STANDARD
    timeframe: Optional[str] = Field("1Y", description="时间范围")
    focus_areas: List[str] = Field(default_factory=list, description="重点关注领域")
    selected_agents: List[str] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    language: str = Field("zh", description="报告语言")

    # 场景专属参数 (支持各场景的特定配置)
    scenario_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="场景特定参数,如早期投资的priority/risk_appetite、成长期的growth_model等"
    )


class UserPreferences(BaseModel):
    """用户投资偏好"""
    investment_style: Optional[InvestmentStyle] = None
    risk_tolerance: Optional[str] = Field(None, description="风险承受能力: low/medium/high")
    time_horizon: Optional[str] = Field(None, description="投资时间跨度")


class AnalysisRequest(BaseModel):
    """统一分析请求"""
    project_name: str = Field(..., description="项目名称")
    scenario: InvestmentScenario = Field(..., description="投资场景")

    # 动态目标对象 (根据scenario解析)
    target: Dict[str, Any] = Field(..., description="分析目标")

    # 配置和偏好
    config: AnalysisConfig = Field(default_factory=AnalysisConfig)
    preferences: Optional[UserPreferences] = None

    user_id: str = Field("default_user")


# ============ 分析响应模型 ============

class WorkflowStep(BaseModel):
    """工作流步骤"""
    id: str
    name: str
    status: str = "pending"  # pending, running, success, error, skipped
    agent: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class QuickJudgmentResult(BaseModel):
    """快速判断结果"""
    recommendation: RecommendationType  # BUY, PASS, FURTHER_DD
    confidence: float
    judgment_time: str
    summary: Dict[str, Any]
    scores: Dict[str, float]
    next_steps: Dict[str, Any]


class AnalysisSession(BaseModel):
    """分析会话"""
    session_id: str
    project_name: str
    scenario: InvestmentScenario
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD
    status: str = "initializing"  # initializing, running, completed, error
    created_at: str
    updated_at: str

    # 工作流
    workflow: List[WorkflowStep] = Field(default_factory=list)
    current_step: int = 0

    # 结果
    results: Dict[str, Any] = Field(default_factory=dict)
    final_report: Optional[Dict[str, Any]] = None

    # 快速判断结果 (如果经过快速判断阶段)
    quick_judgment: Optional[QuickJudgmentResult] = None

    # 元数据
    orchestrator: str
    agents_used: List[str] = Field(default_factory=list)


class AnalysisMessage(BaseModel):
    """WebSocket消息"""
    type: str  # status_update, step_start, step_complete, agent_event, error, completed, quick_judgment_complete
    session_id: str
    timestamp: str
    data: Dict[str, Any]


# ============ Workflow模板定义 ============

class WorkflowStepTemplate(BaseModel):
    """Workflow步骤模板"""
    id: str
    name: str
    required: bool = True
    agent: str
    quick_mode: bool = False
    condition: Optional[str] = None
    inputs: List[str] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    expected_output: List[str] = Field(default_factory=list)
    expected_duration: Optional[int] = None  # 秒


class ScenarioWorkflow(BaseModel):
    """场景workflow定义"""
    name: str
    orchestrator: str
    quick_mode_workflow: List[WorkflowStepTemplate] = Field(default_factory=list)
    standard_workflow: List[WorkflowStepTemplate] = Field(default_factory=list)
    comprehensive_workflow: Optional[List[WorkflowStepTemplate]] = None
