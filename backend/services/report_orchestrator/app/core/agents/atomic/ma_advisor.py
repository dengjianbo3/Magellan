"""
M&A Advisor Agent
并购顾问 Agent

职责：并购标的筛选、战略契合度分析、协同效应量化和整合风险评估
"""
from typing import List
from app.core.roundtable.investment_agents import create_ma_advisor
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名
MAAdvisorAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_ma_advisor", "MAAdvisorAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "ma_advisor",
    "name": {
        "zh": "并购顾问",
        "en": "M&A Advisor"
    },
    "description": {
        "zh": "并购标的筛选、战略契合度分析、协同效应量化和整合风险评估",
        "en": "M&A target screening, strategic fit analysis, synergy quantification and integration risk assessment"
    },
    "capabilities": [
        "标的筛选评估",
        "战略契合度分析",
        "协同效应量化",
        "整合风险识别",
        "交易可行性评估"
    ],
    "tags": ["ma", "merger", "acquisition", "synergy", "integration"],
    "quick_mode_support": True
}
