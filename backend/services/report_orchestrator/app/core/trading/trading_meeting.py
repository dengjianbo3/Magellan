"""
Trading Meeting

Specialized roundtable meeting for trading decisions.
Extends the base Meeting class with trading-specific phases and signal generation.
"""

import asyncio
import logging
import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field

from app.core.roundtable.meeting import Meeting
from app.core.roundtable.agent import Agent
from app.core.roundtable.rewoo_agent import ReWOOAgent
from app.models.trading_models import TradingSignal, AgentVote
from app.core.trading.retry_handler import (
    RetryHandler, RetryConfig, CircuitBreaker,
    CircuitBreakerOpenError, get_llm_retry_handler
)
from app.core.trading.agent_memory import (
    get_memory_store, AgentMemoryStore,
    record_agent_predictions, generate_trade_reflections
)
from app.core.trading.price_service import get_current_btc_price
from app.core.trading.position_context import PositionContext

# Import from new refactored modules
from app.core.trading.trading_config import TradingMeetingConfig
from app.core.trading.vote_calculator import (
    calculate_confidence_from_votes,
    calculate_leverage_from_confidence,
    calculate_amount_from_confidence
)

logger = logging.getLogger(__name__)


# Note: The following are now imported from modular files:
# - TradingMeetingConfig from trading_config.py
# - calculate_confidence_from_votes from vote_calculator.py
# - calculate_leverage_from_confidence from vote_calculator.py
# - calculate_amount_from_confidence from vote_calculator.py


class TradingMeeting(Meeting):
    """
    Specialized meeting for trading decisions.

    Phases:
    1. Market Analysis - Agents gather and analyze market data
    2. Signal Generation - Each agent provides their recommendation
    3. Risk Assessment - Risk manager evaluates proposed trade
    4. Consensus Building - Leader synthesizes opinions
    5. Execution Decision - Final decision and execution

    The meeting produces a TradingSignal that can be executed.
    """

    def __init__(
        self,
        agents: List[Agent],
        llm_service=None,
        config: Optional[TradingMeetingConfig] = None,
        on_message: Optional[Callable] = None,
        on_signal: Optional[Callable] = None,
        retry_handler: Optional[RetryHandler] = None,
        toolkit=None  # 🔧 NEW: Accept toolkit for TradeExecutor
    ):
        super().__init__(
            agents=agents,
            llm_service=llm_service,
            on_message=on_message
        )

        self.config = config or TradingMeetingConfig()
        self.on_message = on_message  # Store locally for easy access
        self.on_signal = on_signal
        self.retry_handler = retry_handler or get_llm_retry_handler()
        self.toolkit = toolkit  # 🔧 NEW: Store toolkit for TradeExecutor

        self._agent_votes: List[AgentVote] = []
        self._final_signal: Optional[TradingSignal] = None
        self._execution_result: Optional[Dict] = None
        self._memory_store: Optional[AgentMemoryStore] = None
        # Track executed tool calls (tool_name, params, result)
        self._last_executed_tools: List[Dict[str, Any]] = []

        # Record Agent predictions (for reflection after closing position)
        self._current_predictions: Dict[str, Dict[str, Any]] = {}
        self._current_trade_id: Optional[str] = None

        # Register position closed callback (for triggering Agent reflection)
        self._register_position_closed_callback()

    def _register_position_closed_callback(self):
        """Register position closed callback for triggering Agent reflection generation"""
        if not self.toolkit:
            logger.debug("No toolkit available, skipping position closed callback registration")
            return

        paper_trader = getattr(self.toolkit, 'paper_trader', None)
        if not paper_trader:
            logger.debug("No paper_trader in toolkit, skipping callback registration")
            return

        # Save original callback (if any)
        original_callback = getattr(paper_trader, 'on_position_closed', None)

        async def on_position_closed_with_reflection(position, pnl, reason="manual"):
            """Position closed callback: trigger Agent reflection generation"""
            logger.info(f"🔄 Position closed callback triggered: PnL=${pnl:.2f}, reason={reason}")

            try:
                # Get trade ID
                trade_id = getattr(position, 'id', None) or self._current_trade_id
                if not trade_id:
                    logger.warning("No trade_id available for reflection generation")
                    return

                # Calculate holding duration
                holding_hours = 0
                opened_at = getattr(position, 'opened_at', None)
                if opened_at:
                    if isinstance(opened_at, str):
                        opened_at = datetime.fromisoformat(opened_at)
                    holding_hours = (datetime.now() - opened_at).total_seconds() / 3600

                # Build trade result
                trade_result = {
                    'entry_price': getattr(position, 'entry_price', 0),
                    'exit_price': getattr(position, 'current_price', 0),
                    'pnl': pnl,
                    'direction': getattr(position, 'direction', 'long'),
                    'reason': reason,
                    'holding_hours': holding_hours
                }

                # Generate Agent reflections
                logger.info(f"📝 Generating agent reflections for trade {trade_id}...")

                # Get an available agent as LLM client (for generating reflections)
                llm_client = None
                if self.agents:
                    llm_client = self.agents[0]

                reflections = await generate_trade_reflections(
                    trade_id=trade_id,
                    trade_result=trade_result,
                    llm_client=llm_client
                )

                if reflections:
                    logger.info(f"✅ Generated {len(reflections)} agent reflections")
                    for r in reflections:
                        status = "correct" if r.prediction_was_correct else "incorrect"
                        logger.info(f"  - {r.agent_name}: prediction {status}, lesson: {r.lessons_learned[0] if r.lessons_learned else 'none'}")
                else:
                    logger.warning(f"No reflections generated for trade {trade_id}")

            except Exception as e:
                logger.error(f"Error in position closed callback: {e}", exc_info=True)

            # Call original callback (if any)
            if original_callback:
                try:
                    await original_callback(position, pnl, reason)
                except Exception as e:
                    logger.error(f"Error in original position closed callback: {e}")

        # Register callback
        paper_trader.on_position_closed = on_position_closed_with_reflection
        logger.info("✅ Registered position closed callback for agent reflection")

    async def _record_agent_predictions_for_trade(self, market_price: float = 0.0):
        """
        Record all Agent predictions (for reflection after closing position)

        Called after successful position opening, records all Agent votes from current meeting to prediction storage.
        """
        try:
            # Get current position ID as trade_id
            trade_id = None
            if self.toolkit and hasattr(self.toolkit, 'paper_trader'):
                position = await self.toolkit.paper_trader.get_position()
                if position:
                    trade_id = getattr(position, 'id', None)

            if not trade_id:
                # If no position ID, generate one using timestamp
                trade_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                logger.warning(f"No position ID found, using generated trade_id: {trade_id}")

            # Save trade_id for lookup when closing position
            self._current_trade_id = trade_id

            # Collect predictions from _agent_votes
            votes_dict = {}
            for vote in self._agent_votes:
                votes_dict[vote.agent_name] = {
                    'direction': vote.direction,
                    'confidence': vote.confidence,
                    'reasoning': vote.reasoning,
                    'key_factors': [],  # Can be extracted from reasoning
                    'market_snapshot': {}
                }

            if votes_dict:
                await record_agent_predictions(
                    trade_id=trade_id,
                    votes=votes_dict,
                    market_price=market_price
                )
                logger.info(f"📝 Recorded {len(votes_dict)} agent predictions for trade {trade_id}")
            else:
                logger.warning("No agent votes to record as predictions")

        except Exception as e:
            logger.error(f"Error recording agent predictions: {e}", exc_info=True)

    @property
    def final_signal(self) -> Optional[TradingSignal]:
        return self._final_signal

    @property
    def agent_votes(self) -> List[AgentVote]:
        return self._agent_votes

    async def run(self, context: Optional[str] = None) -> Optional[TradingSignal]:
        """
        Run the trading meeting.

        Args:
            context: Additional context for the meeting (e.g., trigger reason)

        Returns:
            TradingSignal if a trade decision is made, None otherwise
        """
        logger.info(f"Starting trading meeting for {self.config.symbol}")

        # Step 0: Collect position context
        logger.info("[PositionContext] Collecting position context...")
        position_context = await self._get_position_context()
        logger.info(f"[PositionContext] Has position: {position_context.has_position}")
        if position_context.has_position and position_context.direction:
            logger.info(f"[PositionContext] Direction: {position_context.direction}, "
                       f"PnL: ${position_context.unrealized_pnl:.2f} ({position_context.unrealized_pnl_percent:+.2f}%), "
                       f"Can add: {position_context.can_add_position}")

        # Build the meeting agenda (with position context)
        agenda = self._build_agenda(context, position_context)

        # Add agenda as initial message
        self._add_message(
            agent_id="system",
            agent_name="System",
            content=agenda,
            message_type="agenda"
        )

        try:
            # Phase 1: Market Analysis (with position context)
            await self._run_market_analysis_phase(position_context)

            # Phase 2: Signal Generation (collect votes, with position context)
            await self._run_signal_generation_phase(position_context)

            # Phase 3: Risk Assessment (with position context)
            await self._run_risk_assessment_phase(position_context)

            # Phase 4: Consensus Building (Leader summarizes meeting)
            _temp_signal = await self._run_consensus_phase(position_context)
            # Note: Phase 4 no longer produces final signal, only Leader's summary

            # Phase 5: Trade Execution (TradeExecutor analyzes and decides)
            # NEW: TradeExecutor analyzes Leader's summary and makes decision
            # Regardless of what Leader said, TradeExecutor will run
            await self._run_execution_phase(_temp_signal, position_context)

            # Final signal comes from TradeExecutor
            if self._final_signal:
                # Notify callback
                if self.on_signal:
                    await self.on_signal(self._final_signal)

            return self._final_signal

        except Exception as e:
            logger.error(f"Error in trading meeting: {e}")
            self._add_message(
                agent_id="system",
                agent_name="System",
                content=f"Meeting error occurred: {str(e)}",
                message_type="error"
            )
            return None

    def _build_agenda(self, context: Optional[str] = None, position_context: Optional[PositionContext] = None) -> str:
        """Build the meeting agenda with position context"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        reason = context or "Scheduled analysis"

        # Add position status to agenda
        position_summary = ""
        if position_context:
            if position_context.has_position and position_context.direction:
                pnl_emoji = "📈" if position_context.unrealized_pnl >= 0 else "📉"
                position_summary = f"""
## 💼 Current Position Status ⚠️ Important!

- **Position**: {position_context.direction.upper()} ({position_context.leverage}x leverage)
- **Entry Price**: ${position_context.entry_price:.2f}
- **Current Price**: ${position_context.current_price:.2f}
- {pnl_emoji} **Unrealized PnL**: ${position_context.unrealized_pnl:.2f} ({position_context.unrealized_pnl_percent:+.2f}%)
- **Position Size**: {position_context.current_position_percent*100:.1f}% / {position_context.max_position_percent*100:.1f}%
- **Status**: {'✅ Can add more' if position_context.can_add_position else '❌ Max position reached'}
- **Holding Duration**: {position_context.holding_duration_hours:.1f} hours

⚠️ **All experts please consider current position when analyzing!**
"""
            else:
                position_summary = f"""
## 💼 Current Position Status

- **Position**: No position
- **Available Balance**: ${position_context.available_balance:.2f} USDT
- **Total Equity**: ${position_context.total_equity:.2f} USDT
- **Status**: ✅ Free to open position
"""

        return f"""# Trading Analysis Meeting

**Time**: {now}
**Symbol**: {self.config.symbol}
**Trigger Reason**: {reason}
{position_summary}
## Meeting Agenda

1. **Market Analysis Phase**: Experts obtain and analyze market data
2. **Signal Generation Phase**: Each expert provides trading recommendations
3. **Risk Assessment Phase**: Risk manager evaluates trading risks
4. **Consensus Building Phase**: Leader synthesizes opinions to form decision
5. **Execution Phase**: Execute trades based on decision

## Trading Parameters
- Max Leverage: {self.config.max_leverage}x (options: 1,2,3,...,{self.config.max_leverage})
- Max Position: {self.config.max_position_percent*100:.0f}% of funds
- Min Confidence Required: {self.config.min_confidence}%

## Leverage Selection Guide
- High confidence (>80%): {int(self.config.max_leverage * 0.5)}-{self.config.max_leverage}x
- Medium confidence (60-80%): {int(self.config.max_leverage * 0.25)}-{int(self.config.max_leverage * 0.5)}x
- Low confidence (<60%): 1-{int(self.config.max_leverage * 0.25)}x or hold

Experts, please begin your analysis.
"""

    async def _run_market_analysis_phase(self, position_context: PositionContext):
        """Phase 1: Market Analysis"""
        self._add_message(
            agent_id="system",
            agent_name="System",
            content="## Phase 1: Market Analysis\n\nTechnical Analyst, Macro Economist, and Sentiment Analyst, please begin your market analysis.",
            message_type="phase"
        )

        # Run analysis agents (using agent names from ReWOO agents)
        analysis_agents = ["TechnicalAnalyst", "MacroEconomist", "SentimentAnalyst"]

        # Position context for all analysts
        position_hint = position_context.to_summary()

        # Neutral analysis prompt to avoid confirmation bias
        position_analysis_prompt = self._get_neutral_position_analysis_prompt(position_context)

        agent_prompts = {
            "TechnicalAnalyst": f"""Analyze the current technical situation for {self.config.symbol}.

{position_hint}

{position_analysis_prompt}

**IMPORTANT**: Use your tools to get real-time market data. The system will automatically execute tool calls for you.

**Required Analysis Steps**:
1. Get the current market price for {self.config.symbol}
2. Fetch 4-hour candlestick data (100 candles)
3. Calculate technical indicators (RSI, MACD, Bollinger Bands)

Based on real data, provide **objective analysis**:
- Current price and 24h change
- Technical indicators: RSI, MACD, Bollinger Bands
- Trend analysis and key support/resistance levels
- Technical support for **LONG** position (strong/medium/weak/against)
- Technical support for **SHORT** position (strong/medium/weak/against)
- Your technical score and **independent** trading recommendation (unbiased by current position)""",

            "MacroEconomist": f"""Analyze the current macro-economic environment affecting {self.config.symbol}.

{position_hint}

{position_analysis_prompt}

**IMPORTANT**: Search for the latest market news and information. The system will automatically execute tool calls for you.

**Required Analysis Steps**:
1. Search for "Bitcoin BTC market news today price analysis"
2. Search for "cryptocurrency institutional investment outlook"

Based on search results, provide **objective analysis**:
- Current market liquidity conditions
- Institutional investor movements
- USD index correlation with cryptocurrency
- Macro support for **LONG** position (strong/medium/weak/against)
- Macro support for **SHORT** position (strong/medium/weak/against)
- Your macro score and **independent** directional judgment (unbiased by current position)

**Note**: Focus on market data and investment analysis. Avoid sensitive topics.""",

            "SentimentAnalyst": f"""Analyze the current market sentiment for {self.config.symbol}.

{position_hint}

{position_analysis_prompt}

**IMPORTANT**: Use your tools to fetch real-time sentiment data. The system will automatically execute tool calls for you.

**Required Analysis Steps**:
1. Get the Fear & Greed Index
2. Get the funding rate for {self.config.symbol}
3. Search for "Bitcoin BTC market sentiment social media"

Based on real data, provide **objective analysis**:
- Fear & Greed Index value and interpretation
- Funding rate and long/short ratio
- Social media and news sentiment
- Sentiment support for **LONG** position (strong/medium/weak/against)
- Sentiment support for **SHORT** position (strong/medium/weak/against)
- Your sentiment score and **independent** directional judgment (unbiased by current position)""",

            "QuantStrategist": f"""Analyze quantitative data and statistical signals for {self.config.symbol}.

{position_hint}

{position_analysis_prompt}

**IMPORTANT**: Use your tools to get real-time data for quantitative analysis. The system will automatically execute tool calls for you.

**Required Analysis Steps**:
1. Get the current market price for {self.config.symbol}
2. Fetch 1-hour candlestick data (200 candles)
3. Calculate technical indicators for 1-hour timeframe

Based on real data, provide **objective** quantitative analysis:
- Price volatility and volume analysis
- Multi-timeframe trend consistency
- Momentum and trend indicator signals
- Quantitative support for **LONG** position (strong/medium/weak/against)
- Quantitative support for **SHORT** position (strong/medium/weak/against)
- Your quantitative score and **independent** directional judgment (unbiased by current position)"""
        }

        # Default prompt also requires tool usage
        default_prompt = f"""Analyze the current market situation for {self.config.symbol}.

{position_hint}

**IMPORTANT**: Use tools to get real-time market data. The system will automatically execute tool calls.

Available tools include:
- Market price query
- Search for relevant news

Provide your analysis and views based on real data."""

        for agent_id in analysis_agents:
            agent = self._get_agent_by_id(agent_id)
            if agent:
                prompt = agent_prompts.get(agent_id, default_prompt)
                await self._run_agent_turn(agent, prompt)

    async def _run_signal_generation_phase(self, position_context: PositionContext):
        """
        Phase 2: Signal Generation

        Refactored: Use structured JSON output to avoid string matching errors
        """
        self._add_message(
            agent_id="system",
            agent_name="System",
            content="## Phase 2: Signal Generation\n\nExperts, please provide your trading recommendations (long/short/hold).",
            message_type="phase"
        )

        # Generate decision options based on position status
        decision_options = self._get_decision_options_for_analysts(position_context)

        # JSON structured output prompt
        vote_prompt = f"""Based on the above analysis and real-time data you've collected, please provide your trading recommendation.

{position_context.to_summary()}

{decision_options}

**Note**: If you did not use tools to fetch data in the previous phase, please use relevant tools NOW to get the latest information before making your judgment!

⚠️ **IMPORTANT - Do NOT call decision tools**:
- You are in the "Signal Generation Phase" - only provide **text recommendations**
- **Do NOT** call any decision tools (open_long/open_short/hold/close_position)
- Only the TradeExecutor can execute trades in Phase 5

---

## 📋 Output Requirements

First explain your analysis reasoning, then output a JSON trading signal at the **END** of your response.

**JSON must be valid format, placed in a ```json code block:**

```json
{{
  "direction": "long",
  "confidence": 75,
  "leverage": 6,
  "take_profit_percent": 5.0,
  "stop_loss_percent": 2.0,
  "reasoning": "Brief reasoning with specific data references"
}}
```

**direction field options**:
- `"long"`: Go long / Buy
- `"short"`: Go short / Sell
- `"hold"`: Wait / No action
- `"add_long"`: Add to long position (when already long)
- `"add_short"`: Add to short position (when already short)
- `"close"`: Close position
- `"reverse"`: Reverse (close and open opposite)

**confidence and leverage correlation rules**:
- confidence >= 80: leverage should be in range {int(self.config.max_leverage * 0.5)}-{self.config.max_leverage}
- confidence 60-79: leverage should be in range {int(self.config.max_leverage * 0.25)}-{int(self.config.max_leverage * 0.5)}
- confidence < 60: leverage should be in range 1-{int(self.config.max_leverage * 0.25)}, or choose hold

**Important**: JSON must be at the END of your response and properly formatted!
"""

        vote_agents = ["TechnicalAnalyst", "MacroEconomist", "SentimentAnalyst", "QuantStrategist"]
        for agent_id in vote_agents:
            agent = self._get_agent_by_id(agent_id)
            if agent:
                response = await self._run_agent_turn(agent, vote_prompt)
                vote = self._parse_vote_json(agent_id, agent.name, response)
                if vote:
                    self._agent_votes.append(vote)
                else:
                    # Fallback when JSON parsing fails
                    logger.warning(f"[{agent.name}] JSON parsing failed, attempting text parsing fallback")
                    vote = self._parse_vote_fallback(agent_id, agent.name, response)
                    if vote:
                        self._agent_votes.append(vote)

    async def _run_risk_assessment_phase(self, position_context: PositionContext):
        """Phase 3: Risk Assessment"""
        self._add_message(
            agent_id="system",
            agent_name="System",
            content="## Phase 3: Risk Assessment\n\nRisk Manager, please evaluate the trading risks.",
            message_type="phase"
        )

        # Summarize votes for risk manager
        votes_summary = self._summarize_votes()

        # Generate position risk assessment prompt
        risk_context = self._generate_risk_context(position_context)

        risk_agent = self._get_agent_by_id("RiskAssessor")
        if risk_agent:
            prompt = f"""Here are the expert voting results:

{votes_summary}

{position_context.to_summary()}

{risk_context}

Please evaluate the risk of this trade and decide whether to approve.
If approved, provide final position recommendations and TP/SL settings.
If not approved, explain your reasons.

⚠️ **IMPORTANT**:
- You only need to provide **text recommendations** for risk assessment
- **Do NOT** call any decision tools (open_long/open_short/hold/close_position)
- Only the TradeExecutor can execute trades in Phase 5
- Your responsibility is to assess risk, NOT to execute trades
"""
            await self._run_agent_turn(risk_agent, prompt)
    
    def _generate_risk_context(self, position_context: PositionContext) -> str:
        """
        Generate risk assessment context

        Help RiskAssessor evaluate current position risks
        """
        if not position_context.has_position:
            return """
## 🛡️ Risk Assessment Focus (No Position)

**Key Evaluation Points**:
1. Is the entry direction well-justified?
2. Does the leverage match the confidence level?
3. Are TP/SL settings reasonable?
4. Does the position size comply with risk management principles?
5. Is current market volatility suitable for opening a position?
"""

        # Has position
        direction = position_context.direction or "unknown"
        pnl = position_context.unrealized_pnl
        pnl_percent = position_context.unrealized_pnl_percent

        # Risk level
        if position_context.distance_to_liquidation_percent > 50:
            risk_level = "🟢 Safe"
        elif position_context.distance_to_liquidation_percent > 20:
            risk_level = "🟡 Warning"
        else:
            risk_level = "🔴 Danger"

        # TP/SL proximity warnings
        warnings = []
        if abs(position_context.distance_to_tp_percent) < 5:
            warnings.append(f"⚠️ Near Take Profit (only {abs(position_context.distance_to_tp_percent):.1f}%)")
        if abs(position_context.distance_to_sl_percent) < 5:
            warnings.append(f"🚨 Near Stop Loss (only {abs(position_context.distance_to_sl_percent):.1f}%)")

        warnings_text = "\n".join(warnings) if warnings else "No special warnings"

        return f"""
## 🛡️ Risk Assessment Focus (Has {direction.upper()} Position)

**Current Position Risk**:
- Risk Level: {risk_level}
- Distance to Liquidation: {position_context.distance_to_liquidation_percent:.1f}%
- Unrealized P&L: ${pnl:.2f} ({pnl_percent:+.2f}%)
- Position Ratio: {position_context.current_position_percent*100:.1f}%

**Risk Warnings**:
{warnings_text}

**Evaluation Points** (based on expert recommendation type):

### If experts recommend "Continue {direction}/Add"
1. What is the P&L status of the current {direction} position? Is it healthy?
2. Will the total position exceed risk limits after adding?
3. Is there over-concentration in a single direction?
4. Has the holding duration been too long (currently {position_context.holding_duration_hours:.1f} hours)?

### If experts recommend "Close Position"
1. Is the closing rationale sufficient?
2. Is current P&L status suitable for closing?
3. Is this the right time to take profit/stop loss?

### If experts recommend "Reverse"
1. Is the reversal signal strong enough?
2. Is the current position profitable? What are the closing costs?
3. What is the risk of the new reversed position?
4. Is it worth bearing double transaction costs?

### If experts recommend "Hold"
1. What is the risk of continuing to hold the current position?
2. Should we actively close rather than passively wait?

Please provide comprehensive risk assessment and recommendations!
"""

    async def _run_consensus_phase(self, position_context: PositionContext) -> Optional[TradingSignal]:
        """
        Phase 4: Consensus Building - Leader Meeting Summary

        NEW ARCHITECTURE:
        - Leader only summarizes meeting discussions and expert opinions
        - No longer outputs structured trading decisions
        - Decisions made by TradeExecutor in Phase 5
        """
        self._add_message(
            agent_id="system",
            agent_name="System",
            content="## Phase 4: Consensus Building\n\nModerator, please summarize expert opinions and provide meeting conclusions.",
            message_type="phase"
        )

        # Use Leader for meeting summary
        leader = self._get_agent_by_id("Leader")
        if not leader:
            logger.error("Leader not found")
            return None

        # Generate position-aware decision guidance
        decision_guidance = self._generate_decision_guidance(position_context)

        # Leader as meeting moderator summary prompt
        prompt = f"""As the roundtable moderator, please comprehensively summarize the meeting discussions and expert opinions.

{position_context.to_summary()}

{decision_guidance}

## Expert Opinion Summary
You have heard analysis from the following experts:
- Technical Analyst (TechnicalAnalyst): Candlestick patterns, technical indicators analysis
- Macro Economist (MacroEconomist): Macro economy, monetary policy analysis
- Sentiment Analyst (SentimentAnalyst): Market sentiment, capital flow analysis
- Quant Strategist (QuantStrategist): Quantitative indicators, statistical analysis
- Risk Assessor (RiskAssessor): Risk assessment and recommendations

## Your Task

As moderator, please:

1. **Summarize Expert Consensus**:
   - How many experts are bullish? Bearish? Neutral?
   - What are the core reasons for each expert's opinion?
   - What are the agreements and disagreements among experts?

2. **Comprehensive Market Judgment**:
   - Based on all discussions, your overall view of the current market
   - Comprehensive evaluation of technical, fundamental, and sentiment aspects
   - Factors to consider given the current position status

3. **Risk and Opportunity Assessment**:
   - What are the main risks currently?
   - Where are the potential trading opportunities?
   - Recommendations for current position (if any)

4. **Provide Meeting Conclusions**:
   - Based on all analysis, what strategy should be adopted?
   - Recommended risk level and position size
   - How confident are you?

## 📋 Output Format

Please express your summary and recommendations freely, **no strict format required**.

You can express naturally, for example:

"Based on all expert opinions, I believe...
- TechnicalAnalyst and SentimentAnalyst are bullish because...
- However, MacroEconomist advises caution due to...
- Considering the current {('no position' if not position_context.has_position else f'{position_context.direction} position')} status...
I recommend... strategy because...
Suggested leverage is..., position size is..., my confidence is approximately...%"

⚠️ **Important Reminders**:
- ✅ Express your summary and recommendations in natural language
- ✅ Include expert opinions, your judgment, recommended strategy
- ✅ No need for markers like "【Final Decision】"
- ✅ Your summary will be passed to the Trade Executor, who will make the final decision based on your recommendations

Please begin your summary!
"""

        response = await self._run_agent_turn(leader, prompt)

        # Log meeting summary for monitoring
        vote_summary = self._get_vote_summary()
        logger.info(f"[Meeting Summary] Votes: {len(self._agent_votes)} collected, "
                   f"Vote breakdown: {vote_summary}")
        logger.info(f"[Leader Summary] {response[:200]}...")

        # NEW: No longer extract signal here
        # Phase 5 TradeExecutor will make decision based on this summary
        # Return a temporary signal here just to maintain interface compatibility
        return TradingSignal(
            direction="hold",  # FIX: Use valid value instead of "pending"
            symbol=self.config.symbol,
            leverage=1,
            amount_percent=0.0,
            entry_price=0.0,
            take_profit_price=0.0,
            stop_loss_price=0.0,
            confidence=0,
            reasoning=response[:500],
            agents_consensus=self._get_agents_consensus(),  # FIX: Use method instead of property
            timestamp=datetime.now()
        )
    
    def _generate_decision_guidance(self, position_context: PositionContext) -> str:
        """
        Generate decision guidance based on position status

        FIX: Use neutral decision guidance to avoid holding bias
        - Don't put "hold" as first option
        - Decision matrix treats all options equally
        - Emphasize decisions based on expert opinions, not position bias
        """
        if not position_context.has_position:
            # No position
            return """
## 💡 Decision Guidance (No Position)

**Decision Principle**: Based entirely on expert voting consensus, no preset directional bias.

**Decision Logic**:

| Expert Consensus | Recommended Action | Reason |
|-----------------|-------------------|--------|
| Majority bullish (≥3 votes) | Go Long | Upward market trend, expert consensus formed |
| Majority bearish (≥3 votes) | Go Short | Downward market trend, expert consensus formed |
| Split opinions | Hold | Direction unclear, wait for clearer signals |
| Unanimous hold | Hold | Timing not right |

**Auto-calculated Parameters**:
- Leverage/position determined by voting consensus strength (stronger consensus = higher leverage)
- TP/SL automatically adjusted based on leverage
"""

        # Has position
        direction = position_context.direction or "unknown"
        opposite = "short" if direction == "long" else "long"
        pnl = position_context.unrealized_pnl
        pnl_percent = position_context.unrealized_pnl_percent
        can_add = position_context.can_add_position

        # P&L status
        pnl_status = "profit" if pnl >= 0 else "loss"
        pnl_emoji = "📈" if pnl >= 0 else "📉"

        # Check if near TP/SL
        near_tp = abs(position_context.distance_to_tp_percent) < 5
        near_sl = abs(position_context.distance_to_sl_percent) < 5

        guidance = f"""
## 💡 Decision Guidance (Has {direction.upper()} Position)

**Current Position Status**: {pnl_emoji} {pnl_status} ${abs(pnl):.2f} ({pnl_percent:+.2f}%)
"""

        if near_tp:
            guidance += f"""
⚠️ **Near Take Profit**: Only {abs(position_context.distance_to_tp_percent):.1f}% from TP price
"""

        if near_sl:
            guidance += f"""
🚨 **Near Stop Loss**: Only {abs(position_context.distance_to_sl_percent):.1f}% from SL price
"""

        guidance += f"""
**Decision Principle**: Decide based on expert voting consensus, **do NOT favor any option due to existing position**.

**Decision Logic** (based on expert consensus, regardless of position P&L):

| Expert Consensus | Relation to Current {direction} | Recommended Action | Reason |
|-----------------|-------------------------------|-------------------|--------|
| Majority {opposite} | 🔴 Opposite | **Close or Reverse** | Experts see reversal, respect market signals |
| Majority {direction} | 🟢 Same | Maintain{' or Add' if can_add else ' (Max position)'} | Experts see same direction, trend may continue |
| Split opinions | ⚪ Unclear | Consider closing or hold | Direction unclear, reduce risk exposure |
| Unanimous hold | ⚪ Neutral | Hold but set tighter stop loss | Market may reverse |

⚠️ **Special Reminders**:
- If expert consensus is opposite to current {direction} position, **MUST consider closing or reversing**
- Do not avoid making changes just because currently in {pnl_status}
- Holding duration of {position_context.holding_duration_hours:.1f} hours should NOT become "sunk cost" affecting decisions

**Prohibited Behaviors**:
- ❌ Do not force-find reasons to hold just because already in {direction} position
- ❌ Do not ignore majority expert's reversal recommendations
"""

        return guidance

    def _get_neutral_position_analysis_prompt(self, position_context: PositionContext) -> str:
        """
        Generate neutral position analysis prompt

        Avoid confirmation bias: Don't ask "whether to support current position", but require objective market analysis
        """
        if not position_context.has_position:
            return """
⚠️ **Analysis Requirements**: Please provide objective analysis based on market data, without preset positions.
- Evaluate both long and short reasons simultaneously
- If market direction is unclear, honestly express uncertainty
- Your analysis should be independent of any preset preferences
"""

        direction = position_context.direction or "unknown"
        opposite = "short" if direction == "long" else "long"
        pnl_status = "profit" if position_context.unrealized_pnl >= 0 else "loss"

        return f"""
⚠️ **Objective Analysis Requirements** (Avoid Confirmation Bias):

Currently has {direction.upper()} position (in {pnl_status}), but please **do NOT** favor any direction because of this.

**Your analysis MUST answer these questions**:
1. Objectively, is the market trend **bullish**, **bearish**, or **ranging**?
2. If you had **NO position** right now, would you recommend long, short, or hold?
3. Does the current market condition contradict the existing {direction} position? If so, honestly point it out.
4. What signals support **reversing** (close {direction} and open {opposite})?

**Prohibited**:
- ❌ Do not lean towards {direction} just because already in {direction} position
- ❌ Do not avoid recommending close or reverse
- ❌ Do not use "can continue holding" to avoid giving clear judgment

**Encouraged**:
- ✅ If you see reversal signals, say it directly
- ✅ If market direction contradicts position, clearly recommend close/reverse
- ✅ Give clear directional judgment, don't be ambiguous
"""

    def _get_decision_options_for_analysts(self, position_context: PositionContext) -> str:
        """
        Generate decision options prompt for analysts

        FIX: Use neutral option list to avoid anchoring effect
        - Don't put "hold" as first option
        - Present all options equally
        - Emphasize decisions based on market analysis, not position status
        """
        if not position_context.has_position:
            return """
## 💡 Decision Options (No Position)

Based on **your professional analysis**, choose recommended direction (no preset preferences):

| Option | Applicable Situation |
|--------|---------------------|
| **Long** | Clear upward market trend with sufficient bullish signals |
| **Short** | Clear downward market trend with sufficient bearish signals |
| **Hold** | Market direction unclear, or risk/reward ratio unfavorable |

⚠️ **Make independent judgment**, do not change your analysis conclusion due to other experts' opinions.
"""

        # Has position
        direction = position_context.direction or "unknown"
        opposite = "short" if direction == "long" else "long"
        can_add_text = "Can add" if position_context.can_add_position else "Max position"

        return f"""
## 💡 Decision Options (Has {direction.upper()} Position)

Based on **your professional analysis**, choose recommended action (**do NOT favor any option due to existing position**):

| Option | Applicable Situation | Current Status |
|--------|---------------------|----------------|
| **Close** | Market shows reversal signals, or reached TP/SL | Execute immediately |
| **Reverse** | Clear market reversal, should close {direction} and open {opposite} | Execute immediately |
| **Maintain** | Market trend continues, keep current position | No action |
| **Add** | Market trend strengthens, can increase position | {can_add_text} |

**Current Position Status** (for reference only, should NOT affect your independent judgment):
- Direction: {direction.upper()} | P&L: ${position_context.unrealized_pnl:.2f} ({position_context.unrealized_pnl_percent:+.2f}%)
- Position: {position_context.current_position_percent*100:.1f}% | Duration: {position_context.holding_duration_hours:.1f} hours

⚠️ **Important**: If market analysis contradicts current position direction, **prioritize recommending close or reverse**, do not avoid giving reversal recommendations due to existing position!
"""

    def _get_vote_summary(self) -> str:
        """Get vote summary for logging"""
        if not self._agent_votes:
            return "no votes"
        directions = [v.direction for v in self._agent_votes]
        long_count = directions.count("long")
        short_count = directions.count("short")
        hold_count = directions.count("hold")
        return f"{long_count}L/{short_count}S/{hold_count}H"
    
    def _get_agents_consensus(self) -> Dict[str, str]:
        """
        Build agents_consensus dict from _agent_votes

        Returns:
            Dict[str, str]: {agent_name: direction}
        """
        consensus = {}
        for vote in self._agent_votes:
            consensus[vote.agent_name] = vote.direction
        return consensus

    async def _extract_signal_from_executed_tools(self, response: str) -> Optional[TradingSignal]:
        """
        Extract trading signal ONLY from actually executed tool calls.
        This prevents the bug where text mentions of 'open_long' would be mistaken for actual decisions.
        """
        try:

            # Check if any decision tools were actually executed
            decision_tools = ['open_long', 'open_short', 'hold']
            executed_decision = None
            executed_params = {}

            for tool_exec in self._last_executed_tools:
                tool_name = tool_exec.get('tool_name', '')
                if tool_name in decision_tools:
                    executed_decision = tool_name
                    executed_params = tool_exec.get('params', {})
                    logger.info(f"Found executed decision tool: {tool_name} with params: {executed_params}")
                    break

            # If no decision tool was executed, return None (no signal)
            if not executed_decision:
                logger.warning("No decision tool (open_long/open_short/hold) was executed by Leader")
                # Return a hold signal by default when no tool is called
                return await self._create_hold_signal(response, "Leader did not call any decision tool")

            # Map tool name to direction
            if executed_decision == 'open_long':
                direction = 'long'
            elif executed_decision == 'open_short':
                direction = 'short'
            else:  # 'hold'
                direction = 'hold'

            logger.info(f"Extracted direction from executed tool: {direction}")

            # Extract parameters from executed tool call
            leverage = 1
            amount_percent = self.config.default_position_percent
            tp_percent = self.config.default_tp_percent
            sl_percent = self.config.default_sl_percent
            confidence = self.config.min_confidence

            # Parse leverage from params
            if 'leverage' in executed_params:
                try:
                    leverage = min(int(executed_params['leverage']), self.config.max_leverage)
                except (ValueError, TypeError):
                    pass

            # Parse amount from params
            if 'amount_usdt' in executed_params:
                try:
                    amount_usdt = float(executed_params['amount_usdt'])
                    # Clamp amount_percent between min and max
                    raw_percent = amount_usdt / self.config.default_balance
                    amount_percent = max(self.config.min_position_percent, min(raw_percent, self.config.max_position_percent))
                    logger.info(f"Position percent: {raw_percent*100:.1f}% -> clamped to {amount_percent*100:.1f}% (min={self.config.min_position_percent*100:.0f}%, max={self.config.max_position_percent*100:.0f}%)")
                except (ValueError, TypeError):
                    pass

            # Get current price for TP/SL calculation (now using await since method is async)
            try:
                current_price = await get_current_btc_price()
                logger.info(f"Got real-time BTC price: ${current_price:,.2f}")
            except Exception as e:
                logger.warning(f"Failed to get real-time price: {e}, using fallback")
                current_price = self.config.fallback_price

            if direction == "long":
                tp_price = current_price * (1 + tp_percent / 100)
                sl_price = current_price * (1 - sl_percent / 100)
            elif direction == "short":
                tp_price = current_price * (1 - tp_percent / 100)
                sl_price = current_price * (1 + sl_percent / 100)
            else:  # hold
                tp_price = current_price
                sl_price = current_price
                amount_percent = 0  # Hold means no position, so amount_percent must be 0

            consensus = {v.agent_name: v.direction for v in self._agent_votes}

            return TradingSignal(
                direction=direction,
                symbol=self.config.symbol,
                leverage=leverage,
                amount_percent=amount_percent,
                entry_price=current_price,
                take_profit_price=tp_price,
                stop_loss_price=sl_price,
                confidence=confidence,
                reasoning=response[:500],
                agents_consensus=consensus
            )
        except Exception as e:
            logger.error(f"Error extracting signal from executed tools: {e}")
            return None

    async def _create_hold_signal(self, response: str, reason: str) -> TradingSignal:
        """Create a hold signal when Leader doesn't call any decision tool"""
        try:
            current_price = await get_current_btc_price()
            logger.info(f"Got real-time BTC price for hold signal: ${current_price:,.2f}")
        except Exception as e:
            logger.warning(f"Failed to get real-time price for hold signal: {e}, using fallback")
            current_price = self.config.fallback_price

        consensus = {v.agent_name: v.direction for v in self._agent_votes}

        return TradingSignal(
            direction="hold",
            symbol=self.config.symbol,
            leverage=1,
            amount_percent=0,
            entry_price=current_price,
            take_profit_price=current_price,
            stop_loss_price=current_price,
            confidence=0,
            reasoning=f"{reason}. Response: {response[:300]}",
            agents_consensus=consensus
        )

    async def _extract_signal_from_text(self, response: str) -> Optional[TradingSignal]:
        """
        NEW: Extract trading signal from Leader's structured text output.

        Leader no longer calls tools, but outputs a structured decision in text format:

        【Final Decision】
        - Decision: long/short/hold/close/add_long/add_short
        - Symbol: BTC-USDT-SWAP
        - Leverage: 5
        - Position Percent: 30%
        - Take Profit Price: 98000 USDT
        - Stop Loss Price: 92000 USDT
        - Confidence: 75%
        - Reasoning: ...
        """
        try:
            import re

            logger.info("[SignalExtraction] Extracting signal from Leader's text output")

            # CRITICAL FIX: MUST have Final Decision marker
            # Without this marker, Leader is just discussing, not making final decision
            # Support English markers for Final Decision
            decision_patterns = [
                r'【Final Decision】(.*?)(?=\n\n|$)',      # English with Chinese brackets
                r'\[Final Decision\](.*?)(?=\n\n|$)',     # English with square brackets
                r'\*\*Final Decision\*\*(.*?)(?=\n\n|$)', # Markdown bold
            ]

            match = None
            for pattern in decision_patterns:
                match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
                if match:
                    break

            if not match:
                logger.warning("[SignalExtraction] ⚠️ No Final Decision section found in response")
                logger.warning("[SignalExtraction] This indicates Leader is discussing, not making final decision")
                logger.warning("[SignalExtraction] Returning hold signal to avoid premature execution")
                # FIX: Do NOT fallback to parsing the entire response
                # If there's no Final Decision marker, it means Leader is just discussing
                # Return a hold signal to prevent premature execution
                return await self._create_hold_signal(
                    response,
                    "Leader did not output Final Decision marker, may still be discussing"
                )

            decision_text = match.group(1)
            logger.info(f"[SignalExtraction] ✅ Found Final Decision section")
            logger.info(f"[SignalExtraction] Decision text: {decision_text[:200]}...")

            # Extract fields using regex - try multiple patterns (English first, Chinese fallback)
            def extract_field_multi(patterns, text, default=None):
                """Try multiple patterns and return first match"""
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
                return default

            # Decision type
            decision_type = extract_field_multi([
                r'-\s*Decision\s*[::：]\s*([^\n]+)',      # English
            ], decision_text)
            logger.info(f"[SignalExtraction] decision_type: {decision_type}")

            # Symbol
            symbol = extract_field_multi([
                r'-\s*Symbol\s*[::：]\s*([^\n]+)',        # English
            ], decision_text, self.config.symbol)

            # Leverage
            leverage_str = extract_field_multi([
                r'-\s*Leverage\s*[::：]\s*(\d+)',         # English
            ], decision_text, "1")
            leverage = int(leverage_str)

            # Position percent
            position_str = extract_field_multi([
                r'-\s*Position\s*(?:Percent|Size|%)\s*[::：]\s*(\d+)',  # English
            ], decision_text, "0")
            amount_percent = float(position_str)

            # Take profit price
            tp_str = extract_field_multi([
                r'-\s*Take\s*Profit\s*(?:Price)?\s*[::：]\s*([\d.]+)',  # English
            ], decision_text, "0")
            take_profit_price = float(tp_str)

            # Stop loss price
            sl_str = extract_field_multi([
                r'-\s*Stop\s*Loss\s*(?:Price)?\s*[::：]\s*([\d.]+)',    # English
            ], decision_text, "0")
            stop_loss_price = float(sl_str)

            # Confidence
            confidence_str = extract_field_multi([
                r'-\s*Confidence\s*[::：]\s*(\d+)',       # English
            ], decision_text, "0")
            confidence = int(confidence_str)

            # Reasoning
            reasoning = extract_field_multi([
                r'-\s*Reasoning\s*[::：]\s*([^\n]+)',     # English
            ], decision_text, "")

            # Map decision_type to direction
            direction = "hold"  # default
            if decision_type:
                dt_lower = decision_type.lower()
                # English keywords only
                if "long" in dt_lower or "buy" in dt_lower or "bullish" in dt_lower:
                    direction = "long"
                elif "short" in dt_lower or "sell" in dt_lower or "bearish" in dt_lower:
                    direction = "short"
                elif "add_long" in dt_lower or "add long" in dt_lower:
                    direction = "long"  # Add to long position
                elif "add_short" in dt_lower or "add short" in dt_lower:
                    direction = "short"  # Add to short position
                elif "close" in dt_lower:
                    direction = "hold"  # FIX: TradingSignal doesn't support "close", use hold after closing
                elif "hold" in dt_lower or "wait" in dt_lower:
                    direction = "hold"
            
            logger.info(f"[SignalExtraction] Parsed direction: {direction}, leverage: {leverage}, "
                       f"position: {amount_percent}%, confidence: {confidence}%")
            
            # FIX: Convert amount_percent from percentage to decimal (e.g., 90% → 0.9)
            # TradingSignal expects amount_percent in range [0, 1], not [0, 100]
            amount_percent_decimal = amount_percent / 100.0
            logger.info(f"[SignalExtraction] Converted amount_percent: {amount_percent}% → {amount_percent_decimal}")
            
            # Get current price
            try:
                from app.core.trading.trading_tools import get_current_btc_price
                current_price = await get_current_btc_price()
                logger.info(f"[SignalExtraction] Current BTC price: ${current_price:,.2f}")
            except Exception as e:
                logger.warning(f"[SignalExtraction] Failed to get real-time price: {e}, using fallback")
                current_price = self.config.fallback_price
            
            # Build consensus dict
            consensus = {v.agent_name: v.direction for v in self._agent_votes}
            
            # Create signal
            signal = TradingSignal(
                direction=direction,
                symbol=symbol,
                leverage=leverage,
                amount_percent=amount_percent_decimal,  # Use decimal value
                entry_price=current_price,
                take_profit_price=take_profit_price,
                stop_loss_price=stop_loss_price,
                confidence=confidence,
                reasoning=reasoning or response[:500],
                agents_consensus=consensus
            )
            
            logger.info(f"[SignalExtraction] ✅ Signal extracted: {signal}")
            return signal
            
        except Exception as e:
            logger.error(f"[SignalExtraction] Error extracting signal from text: {e}", exc_info=True)
            return None

    async def _get_position_context(self) -> PositionContext:
        """
        Get complete position context

        Collect all position, account, and risk related information for:
        1. Injecting into Agents' prompts
        2. Passing to Leader for decision making
        3. Passing to TradeExecutor for execution

        Returns:
            PositionContext: Complete position context object
        """
        try:
            # Check if toolkit and paper_trader exist
            if not hasattr(self, 'toolkit') or not self.toolkit:
                logger.error("[PositionContext] No toolkit available")
                raise AttributeError("toolkit not available")

            if not hasattr(self.toolkit, 'paper_trader') or not self.toolkit.paper_trader:
                logger.error("[PositionContext] No paper_trader in toolkit")
                raise AttributeError("paper_trader not available")

            # Get current position
            position = await self.toolkit.paper_trader.get_position()
            if position is None:
                logger.warning("[PositionContext] get_position() returned None, using default empty position")
                position = {'has_position': False}

            has_position = position.get('has_position', False)

            # Get account info
            account = await self.toolkit.paper_trader.get_account()
            if account is None:
                logger.warning("[PositionContext] get_account() returned None, using default balance")
                account = {
                    'available_balance': self.config.default_balance,
                    'total_equity': self.config.default_balance,
                    'used_margin': 0
                }

            # If no position, return simplified context
            if not has_position:
                return PositionContext(
                    has_position=False,
                    available_balance=account.get('available_balance', self.config.default_balance),
                    total_equity=account.get('total_equity', self.config.default_balance),
                    used_margin=account.get('used_margin', 0),
                    max_position_percent=self.config.max_position_percent,
                    can_add_position=False
                )

            # Has position, collect detailed info
            # FIX: get_position() returns flat dict, not nested under 'position' key
            # Get data directly from position dict, not position.get('position', {})
            current_position = position  # position itself is the position details

            direction = position.get('direction', '')
            entry_price = position.get('entry_price', 0)
            current_price = position.get('current_price', 0)
            size = position.get('size', 0)
            leverage = position.get('leverage', 1)
            margin_used = position.get('margin', 0)
            unrealized_pnl = position.get('unrealized_pnl', 0)
            unrealized_pnl_percent = position.get('unrealized_pnl_percent', 0)
            liquidation_price = position.get('liquidation_price', 0)
            take_profit_price = position.get('take_profit_price')
            stop_loss_price = position.get('stop_loss_price')
            opened_at_str = position.get('opened_at')

            # Calculate distance to TP/SL
            distance_to_tp_percent = 0.0
            distance_to_sl_percent = 0.0
            if take_profit_price and current_price:
                distance_to_tp_percent = ((take_profit_price - current_price) / current_price) * 100
            if stop_loss_price and current_price:
                distance_to_sl_percent = ((stop_loss_price - current_price) / current_price) * 100

            # Calculate distance to liquidation
            distance_to_liquidation_percent = 0.0
            if liquidation_price and current_price:
                if direction == "long":
                    distance_to_liquidation_percent = ((current_price - liquidation_price) / current_price) * 100
                else:  # short
                    distance_to_liquidation_percent = ((liquidation_price - current_price) / current_price) * 100

            # Calculate current position percent
            total_equity = account.get('total_equity', self.config.default_balance)
            current_position_percent = margin_used / total_equity if total_equity > 0 else 0

            # Calculate if can add position
            max_margin = total_equity * self.config.max_position_percent
            available_balance = account.get('available_balance', 0)
            can_add_position = (margin_used < max_margin) and (available_balance >= 10)
            max_additional_amount = min(max_margin - margin_used, available_balance) if can_add_position else 0
            
            # Calculate holding duration
            opened_at = None
            holding_duration_hours = 0.0
            if opened_at_str:
                try:
                    opened_at = datetime.fromisoformat(opened_at_str.replace('Z', '+00:00'))
                    holding_duration_hours = (datetime.now(opened_at.tzinfo) - opened_at).total_seconds() / 3600
                except Exception as e:
                    logger.warning(f"Failed to parse opened_at: {e}")

            # Return complete position context
            return PositionContext(
                has_position=True,
                current_position=current_position,
                direction=direction,
                entry_price=entry_price,
                current_price=current_price,
                size=size,
                leverage=leverage,
                margin_used=margin_used,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                liquidation_price=liquidation_price,
                distance_to_liquidation_percent=distance_to_liquidation_percent,
                take_profit_price=take_profit_price,
                stop_loss_price=stop_loss_price,
                distance_to_tp_percent=distance_to_tp_percent,
                distance_to_sl_percent=distance_to_sl_percent,
                available_balance=account.get('available_balance', 0),
                total_equity=total_equity,
                used_margin=account.get('used_margin', 0),
                max_position_percent=self.config.max_position_percent,
                current_position_percent=current_position_percent,
                can_add_position=can_add_position,
                max_additional_amount=max_additional_amount,
                opened_at=opened_at,
                holding_duration_hours=holding_duration_hours
            )
        
        except Exception as e:
            logger.error(f"[PositionContext] Error getting position context: {e}", exc_info=True)
            # Return default empty position context
            return PositionContext(
                has_position=False,
                available_balance=self.config.default_balance,
                total_equity=self.config.default_balance,
                used_margin=0,
                max_position_percent=self.config.max_position_percent,
                can_add_position=False
            )
    
    async def _get_position_info_dict(self) -> Dict[str, Any]:
        """
        🔧 NEW: Get position info as a dict for TradeExecutor.
        
        Returns:
            {
                "has_position": bool,
                "current_position": {...} or None,
                "account": {...},
                "can_add": bool,
                ...
            }
        """
        try:
            # Get paper_trader from toolkit
            paper_trader = None
            if hasattr(self, 'toolkit') and hasattr(self.toolkit, 'paper_trader'):
                paper_trader = self.toolkit.paper_trader
            
            if not paper_trader:
                logger.warning("[PositionInfo] No paper_trader available")
                return {
                    "has_position": False,
                    "current_position": None,
                    "account": {},
                    "can_add": False
                }
            
            # Get account and position (using correct async methods)
            # FIX: get_account and get_position are async methods, need await
            account = await paper_trader.get_account()
            position = await paper_trader.get_position()

            has_position = position is not None and position.get("has_position", False)

            # Calculate if can add more position
            can_add = False
            if has_position:
                # FIX: position_value doesn't exist in get_position() return value
                # Use margin × leverage to calculate position value
                margin = position.get('margin', 0)
                leverage = position.get('leverage', 1)
                current_value = margin * leverage
                max_value = account.get('balance', 0) * (self.config.max_position_percent or 1.0)
                can_add = current_value < max_value * 0.9  # Leave 10% buffer
            
            return {
                "has_position": has_position,
                "current_position": position,
                "account": account,
                "can_add": can_add,
                "max_leverage": self.config.max_leverage,
                "max_position_percent": self.config.max_position_percent
            }
            
        except Exception as e:
            logger.error(f"[PositionInfo] Error getting position info: {e}")
            return {
                "has_position": False,
                "current_position": None,
                "account": {},
                "can_add": False
            }

    async def _run_execution_phase(self, signal: TradingSignal, position_context: PositionContext = None):
        """
        Phase 5: Trade Execution - NEW Intelligent TradeExecutor

        TradeExecutor is now a true decision-making Agent that:
        1. Understands Leader's meeting summary
        2. Analyzes all expert votes
        3. Considers current position state
        4. Makes independent trading decisions
        5. Executes trades

        No longer relies on fixed formats or markers!
        """
        self._add_message(
            agent_id="system",
            agent_name="System",
            content=f"## Phase 5: Trade Execution\n\nTrade Executor is analyzing meeting results and making decisions...",
            message_type="phase"
        )
        
        try:
            # Step 1: Get Leader's meeting summary
            leader_summary = self._get_leader_final_summary()
            logger.info(f"[ExecutionPhase] Leader summary length: {len(leader_summary)} chars")

            # Step 2: Collect expert votes
            agents_votes = self._get_agents_consensus()
            logger.info(f"[ExecutionPhase] Expert votes: {agents_votes}")

            # Step 3: Create TradeExecutor Agent (with direct tool calling capability)
            logger.info("[ExecutionPhase] Creating TradeExecutor Agent...")
            trade_executor_agent = await self._create_trade_executor_agent_instance()

            # Step 4: Build execution prompt
            execution_prompt = self._build_execution_prompt(
                leader_summary=leader_summary,
                agents_votes=agents_votes,
                position_context=position_context
            )
            logger.info(f"[ExecutionPhase] Execution prompt built, length: {len(execution_prompt)} chars")

            # Step 5: TradeExecutor executes trade via Tool Calling
            # KEY CHANGE: run() returns TradingSignal directly, no secondary parsing needed!
            logger.info("[ExecutionPhase] TradeExecutor starting Tool Calling...")
            final_signal = await trade_executor_agent.run(execution_prompt)

            logger.info(
                f"[ExecutionPhase] TradeExecutor decision complete: {final_signal.direction.upper()} "
                f"| Leverage {final_signal.leverage}x "
                f"| Position {final_signal.amount_percent*100:.0f}%"
            )

            # Step 6: Add decision message
            # FIX: _add_message doesn't support metadata parameter, removed
            self._add_message(
                agent_id="trade_executor",
                agent_name="Trade Executor",
                content=f"""## TradeExecutor Final Decision

**Decision**: {final_signal.direction.upper()}
**Leverage**: {final_signal.leverage}x
**Position**: {final_signal.amount_percent*100:.0f}%
**Confidence**: {final_signal.confidence}%

**Take Profit**: ${final_signal.take_profit_price:,.2f}
**Stop Loss**: ${final_signal.stop_loss_price:,.2f}

**Reasoning**:
{final_signal.reasoning}
""",
                message_type="decision"
            )
            
            # Step 7: Record execution result (tool functions already executed trade, no need to execute again!)
            # KEY CHANGE: TradeExecutorAgentWithTools tool functions already executed the trade directly
            # open_long/open_short/close_position functions internally called paper_trader.open_position()
            # So here we only need to record the result, no need to call LegacyExecutor

            if final_signal.direction != "hold":
                logger.info(f"[ExecutionPhase] Trade executed via Tool Calling: {final_signal.direction.upper()}")

                self._add_message(
                    agent_id="trade_executor",
                    agent_name="Trade Executor",
                    content=f"Trade Executed\n\nDecision: {final_signal.direction.upper()}\nLeverage: {final_signal.leverage}x\nPosition: {final_signal.amount_percent*100:.0f}%",
                    message_type="execution"
                )

                self._execution_result = {
                    "status": "success",
                    "action": final_signal.direction,
                    "reason": final_signal.reasoning,
                    "details": {
                        "leverage": final_signal.leverage,
                        "amount_percent": final_signal.amount_percent,
                        "entry_price": final_signal.entry_price,
                        "take_profit": final_signal.take_profit_price,
                        "stop_loss": final_signal.stop_loss_price
                    }
                }

                # Record Agent predictions (for post-close reflection)
                await self._record_agent_predictions_for_trade(final_signal.entry_price)

            else:
                logger.info("[ExecutionPhase] 📊 Decision is hold, no trade executed")
                self._execution_result = {
                    "status": "hold",
                    "action": "hold",
                    "reason": final_signal.reasoning
                }
            
            # Store final signal
            self._final_signal = final_signal
            
        except Exception as e:
            logger.error(f"[ExecutionPhase] ❌ Execution phase failed: {e}", exc_info=True)
            self._add_message(
                agent_id="system",
                agent_name="System",
                content=f"❌ Trade execution phase failed: {str(e)}",
                message_type="error"
            )
            # Return hold signal
            self._final_signal = await self._create_hold_signal(
                "",
                f"Execution phase failed: {str(e)}"
            )
    
    async def _create_trade_executor_agent_instance(self):
        """
        Create TradeExecutor Agent instance

        Refactored: Uses existing Agent class and FunctionTool mechanism
        - Agent class already has full Tool Calling support (native + legacy)
        - Uses FunctionTool to wrap trading functions
        - No longer needs hardcoded regex detection

        Architecture:
        Leader summary -> TradeExecutor Agent -> Agent.call_llm() with tools -> Native Tool Calling -> Execute
        """
        from app.core.roundtable.tool import FunctionTool

        # Get Leader's LLM config
        leader = self._get_agent_by_id("Leader")
        if not leader:
            raise RuntimeError("Leader agent not found, cannot create TradeExecutor")
        
        # Refactored: Use existing Agent class + FunctionTool, leverage Agent's native Tool Calling capability
        # No longer uses hardcoded regex detection!

        # Save toolkit reference for use in tool functions
        toolkit = self.toolkit

        # Create trading tool functions (these will be wrapped as FunctionTool)
        # Each tool executes trade and returns result string, also saves TradingSignal to external variable

        # Container to save execution result
        execution_result = {"signal": None}

        async def get_current_price() -> float:
            """Get current BTC price"""
            try:
                if toolkit and hasattr(toolkit, '_get_market_price'):
                    result = await toolkit._get_market_price()
                    if isinstance(result, str):
                        # FIX: Prefer parsing JSON to get price field
                        try:
                            import json as json_module
                            data = json_module.loads(result)
                            if isinstance(data, dict) and 'price' in data:
                                return float(data['price'])
                        except (json_module.JSONDecodeError, ValueError, KeyError):
                            pass

                        # FIX: Improved regex - match price format starting with number
                        # First try to match $XX,XXX.XX format
                        price_match = re.search(r'\$(\d[\d,]*\.?\d*)', result)
                        if price_match:
                            return float(price_match.group(1).replace(',', ''))
                        # Then try to match pure number (e.g., 93000.0)
                        price_match = re.search(r'(\d[\d,]*\.?\d*)', result)
                        if price_match:
                            price_str = price_match.group(1).replace(',', '')
                            if price_str and price_str != '.':
                                return float(price_str)
                    elif isinstance(result, (int, float)):
                        return float(result)

                if toolkit and hasattr(toolkit, 'paper_trader'):
                    # FIX: PaperTrader uses _current_price attribute (private)
                    if hasattr(toolkit.paper_trader, '_current_price') and toolkit.paper_trader._current_price:
                        return float(toolkit.paper_trader._current_price)
            except Exception as e:
                logger.error(f"[TradeExecutor] Failed to get price: {e}")
            return 93000.0  # fallback

        # Minimum add amount (USD)
        MIN_ADD_AMOUNT = 10.0
        # Safety buffer (reserve some balance to prevent accidents)
        SAFETY_BUFFER = 50.0

        def calculate_safe_stop_loss(direction: str, entry_price: float, leverage: int, margin: float) -> float:
            """
            Calculate safe stop loss price (ensure trigger before liquidation)

            Liquidation condition: Loss reaches 80% of margin
            Safe stop loss: Add 5% safety buffer on top of liquidation price
            """
            # FIX: Prevent division by zero
            if entry_price <= 0 or margin <= 0 or leverage <= 0:
                # Return default stop loss (3%)
                if direction == "long":
                    return entry_price * 0.97 if entry_price > 0 else 0
                else:
                    return entry_price * 1.03 if entry_price > 0 else float('inf')

            size = (margin * leverage) / entry_price
            liquidation_loss = margin * 0.8  # 80% margin loss triggers liquidation

            if direction == "long":
                # Long: liquidation price = entry price - (liquidation loss / position size)
                liquidation_price = entry_price - (liquidation_loss / size) if size > 0 else 0
                # Safe stop loss = liquidation price × 1.05 (5% above liquidation)
                safe_sl = liquidation_price * 1.05
                # But cannot exceed default stop loss (3%)
                default_sl = entry_price * 0.97
                return max(safe_sl, default_sl)
            else:
                # Short: liquidation price = entry price + (liquidation loss / position size)
                liquidation_price = entry_price + (liquidation_loss / size) if size > 0 else float('inf')
                # Safe stop loss = liquidation price × 0.95 (5% below liquidation)
                safe_sl = liquidation_price * 0.95
                # But cannot go below default stop loss (3%)
                default_sl = entry_price * 1.03
                return min(safe_sl, default_sl)

        def validate_stop_loss(direction: str, entry_price: float, sl_price: float,
                              leverage: int, margin: float) -> tuple[bool, str, float]:
            """
            Validate if stop loss price is safe (triggers before liquidation)

            Returns:
                (is_safe, message, safe_sl_price)
            """
            # FIX: Prevent division by zero
            if entry_price <= 0 or margin <= 0 or leverage <= 0:
                # Cannot validate, return original stop loss price
                return True, "", sl_price

            size = (margin * leverage) / entry_price
            if size <= 0:
                return True, "", sl_price

            liquidation_loss = margin * 0.8

            if direction == "long":
                liquidation_price = entry_price - (liquidation_loss / size)
                if sl_price <= liquidation_price:
                    safe_sl = calculate_safe_stop_loss(direction, entry_price, leverage, margin)
                    return False, f"SL ${sl_price:.2f} below liquidation ${liquidation_price:.2f}, auto-adjusted to ${safe_sl:.2f}", safe_sl
            else:
                liquidation_price = entry_price + (liquidation_loss / size)
                if sl_price >= liquidation_price:
                    safe_sl = calculate_safe_stop_loss(direction, entry_price, leverage, margin)
                    return False, f"SL ${sl_price:.2f} above liquidation ${liquidation_price:.2f}, auto-adjusted to ${safe_sl:.2f}", safe_sl

            return True, "", sl_price

        async def open_long_tool(leverage: int = None, amount_percent: float = None,
                                confidence: int = None, reasoning: str = "") -> str:
            """
            Open long position (buy BTC) - Complete intelligent position handling + margin risk management

            Decision matrix:
            - No position -> Normal open long
            - Has long + can add -> Add to long
            - Has long + full position -> Maintain long
            - Has short -> Close short -> Open long (reverse operation)

            Risk checks:
            - Use real available margin (considering unrealized PnL)
            - Validate stop loss price not below liquidation
            - Reserve safety buffer

            Args:
                leverage: Leverage 1-20 (None=auto-calculate based on confidence)
                amount_percent: Position ratio 0.0-1.0 (None=auto-calculate based on confidence)
                confidence: Confidence 0-100 (None=auto-calculate based on votes)
                reasoning: Decision reasoning
            """
            current_price = await get_current_price()

            # FIX: Dynamically calculate parameters, no longer use hardcoded defaults
            # If confidence not provided, calculate dynamically based on votes
            if confidence is None:
                # Use _get_agents_consensus() to get vote dict
                votes_dict = self._get_agents_consensus() if hasattr(self, '_get_agents_consensus') else {}
                confidence = calculate_confidence_from_votes(votes_dict, direction='long')
                logger.info(f"[open_long] confidence not provided, calculated from votes: {confidence}%")

            # If leverage not provided, calculate based on confidence
            if leverage is None:
                leverage = calculate_leverage_from_confidence(confidence)
                logger.info(f"[open_long] leverage not provided, calculated from confidence: {leverage}x")

            # If amount_percent not provided, calculate based on confidence
            if amount_percent is None:
                amount_percent = calculate_amount_from_confidence(confidence)
                logger.info(f"[open_long] amount_percent not provided, calculated from confidence: {amount_percent*100:.0f}%")

            leverage = min(max(int(leverage), 1), 20)
            amount_percent = min(max(float(amount_percent), 0.0), 1.0)

            trade_success = False
            entry_price = current_price
            action_taken = "open_long"
            final_reasoning = reasoning or ""

            # Adjust TP/SL ratios based on leverage
            # Higher leverage = tighter stop loss
            if leverage >= 15:
                tp_percent, sl_percent = 0.05, 0.02  # 5% TP, 2% SL
            elif leverage >= 10:
                tp_percent, sl_percent = 0.06, 0.025  # 6% TP, 2.5% SL
            elif leverage >= 5:
                tp_percent, sl_percent = 0.08, 0.03  # 8% TP, 3% SL
            else:
                tp_percent, sl_percent = 0.10, 0.05  # 10% TP, 5% SL
            
            take_profit = current_price * (1 + tp_percent)
            stop_loss = current_price * (1 - sl_percent)
            
            if toolkit and toolkit.paper_trader:
                try:
                    # 📊 Step 1: Collect complete status info
                    position = await toolkit.paper_trader.get_position()
                    account = await toolkit.paper_trader.get_account()
                    
                    has_position = position and position.get("has_position", False)
                    # 🔧 FIX: get_position() returns flat dict, not nested structure
                    # Get data directly from position dict
                    current_direction = position.get("direction") if has_position else None
                    existing_entry = position.get("entry_price", 0) if has_position else 0
                    existing_margin = position.get("margin", 0) if has_position else 0
                    unrealized_pnl = position.get("unrealized_pnl", 0) if has_position else 0
                    liquidation_price = position.get("liquidation_price", 0) if has_position else 0
                    
                    # 🔧 Key fix: Prioritize OKX's max_avail_size (real available margin)
                    # max_avail_size is from OKX /api/v5/account/max-avail-size
                    # Considers maintenance margin, initial margin rate etc, more accurate than local calc
                    max_avail_size = account.get("max_avail_size", 0)

                    # Fallback: Local calc true_available_margin = total_equity - used_margin
                    total_equity = account.get("total_equity", 10000)
                    used_margin = account.get("used_margin", 0)
                    local_available = total_equity - used_margin

                    # Use OKX value if valid, otherwise use local calculation
                    if max_avail_size > 0:
                        true_available_margin = max_avail_size
                        margin_source = "OKX API"
                    else:
                        true_available_margin = local_available
                        margin_source = "Local calc"

                    # Backward compatibility
                    if true_available_margin <= 0:
                        true_available_margin = account.get("true_available_margin", local_available)

                    available_balance = account.get("available_balance", 0)
                    total_equity = account.get("total_equity", available_balance)
                    used_margin = account.get("used_margin", 0)

                    # 🔧 Add condition: true_available_margin >= min_amount + safety_buffer
                    can_add = true_available_margin >= (MIN_ADD_AMOUNT + SAFETY_BUFFER)

                    logger.info(f"[TradeExecutor] 📊 Status: position={current_direction or 'none'}, "
                               f"available_margin=${true_available_margin:.2f}({margin_source}), "
                               f"balance=${available_balance:.2f}, used=${used_margin:.2f}, "
                               f"unrealized_pnl=${unrealized_pnl:.2f}, can_add={can_add}")
                    
                    # 📌 Scenario 1: Already have long position (same direction)
                    if current_direction == "long":
                        if can_add:
                            # Scenario 1a: Can add -> Add to long position
                            # 🔧 Use true_available_margin (considers unrealized PnL)
                            add_amount = min(
                                true_available_margin * amount_percent,
                                true_available_margin - SAFETY_BUFFER  # Keep safety buffer
                            )
                            add_amount = max(add_amount, 0)  # Ensure non-negative
                            
                            if add_amount >= MIN_ADD_AMOUNT:
                                logger.info(f"[TradeExecutor] 🔄 Already have long, adding ${add_amount:.2f} (available ${true_available_margin:.2f})")
                                
                                # 🔧 Validate stop loss safety
                                is_safe, sl_msg, safe_sl = validate_stop_loss("long", current_price, stop_loss, leverage, add_amount)
                                if not is_safe:
                                    logger.warning(f"[TradeExecutor] ⚠️ {sl_msg}")
                                    stop_loss = safe_sl
                                
                                result = await toolkit.paper_trader.open_long(
                                    symbol="BTC-USDT-SWAP",
                                    leverage=leverage,
                                    amount_usdt=add_amount,
                                    tp_price=take_profit,
                                    sl_price=stop_loss
                                )
                                
                                if result.get("success"):
                                    trade_success = True
                                    action_taken = "add_to_long"
                                    entry_price = result.get("executed_price", current_price)
                                    final_reasoning = f"Add to long success: original entry ${existing_entry:.2f}, added ${add_amount:.2f}(unrealized PnL ${unrealized_pnl:.2f}). {reasoning}"
                                    logger.info(f"[TradeExecutor] ✅ Add to long success")
                                else:
                                    # Add failed, maintain original position
                                    trade_success = True
                                    action_taken = "maintain_long"
                                    entry_price = existing_entry
                                    final_reasoning = f"Add failed({result.get('error')}), maintaining long (entry ${existing_entry:.2f}). {reasoning}"
                            else:
                                # Add amount too small
                                trade_success = True
                                action_taken = "maintain_long_small"
                                entry_price = existing_entry
                                final_reasoning = f"Add amount too small (${add_amount:.2f}<${MIN_ADD_AMOUNT}), maintaining long (unrealized PnL ${unrealized_pnl:.2f}). {reasoning}"
                        else:
                            # Scenario 1b: Full position or near liquidation -> Maintain long
                            trade_success = True
                            action_taken = "maintain_long_full"
                            entry_price = existing_entry
                            # Check if near liquidation
                            if liquidation_price > 0 and current_price < liquidation_price * 1.1:
                                final_reasoning = f"⚠️ Near liquidation (liq price ${liquidation_price:.2f}), maintaining long (unrealized loss ${unrealized_pnl:.2f}). {reasoning}"
                            else:
                                final_reasoning = f"Full position (available ${true_available_margin:.2f}), maintaining long (entry ${existing_entry:.2f}, unrealized PnL ${unrealized_pnl:.2f}). {reasoning}"
                            logger.info(f"[TradeExecutor] ✅ Full position/cannot add, maintaining long")
                    
                    # 📌 Scenario 2: Have short position (opposite direction) -> Close short -> Open long
                    elif current_direction == "short":
                        logger.info(f"[TradeExecutor] 🔄 Reverse operation: close short -> open long (short unrealized PnL ${unrealized_pnl:.2f})")
                        
                        # Close short position first
                        close_result = await toolkit.paper_trader.close_position(
                            symbol="BTC-USDT-SWAP",
                            reason="Reverse: short to long"
                        )
                        
                        if close_result.get("success"):
                            pnl = close_result.get("pnl", 0)
                            logger.info(f"[TradeExecutor] ✅ Close short success, PnL=${pnl:.2f}")
                            
                            # 🔧 Re-get true available margin (balance changed after closing)
                            account = await toolkit.paper_trader.get_account()
                            new_true_available = account.get("true_available_margin", 0)
                            if new_true_available <= 0:
                                new_true_available = account.get("total_equity", 10000) - account.get("used_margin", 0)
                            
                            amount_usdt = min(
                                new_true_available * amount_percent,
                                new_true_available - SAFETY_BUFFER
                            )
                            amount_usdt = max(amount_usdt, 0)
                            
                            if amount_usdt >= MIN_ADD_AMOUNT:
                                # 🔧 Validate stop loss safety
                                is_safe, sl_msg, safe_sl = validate_stop_loss("long", current_price, stop_loss, leverage, amount_usdt)
                                if not is_safe:
                                    logger.warning(f"[TradeExecutor] ⚠️ {sl_msg}")
                                    stop_loss = safe_sl
                                
                                # Open long position
                                result = await toolkit.paper_trader.open_long(
                                    symbol="BTC-USDT-SWAP",
                                    leverage=leverage,
                                    amount_usdt=amount_usdt,
                                    tp_price=take_profit,
                                    sl_price=stop_loss
                                )
                                if result.get("success"):
                                    trade_success = True
                                    action_taken = "reverse_short_to_long"
                                    entry_price = result.get("executed_price", current_price)
                                    final_reasoning = f"Reverse success: closed short (PnL=${pnl:.2f}) -> opened long ${amount_usdt:.2f}. {reasoning}"
                                    logger.info(f"[TradeExecutor] ✅ Reverse to long success")
                                else:
                                    trade_success = True  # Close success counts as partial success
                                    action_taken = "close_short_only"
                                    entry_price = current_price
                                    final_reasoning = f"Close short success (PnL=${pnl:.2f}), but open long failed ({result.get('error')}). {reasoning}"
                            else:
                                trade_success = True
                                action_taken = "close_short_insufficient"
                                entry_price = current_price
                                final_reasoning = f"Close short success (PnL=${pnl:.2f}), but insufficient balance for long (available ${new_true_available:.2f}). {reasoning}"
                        else:
                            final_reasoning = f"Close short failed: {close_result.get('error')}. {reasoning}"
                    
                    # 📌 Scenario 3: No position -> Normal open long
                    else:
                        # 🔧 Use true_available_margin
                        amount_usdt = min(
                            true_available_margin * amount_percent,
                            true_available_margin - SAFETY_BUFFER
                        )
                        amount_usdt = max(amount_usdt, 0)
                        
                        if amount_usdt >= MIN_ADD_AMOUNT:
                            # 🔧 Validate stop loss safety
                            is_safe, sl_msg, safe_sl = validate_stop_loss("long", current_price, stop_loss, leverage, amount_usdt)
                            if not is_safe:
                                logger.warning(f"[TradeExecutor] ⚠️ {sl_msg}")
                                stop_loss = safe_sl
                            
                            logger.info(f"[TradeExecutor] 📈 Normal open long: ${amount_usdt:.2f}, {leverage}x (available ${true_available_margin:.2f})")
                            
                            result = await toolkit.paper_trader.open_long(
                                symbol="BTC-USDT-SWAP",
                                leverage=leverage,
                                amount_usdt=amount_usdt,
                                tp_price=take_profit,
                                sl_price=stop_loss
                            )
                            
                            if result.get("success"):
                                trade_success = True
                                action_taken = "new_long"
                                entry_price = result.get("executed_price", current_price)
                                final_reasoning = f"Open long success: ${amount_usdt:.2f}, {leverage}x leverage, SL ${stop_loss:.2f}. {reasoning}"
                                logger.info(f"[TradeExecutor] ✅ Open long success: entry ${entry_price:.2f}")
                            else:
                                final_reasoning = f"Open long failed: {result.get('error')}. {reasoning}"
                        else:
                            final_reasoning = f"Insufficient balance (${available_balance:.2f}), cannot open position. {reasoning}"
                        
                except Exception as e:
                    logger.error(f"[TradeExecutor] Open long exception: {e}", exc_info=True)
                    final_reasoning = f"Execution exception: {e}. {reasoning}"
            
            # Save TradingSignal
            execution_result["signal"] = TradingSignal(
                direction="long",
                symbol="BTC-USDT-SWAP",
                leverage=leverage,
                amount_percent=amount_percent,
                entry_price=entry_price,
                take_profit_price=take_profit,
                stop_loss_price=stop_loss,
                confidence=confidence,
                reasoning=final_reasoning or f"TradeExecutor decided long ({action_taken})",
                agents_consensus={},
                timestamp=datetime.now()
            )
            
            status = "Success" if trade_success else "Failed"
            return f"✅ Long {status}({action_taken}): {leverage}x leverage, {amount_percent*100:.0f}% position, entry ${entry_price:,.2f}"
        
        async def open_short_tool(leverage: int = None, amount_percent: float = None,
                                 confidence: int = None, reasoning: str = "") -> str:
            """
            Open short position (short BTC) - Smart position handling + margin risk management

            Decision matrix:
            - No position -> Normal open short
            - Already short + can add -> Add to short
            - Already short + full position -> Maintain short
            - Already long -> Close long -> Open short (reverse)

            Risk checks:
            - Uses true available margin (considers unrealized PnL)
            - Validates stop loss not above liquidation price
            - Maintains safety buffer

            Args:
                leverage: Leverage 1-20 (None=auto-calculate based on confidence)
                amount_percent: Position ratio 0.0-1.0 (None=auto-calculate based on confidence)
                confidence: Confidence 0-100 (None=auto-calculate based on votes)
                reasoning: Decision reasoning
            """
            current_price = await get_current_price()

            # 🔧 FIX: Dynamic parameter calculation, no longer using hardcoded defaults
            # If confidence not provided, calculate based on votes
            if confidence is None:
                # Use _get_agents_consensus() to get votes dict
                votes_dict = self._get_agents_consensus() if hasattr(self, '_get_agents_consensus') else {}
                confidence = calculate_confidence_from_votes(votes_dict, direction='short')
                logger.info(f"[open_short] confidence not provided, calculated from votes: {confidence}%")

            # If leverage not provided, calculate based on confidence
            if leverage is None:
                leverage = calculate_leverage_from_confidence(confidence)
                logger.info(f"[open_short] leverage not provided, calculated from confidence: {leverage}x")

            # If amount_percent not provided, calculate based on confidence
            if amount_percent is None:
                amount_percent = calculate_amount_from_confidence(confidence)
                logger.info(f"[open_short] amount_percent not provided, calculated from confidence: {amount_percent*100:.0f}%")

            leverage = min(max(int(leverage), 1), 20)
            amount_percent = min(max(float(amount_percent), 0.0), 1.0)
            
            # Adjust TP/SL ratios based on leverage (for short)
            if leverage >= 15:
                tp_percent, sl_percent = 0.05, 0.02
            elif leverage >= 10:
                tp_percent, sl_percent = 0.06, 0.025
            elif leverage >= 5:
                tp_percent, sl_percent = 0.08, 0.03
            else:
                tp_percent, sl_percent = 0.10, 0.05
            
            take_profit = current_price * (1 - tp_percent)  # Short: TP when price drops
            stop_loss = current_price * (1 + sl_percent)    # Short: SL when price rises
            
            trade_success = False
            entry_price = current_price
            action_taken = "open_short"
            final_reasoning = reasoning or ""
            
            if toolkit and toolkit.paper_trader:
                try:
                    # 📊 Step 1: Collect complete status info
                    position = await toolkit.paper_trader.get_position()
                    account = await toolkit.paper_trader.get_account()
                    
                    has_position = position and position.get("has_position", False)
                    # 🔧 FIX: get_position() returns flat dict, not nested structure
                    # Get data directly from position dict
                    current_direction = position.get("direction") if has_position else None
                    existing_entry = position.get("entry_price", 0) if has_position else 0
                    existing_margin = position.get("margin", 0) if has_position else 0
                    unrealized_pnl = position.get("unrealized_pnl", 0) if has_position else 0
                    liquidation_price = position.get("liquidation_price", 0) if has_position else 0
                    
                    # 🔧 Key fix: Prioritize OKX's max_avail_size (real available margin)
                    max_avail_size = account.get("max_avail_size", 0)

                    # Fallback: Local calculation
                    total_equity = account.get("total_equity", 10000)
                    used_margin = account.get("used_margin", 0)
                    local_available = total_equity - used_margin

                    # Use OKX value if valid
                    if max_avail_size > 0:
                        true_available_margin = max_avail_size
                        margin_source = "OKX API"
                    else:
                        true_available_margin = local_available
                        margin_source = "Local calc"

                    if true_available_margin <= 0:
                        true_available_margin = account.get("true_available_margin", local_available)

                    available_balance = account.get("available_balance", 0)
                    total_equity = account.get("total_equity", available_balance)
                    used_margin = account.get("used_margin", 0)

                    # 🔧 Add condition check
                    can_add = true_available_margin >= (MIN_ADD_AMOUNT + SAFETY_BUFFER)

                    logger.info(f"[TradeExecutor] 📊 Status: position={current_direction or 'none'}, "
                               f"available_margin=${true_available_margin:.2f}({margin_source}), "
                               f"balance=${available_balance:.2f}, used=${used_margin:.2f}, "
                               f"unrealized_pnl=${unrealized_pnl:.2f}, can_add={can_add}")

                    # 📌 Scenario 1: Already have short position (same direction)
                    if current_direction == "short":
                        if can_add:
                            # Scenario 1a: Can add -> Add to short position
                            add_amount = min(
                                true_available_margin * amount_percent,
                                true_available_margin - SAFETY_BUFFER
                            )
                            add_amount = max(add_amount, 0)
                            
                            if add_amount >= MIN_ADD_AMOUNT:
                                logger.info(f"[TradeExecutor] 🔄 Already have short, adding ${add_amount:.2f} (available ${true_available_margin:.2f})")
                                
                                # 🔧 Validate stop loss safety
                                is_safe, sl_msg, safe_sl = validate_stop_loss("short", current_price, stop_loss, leverage, add_amount)
                                if not is_safe:
                                    logger.warning(f"[TradeExecutor] ⚠️ {sl_msg}")
                                    stop_loss = safe_sl
                                
                                result = await toolkit.paper_trader.open_short(
                                    symbol="BTC-USDT-SWAP",
                                    leverage=leverage,
                                    amount_usdt=add_amount,
                                    tp_price=take_profit,
                                    sl_price=stop_loss
                                )
                                
                                if result.get("success"):
                                    trade_success = True
                                    action_taken = "add_to_short"
                                    entry_price = result.get("executed_price", current_price)
                                    final_reasoning = f"Add to short success: original entry ${existing_entry:.2f}, added ${add_amount:.2f}(unrealized PnL ${unrealized_pnl:.2f}). {reasoning}"
                                    logger.info(f"[TradeExecutor] ✅ Add to short success")
                                else:
                                    trade_success = True
                                    action_taken = "maintain_short"
                                    entry_price = existing_entry
                                    final_reasoning = f"Add failed({result.get('error')}), maintaining short (entry ${existing_entry:.2f}). {reasoning}"
                            else:
                                trade_success = True
                                action_taken = "maintain_short_small"
                                entry_price = existing_entry
                                final_reasoning = f"Add amount too small (${add_amount:.2f}<${MIN_ADD_AMOUNT}), maintaining short (unrealized PnL ${unrealized_pnl:.2f}). {reasoning}"
                        else:
                            # Scenario 1b: Full position or near liquidation -> Maintain short
                            trade_success = True
                            action_taken = "maintain_short_full"
                            entry_price = existing_entry
                            if liquidation_price > 0 and current_price > liquidation_price * 0.9:
                                final_reasoning = f"⚠️ Near liquidation (liq price ${liquidation_price:.2f}), maintaining short (unrealized loss ${unrealized_pnl:.2f}). {reasoning}"
                            else:
                                final_reasoning = f"Full position (available ${true_available_margin:.2f}), maintaining short (entry ${existing_entry:.2f}, unrealized PnL ${unrealized_pnl:.2f}). {reasoning}"
                            logger.info(f"[TradeExecutor] ✅ Full position/cannot add, maintaining short")
                    
                    # 📌 Scenario 2: Have long position (opposite direction) -> Close long -> Open short
                    elif current_direction == "long":
                        logger.info(f"[TradeExecutor] 🔄 Reverse operation: close long -> open short (long unrealized PnL ${unrealized_pnl:.2f})")
                        
                        # Close long position first
                        close_result = await toolkit.paper_trader.close_position(
                            symbol="BTC-USDT-SWAP",
                            reason="Reverse: long to short"
                        )
                        
                        if close_result.get("success"):
                            pnl = close_result.get("pnl", 0)
                            logger.info(f"[TradeExecutor] ✅ Close long success, PnL=${pnl:.2f}")
                            
                            # 🔧 Re-get true available margin
                            account = await toolkit.paper_trader.get_account()
                            new_true_available = account.get("true_available_margin", 0)
                            if new_true_available <= 0:
                                new_true_available = account.get("total_equity", 10000) - account.get("used_margin", 0)
                            
                            amount_usdt = min(
                                new_true_available * amount_percent,
                                new_true_available - SAFETY_BUFFER
                            )
                            amount_usdt = max(amount_usdt, 0)
                            
                            if amount_usdt >= MIN_ADD_AMOUNT:
                                # 🔧 Validate stop loss safety
                                is_safe, sl_msg, safe_sl = validate_stop_loss("short", current_price, stop_loss, leverage, amount_usdt)
                                if not is_safe:
                                    logger.warning(f"[TradeExecutor] ⚠️ {sl_msg}")
                                    stop_loss = safe_sl
                                
                                # Open short position
                                result = await toolkit.paper_trader.open_short(
                                    symbol="BTC-USDT-SWAP",
                                    leverage=leverage,
                                    amount_usdt=amount_usdt,
                                    tp_price=take_profit,
                                    sl_price=stop_loss
                                )
                                if result.get("success"):
                                    trade_success = True
                                    action_taken = "reverse_long_to_short"
                                    entry_price = result.get("executed_price", current_price)
                                    final_reasoning = f"Reverse success: closed long (PnL=${pnl:.2f}) -> opened short ${amount_usdt:.2f}. {reasoning}"
                                    logger.info(f"[TradeExecutor] ✅ Reverse to short success")
                                else:
                                    trade_success = True
                                    action_taken = "close_long_only"
                                    entry_price = current_price
                                    final_reasoning = f"Close long success (PnL=${pnl:.2f}), but open short failed ({result.get('error')}). {reasoning}"
                            else:
                                trade_success = True
                                action_taken = "close_long_insufficient"
                                entry_price = current_price
                                final_reasoning = f"Close long success (PnL=${pnl:.2f}), but insufficient balance for short (available ${new_true_available:.2f}). {reasoning}"
                        else:
                            final_reasoning = f"Close long failed: {close_result.get('error')}. {reasoning}"
                    
                    # 📌 Scenario 3: No position -> Normal open short
                    else:
                        amount_usdt = min(
                            true_available_margin * amount_percent,
                            true_available_margin - SAFETY_BUFFER
                        )
                        amount_usdt = max(amount_usdt, 0)
                        
                        if amount_usdt >= MIN_ADD_AMOUNT:
                            # 🔧 Validate stop loss safety
                            is_safe, sl_msg, safe_sl = validate_stop_loss("short", current_price, stop_loss, leverage, amount_usdt)
                            if not is_safe:
                                logger.warning(f"[TradeExecutor] ⚠️ {sl_msg}")
                                stop_loss = safe_sl
                            
                            logger.info(f"[TradeExecutor] 📉 Normal open short: ${amount_usdt:.2f}, {leverage}x (available ${true_available_margin:.2f})")
                            
                            result = await toolkit.paper_trader.open_short(
                                symbol="BTC-USDT-SWAP",
                                leverage=leverage,
                                amount_usdt=amount_usdt,
                                tp_price=take_profit,
                                sl_price=stop_loss
                            )
                            
                            if result.get("success"):
                                trade_success = True
                                action_taken = "new_short"
                                entry_price = result.get("executed_price", current_price)
                                final_reasoning = f"Open short success: ${amount_usdt:.2f}, {leverage}x leverage, SL ${stop_loss:.2f}. {reasoning}"
                                logger.info(f"[TradeExecutor] ✅ Open short success: entry ${entry_price:.2f}")
                            else:
                                final_reasoning = f"Open short failed: {result.get('error')}. {reasoning}"
                        else:
                            final_reasoning = f"Insufficient balance (available ${true_available_margin:.2f}), cannot open position. {reasoning}"
                        
                except Exception as e:
                    logger.error(f"[TradeExecutor] Open short exception: {e}", exc_info=True)
                    final_reasoning = f"Execution exception: {e}. {reasoning}"
            
            execution_result["signal"] = TradingSignal(
                direction="short",
                symbol="BTC-USDT-SWAP",
                leverage=leverage,
                amount_percent=amount_percent,
                entry_price=entry_price,
                take_profit_price=take_profit,
                stop_loss_price=stop_loss,
                confidence=confidence,
                reasoning=final_reasoning or f"TradeExecutor decided short ({action_taken})",
                agents_consensus={},
                timestamp=datetime.now()
            )
            
            status = "Success" if trade_success else "Failed"
            return f"✅ Short {status}({action_taken}): {leverage}x leverage, {amount_percent*100:.0f}% position, entry ${entry_price:,.2f}"
        
        async def close_position_tool(reasoning: str = "") -> str:
            """
            Close current position
            
            Args:
                reasoning: Close reason
            """
            current_price = await get_current_price()
            close_success = False
            pnl = 0.0
            
            if toolkit and toolkit.paper_trader:
                try:
                    # Pass reason parameter for logging
                    result = await toolkit.paper_trader.close_position(
                        symbol="BTC-USDT-SWAP",
                        reason=reasoning or "TradeExecutor decided to close"
                    )
                    
                    if result.get("success"):
                        close_success = True
                        pnl = result.get("pnl", 0)
                        logger.info(f"[TradeExecutor] ✅ Close position success, PnL: ${pnl:.2f}")
                    else:
                        error_msg = result.get("error", "Unknown error")
                        logger.error(f"[TradeExecutor] Close position failed: {error_msg}")
                        reasoning = f"Close execution failed: {error_msg}. " + reasoning
                        
                except Exception as e:
                    logger.error(f"[TradeExecutor] Close position exception: {e}")
                    reasoning = f"Close execution exception: {e}. " + reasoning
            
            execution_result["signal"] = TradingSignal(
                direction="hold",
                symbol="BTC-USDT-SWAP",
                leverage=1,
                amount_percent=0.0,
                entry_price=current_price,
                take_profit_price=current_price,
                stop_loss_price=current_price,
                confidence=100 if close_success else 50,
                reasoning=f"[Close position] {reasoning or 'TradeExecutor decided to close'}" + (f" (PnL: ${pnl:.2f})" if close_success else ""),
                agents_consensus={},
                timestamp=datetime.now()
            )
            
            return f"✅ Close {'Success' if close_success else 'Failed'}" + (f" (PnL: ${pnl:.2f})" if close_success else "")
        
        async def hold_tool(reason: str = "Market unclear, choosing to hold") -> str:
            """
            Hold/Wait - no operation
            
            Args:
                reason: Hold reason
            """
            current_price = await get_current_price()
            logger.info(f"[TradeExecutor] ✅ Decided to hold: {reason}")
            
            execution_result["signal"] = TradingSignal(
                direction="hold",
                symbol="BTC-USDT-SWAP",
                leverage=1,
                amount_percent=0.0,
                entry_price=current_price,
                take_profit_price=current_price,
                stop_loss_price=current_price,
                confidence=0,
                reasoning=reason,
                agents_consensus={},
                timestamp=datetime.now()
            )
            
            return f"📊 Decided to hold: {reason}"
        
        # Create Agent instance and register FunctionTool
        # FIX: Agent uses id instead of agent_id, uses llm_gateway_url instead of llm_endpoint
        trade_executor = Agent(
            id="trade_executor",
            name="TradeExecutor",
            role="Trade Execution Specialist",
            system_prompt="""You are the Trade Executor, responsible for executing trades based on expert meeting results.

## Available Tools
- **analyze_execution_conditions**: Analyze market liquidity and recommend execution strategy (CALL FIRST for large orders!)
- **open_long**: Open long position (buy BTC)
- **open_short**: Open short position (sell BTC)
- **close_position**: Close current position
- **hold**: Hold/wait, no action

## Smart Execution Protocol

### For LARGE Orders (>$10,000):
1. ALWAYS call `analyze_execution_conditions` FIRST
2. Review the recommended strategy (direct/sliced/twap)
3. If slippage > 0.5%, consider reducing position size
4. Use the recommended leverage and slice count

### Capital Tier Guidelines:
- Small (<$1,000): Direct execution
- Medium ($1,000-$10,000): Check slippage first
- Large ($10,000-$50,000): Use sliced execution (3-5 batches)
- XLarge (>$50,000): Requires TWAP strategy

## Decision Rules
1. Experts 3-4 votes unanimous bullish → Call open_long (with execution analysis for large orders)
2. Experts 3-4 votes unanimous bearish → Call open_short (with execution analysis for large orders)
3. Experts split or unclear → Call hold
4. Has opposite position to close → Call close_position

## Risk Management
- Always check liquidity before large orders
- Reduce leverage if slippage is high  
- Abort if estimated slippage > 1%

You MUST call a tool based on meeting results!""",
            llm_gateway_url=leader.llm_gateway_url if hasattr(leader, 'llm_gateway_url') else "http://llm_gateway:8003",
            temperature=0.3
        )

        # Register trading tools (using FunctionTool wrapper)
        trade_executor.register_tool(FunctionTool(
            name="open_long",
            description="Open long position (buy BTC) - Call when expert consensus is bullish",
            func=open_long_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "leverage": {"type": "integer", "description": "Leverage multiplier 1-20"},
                    "amount_percent": {"type": "number", "description": "Position ratio 0.0-1.0"},
                    "confidence": {"type": "integer", "description": "Confidence level 0-100"},
                    "reasoning": {"type": "string", "description": "Decision reasoning"}
                },
                "required": ["leverage", "amount_percent"]
            }
        ))

        trade_executor.register_tool(FunctionTool(
            name="open_short",
            description="Open short position (sell BTC) - Call when expert consensus is bearish",
            func=open_short_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "leverage": {"type": "integer", "description": "Leverage multiplier 1-20"},
                    "amount_percent": {"type": "number", "description": "Position ratio 0.0-1.0"},
                    "confidence": {"type": "integer", "description": "Confidence level 0-100"},
                    "reasoning": {"type": "string", "description": "Decision reasoning"}
                },
                "required": ["leverage", "amount_percent"]
            }
        ))

        trade_executor.register_tool(FunctionTool(
            name="close_position",
            description="Close current position - Call when need TP/SL or reverse operation",
            func=close_position_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "reasoning": {"type": "string", "description": "Close reasoning"}
                }
            }
        ))

        trade_executor.register_tool(FunctionTool(
            name="hold",
            description="Hold/wait, no action - Call when market unclear or experts split",
            func=hold_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Hold reason"}
                },
                "required": ["reason"]
            }
        ))

        # Add execution analysis tool for large orders
        async def analyze_execution_tool(amount_usdt: float, direction: str = "long") -> str:
            """
            Analyze execution conditions before placing a trade.
            Returns strategy recommendation, estimated slippage, and liquidity rating.
            """
            try:
                from app.core.trading.smart_executor import analyze_execution
                analysis = await analyze_execution(
                    amount_usdt=float(amount_usdt),
                    direction=direction.lower(),
                    symbol="BTC"
                )
                
                summary = f"""📊 Execution Analysis for ${amount_usdt:,.2f} {direction.upper()}

💰 Capital Tier: {analysis.get('capital_tier', 'unknown').upper()}
📈 Recommended Strategy: {analysis.get('recommended_strategy', 'direct').upper()}
🔢 Recommended Slices: {analysis.get('recommended_slices', 1)}
📉 Estimated Slippage: {analysis.get('estimated_slippage_percent', 0):.3f}%
💧 Liquidity Rating: {analysis.get('liquidity_rating', 'unknown').upper()}

💡 Recommendation: {analysis.get('recommendation', 'N/A')}"""
                
                logger.info(f"[TradeExecutor] Execution analysis: {analysis.get('recommended_strategy')} with slippage {analysis.get('estimated_slippage_percent', 0):.3f}%")
                return summary
            except Exception as e:
                logger.error(f"[TradeExecutor] Execution analysis error: {e}")
                return f"⚠️ Analysis failed: {e}. Using conservative defaults."
        
        trade_executor.register_tool(FunctionTool(
            name="analyze_execution_conditions",
            description="Analyze market liquidity and recommend execution strategy. CALL THIS FIRST for orders >$10,000!",
            func=analyze_execution_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "amount_usdt": {"type": "number", "description": "Amount in USDT to trade"},
                    "direction": {"type": "string", "description": "Trade direction: long or short", "enum": ["long", "short"]}
                },
                "required": ["amount_usdt", "direction"]
            }
        ))

        logger.info(f"[TradeExecutor] ✅ Agent created successfully, registered {len(trade_executor.tools)} trading tools")
        
        # Wrapper class providing run() method that returns TradingSignal
        class TradeExecutorWrapper:
            def __init__(self, agent, result_container, tools_dict):
                self.agent = agent
                self.result = result_container
                self.tools = tools_dict  # Tool functions dict
            
            async def run(self, prompt: str) -> TradingSignal:
                """
                Run TradeExecutor, call LLM and process tool execution
                
                Flow:
                1. Call Agent._call_llm() to get LLM response
                2. Detect native tool_calls or Legacy [USE_TOOL: xxx] format
                3. Execute corresponding tool functions
                4. Return TradingSignal
                """
                try:
                    # Step 1: Call LLM
                    messages = [{"role": "user", "content": prompt}]
                    response = await self.agent._call_llm(messages)
                    
                    # Step 2: Parse response
                    content = ""
                    tool_calls = []
                    
                    if isinstance(response, dict):
                        # OpenAI format response
                        if "choices" in response and response["choices"]:
                            message = response["choices"][0].get("message", {})
                            content = message.get("content", "")
                            tool_calls = message.get("tool_calls", [])
                        else:
                            content = response.get("content", str(response))
                    else:
                        content = str(response)
                    
                    logger.info(f"[TradeExecutor] LLM response: {content[:200] if content else 'None'}...")
                    
                    # Step 3: Handle native tool_calls (OpenAI format)
                    if tool_calls:
                        logger.info(f"[TradeExecutor] 🎯 Detected native Tool Calls: {len(tool_calls)}")
                        for tc in tool_calls:
                            func = tc.get("function", {})
                            tool_name = func.get("name", "")
                            tool_args_str = func.get("arguments", "{}")
                            
                            if tool_name in self.tools:
                                try:
                                    import json
                                    tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                                    logger.info(f"[TradeExecutor] 🔧 Executing native tool: {tool_name}({tool_args})")
                                    await self.tools[tool_name](**tool_args)
                                except Exception as e:
                                    logger.error(f"[TradeExecutor] Tool execution failed: {e}")
                    
                    # Step 4: Handle Legacy format [USE_TOOL: xxx] (DEPRECATED - kept for backward compat)
                    tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
                    legacy_matches = re.findall(tool_pattern, content or "")
                    
                    if legacy_matches:
                        logger.warning(f"[TradeExecutor] ⚠️ DEPRECATED: Legacy [USE_TOOL: xxx] format detected. This will be removed in future versions.")
                        logger.info(f"[TradeExecutor] 🎯 Detected Legacy Tool Calls: {len(legacy_matches)}")
                        for tool_name, params_str in legacy_matches:
                            if tool_name in self.tools:
                                try:
                                    # Parse arguments
                                    params = {}
                                    # Try various argument formats
                                    for pattern in [r'(\w+)="([^"]*)"', r"(\w+)='([^']*)'", r'(\w+)=(\d+\.?\d*)']:
                                        for key, value in re.findall(pattern, params_str):
                                            # Type conversion
                                            if value.replace('.', '').replace('-', '').isdigit():
                                                value = float(value) if '.' in value else int(value)
                                            params[key] = value

                                    # Parameter name mapping (LLM may use different names)
                                    param_aliases = {
                                        'reason': 'reasoning',  # LLM often uses reason instead of reasoning
                                        'amount': 'amount_percent',
                                        'lev': 'leverage',
                                        'conf': 'confidence',
                                    }
                                    for old_name, new_name in param_aliases.items():
                                        if old_name in params and new_name not in params:
                                            params[new_name] = params.pop(old_name)

                                    logger.info(f"[TradeExecutor] 🔧 Executing Legacy tool: {tool_name}({params})")
                                    await self.tools[tool_name](**params)
                                except Exception as e:
                                    logger.error(f"[TradeExecutor] Tool execution failed: {e}")
                    
                    # Step 5: Check if there are tool execution results
                    if self.result["signal"]:
                        signal = self.result["signal"]
                        logger.info(f"[TradeExecutor] ✅ Tool execution complete: {signal.direction}")
                        # Clear result container for next use
                        self.result["signal"] = None
                        return signal
                    
                    # Step 6: No tool calls - try to infer decision from response text
                    logger.warning("[TradeExecutor] ⚠️ No tool calls detected, trying to infer from response...")
                    return await self._infer_from_text(content or "")
                    
                except Exception as e:
                    logger.error(f"[TradeExecutor] ❌ Execution failed: {e}", exc_info=True)
                    current_price = await get_current_price()
                    return TradingSignal(
                        direction="hold",
                        symbol="BTC-USDT-SWAP",
                        leverage=1,
                        amount_percent=0.0,
                        entry_price=current_price,
                        take_profit_price=current_price,
                        stop_loss_price=current_price,
                        confidence=0,
                        reasoning=f"TradeExecutor execution failed: {str(e)}",
                        agents_consensus={},
                        timestamp=datetime.now()
                    )
            
            async def _infer_from_text(self, text: str) -> TradingSignal:
                """Infer decision from natural language response (DEPRECATED - fallback)"""
                logger.warning("[TradeExecutor] ⚠️ DEPRECATED: Using text inference fallback. "
                              "This indicates LLM did not use native tool calling. "
                              "This fallback will be removed in future versions.")
                text_lower = text.lower()

                # Detect direction keywords (English only)
                if any(kw in text_lower for kw in ['long', 'buy', 'bullish']):
                    # Extract parameters - if not in text, set to None for dynamic calculation
                    leverage_match = re.search(r'(\d+)\s*[xX]', text)
                    leverage = int(leverage_match.group(1)) if leverage_match else None

                    amount_match = re.search(r'(\d+)\s*%', text)
                    amount = (int(amount_match.group(1)) / 100) if amount_match else None

                    confidence_match = re.search(r'[Cc]onfidence\s*[:：]?\s*(\d+)', text)
                    confidence = int(confidence_match.group(1)) if confidence_match else None

                    logger.info(f"[TradeExecutor] 📊 Inferred long from text: leverage={leverage}, amount={amount}, confidence={confidence}")
                    logger.info(f"[TradeExecutor] 📊 Missing parameters will be dynamically calculated from votes")
                    await self.tools['open_long'](
                        leverage=min(leverage, 20) if leverage else None,
                        amount_percent=min(amount, 1.0) if amount else None,
                        confidence=confidence,
                        reasoning=text[:200]
                    )

                elif any(kw in text_lower for kw in ['short', 'sell', 'bearish']):
                    leverage_match = re.search(r'(\d+)\s*[xX]', text)
                    leverage = int(leverage_match.group(1)) if leverage_match else None

                    amount_match = re.search(r'(\d+)\s*%', text)
                    amount = (int(amount_match.group(1)) / 100) if amount_match else None

                    confidence_match = re.search(r'[Cc]onfidence\s*[:：]?\s*(\d+)', text)
                    confidence = int(confidence_match.group(1)) if confidence_match else None

                    logger.info(f"[TradeExecutor] 📊 Inferred short from text: leverage={leverage}, amount={amount}, confidence={confidence}")
                    logger.info(f"[TradeExecutor] 📊 Missing parameters will be dynamically calculated from votes")
                    await self.tools['open_short'](
                        leverage=min(leverage, 20) if leverage else None,
                        amount_percent=min(amount, 1.0) if amount else None,
                        confidence=confidence,
                        reasoning=text[:200]
                    )
                    
                elif any(kw in text_lower for kw in ['close']):
                    logger.info("[TradeExecutor] 📊 Inferred close position from text")
                    await self.tools['close_position'](reasoning=text[:200])
                    
                else:
                    logger.info("[TradeExecutor] 📊 Inferred hold from text")
                    await self.tools['hold'](reason=text[:200] or "Market unclear")
                
                # Return execution result
                if self.result["signal"]:
                    signal = self.result["signal"]
                    self.result["signal"] = None
                    return signal
                
                # If tool execution also failed, return default hold
                current_price = await get_current_price()
                return TradingSignal(
                    direction="hold",
                    symbol="BTC-USDT-SWAP",
                    leverage=1,
                    amount_percent=0.0,
                    entry_price=current_price,
                    take_profit_price=current_price,
                    stop_loss_price=current_price,
                    confidence=0,
                    reasoning=f"Cannot infer decision: {text[:100]}",
                    agents_consensus={},
                    timestamp=datetime.now()
                )
        
        # Create tools dict for wrapper
        tools_dict = {
            'open_long': open_long_tool,
            'open_short': open_short_tool,
            'close_position': close_position_tool,
            'hold': hold_tool
        }
        
        return TradeExecutorWrapper(trade_executor, execution_result, tools_dict)
    
    def _build_execution_prompt(
        self,
        leader_summary: str,
        agents_votes: Dict[str, str],
        position_context: PositionContext
    ) -> str:
        """
        Build execution phase prompt

        This prompt is sent to TradeExecutor's LLM to call tools and execute trades
        """

        # FIX: Ensure agents_votes is dict type
        if isinstance(agents_votes, list):
            logger.warning(f"[_build_execution_prompt] agents_votes is list type, converting to dict")
            try:
                agents_votes = {v.agent_name: v.direction for v in agents_votes if hasattr(v, 'agent_name') and hasattr(v, 'direction')}
            except Exception as e:
                logger.error(f"[_build_execution_prompt] Cannot convert agents_votes: {e}")
                agents_votes = {}

        # Format votes
        long_count = sum(1 for v in agents_votes.values() if v == 'long')
        short_count = sum(1 for v in agents_votes.values() if v == 'short')
        hold_count = sum(1 for v in agents_votes.values() if v == 'hold')

        vote_details = []
        for agent, vote in agents_votes.items():
            emoji = "🟢" if vote == "long" else "🔴" if vote == "short" else "⚪"
            vote_text = "Long" if vote == "long" else "Short" if vote == "short" else "Hold"
            vote_details.append(f"  {emoji} {agent}: {vote_text}")

        # Format position status
        if position_context.has_position:
            direction = position_context.direction or "unknown"
            position_status = f"""**Has Position** ({direction.upper()})
- Entry Price: ${position_context.entry_price:,.2f}
- Current Price: ${position_context.current_price:,.2f}
- Position Size: {position_context.size:.4f} BTC
- Leverage: {position_context.leverage}x
- Unrealized P&L: ${position_context.unrealized_pnl:,.2f} ({position_context.unrealized_pnl_percent:+.2f}%)
- Available Balance: ${position_context.available_balance:,.2f}"""
        else:
            position_status = f"""**No Position**
- Available Balance: ${position_context.available_balance:,.2f}
- Total Equity: ${position_context.total_equity:,.2f}"""

        prompt = f"""## Trade Execution Task

### 1. Expert Voting Results
**Summary**: {long_count} Long / {short_count} Short / {hold_count} Hold

{chr(10).join(vote_details)}

### 2. Current Position Status
{position_status}

### 3. Leader's Meeting Summary
{leader_summary}

---

### Your Task
Based on the above information, you **MUST call a tool** to execute the trading decision.

**Decision Rules (based on voting consensus level)**:
- High consensus (4-5 unanimous votes) → Call open_long/open_short, parameters auto-calculated based on votes
- Moderate consensus (3 votes) → Call open_long/open_short, parameters auto-calculated based on votes
- Weak consensus (2 votes) → Call open_long/open_short, parameters auto-calculated based on votes
- Split opinions or unclear → Call hold(reason="...")
- Has opposite position to handle → First call close_position()

**Important**: confidence/leverage/amount_percent will be auto-calculated based on voting consensus level, no need to manually specify fixed values!

**To execute your decision**, simply state your intent clearly and call the appropriate tool:
- For going long: call open_long with your reasoning
- For going short: call open_short with your reasoning  
- For holding: call hold with your reason
- For closing: call close_position with your reason

Now, please analyze and execute your trading decision."""

        return prompt
    
    def _get_leader_final_summary(self) -> str:
        """Get Leader's last message as meeting summary"""
        if not hasattr(self, 'message_bus') or not self.message_bus:
            self.logger.warning("[TradingMeeting] message_bus does not exist")
            return "No meeting record"

        # FIX: MessageBus uses message_history instead of messages
        messages = getattr(self.message_bus, 'message_history', [])
        if not messages:
            return "No meeting messages"
        
        # Find Leader's last message from message history
        leader_messages = [
            msg for msg in messages
            if (hasattr(msg, 'sender') and msg.sender == "Leader") or
               (hasattr(msg, 'agent_name') and msg.agent_name == "Leader") or
               (hasattr(msg, 'agent_id') and msg.agent_id == "leader") or
               (isinstance(msg, dict) and (
                   msg.get("sender") == "Leader" or 
                   msg.get("agent_name") == "Leader" or 
                   msg.get("agent_id") == "leader"
               ))
        ]
        
        if leader_messages:
            last_msg = leader_messages[-1]
            # Handle Message object or dict
            if isinstance(last_msg, dict):
                return last_msg.get("content", "")
            elif hasattr(last_msg, 'content'):
                return last_msg.content
            else:
                return str(last_msg)
        
        return "Leader did not speak (possibly LLM failure)"

    async def _run_agent_turn(self, agent: Agent, prompt: str) -> str:
        """Run a single agent's turn using agent's own LLM call method with tool execution
        
        For ReWOOAgent instances, uses the 3-phase ReWOO architecture:
        1. Plan: Generate all tool calls at once
        2. Execute: Run tools in parallel
        3. Solve: Synthesize results into final analysis
        
        For regular Agent instances, uses direct LLM call with tool execution.
        """
        # Get conversation history for context
        history = self._get_conversation_history()

        # Build full prompt with history
        full_prompt = f"{history}\n\n{prompt}"

        try:
            # Get agent's memory for context injection
            if not self._memory_store:
                self._memory_store = await get_memory_store()

            memory = await self._memory_store.get_memory(agent.id, agent.name)
            memory_context = memory.get_context_for_prompt()

            # Build enhanced system prompt with memory
            # Use _get_system_prompt() which includes tool usage instructions
            if hasattr(agent, '_get_system_prompt'):
                base_system_prompt = agent._get_system_prompt()
            else:
                base_system_prompt = agent.system_prompt or agent.role_prompt

            # 🔧 FIX: Check if there's any meaningful memory content to inject
            # Check not only total_trades but also reflections and lessons
            has_memory_content = (
                memory.total_trades > 0 or
                len(memory.recent_reflections) > 0 or
                memory.last_trade_summary or
                len(memory.lessons_learned) > 0
            )

            if has_memory_content and memory_context.strip():
                # Only inject memory if agent has meaningful history
                enhanced_system_prompt = f"""{base_system_prompt}

---
{memory_context}
---

Please reference your historical performance and lessons learned in your analysis, avoid repeating past mistakes."""
            else:
                enhanced_system_prompt = base_system_prompt

            # ========================================
            # 🚀 ReWOO vs Regular Agent Routing
            # ========================================
            if isinstance(agent, ReWOOAgent) and hasattr(agent, 'analyze_with_rewoo'):
                # Use ReWOO 3-phase execution for ReWOOAgent instances
                # This is more efficient: Plan once → Execute in parallel → Solve once
                logger.info(f"[ReWOO] Using 3-phase execution for agent: {agent.name}")
                
                # Build context for ReWOO
                rewoo_context = {
                    "system_prompt": enhanced_system_prompt,
                    "memory": memory_context if has_memory_content else "",
                    "symbol": self.config.symbol,
                    "meeting_phase": "trading_analysis"
                }
                
                # Call ReWOO's analyze_with_rewoo method
                content = await agent.analyze_with_rewoo(full_prompt, rewoo_context)
                
                logger.info(f"[ReWOO] {agent.name} completed 3-phase analysis ({len(content) if content else 0} chars)")
                
                # Validate content for ReWOO path
                if not content or not content.strip():
                    content = f"[{agent.name}] Analysis complete, no clear recommendation at this time."
                elif "[Response blocked or empty]" in content:
                    logger.warning(f"[ReWOO] Agent {agent.name} response was blocked by content filter")
                    content = self._get_fallback_response(agent.id, agent.name)
                
                # ReWOO doesn't need additional tool execution - it handles tools internally
                self._pending_native_tool_calls = []
                
            else:
                # Regular Agent: Use direct LLM call with tool execution
                logger.info(f"Calling LLM for agent: {agent.name} (regular mode)")
                
                # Build messages for LLM
                messages = [
                    {"role": "system", "content": enhanced_system_prompt},
                    {"role": "user", "content": full_prompt}
                ]
                
                response = await agent._call_llm(messages)
                
                # Extract content from response for regular agents
                # Agent._call_llm returns OpenAI format: {"choices": [{"message": {"content": "..."}}]}
                content = ""
                if isinstance(response, dict):
                    if "choices" in response:
                        # OpenAI format
                        try:
                            content = response["choices"][0]["message"]["content"]
                        except (KeyError, IndexError):
                            pass
                    if not content:
                        # Fallback to direct content
                        content = response.get("content", response.get("response", ""))
                else:
                    content = str(response)
                
                # ===== Tool Execution for Regular Agents =====
                # Clear previous tool executions for this agent turn
                self._last_executed_tools = []
                
                # Step 1: Detect native tool_calls (OpenAI format)
                native_tool_calls = []
                if isinstance(response, dict) and "choices" in response:
                    try:
                        message = response["choices"][0].get("message", {})
                        native_tool_calls = message.get("tool_calls", [])
                        self._pending_native_tool_calls = native_tool_calls
                    except (KeyError, IndexError):
                        self._pending_native_tool_calls = []
            
            # For regular agents only: check and execute native tool calls
            # ReWOO agents handle tool execution internally via analyze_with_rewoo
            native_tool_calls = getattr(self, '_pending_native_tool_calls', [])
            if native_tool_calls and hasattr(agent, 'tools') and agent.tools and not isinstance(agent, ReWOOAgent):
                logger.info(f"[{agent.name}] 🎯 Detected native Tool Calls: {len(native_tool_calls)}")
                tool_results = []
                
                for tc in native_tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")
                    tool_args_str = func.get("arguments", "{}")
                    
                    if tool_name in agent.tools:
                        try:
                            import json
                            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                            logger.info(f"[{agent.name}] Native Tool Calling: {tool_name}({tool_args})")
                            
                            tool_result = await agent.tools[tool_name].execute(**tool_args)
                            logger.info(f"[{agent.name}] Tool {tool_name} result received")
                            
                            # Record executed tool call
                            self._last_executed_tools.append({
                                "tool_name": tool_name,
                                "params": tool_args,
                                "result": tool_result
                            })
                            
                            # Collect tool results
                            if isinstance(tool_result, dict) and "summary" in tool_result:
                                tool_results.append(f"\n[{tool_name} Result]: {tool_result['summary']}")
                            else:
                                tool_results.append(f"\n[{tool_name} Result]: {str(tool_result)[:1000]}")

                        except Exception as e:
                            logger.error(f"[{agent.name}] Native tool execution failed: {e}")
                            tool_results.append(f"\n[{tool_name} Error]: {str(e)}")
                
                # If we have tool results, do a follow-up LLM call
                if tool_results:
                    logger.info(f"[{agent.name}] Making follow-up LLM call with native tool results")
                    tool_results_text = "\n".join(tool_results)
                    
                    follow_up_messages = messages + [
                        {"role": "assistant", "content": content or ""},
                        {"role": "user", "content": f"Tool results:\n{tool_results_text}\n\nPlease provide your final analysis conclusion based on this real data."}
                    ]
                    
                    follow_up_response = await agent._call_llm(follow_up_messages)
                    
                    if isinstance(follow_up_response, dict):
                        if "choices" in follow_up_response:
                            try:
                                content = follow_up_response["choices"][0]["message"]["content"]
                            except (KeyError, IndexError):
                                pass
                        if not content:
                            content = follow_up_response.get("content", "")
                    elif isinstance(follow_up_response, str):
                        content = follow_up_response
            
            # Step 2: Detect Legacy format [USE_TOOL: xxx] (compatibility mode)
            tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
            tool_matches = re.findall(tool_pattern, content or "")

            # Deduplicate decision tools - only allow the FIRST open_long/open_short/hold call
            # This prevents Leader from accidentally calling the same trading tool multiple times
            decision_tools = {'open_long', 'open_short', 'hold'}
            seen_decision_tool = False
            filtered_matches = []
            for tool_name, params_str in tool_matches:
                if tool_name in decision_tools:
                    if not seen_decision_tool:
                        filtered_matches.append((tool_name, params_str))
                        seen_decision_tool = True
                        logger.info(f"[{agent.name}] Found first decision tool: {tool_name}, will skip any duplicates")
                    else:
                        logger.warning(f"[{agent.name}] Skipping duplicate decision tool call: {tool_name} (already have a decision)")
                else:
                    # Non-decision tools can be called multiple times
                    filtered_matches.append((tool_name, params_str))

            tool_matches = filtered_matches

            if tool_matches and hasattr(agent, 'tools') and agent.tools:
                logger.info(f"Agent {agent.name} has {len(tool_matches)} tool calls to execute")
                tool_results = []

                for tool_name, params_str in tool_matches:
                    # 🔒 CRITICAL: Only Leader can execute decision/execution tools
                    decision_tools = {'open_long', 'open_short', 'hold', 'close_position'}
                    is_leader = (hasattr(agent, 'id') and agent.id == "Leader") or agent.name == "Leader"
                    
                    if tool_name in decision_tools and not is_leader:
                        logger.warning(
                            f"[SECURITY_BLOCK] {agent.name} attempted to call decision tool '{tool_name}' "
                            f"but only Leader can execute trades in Phase 4. BLOCKING this call."
                        )
                        tool_results.append(
                            f"\n[{tool_name} Blocked]: Insufficient permissions - only Leader can execute trade decisions in Phase 4 (consensus formation phase). "
                            f"You should only provide analysis recommendations, do not call decision tools."
                        )
                        continue  # Skip this tool call
                    
                    if tool_name in agent.tools:
                        logger.info(f"[{agent.name}] Executing tool: {tool_name}")
                        try:
                            # Parse parameters - support both double and single quotes
                            params = {}
                            # Try double quotes first
                            param_pattern_double = r'(\w+)="([^"]*)"'
                            param_matches = re.findall(param_pattern_double, params_str)
                            # Try single quotes if no matches
                            if not param_matches:
                                param_pattern_single = r"(\w+)='([^']*)'"
                                param_matches = re.findall(param_pattern_single, params_str)

                            for key, value in param_matches:
                                params[key] = value
                            
                            # 🔧 FIX: Auto-convert parameter types based on tool schema
                            tool = agent.tools[tool_name]
                            if hasattr(tool, 'parameters_schema'):
                                schema = tool.parameters_schema
                                properties = schema.get('properties', {})
                                for key in list(params.keys()):
                                    if key in properties:
                                        expected_type = properties[key].get('type')
                                        try:
                                            if expected_type == 'integer':
                                                params[key] = int(params[key])
                                            elif expected_type == 'number':
                                                params[key] = float(params[key])
                                            elif expected_type == 'boolean':
                                                params[key] = str(params[key]).lower() in ['true', '1', 'yes']
                                            # string type remains as-is
                                        except (ValueError, TypeError) as e:
                                            logger.warning(f"[{agent.name}] Failed to convert param {key}={params[key]} to {expected_type}: {e}")
                            
                            logger.info(f"[{agent.name}] Tool {tool_name} params after type conversion: {params}")

                            # Execute the tool
                            tool_result = await agent.tools[tool_name].execute(**params)
                            logger.info(f"[{agent.name}] Tool {tool_name} executed successfully")

                            # Record executed tool call for signal extraction
                            self._last_executed_tools.append({
                                "tool_name": tool_name,
                                "params": params,
                                "result": tool_result
                            })
                            logger.info(f"[{agent.name}] Recorded tool execution: {tool_name} with params: {params}")

                            # Collect tool results
                            if isinstance(tool_result, dict) and "summary" in tool_result:
                                tool_results.append(f"\n[{tool_name} Result]: {tool_result['summary']}")
                            else:
                                tool_results.append(f"\n[{tool_name} Result]: {str(tool_result)[:1000]}")

                        except Exception as tool_error:
                            logger.error(f"[{agent.name}] Tool {tool_name} error: {tool_error}")
                            tool_results.append(f"\n[{tool_name} Error]: {str(tool_error)}")
                    else:
                        logger.warning(f"[{agent.name}] Tool {tool_name} not found in agent's tools")

                # If we have tool results, do a follow-up LLM call to get final analysis
                if tool_results:
                    logger.info(f"[{agent.name}] Making follow-up LLM call with tool results")
                    tool_results_text = "\n".join(tool_results)

                    follow_up_messages = messages + [
                        {"role": "assistant", "content": content},
                        {"role": "user", "content": f"Tool results:\n{tool_results_text}\n\nPlease provide your final analysis conclusion based on this real data. Note: Use the real data returned by tools, do not fabricate data. **Important: Do NOT call tools again, just summarize your analysis.**"}
                    ]

                    follow_up_response = await agent._call_llm(follow_up_messages)

                    # Extract content from follow-up response
                    if isinstance(follow_up_response, dict) and "choices" in follow_up_response:
                        try:
                            content = follow_up_response["choices"][0]["message"]["content"]
                        except (KeyError, IndexError):
                            pass
                    elif isinstance(follow_up_response, str):
                        content = follow_up_response
                    
                    # 🔒 CRITICAL FIX: Block tool calls in follow-up response
                    # Follow-up is ONLY for summary, should NOT execute tools again
                    follow_up_tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
                    follow_up_tool_matches = re.findall(follow_up_tool_pattern, content)
                    if follow_up_tool_matches:
                        logger.warning(f"[{agent.name}] ⚠️ Follow-up response contains {len(follow_up_tool_matches)} tool calls, BLOCKING them to prevent duplicate execution")
                        for tool_name, _ in follow_up_tool_matches:
                            logger.warning(f"[{agent.name}] Blocked tool call in follow-up: {tool_name}")
                        # Remove all tool call markers from follow-up content
                        content = re.sub(follow_up_tool_pattern, '[Tool Call Blocked]', content)
                        logger.info(f"[{agent.name}] Follow-up content cleaned, tool calls removed")
            # ===== End Tool Execution =====

            logger.info(f"Agent {agent.name} response: {content[:100]}...")

            # Add to message history
            self._add_message(
                agent_id=agent.id,
                agent_name=agent.name,
                content=content,
                message_type="response"
            )

            return content

        except Exception as e:
            logger.error(f"Error in agent turn for {agent.name}: {e}")
            self._add_message(
                agent_id="system",
                agent_name="System",
                content=f"❌ {agent.name} analysis failed: {str(e)[:100]}",
                message_type="error"
            )
            return ""

    def _get_agent_by_id(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        # self.agents is a dict {name: agent} from parent Meeting class
        for agent in self.agents.values():
            if agent.id == agent_id:
                return agent
        return None

    def _get_conversation_history(self) -> str:
        """Get formatted conversation history"""
        lines = []
        for msg in self.messages[-20:]:  # Last 20 messages
            lines.append(f"**{msg.get('agent_name', 'Unknown')}**: {msg.get('content', '')[:500]}")
        return "\n\n".join(lines)

    def _add_message(
        self,
        agent_id: str,
        agent_name: str,
        content: str,
        message_type: str = "message"
    ):
        """Add message to history and notify callback"""
        message = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "content": content,
            "type": message_type,
            "timestamp": datetime.now().isoformat()
        }

        if not hasattr(self, 'messages'):
            self.messages = []
        self.messages.append(message)

        if self.on_message:
            try:
                self.on_message(message)
            except Exception as e:
                logger.error(f"Error in message callback: {e}")

    def _summarize_votes(self) -> str:
        """Summarize agent votes"""
        if not self._agent_votes:
            return "No votes yet"

        lines = []
        for vote in self._agent_votes:
            lines.append(
                f"- {vote.agent_name}: {vote.direction} "
                f"(confidence {vote.confidence}%, leverage {vote.suggested_leverage}x)"
            )

        # Count votes
        directions = [v.direction for v in self._agent_votes]
        long_count = directions.count("long")
        short_count = directions.count("short")
        hold_count = directions.count("hold")

        lines.append(f"\nSummary: Long {long_count}, Short {short_count}, Hold {hold_count}")

        return "\n".join(lines)

    def _parse_vote_json(self, agent_id: str, agent_name: str, response: str) -> Optional[AgentVote]:
        """
        Parse JSON-formatted voting signal from Agent response

        Prefer JSON parsing, more reliable than string matching
        """
        try:
            # Try to extract JSON code block from response
            json_data = self._extract_json_from_response(response)

            if not json_data:
                logger.warning(f"[{agent_name}] No valid JSON code block found")
                return None

            # Parse direction (supports multiple formats)
            raw_direction = json_data.get("direction", "hold").lower().strip()
            direction = self._normalize_direction(raw_direction)

            # Parse other fields
            confidence = int(json_data.get("confidence", self.config.min_confidence))
            leverage = int(json_data.get("leverage", 1))
            tp_percent = float(json_data.get("take_profit_percent", self.config.default_tp_percent))
            sl_percent = float(json_data.get("stop_loss_percent", self.config.default_sl_percent))
            reasoning = json_data.get("reasoning", "")

            # Validate value ranges
            confidence = max(0, min(100, confidence))
            leverage = max(1, min(leverage, self.config.max_leverage))
            tp_percent = max(0.1, min(tp_percent, 50.0))
            sl_percent = max(0.1, min(sl_percent, 50.0))

            logger.info(f"[{agent_name}] ✅ JSON parsed successfully: direction={direction}, confidence={confidence}%, leverage={leverage}x")

            return AgentVote(
                agent_id=agent_id,
                agent_name=agent_name,
                direction=direction,
                confidence=confidence,
                reasoning=reasoning[:500] if reasoning else response[:200],
                suggested_leverage=leverage,
                suggested_tp_percent=tp_percent,
                suggested_sl_percent=sl_percent
            )

        except json.JSONDecodeError as e:
            logger.warning(f"[{agent_name}] JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"[{agent_name}] Error parsing vote: {e}")
            return None

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON object from Agent response

        Supports multiple formats:
        1. ```json ... ``` code block
        2. ``` ... ``` code block
        3. Direct JSON object {...}
        """
        import json

        # Strategy 1: Match ```json ... ``` code block
        json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', response, re.IGNORECASE)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Strategy 2: Match ``` ... ``` code block (without json tag)
        code_block_match = re.search(r'```\s*([\s\S]*?)\s*```', response)
        if code_block_match:
            content = code_block_match.group(1).strip()
            if content.startswith('{'):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass

        # Strategy 3: Direct match JSON object (find last one, as conclusion is usually at end)
        json_matches = list(re.finditer(r'\{[^{}]*"direction"[^{}]*\}', response, re.DOTALL))
        if json_matches:
            try:
                return json.loads(json_matches[-1].group())
            except json.JSONDecodeError:
                pass

        # Strategy 4: More lenient JSON matching (nested objects)
        brace_matches = list(re.finditer(r'\{[\s\S]*?\}', response))
        for match in reversed(brace_matches):  # Try from back to front
            try:
                data = json.loads(match.group())
                if "direction" in data:
                    return data
            except json.JSONDecodeError:
                continue

        return None

    def _normalize_direction(self, raw_direction: str) -> str:
        """
        Normalize trading direction string

        Convert various input formats to long/short/hold
        """
        direction_map = {
            # Long direction
            "long": "long",
            "buy": "long",
            "bullish": "long",
            "add_long": "long",
            # Short direction
            "short": "short",
            "sell": "short",
            "bearish": "short",
            "add_short": "short",
            # Hold direction
            "hold": "hold",
            "wait": "hold",
            "close": "hold",  # Close treated as hold (no new position)
            "reverse": "hold",  # Reverse needs special handling, temporarily treated as hold
        }
        return direction_map.get(raw_direction.lower(), "hold")

    def _parse_vote_fallback(self, agent_id: str, agent_name: str, response: str) -> Optional[AgentVote]:
        """
        Fallback parsing: Use text matching when JSON parsing fails
        
        DEPRECATED: This fallback method will be removed in future versions.
        Agents should output structured JSON for reliability.
        """
        logger.warning(f"[{agent_name}] ⚠️ DEPRECATED: Using text fallback parsing. "
                      "This indicates agent did not output valid JSON. "
                      "This fallback will be removed in future versions.")
        try:
            # Try to extract structured data - use config for defaults
            direction = "hold"
            confidence = self.config.min_confidence
            leverage = 1
            tp_percent = self.config.default_tp_percent
            sl_percent = self.config.default_sl_percent

            # Use improved direction parsing
            direction = self._extract_direction_from_response(response)

            # Parse confidence - English only
            # Format: **Confidence**: **75%**, Confidence: 75
            conf_match = re.search(r'\*{0,2}(?:Confidence)\*{0,2}[:\s]*\*{0,2}(\d+)', response, re.IGNORECASE)
            if conf_match:
                confidence = int(conf_match.group(1))

            # Parse leverage - English only
            # Format: Leverage: 3, 3x leverage
            lev_match = re.search(r'\*{0,2}(?:Suggested\s*)?(?:Leverage)\*{0,2}[:\s]*\*{0,2}(\d+)', response, re.IGNORECASE)
            if not lev_match:
                lev_match = re.search(r'(\d+)\s*[xX].*leverage|leverage.*?(\d+)\s*[xX]', response, re.IGNORECASE)
            if lev_match:
                lev_value = lev_match.group(1) if lev_match.group(1) else lev_match.group(2)
                if lev_value:
                    leverage = int(lev_value)

            # Parse TP/SL - English only
            # Format: Take Profit: 5%, Stop Loss: 3%
            tp_match = re.search(r'(?:Take\s*Profit|TP)[:\s]*(\d+\.?\d*)', response, re.IGNORECASE)
            if tp_match:
                tp_percent = float(tp_match.group(1))

            sl_match = re.search(r'(?:Stop\s*Loss|SL)[:\s]*(\d+\.?\d*)', response, re.IGNORECASE)
            if sl_match:
                sl_percent = float(sl_match.group(1))

            logger.info(f"[{agent_name}] Fallback parsing: direction={direction}, confidence={confidence}%")

            return AgentVote(
                agent_id=agent_id,
                agent_name=agent_name,
                direction=direction,
                confidence=confidence,
                reasoning=response[:200],
                suggested_leverage=min(leverage, self.config.max_leverage),
                suggested_tp_percent=tp_percent,
                suggested_sl_percent=sl_percent
            )

        except Exception as e:
            logger.error(f"[{agent_name}] Error parsing vote (fallback): {e}")
            logger.error(f"[{agent_name}] Response content: {response[:500]}")

            # Return None to signal parsing failure - caller will handle it
            return None

    def _extract_direction_from_response(self, response: str) -> str:
        """
        Extract trading direction from response, avoiding long bias.

        Strategy:
        1. First look for structured format "Direction: XXX"
        2. Then look for specific decision keywords
        3. Finally count keyword occurrences, take majority
        4. Avoid matching "long-term" and similar irrelevant words
        """
        response_lower = response.lower()

        # Strategy 1: Look for structured format "Direction: XXX" or "- Direction: XXX"
        # English only
        direction_match = re.search(
            r'[-\*]*\s*(?:Direction)[：:\s]*[-\*]*\s*(long|short|hold|buy|sell|bullish|bearish|wait)',
            response,
            re.IGNORECASE
        )
        if direction_match:
            raw_direction = direction_match.group(1).lower()
            # English keywords
            if raw_direction in ['long', 'buy', 'bullish']:
                return 'long'
            elif raw_direction in ['short', 'sell', 'bearish']:
                return 'short'
            elif raw_direction in ['hold', 'wait']:
                return 'hold'
            else:
                return 'hold'

        # Strategy 2: Look for explicit decision statements
        # English patterns only
        decision_patterns = [
            # English patterns
            (r'(?:recommend|suggest)[：:\s]*(long|buy|bullish)', 'long'),
            (r'(?:recommend|suggest)[：:\s]*(short|sell|bearish)', 'short'),
            (r'(?:recommend|suggest)[：:\s]*(hold|wait|neutral)', 'hold'),
            (r'(?:conclusion|decision)[：:\s]*(long|buy|bullish)', 'long'),
            (r'(?:conclusion|decision)[：:\s]*(short|sell|bearish)', 'short'),
            (r'(?:should|can|suitable to)\s*(go long|buy|open long)', 'long'),
            (r'(?:should|can|suitable to)\s*(go short|sell|open short)', 'short'),
            (r'I\s*(?:recommend|suggest|think).{0,15}(long|buy|bullish)', 'long'),
            (r'I\s*(?:recommend|suggest|think).{0,15}(short|sell|bearish)', 'short'),
        ]

        for pattern, direction in decision_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                logger.debug(f"[VoteParsing] Matched decision pattern: {pattern} -> {direction}")
                return direction

        # Strategy 3: Count keyword occurrences (avoid false matches)
        # Use precise matching, exclude "long-term", "belong" etc.
        # English keywords only
        long_keywords_en = ['bullish', 'upward', 'uptrend']
        short_keywords_en = ['bearish', 'downward', 'downtrend']
        hold_keywords_en = ['neutral', 'sideways', 'wait']

        # Calculate "strength" for each direction
        long_score = sum(response_lower.count(kw) for kw in long_keywords_en)
        short_score = sum(response_lower.count(kw) for kw in short_keywords_en)
        hold_score = sum(response_lower.count(kw) for kw in hold_keywords_en)

        # Check for English long/short, excluding common false matches
        # Use word boundary matching
        if re.search(r'\blong\b(?!\s*-?\s*term)', response_lower):
            long_score += 2  # Higher weight for explicit "long"
        if re.search(r'\bshort\b(?!\s*-?\s*term)', response_lower):
            short_score += 2  # Higher weight for explicit "short"
        if re.search(r'\bhold\b', response_lower):
            hold_score += 2

        logger.debug(f"[VoteParsing] Keyword scores: long={long_score}, short={short_score}, hold={hold_score}")

        # Take highest score, return hold if tied
        if long_score > short_score and long_score > hold_score:
            return 'long'
        elif short_score > long_score and short_score > hold_score:
            return 'short'
        else:
            return 'hold'

    async def _parse_signal(self, response: str) -> Optional[TradingSignal]:
        """Parse final trading signal from leader's response"""
        try:
            # Use config for all default values
            direction = "hold"
            confidence = self.config.min_confidence
            leverage = 1
            amount_percent = self.config.default_position_percent
            tp_percent = self.config.default_tp_percent
            sl_percent = self.config.default_sl_percent

            # FIX: Use improved direction parsing method to avoid long bias
            direction = self._extract_direction_from_response(response)

            # Parse confidence - English only
            conf_match = re.search(r'\*{0,2}(?:Confidence)\*{0,2}[:\s]*(\d+)', response, re.IGNORECASE)
            if conf_match:
                confidence = int(conf_match.group(1))

            # Parse leverage - English only
            # Format: "Leverage: 3", "**Leverage**: 3", "3x leverage"
            lev_match = re.search(r'\*{0,2}(?:Leverage)\*{0,2}[:\s]*(\d+)', response, re.IGNORECASE)
            if not lev_match:
                lev_match = re.search(r'(\d+)\s*[xX].*leverage|leverage.*?(\d+)\s*[xX]', response, re.IGNORECASE)
            if lev_match:
                lev_value = lev_match.group(1) or lev_match.group(2) if lev_match.lastindex and lev_match.lastindex > 1 else lev_match.group(1)
                leverage = min(int(lev_value), self.config.max_leverage)

            # Log parsed leverage for debugging
            logger.info(f"Parsed leverage: {leverage} (max allowed: {self.config.max_leverage})")

            # Parse position size - English only
            pos_match = re.search(r'(?:Position)[:\s]*(\d+\.?\d*)', response, re.IGNORECASE)
            if pos_match:
                raw_percent = float(pos_match.group(1)) / 100
                amount_percent = max(self.config.min_position_percent, min(raw_percent, self.config.max_position_percent))
                logger.info(f"Parsed position percent: {raw_percent*100:.1f}% -> clamped to {amount_percent*100:.1f}%")

            # Parse TP/SL percentages - English only
            tp_match = re.search(r'(?:Take\s*Profit|TP)[:\s]*(\d+\.?\d*)', response, re.IGNORECASE)
            if tp_match:
                tp_percent = float(tp_match.group(1))

            sl_match = re.search(r'(?:Stop\s*Loss|SL)[:\s]*(\d+\.?\d*)', response, re.IGNORECASE)
            if sl_match:
                sl_percent = float(sl_match.group(1))

            # Get current BTC price from price service (use real price from CoinGecko)
            current_price = await get_current_btc_price(demo_mode=False)
            logger.info(f"Using real BTC price: ${current_price:,.2f}")

            if direction == "long":
                tp_price = current_price * (1 + tp_percent / 100)
                sl_price = current_price * (1 - sl_percent / 100)
            elif direction == "short":
                tp_price = current_price * (1 - tp_percent / 100)
                sl_price = current_price * (1 + sl_percent / 100)
            else:
                tp_price = current_price
                sl_price = current_price

            # Build consensus from votes
            consensus = {v.agent_name: v.direction for v in self._agent_votes}

            return TradingSignal(
                direction=direction,
                symbol=self.config.symbol,
                leverage=leverage,
                amount_percent=amount_percent,
                entry_price=current_price,
                take_profit_price=tp_price,
                stop_loss_price=sl_price,
                confidence=confidence,
                reasoning=response[:500],
                agents_consensus=consensus
            )

        except Exception as e:
            logger.error(f"Error parsing signal: {e}")
            return None

    async def _parse_json_signal(self, response: str) -> Optional[TradingSignal]:
        """Parse trading signal from JSON format in response"""
        import json

        try:
            # Try to extract JSON from markdown code block
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON object
                json_match = re.search(r'\{[^{}]*"direction"[^{}]*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    logger.warning("No JSON found in response, falling back to regex parsing")
                    return await self._parse_signal(response)

            # Remove comments from JSON (LLM sometimes adds // comments)
            json_str = re.sub(r'//.*?(?=\n|$)', '', json_str)
            # Remove trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)

            logger.info(f"Parsing JSON decision: {json_str[:200]}...")

            decision = json.loads(json_str)

            # Extract values with config-based defaults
            direction = decision.get("direction", "hold").lower()
            if direction not in ["long", "short", "hold"]:
                direction = "hold"

            confidence = int(decision.get("confidence", self.config.min_confidence))
            confidence = max(0, min(100, confidence))

            leverage = int(decision.get("leverage", 1))
            leverage = max(1, min(leverage, self.config.max_leverage))

            position_percent = float(decision.get("position_percent", self.config.default_position_percent * 100))
            raw_percent = position_percent / 100
            amount_percent = max(self.config.min_position_percent, min(raw_percent, self.config.max_position_percent))

            tp_percent = float(decision.get("take_profit_percent", self.config.default_tp_percent))
            sl_percent = float(decision.get("stop_loss_percent", self.config.default_sl_percent))

            reasoning = decision.get("reasoning", "")
            risks = decision.get("risks", "")

            logger.info(f"JSON Parsed - Direction: {direction}, Leverage: {leverage}x, Confidence: {confidence}%")

            # Get current BTC price from CoinGecko
            current_price = await get_current_btc_price(demo_mode=False)
            logger.info(f"Using real BTC price: ${current_price:,.2f}")

            # Calculate TP/SL prices
            if direction == "long":
                tp_price = current_price * (1 + tp_percent / 100)
                sl_price = current_price * (1 - sl_percent / 100)
            elif direction == "short":
                tp_price = current_price * (1 - tp_percent / 100)
                sl_price = current_price * (1 + sl_percent / 100)
            else:
                tp_price = current_price
                sl_price = current_price

            # Build consensus from votes
            consensus = {v.agent_name: v.direction for v in self._agent_votes}

            full_reasoning = f"{reasoning}\n\nRisk Warning: {risks}" if risks else reasoning

            return TradingSignal(
                direction=direction,
                symbol=self.config.symbol,
                leverage=leverage,
                amount_percent=amount_percent,
                entry_price=current_price,
                take_profit_price=tp_price,
                stop_loss_price=sl_price,
                confidence=confidence,
                reasoning=full_reasoning[:500],
                agents_consensus=consensus
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}, falling back to regex parsing")
            return await self._parse_signal(response)
        except Exception as e:
            logger.error(f"Error parsing JSON signal: {e}")
            return await self._parse_signal(response)

    def _get_fallback_response(self, agent_id: str, agent_name: str) -> str:
        """
        Generate fallback response when Gemini content filter blocks the response.
        This provides a neutral, conservative response to keep the meeting going.
        """
        fallback_responses = {
            "MacroEconomist": """## Macroeconomic Analysis (Data Limited)

I am the **Macro Economist "Global Perspective"**.

Due to temporary data access limitations, I provide the following analysis framework based on historical experience:

### Macro Score: 5/10 (Neutral)

### Key Observations:
1. **Interest Rate Environment**: Global central bank monetary policies require attention
2. **Liquidity Conditions**: Market liquidity changes may impact crypto assets
3. **US Dollar Index**: USD typically has negative correlation with BTC

### Macro Recommendation:
- Direction: **Hold**
- Current macro environment uncertainty is high
- Recommend waiting for clearer macro signals

### Risk Note:
Macro data access is limited, recommend relying more on technical and sentiment analysis for trading decisions.""",

            "TechnicalAnalyst": """## Technical Analysis (Data Limited)

I am the **Technical Analyst "Chart Master"**.

Due to temporary technical data access limitations, please refer to the following framework:

### Technical Score: 5/10 (Neutral)

### Recommendation:
- Wait for data recovery before detailed technical analysis
- Short-term recommendation is to hold""",

            "SentimentAnalyst": """## Sentiment Analysis (Data Limited)

I am the **Sentiment Analyst "Market Pulse"**.

Due to temporary sentiment data access limitations, here is a reference:

### Sentiment Score: 5/10 (Neutral)

### Recommendation:
- Currently unable to obtain real-time Fear & Greed Index
- Recommend referring to other expert opinions
- Short-term stance should be cautious""",

            "QuantStrategist": """## Quantitative Analysis (Data Limited)

I am the **Quant Strategist "Data Hunter"**.

Due to temporary quant data access limitations:

### Quant Score: 5/10 (Neutral)

### Recommendation:
- Insufficient data, unable to provide quant signals
- Recommend holding and waiting for data recovery""",

            "RiskAssessor": """## Risk Assessment (Cautious Mode)

I am the **Risk Assessor "Prudent Guardian"**.

Due to partial data access limitations, enabling cautious mode:

### Risk Level: Medium-High

### Recommendations:
- Recommend reducing position size
- Lower leverage appropriately
- Set stricter stop losses

### Risk Management Advice:
A more conservative trading strategy should be adopted when data is incomplete."""
        }

        return fallback_responses.get(agent_id, f"""## {agent_name} Analysis (Data Limited)

Due to temporary data access limitations, unable to provide complete analysis.

### Recommendation: Hold
### Confidence: 50%

Recommend referring to other expert opinions for decision making.""")
    
