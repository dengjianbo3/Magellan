# backend/services/report_orchestrator/app/models/dd_models.py
"""
Data models for Due Diligence (DD) workflow in V3.
These models define the structure for BP analysis, team/market analysis outputs, and DD questions.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


# ============================================================================
# Input Models
# ============================================================================

class DDAnalysisRequest(BaseModel):
    """Request model for starting a DD analysis"""
    company_name: str = Field(..., description="公司名称")
    user_id: str = Field(default="default_user", description="发起分析的用户 ID")
    # Note: bp_file will be handled separately as UploadFile in FastAPI endpoint


class InstitutionPreference(BaseModel):
    """
    Institutional investment preferences (for Sprint 4, reserved here)
    机构投资偏好（为 Sprint 4 预留）
    """
    investment_themes: List[str] = Field(default=[], description="投资主题，如 ['SaaS', 'AI']")
    preferred_stages: List[str] = Field(default=[], description="偏好阶段，如 ['Seed', 'Series A']")
    focus_sectors: List[str] = Field(default=[], description="关注赛道")
    min_valuation: Optional[float] = Field(None, description="最小估值（亿元）")
    max_valuation: Optional[float] = Field(None, description="最大估值（亿元）")


# ============================================================================
# BP Structured Data Models
# ============================================================================

class TeamMember(BaseModel):
    """Individual team member information extracted from BP"""
    name: str = Field(..., description="姓名")
    title: str = Field(..., description="职位")
    background: str = Field(..., description="背景描述")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn 链接（如果 BP 中提供）")


class FinancialProjection(BaseModel):
    """Financial projection data from BP"""
    year: int
    revenue: Optional[float] = Field(None, description="营收（万元）")
    profit: Optional[float] = Field(None, description="利润（万元）")
    user_count: Optional[int] = Field(None, description="用户数")
    notes: Optional[str] = Field(None, description="备注")


class BPStructuredData(BaseModel):
    """
    Structured data extracted from Business Plan (BP).
    从商业计划书中提取的结构化数据
    """
    company_name: str = Field(..., description="公司名称")
    founding_date: Optional[str] = Field(None, description="成立日期")
    
    # Team information
    team: List[TeamMember] = Field(default=[], description="团队成员")
    
    # Product information
    product_name: Optional[str] = Field(None, description="产品名称")
    product_description: Optional[str] = Field(None, description="产品描述")
    core_technology: Optional[str] = Field(None, description="核心技术")
    
    # Market information
    target_market: Optional[str] = Field(None, description="目标市场")
    market_size_tam: Optional[str] = Field(None, description="市场规模 (TAM)")
    target_customers: Optional[str] = Field(None, description="目标客户群体")
    
    # Competition
    competitors: List[str] = Field(default=[], description="竞品列表")
    competitive_advantages: Optional[str] = Field(None, description="竞争优势")
    
    # Financials
    funding_request: Optional[str] = Field(None, description="融资金额")
    current_valuation: Optional[str] = Field(None, description="当前估值")
    use_of_funds: Optional[str] = Field(None, description="资金用途")
    financial_projections: List[FinancialProjection] = Field(default=[], description="财务预测")
    
    # Current status
    current_stage: Optional[str] = Field(None, description="当前阶段 (MVP/已上线/已盈利等)")
    key_metrics: Dict[str, Any] = Field(default_factory=dict, description="关键指标 (如 MRR, 用户数等)")
    
    # Additional
    raw_sections: Dict[str, str] = Field(
        default_factory=dict, 
        description="原始章节文本，格式: {章节名: 内容}"
    )


# ============================================================================
# Analysis Output Models
# ============================================================================

class TeamAnalysisOutput(BaseModel):
    """
    Output from TeamAnalysisAgent.
    团队分析模块的输出
    """
    summary: str = Field(..., description="团队整体评价（200-300字）")
    strengths: List[str] = Field(..., description="团队优势（3-5条）")
    concerns: List[str] = Field(..., description="潜在担忧（2-4条）")
    experience_match_score: float = Field(
        ..., 
        ge=0, 
        le=10, 
        description="经验匹配度评分（0-10分）"
    )
    key_findings: List[str] = Field(
        default=[], 
        description="关键发现（如：发现创始人有过失败创业经历）"
    )
    data_sources: List[str] = Field(..., description="使用的数据来源")
    analysis_timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="分析时间戳"
    )


class MarketAnalysisOutput(BaseModel):
    """
    Output from MarketAnalysisAgent.
    市场分析模块的输出
    """
    summary: str = Field(..., description="市场整体评价")
    market_validation: str = Field(..., description="市场规模验证结果")
    growth_potential: str = Field(..., description="增长潜力评估")
    competitive_landscape: str = Field(..., description="竞争格局分析")
    red_flags: List[str] = Field(default=[], description="发现的市场风险")
    opportunities: List[str] = Field(default=[], description="市场机会")
    data_sources: List[str] = Field(..., description="使用的数据来源")
    analysis_timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="分析时间戳"
    )


class CrossCheckResult(BaseModel):
    """
    Result from cross-checking BP data against external sources.
    交叉验证结果
    """
    category: str = Field(..., description="验证类别 (Team/Market/Product/Financial)")
    bp_claim: str = Field(..., description="BP 中的声明")
    external_data: str = Field(..., description="外部数据")
    is_consistent: bool = Field(..., description="是否一致")
    discrepancy_level: str = Field(
        ..., 
        description="差异程度 (None/Minor/Major/Critical)"
    )
    notes: Optional[str] = Field(None, description="备注")


class DDQuestion(BaseModel):
    """
    A single Due Diligence question.
    单个尽职调查问题
    """
    category: str = Field(
        ..., 
        description="分类：Team/Market/Product/Financial/Risk"
    )
    question: str = Field(..., description="问题内容")
    reasoning: str = Field(..., description="为什么要问这个问题")
    priority: str = Field(
        default="Medium", 
        description="优先级：High/Medium/Low"
    )
    bp_reference: Optional[str] = Field(None, description="BP 中相关内容的引用（如：第 5 页）")


class PreliminaryIM(BaseModel):
    """
    Preliminary Investment Memorandum (IM).
    初步投资备忘录
    """
    company_name: str
    analysis_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d"),
        description="分析日期"
    )
    
    # Core analysis sections
    bp_structured_data: BPStructuredData
    team_section: Optional[TeamAnalysisOutput] = Field(default=None, description="团队分析结果(可选)")
    market_section: Optional[MarketAnalysisOutput] = Field(default=None, description="市场分析结果(可选)")
    cross_check_results: List[CrossCheckResult] = Field(default=[], description="交叉验证结果")
    
    # DD Questions
    dd_questions: List[DDQuestion] = Field(..., description="DD 问题清单")
    
    # Metadata
    generated_by: str = Field(default="DD Workflow V3", description="生成者")
    session_id: str = Field(..., description="会话 ID")


# ============================================================================
# Workflow Models
# ============================================================================

class DDWorkflowState(str, Enum):
    """States in the DD workflow state machine"""
    INIT = "init"
    DOC_PARSE = "doc_parse"              # 解析 BP
    PREFERENCE_CHECK = "preference_check" # 偏好匹配检查 (Sprint 4 新增)
    TDD = "team_dd"                      # 团队尽调
    MDD = "market_dd"                    # 市场尽调
    CROSS_CHECK = "cross_check"          # 交叉验证
    DD_QUESTIONS = "dd_questions"        # 生成问题清单
    HITL_REVIEW = "hitl_review"          # 人工审核
    COMPLETED = "completed"
    ERROR = "error"


class DDStep(BaseModel):
    """
    A single step in the DD workflow.
    DD 工作流中的单个步骤
    """
    id: int
    title: str
    status: str = Field(..., description="'running', 'success', 'error', 'paused'")
    result: Optional[str] = None
    progress: Optional[float] = Field(None, ge=0, le=100, description="进度百分比")
    sub_steps: Optional[List[str]] = Field(None, description="子步骤列表")
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class DDWorkflowMessage(BaseModel):
    """
    Message format for WebSocket communication in DD workflow.
    DD 工作流的 WebSocket 消息格式
    """
    session_id: str
    status: str = Field(
        ..., 
        description="'in_progress', 'hitl_required', 'completed', 'error'"
    )
    current_step: Optional[DDStep] = None
    all_steps: Optional[List[DDStep]] = Field(
        None, 
        description="所有步骤的状态（用于前端显示进度）"
    )
    preliminary_im: Optional[PreliminaryIM] = None
    message: Optional[str] = Field(None, description="额外的消息给用户")


class DDSessionContext(BaseModel):
    """
    Context stored for a DD analysis session.
    DD 分析会话的上下文
    """
    session_id: str
    company_name: str
    user_id: str
    current_state: DDWorkflowState = DDWorkflowState.INIT
    
    # Intermediate results
    bp_data: Optional[BPStructuredData] = None
    preference_match_result: Optional[Dict[str, Any]] = Field(None, description="机构偏好匹配结果 (Sprint 4)")
    team_analysis: Optional[TeamAnalysisOutput] = None
    market_analysis: Optional[MarketAnalysisOutput] = None
    cross_check_results: List[CrossCheckResult] = Field(default=[])
    dd_questions: List[DDQuestion] = Field(default=[])
    
    # Metadata
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # Error tracking
    errors: List[str] = Field(default=[], description="记录的错误")


# ============================================================================
# Helper Models
# ============================================================================

class ServiceCallResult(BaseModel):
    """Result from calling an external service"""
    service_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    response_time_ms: Optional[float] = None
