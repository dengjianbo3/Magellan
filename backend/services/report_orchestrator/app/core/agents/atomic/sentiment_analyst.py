"""
Sentiment Analyst Agent
情绪分析师 Agent

职责：分析市场情绪、新闻舆情、社交媒体信号和机构观点
"""
from typing import List
from app.core.roundtable.investment_agents import create_sentiment_analyst
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名
SentimentAnalystAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_sentiment_analyst", "SentimentAnalystAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "sentiment_analyst",
    "name": {
        "zh": "情绪分析师",
        "en": "Sentiment Analyst"
    },
    "description": {
        "zh": "分析市场情绪、新闻舆情、社交媒体信号和机构观点",
        "en": "Analyze market sentiment, news coverage, social media signals and institutional views"
    },
    "capabilities": [
        "新闻情绪监测",
        "社交媒体分析",
        "分析师共识追踪",
        "资金流向监测",
        "反向信号识别"
    ],
    "tags": ["sentiment", "news", "social", "consensus"],
    "quick_mode_support": True
}
