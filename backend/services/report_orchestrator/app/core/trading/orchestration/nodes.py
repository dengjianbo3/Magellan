"""
Trading Workflow Nodes

Defines all nodes for the LangGraph trading workflow.
Each node is an async function that takes state and returns updated state.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, List
import json

from .state import TradingState, NodeResult, TradeDirection

logger = logging.getLogger(__name__)


async def market_analysis_node(state: TradingState) -> Dict[str, Any]:
    """
    Node 1: Market Analysis
    
    Gathers and analyzes market data.
    Input: market_data
    Output: analysis
    """
    start_time = time.time()
    logger.info("[Node: market_analysis] Starting market analysis...")
    
    try:
        market_data = state.get("market_data", {})
        
        # Extract key metrics
        analysis = {
            "current_price": market_data.get("current_price", 0),
            "price_change_24h": market_data.get("price_change_24h", 0),
            "volume_24h": market_data.get("volume_24h", 0),
            "fear_greed_index": market_data.get("fear_greed_index", 50),
            "trend": _determine_trend(market_data),
            "volatility": market_data.get("volatility", "medium"),
            "timestamp": datetime.now().isoformat()
        }
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"[Node: market_analysis] ✅ Complete in {elapsed:.0f}ms - Trend: {analysis['trend']}")
        
        return {
            "analysis": analysis,
            "current_node": "market_analysis",
            "completed_nodes": state.get("completed_nodes", []) + ["market_analysis"],
            "node_timings": {**state.get("node_timings", {}), "market_analysis": elapsed}
        }
        
    except Exception as e:
        logger.error(f"[Node: market_analysis] ❌ Failed: {e}")
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
    logger.info("[Node: signal_generation] Starting agent voting...")
    
    try:
        # This will be replaced with actual agent calls
        # For now, use placeholder votes from context
        existing_votes = state.get("agent_votes", [])
        
        if not existing_votes:
            # Placeholder: In real implementation, call agents here
            logger.warning("[Node: signal_generation] No agent votes available")
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"[Node: signal_generation] ✅ Complete in {elapsed:.0f}ms - {len(existing_votes)} votes")
        
        return {
            "current_node": "signal_generation",
            "completed_nodes": state.get("completed_nodes", []) + ["signal_generation"],
            "node_timings": {**state.get("node_timings", {}), "signal_generation": elapsed}
        }
        
    except Exception as e:
        logger.error(f"[Node: signal_generation] ❌ Failed: {e}")
        return {
            "error": str(e),
            "error_node": "signal_generation",
            "should_fallback": True
        }


async def risk_assessment_node(state: TradingState) -> Dict[str, Any]:
    """
    Node 3: Risk Assessment
    
    Evaluates risk based on votes and current position.
    Input: agent_votes, position_context
    Output: risk_assessment, risk_level, risk_blocked
    """
    start_time = time.time()
    logger.info("[Node: risk_assessment] Evaluating risk...")
    
    try:
        votes = state.get("agent_votes", [])
        position = state.get("position_context", {})
        
        # Calculate risk metrics
        avg_confidence = _calculate_avg_confidence(votes)
        has_position = state.get("has_position", False)
        
        # Determine risk level
        if avg_confidence >= 75:
            risk_level = "low"
        elif avg_confidence >= 55:
            risk_level = "medium"
        elif avg_confidence >= 40:
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
        
        risk_assessment = {
            "avg_confidence": avg_confidence,
            "vote_count": len(votes),
            "risk_level": risk_level,
            "blocked": risk_blocked,
            "block_reason": block_reason,
            "has_position": has_position,
            "timestamp": datetime.now().isoformat()
        }
        
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


async def consensus_node(state: TradingState) -> Dict[str, Any]:
    """
    Node 4: Consensus Building
    
    Synthesizes votes into a consensus decision.
    Input: agent_votes, risk_assessment, agent_weights
    Output: leader_summary, consensus_direction, consensus_confidence
    """
    start_time = time.time()
    logger.info("[Node: consensus] Building consensus...")
    
    try:
        votes = state.get("agent_votes", [])
        weights = state.get("agent_weights", {})
        risk_blocked = state.get("risk_blocked", False)
        
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
        else:
        # Calculate weighted consensus
            consensus_direction, consensus_confidence, weighted_conf = _calculate_weighted_consensus(votes, weights)
            
            # 🔧 RESTORE: Use Leader Agent to generate comprehensive summary if available
            leader_agent = state.get("leader_agent")
            if leader_agent:
                try:
                    logger.info("[Node: consensus] 🧠 Generating comprehensive Leader summary via LLM...")
                    leader_summary = await _generate_llm_leader_summary(
                        leader_agent, 
                        votes, 
                        state.get("position_context", {}),
                        state.get("market_data", {})
                    )
                except Exception as e:
                    logger.error(f"[Node: consensus] ❌ Failed to generate LLM summary: {e}")
                    leader_summary = _generate_leader_summary(votes, consensus_direction, consensus_confidence)
            else:
                leader_summary = _generate_leader_summary(votes, consensus_direction, consensus_confidence)
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"[Node: consensus] ✅ Complete in {elapsed:.0f}ms - {consensus_direction.upper()} ({consensus_confidence}%)")
        
        return {
            "leader_summary": leader_summary,
            "consensus_direction": consensus_direction,
            "consensus_confidence": consensus_confidence,
            "weighted_confidence": weighted_conf if 'weighted_conf' in locals() else 0.0,
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


async def execution_node(state: TradingState) -> Dict[str, Any]:
    """
    Node 5: Execution
    
    Executes the trading decision.
    Input: consensus_direction, consensus_confidence, position_context
    Output: final_signal, execution_result, execution_success
    """
    start_time = time.time()
    logger.info("[Node: execution] Executing decision...")
    
    try:
        direction = state.get("consensus_direction", "hold")
        confidence = state.get("consensus_confidence", 0)
        risk_blocked = state.get("risk_blocked", False)
        market_data = state.get("market_data", {})
        current_price = market_data.get("current_price", 0)
        
        if risk_blocked or direction == "hold" or confidence < 60:
            # Don't execute - stay in hold
            final_signal = {
                "direction": "hold",
                "confidence": confidence,
                "leverage": 0,
                "amount_percent": 0,
                "entry_price": current_price,
                "tp_price": current_price,
                "sl_price": current_price,
                "reasoning": state.get("leader_summary", "No action required"),
                "timestamp": datetime.now().isoformat()
            }
            execution_result = {"action": "hold", "success": True}
            execution_success = True
        else:
            # Calculate execution parameters
            leverage = _calculate_leverage(confidence)
            amount_percent = _calculate_amount(confidence)
            tp_percent = 8.0  # Default TP
            sl_percent = 3.0  # Default SL
            
            # 🔧 FIX: Calculate actual TP/SL prices
            if direction == "long":
                tp_price = current_price * (1 + tp_percent / 100)
                sl_price = current_price * (1 - sl_percent / 100)
            else:  # short
                tp_price = current_price * (1 - tp_percent / 100)
                sl_price = current_price * (1 + sl_percent / 100)
            
            final_signal = {
                "direction": direction,
                "confidence": confidence,
                "leverage": leverage,
                "amount_percent": amount_percent,
                "entry_price": current_price,  # 🔧 FIX: Include entry price
                "tp_price": tp_price,  # 🔧 FIX: Calculated TP price
                "sl_price": sl_price,  # 🔧 FIX: Calculated SL price
                "tp_percent": tp_percent,
                "sl_percent": sl_percent,
                "reasoning": state.get("leader_summary", ""),  # 🔧 FIX: Include leader summary
                "timestamp": datetime.now().isoformat()
            }
            
            # Note: Actual trade execution happens through TradeExecutor
            # This node prepares the signal; integration layer handles execution
            execution_result = {
                "action": direction,
                "leverage": leverage,
                "amount_percent": amount_percent,
                "success": True,
                "message": "Signal prepared for execution"
            }
            execution_success = True
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"[Node: execution] ✅ Complete in {elapsed:.0f}ms - {direction.upper()}")
        
        return {
            "final_signal": final_signal,
            "execution_result": execution_result,
            "execution_success": execution_success,
            "current_node": "execution",
            "completed_nodes": state.get("completed_nodes", []) + ["execution"],
            "node_timings": {**state.get("node_timings", {}), "execution": elapsed}
        }
        
    except Exception as e:
        logger.error(f"[Node: execution] ❌ Failed: {e}")
        return {
            "error": str(e),
            "error_node": "execution",
            "should_fallback": True,
            "execution_success": False
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
        # The actual ReAct logic is in TradeExecutor for more controlled execution
        
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
    """Calculate weighted consensus from votes."""
    if not votes:
        return "hold", 0, 0.0
    
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
    max_score = max(weighted_scores.values())
    winning_direction = "hold"
    for dir_name, score in weighted_scores.items():
        if score == max_score and score > 0:
            winning_direction = dir_name
            break
    
    # Calculate weighted confidence
    avg_confidence = int(total_confidence / len(votes)) if votes else 0
    weighted_conf = max_score / total_weight if total_weight > 0 else 0.0
    
    return winning_direction, avg_confidence, weighted_conf


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
    if confidence >= 85:
        return 10
    elif confidence >= 75:
        return 7
    elif confidence >= 65:
        return 5
    else:
        return 3


def _calculate_amount(confidence: int) -> float:
    """Calculate position amount percent based on confidence."""
    if confidence >= 85:
        return 0.30
    elif confidence >= 75:
        return 0.25
    elif confidence >= 65:
        return 0.20
    else:
        return 0.15


async def _generate_llm_leader_summary(leader_agent: Any, votes: List[Dict], position_context: Dict, market_data: Dict) -> str:
    """
    Generate a comprehensive leader summary using the Leader agent LLM.
    Replicates the functionality of the original run_leader_phase.
    """
    try:
        # 1. Format Position Summary
        has_pos = position_context.get("has_position", False)
        direction = position_context.get("direction", "none")
        entry_price = position_context.get("entry_price", 0)
        current_price = market_data.get("current_price", 0)
        pnl_percent = position_context.get("unrealized_pnl_percent", 0)
        
        pos_summary = f\"\"\"## Current Position Status
- Status: {"Has Position" if has_pos else "No Position"}
- Direction: {direction.upper()}
- Current Price: ${current_price:,.2f}
\"\"\"
        if has_pos:
            pos_summary += f\"\"\"- Entry Price: ${entry_price:,.2f}
- PnL: {pnl_percent:+.2f}%
\"\"\"

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

        # 3. Format Expert Votes
        votes_text = "## Expert Opinion Summary\n"
        for vote in votes:
            agent_name = vote.get("agent_name", "Unknown")
            v_dir = vote.get("direction", "hold").upper()
            v_conf = vote.get("confidence", 0)
            v_reason = vote.get("reasoning", "No reasoning provided")
            votes_text += f"- **{agent_name}** ({v_dir}, {v_conf}%): {v_reason[:200]}...\n"

        # 4. Construct Prompt
        prompt = f\"\"\"As the roundtable moderator, please comprehensively summarize the meeting discussions and expert opinions.

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
- TechnicalAnalyst and SentimentAnalyst are bullish because...
- However, MacroEconomist advises caution due to...
- Considering the current {('no position' if not has_pos else f'{direction} position')} status...
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
\"\"\"

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
        return f"Error generating summary: {str(e)}"

