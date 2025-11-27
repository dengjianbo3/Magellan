"""
Market Analyst Agent
市场分析师 Agent

职责：分析市场规模、竞争格局、行业趋势和增长潜力
"""
from typing import List
from app.core.roundtable.investment_agents import create_market_analyst
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名
MarketAnalystAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_market_analyst", "MarketAnalystAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "market_analyst",
    "name": {
        "zh": "市场分析师",
        "en": "Market Analyst"
    },
    "description": {
        "zh": "分析市场规模、竞争格局、行业趋势和增长潜力",
        "en": "Analyze market size, competitive landscape, industry trends and growth potential"
    },
    "capabilities": [
        "市场规模测算 (TAM/SAM/SOM)",
        "竞争对手分析",
        "行业趋势研判",
        "市场增长预测",
        "市场定位评估"
    ],
    "tags": ["market", "competition", "growth"],
    "quick_mode_support": True
}
