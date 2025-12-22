"""
Market Analysis Phase

Phase 1: Analysts gather and analyze market data.
"""

from datetime import datetime
from typing import Dict, Any, Optional
import logging

from .base import PhaseExecutor, PhaseContext, PhaseResult

logger = logging.getLogger(__name__)


class MarketAnalysisPhase(PhaseExecutor):
    """
    Phase 1: Market Analysis
    
    Technical Analyst, Macro Economist, Sentiment Analyst, and Quant Strategist
    each analyze the market from their perspective.
    """
    
    phase_name = "Market Analysis"
    phase_number = 1
    
    # Analysts to run in this phase
    ANALYST_IDS = [
        "TechnicalAnalyst",
        "MacroEconomist", 
        "SentimentAnalyst",
        "QuantStrategist"
    ]
    
    async def execute(self, context: PhaseContext) -> PhaseResult:
        """Execute market analysis phase."""
        start_time = datetime.now()
        self._log_phase_start(context)
        
        results = {}
        errors = []
        
        for agent_id in self.ANALYST_IDS:
            agent = self._get_agent(agent_id)
            if not agent:
                logger.warning(f"Agent {agent_id} not found, skipping")
                continue
            
            try:
                prompt = self._build_agent_prompt(agent_id, context)
                response = await self._run_agent_with_timeout(agent, prompt)
                
                if response:
                    results[agent_id] = {
                        "response": response,
                        "summary": self._extract_summary(response),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Add to context messages
                    agent_name = getattr(agent, 'name', agent_id)
                    self._add_message(
                        context,
                        agent_id=agent_id,
                        agent_name=agent_name,
                        content=response,
                        message_type="analysis"
                    )
                else:
                    errors.append(f"{agent_id}: No response")
                    
            except Exception as e:
                logger.error(f"Error running {agent_id}: {e}")
                errors.append(f"{agent_id}: {str(e)}")
        
        # Store results in context
        context.analysis_results = results
        
        duration = (datetime.now() - start_time).total_seconds()
        
        result = PhaseResult(
            phase_name=self.phase_name,
            success=len(results) > 0,
            data={
                "agent_count": len(results),
                "results": results,
                "errors": errors
            },
            error="; ".join(errors) if errors and not results else None,
            duration_seconds=duration
        )
        
        self._log_phase_end(result)
        return result
    
    def _build_agent_prompt(self, agent_id: str, context: PhaseContext) -> str:
        """Build analysis prompt for specific agent."""
        symbol = context.config.symbol
        position_hint = context.position_context.to_summary()
        position_analysis = self._get_neutral_analysis_prompt(context)
        
        prompts = {
            "TechnicalAnalyst": f"""Analyze the current technical situation for {symbol}.

{position_hint}

{position_analysis}

**IMPORTANT**: Use your tools to get real-time market data.

**Required Analysis Steps**:
1. Get the current market price for {symbol}
2. Fetch 4-hour candlestick data (100 candles)
3. Calculate technical indicators (RSI, MACD, Bollinger Bands)

Based on real data, provide **objective analysis**:
- Current price and 24h change
- Technical indicators: RSI, MACD, Bollinger Bands
- Trend analysis and key support/resistance levels
- Technical support for **LONG** position (strong/medium/weak/against)
- Technical support for **SHORT** position (strong/medium/weak/against)
- Your technical score and **independent** trading recommendation""",

            "MacroEconomist": f"""Analyze the current macro-economic environment affecting {symbol}.

{position_hint}

{position_analysis}

**IMPORTANT**: Search for the latest market news and information.

**Required Analysis Steps**:
1. Search for "Bitcoin BTC market news today price analysis"
2. Search for "cryptocurrency institutional investment outlook"

Based on search results, provide **objective analysis**:
- Current market liquidity conditions
- Institutional investor movements
- USD index correlation with cryptocurrency
- Macro support for **LONG** position (strong/medium/weak/against)
- Macro support for **SHORT** position (strong/medium/weak/against)
- Your macro score and **independent** directional judgment""",

            "SentimentAnalyst": f"""Analyze the current market sentiment for {symbol}.

{position_hint}

{position_analysis}

**IMPORTANT**: Use your tools to fetch real-time sentiment data.

**Required Analysis Steps**:
1. Get the Fear & Greed Index
2. Get the funding rate for {symbol}
3. Search for "Bitcoin BTC market sentiment social media"

Based on real data, provide **objective analysis**:
- Fear & Greed Index value and interpretation
- Funding rate and long/short ratio
- Social media and news sentiment
- Sentiment support for **LONG** position (strong/medium/weak/against)
- Sentiment support for **SHORT** position (strong/medium/weak/against)
- Your sentiment score and **independent** directional judgment""",

            "QuantStrategist": f"""Analyze quantitative data and statistical signals for {symbol}.

{position_hint}

{position_analysis}

**IMPORTANT**: Use your tools to get real-time data for quantitative analysis.

**Required Analysis Steps**:
1. Get the current market price for {symbol}
2. Fetch 1-hour candlestick data (200 candles)
3. Calculate technical indicators for 1-hour timeframe

Based on real data, provide **objective** quantitative analysis:
- Price volatility and volume analysis
- Multi-timeframe trend consistency
- Momentum and trend indicator signals
- Quantitative support for **LONG** position (strong/medium/weak/against)
- Quantitative support for **SHORT** position (strong/medium/weak/against)
- Your quantitative score and **independent** directional judgment"""
        }
        
        return prompts.get(agent_id, self._get_default_prompt(symbol, position_hint))
    
    def _get_neutral_analysis_prompt(self, context: PhaseContext) -> str:
        """Generate neutral position analysis prompt to avoid confirmation bias."""
        if not context.position_context.has_position:
            return """**Analysis Requirements**:
- Provide objective market analysis
- Evaluate both bullish and bearish scenarios equally
- Base recommendations on data, not assumptions"""
        
        return """**CRITICAL: Avoid Confirmation Bias**
- You currently have a position, but your analysis must be OBJECTIVE
- Do NOT favor the current position direction
- Analyze BOTH directions (long AND short) with equal rigor
- If data suggests reversing, say so clearly
- Your job is to find truth, not to justify existing positions"""
    
    def _get_default_prompt(self, symbol: str, position_hint: str) -> str:
        """Default analysis prompt."""
        return f"""Analyze the current market situation for {symbol}.

{position_hint}

**IMPORTANT**: Use tools to get real-time market data.

Available tools include:
- Market price query
- Search for relevant news

Provide your analysis and views based on real data."""
    
    def _extract_summary(self, response: str, max_length: int = 500) -> str:
        """Extract summary from agent response."""
        if not response:
            return ""
        
        # Take first paragraph or truncate
        lines = response.strip().split('\n\n')
        summary = lines[0] if lines else response
        
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary
