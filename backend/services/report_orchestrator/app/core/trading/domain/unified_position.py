"""
Unified Position Model

Single Position class that replaces PaperPosition and OKXPosition.
Provides a consistent interface across Paper and OKX trading modes.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Literal, Tuple, Dict, Any
from enum import Enum


class PositionSource(Enum):
    """Position data source."""
    PAPER = "paper"
    OKX = "okx"


@dataclass
class Position:
    """
    Unified Position Model.
    
    Replaces:
    - PaperPosition (paper_trader.py)
    - OKXPosition (okx_trader.py)
    
    Provides consistent interface for both trading modes.
    """
    # Core fields
    id: str
    symbol: str
    direction: Literal["long", "short"]
    size: float  # Position size (e.g., BTC amount)
    entry_price: float
    leverage: int
    margin: float  # Margin used (USDT)
    
    # TP/SL
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    
    # Calculated fields (updated by set_current_price)
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    liquidation_price: Optional[float] = None
    
    # Metadata
    opened_at: datetime = field(default_factory=datetime.now)
    source: PositionSource = PositionSource.PAPER
    
    # Extra OKX fields
    pos_id: Optional[str] = None  # OKX position ID
    algo_orders: Optional[Dict[str, str]] = None  # TP/SL algo order IDs
    
    def __post_init__(self):
        """Calculate derived fields after initialization."""
        if self.liquidation_price is None:
            self.liquidation_price = self.calculate_liquidation_price()
    
    def calculate_pnl(self, price: float = None) -> Tuple[float, float]:
        """
        Calculate unrealized PnL.
        
        Args:
            price: Optional price override. Uses current_price if not provided.
            
        Returns:
            Tuple of (pnl_usdt, pnl_percent)
        """
        if price is None:
            price = self.current_price
            
        if price <= 0 or self.entry_price <= 0:
            return 0.0, 0.0
        
        if self.direction == "long":
            pnl = (price - self.entry_price) * self.size
        else:
            pnl = (self.entry_price - price) * self.size
        
        pnl_percent = (pnl / self.margin) * 100 if self.margin > 0 else 0.0
        return pnl, pnl_percent
    
    def calculate_liquidation_price(self) -> float:
        """
        Calculate liquidation price.
        
        Uses simplified 80% margin loss for liquidation.
        OKX positions should use the OKX-provided liquidation price.
        
        Returns:
            Liquidation price
        """
        if self.size <= 0:
            return 0.0 if self.direction == "long" else float('inf')
        
        # Liquidate when loss reaches 80% of margin
        liquidation_loss = self.margin * 0.8
        
        if self.direction == "long":
            return max(0, self.entry_price - (liquidation_loss / self.size))
        else:
            return self.entry_price + (liquidation_loss / self.size)
    
    def set_current_price(self, price: float) -> None:
        """
        Update current price and recalculate PnL.
        
        Args:
            price: Current market price
        """
        self.current_price = price
        self.unrealized_pnl, self.unrealized_pnl_percent = self.calculate_pnl(price)
    
    def check_tp_triggered(self, price: float = None) -> bool:
        """Check if take profit is triggered."""
        if self.take_profit_price is None:
            return False
        
        check_price = price if price is not None else self.current_price
        
        if self.direction == "long":
            return check_price >= self.take_profit_price
        else:
            return check_price <= self.take_profit_price
    
    def check_sl_triggered(self, price: float = None) -> bool:
        """Check if stop loss is triggered."""
        if self.stop_loss_price is None:
            return False
        
        check_price = price if price is not None else self.current_price
        
        if self.direction == "long":
            return check_price <= self.stop_loss_price
        else:
            return check_price >= self.stop_loss_price
    
    def check_liquidation_triggered(self, price: float = None) -> bool:
        """Check if liquidation price is reached."""
        if self.liquidation_price is None:
            return False
        
        check_price = price if price is not None else self.current_price
        
        if self.direction == "long":
            return check_price <= self.liquidation_price
        else:
            return check_price >= self.liquidation_price
    
    @property
    def is_long(self) -> bool:
        return self.direction == "long"
    
    @property
    def is_short(self) -> bool:
        return self.direction == "short"
    
    @property
    def is_profitable(self) -> bool:
        return self.unrealized_pnl > 0
    
    @property
    def holding_duration_hours(self) -> float:
        """Get position holding duration in hours."""
        return (datetime.now() - self.opened_at).total_seconds() / 3600
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "direction": self.direction,
            "size": self.size,
            "entry_price": self.entry_price,
            "leverage": self.leverage,
            "margin": self.margin,
            "take_profit_price": self.take_profit_price,
            "stop_loss_price": self.stop_loss_price,
            "current_price": self.current_price,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_percent": self.unrealized_pnl_percent,
            "liquidation_price": self.liquidation_price,
            "opened_at": self.opened_at.isoformat(),
            "source": self.source.value,
            "pos_id": self.pos_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Position":
        """Create Position from dictionary."""
        # Handle datetime
        opened_at = data.get("opened_at")
        if isinstance(opened_at, str):
            opened_at = datetime.fromisoformat(opened_at)
        elif opened_at is None:
            opened_at = datetime.now()
        
        # Handle source enum
        source = data.get("source", "paper")
        if isinstance(source, str):
            source = PositionSource(source)
        
        return cls(
            id=data["id"],
            symbol=data["symbol"],
            direction=data["direction"],
            size=data["size"],
            entry_price=data["entry_price"],
            leverage=data["leverage"],
            margin=data["margin"],
            take_profit_price=data.get("take_profit_price"),
            stop_loss_price=data.get("stop_loss_price"),
            current_price=data.get("current_price", 0.0),
            unrealized_pnl=data.get("unrealized_pnl", 0.0),
            unrealized_pnl_percent=data.get("unrealized_pnl_percent", 0.0),
            liquidation_price=data.get("liquidation_price"),
            opened_at=opened_at,
            source=source,
            pos_id=data.get("pos_id"),
        )
    
    @classmethod
    def from_okx_response(
        cls,
        okx_data: Dict[str, Any],
        local_tp: float = None,
        local_sl: float = None
    ) -> "Position":
        """
        Create Position from OKX API response.
        
        Args:
            okx_data: OKX position data from API
            local_tp: Local take profit price (if not using OKX algo orders)
            local_sl: Local stop loss price (if not using OKX algo orders)
        """
        direction = "long" if okx_data.get("posSide") == "long" else "short"
        entry_price = float(okx_data.get("avgPx", 0))
        margin = float(okx_data.get("margin", 0))
        leverage = int(float(okx_data.get("lever", 1)))
        
        # Get size - try pos first, then notionalUSD / price
        size = abs(float(okx_data.get("pos", 0)))
        if size == 0 and entry_price > 0:
            notional = float(okx_data.get("notionalUsd", 0))
            size = notional / entry_price if notional else 0
        
        # Get OKX-calculated liquidation price
        liq_price = None
        liq_px_raw = okx_data.get("liqPx")
        if liq_px_raw and liq_px_raw != "":
            liq_price = float(liq_px_raw)
        
        # Current price and PnL from OKX
        current_price = float(okx_data.get("markPx", 0)) or float(okx_data.get("last", 0))
        unrealized_pnl = float(okx_data.get("upl", 0))
        unrealized_pnl_percent = float(okx_data.get("uplRatio", 0)) * 100
        
        # Position timestamp
        opened_at = datetime.now()
        ctime = okx_data.get("cTime")
        if ctime:
            try:
                opened_at = datetime.fromtimestamp(int(ctime) / 1000)
            except:
                pass
        
        return cls(
            id=okx_data.get("posId", f"okx_{datetime.now().timestamp()}"),
            symbol=okx_data.get("instId", "BTC-USDT-SWAP"),
            direction=direction,
            size=size,
            entry_price=entry_price,
            leverage=leverage,
            margin=margin,
            take_profit_price=local_tp,
            stop_loss_price=local_sl,
            current_price=current_price,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_percent=unrealized_pnl_percent,
            liquidation_price=liq_price,
            opened_at=opened_at,
            source=PositionSource.OKX,
            pos_id=okx_data.get("posId"),
        )
    
    @classmethod
    def from_paper_position(cls, paper_pos) -> "Position":
        """
        Create Position from legacy PaperPosition.
        
        For migration compatibility.
        """
        return cls(
            id=paper_pos.id,
            symbol=paper_pos.symbol,
            direction=paper_pos.direction,
            size=paper_pos.size,
            entry_price=paper_pos.entry_price,
            leverage=paper_pos.leverage,
            margin=paper_pos.margin,
            take_profit_price=getattr(paper_pos, 'take_profit_price', None),
            stop_loss_price=getattr(paper_pos, 'stop_loss_price', None),
            opened_at=paper_pos.opened_at,
            source=PositionSource.PAPER,
        )
