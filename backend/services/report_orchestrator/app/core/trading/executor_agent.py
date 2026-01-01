"""
Executor Agent

Trade execution agent that inherits from Agent, providing unified LLM calling approach.
This replaces the old TradeExecutor class that required external llm_service injection.

Key Features:
- Inherits from Agent base class (uses HTTP to llm_gateway, self-contained)
- Registers trading tools: open_long, open_short, hold, close_position
- Uses Agent's native tool calling via /v1/chat/completions endpoint
- Eliminates need for LLMGatewayClient adapter
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from app.core.roundtable.agent import Agent
from app.core.roundtable.tool import FunctionTool
from app.models.trading_models import TradingSignal
from app.core.trading.price_service import get_current_btc_price

logger = logging.getLogger(__name__)


class ExecutorAgent(Agent):
    """
    Trading Execution Agent - inherits from Agent for unified LLM calling.
    
    Replaces TradeExecutor. Uses Agent's _call_llm() which makes HTTP calls
    directly to llm_gateway, avoiding the need for llm_service injection.
    
    Usage:
        executor = ExecutorAgent(
            toolkit=toolkit,
            paper_trader=paper_trader,
            symbol="BTC-USDT-SWAP"
        )
        signal = await executor.execute(leader_summary, agent_votes, position_context)
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
        
        # Register trading tools
        self._register_trading_tools()
        
        logger.info(f"[ExecutorAgent] Initialized with {len(self.tools)} tools")
    
    def _get_executor_role_prompt(self) -> str:
        """Get the role prompt for executor agent."""
        return """You are a professional trading executor responsible for making the final trading decision.

Your job is to:
1. Review the leader's summary and agent consensus
2. Consider the current position context
3. Make a decisive trading action by calling ONE of the available tools

IMPORTANT RULES:
- You MUST call exactly ONE tool to express your decision
- Be decisive - choose the action that best matches the consensus
- If experts recommend HOLD, call the hold() tool
- If opening a position, use appropriate leverage (3-10x) and risk parameters
- Always provide clear reasoning for your decision"""
    
    def _register_trading_tools(self):
        """Register trading tools for LLM tool calling."""
        
        # open_long tool
        self.register_tool(FunctionTool(
            name="open_long",
            description="Open a LONG position (buy, expecting price to rise)",
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
            description="Open a SHORT position (sell, expecting price to fall)",
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
            description="Do not trade, maintain current position or wait for better opportunity",
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
            description="Close the current position completely",
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
        
        This is the main entry point, called by LangGraph execution_node.
        
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
        
        logger.info("[ExecutorAgent] Starting execution phase...")
        
        # Build execution prompt
        prompt = self._build_execution_prompt(
            leader_summary=leader_summary,
            agent_votes=agent_votes,
            position_context=position_context
        )
        
        try:
            # Call LLM with tools using Agent's native method
            messages = [{"role": "user", "content": prompt}]
            response = await self._call_llm_with_tools(messages)
            
            # Process tool calls from response
            await self._process_tool_calls(response)
            
            # Check if we got a signal
            if self._result.get("signal"):
                signal = self._result["signal"]
                logger.info(f"[ExecutorAgent] ✅ Execution complete: {signal.direction.upper()}")
                return signal
            else:
                logger.warning("[ExecutorAgent] No signal generated, defaulting to HOLD")
                return await self._generate_hold_signal("No tool call made, defaulting to HOLD")
                
        except Exception as e:
            logger.error(f"[ExecutorAgent] Execution failed: {e}")
            return await self._generate_hold_signal(f"Execution error: {str(e)}")
    
    def _build_execution_prompt(
        self,
        leader_summary: str,
        agent_votes: List[Dict],
        position_context: Dict
    ) -> str:
        """Build the execution prompt with all context."""
        
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
- open_long() - Open a LONG position
- open_short() - Open a SHORT position
- hold() - Maintain current state, no action
- close_position() - Close existing position

IMPORTANT: You MUST call exactly one tool to make your decision."""
    
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
    
    async def _call_llm_with_tools(self, messages: List[Dict]) -> Dict:
        """Call LLM with tool definitions using Agent's native HTTP approach."""
        import httpx
        
        # Get tools in OpenAI format
        tools_schema = self._get_tools_openai_format()
        
        request_data = {
            "messages": messages,
            "tools": tools_schema,
            "tool_choice": "required",  # Force tool call
            "temperature": self.temperature
        }
        
        logger.info(f"[ExecutorAgent] Calling LLM with {len(tools_schema)} tools")
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{self.llm_gateway_url}/v1/chat/completions",
                json=request_data
            )
            response.raise_for_status()
            result = response.json()
            
            logger.debug(f"[ExecutorAgent] LLM response received")
            return result
    
    def _get_tools_openai_format(self) -> List[Dict]:
        """Convert registered tools to OpenAI function calling format."""
        tools = []
        for tool in self.tools.values():
            schema = tool.to_schema()
            tools.append({
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema["description"],
                    "parameters": schema.get("parameters", {"type": "object", "properties": {}})
                }
            })
        return tools
    
    async def _process_tool_calls(self, response: Dict):
        """Process tool calls from LLM response."""
        if "choices" not in response or not response["choices"]:
            logger.warning("[ExecutorAgent] No choices in LLM response")
            return
        
        message = response["choices"][0].get("message", {})
        tool_calls = message.get("tool_calls", [])
        
        if not tool_calls:
            # Check if there's content that might indicate a decision
            content = message.get("content", "")
            if content:
                logger.info(f"[ExecutorAgent] LLM returned text instead of tool call: {content[:100]}")
            return
        
        # Execute each tool call
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            tool_name = function.get("name", "")
            arguments_str = function.get("arguments", "{}")
            
            logger.info(f"[ExecutorAgent] Executing tool: {tool_name}")
            
            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                logger.error(f"[ExecutorAgent] Failed to parse arguments: {arguments_str}")
                continue
            
            # Get the registered tool and execute it
            tool = self.tools.get(tool_name)
            if tool:
                try:
                    await tool.execute(**arguments)
                    self._executed_tools.append({
                        "tool": tool_name,
                        "params": arguments,
                        "success": True
                    })
                except Exception as e:
                    logger.error(f"[ExecutorAgent] Tool execution failed: {e}")
                    self._executed_tools.append({
                        "tool": tool_name,
                        "params": arguments,
                        "success": False,
                        "error": str(e)
                    })
            else:
                logger.warning(f"[ExecutorAgent] Unknown tool: {tool_name}")
    
    # ==================== Tool Implementation Methods ====================
    
    async def _execute_open_long(
        self,
        leverage: int = 5,
        amount_percent: float = 0.2,
        tp_percent: float = 8.0,
        sl_percent: float = 3.0,
        reasoning: str = "",
        confidence: int = 70
    ):
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
    
    async def _execute_open_short(
        self,
        leverage: int = 5,
        amount_percent: float = 0.2,
        tp_percent: float = 8.0,
        sl_percent: float = 3.0,
        reasoning: str = "",
        confidence: int = 70
    ):
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
    
    async def _execute_hold(
        self,
        reason: str = "",
        confidence: int = 50
    ):
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
    
    async def _execute_close_position(
        self,
        reason: str = "",
        confidence: int = 100
    ):
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
