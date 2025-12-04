"""
Trading Agents for Auto Trading System

Uses atomic agents from AgentRegistry and adds trading-specific tools.
Following the atomic agent design principle:
- Agents are defined in agents.yaml
- This module only orchestrates them with trading tools
"""

from typing import List, Dict, Any
from app.core.agent_registry import get_registry
from app.core.roundtable.investment_agents import create_leader
import logging

logger = logging.getLogger(__name__)


def create_trading_agents(toolkit=None) -> List[Any]:
    """
    Create trading agents by loading atomic agents from AgentRegistry
    and adding trading-specific tools.

    Architecture:
    - Load analysis agents from agents.yaml via AgentRegistry
    - Create Leader agent for final decision and execution
    - Add trading tools to appropriate agents
    - This follows the atomic agent design principle

    Agent Roles:
    - TechnicalAnalyst: K-line, technical indicators analysis
    - MacroEconomist: Macro economic analysis
    - SentimentAnalyst: Market sentiment, fear/greed index
    - QuantStrategist: Quantitative analysis
    - RiskAssessor: Risk assessment (analysis only, no execution)
    - Leader: Synthesize all opinions, make final decision, EXECUTE trades

    Args:
        toolkit: TradingToolkit instance with analysis and execution tools

    Returns:
        List of Agent instances configured for trading
    """
    registry = get_registry()
    agents = []

    # Define which atomic agents to use for analysis
    # These IDs must match agents.yaml
    analysis_agent_ids = [
        "technical_analyst",    # K-line, technical indicators
        "macro_economist",      # Macro economic analysis
        "sentiment_analyst",    # Market sentiment, fear/greed index
        "risk_assessor",        # Risk assessment (analysis only)
        "quant_strategist",     # Quantitative analysis
    ]

    # Load analysis agents from registry
    for agent_id in analysis_agent_ids:
        try:
            # Create agent instance from registry
            # Pass language='zh' for Chinese output
            agent = registry.create_agent(agent_id, language='zh')
            agents.append(agent)
        except Exception as e:
            logger.error(f"Failed to load agent '{agent_id}' from registry: {e}")
            continue

    # Create Leader agent for final decision and execution
    try:
        leader = create_leader(language='zh')
        agents.append(leader)
        logger.info("Created Leader agent for trading decision execution")
    except Exception as e:
        logger.error(f"Failed to create Leader agent: {e}")

    # Register trading tools if toolkit provided
    if toolkit:
        analysis_tools = toolkit.get_analysis_tools()
        # ❌ REMOVED: execution_tools - Leader no longer executes trades
        # execution_tools = toolkit.get_execution_tools()

        for agent in agents:
            # Analysis agents get analysis tools to perform their analysis
            # Leader does NOT need ANY tools - it only synthesizes opinions and makes decisions
            is_leader = hasattr(agent, 'id') and agent.id == "Leader"

            if not is_leader:
                # Analysis agents (TechnicalAnalyst, MacroEconomist, etc.) get analysis tools
                for tool in analysis_tools:
                    agent.register_tool(tool)
                logger.info(f"Registered {len(analysis_tools)} analysis tools to {agent.name}")

            # 🔧 ARCHITECTURE CHANGE: Leader no longer gets execution tools
            # - Leader只负责决策（synthesize opinions, make decisions）
            # - TradeExecutor负责执行（execute trades）
            # - This follows Separation of Concerns principle
            if is_leader:
                logger.info(f"Leader has NO tools - it only makes decisions, TradeExecutor handles execution")

    return agents


def get_trading_agent_config() -> List[Dict[str, Any]]:
    """
    Get agent configuration for frontend display.

    Returns simplified config without actual Agent instances.
    Maps atomic agents to trading-specific display information.
    """
    # Get agent info from registry
    registry = get_registry()

    # Map agent IDs to display configuration
    agent_configs = []

    # Technical Analyst
    tech_config = registry.get_agent_info("technical_analyst")
    if tech_config:
        agent_configs.append({
            "id": "technical_analyst",
            "name": tech_config['name'].get('zh', '技术分析师'),
            "name_en": tech_config['name'].get('en', 'Technical Analyst'),
            "role": "技术面分析",
            "icon": "candlestick_chart",
            "description": "K线形态、技术指标、支撑阻力位分析",
            "capabilities": ["RSI/MACD分析", "K线形态识别", "趋势判断"]
        })

    # Macro Economist
    macro_config = registry.get_agent_info("macro_economist")
    if macro_config:
        agent_configs.append({
            "id": "macro_economist",
            "name": macro_config['name'].get('zh', '宏观经济分析师'),
            "name_en": macro_config['name'].get('en', 'Macro Economist'),
            "role": "宏观分析",
            "icon": "public",
            "description": "全球宏观经济、货币政策、流动性分析",
            "capabilities": ["货币政策分析", "经济周期判断", "风险事件评估"]
        })

    # Sentiment Analyst
    sentiment_config = registry.get_agent_info("sentiment_analyst")
    if sentiment_config:
        agent_configs.append({
            "id": "sentiment_analyst",
            "name": sentiment_config['name'].get('zh', '情绪分析师'),
            "name_en": sentiment_config['name'].get('en', 'Sentiment Analyst'),
            "role": "情绪分析",
            "icon": "psychology",
            "description": "恐慌贪婪指数、资金费率、市场情绪分析",
            "capabilities": ["情绪指标解读", "资金流向分析", "逆向思维"]
        })

    # Risk Assessor (as Risk Manager in trading context)
    risk_config = registry.get_agent_info("risk_assessor")
    if risk_config:
        agent_configs.append({
            "id": "risk_assessor",
            "name": "风险管理师",  # Override name for trading context
            "name_en": "Risk Manager",
            "role": "风险管理",
            "icon": "shield",
            "description": "仓位控制、止盈止损、风险评估",
            "capabilities": ["仓位管理", "风险收益比", "资金保护"]
        })

    # Quant Strategist
    quant_config = registry.get_agent_info("quant_strategist")
    if quant_config:
        agent_configs.append({
            "id": "quant_strategist",
            "name": quant_config['name'].get('zh', '量化策略师'),
            "name_en": quant_config['name'].get('en', 'Quant Strategist'),
            "role": "量化分析",
            "icon": "analytics",
            "description": "统计分析、概率计算、历史回测",
            "capabilities": ["统计分析", "概率评估", "波动率分析"]
        })

    return agent_configs
