"""
Legal Advisor Agent
法律顾问 Agent

职责：评估法律合规、知识产权、合同风险和监管环境
"""
from app.core.roundtable.investment_agents import create_legal_advisor
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名
LegalAdvisorAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_legal_advisor", "LegalAdvisorAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "legal_advisor",
    "name": {
        "zh": "法律顾问",
        "en": "Legal Advisor"
    },
    "description": {
        "zh": "评估法律合规、知识产权、合同风险和监管环境",
        "en": "Assess legal compliance, intellectual property, contract risks and regulatory environment"
    },
    "capabilities": [
        "合规性审查",
        "知识产权评估",
        "合同风险分析",
        "监管环境分析",
        "法律风险识别"
    ],
    "tags": ["legal", "compliance", "ip"],
    "quick_mode_support": True
}
