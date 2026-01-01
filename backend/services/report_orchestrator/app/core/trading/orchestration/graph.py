"""
Trading Graph

LangGraph workflow definition for trading decisions.
Orchestrates the flow between analysis, consensus, execution, and reflection.
"""

import logging
from typing import Dict, Any, Optional, Callable, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import TradingState, create_initial_state
from .nodes import (
    market_analysis_node,
    signal_generation_node,
    risk_assessment_node,
    consensus_node,
    execution_node,
    react_fallback_node,
    reflection_node
)

logger = logging.getLogger(__name__)


def should_fallback(state: TradingState) -> Literal["fallback", "continue"]:
    """
    Conditional edge: Check if we should trigger fallback.
    """
    if state.get("should_fallback") or state.get("error"):
        return "fallback"
    return "continue"


def should_reflect(state: TradingState) -> Literal["reflect", "end"]:
    """
    Conditional edge: Check if we should generate reflection.
    """
    signal = state.get("final_signal", {})
    direction = signal.get("direction", "hold")
    
    # Only reflect on actual trades, not holds
    if direction in ("long", "short"):
        return "reflect"
    return "end"


def should_execute_or_fallback(state: TradingState) -> Literal["execute", "fallback"]:
    """
    Conditional edge: After consensus, check if we can execute.
    """
    if state.get("risk_blocked"):
        return "execute"  # Execute will return HOLD signal
    if state.get("error"):
        return "fallback"
    return "execute"


def build_trading_graph() -> StateGraph:
    """
    Build the trading workflow graph.
    
    Flow:
    ```
    start
      ↓
    market_analysis
      ↓
    signal_generation
      ↓
    risk_assessment
      ↓
    consensus
      ↓ (check)
    execution ──→ (success) → reflection → END
      ↓ (failure)
    react_fallback → END
    ```
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph
    workflow = StateGraph(TradingState)
    
    # Add nodes
    workflow.add_node("market_analysis", market_analysis_node)
    workflow.add_node("signal_generation", signal_generation_node)
    workflow.add_node("risk_assessment", risk_assessment_node)
    workflow.add_node("consensus", consensus_node)
    workflow.add_node("execution", execution_node)
    workflow.add_node("react_fallback", react_fallback_node)
    workflow.add_node("reflection", reflection_node)
    
    # Set entry point
    workflow.set_entry_point("market_analysis")
    
    # Add edges - main flow
    workflow.add_edge("market_analysis", "signal_generation")
    workflow.add_edge("signal_generation", "risk_assessment")
    workflow.add_edge("risk_assessment", "consensus")
    
    # After consensus, check if we should execute or fallback
    workflow.add_conditional_edges(
        "consensus",
        should_execute_or_fallback,
        {
            "execute": "execution",
            "fallback": "react_fallback"
        }
    )
    
    # After execution, check if we should reflect or end
    workflow.add_conditional_edges(
        "execution",
        should_reflect,
        {
            "reflect": "reflection",
            "end": END
        }
    )
    
    # Fallback always ends
    workflow.add_edge("react_fallback", END)
    
    # Reflection always ends
    workflow.add_edge("reflection", END)
    
    return workflow


class TradingGraph:
    """
    High-level interface for the trading workflow graph.
    
    Usage:
        graph = TradingGraph()
        result = await graph.run(
            trigger_reason="scheduled",
            market_data={...},
            position_context={...},
            agent_votes=[...]
        )
    """
    
    def __init__(
        self,
        checkpointer: Optional[Any] = None,
        on_node_complete: Optional[Callable] = None
    ):
        """
        Initialize the trading graph.
        
        Args:
            checkpointer: Optional checkpointer for persistence
            on_node_complete: Callback for node completion events
        """
        self.workflow = build_trading_graph()
        self.checkpointer = checkpointer or MemorySaver()
        self.on_node_complete = on_node_complete
        
        # Compile the graph
        self.graph = self.workflow.compile(checkpointer=self.checkpointer)
        
        logger.info("[TradingGraph] ✅ Graph compiled successfully")
    
    async def run(
        self,
        trigger_reason: str,
        symbol: str = "BTC-USDT-SWAP",
        market_data: Dict = None,
        position_context: Dict = None,
        agent_votes: list = None,
        agent_weights: Dict = None,
        thread_id: str = None,
        leader_agent: Any = None,
        trade_executor: Any = None  # ExecutorAgent instance for execution_node
    ) -> TradingState:
        """
        Run the trading workflow.
        
        Args:
            trigger_reason: Why the workflow was triggered
            symbol: Trading symbol
            market_data: Current market data
            position_context: Current position info
            agent_votes: Pre-computed agent votes (optional)
            agent_weights: Agent weight multipliers (optional)
            thread_id: Thread ID for checkpointing
            leader_agent: Leader agent instance for summary generation
            trade_executor: ExecutorAgent instance for execution decisions
            
        Returns:
            Final TradingState with results
        """
        logger.info(f"[TradingGraph] 🚀 Starting workflow - Trigger: {trigger_reason}")
        
        # Create initial state
        initial_state = create_initial_state(
            trigger_reason=trigger_reason,
            symbol=symbol,
            market_data=market_data,
            position_context=position_context
        )
        
        # Add pre-computed values if provided
        if agent_votes:
            initial_state["agent_votes"] = agent_votes
        if agent_weights:
            initial_state["agent_weights"] = agent_weights
        
        # Run the graph - pass agents via config (non-serializable, ephemeral)
        config = {
            "configurable": {
                "thread_id": thread_id or "default",
                "leader_agent": leader_agent,
                "trade_executor": trade_executor  # 🔧 NEW: Pass to execution_node
            }
        }
        
        try:
            # Stream through nodes
            final_state = initial_state
            async for event in self.graph.astream(initial_state, config=config):
                # Each event is a dict with node name as key
                for node_name, node_state in event.items():
                    logger.debug(f"[TradingGraph] Node completed: {node_name}")
                    
                    # Merge node state into final state
                    final_state = {**final_state, **node_state}
                    
                    # Call callback if provided
                    if self.on_node_complete:
                        try:
                            await self.on_node_complete(node_name, node_state)
                        except Exception as e:
                            logger.warning(f"Callback error: {e}")
            
            # Log completion
            signal = final_state.get("final_signal", {})
            direction = signal.get("direction", "unknown")
            confidence = signal.get("confidence", 0)
            logger.info(
                f"[TradingGraph] ✅ Workflow complete - "
                f"Signal: {direction.upper()} ({confidence}%) - "
                f"Nodes: {' → '.join(final_state.get('completed_nodes', []))}"
            )
            
            return final_state
            
        except Exception as e:
            logger.error(f"[TradingGraph] ❌ Workflow failed: {e}", exc_info=True)
            
            # Return error state with HOLD signal
            return {
                **initial_state,
                "error": str(e),
                "execution_success": False,
                "final_signal": {
                    "direction": "hold",
                    "confidence": 0,
                    "leverage": 0,
                    "amount_percent": 0,
                    "reasoning": f"Workflow error: {e}"
                }
            }
    
    async def run_single_node(
        self,
        node_name: str,
        state: TradingState
    ) -> TradingState:
        """
        Run a single node for testing or debugging.
        
        Args:
            node_name: Name of the node to run
            state: Current state
            
        Returns:
            Updated state after node execution
        """
        node_map = {
            "market_analysis": market_analysis_node,
            "signal_generation": signal_generation_node,
            "risk_assessment": risk_assessment_node,
            "consensus": consensus_node,
            "execution": execution_node,
            "react_fallback": react_fallback_node,
            "reflection": reflection_node
        }
        
        if node_name not in node_map:
            raise ValueError(f"Unknown node: {node_name}")
        
        node_fn = node_map[node_name]
        result = await node_fn(state)
        
        return {**state, **result}
    
    def get_graph_visualization(self) -> str:
        """
        Get a text representation of the graph for debugging.
        """
        return """
Trading Workflow Graph:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
          ┌─────────────────┐
          │  market_analysis │
          └────────┬────────┘
                   ↓
          ┌─────────────────┐
          │signal_generation │
          └────────┬────────┘
                   ↓
          ┌─────────────────┐
          │ risk_assessment  │
          └────────┬────────┘
                   ↓
          ┌─────────────────┐
          │    consensus     │
          └────────┬────────┘
                   ↓
         ┌────────┴────────┐
         ↓ (success)       ↓ (error)
    ┌──────────┐    ┌───────────────┐
    │ execution │    │ react_fallback │
    └─────┬────┘    └───────┬───────┘
          ↓                 ↓
   ┌──────┴─────┐          END
   ↓ (trade)    ↓ (hold)
┌──────────┐    │
│reflection│    │
└────┬─────┘    │
     ↓          ↓
    END        END

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
