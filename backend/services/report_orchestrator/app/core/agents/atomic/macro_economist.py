"""
Macro Economist Agent
宏观经济分析师 Agent

职责：分析宏观经济周期、货币政策、通胀趋势和板块轮动
"""
from typing import List
from app.core.roundtable.investment_agents import create_macro_economist
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名
MacroEconomistAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_macro_economist", "MacroEconomistAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "macro_economist",
    "name": {
        "zh": "宏观经济分析师",
        "en": "Macro Economist"
    },
    "description": {
        "zh": "分析宏观经济周期、货币政策、通胀趋势和板块轮动",
        "en": "Analyze macroeconomic cycles, monetary policy, inflation trends and sector rotation"
    },
    "capabilities": [
        "经济周期定位",
        "货币政策分析",
        "通胀趋势判断",
        "利率敏感度分析",
        "板块轮动建议"
    ],
    "tags": ["macro", "economics", "policy", "inflation"],
    "quick_mode_support": True
}
