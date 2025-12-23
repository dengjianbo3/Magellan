"""
Quant Strategist Agent
量化策略师 Agent

职责：因子分析、组合优化、风险量化和策略回测
"""
from app.core.roundtable.investment_agents import create_quant_strategist
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名
QuantStrategistAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_quant_strategist", "QuantStrategistAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "quant_strategist",
    "name": {
        "zh": "量化策略师",
        "en": "Quant Strategist"
    },
    "description": {
        "zh": "因子分析、组合优化、风险量化和策略回测",
        "en": "Factor analysis, portfolio optimization, risk quantification and strategy backtesting"
    },
    "capabilities": [
        "多因子分析",
        "组合优化建议",
        "风险指标计算",
        "策略回测分析",
        "情景压力测试"
    ],
    "tags": ["quant", "factor", "portfolio", "risk-metrics"],
    "quick_mode_support": True
}
