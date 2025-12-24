"""
ESG Analyst Agent
ESG 分析师 Agent

职责：评估环境、社会、公司治理因素，识别ESG风险与机会
"""
from app.core.roundtable.investment_agents import create_esg_analyst
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名
ESGAnalystAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_esg_analyst", "ESGAnalystAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "esg_analyst",
    "name": {
        "zh": "ESG分析师",
        "en": "ESG Analyst"
    },
    "description": {
        "zh": "评估环境、社会、公司治理因素，识别ESG风险与机会",
        "en": "Evaluate Environmental, Social, and Governance factors, identify ESG risks and opportunities"
    },
    "capabilities": [
        "碳排放分析",
        "环境合规评估",
        "社会责任评价",
        "公司治理评分",
        "ESG投资机会识别"
    ],
    "tags": ["esg", "sustainability", "governance", "impact"],
    "quick_mode_support": True
}
