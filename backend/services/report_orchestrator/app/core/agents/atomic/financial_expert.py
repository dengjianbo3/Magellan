"""
Financial Expert Agent
财务专家 Agent

职责：分析财务数据、盈利能力、现金流和估值
"""
from typing import List
from app.core.roundtable.investment_agents import create_financial_expert
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名
FinancialExpertAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_financial_expert", "FinancialExpertAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "financial_expert",
    "name": {
        "zh": "财务专家",
        "en": "Financial Expert"
    },
    "description": {
        "zh": "分析财务数据、盈利能力、现金流和估值",
        "en": "Analyze financial data, profitability, cash flow and valuation"
    },
    "capabilities": [
        "财务健康度分析",
        "盈利能力评估",
        "现金流分析",
        "估值建模",
        "财务风险识别"
    ],
    "tags": ["finance", "valuation", "profitability"],
    "quick_mode_support": True
}
