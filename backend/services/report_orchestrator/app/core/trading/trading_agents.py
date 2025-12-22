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
        "onchain_analyst",      # On-chain data, whale monitoring
        "risk_assessor",        # Risk assessment (analysis only)
        "quant_strategist",     # Quantitative analysis
    ]

    # Load analysis agents from registry
    for agent_id in analysis_agent_ids:
        try:
            # Create agent instance from registry
            # Pass language='en' for English output (better for LLM understanding)
            agent = registry.create_agent(agent_id, language='en')
            agents.append(agent)
            logger.info(f"✅ Loaded agent '{agent_id}' -> name='{agent.name}', id='{agent.id}'")
        except Exception as e:
            logger.error(f"Failed to load agent '{agent_id}' from registry: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Create Leader agent for final decision and execution
    try:
        leader = create_leader(language='en')
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

            # ARCHITECTURE CHANGE: Leader no longer gets execution tools
            # - Leader only makes decisions (synthesize opinions, make decisions)
            # - TradeExecutor handles execution (execute trades)
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
            "name": tech_config['name'].get('en', 'Technical Analyst'),
            "role": "Technical Analysis",
            "icon": "candlestick_chart",
            "description": "K-line patterns, technical indicators, support/resistance analysis",
            "capabilities": ["RSI/MACD Analysis", "K-line Pattern Recognition", "Trend Analysis"]
        })

    # Macro Economist
    macro_config = registry.get_agent_info("macro_economist")
    if macro_config:
        agent_configs.append({
            "id": "macro_economist",
            "name": macro_config['name'].get('en', 'Macro Economist'),
            "role": "Macro Analysis",
            "icon": "public",
            "description": "Global macroeconomics, monetary policy, liquidity analysis",
            "capabilities": ["Monetary Policy Analysis", "Economic Cycle Assessment", "Risk Event Evaluation"]
        })

    # Sentiment Analyst
    sentiment_config = registry.get_agent_info("sentiment_analyst")
    if sentiment_config:
        agent_configs.append({
            "id": "sentiment_analyst",
            "name": sentiment_config['name'].get('en', 'Sentiment Analyst'),
            "role": "Sentiment Analysis",
            "icon": "psychology",
            "description": "Fear/Greed Index, funding rates, market sentiment analysis",
            "capabilities": ["Sentiment Indicator Analysis", "Fund Flow Analysis", "Contrarian Thinking"]
        })

    # Risk Assessor (as Risk Manager in trading context)
    risk_config = registry.get_agent_info("risk_assessor")
    if risk_config:
        agent_configs.append({
            "id": "risk_assessor",
            "name": "Risk Manager",
            "role": "Risk Management",
            "icon": "shield",
            "description": "Position control, take profit/stop loss, risk assessment",
            "capabilities": ["Position Management", "Risk/Reward Ratio", "Capital Protection"]
        })

    # Quant Strategist
    quant_config = registry.get_agent_info("quant_strategist")
    if quant_config:
        agent_configs.append({
            "id": "quant_strategist",
            "name": quant_config['name'].get('en', 'Quant Strategist'),
            "role": "Quantitative Analysis",
            "icon": "analytics",
            "description": "Statistical analysis, probability calculation, historical backtesting",
            "capabilities": ["Statistical Analysis", "Probability Assessment", "Volatility Analysis"]
        })

    # Onchain Analyst (Phase 3)
    onchain_config = registry.get_agent_info("onchain_analyst")
    if onchain_config:
        agent_configs.append({
            "id": "onchain_analyst",
            "name": onchain_config['name'].get('en', 'Onchain Analyst'),
            "role": "On-Chain Analysis",
            "icon": "link",
            "description": "Whale monitoring, exchange flows, DeFi TVL, on-chain metrics",
            "capabilities": ["Whale Tracking", "Exchange Flow Analysis", "DeFi TVL Monitoring", "MVRV/SOPR Indicators"]
        })

    return agent_configs
