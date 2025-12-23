"""
Trade Execution Tools

Tools for opening and closing trading positions.
"""

from typing import List
import logging

from ..base import BaseTool, ToolResult, ToolParameter, ToolCategory

logger = logging.getLogger(__name__)


class OpenLongTool(BaseTool):
    """
    Open a long (buy) position.
    """
    
    name = "open_long"
    description = "Open a long (buy) position. Use when bullish on the market."
    category = ToolCategory.EXECUTION
    
    def __init__(self, trader=None):
        super().__init__()
        self.trader = trader
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="leverage",
                type="integer",
                description="Leverage multiplier (1-10 recommended, max 125)",
                required=False,
                default=3
            ),
            ToolParameter(
                name="amount_percent",
                type="number",
                description="Position size as percentage of available balance (0.1-0.5)",
                required=False,
                default=0.2
            ),
            ToolParameter(
                name="take_profit_percent",
                type="number",
                description="Take profit percentage above entry (1-20%)",
                required=False,
                default=5.0
            ),
            ToolParameter(
                name="stop_loss_percent",
                type="number", 
                description="Stop loss percentage below entry (0.5-10%)",
                required=False,
                default=2.0
            ),
            ToolParameter(
                name="reasoning",
                type="string",
                description="Reason for opening this position",
                required=False,
                default=""
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute long position open."""
        if not self.trader:
            return ToolResult.error_result(
                "No trader configured - cannot execute trades",
                self.name
            )
        
        leverage = min(125, max(1, kwargs.get("leverage", 3)))
        amount_percent = min(0.5, max(0.1, kwargs.get("amount_percent", 0.2)))
        tp_percent = kwargs.get("take_profit_percent", 5.0)
        sl_percent = kwargs.get("stop_loss_percent", 2.0)
        reasoning = kwargs.get("reasoning", "")
        
        try:
            result = await self.trader.open_long(
                leverage=leverage,
                amount_percent=amount_percent,
                tp_percent=tp_percent,
                sl_percent=sl_percent,
                reason=reasoning
            )
            
            if result.success:
                return ToolResult.success_result({
                    "action": "open_long",
                    "success": True,
                    "order_id": result.order_id,
                    "entry_price": result.price,
                    "leverage": leverage,
                    "size": result.size,
                    "take_profit": result.take_profit_price,
                    "stop_loss": result.stop_loss_price,
                    "reasoning": reasoning
                }, self.name)
            else:
                return ToolResult.error_result(
                    f"Failed to open long: {result.error}",
                    self.name
                )
                
        except Exception as e:
            logger.error(f"Open long error: {e}")
            return ToolResult.error_result(str(e), self.name)


class OpenShortTool(BaseTool):
    """
    Open a short (sell) position.
    """
    
    name = "open_short"
    description = "Open a short (sell) position. Use when bearish on the market."
    category = ToolCategory.EXECUTION
    
    def __init__(self, trader=None):
        super().__init__()
        self.trader = trader
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="leverage",
                type="integer",
                description="Leverage multiplier (1-10 recommended, max 125)",
                required=False,
                default=3
            ),
            ToolParameter(
                name="amount_percent",
                type="number",
                description="Position size as percentage of available balance (0.1-0.5)",
                required=False,
                default=0.2
            ),
            ToolParameter(
                name="take_profit_percent",
                type="number",
                description="Take profit percentage below entry (1-20%)",
                required=False,
                default=5.0
            ),
            ToolParameter(
                name="stop_loss_percent",
                type="number",
                description="Stop loss percentage above entry (0.5-10%)",
                required=False,
                default=2.0
            ),
            ToolParameter(
                name="reasoning",
                type="string",
                description="Reason for opening this position",
                required=False,
                default=""
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute short position open."""
        if not self.trader:
            return ToolResult.error_result(
                "No trader configured - cannot execute trades",
                self.name
            )
        
        leverage = min(125, max(1, kwargs.get("leverage", 3)))
        amount_percent = min(0.5, max(0.1, kwargs.get("amount_percent", 0.2)))
        tp_percent = kwargs.get("take_profit_percent", 5.0)
        sl_percent = kwargs.get("stop_loss_percent", 2.0)
        reasoning = kwargs.get("reasoning", "")
        
        try:
            result = await self.trader.open_short(
                leverage=leverage,
                amount_percent=amount_percent,
                tp_percent=tp_percent,
                sl_percent=sl_percent,
                reason=reasoning
            )
            
            if result.success:
                return ToolResult.success_result({
                    "action": "open_short",
                    "success": True,
                    "order_id": result.order_id,
                    "entry_price": result.price,
                    "leverage": leverage,
                    "size": result.size,
                    "take_profit": result.take_profit_price,
                    "stop_loss": result.stop_loss_price,
                    "reasoning": reasoning
                }, self.name)
            else:
                return ToolResult.error_result(
                    f"Failed to open short: {result.error}",
                    self.name
                )
                
        except Exception as e:
            logger.error(f"Open short error: {e}")
            return ToolResult.error_result(str(e), self.name)


class ClosePositionTool(BaseTool):
    """
    Close an existing position.
    """
    
    name = "close_position"
    description = "Close the current position. Use to take profits or cut losses."
    category = ToolCategory.EXECUTION
    
    def __init__(self, trader=None):
        super().__init__()
        self.trader = trader
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="reasoning",
                type="string",
                description="Reason for closing the position",
                required=False,
                default=""
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute position close."""
        if not self.trader:
            return ToolResult.error_result(
                "No trader configured - cannot execute trades",
                self.name
            )
        
        reasoning = kwargs.get("reasoning", "")
        
        try:
            result = await self.trader.close_position(reason=reasoning)
            
            if result.success:
                return ToolResult.success_result({
                    "action": "close_position",
                    "success": True,
                    "closed_at": result.price,
                    "pnl": result.pnl if hasattr(result, 'pnl') else None,
                    "reasoning": reasoning
                }, self.name)
            else:
                return ToolResult.error_result(
                    f"Failed to close position: {result.error}",
                    self.name
                )
                
        except Exception as e:
            logger.error(f"Close position error: {e}")
            return ToolResult.error_result(str(e), self.name)


class HoldTool(BaseTool):
    """
    Hold/wait - no action taken.
    """
    
    name = "hold"
    description = "Hold - take no trading action. Use when market conditions are unclear or unfavorable."
    category = ToolCategory.EXECUTION
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="reason",
                type="string",
                description="Reason for holding/not trading",
                required=False,
                default="Market conditions unclear"
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute hold (no-op)."""
        reason = kwargs.get("reason", "Market conditions unclear")
        
        return ToolResult.success_result({
            "action": "hold",
            "success": True,
            "reason": reason,
            "message": "No trade executed - holding position"
        }, self.name)
