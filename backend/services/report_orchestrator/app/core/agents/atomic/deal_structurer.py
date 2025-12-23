"""
Deal Structurer Agent
交易结构师 Agent

职责：设计交易结构、估值谈判、条款设计和退出机制
"""
from app.core.roundtable.investment_agents import create_deal_structurer
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名
DealStructurerAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_deal_structurer", "DealStructurerAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "deal_structurer",
    "name": {
        "zh": "交易结构师",
        "en": "Deal Structurer"
    },
    "description": {
        "zh": "设计交易结构、估值谈判、条款设计和退出机制",
        "en": "Design deal structure, valuation negotiation, term sheet design and exit mechanisms"
    },
    "capabilities": [
        "估值建模",
        "条款设计",
        "股权结构优化",
        "退出机制分析",
        "谈判策略建议"
    ],
    "tags": ["deal", "valuation", "terms", "exit", "primary-market"],
    "quick_mode_support": True
}
