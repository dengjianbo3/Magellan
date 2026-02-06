# backend/services/report_orchestrator/tests/test_dd_models.py
"""
Unit tests for DD data models.
测试 DD 数据模型
"""
import pytest
from pydantic import ValidationError
from app.models.dd_models import (
    TeamMember,
    BPStructuredData,
    TeamAnalysisOutput,
    MarketAnalysisOutput,
    DDQuestion,
    PreliminaryIM,
    DDWorkflowState,
    DDStep,
)


def test_team_member_model():
    """Test TeamMember model"""
    member = TeamMember(
        name="张三",
        title="CEO",
        background="10年互联网经验"
    )
    assert member.name == "张三"
    assert member.title == "CEO"
    assert member.linkedin_url is None


def test_bp_structured_data_model():
    """Test BPStructuredData model"""
    team = [
        TeamMember(name="张三", title="CEO", background="背景1"),
        TeamMember(name="李四", title="CTO", background="背景2"),
    ]
    
    bp_data = BPStructuredData(
        company_name="测试公司",
        team=team,
        product_description="AI 产品",
        target_market="企业 SaaS"
    )
    
    assert bp_data.company_name == "测试公司"
    assert len(bp_data.team) == 2
    assert bp_data.team[0].name == "张三"


def test_team_analysis_output_model():
    """Test TeamAnalysisOutput model"""
    analysis = TeamAnalysisOutput(
        summary="团队分析摘要",
        strengths=["优势1", "优势2"],
        concerns=["担忧1"],
        experience_match_score=7.5,
        data_sources=["BP", "LinkedIn"]
    )
    
    assert analysis.experience_match_score == 7.5
    assert len(analysis.strengths) == 2
    assert len(analysis.concerns) == 1


def test_experience_score_validation():
    """Test that experience_match_score must be between 0 and 10"""
    # Valid score
    analysis = TeamAnalysisOutput(
        summary="测试",
        strengths=["优势"],
        concerns=[],
        experience_match_score=5.0,
        data_sources=[]
    )
    assert analysis.experience_match_score == 5.0
    
    # Invalid score (too high)
    with pytest.raises(ValidationError):
        TeamAnalysisOutput(
            summary="测试",
            strengths=[],
            concerns=[],
            experience_match_score=11.0,
            data_sources=[]
        )
    
    # Invalid score (negative)
    with pytest.raises(ValidationError):
        TeamAnalysisOutput(
            summary="测试",
            strengths=[],
            concerns=[],
            experience_match_score=-1.0,
            data_sources=[]
        )


def test_dd_question_model():
    """Test DDQuestion model"""
    question = DDQuestion(
        category="Team",
        question="请提供 CEO 的详细履历",
        reasoning="验证 CEO 背景",
        priority="High",
        bp_reference="第 5 页"
    )
    
    assert question.category == "Team"
    assert question.priority == "High"
    assert question.bp_reference == "第 5 页"


def test_dd_workflow_state_enum():
    """Test DDWorkflowState enum"""
    assert DDWorkflowState.INIT == "init"
    assert DDWorkflowState.DOC_PARSE == "doc_parse"
    assert DDWorkflowState.TDD == "team_dd"
    assert DDWorkflowState.MDD == "market_dd"
    assert DDWorkflowState.COMPLETED == "completed"
    assert DDWorkflowState.ERROR == "error"


def test_dd_step_model():
    """Test DDStep model"""
    step = DDStep(
        id=1,
        title="解析 BP",
        status="running",
        progress=50.0
    )
    
    assert step.id == 1
    assert step.status == "running"
    assert step.progress == 50.0
    assert step.result is None


def test_preliminary_im_model():
    """Test PreliminaryIM model"""
    bp_data = BPStructuredData(
        company_name="测试公司",
        product_description="测试产品",
        target_market="测试市场"
    )
    
    team_analysis = TeamAnalysisOutput(
        summary="团队很强",
        strengths=["优势1"],
        concerns=[],
        experience_match_score=8.0,
        data_sources=["BP"]
    )
    
    market_analysis = MarketAnalysisOutput(
        summary="市场很大",
        market_validation="合理",
        growth_potential="高",
        competitive_landscape="激烈",
        data_sources=["网络搜索"]
    )
    
    dd_questions = [
        DDQuestion(
            category="Team",
            question="测试问题",
            reasoning="测试原因"
        )
    ]
    
    im = PreliminaryIM(
        company_name="测试公司",
        bp_structured_data=bp_data,
        team_section=team_analysis,
        market_section=market_analysis,
        dd_questions=dd_questions,
        session_id="test_session_123"
    )
    
    assert im.company_name == "测试公司"
    assert im.session_id == "test_session_123"
    assert len(im.dd_questions) == 1
    assert im.generated_by == "DD Workflow V3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
