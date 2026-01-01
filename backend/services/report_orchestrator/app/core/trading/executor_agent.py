"""
Executor Agent

Trade execution agent that inherits from ReWOOAgent, using the same 3-phase
(Plan → Execute → Solve) workflow as other analysis agents.

Key Features:
- Inherits from ReWOOAgent (unified architecture with other agents)
- Registers trading tools: open_long, open_short, hold, close_position
- Uses same LLM calling pattern as TechnicalAnalyst, MacroEconomist, etc.
- No special tool_choice param - follows standard ReWOO planning
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from app.core.roundtable.rewoo_agent import ReWOOAgent
from app.core.roundtable.tool import FunctionTool
from app.models.trading_models import TradingSignal
from app.core.trading.price_service import get_current_btc_price
from app.core.trading.decision_store import TradingDecision, TradingDecisionStore

logger = logging.getLogger(__name__)


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
    
    # Safety thresholds
    MIN_CONFIDENCE_OPEN = 65
    MIN_CONFIDENCE_CLOSE = 50
    
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
            temperature=0.3  # Lower temperature for trading decisions
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
        
        # Register trading tools
        self._register_trading_tools()
        
        logger.info(f"[ExecutorAgent] Initialized with {len(self.tools)} tools (ReWOOAgent pattern)")
    
    def _get_executor_role_prompt(self) -> str:
        """Get the role prompt for executor agent."""
        return """You are a professional trading executor responsible for making the final trading decision.

Your job is to:
1. Review the leader's summary and agent consensus
2. Consider the current position context
3. Decide on a trading action: open_long, open_short, hold, or close_position

You have access to trading tools. Based on the analysis, you MUST use exactly ONE of these tools:
- open_long: Open a LONG position (buy, expecting price to rise)
- open_short: Open a SHORT position (sell, expecting price to fall)
- hold: Maintain current state, no action
- close_position: Close existing position

IMPORTANT RULES:
- You MUST call exactly ONE tool to express your decision
- Be decisive - choose the action that best matches the consensus
- If experts recommend HOLD, call the hold() tool
- If opening a position, use appropriate leverage (3-10x) and risk parameters
- Always provide clear reasoning for your decision"""
    
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
  {{"step": 1, "tool": "open_long", "params": {{"leverage": 5, "amount_percent": 0.2, "tp_percent": 8.0, "sl_percent": 3.0, "reasoning": "Strong bullish consensus with 4/5 experts recommending LONG. Technical breakout confirmed.", "confidence": 75}}, "purpose": "Open long position based on bullish consensus"}}
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
        
        # open_long tool
        self.register_tool(FunctionTool(
            name="open_long",
            description="Open a LONG position (buy, expecting price to rise). Parameters: leverage (1-20), amount_percent (0.1-0.3), tp_percent (take profit %), sl_percent (stop loss %), reasoning (string), confidence (0-100)",
            func=self._execute_open_long,
            parameters_schema={
                "type": "object",
                "properties": {
                    "leverage": {"type": "integer", "description": "Leverage (1-20)", "default": 5},
                    "amount_percent": {"type": "number", "description": "Position size as % of account (0.1-0.3)", "default": 0.2},
                    "tp_percent": {"type": "number", "description": "Take profit % from entry", "default": 8.0},
                    "sl_percent": {"type": "number", "description": "Stop loss % from entry", "default": 3.0},
                    "reasoning": {"type": "string", "description": "Reason for this trade"},
                    "confidence": {"type": "integer", "description": "Confidence level 0-100", "default": 70}
                },
                "required": ["reasoning"]
            }
        ))
        
        # open_short tool
        self.register_tool(FunctionTool(
            name="open_short",
            description="Open a SHORT position (sell, expecting price to fall). Parameters: leverage (1-20), amount_percent (0.1-0.3), tp_percent (take profit %), sl_percent (stop loss %), reasoning (string), confidence (0-100)",
            func=self._execute_open_short,
            parameters_schema={
                "type": "object",
                "properties": {
                    "leverage": {"type": "integer", "description": "Leverage (1-20)", "default": 5},
                    "amount_percent": {"type": "number", "description": "Position size as % of account (0.1-0.3)", "default": 0.2},
                    "tp_percent": {"type": "number", "description": "Take profit % from entry", "default": 8.0},
                    "sl_percent": {"type": "number", "description": "Stop loss % from entry", "default": 3.0},
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
        
        # Build query for ReWOO analysis
        query = self._build_execution_query(
            leader_summary=leader_summary,
            agent_votes=agent_votes,
            position_context=position_context
        )
        
        try:
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
            
            # Fallback to HOLD
            logger.warning("[ExecutorAgent] No signal generated, defaulting to HOLD")
            signal = await self._generate_hold_signal("No tool call made, defaulting to HOLD")
            await self._save_decision(signal)
            return signal
                
        except Exception as e:
            logger.error(f"[ExecutorAgent] Execution failed: {e}")
            import traceback
            traceback.print_exc()
            signal = await self._generate_hold_signal(f"Execution error: {str(e)}")
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
    
    def _build_execution_query(
        self,
        leader_summary: str,
        agent_votes: List[Dict],
        position_context: Dict
    ) -> str:
        """Build the execution query for ReWOO analysis."""
        
        # Format votes
        votes_text = self._format_votes(agent_votes)
        
        # Format position context
        position_text = self._format_position_context(position_context)
        
        return f"""# Trading Execution Decision

## Leader's Summary
{leader_summary}

## Agent Votes Summary
{votes_text}

## Current Position
{position_text}

## Your Task
Based on the above information, make a trading decision by calling ONE of the available tools:
- open_long: Open a LONG position
- open_short: Open a SHORT position
- hold: Maintain current state, no action
- close_position: Close existing position

You MUST call exactly one tool to make your decision. Analyze the consensus and make a decisive action."""
    
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
    
    async def _execute_open_long(
        self,
        leverage: int = 5,
        amount_percent: float = 0.2,
        tp_percent: float = 8.0,
        sl_percent: float = 3.0,
        reasoning: str = "",
        confidence: int = 70
    ) -> Dict[str, Any]:
        """Execute open_long tool."""
        logger.info(f"[ExecutorAgent] Executing: open_long(leverage={leverage}, confidence={confidence})")
        
        current_price = await get_current_btc_price()
        tp_price = current_price * (1 + tp_percent / 100)
        sl_price = current_price * (1 - sl_percent / 100)
        
        signal = TradingSignal(
            direction="long",
            symbol=self.symbol,
            leverage=min(leverage, 20),
            amount_percent=min(amount_percent, 0.3),
            entry_price=current_price,
            take_profit_price=tp_price,
            stop_loss_price=sl_price,
            confidence=confidence,
            reasoning=reasoning,
            timestamp=datetime.now()
        )
        
        self._result["signal"] = signal
        
        return {
            "success": True,
            "action": "open_long",
            "price": current_price,
            "leverage": leverage,
            "confidence": confidence,
            "reasoning": reasoning
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
        """Execute open_short tool."""
        logger.info(f"[ExecutorAgent] Executing: open_short(leverage={leverage}, confidence={confidence})")
        
        current_price = await get_current_btc_price()
        tp_price = current_price * (1 - tp_percent / 100)
        sl_price = current_price * (1 + sl_percent / 100)
        
        signal = TradingSignal(
            direction="short",
            symbol=self.symbol,
            leverage=min(leverage, 20),
            amount_percent=min(amount_percent, 0.3),
            entry_price=current_price,
            take_profit_price=tp_price,
            stop_loss_price=sl_price,
            confidence=confidence,
            reasoning=reasoning,
            timestamp=datetime.now()
        )
        
        self._result["signal"] = signal
        
        return {
            "success": True,
            "action": "open_short",
            "price": current_price,
            "leverage": leverage,
            "confidence": confidence,
            "reasoning": reasoning
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
        """Execute close_position tool."""
        logger.info(f"[ExecutorAgent] Executing: close_position(reason={reason[:50]}...)")
        
        current_price = await get_current_btc_price()
        
        signal = TradingSignal(
            direction="close",
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
            "action": "close_position",
            "price": current_price,
            "confidence": confidence,
            "reasoning": reason
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
