"""
Mock Trader

Mock trading implementation for testing without real trades.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class MockPosition:
    """Mock position data."""
    symbol: str = "BTC-USDT-SWAP"
    direction: str = "long"
    size: float = 0.1
    entry_price: float = 50000.0
    current_price: float = 51000.0
    leverage: int = 3
    margin: float = 1666.67
    unrealized_pnl: float = 100.0
    unrealized_pnl_percent: float = 6.0
    liquidation_price: float = 35000.0
    take_profit_price: Optional[float] = 52500.0
    stop_loss_price: Optional[float] = 49000.0
    opened_at: datetime = field(default_factory=datetime.now)


@dataclass
class MockAccountBalance:
    """Mock account balance."""
    total_equity: float = 10000.0
    available_balance: float = 8000.0
    used_margin: float = 2000.0
    unrealized_pnl: float = 100.0
    margin_ratio: float = 0.2


@dataclass
class MockTradeResult:
    """Mock trade execution result."""
    success: bool = True
    order_id: str = "mock_order_123"
    price: float = 50000.0
    size: float = 0.1
    error: Optional[str] = None
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    pnl: Optional[float] = None


class MockTrader:
    """
    Mock Trader for testing.
    
    Simulates trading operations without real API calls.
    """
    
    def __init__(self, initial_balance: float = 10000.0):
        """
        Initialize mock trader.
        
        Args:
            initial_balance: Starting balance for simulation
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: Dict[str, MockPosition] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.order_counter = 0
        
        # Configuration
        self.simulate_failures = False
        self.failure_rate = 0.0
    
    async def get_account(self) -> MockAccountBalance:
        """Get mock account balance."""
        used_margin = sum(p.margin for p in self.positions.values())
        unrealized_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        
        return MockAccountBalance(
            total_equity=self.balance + unrealized_pnl,
            available_balance=self.balance - used_margin,
            used_margin=used_margin,
            unrealized_pnl=unrealized_pnl,
            margin_ratio=used_margin / self.balance if self.balance > 0 else 0
        )
    
    async def get_position(self, symbol: str = "BTC-USDT-SWAP") -> Optional[MockPosition]:
        """Get mock position."""
        return self.positions.get(symbol)
    
    async def open_long(
        self,
        leverage: int = 3,
        amount_percent: float = 0.2,
        tp_percent: float = 5.0,
        sl_percent: float = 2.0,
        reason: str = "",
        symbol: str = "BTC-USDT-SWAP"
    ) -> MockTradeResult:
        """Open mock long position."""
        return await self._open_position(
            direction="long",
            leverage=leverage,
            amount_percent=amount_percent,
            tp_percent=tp_percent,
            sl_percent=sl_percent,
            reason=reason,
            symbol=symbol
        )
    
    async def open_short(
        self,
        leverage: int = 3,
        amount_percent: float = 0.2,
        tp_percent: float = 5.0,
        sl_percent: float = 2.0,
        reason: str = "",
        symbol: str = "BTC-USDT-SWAP"
    ) -> MockTradeResult:
        """Open mock short position."""
        return await self._open_position(
            direction="short",
            leverage=leverage,
            amount_percent=amount_percent,
            tp_percent=tp_percent,
            sl_percent=sl_percent,
            reason=reason,
            symbol=symbol
        )
    
    async def _open_position(
        self,
        direction: str,
        leverage: int,
        amount_percent: float,
        tp_percent: float,
        sl_percent: float,
        reason: str,
        symbol: str
    ) -> MockTradeResult:
        """Internal method to open position."""
        # Simulate failure if configured
        if self.simulate_failures:
            import random
            if random.random() < self.failure_rate:
                return MockTradeResult(
                    success=False,
                    error="Simulated order failure"
                )
        
        # Calculate position parameters
        entry_price = 50000.0  # Mock entry price
        margin = self.balance * amount_percent
        size = (margin * leverage) / entry_price
        
        # Calculate TP/SL prices
        if direction == "long":
            tp_price = entry_price * (1 + tp_percent / 100)
            sl_price = entry_price * (1 - sl_percent / 100)
            liq_price = entry_price * (1 - 0.9 / leverage)
        else:
            tp_price = entry_price * (1 - tp_percent / 100)
            sl_price = entry_price * (1 + sl_percent / 100)
            liq_price = entry_price * (1 + 0.9 / leverage)
        
        # Create position
        self.order_counter += 1
        order_id = f"mock_order_{self.order_counter}"
        
        position = MockPosition(
            symbol=symbol,
            direction=direction,
            size=size,
            entry_price=entry_price,
            current_price=entry_price,
            leverage=leverage,
            margin=margin,
            unrealized_pnl=0.0,
            unrealized_pnl_percent=0.0,
            liquidation_price=liq_price,
            take_profit_price=tp_price,
            stop_loss_price=sl_price
        )
        
        self.positions[symbol] = position
        
        # Record trade
        self.trade_history.append({
            "action": f"open_{direction}",
            "order_id": order_id,
            "symbol": symbol,
            "price": entry_price,
            "size": size,
            "leverage": leverage,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        return MockTradeResult(
            success=True,
            order_id=order_id,
            price=entry_price,
            size=size,
            take_profit_price=tp_price,
            stop_loss_price=sl_price
        )
    
    async def close_position(
        self,
        symbol: str = "BTC-USDT-SWAP",
        reason: str = ""
    ) -> MockTradeResult:
        """Close mock position."""
        position = self.positions.get(symbol)
        
        if not position:
            return MockTradeResult(
                success=False,
                error=f"No position found for {symbol}"
            )
        
        # Calculate P&L
        close_price = position.current_price
        pnl = position.unrealized_pnl
        
        # Update balance
        self.balance += pnl
        
        # Remove position
        del self.positions[symbol]
        
        # Record trade
        self.order_counter += 1
        order_id = f"mock_order_{self.order_counter}"
        
        self.trade_history.append({
            "action": "close",
            "order_id": order_id,
            "symbol": symbol,
            "price": close_price,
            "pnl": pnl,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        return MockTradeResult(
            success=True,
            order_id=order_id,
            price=close_price,
            pnl=pnl
        )
    
    def set_price(self, symbol: str, price: float) -> None:
        """
        Set current price for a position (for testing P&L).
        
        Args:
            symbol: Trading pair
            price: New current price
        """
        if symbol in self.positions:
            position = self.positions[symbol]
            position.current_price = price
            
            # Recalculate P&L
            price_diff = price - position.entry_price
            if position.direction == "short":
                price_diff = -price_diff
            
            position.unrealized_pnl = price_diff * position.size
            position.unrealized_pnl_percent = (
                position.unrealized_pnl / position.margin * 100
                if position.margin > 0 else 0
            )
    
    def reset(self) -> None:
        """Reset trader state for new test."""
        self.balance = self.initial_balance
        self.positions.clear()
        self.trade_history.clear()
        self.order_counter = 0
    
    def get_trade_count(self) -> int:
        """Get number of trades executed."""
        return len(self.trade_history)
