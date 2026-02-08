"""
Trading Workflow Nodes

Defines all nodes for the LangGraph trading workflow.
Each node is an async function that takes state and returns updated state.

Observability: Uses structured logging with trace ID and Prometheus metrics.
"""

import time
from datetime import datetime
from typing import Dict, Any, List
import json
import traceback

from langchain_core.runnables import RunnableConfig
from .state import TradingState
from app.core.trading.executor_agent import ExecutorAgent
from app.core.trading.mode_manager import (
    get_mode_manager,
    TradingMode,
    ExecutionAction,
)
from app.core.trading.constants import CONFIDENCE, LEVERAGE

# Observability imports
from app.core.observability.logging import get_logger, TradingLogger
from app.core.observability.metrics import (
    signals_generated,
    execution_failures,
    signal_generation_latency,
)

logger = get_logger(__name__)
trading_logger = TradingLogger(__name__)


async def market_analysis_node(state: TradingState) -> Dict[str, Any]:
    """
    Node 1: Market Analysis
    
    Gathers and analyzes market data.
    Input: market_data
    Output: analysis
    """
    start_time = time.time()
    logger.info("node_started", node="market_analysis")
    
    try:
        market_data = state.get("market_data", {})
        
        # Extract key metrics
        trend = _determine_trend(market_data)
        analysis = {
            "current_price": market_data.get("current_price", 0),
            "price_change_24h": market_data.get("price_change_24h", 0),
            "volume_24h": market_data.get("volume_24h", 0),
            "fear_greed_index": market_data.get("fear_greed_index", 50),
            "trend": trend,
            "volatility": market_data.get("volatility", "medium"),
            "timestamp": datetime.now().isoformat()
        }
        
        elapsed = (time.time() - start_time) * 1000
        logger.info("node_completed", 
            node="market_analysis", 
            duration_ms=elapsed,
            trend=trend,
            current_price=analysis["current_price"]
        )
        
        return {
            "analysis": analysis,
            "current_node": "market_analysis",
            "completed_nodes": state.get("completed_nodes", []) + ["market_analysis"],
            "node_timings": {**state.get("node_timings", {}), "market_analysis": elapsed}
        }
        
    except Exception as e:
        logger.error("node_failed", node="market_analysis", error=str(e))
        return {
            "error": str(e),
            "error_node": "market_analysis",
            "should_fallback": True
        }


async def signal_generation_node(state: TradingState) -> Dict[str, Any]:
    """
    Node 2: Signal Generation
    
    Runs all analyst agents in parallel to generate signals.
    Input: analysis, market_data
    Output: agent_votes
    """
    start_time = time.time()
    mode = state.get("mode", "full_auto")
    logger.info("node_started", node="signal_generation", mode=mode)
    
    try:
        # Track signal generation latency with Prometheus
        with signal_generation_latency.labels(mode=mode).time():
            # This will be replaced with actual agent calls
            # For now, use placeholder votes from context
            existing_votes = state.get("agent_votes", [])
            
            if not existing_votes:
                logger.warning("no_agent_votes", node="signal_generation")
        
        elapsed = (time.time() - start_time) * 1000
        logger.info("node_completed",
            node="signal_generation",
            duration_ms=elapsed,
            vote_count=len(existing_votes)
        )
        
        return {
            "current_node": "signal_generation",
            "completed_nodes": state.get("completed_nodes", []) + ["signal_generation"],
            "node_timings": {**state.get("node_timings", {}), "signal_generation": elapsed}
        }
        
    except Exception as e:
        logger.error("node_failed", node="signal_generation", error=str(e))
        return {
            "error": str(e),
            "error_node": "signal_generation",
            "should_fallback": True
        }


async def risk_assessment_node(state: TradingState, config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Node 3: Risk Assessment
    
    Evaluates risk based on votes and current position.
    Uses RiskAssessor LLM when available, with fallback to threshold logic.
    Input: agent_votes, position_context
    Output: risk_assessment, risk_level, risk_blocked
    """
    start_time = time.time()
    logger.info("[Node: risk_assessment] Evaluating risk...")
    
    try:
        votes = state.get("agent_votes", [])
        position = state.get("position_context", {})
        market_data = state.get("market_data", {})
        
        # Get on_message callback for broadcasting to frontend
        on_message = None
        risk_agent = None
        if config:
            on_message = config.get("configurable", {}).get("on_message")
            risk_agent = config.get("configurable", {}).get("risk_agent")
        
        has_position = position.get("has_position", False)
        
        # 🆕 Use RiskAssessor LLM if available (100% parity with traditional flow)
        if risk_agent:
            logger.info("[Node: risk_assessment] 🧠 Using RiskAssessor LLM for comprehensive assessment...")
            llm_result = await _generate_llm_risk_assessment(
                risk_agent, votes, position, market_data
            )
            
            risk_message = llm_result["risk_message"]
            risk_level = llm_result["risk_level"]
            risk_blocked = llm_result["risk_blocked"]
            block_reason = llm_result["block_reason"]
            avg_confidence = llm_result["avg_confidence"]
            
            logger.info(f"[Node: risk_assessment] LLM result: {risk_level}, blocked={risk_blocked}")
        else:
            # Fallback to simple threshold logic
            logger.info("[Node: risk_assessment] ⚠️ No RiskAssessor agent, using threshold logic fallback...")
            avg_confidence = _calculate_avg_confidence(votes)
            
            # Determine risk level based on confidence thresholds
            if avg_confidence >= CONFIDENCE.HIGH:
                risk_level = "low"
            elif avg_confidence >= CONFIDENCE.MEDIUM:
                risk_level = "medium"
            elif avg_confidence >= CONFIDENCE.LOW:
                risk_level = "high"
            else:
                risk_level = "extreme"
            
            # Check if we should block execution
            risk_blocked = False
            block_reason = None
            
            if risk_level == "extreme":
                risk_blocked = True
                block_reason = "Extreme risk level - confidence too low"
            elif has_position and state.get("trigger_reason") == "startup":
                # Block auto-reverse on startup
                current_dir = state.get("current_direction")
                consensus_dir = _get_consensus_direction(votes)
                if current_dir and consensus_dir and current_dir != consensus_dir and consensus_dir != "hold":
                    risk_blocked = True
                    block_reason = f"Startup protection: blocked reverse from {current_dir} to {consensus_dir}"
            
            # Generate fallback risk message
            risk_message = _generate_risk_assessment_message(
                votes, avg_confidence, risk_level, risk_blocked, block_reason, has_position
            )
        
        risk_assessment = {
            "avg_confidence": avg_confidence,
            "vote_count": len(votes),
            "risk_level": risk_level,
            "blocked": risk_blocked,
            "block_reason": block_reason,
            "has_position": has_position,
            "timestamp": datetime.now().isoformat()
        }
        
        # Broadcast Risk Manager message to frontend
        if on_message and risk_message:
            try:
                import asyncio
                msg_data = {
                    "agent_id": "RiskAssessor",
                    "agent_name": "Risk Manager",
                    "content": risk_message,
                    "message_type": "risk_assessment",
                    "timestamp": datetime.now().isoformat()
                }
                # Handle both sync and async callbacks
                result = on_message(msg_data)
                if asyncio.iscoroutine(result):
                    await result
                logger.info("[Node: risk_assessment] 📢 Risk Manager message broadcasted to frontend")
            except Exception as e:
                logger.warning(f"[Node: risk_assessment] Failed to broadcast Risk Manager message: {e}")
        
        elapsed = (time.time() - start_time) * 1000
        status = "BLOCKED" if risk_blocked else risk_level.upper()
        logger.info(f"[Node: risk_assessment] ✅ Complete in {elapsed:.0f}ms - Risk: {status}")
        
        return {
            "risk_assessment": risk_assessment,
            "risk_level": risk_level,
            "risk_blocked": risk_blocked,
            "current_node": "risk_assessment",
            "completed_nodes": state.get("completed_nodes", []) + ["risk_assessment"],
            "node_timings": {**state.get("node_timings", {}), "risk_assessment": elapsed}
        }
        
    except Exception as e:
        logger.error(f"[Node: risk_assessment] ❌ Failed: {e}")
        return {
            "error": str(e),
            "error_node": "risk_assessment",
            "should_fallback": True
        }


async def consensus_node(state: TradingState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node 4: Consensus Building

    Synthesizes votes into a consensus decision.
    Input: agent_votes, risk_assessment, agent_weights
    Output: leader_summary, consensus_direction, consensus_confidence

    🆕 P0 Fix: Now uses WeightLearner for dynamic agent weights based on historical accuracy.
    """
    start_time = time.time()
    logger.info("[Node: consensus] Building consensus...")

    try:
        votes = state.get("agent_votes", [])
        risk_blocked = state.get("risk_blocked", False)

        # 🆕 P0: Use WeightLearner for dynamic weights (falls back to static if unavailable)
        static_weights = state.get("agent_weights", {})
        try:
            from app.core.trading.weight_learner import get_learned_weights
            learned_weights = await get_learned_weights()
            # Merge: learned weights take priority, fall back to static
            weights = {**static_weights, **learned_weights}
            if learned_weights:
                logger.info(f"[Node: consensus] 🧠 Using learned weights: {learned_weights}")
        except Exception as e:
            logger.warning(f"[Node: consensus] WeightLearner unavailable, using static weights: {e}")
            weights = static_weights
        
        # Get on_message callback for broadcasting to frontend
        on_message = config.get("configurable", {}).get("on_message")
        
        if risk_blocked:
            # Risk blocked - force HOLD
            consensus_direction = "hold"
            consensus_confidence = 0
            leader_summary = f"Risk assessment blocked execution: {state.get('risk_assessment', {}).get('block_reason', 'unknown')}"
        elif not votes:
            # No votes - HOLD
            consensus_direction = "hold"
            consensus_confidence = 0
            leader_summary = "No agent votes available - defaulting to HOLD"
            echo_chamber_result = None
        else:
        # Calculate weighted consensus
            consensus_direction, consensus_confidence, weighted_conf = _calculate_weighted_consensus(votes, weights)
            
            # 🆕 ANTI-BIAS: Echo Chamber Detection
            # When 80%+ of agents agree, it may be groupthink - reduce confidence
            from app.core.trading.anti_bias import get_echo_chamber_detector
            echo_detector = get_echo_chamber_detector()
            echo_chamber_result = echo_detector.check(votes)
            
            if echo_chamber_result.status.value == "echo_chamber_detected":
                logger.warning(f"[Node: consensus] {echo_chamber_result.warning_message}")
                # Apply confidence penalty
                original_confidence = consensus_confidence
                consensus_confidence = echo_detector.apply_penalty(consensus_confidence, echo_chamber_result)
                logger.info(f"[Node: consensus] Confidence adjusted: {original_confidence}% → {consensus_confidence}% (Echo Chamber penalty)")
            
            # 🔧 RESTORE: Use Leader Agent to generate comprehensive summary if available
            # Retrieve leader_agent from config (not state, to avoid serialization issues)
            leader_agent = config.get("configurable", {}).get("leader_agent")
            
            if leader_agent:
                try:
                    logger.info("[Node: consensus] 🧠 Generating comprehensive Leader summary via LLM...")
                    leader_summary = await _generate_llm_leader_summary(
                        leader_agent, 
                        votes, 
                        state.get("position_context", {}),
                        state.get("market_data", {}),
                        echo_chamber_warning=echo_chamber_result.warning_message if echo_chamber_result and echo_chamber_result.status.value == "echo_chamber_detected" else None
                    )
                except Exception as e:
                    logger.error(f"[Node: consensus] ❌ Failed to generate LLM summary: {e}")
                    leader_summary = _generate_leader_summary(votes, consensus_direction, consensus_confidence)
            else:
                leader_summary = _generate_leader_summary(votes, consensus_direction, consensus_confidence)
        
        # 🆕 Broadcast Leader message to frontend
        if on_message and leader_summary:
            try:
                import asyncio
                msg_data = {
                    "agent_id": "Leader",
                    "agent_name": "Leader",
                    "content": leader_summary,
                    "message_type": "consensus",
                    "timestamp": datetime.now().isoformat()
                }
                # Handle both sync and async callbacks
                result = on_message(msg_data)
                if asyncio.iscoroutine(result):
                    await result
                logger.info("[Node: consensus] 📢 Leader message broadcasted to frontend")
            except Exception as e:
                logger.warning(f"[Node: consensus] Failed to broadcast Leader message: {e}")
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"[Node: consensus] ✅ Complete in {elapsed:.0f}ms - {consensus_direction.upper()} ({consensus_confidence}%)")
        
        return {
            "leader_summary": leader_summary,
            "consensus_direction": consensus_direction,
            "consensus_confidence": consensus_confidence,
            "weighted_confidence": weighted_conf if 'weighted_conf' in locals() else 0.0,
            # 🆕 ANTI-BIAS: Echo Chamber Detection results
            "echo_chamber_detected": echo_chamber_result.status.value == "echo_chamber_detected" if echo_chamber_result else False,
            "echo_chamber_warning": echo_chamber_result.warning_message if echo_chamber_result and echo_chamber_result.status.value == "echo_chamber_detected" else None,
            "echo_chamber_consensus_ratio": echo_chamber_result.consensus_ratio if echo_chamber_result else 0.0,
            "current_node": "consensus",
            "completed_nodes": state.get("completed_nodes", []) + ["consensus"],
            "node_timings": {**state.get("node_timings", {}), "consensus": elapsed}
        }
        
    except Exception as e:
        logger.error(f"[Node: consensus] ❌ Failed: {e}")
        return {
            "error": str(e),
            "error_node": "consensus",
            "should_fallback": True
        }


async def execution_node(state: TradingState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node 5: Execution (Uses ExecutorAgent - unified Agent architecture)
    
    Uses ExecutorAgent (inherits from Agent) to make intelligent trading decisions.
    The agent considers:
    - Leader's meeting summary
    - All agent votes
    - Current position context
    - Risk assessment
    
    Input: leader_summary, agent_votes, position_context, consensus_*
    Output: final_signal, execution_result, execution_success
    """
    start_time = time.time()
    
    # 🆕 Phase 1.3: HITL - Check trading mode before execution
    mode_manager = get_mode_manager()
    current_mode = await mode_manager.get_mode()
    mode = current_mode.value
    
    logger.info("node_started", node="execution", mode=mode)
    
    try:
        # Get ExecutorAgent from config (passed from TradingMeeting)
        trade_executor = config.get("configurable", {}).get("trade_executor")
        
        if not trade_executor:
            logger.error("executor_not_found", node="execution")
            execution_failures.labels(reason="executor_not_available").inc()
            return _fallback_execution(state, start_time, "ExecutorAgent not available")
        
        # Prepare inputs for ExecutorAgent
        leader_summary = state.get("leader_summary", "")
        agent_votes = state.get("agent_votes", [])
        position_context = state.get("position_context", {})
        trigger_reason = state.get("trigger_reason", "scheduled")
        
        logger.info("executor_inputs",
            node="execution",
            vote_count=len(agent_votes),
            has_position=position_context.get("has_position", False),
            trigger_reason=trigger_reason
        )
        
        # Call ExecutorAgent.execute() - LLM decides: open_long/open_short/hold/close
        signal = await trade_executor.execute(
            leader_summary=leader_summary,
            agent_votes=agent_votes,
            position_context=position_context,
            trigger_reason=trigger_reason
        )
        
        # Convert TradingSignal to dict for state
        if signal:
            final_signal = {
                "direction": signal.direction,
                "confidence": signal.confidence,
                "leverage": signal.leverage,
                "amount_percent": signal.amount_percent,
                "entry_price": signal.entry_price,
                "tp_price": signal.take_profit_price,
                "sl_price": signal.stop_loss_price,
                "reasoning": signal.reasoning,
                "timestamp": signal.timestamp.isoformat() if signal.timestamp else datetime.now().isoformat()
            }
            execution_result = {
                "action": signal.direction,
                "success": True,
                "message": f"ExecutorAgent decided: {signal.direction.upper()}"
            }
            execution_success = True
            
            # Record metrics
            signals_generated.labels(direction=signal.direction, mode=mode).inc()
            
            # Use trading logger for signal
            trading_logger.signal_generated(
                direction=signal.direction,
                confidence=signal.confidence,
                mode=mode,
                agent_votes=len(agent_votes)
            )
        else:
            # ExecutorAgent returned None - fallback to HOLD
            logger.warning("executor_no_signal", node="execution")
            return _fallback_execution(state, start_time, "ExecutorAgent returned no signal")
        
        elapsed = (time.time() - start_time) * 1000
        logger.info("node_completed",
            node="execution",
            duration_ms=elapsed,
            direction=signal.direction,
            confidence=signal.confidence
        )
        
        return {
            "final_signal": final_signal,
            "execution_result": execution_result,
            "execution_success": execution_success,
            "current_node": "execution",
            "completed_nodes": state.get("completed_nodes", []) + ["execution"],
            "node_timings": {**state.get("node_timings", {}), "execution": elapsed}
        }
        
    except Exception as e:
        logger.error("node_failed", node="execution", error=str(e))
        logger.error("execution_traceback", traceback=traceback.format_exc())
        execution_failures.labels(reason="exception").inc()
        return {
            "error": str(e),
            "error_node": "execution",
            "should_fallback": True,
            "execution_success": False
        }


def _fallback_execution(state: TradingState, start_time: float, reason: str) -> Dict[str, Any]:
    """Fallback to HOLD when ExecutorAgent is not available."""
    market_data = state.get("market_data", {})
    current_price = market_data.get("current_price", 0)
    
    final_signal = {
        "direction": "hold",
        "confidence": 0,
        "leverage": 0,
        "amount_percent": 0,
        "entry_price": current_price,
        "tp_price": current_price,
        "sl_price": current_price,
        "reasoning": f"Fallback HOLD: {reason}",
        "timestamp": datetime.now().isoformat()
    }
    
    elapsed = (time.time() - start_time) * 1000
    logger.warning(f"[Node: execution] ⚠️ Fallback HOLD in {elapsed:.0f}ms - {reason}")
    
    return {
        "final_signal": final_signal,
        "execution_result": {"action": "hold", "success": True, "message": reason},
        "execution_success": True,
        "current_node": "execution",
        "completed_nodes": state.get("completed_nodes", []) + ["execution"],
        "node_timings": {**state.get("node_timings", {}), "execution": elapsed}
    }


async def react_fallback_node(state: TradingState) -> Dict[str, Any]:
    """
    Node: ReAct Fallback
    
    Handles failures using ReAct pattern.
    Input: error, agent_votes
    Output: final_signal (HOLD)
    """
    start_time = time.time()
    iterations = state.get("fallback_iterations", 0) + 1
    max_iterations = 3
    
    logger.info(f"[Node: react_fallback] Iteration {iterations}/{max_iterations}...")
    
    try:
        error = state.get("error", "Unknown error")
        error_node = state.get("error_node", "unknown")
        
        # For safety, ReAct fallback always returns HOLD in production
        # The actual ReAct logic is in ExecutorAgent for more controlled execution
        
        if iterations >= max_iterations:
            logger.warning(f"[Node: react_fallback] Max iterations reached, returning HOLD")
            final_signal = {
                "direction": "hold",
                "confidence": 0,
                "leverage": 0,
                "amount_percent": 0,
                "reasoning": f"ReAct fallback after {error_node} error: {error}",
                "timestamp": datetime.now().isoformat()
            }
            should_fallback = False  # Stop fallback loop
        else:
            # Could implement recovery logic here
            final_signal = {
                "direction": "hold",
                "confidence": 0,
                "leverage": 0,
                "amount_percent": 0,
                "reasoning": f"Fallback iteration {iterations}: {error}",
                "timestamp": datetime.now().isoformat()
            }
            should_fallback = False  # For now, don't retry
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"[Node: react_fallback] ✅ Complete in {elapsed:.0f}ms - Returning HOLD")
        
        return {
            "final_signal": final_signal,
            "execution_success": True,  # HOLD is a valid outcome
            "fallback_iterations": iterations,
            "should_fallback": should_fallback,
            "current_node": "react_fallback",
            "completed_nodes": state.get("completed_nodes", []) + ["react_fallback"],
            "node_timings": {**state.get("node_timings", {}), "react_fallback": elapsed}
        }
        
    except Exception as e:
        logger.error(f"[Node: react_fallback] ❌ Failed: {e}")
        # Ultimate fallback - just return HOLD
        return {
            "final_signal": {
                "direction": "hold",
                "confidence": 0,
                "leverage": 0,
                "amount_percent": 0,
                "reasoning": f"Ultimate fallback: {e}",
                "timestamp": datetime.now().isoformat()
            },
            "execution_success": True,
            "should_fallback": False
        }


async def reflection_node(state: TradingState) -> Dict[str, Any]:
    """
    Node: Reflection
    
    Generates reflection after execution (for learning).
    Only runs after successful trades.
    Input: final_signal, execution_result, agent_votes
    Output: reflection
    """
    start_time = time.time()
    logger.info("[Node: reflection] Generating reflection...")
    
    try:
        signal = state.get("final_signal", {})
        direction = signal.get("direction", "hold")
        
        if direction == "hold":
            # No reflection needed for hold decisions
            reflection = None
        else:
            # Generate reflection summary
            votes = state.get("agent_votes", [])
            reflection = {
                "trade_direction": direction,
                "confidence": signal.get("confidence", 0),
                "vote_count": len(votes),
                "timestamp": datetime.now().isoformat(),
                "note": "Trade initiated - reflection will be completed after position closes"
            }
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"[Node: reflection] ✅ Complete in {elapsed:.0f}ms")
        
        return {
            "reflection": reflection,
            "current_node": "reflection",
            "completed_nodes": state.get("completed_nodes", []) + ["reflection"],
            "node_timings": {**state.get("node_timings", {}), "reflection": elapsed}
        }
        
    except Exception as e:
        logger.warning(f"[Node: reflection] ⚠️ Non-fatal error: {e}")
        return {
            "reflection": None,
            "current_node": "reflection"
        }


# === Helper Functions ===

def _generate_risk_assessment_message(
    votes: List[Dict], 
    avg_confidence: float, 
    risk_level: str, 
    risk_blocked: bool, 
    block_reason: str,
    has_position: bool
) -> str:
    """Generate a descriptive risk assessment message for display."""
    
    # Count vote directions
    direction_counts = {"long": 0, "short": 0, "hold": 0, "close": 0}
    for vote in votes:
        direction = str(vote.get("direction", "hold")).lower()
        if direction in direction_counts:
            direction_counts[direction] += 1
    
    # Build message
    risk_emoji = {
        "low": "🟢",
        "medium": "🟡", 
        "high": "🟠",
        "extreme": "🔴"
    }
    
    message = f"""## Risk Assessment Report

### Overall Risk Level: {risk_emoji.get(risk_level, '⚪')} {risk_level.upper()}

**Expert Consensus:**
- {direction_counts['long']} experts voted LONG
- {direction_counts['short']} experts voted SHORT
- {direction_counts['hold']} experts voted HOLD
- Average Confidence: {avg_confidence:.1f}%

**Position Status:** {'Has open position' if has_position else 'No open position'}
"""
    
    if risk_blocked:
        message += f"""
### ⚠️ EXECUTION BLOCKED
Reason: {block_reason}

Trade execution has been blocked due to elevated risk. Recommend HOLD and wait for better setup.
"""
    else:
        if risk_level == "low":
            message += """
### ✅ APPROVED FOR EXECUTION
Risk within acceptable parameters. Trade execution may proceed with standard position sizing.
"""
        elif risk_level == "medium":
            message += """
### ⚠️ CAUTION ADVISED
Moderate risk detected. Recommend reduced position size and tighter stop-loss.
"""
        elif risk_level == "high":
            message += """
### ⚠️ HIGH RISK WARNING
Elevated risk detected. If proceeding, use minimum position size with strict risk limits.
"""
    
    return message


def _determine_trend(market_data: Dict) -> str:
    """Determine market trend from data."""
    change = market_data.get("price_change_24h", 0)
    if change > 3:
        return "strong_bullish"
    elif change > 1:
        return "bullish"
    elif change < -3:
        return "strong_bearish"
    elif change < -1:
        return "bearish"
    else:
        return "neutral"


def _calculate_avg_confidence(votes: List[Dict]) -> float:
    """Calculate average confidence from votes."""
    if not votes:
        return 0.0
    
    confidences = []
    for vote in votes:
        conf = vote.get("confidence", 0)
        if isinstance(conf, (int, float)):
            confidences.append(conf)
    
    return sum(confidences) / len(confidences) if confidences else 0.0


def _get_consensus_direction(votes: List[Dict]) -> str:
    """Get consensus direction from votes."""
    if not votes:
        return "hold"
    
    directions = {"long": 0, "short": 0, "hold": 0}
    for vote in votes:
        direction = vote.get("direction", "hold").lower()
        if hasattr(direction, 'value'):
            direction = direction.value
        if direction in directions:
            directions[direction] += 1
    
    max_votes = max(directions.values())
    for dir_name, count in directions.items():
        if count == max_votes:
            return dir_name
    
    return "hold"


def _calculate_weighted_consensus(votes: List[Dict], weights: Dict[str, float]) -> tuple:
    """
    Calculate weighted consensus from votes.

    Supports both legacy votes (direction field) and neutral votes (bullish_score/bearish_score).
    """
    if not votes:
        return "hold", 0, 0.0

    # Check if any vote has neutral format (bullish_score/bearish_score)
    has_neutral_votes = any(
        "bullish_score" in vote and "bearish_score" in vote
        for vote in votes
    )

    if has_neutral_votes:
        # Use DirectionNeutralizer for neutral votes
        return _calculate_neutral_consensus(votes, weights)

    # Legacy direction-based voting
    weighted_scores = {"long": 0.0, "short": 0.0, "hold": 0.0}
    total_weight = 0.0
    total_confidence = 0.0

    for vote in votes:
        agent_id = vote.get("agent_id") or vote.get("agent_name", "unknown")
        direction = vote.get("direction", "hold").lower()
        if hasattr(direction, 'value'):
            direction = direction.value
        confidence = vote.get("confidence", 50)
        weight = weights.get(agent_id, 1.0)

        if direction in weighted_scores:
            weighted_scores[direction] += confidence * weight
            total_weight += weight
            total_confidence += confidence

    # Find winning direction
    # 🔧 FIX: Check for tie between long and short to avoid primacy bias
    max_score = max(weighted_scores.values())
    candidates = [d for d, s in weighted_scores.items() if s == max_score and s > 0]

    if len(candidates) == 0:
        winning_direction = "hold"
    elif len(candidates) == 1:
        winning_direction = candidates[0]
    elif "long" in candidates and "short" in candidates:
        # Tie between long and short: return hold (conservative approach)
        winning_direction = "hold"
    else:
        winning_direction = candidates[0]

    # Calculate weighted confidence
    avg_confidence = int(total_confidence / len(votes)) if votes else 0
    weighted_conf = max_score / total_weight if total_weight > 0 else 0.0

    return winning_direction, avg_confidence, weighted_conf


def _calculate_neutral_consensus(votes: List[Dict], weights: Dict[str, float]) -> tuple:
    """
    Calculate consensus from neutral votes using DirectionNeutralizer.

    This eliminates linguistic bias by having agents score bullish/bearish arguments
    separately, then calculating direction mathematically.
    """
    from app.core.trading.anti_bias import DirectionNeutralizer, NeutralVote

    neutral_votes = []

    for vote in votes:
        # Convert dict to NeutralVote if it has the required fields
        if "bullish_score" in vote and "bearish_score" in vote:
            neutral_vote = NeutralVote(
                agent_id=vote.get("agent_id") or vote.get("agent_name", "unknown"),
                agent_name=vote.get("agent_name", "unknown"),
                bullish_score=int(vote.get("bullish_score", 50)),
                bearish_score=int(vote.get("bearish_score", 50)),
                confidence=int(vote.get("confidence", 50)),
                leverage=int(vote.get("leverage", 1)),
                take_profit_percent=float(vote.get("take_profit_percent", 8.0)),
                stop_loss_percent=float(vote.get("stop_loss_percent", 3.0)),
                reasoning=vote.get("reasoning", "")
            )
            neutral_votes.append(neutral_vote)
        else:
            # Legacy vote - convert to neutral format
            direction = vote.get("direction", "hold").lower()
            if hasattr(direction, 'value'):
                direction = direction.value
            confidence = int(vote.get("confidence", 50))

            # Convert direction to scores
            if direction == "long":
                bullish_score = 50 + confidence // 2
                bearish_score = 50 - confidence // 2
            elif direction == "short":
                bullish_score = 50 - confidence // 2
                bearish_score = 50 + confidence // 2
            else:  # hold
                bullish_score = 50
                bearish_score = 50

            neutral_vote = NeutralVote(
                agent_id=vote.get("agent_id") or vote.get("agent_name", "unknown"),
                agent_name=vote.get("agent_name", "unknown"),
                bullish_score=bullish_score,
                bearish_score=bearish_score,
                confidence=confidence,
                leverage=int(vote.get("leverage", 1)),
                take_profit_percent=float(vote.get("take_profit_percent", 8.0)),
                stop_loss_percent=float(vote.get("stop_loss_percent", 3.0)),
                reasoning=vote.get("reasoning", "")
            )
            neutral_votes.append(neutral_vote)

    # Use DirectionNeutralizer to aggregate
    direction, confidence, metadata = DirectionNeutralizer.aggregate_neutral_votes(
        neutral_votes,
        weights
    )

    logger.info(
        f"[NeutralConsensus] Aggregated {len(neutral_votes)} votes: "
        f"bullish={metadata.get('avg_bullish_score', 0):.1f}, "
        f"bearish={metadata.get('avg_bearish_score', 0):.1f} → {direction.upper()}"
    )

    # weighted_conf is the score difference normalized
    weighted_conf = abs(metadata.get('score_difference', 0)) / 100.0

    return direction, confidence, weighted_conf


def _generate_leader_summary(votes: List[Dict], direction: str, confidence: int) -> str:
    """Generate a leader summary from votes."""
    vote_count = len(votes)
    dir_counts = {}
    for vote in votes:
        d = vote.get("direction", "hold")
        if hasattr(d, 'value'):
            d = d.value
        dir_counts[d] = dir_counts.get(d, 0) + 1
    
    return (
        f"Consensus: {direction.upper()} with {confidence}% confidence. "
        f"Votes: {dir_counts}. Total experts: {vote_count}."
    )


def _calculate_leverage(confidence: int) -> int:
    """Calculate leverage based on confidence."""
    if confidence >= LEVERAGE.HIGH_CONFIDENCE:
        return LEVERAGE.HIGH_LEVERAGE
    elif confidence >= LEVERAGE.MEDIUM_CONFIDENCE:
        return 7
    elif confidence >= LEVERAGE.LOW_CONFIDENCE:
        return LEVERAGE.MEDIUM_LEVERAGE
    else:
        return LEVERAGE.LOW_LEVERAGE


def _calculate_amount(confidence: int) -> float:
    """Calculate position amount percent based on confidence."""
    if confidence >= LEVERAGE.HIGH_CONFIDENCE:
        return 0.30
    elif confidence >= LEVERAGE.MEDIUM_CONFIDENCE:
        return 0.25
    elif confidence >= LEVERAGE.LOW_CONFIDENCE:
        return 0.20
    else:
        return 0.15


async def _generate_llm_leader_summary(
    leader_agent: Any, 
    votes: List[Dict], 
    position_context: Dict, 
    market_data: Dict,
    echo_chamber_warning: str = None
) -> str:
    """
    Generate a comprehensive leader summary using the Leader agent LLM.
    Replicates the functionality of the original run_leader_phase.
    
    Args:
        leader_agent: Leader agent instance
        votes: List of agent votes
        position_context: Current position information
        market_data: Current market data
        echo_chamber_warning: Optional warning from EchoChamberDetector
    """
    try:
        # 1. Format Position Summary
        has_pos = position_context.get("has_position", False)
        direction = position_context.get("direction")
        # Handle None direction safely
        direction_str = str(direction).upper() if direction else "NONE"
        entry_price = position_context.get("entry_price", 0)
        current_price = market_data.get("current_price", 0)
        pnl_percent = position_context.get("unrealized_pnl_percent", 0)
        
        pos_summary = f"""## Current Position Status
- Status: {"Has Position" if has_pos else "No Position"}
- Direction: {direction_str}
- Current Price: ${current_price:,.2f}
"""
        if has_pos:
            pos_summary += f"""- Entry Price: ${entry_price:,.2f}
- PnL: {pnl_percent:+.2f}%
"""

        # 2. Generate Decision Guidance
        decision_guidance = "## Decision Guidance\n"
        if has_pos:
            if pnl_percent > 5:
                decision_guidance += f"- Current position has good profit ({pnl_percent:+.2f}%). Consider securing profits or trailing stop.\n"
            elif pnl_percent < -3:
                decision_guidance += f"- Current position is in loss ({pnl_percent:+.2f}%). Evaluate if thesis is still valid or stop loss needed.\n"
            
            if direction == "long":
                decision_guidance += "- HOLD LONG if bullish trend continues. CLOSE if trend reversal confirmed.\n"
            elif direction == "short":
                decision_guidance += "- HOLD SHORT if bearish trend continues. CLOSE if support holds or reversal likely.\n"
        else:
            decision_guidance += "- No position. Look for high-confidence setup to enter.\n"

        # Echo chamber detection - warn when votes are too unanimous
        dir_counts = {}
        for vote in votes:
            d = vote.get("direction", "hold")
            if hasattr(d, 'value'):
                d = d.value
            d = str(d).lower() if d else "hold"
            dir_counts[d] = dir_counts.get(d, 0) + 1
        
        total_votes = len(votes)
        max_count = max(dir_counts.values()) if dir_counts else 0
        
        if total_votes >= 4 and max_count >= total_votes * 0.8:
            dominant_direction = max(dir_counts, key=dir_counts.get)
            decision_guidance += f"\n⚠️ **ECHO CHAMBER WARNING**: {max_count}/{total_votes} experts voted {dominant_direction.upper()}. "
            decision_guidance += "When consensus is this strong, CRITICALLY evaluate:\n"
            decision_guidance += "- What could make this consensus WRONG?\n"
            decision_guidance += "- Are there overlooked bearish/bullish signals?\n"
            decision_guidance += "- Consider reducing confidence or position size due to groupthink risk.\n"

        votes_text = "## Expert Opinion Summary\n"
        for vote in votes:
            agent_name = vote.get("agent_name", "Unknown")
            v_dir_raw = vote.get("direction")
            # Handle None direction safely
            v_dir = str(v_dir_raw).upper() if v_dir_raw else "HOLD"
            v_conf = vote.get("confidence", 0)
            v_reason = vote.get("reasoning", "No reasoning provided")
            votes_text += f"- **{agent_name}** ({v_dir}, {v_conf}%): {v_reason[:200]}...\n"

        # 4. Construct Prompt
        prompt = f"""As the roundtable moderator, please comprehensively summarize the meeting discussions and expert opinions.

{pos_summary}

{decision_guidance}

{votes_text}

## Your Task

As moderator, please:

1. **Summarize Expert Consensus**:
   - How many experts are bullish? Bearish? Neutral?
   - What are the core reasons for each expert's opinion?
   - What are the agreements and disagreements among experts?

2. **Comprehensive Market Judgment**:
   - Based on all discussions, your overall view of the current market
   - Comprehensive evaluation of technical, fundamental, and sentiment aspects
   - Factors to consider given the current position status

3. **Risk and Opportunity Assessment**:
   - What are the main risks currently?
   - Where are the potential trading opportunities?
   - Recommendations for current position (if any)

4. **⚠️ CRITICAL - Final Risk Parameters Decision**:
   Based on expert TP/SL recommendations and current market volatility:
   - **Take Profit %**: Average expert recommendation, adjust for volatility
   - **Stop Loss %**: Average expert recommendation, adjust for protection
   - These are MARGIN-based (not price-based)!
   
   Example: "Given 4% volatility, I recommend TP 10%, SL 4% on margin"

5. **Provide Meeting Conclusions**:
   - Based on all analysis, what strategy should be adopted?
   - Recommended leverage, position size, **TP% and SL%**
   - How confident are you?

## 📋 Output Format

Please express your summary and recommendations freely, **no strict format required**.

You can express naturally, for example:

"Based on all expert opinions, I believe...
- Some experts (e.g., TechnicalAnalyst, SentimentAnalyst) are [bullish/bearish] because...
- However, other experts advise [different view] due to...
- Considering the current {('no position' if not has_pos else f'{direction_str} position')} status...
I recommend... strategy because...
Suggested leverage is..., position size is...
**For risk management, I recommend TP at X% and SL at Y% (margin-based)**
My confidence is approximately...%"

⚠️ **Important Reminders**:
- ✅ Express your summary and recommendations in natural language
- ✅ Include expert opinions, your judgment, recommended strategy
- ✅ **ALWAYS include your recommended TP% and SL% values**
- ✅ No need for markers like "【Final Decision】"
- ✅ Your summary will be passed to the Trade Executor

Please begin your summary!
"""

        # 5. Call LLM
        # Use _call_llm directly
        messages = [
            {"role": "system", "content": leader_agent.system_prompt or leader_agent.role_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = await leader_agent._call_llm(messages)
        
        # 6. Extract content
        content = ""
        if isinstance(response, dict):
            if "choices" in response:
                try:
                    content = response["choices"][0]["message"]["content"]
                except (KeyError, IndexError):
                    pass
            if not content:
                content = response.get("content", response.get("response", ""))
        else:
            content = str(response)
            
        return content if content else "Failed to generate leader summary."
        
    except Exception as e:
        logger.error(f"[_generate_llm_leader_summary] Error: {e}")
        logger.error(traceback.format_exc())
        return f"Error generating summary: {str(e)}"


async def _generate_llm_risk_assessment(
    risk_agent: Any, 
    votes: List[Dict], 
    position_context: Dict,
    market_data: Dict
) -> Dict[str, Any]:
    """
    Generate a comprehensive risk assessment using the RiskAssessor agent LLM.
    Replicates the functionality of the original _run_risk_assessment_phase.
    
    Returns:
        Dict with risk_message (str), risk_level (str), risk_blocked (bool), block_reason (str)
    """
    try:
        # 1. Format votes summary
        votes_summary = "## Expert Voting Results\n"
        direction_counts = {"long": 0, "short": 0, "hold": 0, "close": 0}
        total_confidence = 0
        
        for vote in votes:
            agent_name = vote.get("agent_name", "Unknown")
            v_dir = str(vote.get("direction", "hold")).lower()
            v_conf = vote.get("confidence", 50)
            v_lev = vote.get("leverage", 1)
            v_tp = vote.get("take_profit_percent", 5.0)
            v_sl = vote.get("stop_loss_percent", 2.0)
            v_reason = vote.get("reasoning", "No reasoning")[:200]
            
            if v_dir in direction_counts:
                direction_counts[v_dir] += 1
            total_confidence += v_conf
            
            votes_summary += f"- **{agent_name}**: {v_dir.upper()} ({v_conf}%), Leverage: {v_lev}x, TP: {v_tp}%, SL: {v_sl}%\n"
            votes_summary += f"  Reasoning: {v_reason}...\n"
        
        avg_confidence = total_confidence / len(votes) if votes else 0
        
        # 2. Format position context
        has_pos = position_context.get("has_position", False)
        direction = position_context.get("direction")
        pnl_percent = position_context.get("unrealized_pnl_percent", 0)
        entry_price = position_context.get("entry_price", 0)
        current_price = market_data.get("current_price", 0)
        
        pos_summary = f"""## Current Position Status
- Status: {"Has Position" if has_pos else "No Position"}
"""
        if has_pos:
            pos_summary += f"""- Direction: {str(direction).upper() if direction else "UNKNOWN"}
- Entry Price: ${entry_price:,.2f}
- Current Price: ${current_price:,.2f}
- Unrealized PnL: {pnl_percent:+.2f}%
"""
        
        # 3. Generate risk context
        risk_context = """
## 🛡️ Risk Assessment Focus

**Key Evaluation Points**:
1. Is the entry direction well-justified by expert consensus?
2. Does the leverage match the confidence level?
3. Are TP/SL settings reasonable for current volatility?
4. Does the position size comply with risk management principles?
5. Is current market volatility suitable for trading?
6. Are there any conflicting signals among experts?
"""
        
        # 4. Construct prompt - Request structured JSON decision at the end
        prompt = f"""As the Risk Manager, please evaluate the trading risks based on expert opinions.

{votes_summary}

{pos_summary}

{risk_context}

## Your Task

Please evaluate the risk of this trade and decide whether to approve.

**Evaluation Criteria**:
- Average Expert Confidence: {avg_confidence:.1f}%
- Expert Vote Distribution: LONG: {direction_counts['long']}, SHORT: {direction_counts['short']}, HOLD: {direction_counts['hold']}, CLOSE: {direction_counts['close']}

**Your Assessment Should Include**:

1. **Overall Risk Level**: low / medium / high / extreme
2. **Approval Decision**: approved / blocked
3. **Key Risk Factors**: List main risks identified
4. **Position Recommendations**: If approved, recommended position size and leverage adjustments
5. **TP/SL Recommendations**: Your recommended risk parameters

⚠️ **IMPORTANT**:
- You only need to provide **text recommendations** for risk assessment
- **Do NOT** call any decision tools (open_long/open_short/hold/close_position)
- Only the TradeExecutor can execute trades
- Your responsibility is to assess risk, NOT to execute trades

Please provide your comprehensive risk assessment!

## 📋 REQUIRED: At the very END of your response, you MUST include a JSON decision block like this:

```json
{{
    "risk_level": "low|medium|high|extreme",
    "approved": true|false,
    "reason": "Brief reason for the decision"
}}
```

This JSON block is required for the system to process your decision correctly.
"""

        # 5. Call LLM
        messages = [
            {"role": "system", "content": risk_agent.system_prompt or risk_agent.role_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = await risk_agent._call_llm(messages)
        
        # 6. Extract content
        risk_message = ""
        if isinstance(response, dict):
            if "choices" in response:
                try:
                    risk_message = response["choices"][0]["message"]["content"]
                except (KeyError, IndexError):
                    pass
            if not risk_message:
                risk_message = response.get("content", response.get("response", ""))
        else:
            risk_message = str(response)
        
        # 7. Parse JSON decision block from LLM response (LLM-based understanding)
        import json
        import re
        
        risk_level = "medium"  # Default
        risk_blocked = False
        block_reason = None
        
        # Try to extract JSON block from response
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', risk_message, re.DOTALL)
        if not json_match:
            # Try without code block markers
            json_match = re.search(r'\{\s*"risk_level".*?"approved".*?\}', risk_message, re.DOTALL)
        
        if json_match:
            try:
                json_str = json_match.group(1) if '```' in json_match.group(0) else json_match.group(0)
                decision = json.loads(json_str)
                
                # Extract decision from JSON
                risk_level = decision.get("risk_level", "medium").lower()
                is_approved = decision.get("approved", True)
                decision_reason = decision.get("reason", "")
                
                if not is_approved:
                    risk_blocked = True
                    block_reason = decision_reason or "RiskAssessor decided to block this trade"
                    
                logger.info(f"[_generate_llm_risk_assessment] Parsed JSON decision: approved={is_approved}, risk_level={risk_level}")
                
            except json.JSONDecodeError as e:
                logger.warning(f"[_generate_llm_risk_assessment] Failed to parse JSON decision: {e}")
                # Fallback: don't block if we can't parse (safer default)
                risk_blocked = False
        else:
            logger.warning("[_generate_llm_risk_assessment] No JSON decision block found in response")
            # Fallback: don't block if no JSON found (safer default, let ExecutorAgent decide)
            risk_blocked = False
        
        # Additional safety checks that always apply
        if risk_level == "extreme" and not risk_blocked:
            risk_blocked = True
            block_reason = "Extreme risk level detected"
        elif avg_confidence < 40 and not risk_blocked:
            risk_blocked = True
            block_reason = f"Average confidence too low ({avg_confidence:.1f}%)"
        
        return {
            "risk_message": risk_message if risk_message else "Failed to generate risk assessment.",
            "risk_level": risk_level,
            "risk_blocked": risk_blocked,
            "block_reason": block_reason,
            "avg_confidence": avg_confidence
        }
        
    except Exception as e:
        logger.error(f"[_generate_llm_risk_assessment] Error: {e}")
        logger.error(traceback.format_exc())
        return {
            "risk_message": f"Error generating risk assessment: {str(e)}",
            "risk_level": "high",
            "risk_blocked": False,
            "block_reason": None,
            "avg_confidence": 0
        }
