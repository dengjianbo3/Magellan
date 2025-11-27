"""
Risk Assessor Agent
风险评估师 Agent

职责：识别和评估各类投资风险（市场、运营、财务、法律等）
"""
from typing import List
from app.core.roundtable.investment_agents import create_risk_assessor
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名
RiskAssessorAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_risk_assessor", "RiskAssessorAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "risk_assessor",
    "name": {
        "zh": "风险评估师",
        "en": "Risk Assessor"
    },
    "description": {
        "zh": "识别和评估各类投资风险 (市场、运营、财务、法律等)",
        "en": "Identify and assess various investment risks (market, operational, financial, legal, etc.)"
    },
    "capabilities": [
        "市场风险评估",
        "运营风险识别",
        "财务风险分析",
        "合规风险评估",
        "风险缓解建议"
    ],
    "tags": ["risk", "compliance", "due-diligence"],
    "quick_mode_support": True
}
