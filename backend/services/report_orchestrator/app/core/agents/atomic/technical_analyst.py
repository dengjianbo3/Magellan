"""
Technical Analyst Agent
技术分析师 Agent

职责：基于K线形态、技术指标进行量化分析，提供交易信号
"""
from app.core.roundtable.investment_agents import create_technical_analyst
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名
TechnicalAnalystAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_technical_analyst", "TechnicalAnalystAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "technical_analyst",
    "name": {
        "zh": "技术分析师",
        "en": "Technical Analyst"
    },
    "description": {
        "zh": "基于K线形态、技术指标进行量化分析，提供支撑阻力位、趋势判断和交易信号",
        "en": "Quantitative analysis based on candlestick patterns and technical indicators"
    },
    "capabilities": [
        "K线形态识别 (头肩、双顶、三角形等)",
        "技术指标计算 (RSI, MACD, KDJ, 布林带等)",
        "均线分析 (EMA, SMA, 均线排列)",
        "支撑阻力位识别 (斐波那契、枢轴点)",
        "趋势判断与交易信号",
        "多时间周期联动分析"
    ],
    "tags": ["technical-analysis", "trading", "quantitative", "crypto", "stock"],
    "quick_mode_support": True
}
