"""
Account Information Tools

Tools for getting account balance and position information.
"""

from typing import List
import logging

from ..base import BaseTool, ToolResult, ToolParameter, ToolCategory

logger = logging.getLogger(__name__)


class GetAccountTool(BaseTool):
    """
    Get account balance and status.
    """
    
    name = "get_account"
    description = "Get account balance, available margin, and usage information"
    category = ToolCategory.ACCOUNT
    
    def __init__(self, trader=None):
        super().__init__()
        self.trader = trader
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []  # No parameters needed
    
    async def execute(self, **kwargs) -> ToolResult:
        """Get account information."""
        if not self.trader:
            # Return mock data for testing
            return ToolResult.success_result({
                "total_equity": 10000.0,
                "available_balance": 8000.0,
                "used_margin": 2000.0,
                "unrealized_pnl": 0.0,
                "currency": "USDT",
                "margin_ratio": 0.2,
                "note": "Mock data - no trader configured"
            }, self.name)
        
        try:
            account = await self.trader.get_account()
            
            return ToolResult.success_result({
                "total_equity": account.total_equity,
                "available_balance": account.available_balance,
                "used_margin": account.used_margin,
                "unrealized_pnl": account.unrealized_pnl,
                "currency": "USDT",
                "margin_ratio": account.margin_ratio if hasattr(account, 'margin_ratio') else 0
            }, self.name)
                
        except Exception as e:
            logger.error(f"Get account error: {e}")
            return ToolResult.error_result(str(e), self.name)


class GetPositionTool(BaseTool):
    """
    Get current position information.
    """
    
    name = "get_position"
    description = "Get current position details including entry price, P&L, leverage, and liquidation price"
    category = ToolCategory.ACCOUNT
    
    def __init__(self, trader=None):
        super().__init__()
        self.trader = trader
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="symbol",
                type="string",
                description="Trading pair (e.g., 'BTC-USDT-SWAP')",
                required=False,
                default="BTC-USDT-SWAP"
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Get position information."""
        symbol = kwargs.get("symbol", "BTC-USDT-SWAP")
        
        if not self.trader:
            # Return no position for testing
            return ToolResult.success_result({
                "has_position": False,
                "symbol": symbol,
                "note": "Mock data - no trader configured"
            }, self.name)
        
        try:
            position = await self.trader.get_position(symbol)
            
            if position is None:
                return ToolResult.success_result({
                    "has_position": False,
                    "symbol": symbol
                }, self.name)
            
            return ToolResult.success_result({
                "has_position": True,
                "symbol": symbol,
                "direction": position.direction,
                "size": position.size,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "leverage": position.leverage,
                "margin": position.margin,
                "unrealized_pnl": position.unrealized_pnl,
                "unrealized_pnl_percent": position.unrealized_pnl_percent,
                "liquidation_price": position.liquidation_price,
                "take_profit_price": position.take_profit_price,
                "stop_loss_price": position.stop_loss_price
            }, self.name)
                
        except Exception as e:
            logger.error(f"Get position error: {e}")
            return ToolResult.error_result(str(e), self.name)
