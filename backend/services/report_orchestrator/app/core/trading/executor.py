"""
Trade Executor Module (DEPRECATED)

⚠️ DEPRECATION WARNING (2026-01-01):
This module is deprecated. Use ExecutorAgent instead:
    from app.core.trading.executor_agent import ExecutorAgent

ExecutorAgent inherits from ReWOOAgent and provides the same functionality
with a unified architecture. This file will be removed after 2026-01-15.

---
Original Description:
Standalone TradeExecutor class extracted from trading_meeting.py.
Responsible for making final trading decisions based on agent votes and market analysis.

Key Features:
- LLM-based decision making with tool calling
- Native tool_calls support (OpenAI format)
- Safety-first: text inference defaults to HOLD
- ReAct fallback capability
"""

import warnings
warnings.warn(
    "TradeExecutor is deprecated. Use ExecutorAgent from executor_agent.py instead. "
    "This module will be removed after 2026-01-15.",
    DeprecationWarning,
    stacklevel=2
)

import logging
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from app.models.trading_models import TradingSignal
from app.core.trading.price_service import get_current_btc_price
from app.core.trading.safety.guards import SafetyGuard, SafetyCheckResult

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
        signal = await executor.execute(
            leader_summary=summary,
            agent_votes=votes,
            position_context=context
        )
    """
    
    # Safety thresholds for confidence validation
    MIN_CONFIDENCE_OPEN = 65    # Minimum confidence to open new position  
    MIN_CONFIDENCE_CLOSE = 50   # Minimum confidence to close position
    
    def __init__(
        self,
        llm_service,
        toolkit=None,
        paper_trader=None,
        safety_guard: Optional[SafetyGuard] = None,
        on_message: Optional[Callable] = None,
        symbol: str = "BTC-USDT-SWAP"
    ):
        self.llm = llm_service
        self.toolkit = toolkit
        self.paper_trader = paper_trader
        self.safety_guard = safety_guard
        self.on_message = on_message
        self.symbol = symbol
        
        # Result container for tool execution
        self._result: Dict[str, Any] = {"signal": None}
        
        # Track executed tools for debugging
        self._executed_tools: List[Dict[str, Any]] = []
    
    async def execute(
        self,
        leader_summary: str,
        agent_votes: List[Dict],
        position_context: Dict,
        trigger_reason: str = None,
        enable_react_fallback: bool = True
    ) -> TradingSignal:
        """
        Execute trading decision based on meeting results.
        
        Args:
            leader_summary: Leader's summary of the meeting discussion
            agent_votes: List of agent votes with direction, confidence, reasoning
            position_context: Current position state
            trigger_reason: Why this analysis was triggered
            enable_react_fallback: Enable ReAct fallback on failure
            
        Returns:
            TradingSignal with the final decision
        """
        self._result = {"signal": None}
        self._executed_tools = []
        
        logger.info("[TradeExecutor] Starting execution phase...")
        
        # Build execution prompt
        prompt = self._build_execution_prompt(
            leader_summary=leader_summary,
            agent_votes=agent_votes,
            position_context=position_context
        )
        
        # Get trading tools
        tools = self._get_execution_tools()
        tools_dict = self._build_tools_dict()
        
        try:
            # Call LLM with tools
            response = await self._call_llm_with_tools(prompt, tools)
            
            # Parse and execute tool calls
            signal = await self._process_response(response, tools_dict)
            
            if signal:
                logger.info(f"[TradeExecutor] Decision: {signal.direction.upper()} | "
                           f"Confidence: {signal.confidence}% | Leverage: {signal.leverage}x")
                return signal
            
            # No tool executed - try ReAct fallback if enabled
            if enable_react_fallback:
                logger.warning("[TradeExecutor] No tool executed, triggering ReAct fallback...")
                return await self._react_fallback(
                    error="No tool call detected in LLM response",
                    agent_votes=agent_votes,
                    position_context=position_context,
                    tools_dict=tools_dict
                )
            
            # Fallback to HOLD if no tool was executed
            logger.warning("[TradeExecutor] No tool executed, defaulting to HOLD")
            return await self._generate_hold_signal("No trading tool executed")
            
        except Exception as e:
            logger.error(f"[TradeExecutor] Execution failed: {e}", exc_info=True)
            
            # Try ReAct fallback on exception
            if enable_react_fallback:
                logger.info("[TradeExecutor] Triggering ReAct fallback after exception...")
                return await self._react_fallback(
                    error=str(e),
                    agent_votes=agent_votes,
                    position_context=position_context,
                    tools_dict=tools_dict
                )
            
            return await self._generate_hold_signal(f"Execution error: {e}")
    
    async def _react_fallback(
        self,
        error: str,
        agent_votes: List[Dict],
        position_context: Dict,
        tools_dict: Dict,
        max_iterations: int = 3
    ) -> TradingSignal:
        """
        ReAct fallback: Reasoning-Action-Observation loop.
        
        When primary tool calling fails, use ReAct pattern to recover:
        1. REASON: Analyze the situation and error
        2. ACT: Choose and execute an action
        3. OBSERVE: Check the result
        4. Repeat until success or max iterations
        
        Args:
            error: The error that triggered fallback
            agent_votes: Agent votes for context
            position_context: Current position
            tools_dict: Available tools
            max_iterations: Max ReAct iterations
            
        Returns:
            TradingSignal from successful action or HOLD
        """
        logger.info(f"[ReAct] Starting fallback (max {max_iterations} iterations)")
        
        observations = [f"Previous execution failed: {error}"]
        
        for iteration in range(max_iterations):
            logger.info(f"[ReAct] Iteration {iteration + 1}/{max_iterations}")
            
            try:
                # Step 1: REASON - Analyze current state and decide action
                thought = await self._react_reason(observations, agent_votes, position_context)
                logger.info(f"[ReAct] Thought: {thought[:100]}...")
                
                # Step 2: ACT - Parse thought and execute action
                action, params = self._react_parse_action(thought)
                logger.info(f"[ReAct] Action: {action}({params})")
                
                if action and action in tools_dict:
                    # Execute the action
                    await tools_dict[action](**params)
                    
                    # Step 3: OBSERVE - Check result
                    if self._result.get("signal"):
                        signal = self._result["signal"]
                        logger.info(f"[ReAct] ✅ Success: {signal.direction.upper()}")
                        return signal
                    else:
                        observations.append(f"Action {action} executed but no signal generated")
                else:
                    observations.append(f"Invalid action: {action}")
                    
            except Exception as e:
                logger.warning(f"[ReAct] Iteration {iteration + 1} failed: {e}")
                observations.append(f"Error: {str(e)}")
        
        # Max iterations reached - return safe HOLD
        logger.warning(f"[ReAct] Max iterations ({max_iterations}) reached, defaulting to HOLD")
        return await self._generate_hold_signal(
            f"ReAct fallback exhausted after {max_iterations} iterations. Last observations: {observations[-1]}"
        )
    
    async def _react_reason(
        self,
        observations: List[str],
        agent_votes: List[Dict],
        position_context: Dict
    ) -> str:
        """
        ReAct REASON step: Generate thought about what action to take.
        """
        # Analyze votes to determine majority direction
        vote_summary = self._analyze_votes(agent_votes)
        
        prompt = f"""You are in ReAct fallback mode. The normal execution failed.

## Previous Observations
{chr(10).join(f"- {obs}" for obs in observations[-3:])}

## Vote Summary
{vote_summary}

## Current Position
{self._format_position_context(position_context)}

## Available Actions
- open_long(leverage=5, amount_percent=0.2, tp_percent=8.0, sl_percent=3.0, reasoning="...")
- open_short(leverage=5, amount_percent=0.2, tp_percent=8.0, sl_percent=3.0, reasoning="...")
- hold(reason="...")
- close_position(reason="...")

## Your Task
Think step by step:
1. What do the votes suggest?
2. What is the current position state?
3. What action should I take?

Then output your decision in this exact format:
ACTION: <action_name>(<param1>=<value1>, <param2>=<value2>, ...)

Example:
ACTION: hold(reason="Low confidence from experts, waiting for clearer signals")
"""
        
        try:
            response = await self.llm.generate(prompt)
            return response if isinstance(response, str) else str(response)
        except Exception as e:
            logger.error(f"[ReAct] Reason step failed: {e}")
            return "ACTION: hold(reason=\"ReAct reasoning failed\")"
    
    def _react_parse_action(self, thought: str) -> tuple:
        """
        Parse ACTION from ReAct thought.
        
        Returns:
            Tuple of (action_name, params_dict)
        """
        # Look for ACTION: pattern
        action_pattern = r'ACTION:\s*(\w+)\s*\((.*?)\)'
        match = re.search(action_pattern, thought, re.IGNORECASE | re.DOTALL)
        
        if not match:
            # Fallback: look for tool names directly
            for tool_name in ['open_long', 'open_short', 'hold', 'close_position']:
                if tool_name in thought.lower():
                    if tool_name == 'hold':
                        return ('hold', {'reason': 'Inferred from ReAct response'})
                    elif tool_name in ('open_long', 'open_short'):
                        return (tool_name, {
                            'leverage': 5,
                            'amount_percent': 0.2,
                            'tp_percent': 8.0,
                            'sl_percent': 3.0,
                            'reasoning': 'Inferred from ReAct response'
                        })
                    elif tool_name == 'close_position':
                        return ('close_position', {'reason': 'Inferred from ReAct response'})
            
            # Default to hold
            return ('hold', {'reason': 'Could not parse action from response'})
        
        action_name = match.group(1).lower()
        params_str = match.group(2)
        
        # Parse parameters
        params = {}
        
        # Handle different parameter formats
        # Format: key=value, key="value", key='value'
        param_patterns = [
            r'(\w+)\s*=\s*"([^"]*)"',  # key="value"
            r"(\w+)\s*=\s*'([^']*)'",   # key='value'
            r'(\w+)\s*=\s*([0-9.]+)',   # key=number
        ]
        
        for pattern in param_patterns:
            for key, value in re.findall(pattern, params_str):
                key = key.lower()
                # Type conversion
                if value.replace('.', '').replace('-', '').isdigit():
                    value = float(value) if '.' in value else int(value)
                params[key] = value
        
        # Set defaults for missing params
        if action_name in ('open_long', 'open_short'):
            params.setdefault('leverage', 5)
            params.setdefault('amount_percent', 0.2)
            params.setdefault('tp_percent', 8.0)
            params.setdefault('sl_percent', 3.0)
            params.setdefault('reasoning', params.get('reason', 'ReAct decision'))
        elif action_name == 'hold':
            params.setdefault('reason', 'ReAct decision')
        elif action_name == 'close_position':
            params.setdefault('reason', 'ReAct decision')
        
        return (action_name, params)
    
    def _analyze_votes(self, votes: List[Dict]) -> str:
        """Analyze votes and return summary."""
        if not votes:
            return "No votes available."
        
        long_votes = []
        short_votes = []
        hold_votes = []
        
        for vote in votes:
            direction = vote.get("direction", "").lower()
            if hasattr(direction, 'value'):
                direction = direction.value.lower()
            
            confidence = vote.get("confidence", 0)
            agent = vote.get("agent_name", vote.get("agent_id", "Unknown"))
            
            if direction in ("long", "buy", "bullish"):
                long_votes.append((agent, confidence))
            elif direction in ("short", "sell", "bearish"):
                short_votes.append((agent, confidence))
            else:
                hold_votes.append((agent, confidence))
        
        lines = [
            f"LONG votes: {len(long_votes)} (avg conf: {sum(c for _, c in long_votes) / len(long_votes):.0f}%)" if long_votes else "LONG votes: 0",
            f"SHORT votes: {len(short_votes)} (avg conf: {sum(c for _, c in short_votes) / len(short_votes):.0f}%)" if short_votes else "SHORT votes: 0",
            f"HOLD votes: {len(hold_votes)}" if hold_votes else "HOLD votes: 0"
        ]
        
        # Determine recommendation
        if len(long_votes) >= 3 and sum(c for _, c in long_votes) / len(long_votes) >= 70:
            lines.append("RECOMMENDATION: LONG (strong consensus)")
        elif len(short_votes) >= 3 and sum(c for _, c in short_votes) / len(short_votes) >= 70:
            lines.append("RECOMMENDATION: SHORT (strong consensus)")
        else:
            lines.append("RECOMMENDATION: HOLD (no clear consensus)")
        
        return "\n".join(lines)
    
    def _build_execution_prompt(
        self,
        leader_summary: str,
        agent_votes: List[Dict],
        position_context: Dict
    ) -> str:
        """Build the execution prompt for LLM."""
        
        # Format agent votes
        votes_text = self._format_agent_votes(agent_votes)
        
        # Format position context
        position_text = self._format_position_context(position_context)
        
        prompt = f"""You are TradeExecutor, responsible for making the final trading decision.

## Meeting Summary
{leader_summary}

## Expert Votes
{votes_text}

## Current Position Status
{position_text}

## Your Task
Based on the above information, make a trading decision:

1. If experts strongly agree on a direction (≥3 votes same direction with avg confidence ≥70%), execute that trade
2. If there's an existing position and experts recommend the opposite direction (≥70% confidence), consider reversing
3. If confidence is low or experts disagree, HOLD (do not trade)

## Available Actions
- `open_long(leverage, amount_percent, tp_percent, sl_percent, reasoning)` - Open a long position
- `open_short(leverage, amount_percent, tp_percent, sl_percent, reasoning)` - Open a short position
- `close_position(reason)` - Close current position
- `hold(reason)` - Do not trade

Choose ONE action and execute it. Be decisive but cautious.
"""
        return prompt
    
    def _format_agent_votes(self, votes: List[Dict]) -> str:
        """Format agent votes for prompt."""
        if not votes:
            return "No votes received."
        
        lines = []
        for vote in votes:
            agent = vote.get("agent_name", vote.get("agent_id", "Unknown"))
            direction = vote.get("direction", "unknown")
            if hasattr(direction, 'value'):
                direction = direction.value
            confidence = vote.get("confidence", 0)
            reasoning = vote.get("reasoning", "")[:150]
            
            lines.append(f"- **{agent}**: {direction.upper()} ({confidence}%) - {reasoning}")
        
        return "\n".join(lines)
    
    def _format_position_context(self, context: Dict) -> str:
        """Format position context for prompt."""
        if not context or not context.get("has_position"):
            return "No active position."
        
        return f"""- Direction: {context.get('direction', 'unknown').upper()}
- Entry Price: ${context.get('entry_price', 0):,.2f}
- Current Price: ${context.get('current_price', 0):,.2f}
- Unrealized PnL: ${context.get('unrealized_pnl', 0):,.2f} ({context.get('unrealized_pnl_percent', 0):+.1f}%)
- Leverage: {context.get('leverage', 1)}x"""
    
    def _get_execution_tools(self) -> List[Dict]:
        """Get tool definitions for LLM."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "open_long",
                    "description": "Open a LONG position (buy, expecting price to rise)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "leverage": {"type": "integer", "description": "Leverage (1-20)", "default": 5},
                            "amount_percent": {"type": "number", "description": "Position size as % of account (0.1-0.3)", "default": 0.2},
                            "tp_percent": {"type": "number", "description": "Take profit % from entry", "default": 8.0},
                            "sl_percent": {"type": "number", "description": "Stop loss % from entry", "default": 3.0},
                            "reasoning": {"type": "string", "description": "Reason for this trade"},
                            "confidence": {"type": "integer", "description": "Confidence level 0-100", "minimum": 0, "maximum": 100, "default": 70}
                        },
                        "required": ["reasoning"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_short",
                    "description": "Open a SHORT position (sell, expecting price to fall)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "leverage": {"type": "integer", "description": "Leverage (1-20)", "default": 5},
                            "amount_percent": {"type": "number", "description": "Position size as % of account (0.1-0.3)", "default": 0.2},
                            "tp_percent": {"type": "number", "description": "Take profit % from entry", "default": 8.0},
                            "sl_percent": {"type": "number", "description": "Stop loss % from entry", "default": 3.0},
                            "reasoning": {"type": "string", "description": "Reason for this trade"},
                            "confidence": {"type": "integer", "description": "Confidence level 0-100", "minimum": 0, "maximum": 100, "default": 70}
                        },
                        "required": ["reasoning"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "hold",
                    "description": "Do not trade, wait for better opportunity",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string", "description": "Reason for holding"},
                            "confidence": {"type": "integer", "description": "Confidence level 0-100", "minimum": 0, "maximum": 100, "default": 50}
                        },
                        "required": ["reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "close_position",
                    "description": "Close the current position",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string", "description": "Reason for closing"},
                            "confidence": {"type": "integer", "description": "Confidence level 0-100", "minimum": 0, "maximum": 100, "default": 100}
                        },
                        "required": ["reason"]
                    }
                }
            }
        ]
    
    def _build_tools_dict(self) -> Dict[str, Callable]:
        """Build dictionary of tool functions."""
        return {
            "open_long": self._tool_open_long,
            "open_short": self._tool_open_short,
            "hold": self._tool_hold,
            "close_position": self._tool_close_position,
        }
    
    async def _call_llm_with_tools(self, prompt: str, tools: List[Dict]) -> Dict:
        """Call LLM with tool definitions."""
        messages = [{"role": "user", "content": prompt}]
        
        # Use LLM service's tool calling capability
        if hasattr(self.llm, 'generate_with_tools'):
            return await self.llm.generate_with_tools(messages, tools)
        elif hasattr(self.llm, 'chat'):
            return await self.llm.chat(messages, tools=tools)
        else:
            # Fallback: generate without tools and parse
            response = await self.llm.generate(prompt)
            return {"content": response}
    
    async def _process_response(self, response: Dict, tools_dict: Dict) -> Optional[TradingSignal]:
        """Process LLM response and execute tool calls."""
        content = ""
        tool_calls = []
        
        # Parse response format
        if isinstance(response, dict):
            if "choices" in response and response["choices"]:
                message = response["choices"][0].get("message", {})
                content = message.get("content", "")
                tool_calls = message.get("tool_calls", [])
            else:
                content = response.get("content", str(response))
        else:
            content = str(response)
        
        logger.debug(f"[TradeExecutor] Response content: {content[:200] if content else 'None'}...")
        
        # Handle native tool_calls (OpenAI format)
        if tool_calls:
            logger.info(f"[TradeExecutor] Processing {len(tool_calls)} native tool calls")
            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                args_str = func.get("arguments", "{}")
                
                if tool_name in tools_dict:
                    try:
                        args = json.loads(args_str) if isinstance(args_str, str) else args_str
                        logger.info(f"[TradeExecutor] Executing: {tool_name}({args})")
                        await tools_dict[tool_name](**args)
                        self._executed_tools.append({"name": tool_name, "args": args})
                    except Exception as e:
                        logger.error(f"[TradeExecutor] Tool {tool_name} failed: {e}")
        
        # Handle legacy [USE_TOOL: xxx] format (deprecated)
        if not self._result["signal"] and content:
            legacy_signal = await self._parse_legacy_format(content, tools_dict)
            if legacy_signal:
                return legacy_signal
        
        return self._result.get("signal")
    
    async def _parse_legacy_format(self, content: str, tools_dict: Dict) -> Optional[TradingSignal]:
        """Parse legacy [USE_TOOL: xxx] format (deprecated)."""
        tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
        matches = re.findall(tool_pattern, content)
        
        if not matches:
            return None
        
        logger.warning("[TradeExecutor] DEPRECATED: Legacy [USE_TOOL: xxx] format detected")
        
        for tool_name, params_str in matches:
            if tool_name in tools_dict:
                try:
                    params = self._parse_legacy_params(params_str)
                    await tools_dict[tool_name](**params)
                except Exception as e:
                    logger.error(f"[TradeExecutor] Legacy tool {tool_name} failed: {e}")
        
        return self._result.get("signal")
    
    def _parse_legacy_params(self, params_str: str) -> Dict:
        """Parse legacy tool parameters."""
        params = {}
        for pattern in [r'(\w+)="([^"]*)"', r"(\w+)='([^']*)'", r'(\w+)=(\d+\.?\d*)']:
            for key, value in re.findall(pattern, params_str):
                if value.replace('.', '').replace('-', '').isdigit():
                    value = float(value) if '.' in value else int(value)
                params[key] = value
        
        # Parameter aliases
        aliases = {'reason': 'reasoning', 'amount': 'amount_percent', 'lev': 'leverage'}
        for old, new in aliases.items():
            if old in params and new not in params:
                params[new] = params.pop(old)
        
        return params
    
    # Tool implementations
    async def _tool_open_long(
        self,
        leverage: int = 5,
        amount_percent: float = 0.2,
        tp_percent: float = 8.0,
        sl_percent: float = 3.0,
        reasoning: str = "",
        confidence: int = 70
    ):
        """Open long position tool."""
        await self._execute_open_position("long", leverage, amount_percent, tp_percent, sl_percent, reasoning, confidence)
    
    async def _tool_open_short(
        self,
        leverage: int = 5,
        amount_percent: float = 0.2,
        tp_percent: float = 8.0,
        sl_percent: float = 3.0,
        reasoning: str = "",
        confidence: int = 70
    ):
        """Open short position tool."""
        await self._execute_open_position("short", leverage, amount_percent, tp_percent, sl_percent, reasoning, confidence)
    
    async def _execute_open_position(
        self,
        direction: str,
        leverage: int,
        amount_percent: float,
        tp_percent: float,
        sl_percent: float,
        reasoning: str,
        confidence: int = 70
    ):
        """Execute position opening."""
        # ✅ Confidence validation
        if confidence < self.MIN_CONFIDENCE_OPEN:
            logger.warning(
                f"[SafetyGuard] Confidence {confidence}% below minimum {self.MIN_CONFIDENCE_OPEN}% - "
                f"Blocking {direction} trade"
            )
            self._result["signal"] = await self._generate_hold_signal(
                f"Blocked - Confidence {confidence}% too low for opening position"
            )
            return
        
        try:
            current_price = await get_current_btc_price()
            
            # Calculate TP/SL prices
            if direction == "long":
                tp_price = current_price * (1 + tp_percent / 100)
                sl_price = current_price * (1 - sl_percent / 100)
            else:
                tp_price = current_price * (1 - tp_percent / 100)
                sl_price = current_price * (1 + sl_percent / 100)
            
            # Execute via trader if available
            if self.paper_trader:
                account = await self.paper_trader.get_account()
                available = account.get('available_balance', account.get('balance', 10000))
                amount_usdt = available * min(amount_percent, 0.3)
                
                if direction == "long":
                    result = await self.paper_trader.open_long(
                        symbol=self.symbol,
                        leverage=leverage,
                        amount_usdt=amount_usdt,
                        tp_price=tp_price,
                        sl_price=sl_price
                    )
                else:
                    result = await self.paper_trader.open_short(
                        symbol=self.symbol,
                        leverage=leverage,
                        amount_usdt=amount_usdt,
                        tp_price=tp_price,
                        sl_price=sl_price
                    )
                
                logger.info(f"[TradeExecutor] Position opened: {direction.upper()} | "
                           f"Leverage: {leverage}x | Amount: ${amount_usdt:.2f}")
            
            # Create signal
            self._result["signal"] = TradingSignal(
                direction=direction,
                symbol=self.symbol,
                leverage=leverage,
                amount_percent=amount_percent,
                entry_price=current_price,
                take_profit_price=tp_price,
                stop_loss_price=sl_price,
                confidence=confidence,  # From LLM or default
                reasoning=reasoning,
                agents_consensus={},
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"[TradeExecutor] Open position failed: {e}")
            raise
    
    async def _tool_hold(self, reason: str = "", confidence: int = 50):
        """Hold tool - do not trade."""
        current_price = await get_current_btc_price()
        
        self._result["signal"] = TradingSignal(
            direction="hold",
            symbol=self.symbol,
            leverage=1,
            amount_percent=0.0,
            entry_price=current_price,
            take_profit_price=current_price,
            stop_loss_price=current_price,
            confidence=confidence,  # From LLM or default
            reasoning=reason,
            agents_consensus={},
            timestamp=datetime.now()
        )
        
        logger.info(f"[TradeExecutor] HOLD: {reason}")
    
    async def _tool_close_position(self, reason: str = "", confidence: int = 100):
        """Close position tool."""
        # ✅ Confidence validation        
        if confidence < self.MIN_CONFIDENCE_CLOSE:
            logger.warning(
                f"[SafetyGuard] Confidence {confidence}% below minimum {self.MIN_CONFIDENCE_CLOSE}% - "
                f"Blocking close"
            )
            self._result["signal"] = await self._generate_hold_signal(
                f"Blocked - Confidence {confidence}% too low for closing position"
            )
            return
        
        current_price = await get_current_btc_price()
        
        if self.paper_trader:
            try:
                result = await self.paper_trader.close_position(reason=f"executor: {reason}")
                logger.info(f"[TradeExecutor] Position closed: {reason}")
            except Exception as e:
                logger.error(f"[TradeExecutor] Close position failed: {e}")
        
        self._result["signal"] = TradingSignal(
            direction="close_position",  # CRITICAL FIX: was "hold", should be "close_position"
            symbol=self.symbol,
            leverage=1,
            amount_percent=0.0,
            entry_price=current_price,
            take_profit_price=current_price,
            stop_loss_price=current_price,
            confidence=confidence,  # From LLM, default 100 for deliberate close
            reasoning=f"[Close position] {reason}",
            agents_consensus={},
            timestamp=datetime.now()
        )
    
    async def _generate_hold_signal(self, reason: str, confidence: int = 50) -> TradingSignal:
        """Generate a HOLD signal (fallback path)."""
        current_price = await get_current_btc_price()
        
        return TradingSignal(
            direction="hold",
            symbol=self.symbol,
            leverage=1,
            amount_percent=0.0,
            entry_price=current_price,
            take_profit_price=current_price,
            stop_loss_price=current_price,
            confidence=confidence,  # Configurable, default 50
            reasoning=reason,
            agents_consensus={},
            timestamp=datetime.now()
        )
