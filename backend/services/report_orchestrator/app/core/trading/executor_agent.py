"""
Executor Agent

Trade execution agent that inherits from ReWOOAgent, using the same 3-phase
(Plan → Execute → Solve) workflow as other analysis agents.

Key Features:
- Inherits from ReWOOAgent (unified architecture with other agents)
- Registers trading tools: open_long, open_short, hold, close_position
- Uses same LLM calling pattern as TechnicalAnalyst, MacroEconomist, etc.
- No special tool_choice param - follows standard ReWOO planning
- Funding fee awareness for cost-conscious trading decisions
"""

import logging
import json
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from app.core.roundtable.rewoo_agent import ReWOOAgent
from app.core.roundtable.tool import FunctionTool
from app.models.trading_models import TradingSignal
from app.core.trading.price_service import get_current_btc_price
from app.core.trading.decision_store import TradingDecision, TradingDecisionStore

# Funding fee awareness imports
from app.core.trading.funding import (
    get_funding_data_service,
    get_funding_calculator,
    get_entry_timing_controller,
    get_funding_context_provider,
    get_funding_impact_monitor,
    get_holding_time_manager,
    EntryAction,
    TradeViability
)

logger = logging.getLogger(__name__)

# ========== Config from Environment ==========
def _get_env_float(key: str, default: float) -> float:
    val = os.getenv(key)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default

def _get_env_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default

# Read trading config from environment (same as TradingMeetingConfig)
EXECUTOR_CONFIG = {
    # Position sizing
    "min_percent": _get_env_float("MIN_POSITION_PERCENT", 10) / 100,
    "max_percent": _get_env_float("MAX_POSITION_PERCENT", 30) / 100,
    "default_percent": _get_env_float("DEFAULT_POSITION_PERCENT", 20) / 100,
    # TP/SL defaults
    "default_tp": _get_env_float("DEFAULT_TP_PERCENT", 5.0),
    "default_sl": _get_env_float("DEFAULT_SL_PERCENT", 2.0),
    # Leverage
    "max_leverage": _get_env_int("MAX_LEVERAGE", 20),
    "default_leverage": 5,  # Default for LLM when not specified
    # Confidence thresholds
    "min_confidence": _get_env_int("MIN_CONFIDENCE", 60),
    "min_confidence_open": _get_env_int("MIN_CONFIDENCE_OPEN", 65),  # For opening positions
    "min_confidence_close": _get_env_int("MIN_CONFIDENCE_CLOSE", 50),  # For closing positions
}

# Backward compatibility alias
POSITION_CONFIG = EXECUTOR_CONFIG


class ExecutorAgent(ReWOOAgent):
    """
    Trading Execution Agent - inherits from ReWOOAgent for unified architecture.
    
    Uses the same 3-phase workflow as other analysis agents:
    1. Plan: LLM decides which trading action to take
    2. Execute: Run the selected trading tool
    3. Solve: Generate final trading signal
    
    This ensures ExecutorAgent uses the same LLM calling pattern that works
    for other agents, avoiding tool_choice incompatibility issues.
    """
    
    # Safety thresholds - now read from environment
    MIN_CONFIDENCE_OPEN = EXECUTOR_CONFIG['min_confidence_open']
    MIN_CONFIDENCE_CLOSE = EXECUTOR_CONFIG['min_confidence_close']
    
    # Position management constants
    MIN_ADD_AMOUNT = 10.0  # Minimum USDT to add to position
    SAFETY_BUFFER = 50.0   # Reserve this much USDT in margin
    
    def __init__(
        self,
        toolkit=None,
        paper_trader=None,
        safety_guard=None,
        on_message: Optional[Callable] = None,
        symbol: str = "BTC-USDT-SWAP",
        llm_gateway_url: str = "http://llm_gateway:8003"
    ):
        """
        Initialize ExecutorAgent.
        
        Args:
            toolkit: Trading toolkit with trading functions
            paper_trader: Paper trading client
            safety_guard: Optional SafetyGuard for risk checks
            on_message: Callback for progress messages
            symbol: Trading symbol
            llm_gateway_url: LLM gateway service URL
        """
        super().__init__(
            name="TradeExecutor",
            role_prompt=self._get_executor_role_prompt(),
            llm_gateway_url=llm_gateway_url,
            model="gpt-4",
            temperature=1.0  # Match other ReWOO agents - low temp (0.3) caused instability
        )
        
        self.toolkit = toolkit
        self.paper_trader = paper_trader
        self.safety_guard = safety_guard
        self.on_message = on_message
        self.symbol = symbol
        
        # Result container for tool execution
        self._result: Dict[str, Any] = {"signal": None}
        self._executed_tools: List[Dict[str, Any]] = []
        
        # Decision store for Redis persistence
        self._decision_store = TradingDecisionStore()
        self._current_context: Optional[Dict[str, Any]] = None  # For saving with decision
        
        # Position context (updated before each execution)
        self._position_context: Dict[str, Any] = {}
        
        # Register trading tools
        self._register_trading_tools()
        
        # Funding fee awareness - register force-close callback
        self._setup_funding_monitor()
        
        logger.info(
            f"[ExecutorAgent] Initialized with {len(self.tools)} tools - "
            f"Position range: {POSITION_CONFIG['min_percent']*100:.0f}%-{POSITION_CONFIG['max_percent']*100:.0f}%, "
            f"Default: {POSITION_CONFIG['default_percent']*100:.0f}%, "
            f"Funding fee awareness: enabled"
        )
    
    def _get_executor_role_prompt(self) -> str:
        """Get the role prompt for executor agent."""
        return """You are a professional trading executor responsible for making the final trading decision.

Your job is to:
1. Review the leader's summary and agent consensus
2. Consider the current position context (IMPORTANT!)
3. Decide on a trading action based on BOTH consensus AND position state

You have access to these trading tools:

BASIC ACTIONS:
- open_long: Open a new LONG position (when NO position or CLOSING SHORT to go LONG)
- open_short: Open a new SHORT position (when NO position or CLOSING LONG to go SHORT)
- hold: Do nothing, wait for better opportunity
- close_position: Close existing position completely

POSITION MANAGEMENT (use when already holding a position):
- add_to_long: Add to existing LONG position (when already LONG and trend strengthens)
- add_to_short: Add to existing SHORT position (when already SHORT and trend strengthens)
- reduce_position: Partially close position (to lock in profits or reduce risk)

DECISION LOGIC:
1. If NO position: use open_long, open_short, or hold
2. If holding LONG and bullish consensus: use add_to_long or hold
3. If holding LONG and bearish consensus: use close_position or reduce_position
4. If holding SHORT and bearish consensus: use add_to_short or hold
5. If holding SHORT and bullish consensus: use close_position or reduce_position

IMPORTANT RULES:
- You MUST call exactly ONE tool to express your decision
- ALWAYS consider current position before acting
- When in profit, consider reduce_position to lock in gains
- If already holding same direction as consensus, prefer add_to or hold over new open"""
    
    def _create_planning_prompt(self) -> str:
        """
        Override ReWOOAgent's planning prompt to use trading-specific examples.
        
        This prevents the LLM from generating analysis tool calls (like crypto_price,
        technical_analysis) which ExecutorAgent doesn't have. Instead, it provides
        examples of trading tools (hold, open_long, etc.).
        """
        tools_desc = self._format_tools_description()
        
        return f"""You are {self.name}, making a trading execution decision.

{self.role_prompt}

## Available Tools (ONLY THESE):
{tools_desc}

## Your Task:
Based on the trading analysis already completed, you need to:
1. Review the leader's summary and agent consensus
2. Consider current position context
3. Make ONE decisive trading action

## OUTPUT FORMAT (CRITICAL - MUST FOLLOW EXACTLY):

You MUST output ONLY a JSON array with EXACTLY ONE tool call. NO other text, NO explanation.

Valid output examples:

Example 1 (HOLD decision - most common):
[
  {{"step": 1, "tool": "hold", "params": {{"reason": "Majority of analysts recommend holding. Extreme Fear sentiment provides contrarian support but technical signals are mixed.", "confidence": 65}}, "purpose": "Maintain current position as per consensus"}}
]

Example 2 (OPEN LONG - bullish consensus):
[
  {{"step": 1, "tool": "open_long", "params": {{"leverage": 5, "amount_percent": {EXECUTOR_CONFIG['default_percent']}, "tp_percent": {EXECUTOR_CONFIG['default_tp']}, "sl_percent": {EXECUTOR_CONFIG['default_sl']}, "reasoning": "Strong bullish consensus with 4/5 experts recommending LONG. Technical breakout confirmed.", "confidence": 75}}, "purpose": "Open long position based on bullish consensus"}}
]

Example 3 (CLOSE POSITION - risk management):
[
  {{"step": 1, "tool": "close_position", "params": {{"reason": "Stop loss threshold reached. Risk management dictates exit.", "confidence": 90}}, "purpose": "Close existing position to protect capital"}}
]

## CRITICAL RULES:
1. Output ONLY the JSON array - nothing before, nothing after
2. You can ONLY use these tools: hold, open_long, open_short, close_position
3. Call EXACTLY ONE tool - not zero, not two, just one
4. DO NOT try to call analysis tools like crypto_price, technical_analysis, etc.
5. The analysis is already done - your job is to DECIDE and EXECUTE

DO NOT add explanations. DO NOT use markdown code blocks. JUST the raw JSON array with ONE tool call.
"""
    
    def _register_trading_tools(self):
        """Register trading tools for LLM tool calling."""
        
        # Dynamic position sizing from config
        min_pct = POSITION_CONFIG['min_percent']
        max_pct = POSITION_CONFIG['max_percent']
        default_pct = POSITION_CONFIG['default_percent']
        default_tp = POSITION_CONFIG['default_tp']
        default_sl = POSITION_CONFIG['default_sl']
        
        # open_long tool
        self.register_tool(FunctionTool(
            name="open_long",
            description=f"Open a LONG position (buy, expecting price to rise). Parameters: leverage (1-20), amount_percent ({min_pct:.1f}-{max_pct:.1f}, default {default_pct:.1f}), tp_percent (default {default_tp}%), sl_percent (default {default_sl}%), reasoning (string), confidence (0-100)",
            func=self._execute_open_long,
            parameters_schema={
                "type": "object",
                "properties": {
                    "leverage": {"type": "integer", "description": "Leverage (1-20)", "default": 5},
                    "amount_percent": {"type": "number", "description": f"Position size as % of account ({min_pct:.1f}-{max_pct:.1f})", "default": default_pct},
                    "tp_percent": {"type": "number", "description": "Take profit % from entry", "default": default_tp},
                    "sl_percent": {"type": "number", "description": "Stop loss % from entry", "default": default_sl},
                    "reasoning": {"type": "string", "description": "Reason for this trade"},
                    "confidence": {"type": "integer", "description": "Confidence level 0-100", "default": 70}
                },
                "required": ["reasoning"]
            }
        ))
        
        # open_short tool
        self.register_tool(FunctionTool(
            name="open_short",
            description=f"Open a SHORT position (sell, expecting price to fall). Parameters: leverage (1-20), amount_percent ({min_pct:.1f}-{max_pct:.1f}, default {default_pct:.1f}), tp_percent (default {default_tp}%), sl_percent (default {default_sl}%), reasoning (string), confidence (0-100)",
            func=self._execute_open_short,
            parameters_schema={
                "type": "object",
                "properties": {
                    "leverage": {"type": "integer", "description": "Leverage (1-20)", "default": 5},
                    "amount_percent": {"type": "number", "description": f"Position size as % of account ({min_pct:.1f}-{max_pct:.1f})", "default": default_pct},
                    "tp_percent": {"type": "number", "description": "Take profit % from entry", "default": default_tp},
                    "sl_percent": {"type": "number", "description": "Stop loss % from entry", "default": default_sl},
                    "reasoning": {"type": "string", "description": "Reason for this trade"},
                    "confidence": {"type": "integer", "description": "Confidence level 0-100", "default": 70}
                },
                "required": ["reasoning"]
            }
        ))
        
        # hold tool
        self.register_tool(FunctionTool(
            name="hold",
            description="Do not trade, maintain current position or wait for better opportunity. Parameters: reason (string), confidence (0-100)",
            func=self._execute_hold,
            parameters_schema={
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Reason for holding"},
                    "confidence": {"type": "integer", "description": "Confidence level 0-100", "default": 50}
                },
                "required": ["reason"]
            }
        ))
        
        # close_position tool
        self.register_tool(FunctionTool(
            name="close_position",
            description="Close the current position completely. Parameters: reason (string), confidence (0-100)",
            func=self._execute_close_position,
            parameters_schema={
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Reason for closing the position"},
                    "confidence": {"type": "integer", "description": "Confidence level 0-100", "default": 100}
                },
                "required": ["reason"]
            }
        ))
        
        # add_to_long tool (NEW - position management)
        self.register_tool(FunctionTool(
            name="add_to_long",
            description="Add to existing LONG position when trend continues upward. Use when already holding LONG and bullish consensus. Parameters: amount_percent (0.1-0.3), reasoning (string), confidence (0-100)",
            func=self._execute_add_to_long,
            parameters_schema={
                "type": "object",
                "properties": {
                    "amount_percent": {"type": "number", "description": "Additional position size as % of available margin (0.1-0.3)", "default": 0.15},
                    "reasoning": {"type": "string", "description": "Reason for adding to position"},
                    "confidence": {"type": "integer", "description": "Confidence level 0-100", "default": 70}
                },
                "required": ["reasoning"]
            }
        ))
        
        # add_to_short tool (NEW - position management)
        self.register_tool(FunctionTool(
            name="add_to_short",
            description="Add to existing SHORT position when trend continues downward. Use when already holding SHORT and bearish consensus. Parameters: amount_percent (0.1-0.3), reasoning (string), confidence (0-100)",
            func=self._execute_add_to_short,
            parameters_schema={
                "type": "object",
                "properties": {
                    "amount_percent": {"type": "number", "description": "Additional position size as % of available margin (0.1-0.3)", "default": 0.15},
                    "reasoning": {"type": "string", "description": "Reason for adding to position"},
                    "confidence": {"type": "integer", "description": "Confidence level 0-100", "default": 70}
                },
                "required": ["reasoning"]
            }
        ))
        
        # reduce_position tool (NEW - position management)
        self.register_tool(FunctionTool(
            name="reduce_position",
            description="Partially close existing position to lock in profits or reduce risk. Parameters: reduce_percent (0.25-0.75), reasoning (string), confidence (0-100)",
            func=self._execute_reduce_position,
            parameters_schema={
                "type": "object",
                "properties": {
                    "reduce_percent": {"type": "number", "description": "Percentage of position to close (0.25-0.75)", "default": 0.5},
                    "reasoning": {"type": "string", "description": "Reason for reducing position"},
                    "confidence": {"type": "integer", "description": "Confidence level 0-100", "default": 75}
                },
                "required": ["reasoning"]
            }
        ))
    
    async def execute(
        self,
        leader_summary: str,
        agent_votes: List[Dict],
        position_context: Dict,
        trigger_reason: str = None
    ) -> TradingSignal:
        """
        Execute trading decision based on meeting results.
        
        Uses ReWOOAgent's analyze_with_rewoo for the same 3-phase workflow
        as other analysis agents.
        
        Args:
            leader_summary: Leader's summary of the meeting discussion
            agent_votes: List of agent votes with direction, confidence, reasoning
            position_context: Current position state
            trigger_reason: Why this analysis was triggered
            
        Returns:
            TradingSignal with the final decision
        """
        self._result = {"signal": None}
        self._executed_tools = []
        
        logger.info("[ExecutorAgent] Starting execution phase (ReWOO pattern)...")
        
        # Store context for decision saving
        self._current_context = {
            "leader_summary": leader_summary,
            "agent_votes": agent_votes,
            "position_context": position_context,
            "trigger_reason": trigger_reason or "scheduled"
        }
        
        # Build query for ReWOO analysis (with async funding context)
        query = await self._build_execution_query(
            leader_summary=leader_summary,
            agent_votes=agent_votes,
            position_context=position_context
        )
        
        # Retry parameters for LLM instability
        max_attempts = 2
        
        for attempt in range(1, max_attempts + 1):
            try:
                # Reset result for each attempt
                self._result = {"signal": None}
                self._executed_tools = []
                
                if attempt > 1:
                    logger.info(f"[ExecutorAgent] ⟳ Retry attempt {attempt}/{max_attempts}...")
                
                # Use ReWOO 3-phase analysis (inherited from ReWOOAgent)
                result = await self.analyze_with_rewoo(query, self._current_context)
                
                # Check if we got a signal from tool execution
                if self._result.get("signal"):
                    signal = self._result["signal"]
                    logger.info(f"[ExecutorAgent] ✅ Execution complete: {signal.direction.upper()}")
                    # Save decision to Redis
                    await self._save_decision(signal)
                    return signal
                
                # If no tool was called, try to parse decision from result text
                if result:
                    signal = self._parse_decision_from_text(result, position_context)
                    if signal:
                        await self._save_decision(signal)
                        return signal
                
                # No signal generated - retry if attempts remaining
                if attempt < max_attempts:
                    logger.warning(f"[ExecutorAgent] No signal on attempt {attempt}, retrying...")
                    continue
                
                # All retries exhausted - fallback to HOLD
                logger.warning("[ExecutorAgent] No signal generated after all attempts, defaulting to HOLD")
                signal = await self._generate_hold_signal("No tool call made after retries, defaulting to HOLD")
                await self._save_decision(signal)
                return signal
                    
            except Exception as e:
                logger.error(f"[ExecutorAgent] Execution failed on attempt {attempt}: {e}")
                if attempt < max_attempts:
                    logger.info(f"[ExecutorAgent] Retrying after exception...")
                    continue
                    
                import traceback
                traceback.print_exc()
                signal = await self._generate_hold_signal(f"Execution error: {str(e)}")
                await self._save_decision(signal)
                return signal
        
        # Should not reach here, but fallback just in case
        signal = await self._generate_hold_signal("Unexpected fallback")
        await self._save_decision(signal)
        return signal
    
    async def _save_decision(self, signal: TradingSignal):
        """
        Save trading decision to Redis for frontend persistence.
        
        This allows the frontend to display recent decisions after page refresh.
        """
        try:
            if not self._current_context:
                logger.warning("[ExecutorAgent] No context available for saving decision")
                return
            
            decision = TradingDecision(
                trade_id=str(uuid.uuid4()),
                timestamp=signal.timestamp or datetime.now(),
                trigger_reason=self._current_context.get("trigger_reason", "scheduled"),
                direction=signal.direction,
                confidence=signal.confidence or 0,
                leverage=signal.leverage or 1,
                reasoning=signal.reasoning or "",
                entry_price=signal.entry_price or 0.0,
                tp_price=signal.take_profit_price or 0.0,
                sl_price=signal.stop_loss_price or 0.0,
                amount_percent=signal.amount_percent or 0.0,
                leader_summary=self._current_context.get("leader_summary", ""),
                agent_votes=self._current_context.get("agent_votes", []),
                position_context=self._current_context.get("position_context", {}),
                was_executed=True,
            )
            
            await self._decision_store.save_decision(decision)
            logger.info(f"[ExecutorAgent] 💾 Decision saved to Redis: {decision.trade_id[:8]}...")
            
        except Exception as e:
            logger.error(f"[ExecutorAgent] Failed to save decision: {e}")
            # Non-fatal - continue even if save fails
    
    async def _build_execution_query(
        self,
        leader_summary: str,
        agent_votes: List[Dict],
        position_context: Dict
    ) -> str:
        """Build the execution query for ReWOO analysis with funding fee context."""
        
        # Format votes
        votes_text = self._format_votes(agent_votes)
        
        # Format position context
        position_text = self._format_position_context(position_context)
        
        # Get funding fee context (async)
        funding_context = await self._get_funding_context(position_context)
        
        return f"""# Trading Execution Decision

## Leader's Summary
{leader_summary}

## Agent Votes Summary
{votes_text}

## Current Position
{position_text}

{funding_context}

## Your Task
Based on the above information (especially funding fee costs), make a trading decision by calling ONE of the available tools:
- open_long: Open a LONG position
- open_short: Open a SHORT position
- hold: Maintain current state, no action
- close_position: Close existing position

You MUST call exactly one tool to make your decision. Consider funding fee impact when holding positions.
Analyze the consensus and make a decisive action."""
    
    def _format_votes(self, agent_votes: List[Dict]) -> str:
        """Format agent votes for the prompt."""
        if not agent_votes:
            return "No votes available."
        
        lines = []
        for vote in agent_votes:
            agent = vote.get('agent_id', 'Unknown')
            direction = vote.get('direction') or 'unknown'  # Defensive check for None
            confidence = vote.get('confidence', 0)
            reasoning = (vote.get('reasoning') or '')[:100]
            lines.append(f"- {agent}: {direction.upper()} ({confidence}%) - {reasoning}")
        
        return "\n".join(lines)
    
    def _format_position_context(self, context: Dict) -> str:
        """Format position context for prompt."""
        if not context or not context.get("has_position"):
            return "No active position."
        
        direction = context.get('direction') or 'unknown'  # Defensive check for None
        return f"""- Direction: {direction.upper()}
- Entry Price: ${context.get('entry_price', 0):,.2f}
- Current Price: ${context.get('current_price', 0):,.2f}
- Unrealized PnL: ${context.get('unrealized_pnl', 0):,.2f} ({context.get('unrealized_pnl_percent', 0):+.1f}%)
- Leverage: {context.get('leverage', 1)}x"""
    
    def _parse_decision_from_text(self, result: str, position_context: Dict) -> Optional[TradingSignal]:
        """Try to parse trading decision from text if no tool was called."""
        result_lower = result.lower()
        
        # Look for clear decision indicators
        if "hold" in result_lower and ("recommend" in result_lower or "decision" in result_lower):
            return None  # Let it fall through to fallback HOLD
        
        # More complex parsing could be added here
        return None
    
    # ==================== Tool Implementation Methods ====================
    
    async def _get_position_info(self) -> Dict[str, Any]:
        """Get current position information from paper_trader."""
        if not self.paper_trader:
            return {"has_position": False}
        
        try:
            position = await self.paper_trader.get_position(self.symbol)
            if position and position.get("direction") and position.get("direction") != "none":
                return {
                    "has_position": True,
                    "direction": position.get("direction", "none"),
                    "entry_price": position.get("entry_price", 0),
                    "size": position.get("size", 0),
                    "margin": position.get("margin", 0),
                    "unrealized_pnl": position.get("unrealized_pnl", 0),
                    "leverage": position.get("leverage", 1),
                    "liquidation_price": position.get("liquidation_price", 0),
                }
            return {"has_position": False}
        except Exception as e:
            logger.warning(f"[ExecutorAgent] Failed to get position: {e}")
            return {"has_position": False}
    
    async def _get_available_margin(self) -> float:
        """Get available margin for trading (considers unrealized PnL)."""
        if not self.paper_trader:
            return 0.0
        
        try:
            status = await self.paper_trader.get_status()
            available = status.get("available_balance", 0)
            unrealized_pnl = status.get("unrealized_pnl", 0)
            # True available = available + unrealized (since closing would realize it)
            true_available = available + max(unrealized_pnl, 0)
            return true_available
        except Exception as e:
            logger.warning(f"[ExecutorAgent] Failed to get margin: {e}")
            return 0.0
    
    def _validate_stop_loss(self, direction: str, entry_price: float, sl_price: float,
                            leverage: int, margin: float) -> tuple:
        """
        Validate stop loss is safe (triggers before liquidation).
        Returns (is_safe, message, safe_sl_price)
        """
        if entry_price <= 0 or margin <= 0 or leverage <= 0:
            return True, "", sl_price
        
        size = (margin * leverage) / entry_price
        if size <= 0:
            return True, "", sl_price
        
        liquidation_loss = margin * 0.8  # 80% margin loss = liquidation
        
        if direction == "long":
            liquidation_price = entry_price - (liquidation_loss / size)
            if sl_price <= liquidation_price:
                # Calculate safe SL (5% above liquidation)
                safe_sl = liquidation_price * 1.05
                return False, f"SL ${sl_price:.2f} below liquidation ${liquidation_price:.2f}", safe_sl
        else:  # short
            liquidation_price = entry_price + (liquidation_loss / size)
            if sl_price >= liquidation_price:
                safe_sl = liquidation_price * 0.95
                return False, f"SL ${sl_price:.2f} above liquidation ${liquidation_price:.2f}", safe_sl
        
        return True, "", sl_price
    
    async def _execute_open_long(
        self,
        leverage: int = 5,
        amount_percent: float = 0.2,
        tp_percent: float = 8.0,
        sl_percent: float = 3.0,
        reasoning: str = "",
        confidence: int = 70
    ) -> Dict[str, Any]:
        """
        Execute open_long with full scenario logic:
        - Scenario 1: Already LONG → add to position or maintain
        - Scenario 2: Currently SHORT → close short, then open long
        - Scenario 3: No position → open new long
        """
        logger.info(f"[ExecutorAgent] Executing: open_long(leverage={leverage}, confidence={confidence})")
        
        current_price = await get_current_btc_price()
        position = await self._get_position_info()
        available_margin = await self._get_available_margin()
        
        tp_price = current_price * (1 + tp_percent / 100)
        sl_price = current_price * (1 - sl_percent / 100)
        
        action_taken = "open_long"
        trade_result = None
        
        # Scenario 1: Already holding LONG
        if position.get("has_position") and position.get("direction") == "long":
            logger.info("[ExecutorAgent] Already holding LONG - will add to position if possible")
            # This is essentially an add_to operation
            can_add = available_margin > self.SAFETY_BUFFER + self.MIN_ADD_AMOUNT
            
            if can_add and self.paper_trader:
                add_amount = min(
                    available_margin * amount_percent,
                    available_margin - self.SAFETY_BUFFER
                )
                add_amount = max(add_amount, 0)
                
                if add_amount >= self.MIN_ADD_AMOUNT:
                    # Validate stop loss
                    is_safe, msg, safe_sl = self._validate_stop_loss("long", current_price, sl_price, leverage, add_amount)
                    if not is_safe:
                        logger.warning(f"[ExecutorAgent] {msg}, adjusting SL to ${safe_sl:.2f}")
                        sl_price = safe_sl
                    
                    trade_result = await self.paper_trader.open_long(
                        symbol=self.symbol,
                        leverage=leverage,
                        amount_usdt=add_amount,
                        tp_price=tp_price,
                        sl_price=sl_price
                    )
                    action_taken = "add_to_long"
                    logger.info(f"[ExecutorAgent] ✅ Added ${add_amount:.2f} to long position")
                else:
                    action_taken = "maintain_long_small_amount"
                    logger.info("[ExecutorAgent] Add amount too small, maintaining position")
            else:
                action_taken = "maintain_long_full"
                logger.info("[ExecutorAgent] Cannot add (margin limit), maintaining position")
        
        # Scenario 2: Currently SHORT → close then open long
        elif position.get("has_position") and position.get("direction") == "short":
            logger.info("[ExecutorAgent] 🔄 Reversing: close SHORT → open LONG")
            if self.paper_trader:
                # Close short first
                close_result = await self.paper_trader.close_position(symbol=self.symbol)
                if close_result.get("success"):
                    logger.info("[ExecutorAgent] ✅ Closed short position")
                    # Now open long
                    amount_usdt = min(available_margin * amount_percent, available_margin - self.SAFETY_BUFFER)
                    trade_result = await self.paper_trader.open_long(
                        symbol=self.symbol,
                        leverage=leverage,
                        amount_usdt=amount_usdt,
                        tp_price=tp_price,
                        sl_price=sl_price
                    )
                    action_taken = "reverse_short_to_long"
                else:
                    action_taken = "close_short_failed"
                    logger.error(f"[ExecutorAgent] Failed to close short: {close_result.get('error')}")
        
        # Scenario 3: No position → new long
        else:
            logger.info("[ExecutorAgent] No position, opening new LONG")
            if self.paper_trader:
                amount_usdt = min(available_margin * amount_percent, available_margin - self.SAFETY_BUFFER)
                amount_usdt = max(amount_usdt, 0)
                
                if amount_usdt >= self.MIN_ADD_AMOUNT:
                    # Validate stop loss
                    is_safe, msg, safe_sl = self._validate_stop_loss("long", current_price, sl_price, leverage, amount_usdt)
                    if not is_safe:
                        logger.warning(f"[ExecutorAgent] {msg}, adjusting SL to ${safe_sl:.2f}")
                        sl_price = safe_sl
                    
                    trade_result = await self.paper_trader.open_long(
                        symbol=self.symbol,
                        leverage=leverage,
                        amount_usdt=amount_usdt,
                        tp_price=tp_price,
                        sl_price=sl_price
                    )
                    action_taken = "new_long"
                else:
                    action_taken = "insufficient_margin"
                    logger.warning(f"[ExecutorAgent] Insufficient margin: ${amount_usdt:.2f}")
        
        # Create signal for record-keeping
        entry_price = trade_result.get("executed_price", current_price) if trade_result else current_price
        signal = TradingSignal(
            direction="long",
            symbol=self.symbol,
            leverage=min(leverage, 20),
            amount_percent=min(amount_percent, 0.3),
            entry_price=entry_price,
            take_profit_price=tp_price,
            stop_loss_price=sl_price,
            confidence=confidence,
            reasoning=f"[{action_taken}] {reasoning}",
            timestamp=datetime.now()
        )
        
        self._result["signal"] = signal
        self._executed_tools.append({
            "tool": "open_long",
            "action_taken": action_taken,
            "trade_result": trade_result,
            "success": trade_result.get("success", False) if trade_result else ("maintain" in action_taken or "insufficient" in action_taken)
        })
        
        return {
            "success": True,
            "action": action_taken,
            "price": current_price,
            "leverage": leverage,
            "confidence": confidence,
            "reasoning": reasoning,
            "trade_result": trade_result
        }
    
    async def _execute_open_short(
        self,
        leverage: int = 5,
        amount_percent: float = 0.2,
        tp_percent: float = 8.0,
        sl_percent: float = 3.0,
        reasoning: str = "",
        confidence: int = 70
    ) -> Dict[str, Any]:
        """
        Execute open_short with full scenario logic:
        - Scenario 1: Already SHORT → add to position or maintain
        - Scenario 2: Currently LONG → close long, then open short
        - Scenario 3: No position → open new short
        """
        logger.info(f"[ExecutorAgent] Executing: open_short(leverage={leverage}, confidence={confidence})")
        
        current_price = await get_current_btc_price()
        position = await self._get_position_info()
        available_margin = await self._get_available_margin()
        
        tp_price = current_price * (1 - tp_percent / 100)
        sl_price = current_price * (1 + sl_percent / 100)
        
        action_taken = "open_short"
        trade_result = None
        
        # Scenario 1: Already holding SHORT
        if position.get("has_position") and position.get("direction") == "short":
            logger.info("[ExecutorAgent] Already holding SHORT - will add to position if possible")
            can_add = available_margin > self.SAFETY_BUFFER + self.MIN_ADD_AMOUNT
            
            if can_add and self.paper_trader:
                add_amount = min(
                    available_margin * amount_percent,
                    available_margin - self.SAFETY_BUFFER
                )
                add_amount = max(add_amount, 0)
                
                if add_amount >= self.MIN_ADD_AMOUNT:
                    is_safe, msg, safe_sl = self._validate_stop_loss("short", current_price, sl_price, leverage, add_amount)
                    if not is_safe:
                        logger.warning(f"[ExecutorAgent] {msg}, adjusting SL to ${safe_sl:.2f}")
                        sl_price = safe_sl
                    
                    trade_result = await self.paper_trader.open_short(
                        symbol=self.symbol,
                        leverage=leverage,
                        amount_usdt=add_amount,
                        tp_price=tp_price,
                        sl_price=sl_price
                    )
                    action_taken = "add_to_short"
                    logger.info(f"[ExecutorAgent] ✅ Added ${add_amount:.2f} to short position")
                else:
                    action_taken = "maintain_short_small_amount"
                    logger.info("[ExecutorAgent] Add amount too small, maintaining position")
            else:
                action_taken = "maintain_short_full"
                logger.info("[ExecutorAgent] Cannot add (margin limit), maintaining position")
        
        # Scenario 2: Currently LONG → close then open short
        elif position.get("has_position") and position.get("direction") == "long":
            logger.info("[ExecutorAgent] 🔄 Reversing: close LONG → open SHORT")
            if self.paper_trader:
                close_result = await self.paper_trader.close_position(symbol=self.symbol)
                if close_result.get("success"):
                    logger.info("[ExecutorAgent] ✅ Closed long position")
                    amount_usdt = min(available_margin * amount_percent, available_margin - self.SAFETY_BUFFER)
                    trade_result = await self.paper_trader.open_short(
                        symbol=self.symbol,
                        leverage=leverage,
                        amount_usdt=amount_usdt,
                        tp_price=tp_price,
                        sl_price=sl_price
                    )
                    action_taken = "reverse_long_to_short"
                else:
                    action_taken = "close_long_failed"
                    logger.error(f"[ExecutorAgent] Failed to close long: {close_result.get('error')}")
        
        # Scenario 3: No position → new short
        else:
            logger.info("[ExecutorAgent] No position, opening new SHORT")
            if self.paper_trader:
                amount_usdt = min(available_margin * amount_percent, available_margin - self.SAFETY_BUFFER)
                amount_usdt = max(amount_usdt, 0)
                
                if amount_usdt >= self.MIN_ADD_AMOUNT:
                    is_safe, msg, safe_sl = self._validate_stop_loss("short", current_price, sl_price, leverage, amount_usdt)
                    if not is_safe:
                        logger.warning(f"[ExecutorAgent] {msg}, adjusting SL to ${safe_sl:.2f}")
                        sl_price = safe_sl
                    
                    trade_result = await self.paper_trader.open_short(
                        symbol=self.symbol,
                        leverage=leverage,
                        amount_usdt=amount_usdt,
                        tp_price=tp_price,
                        sl_price=sl_price
                    )
                    action_taken = "new_short"
                else:
                    action_taken = "insufficient_margin"
                    logger.warning(f"[ExecutorAgent] Insufficient margin: ${amount_usdt:.2f}")
        
        entry_price = trade_result.get("executed_price", current_price) if trade_result else current_price
        signal = TradingSignal(
            direction="short",
            symbol=self.symbol,
            leverage=min(leverage, 20),
            amount_percent=min(amount_percent, 0.3),
            entry_price=entry_price,
            take_profit_price=tp_price,
            stop_loss_price=sl_price,
            confidence=confidence,
            reasoning=f"[{action_taken}] {reasoning}",
            timestamp=datetime.now()
        )
        
        self._result["signal"] = signal
        self._executed_tools.append({
            "tool": "open_short",
            "action_taken": action_taken,
            "trade_result": trade_result,
            "success": trade_result.get("success", False) if trade_result else ("maintain" in action_taken or "insufficient" in action_taken)
        })
        
        return {
            "success": True,
            "action": action_taken,
            "price": current_price,
            "leverage": leverage,
            "confidence": confidence,
            "reasoning": reasoning,
            "trade_result": trade_result
        }
    
    async def _execute_hold(
        self,
        reason: str = "",
        confidence: int = 50
    ) -> Dict[str, Any]:
        """Execute hold tool."""
        logger.info(f"[ExecutorAgent] Executing: hold(reason={reason[:50]}...)")
        
        current_price = await get_current_btc_price()
        
        signal = TradingSignal(
            direction="hold",
            symbol=self.symbol,
            leverage=1,
            amount_percent=0.0,
            entry_price=current_price,
            take_profit_price=current_price,
            stop_loss_price=current_price,
            confidence=confidence,
            reasoning=reason,
            timestamp=datetime.now()
        )
        
        self._result["signal"] = signal
        
        return {
            "success": True,
            "action": "hold",
            "price": current_price,
            "confidence": confidence,
            "reasoning": reason
        }
    
    async def _execute_close_position(
        self,
        reason: str = "",
        confidence: int = 100
    ) -> Dict[str, Any]:
        """Execute close_position tool - directly calls paper_trader."""
        logger.info(f"[ExecutorAgent] Executing: close_position(reason={reason[:50]}...)")
        
        current_price = await get_current_btc_price()
        trade_result = None
        action_taken = "close_position"
        
        # Check if we have a position to close
        position = await self._get_position_info()
        
        if position.get("has_position") and self.paper_trader:
            trade_result = await self.paper_trader.close_position(symbol=self.symbol)
            if trade_result.get("success"):
                logger.info(f"[ExecutorAgent] ✅ Closed {position.get('direction')} position")
                action_taken = f"closed_{position.get('direction')}"
            else:
                logger.error(f"[ExecutorAgent] ❌ Failed to close: {trade_result.get('error')}")
                action_taken = "close_failed"
        else:
            logger.info("[ExecutorAgent] No position to close")
            action_taken = "no_position"
        
        signal = TradingSignal(
            direction="close",
            symbol=self.symbol,
            leverage=1,
            amount_percent=0.0,
            entry_price=current_price,
            take_profit_price=current_price,
            stop_loss_price=current_price,
            confidence=confidence,
            reasoning=f"[{action_taken}] {reason}",
            timestamp=datetime.now()
        )
        
        self._result["signal"] = signal
        self._executed_tools.append({
            "tool": "close_position",
            "action_taken": action_taken,
            "trade_result": trade_result,
            "success": trade_result.get("success", False) if trade_result else action_taken == "no_position"
        })
        
        return {
            "success": True,
            "action": action_taken,
            "price": current_price,
            "confidence": confidence,
            "reasoning": reason,
            "trade_result": trade_result
        }
    
    async def _generate_hold_signal(self, reason: str) -> TradingSignal:
        """Generate a fallback HOLD signal."""
        current_price = await get_current_btc_price()
        
        return TradingSignal(
            direction="hold",
            symbol=self.symbol,
            leverage=1,
            amount_percent=0.0,
            entry_price=current_price,
            take_profit_price=current_price,
            stop_loss_price=current_price,
            confidence=0,
            reasoning=f"Fallback HOLD: {reason}",
            timestamp=datetime.now()
        )
    
    # ==================== New Position Management Methods ====================
    
    async def _execute_add_to_long(
        self,
        amount_percent: float = 0.15,
        reasoning: str = "",
        confidence: int = 70
    ) -> Dict[str, Any]:
        """
        Execute add_to_long tool - add to existing LONG position with safety checks.
        Directly calls paper_trader.open_long() to add to position.
        """
        logger.info(f"[ExecutorAgent] Executing: add_to_long(amount_percent={amount_percent}, confidence={confidence})")
        
        current_price = await get_current_btc_price()
        position = await self._get_position_info()
        available_margin = await self._get_available_margin()
        
        trade_result = None
        action_taken = "add_to_long"
        
        # Verify we're holding a LONG position
        if not position.get("has_position"):
            logger.warning("[ExecutorAgent] add_to_long called but no position exists")
            action_taken = "no_position_to_add"
        elif position.get("direction") != "long":
            logger.warning(f"[ExecutorAgent] add_to_long called but holding {position.get('direction')}")
            action_taken = "wrong_direction"
        elif not self.paper_trader:
            logger.warning("[ExecutorAgent] No paper_trader available")
            action_taken = "no_trader"
        else:
            # Check if we can add
            can_add = available_margin > self.SAFETY_BUFFER + self.MIN_ADD_AMOUNT
            
            if can_add:
                add_amount = min(
                    available_margin * amount_percent,
                    available_margin - self.SAFETY_BUFFER
                )
                add_amount = max(add_amount, 0)
                
                if add_amount >= self.MIN_ADD_AMOUNT:
                    leverage = position.get("leverage", 5)
                    tp_price = current_price * 1.08
                    sl_price = current_price * 0.97
                    
                    # Validate stop loss
                    is_safe, msg, safe_sl = self._validate_stop_loss("long", current_price, sl_price, leverage, add_amount)
                    if not is_safe:
                        logger.warning(f"[ExecutorAgent] {msg}")
                        sl_price = safe_sl
                    
                    trade_result = await self.paper_trader.open_long(
                        symbol=self.symbol,
                        leverage=leverage,
                        amount_usdt=add_amount,
                        tp_price=tp_price,
                        sl_price=sl_price
                    )
                    
                    if trade_result.get("success"):
                        logger.info(f"[ExecutorAgent] ✅ Added ${add_amount:.2f} to long position")
                        action_taken = "added_to_long"
                    else:
                        logger.error(f"[ExecutorAgent] Add failed: {trade_result.get('error')}")
                        action_taken = "add_failed"
                else:
                    action_taken = "amount_too_small"
                    logger.info(f"[ExecutorAgent] Add amount ${add_amount:.2f} too small")
            else:
                action_taken = "insufficient_margin"
                logger.info("[ExecutorAgent] Insufficient margin to add position")
        
        signal = TradingSignal(
            direction="add_long",
            symbol=self.symbol,
            leverage=position.get("leverage", 5) if position.get("has_position") else 5,
            amount_percent=min(amount_percent, 0.3),
            entry_price=trade_result.get("executed_price", current_price) if trade_result else current_price,
            take_profit_price=current_price * 1.08,
            stop_loss_price=current_price * 0.97,
            confidence=confidence,
            reasoning=f"[{action_taken}] {reasoning}",
            timestamp=datetime.now()
        )
        
        self._result["signal"] = signal
        self._executed_tools.append({
            "tool": "add_to_long",
            "action_taken": action_taken,
            "trade_result": trade_result,
            "success": trade_result.get("success", False) if trade_result else False
        })
        
        return {
            "success": action_taken == "added_to_long",
            "action": action_taken,
            "price": current_price,
            "confidence": confidence,
            "reasoning": reasoning,
            "trade_result": trade_result
        }
    
    async def _execute_add_to_short(
        self,
        amount_percent: float = 0.15,
        reasoning: str = "",
        confidence: int = 70
    ) -> Dict[str, Any]:
        """
        Execute add_to_short tool - add to existing SHORT position with safety checks.
        Directly calls paper_trader.open_short() to add to position.
        """
        logger.info(f"[ExecutorAgent] Executing: add_to_short(amount_percent={amount_percent}, confidence={confidence})")
        
        current_price = await get_current_btc_price()
        position = await self._get_position_info()
        available_margin = await self._get_available_margin()
        
        trade_result = None
        action_taken = "add_to_short"
        
        # Verify we're holding a SHORT position
        if not position.get("has_position"):
            logger.warning("[ExecutorAgent] add_to_short called but no position exists")
            action_taken = "no_position_to_add"
        elif position.get("direction") != "short":
            logger.warning(f"[ExecutorAgent] add_to_short called but holding {position.get('direction')}")
            action_taken = "wrong_direction"
        elif not self.paper_trader:
            logger.warning("[ExecutorAgent] No paper_trader available")
            action_taken = "no_trader"
        else:
            can_add = available_margin > self.SAFETY_BUFFER + self.MIN_ADD_AMOUNT
            
            if can_add:
                add_amount = min(
                    available_margin * amount_percent,
                    available_margin - self.SAFETY_BUFFER
                )
                add_amount = max(add_amount, 0)
                
                if add_amount >= self.MIN_ADD_AMOUNT:
                    leverage = position.get("leverage", 5)
                    tp_price = current_price * 0.92
                    sl_price = current_price * 1.03
                    
                    is_safe, msg, safe_sl = self._validate_stop_loss("short", current_price, sl_price, leverage, add_amount)
                    if not is_safe:
                        logger.warning(f"[ExecutorAgent] {msg}")
                        sl_price = safe_sl
                    
                    trade_result = await self.paper_trader.open_short(
                        symbol=self.symbol,
                        leverage=leverage,
                        amount_usdt=add_amount,
                        tp_price=tp_price,
                        sl_price=sl_price
                    )
                    
                    if trade_result.get("success"):
                        logger.info(f"[ExecutorAgent] ✅ Added ${add_amount:.2f} to short position")
                        action_taken = "added_to_short"
                    else:
                        logger.error(f"[ExecutorAgent] Add failed: {trade_result.get('error')}")
                        action_taken = "add_failed"
                else:
                    action_taken = "amount_too_small"
            else:
                action_taken = "insufficient_margin"
        
        signal = TradingSignal(
            direction="add_short",
            symbol=self.symbol,
            leverage=position.get("leverage", 5) if position.get("has_position") else 5,
            amount_percent=min(amount_percent, 0.3),
            entry_price=trade_result.get("executed_price", current_price) if trade_result else current_price,
            take_profit_price=current_price * 0.92,
            stop_loss_price=current_price * 1.03,
            confidence=confidence,
            reasoning=f"[{action_taken}] {reasoning}",
            timestamp=datetime.now()
        )
        
        self._result["signal"] = signal
        self._executed_tools.append({
            "tool": "add_to_short",
            "action_taken": action_taken,
            "trade_result": trade_result,
            "success": trade_result.get("success", False) if trade_result else False
        })
        
        return {
            "success": action_taken == "added_to_short",
            "action": action_taken,
            "price": current_price,
            "confidence": confidence,
            "reasoning": reasoning,
            "trade_result": trade_result
        }
    
    async def _execute_reduce_position(
        self,
        reduce_percent: float = 0.5,
        reasoning: str = "",
        confidence: int = 75
    ) -> Dict[str, Any]:
        """
        Execute reduce_position tool - partially close existing position.
        Directly calls paper_trader to reduce position size.
        """
        logger.info(f"[ExecutorAgent] Executing: reduce_position(reduce_percent={reduce_percent}, confidence={confidence})")
        
        current_price = await get_current_btc_price()
        position = await self._get_position_info()
        
        reduce_percent = max(0.25, min(reduce_percent, 0.75))
        trade_result = None
        action_taken = "reduce_position"
        
        if not position.get("has_position"):
            logger.warning("[ExecutorAgent] No position to reduce")
            action_taken = "no_position"
        elif not self.paper_trader:
            logger.warning("[ExecutorAgent] No paper_trader available")
            action_taken = "no_trader"
        else:
            # Calculate amount to close
            current_margin = position.get("margin", 0)
            reduce_amount = current_margin * reduce_percent
            
            if reduce_amount > 0:
                # Close partial position
                trade_result = await self.paper_trader.close_position(
                    symbol=self.symbol,
                    partial=True,
                    reduce_percent=reduce_percent
                )
                
                if trade_result.get("success"):
                    logger.info(f"[ExecutorAgent] ✅ Reduced position by {reduce_percent*100:.0f}%")
                    action_taken = f"reduced_{position.get('direction')}_{reduce_percent*100:.0f}p"
                else:
                    # Fallback to full close if partial not supported
                    logger.warning("[ExecutorAgent] Partial close not supported, closing full position")
                    trade_result = await self.paper_trader.close_position(symbol=self.symbol)
                    action_taken = "closed_full"
            else:
                action_taken = "nothing_to_reduce"
        
        signal = TradingSignal(
            direction="reduce",
            symbol=self.symbol,
            leverage=1,
            amount_percent=reduce_percent,
            entry_price=current_price,
            take_profit_price=current_price,
            stop_loss_price=current_price,
            confidence=confidence,
            reasoning=f"[{action_taken}] {reasoning}",
            timestamp=datetime.now()
        )
        
        self._result["signal"] = signal
        self._executed_tools.append({
            "tool": "reduce_position",
            "action_taken": action_taken,
            "reduce_percent": reduce_percent,
            "trade_result": trade_result,
            "success": trade_result.get("success", False) if trade_result else action_taken == "no_position"
        })
        
        return {
            "success": "reduced" in action_taken or "closed" in action_taken,
            "action": action_taken,
            "reduce_percent": reduce_percent,
            "price": current_price,
            "confidence": confidence,
            "reasoning": reasoning,
            "trade_result": trade_result
        }

    # ==================== Funding Fee Methods ====================
    
    def _setup_funding_monitor(self):
        """Setup funding impact monitor with force-close callback."""
        try:
            monitor = get_funding_impact_monitor()
            
            # Register callback for force closing positions
            async def force_close_callback(symbol: str, reason: str) -> Dict:
                """Callback to force close position when funding impact exceeds threshold."""
                if self.paper_trader:
                    logger.warning(f"[ExecutorAgent] 🚨 Force closing position: {reason}")
                    return await self.paper_trader.close_position(symbol=symbol, reason=reason)
                return {"success": False, "error": "No paper trader available"}
            
            monitor.register_close_callback(force_close_callback)
            logger.info("[ExecutorAgent] ✅ Funding impact monitor callback registered")
            
        except Exception as e:
            logger.warning(f"[ExecutorAgent] Failed to setup funding monitor: {e}")
    
    async def _get_funding_context(self, position_context: Dict) -> str:
        """
        Get funding fee context for execution query.
        
        Args:
            position_context: Current position information
            
        Returns:
            Formatted funding fee context string
        """
        try:
            # Determine expected direction from position context
            has_position = position_context.get('has_position', False)
            current_direction = position_context.get('direction', None)
            leverage = position_context.get('leverage', 3)
            
            # For new positions, default to long for context calculation
            direction = current_direction if current_direction else "long"
            
            # Get funding context provider
            context_provider = await get_funding_context_provider()
            
            # Generate context with expected parameters
            funding_context = await context_provider.generate_context(
                symbol=self.symbol,
                direction=direction,
                leverage=leverage,
                expected_holding_hours=24,  # Default 24h analysis
                margin=position_context.get('margin', 100.0)
            )
            
            return funding_context
            
        except Exception as e:
            logger.warning(f"[ExecutorAgent] Failed to get funding context: {e}")
            return "## ⚠️ 资金费率状态\n\n无法获取资金费率数据，请谨慎考虑持仓成本。"
    
    async def _check_entry_timing(self, direction: str) -> Dict[str, Any]:
        """
        Check if entry timing is optimal based on funding settlement.
        
        Args:
            direction: Position direction ("long" or "short")
            
        Returns:
            Dict with should_delay, wait_minutes, reason
        """
        try:
            data_service = await get_funding_data_service()
            funding_rate = await data_service.get_current_rate(self.symbol)
            
            if not funding_rate:
                return {"should_delay": False, "reason": "Unable to fetch funding rate"}
            
            timing_controller = get_entry_timing_controller()
            decision = timing_controller.should_delay_entry(direction, funding_rate)
            
            return {
                "should_delay": decision.action == EntryAction.DELAY,
                "wait_minutes": decision.minutes_to_wait,
                "reason": decision.reason,
                "action": decision.action.value
            }
            
        except Exception as e:
            logger.warning(f"[ExecutorAgent] Entry timing check failed: {e}")
            return {"should_delay": False, "reason": f"Error: {str(e)}"}
    
    async def _evaluate_trade_viability(
        self,
        direction: str,
        expected_profit_percent: float = 5.0,
        holding_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Evaluate if trade is viable considering funding costs.
        
        Args:
            direction: Position direction
            expected_profit_percent: Expected profit as % of margin
            holding_hours: Expected holding duration
            
        Returns:
            Dict with viability assessment
        """
        try:
            data_service = await get_funding_data_service()
            funding_rate = await data_service.get_current_rate(self.symbol)
            
            if not funding_rate:
                return {"viable": True, "reason": "Unable to assess - defaulting to viable"}
            
            calculator = get_funding_calculator()
            
            # Get leverage from config
            leverage = self._position_context.get('leverage', EXECUTOR_CONFIG['max_leverage'])
            
            viability = calculator.evaluate_trade_viability(
                expected_profit_percent=expected_profit_percent,
                expected_holding_hours=holding_hours,
                funding_rate=funding_rate.rate,
                leverage=leverage,
                direction=direction
            )
            
            # Get optimal holding time
            holding_manager = get_holding_time_manager()
            optimal_hours = holding_manager.calculate_optimal_holding(
                expected_profit_percent=expected_profit_percent,
                funding_rate=funding_rate.rate,
                leverage=leverage,
                confidence=70,
                direction=direction
            )
            
            return {
                "viable": viability != TradeViability.NOT_VIABLE,
                "viability": viability.value,
                "optimal_holding_hours": optimal_hours,
                "funding_rate": funding_rate.rate_percent,
                "is_extreme": funding_rate.is_extreme
            }
            
        except Exception as e:
            logger.warning(f"[ExecutorAgent] Trade viability check failed: {e}")
            return {"viable": True, "reason": f"Error: {str(e)}"}

