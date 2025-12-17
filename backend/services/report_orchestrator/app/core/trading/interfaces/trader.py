"""
ITrader Interface

Abstract base class defining the contract for all trader implementations.
Both OKXTrader and PaperTrader must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Position:
    """Represents a trading position."""
    id: str
    symbol: str
    direction: str  # "long" or "short"
    size: float  # Amount in base currency (e.g., BTC)
    entry_price: float
    current_price: float
    leverage: int
    margin: float  # Collateral in quote currency (e.g., USDT)
    unrealized_pnl: float
    unrealized_pnl_percent: float
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    liquidation_price: Optional[float] = None
    opened_at: Optional[datetime] = None


@dataclass
class AccountBalance:
    """Represents account balance state."""
    total_equity: float  # Total account value
    available_balance: float  # Available for new positions
    used_margin: float  # Currently used as collateral
    unrealized_pnl: float  # Floating P&L
    max_avail_size: float  # Max position size allowed


@dataclass
class TradeResult:
    """Result of a trade operation."""
    success: bool
    order_id: Optional[str] = None
    symbol: str = ""
    direction: str = ""
    size: float = 0.0
    price: float = 0.0
    leverage: int = 1
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    message: str = ""
    error: Optional[str] = None
    timestamp: Optional[datetime] = None


class ITrader(ABC):
    """
    Abstract trader interface.
    
    All trader implementations (OKXTrader, PaperTrader) must implement
    this interface to ensure consistent behavior and enable testing.
    """
    
    @abstractmethod
    async def open_long(
        self,
        symbol: str,
        leverage: int,
        amount_usdt: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        reason: str = ""
    ) -> TradeResult:
        """
        Open a long position.
        
        Args:
            symbol: Trading pair (e.g., "BTC-USDT-SWAP")
            leverage: Leverage multiplier (1-125)
            amount_usdt: Position size in USDT
            tp_price: Take profit price (optional)
            sl_price: Stop loss price (optional)
            reason: Reason for the trade (for logging)
            
        Returns:
            TradeResult with operation outcome
        """
        pass
    
    @abstractmethod
    async def open_short(
        self,
        symbol: str,
        leverage: int,
        amount_usdt: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        reason: str = ""
    ) -> TradeResult:
        """
        Open a short position.
        
        Args:
            symbol: Trading pair (e.g., "BTC-USDT-SWAP")
            leverage: Leverage multiplier (1-125)
            amount_usdt: Position size in USDT
            tp_price: Take profit price (optional)
            sl_price: Stop loss price (optional)
            reason: Reason for the trade (for logging)
            
        Returns:
            TradeResult with operation outcome
        """
        pass
    
    @abstractmethod
    async def close_position(self, symbol: str, reason: str = "") -> TradeResult:
        """
        Close an existing position.
        
        Args:
            symbol: Trading pair to close
            reason: Reason for closing (for logging)
            
        Returns:
            TradeResult with operation outcome
        """
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get current position for a symbol.
        
        Args:
            symbol: Trading pair to query
            
        Returns:
            Position if exists, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_account(self) -> AccountBalance:
        """
        Get account balance information.
        
        Returns:
            AccountBalance with current account state
        """
        pass
    
    @abstractmethod
    async def get_current_price(self, symbol: str) -> float:
        """
        Get current market price for a symbol.
        
        Args:
            symbol: Trading pair to query
            
        Returns:
            Current market price
        """
        pass
    
    @abstractmethod
    async def get_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get trade history.
        
        Args:
            symbol: Filter by symbol (optional)
            limit: Maximum number of trades to return
            
        Returns:
            List of historical trades
        """
        pass
