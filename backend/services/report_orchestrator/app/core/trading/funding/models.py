"""
Funding Fee Data Models

Core data structures for funding fee tracking and analysis.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class FundingDirection(Enum):
    """Direction of funding payment"""
    PAYING = "paying"      # Position holder pays
    RECEIVING = "receiving"  # Position holder receives


class RateTrend(Enum):
    """Funding rate trend"""
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"


class TradeViability(Enum):
    """Trade viability assessment"""
    VIABLE = "viable"           # Expected profit covers funding cost well
    MARGINAL = "marginal"       # Profit barely covers cost (warning)
    NOT_VIABLE = "not_viable"   # Funding cost exceeds expected profit


class EntryAction(Enum):
    """Entry timing action"""
    ENTER_NOW = "enter_now"     # Good to enter
    DELAY = "delay"             # Wait for settlement
    ENTER_AFTER_SETTLEMENT = "enter_after_settlement"  # Enter right after next settlement


class HoldingAlertLevel(Enum):
    """Holding alert level based on funding impact"""
    NORMAL = "normal"         # Funding < 20% of price PnL
    WARNING = "warning"       # Funding 20-40% of price PnL
    DANGER = "danger"         # Funding 40-50% of price PnL
    CRITICAL = "critical"     # Funding > 50% of price PnL (force close)


@dataclass
class FundingRate:
    """
    Current and historical funding rate data
    """
    symbol: str
    rate: float                      # Current rate (e.g., 0.0003 = 0.03%)
    rate_percent: float = field(init=False)  # Rate as percentage
    next_settlement_time: Optional[datetime] = None
    funding_interval_hours: int = 8
    
    # Historical averages (for context)
    avg_24h: float = 0.0
    avg_7d: float = 0.0
    
    # Analysis
    trend: RateTrend = RateTrend.STABLE
    is_extreme: bool = False         # > 0.1% is extreme
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.rate_percent = self.rate * 100
        self.is_extreme = abs(self.rate) > 0.001  # > 0.1%
    
    @property
    def minutes_to_settlement(self) -> int:
        """Minutes until next settlement"""
        if not self.next_settlement_time:
            return 999
        delta = self.next_settlement_time - datetime.now()
        return max(0, int(delta.total_seconds() / 60))
    
    def direction_for_position(self, position_direction: str) -> FundingDirection:
        """
        Determine if position pays or receives funding
        
        - Positive rate + Long = PAYING
        - Positive rate + Short = RECEIVING
        - Negative rate + Long = RECEIVING
        - Negative rate + Short = PAYING
        """
        is_long = position_direction.lower() == "long"
        if (self.rate > 0 and is_long) or (self.rate < 0 and not is_long):
            return FundingDirection.PAYING
        return FundingDirection.RECEIVING


@dataclass
class FundingBill:
    """
    Single funding fee settlement record
    """
    timestamp: datetime
    amount: float                    # Positive = received, Negative = paid
    position_value: float
    rate: float
    symbol: str = "BTC-USDT-SWAP"
    
    @property
    def is_payment(self) -> bool:
        """True if this was a payment (cost)"""
        return self.amount < 0


@dataclass
class HoldingCostEstimate:
    """
    Estimated cost of holding a position for a given duration
    """
    holding_hours: int
    settlement_count: int            # Number of settlements during hold
    
    # Cost estimates
    estimated_cost: float            # Expected cost in USDT
    min_cost: float                  # Optimistic (rate drops)
    max_cost: float                  # Pessimistic (rate increases)
    
    # As percentage of margin
    cost_percent_of_margin: float
    
    # Break-even analysis
    break_even_price_move: float     # Price must move this % to break even
    
    # Context
    assumed_rate: float
    leverage: int
    position_value: float


@dataclass
class EntryDecision:
    """
    Entry timing decision
    """
    action: EntryAction
    minutes_to_wait: int = 0
    reason: str = ""
    next_settlement: Optional[datetime] = None
    
    # If delaying, this is when to enter
    recommended_entry_time: Optional[datetime] = None


@dataclass
class HoldingAdvice:
    """
    Holding time advice for a position
    """
    current_holding_hours: float
    recommended_max_hours: int
    
    # Impact assessment
    accumulated_funding: float       # Total funding paid/received so far
    funding_impact_percent: float    # Funding as % of price PnL
    
    alert_level: HoldingAlertLevel
    advice: str                      # Human-readable advice


@dataclass
class TruePnL:
    """
    True PnL including all costs
    """
    # Price-based PnL
    price_pnl: float                 # (exit - entry) × size
    price_pnl_percent: float         # As % of margin
    
    # Funding fees
    funding_pnl: float               # Accumulated funding (negative = paid)
    funding_count: int               # Number of settlements experienced
    avg_funding_rate: float          # Average rate during holding
    
    # Trading fees
    trading_fees: float              # Open + close fees
    
    # True result
    true_pnl: float = field(init=False)
    true_pnl_percent: float = field(init=False)
    
    # Analysis
    funding_impact_percent: float = field(init=False)  # How much funding affected
    
    margin: float = 0.0              # For percentage calculations
    
    def __post_init__(self):
        self.true_pnl = self.price_pnl + self.funding_pnl - self.trading_fees
        
        if self.margin > 0:
            self.true_pnl_percent = (self.true_pnl / self.margin) * 100
            self.price_pnl_percent = (self.price_pnl / self.margin) * 100
        else:
            self.true_pnl_percent = 0
            self.price_pnl_percent = 0
        
        # Funding impact as % of price PnL
        if abs(self.price_pnl) > 0.01:
            self.funding_impact_percent = abs(self.funding_pnl) / abs(self.price_pnl) * 100
        else:
            self.funding_impact_percent = 0 if self.funding_pnl == 0 else 100
    
    @property
    def summary(self) -> str:
        """Human-readable summary"""
        impact_str = ""
        if self.funding_impact_percent > 100:
            impact_str = f"⚠️ 资金费吞噬了 {self.funding_impact_percent:.0f}% 的价差利润"
        elif self.funding_impact_percent > 50:
            impact_str = f"⚠️ 资金费占价差利润的 {self.funding_impact_percent:.0f}%"
        elif self.funding_impact_percent > 20:
            impact_str = f"资金费影响: {self.funding_impact_percent:.0f}%"
        else:
            impact_str = f"资金费影响较小: {self.funding_impact_percent:.0f}%"
        
        return f"""
价差盈亏: ${self.price_pnl:+.2f} ({self.price_pnl_percent:+.2f}%)
资金费用: ${self.funding_pnl:+.2f} ({self.funding_count}次结算)
交易手续费: -${self.trading_fees:.2f}
─────────────
真实盈亏: ${self.true_pnl:+.2f} ({self.true_pnl_percent:+.2f}%)
{impact_str}
"""
