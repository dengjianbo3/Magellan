# Data Structures

This document defines the core data models used in the trading system.

## Table of Contents
1. [Trading Signal](#trading-signal)
2. [Agent Vote](#agent-vote)
3. [Position Context](#position-context)
4. [Agent Memory](#agent-memory)
5. [Trade Result](#trade-result)

---

## Trading Signal

The final output of a trading meeting - represents a trading decision.

```python
@dataclass
class TradingSignal:
    """Trading decision output from meeting"""
    
    # Core Decision
    direction: Literal["long", "short", "hold"]
    symbol: str = "BTC-USDT-SWAP"
    
    # Position Parameters
    leverage: int           # 1-20
    amount_percent: float   # 0.0-1.0 (percentage of equity)
    
    # Prices
    entry_price: float
    take_profit_price: float
    stop_loss_price: float
    
    # Confidence
    confidence: int         # 0-100
    reasoning: str
    
    # Consensus Info
    agents_consensus: Dict[str, str]  # {agent_name: direction}
    
    # Metadata
    timestamp: datetime
```

### Computed Properties

```python
@property
def risk_reward_ratio(self) -> float:
    """Calculate R:R ratio"""
    if self.direction == "long":
        risk = abs(self.entry_price - self.stop_loss_price)
        reward = abs(self.take_profit_price - self.entry_price)
    else:  # short
        risk = abs(self.stop_loss_price - self.entry_price)
        reward = abs(self.entry_price - self.take_profit_price)
    return reward / risk if risk > 0 else 0.0
```

---

## Agent Vote

Structured vote from an analyst agent in Phase 2.

```python
@dataclass
class AgentVote:
    """Vote from an analyst agent"""
    
    # Agent Info
    agent_id: str
    agent_name: str
    
    # Vote
    direction: Literal["long", "short", "hold", "close", "add_long", "add_short", "reverse"]
    confidence: int           # 0-100
    
    # Suggested Parameters
    suggested_leverage: int
    suggested_tp_percent: float
    suggested_sl_percent: float
    
    # Reasoning
    reasoning: str
```

### Direction Normalization

```python
DIRECTION_MAP = {
    # Long variations
    "long": "long", "做多": "long", "开多": "long",
    "buy": "long", "bullish": "long",
    
    # Short variations
    "short": "short", "做空": "short", "开空": "short",
    "sell": "short", "bearish": "short",
    
    # Hold variations
    "hold": "hold", "观望": "hold", "wait": "hold",
    "neutral": "hold",
    
    # Close
    "close": "close", "平仓": "close",
    
    # Special actions
    "add_long": "add_long",
    "add_short": "add_short",
    "reverse": "reverse"
}
```

---

## Position Context

Current position state, injected into agent prompts.

```python
@dataclass
class PositionContext:
    """Current position state for prompt injection"""
    
    # === Basic Info ===
    has_position: bool
    current_position: Optional[dict]
    
    # === Position Details ===
    direction: Optional[str]      # "long" or "short"
    entry_price: float
    current_price: float
    size: float                   # Position size in base currency
    leverage: int
    margin_used: float
    
    # === P&L ===
    unrealized_pnl: float
    unrealized_pnl_percent: float
    
    # === Risk Metrics ===
    liquidation_price: Optional[float]
    distance_to_liquidation_percent: float
    
    # === TP/SL ===
    take_profit_price: Optional[float]
    stop_loss_price: Optional[float]
    distance_to_tp_percent: float
    distance_to_sl_percent: float
    
    # === Account Status ===
    available_balance: float
    total_equity: float
    used_margin: float
    
    # === Position Limits ===
    max_position_percent: float
    current_position_percent: float
    can_add_position: bool
    max_additional_amount: float
    
    # === Holding Duration ===
    opened_at: Optional[datetime]
    holding_duration_hours: float
```

### Summary Method

```python
def to_summary(self) -> str:
    """Generate human-readable summary for prompt injection"""
    
    if not self.has_position:
        return """
## 📊 Current Position Status
**No current position** - Free to open new position

### Account Status
- Available Balance: ${:,.2f}
- Total Equity: ${:,.2f}
""".format(self.available_balance, self.total_equity)
    
    return """
## 📊 Current Position Status
**Direction**: {} {}
**Entry Price**: ${:,.2f}
**Current Price**: ${:,.2f}
**Leverage**: {}x

### P&L
- Unrealized P&L: ${:,.2f} ({:+.2f}%)

### Risk Levels
- Distance to Liquidation: {:.1f}%
- Distance to Take Profit: {:.1f}%
- Distance to Stop Loss: {:.1f}%

### Holding Duration
- Opened: {} ago
""".format(...)
```

---

## Agent Memory

Historical performance and learning for each agent.

```python
@dataclass
class AgentMemory:
    """Agent's historical performance and learning"""
    
    # === Identity ===
    agent_id: str
    agent_name: str
    
    # === Performance Statistics ===
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    win_rate: float           # 0.0-1.0
    average_pnl: float
    best_trade_pnl: float
    worst_trade_pnl: float
    
    # === Streaks ===
    consecutive_wins: int
    consecutive_losses: int
    max_consecutive_wins: int
    max_consecutive_losses: int
    
    # === Learning ===
    lessons_learned: List[str]
    recent_experiences: List[Dict]
    prediction_accuracy: Dict[str, float]  # {direction: accuracy}
    strengths: List[str]
    weaknesses: List[str]
    
    # === Reflection System ===
    recent_reflections: List[Dict]
    last_trade_summary: str
    current_focus: str
    common_mistakes: List[str]
    
    # === Metadata ===
    last_updated: datetime
```

### Context for Prompt

```python
def get_context_for_prompt(self) -> str:
    """Generate memory context for system prompt injection"""
    
    return """
## 📊 Last Trade Review
{status_emoji} Last trade: {last_trade_summary}
Lesson: {recent_lesson}

## ⚠️ Current Focus
{current_focus}

## 📝 Lessons You've Learned
{lessons_bullet_list}

## 📈 Your Trading Performance
- Total Trades: {total_trades}
- Win Rate: {win_rate:.1%}
- Total P&L: ${total_pnl:,.2f}
- Average P&L: ${average_pnl:,.2f}
- Current Win Streak: {consecutive_wins}

## 🚫 Mistakes to Avoid
{mistakes_bullet_list}

## ✅ Your Strengths
{strengths_bullet_list}

## 🔧 Areas for Improvement
{weaknesses_bullet_list}
""".format(...)
```

---

## Trade Result

Result of a completed trade, used for reflection generation.

```python
@dataclass
class TradeResult:
    """Completed trade result"""
    
    # === Trade Info ===
    trade_id: str
    symbol: str
    direction: str
    
    # === Execution ===
    entry_price: float
    exit_price: float
    leverage: int
    position_size: float
    
    # === Result ===
    pnl: float
    pnl_percent: float
    is_win: bool
    
    # === Close Details ===
    close_reason: Literal["tp", "sl", "manual", "liquidation"]
    holding_duration_hours: float
    
    # === Market Context ===
    entry_time: datetime
    exit_time: datetime
    market_conditions: Dict[str, Any]
```

---

## Type Definitions

### Direction Types

```python
from typing import Literal

Direction = Literal["long", "short", "hold"]
ExtendedDirection = Literal["long", "short", "hold", "close", "add_long", "add_short", "reverse"]
CloseReason = Literal["tp", "sl", "manual", "liquidation"]
RiskLevel = Literal["safe", "warning", "danger"]
```

### Configuration Types

```python
@dataclass
class RiskLimits:
    max_leverage: int = 20
    max_position_percent: float = 0.30
    min_position_percent: float = 0.10
    max_daily_loss_percent: float = 0.10
    consecutive_loss_limit: int = 3
    cooldown_hours: int = 24
    min_confidence: int = 60

@dataclass
class TradingConfig:
    analysis_interval_hours: int = 4
    symbol: str = "BTC-USDT-SWAP"
    initial_capital: float = 10000.0
    risk_limits: RiskLimits
    enabled: bool = True
    demo_mode: bool = False
```

---

## Related Documents

- [AGENT_DATA_FLOW.md](./AGENT_DATA_FLOW.md) - Data flow visualization
- [PHASE_DETAILS.md](./PHASE_DETAILS.md) - Phase information
- [MEMORY_SYSTEM.md](./MEMORY_SYSTEM.md) - Memory and reflection

---

*Last Updated: 2024-12-09*
