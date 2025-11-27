"""
Team Evaluator Agent
团队评估师 Agent

职责：评估创始团队背景、能力、经验和团队结构
"""
from typing import List
from app.core.roundtable.investment_agents import create_team_evaluator
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名，用于类型注解
TeamEvaluatorAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_team_evaluator", "TeamEvaluatorAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "team_evaluator",
    "name": {
        "zh": "团队评估师",
        "en": "Team Evaluator"
    },
    "description": {
        "zh": "评估创始团队背景、能力、经验和团队结构",
        "en": "Evaluate founding team background, capabilities, experience and team structure"
    },
    "capabilities": [
        "创始人背景分析",
        "团队能力评估",
        "组织架构评估",
        "团队协作评估",
        "人才储备分析"
    ],
    "tags": ["team", "due-diligence", "early-stage"],
    "quick_mode_support": True
}
