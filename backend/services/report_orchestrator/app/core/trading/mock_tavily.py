"""
Mock Tavily Search Data for Testing

This module provides mock search results to test the trading system
without incurring Tavily API costs. Contains scenarios designed to
lead the AI to make LONG, SHORT, or HOLD decisions.

Usage:
    Set environment variable MOCK_TAVILY=true to enable mock mode
"""

import os
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# ============================================
# Mock Data Scenarios
# ============================================

BULLISH_NEWS = [
    {
        "title": "Bitcoin突破历史新高，机构资金持续涌入",
        "url": "https://example.com/btc-ath",
        "content": "比特币价格突破历史新高，创下$105,000的纪录。BlackRock和Fidelity的ETF流入资金创单日新高，达$12亿美元。分析师预测牛市将持续到2025年第一季度。",
        "score": 0.95
    },
    {
        "title": "美联储暗示可能降息，风险资产受提振",
        "url": "https://example.com/fed-rate",
        "content": "美联储主席鲍威尔暗示2025年可能有两次降息，市场对流动性宽松预期增强。比特币和科技股同步上涨，加密货币总市值突破$4万亿。",
        "score": 0.92
    },
    {
        "title": "大型机构增持BTC，链上数据显示巨鲸积累",
        "url": "https://example.com/whale-accumulation",
        "content": "Glassnode数据显示，持有超过1000 BTC的地址在过去一周增持了50,000 BTC。矿工持仓指数上升，表明长期持有者信心增强。",
        "score": 0.90
    },
    {
        "title": "比特币网络活跃度创新高",
        "url": "https://example.com/network-activity",
        "content": "比特币网络日活跃地址数突破120万，创2021年牛市以来新高。交易量和费用均显著增长，表明市场参与度高涨。",
        "score": 0.88
    },
    {
        "title": "加密货币友好政策接连出台",
        "url": "https://example.com/crypto-policy",
        "content": "美国多个州通过加密货币友好法案，SEC对现货ETF态度趋于开放。分析师认为监管环境改善将吸引更多机构投资者入场。",
        "score": 0.85
    }
]

BEARISH_NEWS = [
    {
        "title": "Bitcoin跌破关键支撑位，恐慌情绪蔓延",
        "url": "https://example.com/btc-crash",
        "content": "比特币价格暴跌15%，跌破$85,000支撑位。恐惧贪婪指数降至25（极度恐惧）。清算数据显示过去24小时有$5亿多头被强平。",
        "score": 0.95
    },
    {
        "title": "美联储释放鹰派信号，加息预期升温",
        "url": "https://example.com/fed-hawkish",
        "content": "美联储会议纪要显示通胀担忧加剧，官员暗示可能需要更长时间维持高利率。美元指数走强，风险资产承压。加密货币市场大幅回调。",
        "score": 0.93
    },
    {
        "title": "重大交易所遭黑客攻击，市场信心受挫",
        "url": "https://example.com/exchange-hack",
        "content": "一家主要加密货币交易所遭受黑客攻击，损失超过$1.5亿。事件引发市场恐慌，多个代币价格急挫。监管机构呼吁加强行业监管。",
        "score": 0.91
    },
    {
        "title": "巨鲸大量抛售，链上数据发出警告",
        "url": "https://example.com/whale-selling",
        "content": "链上分析显示，多个巨鲸地址在过去48小时内向交易所转入大量BTC，总计约30,000枚。这通常是抛售的前兆信号。",
        "score": 0.89
    },
    {
        "title": "比特币矿工投降，算力下降明显",
        "url": "https://example.com/miner-capitulation",
        "content": "由于价格下跌，大量矿工被迫关机或出售持仓以维持运营。比特币算力在一周内下降12%，矿工投降信号出现。",
        "score": 0.87
    }
]

NEUTRAL_NEWS = [
    {
        "title": "比特币在$90,000附近窄幅震荡",
        "url": "https://example.com/btc-consolidation",
        "content": "比特币价格在$88,000-$92,000区间内横盘整理已超过一周。交易量萎缩，市场等待明确方向指引。多空双方力量相对均衡。",
        "score": 0.90
    },
    {
        "title": "市场观望情绪浓厚，等待美联储决议",
        "url": "https://example.com/market-wait",
        "content": "投资者普遍持观望态度，等待即将公布的美联储利率决议。各大机构分析师意见分歧，部分认为应等待更明确信号再入场。",
        "score": 0.88
    },
    {
        "title": "加密货币市场成交量持续低迷",
        "url": "https://example.com/low-volume",
        "content": "过去一周加密货币现货和衍生品交易量均处于低位。市场缺乏明显催化剂，短期内可能继续震荡。建议投资者保持谨慎。",
        "score": 0.85
    },
    {
        "title": "分析师对后市看法出现分歧",
        "url": "https://example.com/analyst-divergence",
        "content": "知名分析师对比特币后市看法出现明显分歧。部分认为即将迎来突破上涨，另一部分则警告可能出现回调。建议等待趋势明确再操作。",
        "score": 0.82
    },
    {
        "title": "比特币ETF资金流入流出基本持平",
        "url": "https://example.com/etf-neutral",
        "content": "本周比特币现货ETF资金净流入接近零，显示机构投资者也在观望。市场情绪指数处于中性区间（50-55）。",
        "score": 0.80
    }
]


def _get_current_scenario() -> str:
    """
    Get the current mock scenario from environment variable.
    
    Returns:
        'bullish', 'bearish', 'neutral', or 'random'
    """
    return os.getenv("MOCK_SCENARIO", "random").lower()


def _add_timestamps(results: List[Dict]) -> List[Dict]:
    """Add realistic timestamps to mock results"""
    for i, r in enumerate(results):
        # News from past few hours
        hours_ago = random.randint(1, 12)
        timestamp = datetime.now() - timedelta(hours=hours_ago)
        r["published_date"] = timestamp.isoformat()
    return results


def get_mock_search_results(query: str, max_results: int = 5) -> Dict:
    """
    Get mock Tavily search results based on the configured scenario.
    
    Args:
        query: The search query (used for logging)
        max_results: Maximum number of results to return
        
    Returns:
        Mock search results in Tavily-compatible format
    """
    scenario = _get_current_scenario()
    
    if scenario == "random":
        scenario = random.choice(["bullish", "bearish", "neutral"])
    
    logger.info(f"[MockTavily] Using scenario: {scenario} for query: '{query}'")
    
    if scenario == "bullish":
        results = BULLISH_NEWS[:max_results]
        summary = "市场整体呈现强烈看涨氛围。机构资金持续流入，技术面突破关键阻力位，宏观经济环境有利于风险资产。建议关注做多机会。"
    elif scenario == "bearish":
        results = BEARISH_NEWS[:max_results]
        summary = "市场情绪转向悲观，多重利空因素叠加。技术面跌破支撑位，链上数据显示抛压增加，宏观不确定性上升。建议关注做空机会或观望。"
    else:  # neutral
        results = NEUTRAL_NEWS[:max_results]
        summary = "市场处于震荡整理阶段，缺乏明确方向。成交量萎缩，多空力量均衡。建议保持观望，等待趋势明确再做决策。"
    
    results = _add_timestamps(results)
    
    return {
        "success": True,
        "query": query,
        "answer": summary,
        "results": results,
        "result_count": len(results),
        "source": "Mock Tavily (Testing)",
        "message": f"[MOCK] Search '{query}' returned {len(results)} results - Scenario: {scenario.upper()}"
    }


def is_mock_mode_enabled() -> bool:
    """Check if mock Tavily mode is enabled"""
    return os.getenv("MOCK_TAVILY", "false").lower() == "true"


# ============================================
# Preset Test Scenarios
# ============================================

def set_scenario(scenario: str):
    """
    Set the current mock scenario.
    
    Args:
        scenario: 'bullish', 'bearish', 'neutral', or 'random'
    """
    os.environ["MOCK_SCENARIO"] = scenario
    logger.info(f"[MockTavily] Scenario set to: {scenario}")


def enable_mock_mode():
    """Enable mock Tavily mode"""
    os.environ["MOCK_TAVILY"] = "true"
    logger.info("[MockTavily] Mock mode ENABLED")


def disable_mock_mode():
    """Disable mock Tavily mode"""
    os.environ["MOCK_TAVILY"] = "false"
    logger.info("[MockTavily] Mock mode DISABLED")
