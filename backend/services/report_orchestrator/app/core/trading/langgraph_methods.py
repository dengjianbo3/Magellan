# LangGraph Integration Methods for TradingMeeting
# To be added to trading_meeting.py

async def run_with_graph(
    self,
    trigger_reason: str = "scheduled",
    context: Optional[str] = None
) -> Optional[TradingSignal]:
    """
    Run trading workflow using LangGraph.
    Alternative execution path when use_langgraph=True.
    
    Args:
        trigger_reason: Why the workflow was triggered
        context: Optional additional context
        
    Returns:
        TradingSignal or None
    """
    logger.info(f"[TradingMeeting] 🔄 Running via LangGraph - Trigger: {trigger_reason}")
    
    try:
        # Load agent weights  
        agent_weights = await self._calculate_agent_weights()
        
        # Get market data
        market_data = {
            "current_price": await get_current_btc_price(),
            "trigger_reason": trigger_reason
        }
        
        # Get position context
        position_context = {}
        if self.toolkit and hasattr(self.toolkit, 'paper_trader'):
            pos = await self.toolkit.paper_trader.get_position(self.config.symbol)
            position_context = {
                "has_position": pos is not None,
                "direction": pos.get("side") if pos else None
            }
        
        # Collect agent votes using existing logic
        votes = await self._collect_agent_votes_for_graph()
        
        # Run the graph
        result_state = await self._trading_graph.run(
            trigger_reason=trigger_reason,
            symbol=self.config.symbol,
            market_data=market_data,
            position_context=position_context,
            agent_votes=[v if isinstance(v, dict) else v.to_dict() for v in votes],
            agent_weights=agent_weights
        )
        
        # Extract final signal from graph state
        signal_dict = result_state.get("final_signal")
        if signal_dict:
            signal = TradingSignal(
                direction=signal_dict["direction"],
                symbol=self.config.symbol,
                leverage=signal_dict.get("leverage", 1),
                amount_percent=signal_dict.get("amount_percent", 0.2),
                entry_price=signal_dict.get("entry_price", market_data["current_price"]),
                take_profit_price=signal_dict.get("tp_price", market_data["current_price"]),
                stop_loss_price=signal_dict.get("sl_price", market_data["current_price"]),
                confidence=signal_dict.get("confidence", 50),
                reasoning=signal_dict.get("reasoning", ""),
                agents_consensus={"graph_state": "langgraph_execution"},
                timestamp=datetime.now()
            )
            
            self._final_signal = signal
            logger.info(f"[TradingMeeting] ✅ LangGraph execution complete: {signal.direction.upper()}")
            return signal
        
        logger.warning("[TradingMeeting] ⚠️ No signal from LangGraph, returning None")
        return None
        
    except Exception as e:
        logger.error(f"[TradingMeeting] ❌ LangGraph execution failed: {e}", exc_info=True)
        # Fallback to traditional flow
        logger.info("[TradingMeeting] Falling back to traditional execution...")
        return None


async def _collect_agent_votes_for_graph(self) -> List[Dict]:
    """
    Collect agent votes in format suitable for graph.
    Simplified version for LangGraph integration.
    """
    # This is a placeholder - the actual implementation would
    # reuse existing agent voting logic from run()
    # For now, return empty to use graph's signal_generation_node
    return []


def _format_memory_context(self, memory) -> str:
    """
    Format agent memory into rich context string.
    
    Phase 5: Enhanced Memory - improves prompt quality
    """
    if not memory or not hasattr(memory, 'win_rate'):
        return ""
    
    # Calculate focus area based on performance
    focus = self._calculate_focus_area(memory)
    
    # Format recent lessons
    lessons_text = ""
    if hasattr(memory, 'lessons_learned') and memory.lessons_learned:
        lessons = memory.lessons_learned[-5:]  # Last 5 lessons
        lessons_text = "\n".join([f"  • {lesson}" for lesson in lessons])
    else:
        lessons_text = "  No lessons yet - this is your first analysis"
    
    # Rich formatting with visual separators
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 YOUR TRACK RECORD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Win Rate: {memory.win_rate:.1f}% 
Trades: {memory.winning_trades}W / {memory.losing_trades}L
Current Streak: {"🔥 " if getattr(memory, 'consecutive_wins', 0) > 0 else "❄️ "}{max(getattr(memory, 'consecutive_wins', 0), getattr(memory, 'consecutive_losses', 0))} trades

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 CURRENT FOCUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{focus}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 KEY LESSONS (Recent 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{lessons_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def _calculate_focus_area(self, memory) -> str:
    """
    Dynamically calculate what agent should focus on based on performance.
    
    Phase 5: Enhanced Memory - provides actionable guidance
    """
    consecutive_losses = getattr(memory, 'consecutive_losses', 0)
    consecutive_wins = getattr(memory, 'consecutive_wins', 0)
    win_rate = getattr(memory, 'win_rate', 50)
    
    # Determine focus based on performance patterns
    if consecutive_losses >= 3:
        return "⚠️ RISK CONTROL - Reduce position sizes, tighten stops, avoid revenge trading"
    elif win_rate < 40:
        return "🎯 ACCURACY - Focus on high-confidence setups only (>70%)"
    elif consecutive_wins >= 3:
        return "💰 CAPITALIZE - Trending well, maintain discipline, don't overtrade"
    elif win_rate >= 60:
        return "📈 PERFORMING - Good consistency, continue current approach"
    else:
        return "📊 BALANCED - Stick to your strategy, wait for quality setups"
