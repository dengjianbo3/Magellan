"""
Base Trader Abstract Class

Defines the common interface for all trader implementations (PaperTrader, OKXTrader, etc.)
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents an open trading position"""
    symbol: str
    direction: str  # "long" or "short"
    size: float  # Position size in base currency
    entry_price: float
    leverage: int
    margin: float  # Margin used (USDT)
    unrealized_pnl: float = 0.0
    tp_price: Optional[float] = None
    sl_price: Optional[float] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "size": self.size,
            "entry_price": self.entry_price,
            "leverage": self.leverage,
            "margin": self.margin,
            "unrealized_pnl": self.unrealized_pnl,
            "tp_price": self.tp_price,
            "sl_price": self.sl_price,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class Account:
    """Represents account balance information"""
    total_equity: float
    available_balance: float
    used_margin: float
    unrealized_pnl: float = 0.0
    
    @property
    def true_available_margin(self) -> float:
        """Available margin considering unrealized PnL"""
        return self.available_balance + min(0, self.unrealized_pnl)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_equity": self.total_equity,
            "available_balance": self.available_balance,
            "used_margin": self.used_margin,
            "unrealized_pnl": self.unrealized_pnl,
            "true_available_margin": self.true_available_margin
        }


class BaseTrader(ABC):
    """
    Abstract base class for trading implementations.
    
    All traders (Paper, OKX, Binance, etc.) should inherit from this class
    to ensure consistent API across different implementations.
    
    Usage:
        class MyTrader(BaseTrader):
            async def open_long(...): ...
            async def open_short(...): ...
            ...
    """
    
    def __init__(self, symbol: str = "BTC-USDT-SWAP"):
        self.symbol = symbol
        self._position: Optional[Position] = None
        self._current_price: float = 0.0
        self._on_position_closed_callback = None
        
    def register_position_closed_callback(self, callback):
        """Register callback to be called when position is closed"""
        self._on_position_closed_callback = callback
    
    @abstractmethod
    async def open_long(
        self,
        symbol: str = None,
        leverage: int = 1,
        amount_usdt: float = 0,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Open a long position.
        
        Args:
            symbol: Trading pair (default: instance symbol)
            leverage: Leverage multiplier (1-125)
            amount_usdt: Position size in USDT
            tp_price: Take profit price (optional)
            sl_price: Stop loss price (optional)
            
        Returns:
            Dict with:
                - success: bool
                - executed_price: float (if success)
                - position: dict (if success)
                - error: str (if failed)
        """
        pass
    
    @abstractmethod
    async def open_short(
        self,
        symbol: str = None,
        leverage: int = 1,
        amount_usdt: float = 0,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Open a short position.
        
        Args:
            symbol: Trading pair (default: instance symbol)
            leverage: Leverage multiplier (1-125)
            amount_usdt: Position size in USDT
            tp_price: Take profit price (optional)
            sl_price: Stop loss price (optional)
            
        Returns:
            Dict with:
                - success: bool
                - executed_price: float (if success)
                - position: dict (if success)
                - error: str (if failed)
        """
        pass
    
    @abstractmethod
    async def close_position(
        self,
        symbol: str = None,
        reason: str = "manual"
    ) -> Dict[str, Any]:
        """
        Close current position.
        
        Args:
            symbol: Trading pair (default: instance symbol)
            reason: Reason for closing
            
        Returns:
            Dict with:
                - success: bool
                - pnl: float (realized PnL)
                - exit_price: float
                - error: str (if failed)
        """
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str = None) -> Optional[Dict[str, Any]]:
        """
        Get current position info.
        
        Args:
            symbol: Trading pair (default: instance symbol)
            
        Returns:
            Position dict or None if no position
        """
        pass
    
    @abstractmethod
    async def get_account(self) -> Dict[str, Any]:
        """
        Get account balance info.
        
        Returns:
            Dict with:
                - total_equity: float
                - available_balance: float
                - used_margin: float
                - true_available_margin: float
                - unrealized_pnl: float
        """
        pass
    
    @abstractmethod
    async def update_price(self, price: float):
        """
        Update current market price.
        
        Args:
            price: Current market price
        """
        pass
    
    # Optional methods with default implementations
    
    async def add_to_position(
        self,
        symbol: str = None,
        amount_usdt: float = 0,
        leverage: int = None
    ) -> Dict[str, Any]:
        """
        Add to existing position.
        
        Default implementation: not supported
        """
        return {
            "success": False,
            "error": "add_to_position not supported by this trader"
        }
    
    async def set_tp_sl(
        self,
        symbol: str = None,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update take profit / stop loss prices.
        
        Default implementation: not supported
        """
        return {
            "success": False,
            "error": "set_tp_sl not supported by this trader"
        }
    
    async def get_trade_history(self, limit: int = 20) -> list:
        """
        Get trade history.
        
        Default implementation: returns empty list
        """
        return []
    
    def has_position(self) -> bool:
        """Check if there's an open position"""
        return self._position is not None
    
    def get_position_direction(self) -> Optional[str]:
        """Get current position direction"""
        return self._position.direction if self._position else None
