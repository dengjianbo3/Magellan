"""
Atomic Agents Module
原子 Agent 模块

定义7个原子 Agent - 系统的基本分析单元
所有场景（分析模块、圆桌会议）都通过组合这些原子 Agent 实现

原子 Agent 列表:
1. team_evaluator - 团队评估师
2. market_analyst - 市场分析师
3. financial_expert - 财务专家
4. risk_assessor - 风险评估师
5. tech_specialist - 技术专家
6. legal_advisor - 法律顾问
7. technical_analyst - 技术分析师（量化/K线）
"""

from .team_evaluator import create_team_evaluator, TeamEvaluatorAgent
from .market_analyst import create_market_analyst, MarketAnalystAgent
from .financial_expert import create_financial_expert, FinancialExpertAgent
from .risk_assessor import create_risk_assessor, RiskAssessorAgent
from .tech_specialist import create_tech_specialist, TechSpecialistAgent
from .legal_advisor import create_legal_advisor, LegalAdvisorAgent
from .technical_analyst import create_technical_analyst, TechnicalAnalystAgent

__all__ = [
    # 工厂函数 (用于创建 Agent 实例)
    "create_team_evaluator",
    "create_market_analyst",
    "create_financial_expert",
    "create_risk_assessor",
    "create_tech_specialist",
    "create_legal_advisor",
    "create_technical_analyst",

    # Agent 类 (用于类型注解)
    "TeamEvaluatorAgent",
    "MarketAnalystAgent",
    "FinancialExpertAgent",
    "RiskAssessorAgent",
    "TechSpecialistAgent",
    "LegalAdvisorAgent",
    "TechnicalAnalystAgent",
]


# Agent ID 到工厂函数的映射
AGENT_FACTORY_MAP = {
    "team_evaluator": create_team_evaluator,
    "market_analyst": create_market_analyst,
    "financial_expert": create_financial_expert,
    "risk_assessor": create_risk_assessor,
    "tech_specialist": create_tech_specialist,
    "legal_advisor": create_legal_advisor,
    "technical_analyst": create_technical_analyst,
}


def get_atomic_agent_factory(agent_id: str):
    """
    根据 agent_id 获取对应的工厂函数

    Args:
        agent_id: Agent 标识

    Returns:
        工厂函数，如果不存在则返回 None
    """
    return AGENT_FACTORY_MAP.get(agent_id)


def list_atomic_agents():
    """
    列出所有可用的原子 Agent

    Returns:
        Agent ID 列表
    """
    return list(AGENT_FACTORY_MAP.keys())
