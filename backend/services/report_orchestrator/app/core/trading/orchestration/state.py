"""
Trading State

Defines the state that flows through the LangGraph trading workflow.
All nodes read from and write to this shared state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict, List, Dict, Optional, Any, Annotated
from enum import Enum
import operator


class TriggerReason(str, Enum):
    """Reason for triggering the trading workflow."""
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    TP_SL = "tp_sl"
    STARTUP = "startup"
    PRICE_ALERT = "price_alert"


class TradeDirection(str, Enum):
    """Trading direction."""
    LONG = "long"
    SHORT = "short"
    HOLD = "hold"
    CLOSE = "close"


class NodeResult(str, Enum):
    """Result status from a node execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    SKIP = "skip"


@dataclass
class AgentVoteState:
    """Agent vote in the workflow state."""
    agent_id: str
    agent_name: str
    direction: str
    confidence: int
    reasoning: str
    weight: float = 1.0
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "direction": self.direction,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "weight": self.weight
        }


@dataclass
class SignalState:
    """Trading signal in the workflow state."""
    direction: str
    confidence: int
    leverage: int
    amount_percent: float
    tp_percent: float
    sl_percent: float
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "confidence": self.confidence,
            "leverage": self.leverage,
            "amount_percent": self.amount_percent,
            "tp_percent": self.tp_percent,
            "sl_percent": self.sl_percent,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat()
        }


class TradingState(TypedDict, total=False):
    """
    Trading workflow state.
    
    This state flows through all nodes in the LangGraph workflow.
    Each node reads from and writes to specific fields.
    
    Flow:
    1. market_analysis: Reads market_data, writes analysis
    2. signal_generation: Reads analysis, writes agent_votes
    3. risk_assessment: Reads agent_votes + position, writes risk_assessment
    4. consensus: Reads agent_votes + risk, writes leader_summary
    5. execution: Reads all, writes execution_result + final_signal
    6. react_fallback: Only on failure, writes final_signal
    7. reflection: After execution, writes reflection
    """
    
    # === Input (set at workflow start) ===
    trigger_reason: str
    trigger_timestamp: str
    symbol: str
    
    # Market data
    market_data: Dict[str, Any]  # Current prices, indicators, etc.
    
    # Current position context
    position_context: Dict[str, Any]
    has_position: bool
    current_direction: Optional[str]
    
    # === Phase 1: Market Analysis ===
    analysis: Dict[str, Any]  # Aggregated market analysis
    
    # === Phase 2: Signal Generation ===
    agent_votes: Annotated[List[Dict], operator.add]  # Append-only list
    agent_weights: Dict[str, float]
    
    # === Phase 3: Risk Assessment ===
    risk_assessment: Dict[str, Any]
    risk_level: str  # "low", "medium", "high", "extreme"
    risk_blocked: bool
    
    # === Phase 4: Consensus ===
    leader_summary: str
    consensus_direction: str
    consensus_confidence: int
    weighted_confidence: float
    
    # === Phase 5: Execution ===
    final_signal: Optional[Dict[str, Any]]
    execution_result: Optional[Dict[str, Any]]
    execution_success: bool
    
    # === Error Handling ===
    error: Optional[str]
    error_node: Optional[str]
    should_fallback: bool
    fallback_iterations: int
    
    # === Reflection ===
    reflection: Optional[Dict[str, Any]]
    
    # === Control Flow ===
    current_node: str
    completed_nodes: List[str]
    node_timings: Dict[str, float]  # Node execution times in ms


def create_initial_state(
    trigger_reason: str,
    symbol: str = "BTC-USDT-SWAP",
    market_data: Dict = None,
    position_context: Dict = None
) -> TradingState:
    """
    Create initial state for a trading workflow run.
    
    Args:
        trigger_reason: Why the workflow was triggered
        symbol: Trading symbol
        market_data: Current market data
        position_context: Current position info
        
    Returns:
        TradingState ready for workflow execution
    """
    pos_ctx = position_context or {}
    
    return TradingState(
        # Input
        trigger_reason=trigger_reason,
        trigger_timestamp=datetime.now().isoformat(),
        symbol=symbol,
        market_data=market_data or {},
        position_context=pos_ctx,
        has_position=pos_ctx.get("has_position", False),
        current_direction=pos_ctx.get("direction"),
        
        # Initialize empty/default values
        analysis={},
        agent_votes=[],
        agent_weights={},
        risk_assessment={},
        risk_level="unknown",
        risk_blocked=False,
        leader_summary="",
        consensus_direction="hold",
        consensus_confidence=0,
        weighted_confidence=0.0,
        final_signal=None,
        execution_result=None,
        execution_success=False,
        error=None,
        error_node=None,
        should_fallback=False,
        fallback_iterations=0,
        reflection=None,
        current_node="start",
        completed_nodes=[],
        node_timings={}
    )


def state_summary(state: TradingState) -> str:
    """Generate a human-readable summary of the current state."""
    lines = [
        f"=== Trading State Summary ===",
        f"Trigger: {state.get('trigger_reason', 'unknown')}",
        f"Symbol: {state.get('symbol', 'unknown')}",
        f"Position: {state.get('current_direction', 'none')}",
        f"",
        f"Votes: {len(state.get('agent_votes', []))}",
        f"Consensus: {state.get('consensus_direction', 'none')} ({state.get('consensus_confidence', 0)}%)",
        f"Risk: {state.get('risk_level', 'unknown')}",
        f"",
        f"Executed: {state.get('execution_success', False)}",
        f"Error: {state.get('error', 'none')}",
        f"Nodes: {' → '.join(state.get('completed_nodes', []))}",
    ]
    return "\n".join(lines)
