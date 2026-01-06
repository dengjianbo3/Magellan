"""
Trading API Routes

REST API endpoints for the auto trading system.
Supports both local PaperTrader and OKX Demo trading.
"""

import os
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.core.trading.paper_trader import PaperTrader, get_paper_trader
from app.core.trading.okx_trader import OKXTrader, get_okx_trader
from app.core.trading.trading_tools import TradingToolkit
from app.core.trading.trading_agents import create_trading_agents, get_trading_agent_config
from app.core.trading.trading_meeting import TradingMeeting, TradingMeetingConfig
from app.core.trading.agent_memory import get_memory_store
from app.core.trading.decision_store import get_decision_store  # Redis persistence for signals
from app.core.trading.scheduler import TradingScheduler, CooldownManager
from app.core.trading.trigger import TriggerScheduler, TriggerAgent
from app.models.trading_models import TradingConfig, TradingSignal

logger = logging.getLogger(__name__)

# Check if OKX credentials are configured
def _use_okx_trading() -> bool:
    """Check if OKX trading should be used based on env config"""
    okx_key = os.getenv("OKX_API_KEY", "")
    okx_secret = os.getenv("OKX_SECRET_KEY", "")
    okx_pass = os.getenv("OKX_PASSPHRASE", "")
    # Default to false - use local paper trader for easier testing
    use_okx = os.getenv("USE_OKX_TRADING", "false").lower() == "true"

    # Use OKX if credentials are set and USE_OKX_TRADING is explicitly true
    return bool(okx_key and okx_secret and okx_pass and use_okx)

router = APIRouter(prefix="/api/trading", tags=["trading"])

# Global state
_trading_system: Optional['TradingSystem'] = None


class TradingSystem:
    """
    Central trading system manager.

    Coordinates scheduler, position monitor, and trading meetings.
    Supports both local PaperTrader and OKX Demo trading.
    """

    def __init__(self, llm_service=None):
        self.llm_service = llm_service
        self.config = TradingConfig()

        # Trader can be either PaperTrader or OKXTrader
        self.trader: Optional[Union[PaperTrader, OKXTrader]] = None
        self.trader_type: str = "paper"  # "paper" or "okx"

        # Keep paper_trader as alias for compatibility
        self.paper_trader: Optional[Union[PaperTrader, OKXTrader]] = None

        self.toolkit: Optional[TradingToolkit] = None
        self.scheduler: Optional[TradingScheduler] = None
        self.trigger_scheduler: Optional[TriggerScheduler] = None  # Event-driven trigger
        self.cooldown_manager = CooldownManager()

        self._ws_clients: Dict[str, WebSocket] = {}
        self._current_meeting: Optional[TradingMeeting] = None
        self._trade_history: List[Dict] = []
        self._discussion_messages: List[Dict] = []  # Store discussion messages for persistence
        self._monitor_task: Optional[asyncio.Task] = None
        self._initialized = False
        self._started = False  # 🔧 FIX: Prevent duplicate start() calls

    async def initialize(self):
        """Initialize the trading system"""
        if self._initialized:
            return

        # Determine which trader to use
        use_okx = _use_okx_trading()

        if use_okx:
            logger.info("Initializing trading system with OKX Demo Trading...")
            self.trader_type = "okx"
            self.trader = await get_okx_trader(
                initial_balance=self.config.initial_capital
            )
        else:
            logger.info("Initializing trading system with Paper Trader...")
            self.trader_type = "paper"
            self.trader = await get_paper_trader(
                initial_balance=self.config.initial_capital
            )

        # Set alias for compatibility
        self.paper_trader = self.trader

        # Set callbacks
        self.trader.on_position_closed = self._on_position_closed
        self.trader.on_tp_hit = self._on_tp_hit
        self.trader.on_sl_hit = self._on_sl_hit

        # Initialize toolkit with trader
        self.toolkit = TradingToolkit(paper_trader=self.trader)

        # Initialize scheduler
        self.scheduler = TradingScheduler(
            interval_hours=self.config.analysis_interval_hours,
            on_analysis_cycle=self._on_analysis_cycle,
            on_state_change=self._on_scheduler_state_change
        )

        # Initialize event-driven trigger scheduler
        # Runs every 15 minutes, uses LLM to decide if immediate analysis needed
        self.trigger_scheduler = TriggerScheduler(
            trigger_agent=TriggerAgent(paper_trader=self.paper_trader),
            on_trigger=self._on_trigger_event,
            interval_minutes=15,
            cooldown_minutes=30
        )
        logger.info("✅ TriggerScheduler initialized (15min interval, LLM-driven, position-aware)")

        self._initialized = True
        logger.info(f"Trading system initialized with {self.trader_type} trader")

    async def start(self):
        """Start the trading system"""
        # 🔧 FIX: Prevent duplicate start() calls
        if self._started:
            logger.warning("⚠️  Trading system already started, ignoring duplicate start call")
            return
        
        # 🔧 FIX: Check if monitor_task already exists
        if self._monitor_task and not self._monitor_task.done():
            logger.warning("⚠️  Monitor task already running, cancelling old task")
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        if not self._initialized:
            await self.initialize()

        if not self.config.enabled:
            logger.warning("Trading system is disabled")
            return

        logger.info("🚀 Starting trading system...")
        self._started = True  # 🔧 FIX: Mark as started
        
        await self.scheduler.start()

        # Start event-driven trigger scheduler
        if self.trigger_scheduler:
            await self.trigger_scheduler.start()
            logger.info("🎯 Trigger scheduler started (event-driven analysis)")

        # Start position monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("📊 Monitor task created")

        await self._broadcast({
            "type": "system_started",
            "timestamp": datetime.now().isoformat()
        })

    async def stop(self):
        """Stop the trading system"""
        logger.info("🛑 Stopping trading system...")
        
        self._started = False  # 🔧 FIX: Reset started flag

        if self.scheduler:
            await self.scheduler.stop()

        # Stop trigger scheduler
        if self.trigger_scheduler:
            await self.trigger_scheduler.stop()
            logger.info("🛑 Trigger scheduler stopped")

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        await self._broadcast({
            "type": "system_stopped",
            "timestamp": datetime.now().isoformat()
        })

    async def _monitor_loop(self):
        """Monitor positions for TP/SL triggers"""
        while True:
            try:
                if self.paper_trader:
                    # Check TP/SL
                    trigger = await self.paper_trader.check_tp_sl()
                    if trigger:
                        # TP or SL hit, trigger new analysis
                        # Only trigger if scheduler is not currently analyzing
                        from app.core.trading.scheduler import SchedulerState
                        if self.scheduler and self.scheduler._state != SchedulerState.ANALYZING:
                            logger.info(f"TP/SL trigger detected: {trigger}, triggering new analysis")
                            await self.scheduler.trigger_now(reason=f"{trigger}_triggered")
                        else:
                            logger.info(f"TP/SL trigger detected: {trigger}, but skipping (already analyzing)")

                    # Update equity
                    account = await self.paper_trader.get_account()
                    await self._broadcast({
                        "type": "account_update",
                        "account": account
                    })

                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(30)

    async def _on_trigger_event(self, context):
        """
        Handle LLM-driven trigger event.
        
        Called by TriggerScheduler when significant market events are detected.
        Triggers an immediate analysis cycle via the main scheduler.
        """
        logger.info(f"🎯 Trigger event received! Urgency: {context.urgency}, Confidence: {context.confidence}%")
        logger.info(f"   Reason: {context.reasoning}")
        logger.info(f"   Key events: {context.key_events}")
        
        # Broadcast trigger event to WebSocket clients
        await self._broadcast({
            "type": "trigger_event",
            "urgency": context.urgency,
            "confidence": context.confidence,
            "reasoning": context.reasoning,
            "key_events": context.key_events,
            "current_price": context.current_price,
            "news_count": context.news_count,
            "timestamp": context.trigger_time
        })
        
        # Trigger immediate analysis via main scheduler
        if self.scheduler:
            reason = f"trigger_event: {context.urgency} urgency, {context.confidence}% confidence"
            triggered = await self.scheduler.trigger_now(reason=reason)
            if triggered:
                logger.info("✅ Immediate analysis triggered successfully")
            else:
                logger.warning("⚠️ Could not trigger immediate analysis (scheduler busy or cooldown)")


    async def _on_analysis_cycle(self, cycle_number: int, reason: str, timestamp: datetime):
        """Handle analysis cycle"""
        logger.info(f"Starting analysis cycle #{cycle_number}, reason: {reason}")

        # ⚠️ CRITICAL: Check Tavily/MCP health before any analysis
        tavily_healthy = await self._check_tavily_health()
        if not tavily_healthy:
            logger.error("🚨 Tavily/MCP search service is DOWN! Halting analysis to prevent uninformed decisions.")
            await self._broadcast({
                "type": "analysis_halted",
                "reason": "tavily_unavailable",
                "message": "Search service unavailable - cannot make informed trading decisions",
                "timestamp": timestamp.isoformat()
            })
            return

        # Check cooldown
        if not self.cooldown_manager.check_cooldown():
            logger.warning("In cooldown period, skipping analysis")
            await self._broadcast({
                "type": "analysis_skipped",
                "reason": "cooldown",
                "cooldown_status": self.cooldown_manager.get_cooldown_status()
            })
            return

        await self._broadcast({
            "type": "analysis_started",
            "cycle_number": cycle_number,
            "reason": reason,
            "timestamp": timestamp.isoformat()
        })

        try:
            # Run trading meeting
            logger.info(f"[SIGNAL_DEBUG] Starting trading meeting for cycle #{cycle_number}")
            signal = await self._run_trading_meeting(reason)
            logger.info(f"[SIGNAL_DEBUG] Trading meeting returned signal: {signal}")

            if signal:
                logger.info(f"[SIGNAL_DEBUG] Signal is not None, direction={signal.direction}")
                await self._broadcast({
                    "type": "signal_generated",
                    "signal": signal.model_dump()
                })

                # Record all decisions to history (including hold)
                if signal.direction == "hold":
                    # Record hold decision
                    logger.info(f"[SIGNAL_DEBUG] Recording HOLD signal to history")
                    self._trade_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "signal": signal.model_dump(),
                        "status": "hold",
                        "trade_result": {"action": "hold", "message": "观望，不执行交易"}
                    })
                    logger.info(f"[SIGNAL_DEBUG] History now has {len(self._trade_history)} entries")
                else:
                    # 🔧 FIX: LangGraph execution_node only PREPARES the signal, 
                    # it does NOT actually execute trades via the trader.
                    # We MUST call _execute_signal to actually open the position.
                    logger.info(f"[SIGNAL_DEBUG] Executing {signal.direction} signal via _execute_signal")
                    
                    # Check if position already exists to prevent duplicates
                    current_position = await self.paper_trader.get_position() if self.paper_trader else None
                    has_existing_position = current_position and current_position.get("has_position")
                    existing_direction = current_position.get("direction") if has_existing_position else None
                    
                    # 🔧 FIX: Do not skip execution if position exists.
                    # Allow "adding to position" if the strategy dictates.
                    # The underlying trader (Paper/OKX) will handle checks/merging.
                    
                    # Execute the trade
                    trade_result = await self._execute_signal(signal)
                    logger.info(f"[SIGNAL_DEBUG] Trade execution result: {trade_result}")
                    
                    # Determine actual execution status
                    # Check if trade was really executed (not just tool ran successfully)
                    action = trade_result.get("action", "")
                    trade_success = trade_result.get("success", False)
                    order_id = trade_result.get("order_id")  # OKX order ID = definitive success
                    
                    # If we have an order_id from OKX, the trade definitely succeeded
                    if order_id and trade_success:
                        trade_actually_executed = True
                        # Fix reasoning if it has wrong tag from ExecutorAgent
                        if signal and "[insufficient_margin]" in signal.reasoning:
                            # Remove the incorrect tag since trade actually succeeded
                            signal.reasoning = signal.reasoning.replace("[insufficient_margin]", "[new_long]")
                            logger.info(f"[SIGNAL_DEBUG] Fixed reasoning tag: replaced [insufficient_margin] with [new_long]")
                    else:
                        # Failed actions: insufficient_margin, close_short_failed, etc.
                        failed_actions = ["insufficient_margin", "close_short_failed", "close_long_failed", "failed"]
                        trade_actually_executed = trade_success and action not in failed_actions
                    
                    self._trade_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "signal": signal.model_dump(),
                        "status": "executed" if trade_actually_executed else "failed",
                        "trade_result": trade_result
                    })
                    logger.info(f"[SIGNAL_DEBUG] History now has {len(self._trade_history)} entries")

                    # Broadcast trade executed event so frontend can refresh data
                    await self._broadcast({
                        "type": "trade_executed",
                        "signal": signal.model_dump(),
                        "success": trade_actually_executed,
                        "trade_result": trade_result
                    })
            else:
                # No signal generated - record this too
                logger.info(f"[SIGNAL_DEBUG] Signal is None, recording no_signal status")
                self._trade_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "signal": None,
                    "status": "no_signal",
                    "trade_result": {"action": "none", "message": "未产生有效决策信号"}
                })
                logger.info(f"[SIGNAL_DEBUG] History now has {len(self._trade_history)} entries")

        except Exception as e:
            logger.error(f"Error in analysis cycle: {e}")
            await self._broadcast({
                "type": "analysis_error",
                "error": str(e)
            })

    async def _execute_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """
        Execute a trading signal via the paper trader.

        Args:
            signal: The trading signal to execute

        Returns:
            Dict with execution result including success status and trade details
        """
        if not self.paper_trader:
            return {"success": False, "error": "Paper trader not initialized"}

        if signal.direction == "hold":
            return {"success": True, "action": "hold", "message": "No trade executed - hold signal"}

        try:
            # Get account balance to calculate position size
            account = await self.paper_trader.get_account()
            available_balance = account.get("available_balance", 0)

            # Calculate amount in USDT based on signal's amount_percent
            amount_usdt = available_balance * signal.amount_percent

            logger.info(f"Executing {signal.direction} signal: ${amount_usdt:.2f} @ {signal.leverage}x leverage")

            # Check if we already have a position
            position = await self.paper_trader.get_position()
            if position and position.get("has_position"):
                # 🔧 FIX Issue #3: 在hedge mode中不要自动关闭仓位反转
                # 因为在OKX hedge mode中，LONG和SHORT可以同时存在
                existing_direction = position.get("direction")
                if existing_direction and existing_direction != signal.direction:
                    # 检查是否是OKX trader (hedge mode)
                    is_okx_trader = self.trader_type == "okx"
                    
                    if is_okx_trader:
                        # OKX hedge mode: 不自动关闭，避免关错仓位
                        logger.warning(f"[_execute_signal] OKX hedge mode: Cannot auto-close {existing_direction} to open {signal.direction}")
                        return {
                            "success": False, 
                            "action": "blocked",
                            "message": f"OKX hedge mode: 已存在{existing_direction}仓位，请先手动平仓后再反向开仓",
                            "existing_direction": existing_direction,
                            "requested_direction": signal.direction
                        }
                    else:
                        # Paper trading: 可以安全关闭
                        logger.info(f"Closing existing {existing_direction} position before opening {signal.direction}")
                        close_result = await self.paper_trader.close_position(reason="signal_reversal")
                        await self._broadcast({
                            "type": "position_closed",
                            "reason": "signal_reversal",
                            "pnl": close_result.get("pnl", 0) if close_result else 0
                        })
                else:
                    # Same direction, skip opening new position
                    return {"success": True, "action": "skip", "message": f"Already in {existing_direction} position"}

            # Execute the trade
            if signal.direction == "long":
                result = await self.paper_trader.open_long(
                    symbol=signal.symbol,
                    leverage=signal.leverage,
                    amount_usdt=amount_usdt,
                    tp_price=signal.take_profit_price,
                    sl_price=signal.stop_loss_price
                )
            else:  # short
                result = await self.paper_trader.open_short(
                    symbol=signal.symbol,
                    leverage=signal.leverage,
                    amount_usdt=amount_usdt,
                    tp_price=signal.take_profit_price,
                    sl_price=signal.stop_loss_price
                )

            if result.get("success"):
                logger.info(f"Trade executed successfully: {signal.direction} position opened")
                await self._broadcast({
                    "type": "trade_executed",
                    "direction": signal.direction,
                    "leverage": signal.leverage,
                    "amount_usdt": amount_usdt,
                    "entry_price": result.get("entry_price"),
                    "tp_price": signal.take_profit_price,
                    "sl_price": signal.stop_loss_price
                })
            else:
                logger.error(f"Trade execution failed: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return {"success": False, "error": str(e)}

    async def _run_trading_meeting(self, reason: str) -> Optional[TradingSignal]:
        """Run a trading meeting"""
        # Create agents with toolkit
        agents = create_trading_agents(toolkit=self.toolkit)

        # Create meeting config
        meeting_config = TradingMeetingConfig(
            symbol=self.config.symbol,
            max_leverage=self.config.risk_limits.max_leverage,
            max_position_percent=self.config.risk_limits.max_position_percent,
            min_confidence=self.config.risk_limits.min_confidence
        )

        # Create meeting
        self._current_meeting = TradingMeeting(
            agents=agents,
            llm_service=self.llm_service,
            config=meeting_config,
            on_message=self._on_meeting_message,
            toolkit=self.toolkit  # 🔧 NEW: Pass toolkit for TradeExecutor
        )

        # Run meeting
        signal = await self._current_meeting.run(context=reason)
        self._current_meeting = None

        return signal

    def _on_meeting_message(self, message: Dict):
        """Handle meeting message"""
        # Log for debugging
        logger.info(f"[MEETING MSG] agent_name={message.get('agent_name')}, content_len={len(message.get('content', ''))}")
        # Spread message first, then override type to ensure it's always "agent_message"
        asyncio.create_task(self._broadcast({
            **message,
            "type": "agent_message"  # Must come LAST to override any "type" in message
        }))

    def _on_scheduler_state_change(self, old_state, new_state):
        """Handle scheduler state change"""
        # Broadcast state change
        asyncio.create_task(self._broadcast({
            "type": "scheduler_state",
            "old_state": old_state.value,
            "new_state": new_state.value
        }))

        # Sync TriggerLock state with main scheduler
        async def _sync_lock():
            if self.trigger_scheduler and self.trigger_scheduler.trigger_lock:
                lock = self.trigger_scheduler.trigger_lock
                
                # Check enum values directly
                if new_state.value == "analyzing":
                     # Main analysis started -> Acquire lock
                    await lock.acquire()
                    logger.info("🔒 TriggerLock acquired (Main Analysis Started)")
                
                elif (old_state.value == "analyzing") and (new_state.value != "analyzing"):
                    # Main analysis finished -> Release lock (enter cooldown)
                    # Only release if we effectively hold the lock
                    if lock.state == "analyzing":
                        lock.release()
                        logger.info("🔓 TriggerLock released (Main Analysis Finished) -> Cooldown started")
        
        asyncio.create_task(_sync_lock())

    async def _on_position_closed(self, position, pnl: float, reason: str = None):
        """Handle position closed"""
        logger.info(f"Position closed with PnL: {pnl}" + (f", reason: {reason[:100]}..." if reason else ""))

        # Record result
        result = self.cooldown_manager.record_trade_result(pnl)

        # Run reflection meeting to analyze why trade succeeded/failed
        lessons = await self._run_reflection_meeting(position, pnl)

        # Update agent memory with lessons learned
        memory_store = await get_memory_store()
        trade_id = str(uuid.uuid4())

        # Use correct PascalCase agent IDs
        trading_agents = ["TechnicalAnalyst", "MacroEconomist", "SentimentAnalyst", "QuantStrategist", "RiskAssessor"]
        for i, agent_id in enumerate(trading_agents):
            lesson = lessons.get(agent_id, f"交易结果: {'盈利' if pnl > 0 else '亏损'} ${abs(pnl):.2f}")
            await memory_store.record_trade_result(
                agent_id=agent_id,
                agent_name=agent_id,
                trade_id=trade_id,
                prediction={"direction": position.direction},
                actual_outcome={"pnl": pnl},
                pnl=pnl,
                lesson=lesson
            )

        await self._broadcast({
            "type": "position_closed",
            "pnl": pnl,
            "can_continue": result,
            "lessons": lessons
        })

        # Trigger new analysis if not in cooldown
        if result:
            await self.scheduler.trigger_now(reason="position_closed")

    async def _run_reflection_meeting(self, position, pnl: float) -> Dict[str, str]:
        """
        Run a reflection meeting to analyze why trade succeeded or failed.
        Each agent reflects on their prediction and learns from the outcome.

        Returns:
            Dict mapping agent_id to their learned lesson
        """
        logger.info(f"Starting reflection meeting for trade with PnL: {pnl}")

        outcome_type = "Take Profit" if pnl > 0 else "Stop Loss"
        lessons = {}

        # Build reflection context
        reflection_context = f"""## Trade Reflection Meeting

### Trade Result
- **Outcome**: {outcome_type}
- **Direction**: {position.direction}
- **Entry Price**: {position.entry_price:.2f}
- **Exit Price**: {position.current_price:.2f}
- **PnL**: ${pnl:.2f}
- **Leverage**: {position.leverage}x

### Please answer the following questions (within 50 words):
1. What was the basis for your judgment?
2. Why was your judgment {'correct' if pnl > 0 else 'incorrect'}?
3. What did you learn from this trade?
"""

        # Create agents with toolkit
        agents = create_trading_agents(toolkit=self.toolkit)

        await self._broadcast({
            "type": "reflection_started",
            "pnl": pnl,
            "outcome": outcome_type
        })

        # Have each agent reflect
        for agent in agents:  # agents is a List, not Dict
            try:
                messages = [
                    {"role": "system", "content": agent.system_prompt or agent.role_prompt},
                    {"role": "user", "content": reflection_context}
                ]

                response = await agent._call_llm(messages)

                # Extract content
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

                # Extract a concise lesson (first 200 chars)
                lesson = content[:200] if content else f"Further analysis needed for {outcome_type} reason"
                lessons[agent.id] = lesson

                # Broadcast reflection
                await self._broadcast({
                    "type": "agent_reflection",
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "lesson": lesson,
                    "outcome": outcome_type
                })

                logger.info(f"Agent {agent.name} reflection: {lesson[:100]}...")

            except Exception as e:
                logger.error(f"Error in reflection for {agent.name}: {e}")
                lessons[agent.id] = f"Reflection failed: {str(e)[:50]}"

        await self._broadcast({
            "type": "reflection_completed",
            "pnl": pnl,
            "lessons_count": len(lessons)
        })

        return lessons

    async def _on_tp_hit(self, position, price: float):
        """Handle take profit hit"""
        logger.info(f"Take profit hit at {price}")
        await self._broadcast({
            "type": "tp_hit",
            "price": price,
            "position": {
                "direction": position.direction,
                "entry_price": position.entry_price
            }
        })

    async def _on_sl_hit(self, position, price: float):
        """Handle stop loss hit"""
        logger.info(f"Stop loss hit at {price}")
        await self._broadcast({
            "type": "sl_hit",
            "price": price,
            "position": {
                "direction": position.direction,
                "entry_price": position.entry_price
            }
        })

    async def _on_pnl_update(self, pnl: float, pnl_percent: float, position):
        """Handle PnL update"""
        await self._broadcast({
            "type": "pnl_update",
            "pnl": pnl,
            "pnl_percent": pnl_percent
        })

    async def _check_tavily_health(self) -> bool:
        """
        Check if Tavily/MCP search service is available.
        Returns True if healthy, False if unavailable.
        
        CRITICAL: If search is down, we should NOT make trading decisions
        as they would be based on incomplete/stale information.
        """
        import httpx
        
        web_search_url = os.getenv("WEB_SEARCH_URL", "http://web_search_service:8010")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try health endpoint first
                try:
                    response = await client.get(f"{web_search_url}/health")
                    if response.status_code == 200:
                        logger.info("✅ Tavily/MCP search service is healthy")
                        return True
                except Exception:
                    pass
                
                # Fallback: try actual search endpoint
                try:
                    response = await client.post(
                        f"{web_search_url}/mcp/tools/search",
                        json={"query": "bitcoin price", "max_results": 1},
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("results") or data.get("content"):
                            logger.info("✅ Tavily/MCP search service operational (search test passed)")
                            return True
                except Exception as e:
                    logger.warning(f"Tavily search test failed: {e}")
                
                logger.error("❌ Tavily/MCP search service is unavailable")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to check Tavily health: {e}")
            return False

    async def _broadcast(self, message: Dict):
        """Broadcast message to all WebSocket clients"""
        import json
        dead_clients = []

        msg_type = message.get('type', 'unknown')
        client_count = len(self._ws_clients)
        if msg_type == 'agent_message':
            logger.info(f"[BROADCAST] type={msg_type}, clients={client_count}, agent={message.get('agent_name')}")
            # Store agent messages for persistence
            self._discussion_messages.append({
                'agent_name': message.get('agent_name', 'Unknown'),
                'content': message.get('content', ''),
                'timestamp': message.get('timestamp', datetime.now().isoformat())
            })
            # Keep only last 100 messages
            if len(self._discussion_messages) > 100:
                self._discussion_messages = self._discussion_messages[-100:]

        for client_id, ws in self._ws_clients.items():
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"[BROADCAST] Failed to send to {client_id}: {e}")
                dead_clients.append(client_id)

        for client_id in dead_clients:
            del self._ws_clients[client_id]

    def register_ws_client(self, client_id: str, ws: WebSocket):
        """Register WebSocket client"""
        self._ws_clients[client_id] = ws
        logger.info(f"WebSocket client registered: {client_id}")

    def unregister_ws_client(self, client_id: str):
        """Unregister WebSocket client"""
        if client_id in self._ws_clients:
            del self._ws_clients[client_id]
            logger.info(f"WebSocket client unregistered: {client_id}")

    async def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        # Determine actual running state based on scheduler state
        # enabled should reflect if the system is actually running, not just configured
        is_running = False
        if self.scheduler:
            scheduler_state = self.scheduler.state.value
            # Consider running if scheduler is in RUNNING, ANALYZING, or EXECUTING state
            is_running = scheduler_state in ["running", "analyzing", "executing"]

        trader_status = await self.paper_trader.get_status() if self.paper_trader else None

        return {
            "initialized": self._initialized,
            "enabled": is_running,  # Use actual running state, not config flag
            "config_enabled": self.config.enabled,  # Keep original config for reference
            "demo_mode": self.config.demo_mode,
            "symbol": self.config.symbol,
            "trader_type": self.trader_type,  # "paper" or "okx"
            "scheduler": self.scheduler.get_status() if self.scheduler else None,
            "paper_trader": trader_status,
            "trader": trader_status,  # Alias for clarity
            "cooldown": self.cooldown_manager.get_cooldown_status(),
            "connected_clients": len(self._ws_clients)
        }


async def get_trading_system(llm_service=None) -> TradingSystem:
    """Get or create trading system singleton"""
    global _trading_system
    if _trading_system is None:
        _trading_system = TradingSystem(llm_service=llm_service)
        await _trading_system.initialize()
    return _trading_system


# ===== REST API Endpoints =====

@router.get("/status")
async def get_status():
    """Get trading system status"""
    system = await get_trading_system()
    return await system.get_status()


@router.get("/funding")
async def get_funding_rate():
    """Get current funding rate and cost analysis"""
    try:
        from app.core.trading.funding import (
            get_funding_data_service,
            get_funding_calculator,
            get_funding_config
        )
        
        # Get funding rate data
        data_service = await get_funding_data_service()
        funding_rate = await data_service.get_current_rate("BTC-USDT-SWAP")
        
        if not funding_rate:
            return {
                "available": False,
                "error": "Unable to fetch funding rate from OKX"
            }
        
        # Get config
        config = get_funding_config()
        calculator = get_funding_calculator()
        
        # Calculate cost estimates for standard position
        # Assume $1000 position with 3x leverage
        position_value = 1000
        margin = position_value / 3
        leverage = 3
        
        estimate_8h = calculator.estimate_holding_cost(
            position_value=position_value,
            margin=margin,
            leverage=leverage,
            holding_hours=8,
            current_rate=funding_rate.rate,
            direction="long"
        )
        
        estimate_24h = calculator.estimate_holding_cost(
            position_value=position_value,
            margin=margin,
            leverage=leverage,
            holding_hours=24,
            current_rate=funding_rate.rate,
            direction="long"
        )
        
        return {
            "available": True,
            "symbol": funding_rate.symbol,
            "rate": funding_rate.rate,
            "rate_percent": round(funding_rate.rate_percent, 4),
            "avg_24h": round(funding_rate.avg_24h * 100, 4) if funding_rate.avg_24h else None,
            "avg_7d": round(funding_rate.avg_7d * 100, 4) if funding_rate.avg_7d else None,
            "trend": funding_rate.trend.value if funding_rate.trend else "stable",
            "is_extreme": funding_rate.is_extreme,
            "minutes_to_settlement": funding_rate.minutes_to_settlement,
            "next_settlement_time": funding_rate.next_settlement_time.isoformat() if funding_rate.next_settlement_time else None,
            
            # Cost analysis (per $1000 position at 3x)
            "cost_analysis": {
                "position_value": position_value,
                "leverage": leverage,
                "cost_8h": round(estimate_8h.estimated_cost, 4),
                "cost_24h": round(estimate_24h.estimated_cost, 4),
                "cost_8h_percent": round(estimate_8h.cost_percent_of_margin, 3),
                "cost_24h_percent": round(estimate_24h.cost_percent_of_margin, 3),
                "break_even_24h": round(estimate_24h.break_even_price_move, 3)
            },
            
            # Config thresholds
            "thresholds": {
                "force_close_percent": config.force_close_threshold,
                "warning_percent": config.warning_threshold,
                "pre_settlement_buffer_min": config.pre_settlement_buffer_minutes,
                "max_holding_hours": config.default_max_holding_hours
            }
        }
    except Exception as e:
        logger.error(f"Error fetching funding rate: {e}")
        return {
            "available": False,
            "error": str(e)
        }


@router.get("/account")
async def get_account():
    """Get account information"""
    system = await get_trading_system()
    if system.paper_trader:
        account = await system.paper_trader.get_account()
        return account
    return {"error": "Paper trader not initialized"}


@router.get("/position")
async def get_position(symbol: str = "BTC-USDT-SWAP"):
    """Get current position"""
    system = await get_trading_system()
    if system.paper_trader:
        position = await system.paper_trader.get_position()
        if position:
            return position
        return {"has_position": False}
    return {"error": "Paper trader not initialized"}


@router.get("/history")
async def get_trade_history(limit: int = Query(default=50, le=100)):
    """Get trade history including signals and actual closed trades"""
    system = await get_trading_system()

    # 🔧 CRITICAL FIX: Always use async get_trade_history() for REAL OKX data
    # The old get_filtered_trade_history() returned local estimates without fees
    actual_trades = []
    if system.paper_trader:
        # Call the async method that fetches from OKX API
        actual_trades = await system.paper_trader.get_trade_history(limit)

    # 🆕 Get signals from Redis for persistence across restarts
    signals = []
    try:
        decision_store = await get_decision_store()
        redis_signals = await decision_store.get_recent_decisions_for_frontend(limit)
        if redis_signals:
            signals = redis_signals
            logger.info(f"[get_trade_history] Loaded {len(signals)} signals from Redis")
    except Exception as e:
        logger.warning(f"[get_trade_history] Redis failed, using memory: {e}")
    
    # Fallback to memory if Redis is empty
    if not signals and system._trade_history:
        signals = system._trade_history[-limit:]
        logger.info(f"[get_trade_history] Using {len(signals)} signals from memory")

    return {
        "trades": actual_trades,  # REAL closed trades with actual PnL from OKX
        "signals": signals  # Signal history from Redis (persisted) or memory (fallback)
    }


@router.get("/messages")
async def get_discussion_messages(limit: int = Query(default=100, le=200)):
    """Get discussion messages history for state restoration"""
    system = await get_trading_system()
    return {"messages": system._discussion_messages[-limit:]}


@router.get("/equity")
async def get_equity_history(limit: int = Query(default=100, le=500)):
    """Get equity history for charting"""
    system = await get_trading_system()
    if system.paper_trader:
        return {"data": await system.paper_trader.get_equity_history(limit)}
    return {"data": []}


@router.get("/drawdown")
async def get_max_drawdown(start_date: Optional[str] = Query(default=None, description="Start date in YYYY-MM-DD format")):
    """
    Get maximum drawdown statistics from trade history.
    
    Args:
        start_date: Optional start date filter (YYYY-MM-DD format)
        
    Returns:
        - max_drawdown_pct: Maximum drawdown percentage
        - max_drawdown_usd: Maximum drawdown in USD
        - peak_equity: Peak equity value
        - trough_equity: Trough equity value  
        - current_drawdown_pct: Current drawdown from peak
        - trades_analyzed: Number of trades analyzed
    """
    system = await get_trading_system()
    
    if not system.paper_trader:
        return {
            "error": "Trader not initialized",
            "max_drawdown_pct": 0.0,
            "max_drawdown_usd": 0.0,
            "trades_analyzed": 0
        }
    
    try:
        # 🆕 Use filtered trade history if metrics baseline is set
        if hasattr(system.paper_trader, 'get_filtered_trade_history'):
            trades = system.paper_trader.get_filtered_trade_history()[-100:]
        else:
            trades = await system.paper_trader.get_trade_history(limit=100)
        
        # Filter by start_date if provided (additional manual filter)
        if start_date and trades:
            try:
                from datetime import datetime
                filter_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                trades = [
                    t for t in trades 
                    if datetime.fromisoformat(
                        t.get('closed_at', t.get('timestamp', t.get('closeTime', '2000-01-01'))).replace('Z', '+00:00')
                    ) >= filter_date
                ]
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid start_date format: {start_date}, using all trades. Error: {e}")

        
        if not trades:
            initial_balance = getattr(system.paper_trader, 'initial_balance', 5000)
            return {
                'max_drawdown_pct': 0.0,
                'max_drawdown_usd': 0.0,
                'peak_equity': initial_balance,
                'trough_equity': initial_balance,
                'current_drawdown_pct': 0.0,
                'recovery_pct': 100.0,
                'start_date': start_date,
                'trades_analyzed': 0
            }
        
        # Calculate drawdown from trades
        initial_balance = getattr(system.paper_trader, 'initial_balance', 5000)
        equity_curve = [initial_balance]
        running_equity = initial_balance
        
        for trade in trades:
            # Handle different PnL field names from OKX API vs local
            pnl = trade.get('pnl') or trade.get('realizedPnl') or trade.get('pnl_usd') or 0
            if isinstance(pnl, str):
                try:
                    pnl = float(pnl)
                except:
                    pnl = 0
            running_equity += pnl
            equity_curve.append(running_equity)
        
        # Calculate max drawdown
        peak = equity_curve[0]
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        peak_at_max_dd = peak
        trough_at_max_dd = peak
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            
            drawdown = peak - equity
            drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0
            
            if drawdown_pct > max_drawdown_pct:
                max_drawdown_pct = drawdown_pct
                max_drawdown = drawdown
                peak_at_max_dd = peak
                trough_at_max_dd = equity
        
        # Current drawdown
        current_equity = equity_curve[-1]
        current_peak = max(equity_curve)
        current_drawdown_pct = ((current_peak - current_equity) / current_peak * 100) if current_peak > 0 else 0
        
        # Recovery percentage
        if max_drawdown > 0:
            recovery_pct = min(100.0, ((current_equity - trough_at_max_dd) / max_drawdown * 100))
        else:
            recovery_pct = 100.0
        
        return {
            'max_drawdown_pct': round(max_drawdown_pct, 2),
            'max_drawdown_usd': round(max_drawdown, 2),
            'peak_equity': round(peak_at_max_dd, 2),
            'trough_equity': round(trough_at_max_dd, 2),
            'current_equity': round(current_equity, 2),
            'current_drawdown_pct': round(current_drawdown_pct, 2),
            'recovery_pct': round(recovery_pct, 1),
            'start_date': start_date,
            'trades_analyzed': len(trades)
        }
        
    except Exception as e:
        logger.error(f"Error calculating drawdown: {e}")
        return {
            "error": str(e),
            "max_drawdown_pct": 0.0,
            "max_drawdown_usd": 0.0,
            "trades_analyzed": 0
        }


@router.get("/performance")
async def get_performance_metrics(start_date: Optional[str] = Query(default=None, description="Start date in YYYY-MM-DD format")):
    """
    Get performance metrics including Sharpe Ratio, Sortino Ratio, Alpha, etc.
    
    Args:
        start_date: Optional start date filter (YYYY-MM-DD format)
        
    Returns:
        - sharpe_ratio: Risk-adjusted return
        - sortino_ratio: Downside risk-adjusted return
        - alpha: Excess return over benchmark
        - win_rate: Winning trade percentage
        - profit_factor: Gross profit / Gross loss
        - total_return_pct: Total return percentage
        - volatility_pct: Return volatility
        - And more...
    """
    system = await get_trading_system()
    
    if not system.paper_trader:
        return {
            "error": "Trader not initialized",
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "alpha": 0.0,
            "trades_analyzed": 0
        }
    
    try:
        # Check if trader has calculate_performance_metrics method (OKXTrader)
        if hasattr(system.paper_trader, 'calculate_performance_metrics'):
            return await system.paper_trader.calculate_performance_metrics(start_date)
        
        # 🆕 Use filtered trade history if metrics baseline is set
        import math
        if hasattr(system.paper_trader, 'get_filtered_trade_history'):
            trades = system.paper_trader.get_filtered_trade_history()[-200:]
        else:
            trades = await system.paper_trader.get_trade_history(limit=200)
        
        # Additional start_date filter if provided
        if start_date and trades:
            try:
                from datetime import datetime
                filter_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                trades = [
                    t for t in trades 
                    if datetime.fromisoformat(
                        t.get('closed_at', '2000-01-01').replace('Z', '+00:00')
                    ) >= filter_date
                ]
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid start_date format: {start_date}. Error: {e}")

        
        if not trades or len(trades) < 2:
            return {
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'alpha': 0.0,
                'beta': 1.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_return_pct': 0.0,
                'trades_analyzed': len(trades) if trades else 0,
                'start_date': start_date
            }
        
        # Calculate metrics
        pnl_list = [t.get('pnl', 0) for t in trades]
        pnl_pct_list = [t.get('pnl_percent', 0) for t in trades]
        
        wins = [p for p in pnl_list if p > 0]
        losses = [p for p in pnl_list if p < 0]
        
        win_rate = len(wins) / len(pnl_list) * 100 if pnl_list else 0
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        initial = getattr(system.paper_trader, 'initial_balance', 5000)
        total_pnl = sum(pnl_list)
        total_return_pct = (total_pnl / initial) * 100 if initial > 0 else 0
        
        # Sharpe calculation
        if len(pnl_pct_list) > 1:
            mean_return = sum(pnl_pct_list) / len(pnl_pct_list)
            variance = sum((r - mean_return) ** 2 for r in pnl_pct_list) / (len(pnl_pct_list) - 1)
            volatility = math.sqrt(variance)
            sharpe_ratio = (mean_return / volatility) * math.sqrt(len(trades)) if volatility > 0 else 0
        else:
            sharpe_ratio = 0
            volatility = 0
        
        return {
            'sharpe_ratio': round(sharpe_ratio, 2),
            'sortino_ratio': round(sharpe_ratio, 2),  # Simplified
            'alpha': round(total_return_pct, 2),
            'beta': 1.0,
            'win_rate': round(win_rate, 2),
            'profit_factor': round(min(profit_factor, 99.99), 2),
            'total_return_pct': round(total_return_pct, 2),
            'volatility_pct': round(volatility, 2),
            'best_trade': round(max(pnl_list), 2) if pnl_list else 0,
            'worst_trade': round(min(pnl_list), 2) if pnl_list else 0,
            'trades_analyzed': len(trades),
            'start_date': start_date
        }
        
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        return {
            "error": str(e),
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "alpha": 0.0,
            "trades_analyzed": 0
        }


@router.post("/start")
async def start_trading():
    """Start auto trading"""
    system = await get_trading_system()
    await system.start()
    return {"status": "started", "message": "Trading system started"}


@router.post("/stop")
async def stop_trading():
    """Stop auto trading"""
    system = await get_trading_system()
    await system.stop()
    return {"status": "stopped", "message": "Trading system stopped"}


@router.post("/trigger")
async def manual_trigger(reason: str = "manual"):
    """Manually trigger analysis cycle"""
    system = await get_trading_system()
    if system.scheduler:
        success = await system.scheduler.trigger_now(reason=reason)
        return {"triggered": success}
    return {"error": "Scheduler not initialized"}


@router.post("/close")
async def close_position():
    """Manually close current position"""
    system = await get_trading_system()
    if not system.paper_trader:
        return {"error": "Paper trader not initialized"}

    position = await system.paper_trader.get_position()
    if not position or not position.get("has_position"):
        return {"error": "No open position to close"}

    try:
        # Close position at current market price
        result = await system.paper_trader.close_position(reason="manual_close")

        if result:
            logger.info(f"Position manually closed: {result}")
            await system._broadcast({
                "type": "position_closed",
                "pnl": result.get("pnl", 0),
                "reason": "manual_close",
                "timestamp": datetime.now().isoformat()
            })
            return {
                "status": "closed",
                "pnl": result.get("pnl", 0),
                "message": "Position closed successfully"
            }
        else:
            return {"error": "Failed to close position"}
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        return {"error": str(e)}


@router.post("/reset-metrics")
async def reset_metrics_baseline():
    """
    Reset metrics baseline - all performance metrics will be calculated from this point.
    
    Use this when:
    1. Trade history is corrupted/polluted by bugs
    2. Starting fresh evaluation after system issues
    3. Beginning a new performance tracking period
    
    Returns the new baseline timestamp.
    """
    system = await get_trading_system()
    if not system.paper_trader:
        return {"error": "Trader not initialized"}

    try:
        result = await system.paper_trader.reset_metrics_baseline()
        logger.info(f"[API] Metrics baseline reset: {result}")
        return result
    except Exception as e:
        logger.error(f"Error resetting metrics baseline: {e}")
        return {"error": str(e)}


@router.get("/agents")
async def get_agents():
    """Get trading agent configuration"""
    return {"agents": get_trading_agent_config()}


@router.get("/agents/memory")
async def get_agent_memories():
    """Get agent memories and performance stats"""
    memory_store = await get_memory_store()
    memories = await memory_store.get_all_memories()
    team_summary = await memory_store.get_team_summary()

    return {
        "team_summary": team_summary,
        "agents": {
            agent_id: memory.to_dict()
            for agent_id, memory in memories.items()
        }
    }


class TradingConfigUpdate(BaseModel):
    """Trading config update request"""
    analysis_interval_hours: Optional[int] = None
    max_leverage: Optional[int] = None
    max_position_percent: Optional[float] = None
    enabled: Optional[bool] = None
    use_okx_trading: Optional[bool] = None  # Switch to OKX demo trading


@router.get("/config")
async def get_config():
    """Get current trading configuration"""
    system = await get_trading_system()
    return {
        "analysis_interval_hours": system.config.analysis_interval_hours,
        "max_leverage": system.config.risk_limits.max_leverage,
        "max_position_percent": system.config.risk_limits.max_position_percent,
        "enabled": system.config.enabled,
        "trader_type": system.trader_type,  # "paper" or "okx"
        "symbol": system.config.symbol,
        "initial_capital": system.config.initial_capital,
        "risk_limits": {
            "max_daily_loss_percent": system.config.risk_limits.max_daily_loss_percent,
            "consecutive_loss_limit": system.config.risk_limits.consecutive_loss_limit,
            "min_confidence": system.config.risk_limits.min_confidence
        }
    }


@router.patch("/config")
async def update_config(update: TradingConfigUpdate):
    """Update trading configuration"""
    system = await get_trading_system()
    needs_restart = False

    if update.analysis_interval_hours:
        system.config.analysis_interval_hours = update.analysis_interval_hours
        if system.scheduler:
            system.scheduler.interval_hours = update.analysis_interval_hours
            system.scheduler.interval_seconds = update.analysis_interval_hours * 3600

    if update.max_leverage:
        system.config.risk_limits.max_leverage = update.max_leverage

    if update.max_position_percent:
        system.config.risk_limits.max_position_percent = update.max_position_percent

    if update.enabled is not None:
        system.config.enabled = update.enabled

    # Handle OKX trading switch
    if update.use_okx_trading is not None:
        current_is_okx = system.trader_type == "okx"
        if update.use_okx_trading != current_is_okx:
            needs_restart = True
            # Set environment variable for restart
            os.environ["USE_OKX_TRADING"] = "true" if update.use_okx_trading else "false"
            logger.info(f"Trader type will switch to: {'OKX Demo' if update.use_okx_trading else 'Paper Trader'}")

    response = {
        "status": "updated",
        "config": system.config.model_dump(),
        "trader_type": system.trader_type,
        "needs_restart": needs_restart
    }

    if needs_restart:
        response["message"] = "Trading system needs restart to apply trader type change. Please reset the system."

    return response


@router.post("/cooldown/end")
async def end_cooldown():
    """Force end cooldown period"""
    system = await get_trading_system()
    system.cooldown_manager.force_end_cooldown()
    return {"status": "cooldown_ended"}


@router.post("/reset-daily-pnl")
async def reset_daily_pnl():
    """
    Reset daily PnL tracking and halt status.
    
    Use this when:
    1. Daily PnL data is corrupted (e.g., showing impossible values)
    2. Manual override needed after fixing bugs
    3. Trading is incorrectly halted due to bad data
    
    Returns:
        Dict with old and new values
    """
    system = await get_trading_system()
    
    if not system.trader:
        return {"success": False, "error": "Trading system not initialized"}
    
    # OKXTrader has reset_daily_pnl method
    if hasattr(system.trader, 'reset_daily_pnl'):
        result = await system.trader.reset_daily_pnl()
        return result
    else:
        return {"success": False, "error": "Trader does not support daily PnL reset"}


@router.post("/reset")
async def reset_trading_system():
    """
    Reset the trading system.

    This will:
    - Stop the trading system if running
    - Close any open positions
    - Clear trade history
    - Reset cooldown
    - Clear agent memories
    - Re-initialize the system
    """
    global _trading_system

    logger.info("Resetting trading system...")

    try:
        if _trading_system:
            # Stop system if running
            await _trading_system.stop()

            # Reset paper trader completely (balance, trades, position)
            if _trading_system.paper_trader:
                await _trading_system.paper_trader.reset()
                logger.info("Paper trader reset: balance, trades, and position cleared")

            # Clear trade history
            _trading_system._trade_history = []

            # Reset cooldown
            _trading_system.cooldown_manager.force_end_cooldown()
            _trading_system.cooldown_manager.consecutive_losses = 0

            # Broadcast reset
            await _trading_system._broadcast({
                "type": "system_reset",
                "message": "Trading system has been reset",
                "timestamp": datetime.now().isoformat()
            })

        # Clear agent memories
        memory_store = await get_memory_store()
        await memory_store.clear_all_memories()

        # Reset singleton to force re-initialization
        _trading_system = None

        # Re-initialize
        system = await get_trading_system()

        logger.info("Trading system reset complete")

        return {
            "status": "reset_complete",
            "message": "Trading system has been reset successfully",
            "trader_type": system.trader_type,
            "account": await system.paper_trader.get_account() if system.paper_trader else None
        }

    except Exception as e:
        logger.error(f"Error resetting trading system: {e}")
        return {"status": "error", "error": str(e)}


# ===== WebSocket Endpoint =====

@router.websocket("/ws/{session_id}")
async def trading_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket for real-time trading updates.

    Sends:
    - system_started/stopped
    - analysis_started/completed
    - agent_message
    - signal_generated
    - position_closed
    - pnl_update
    - tp_hit/sl_hit
    """
    await websocket.accept()
    logger.info(f"Trading WebSocket connected: {session_id}")

    system = await get_trading_system()
    system.register_ws_client(session_id, websocket)

    # Send initial status
    await websocket.send_json({
        "type": "connected",
        "status": await system.get_status()
    })

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            logger.debug(f"Received from {session_id}: {data}")

            # Handle commands
            import json
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception:
                pass

    except WebSocketDisconnect:
        logger.info(f"Trading WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Trading WebSocket error: {e}")
    finally:
        system.unregister_ws_client(session_id)


# ===== Mobile Status Page =====

MOBILE_STATUS_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Magellan Trading Status</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 10px;
            min-height: 100vh;
        }
        .header {
            text-align: center;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            margin-bottom: 15px;
        }
        .header h1 { font-size: 1.3em; }
        .header p { font-size: 0.8em; opacity: 0.8; margin-top: 5px; }
        .card {
            background: #16213e;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .card-title {
            font-size: 0.9em;
            color: #667eea;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #333;
        }
        .row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 0.85em;
        }
        .label { color: #888; }
        .value { font-weight: 500; }
        .positive { color: #4ade80; }
        .negative { color: #f87171; }
        .neutral { color: #fbbf24; }
        .position-card {
            background: linear-gradient(135deg, #1e3a5f 0%, #16213e 100%);
            border: 1px solid #334;
        }
        .position-direction {
            font-size: 1.5em;
            font-weight: bold;
            text-align: center;
            padding: 10px;
        }
        .position-direction.long { color: #4ade80; }
        .position-direction.short { color: #f87171; }
        .position-direction.none { color: #888; }
        .pnl-display {
            text-align: center;
            font-size: 1.8em;
            font-weight: bold;
            padding: 15px;
        }
        .trade-item {
            background: #1e293b;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 8px;
            font-size: 0.8em;
        }
        .trade-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
        }
        .trade-direction {
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 4px;
        }
        .trade-direction.long { background: #166534; color: #4ade80; }
        .trade-direction.short { background: #991b1b; color: #f87171; }
        .btn {
            display: block;
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            margin-bottom: 10px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-secondary {
            background: #334155;
            color: #eee;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #888;
        }
        .error {
            background: #7f1d1d;
            color: #fca5a5;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        .last-update {
            text-align: center;
            font-size: 0.75em;
            color: #666;
            margin-top: 10px;
        }
        .status-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-dot.running { background: #4ade80; }
        .status-dot.stopped { background: #f87171; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Magellan Trading</h1>
        <p>Auto Trading Status Monitor</p>
    </div>

    <div id="content">
        <div class="loading">Loading...</div>
    </div>

    <div style="margin-top: 15px;">
        <button class="btn btn-primary" onclick="refresh()">Refresh</button>
        <button class="btn btn-secondary" onclick="toggleAutoRefresh()">
            Auto Refresh: <span id="autoRefreshStatus">OFF</span>
        </button>
    </div>

    <div class="last-update" id="lastUpdate"></div>

    <script>
        const SERVER = window.location.origin;
        let autoRefresh = false;
        let refreshInterval = null;

        async function fetchData(endpoint) {
            try {
                const response = await fetch(`${SERVER}/api/trading/${endpoint}`, {
                    method: 'GET',
                    headers: { 'Accept': 'application/json' }
                });
                return await response.json();
            } catch (e) {
                console.error(`Error fetching ${endpoint}:`, e);
                return null;
            }
        }

        function formatNumber(num, decimals = 2) {
            if (num === null || num === undefined) return 'N/A';
            return Number(num).toLocaleString('en-US', {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            });
        }

        function formatPnL(pnl) {
            const cls = pnl >= 0 ? 'positive' : 'negative';
            const sign = pnl >= 0 ? '+' : '';
            return `<span class="${cls}">${sign}$${formatNumber(pnl)}</span>`;
        }

        async function refresh() {
            const content = document.getElementById('content');
            content.innerHTML = '<div class="loading">Loading...</div>';

            try {
                const [status, account, position, history] = await Promise.all([
                    fetchData('status'),
                    fetchData('account'),
                    fetchData('position'),
                    fetchData('history?limit=5')
                ]);

                if (!status) {
                    content.innerHTML = '<div class="error">Cannot connect to server</div>';
                    return;
                }

                let html = '';

                // System Status
                const isRunning = status.enabled;
                html += `
                    <div class="card">
                        <div class="card-title">System Status</div>
                        <div class="row">
                            <span class="label">Status</span>
                            <span class="value">
                                <span class="status-dot ${isRunning ? 'running' : 'stopped'}"></span>
                                ${isRunning ? 'Running' : 'Stopped'}
                            </span>
                        </div>
                        <div class="row">
                            <span class="label">Mode</span>
                            <span class="value">${status.demo_mode ? 'Demo' : 'Live'}</span>
                        </div>
                        <div class="row">
                            <span class="label">Symbol</span>
                            <span class="value">${status.symbol || 'N/A'}</span>
                        </div>
                        <div class="row">
                            <span class="label">Next Analysis</span>
                            <span class="value">${status.scheduler?.next_run?.substring(11, 19) || 'N/A'}</span>
                        </div>
                    </div>
                `;

                // Account
                if (account) {
                    const balance = account.balance || account.total_balance || 0;
                    const equity = account.equity || account.total_equity || balance;
                    html += `
                        <div class="card">
                            <div class="card-title">Account</div>
                            <div class="row">
                                <span class="label">Balance</span>
                                <span class="value">$${formatNumber(balance)}</span>
                            </div>
                            <div class="row">
                                <span class="label">Equity</span>
                                <span class="value">$${formatNumber(equity)}</span>
                            </div>
                        </div>
                    `;
                }

                // Position
                if (position) {
                    const hasPos = position.has_position;
                    const direction = position.direction || position.side || 'none';
                    const pnl = position.unrealized_pnl || 0;
                    const pnlPct = position.pnl_percent || 0;

                    html += `
                        <div class="card position-card">
                            <div class="card-title">Current Position</div>
                            <div class="position-direction ${hasPos ? direction : 'none'}">
                                ${hasPos ? direction.toUpperCase() : 'NO POSITION'}
                            </div>
                    `;

                    if (hasPos) {
                        html += `
                            <div class="pnl-display ${pnl >= 0 ? 'positive' : 'negative'}">
                                ${pnl >= 0 ? '+' : ''}$${formatNumber(pnl)}
                                <div style="font-size: 0.5em;">(${pnl >= 0 ? '+' : ''}${formatNumber(pnlPct)}%)</div>
                            </div>
                            <div class="row">
                                <span class="label">Entry</span>
                                <span class="value">$${formatNumber(position.entry_price)}</span>
                            </div>
                            <div class="row">
                                <span class="label">Current</span>
                                <span class="value">$${formatNumber(position.current_price || position.mark_price)}</span>
                            </div>
                            <div class="row">
                                <span class="label">Leverage</span>
                                <span class="value">${position.leverage || 1}x</span>
                            </div>
                            <div class="row">
                                <span class="label">TP / SL</span>
                                <span class="value">
                                    <span class="positive">$${formatNumber(position.tp_price)}</span> /
                                    <span class="negative">$${formatNumber(position.sl_price)}</span>
                                </span>
                            </div>
                        `;
                    }
                    html += `</div>`;
                }

                // Trade History
                if (history && history.trades && history.trades.length > 0) {
                    html += `
                        <div class="card">
                            <div class="card-title">Recent Trades</div>
                    `;
                    for (const trade of history.trades.slice(-5).reverse()) {
                        const dir = trade.direction || trade.side || 'N/A';
                        const pnl = trade.pnl || trade.realized_pnl || 0;
                        html += `
                            <div class="trade-item">
                                <div class="trade-header">
                                    <span class="trade-direction ${dir}">${dir.toUpperCase()}</span>
                                    ${formatPnL(pnl)}
                                </div>
                                <div class="row">
                                    <span class="label">Entry -> Exit</span>
                                    <span class="value">$${formatNumber(trade.entry_price)} -> $${formatNumber(trade.exit_price || trade.close_price)}</span>
                                </div>
                            </div>
                        `;
                    }
                    html += `</div>`;
                } else {
                    html += `
                        <div class="card">
                            <div class="card-title">Recent Trades</div>
                            <div style="text-align: center; color: #666; padding: 20px;">
                                No trades yet
                            </div>
                        </div>
                    `;
                }

                content.innerHTML = html;
                document.getElementById('lastUpdate').textContent =
                    `Last updated: ${new Date().toLocaleTimeString()}`;

            } catch (e) {
                content.innerHTML = `<div class="error">Error: ${e.message}</div>`;
            }
        }

        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            document.getElementById('autoRefreshStatus').textContent = autoRefresh ? 'ON (30s)' : 'OFF';

            if (autoRefresh) {
                refreshInterval = setInterval(refresh, 30000);
            } else {
                clearInterval(refreshInterval);
            }
        }

        // Initial load
        refresh();
    </script>
</body>
</html>
"""

@router.get("/dashboard", response_class=HTMLResponse)
async def trading_dashboard():
    """Mobile-friendly trading status dashboard"""
    return MOBILE_STATUS_HTML


# ============================================
# Mock Testing APIs
# ============================================

@router.post("/mock/enable")
async def enable_mock_mode(scenario: str = Query(default="random", description="Scenario: bullish, bearish, neutral, random")):
    """
    Enable mock Tavily mode for testing.
    
    This allows testing the full trading flow without Tavily API costs.
    The LLM will receive mock news data designed to lead to LONG/SHORT/HOLD decisions.
    
    Args:
        scenario: 'bullish' (leads to LONG), 'bearish' (leads to SHORT), 
                  'neutral' (leads to HOLD), 'random' (random each time)
    """
    from app.core.trading.mock_tavily import enable_mock_mode, set_scenario
    
    enable_mock_mode()
    set_scenario(scenario)
    
    return {
        "success": True,
        "mock_mode": True,
        "scenario": scenario,
        "message": f"Mock mode enabled with scenario: {scenario}",
        "expected_outcome": {
            "bullish": "AI will likely recommend LONG",
            "bearish": "AI will likely recommend SHORT",
            "neutral": "AI will likely recommend HOLD",
            "random": "Random scenario each analysis"
        }.get(scenario, "Unknown")
    }


@router.post("/mock/disable")
async def disable_mock_mode():
    """Disable mock mode and use real Tavily API"""
    from app.core.trading.mock_tavily import disable_mock_mode
    
    disable_mock_mode()
    
    return {
        "success": True,
        "mock_mode": False,
        "message": "Mock mode disabled, using real Tavily API"
    }


@router.get("/mock/status")
async def get_mock_status():
    """Get current mock mode status"""
    import os
    from app.core.trading.mock_tavily import is_mock_mode_enabled
    
    return {
        "mock_mode": is_mock_mode_enabled(),
        "scenario": os.getenv("MOCK_SCENARIO", "random"),
        "okx_trading": os.getenv("USE_OKX_TRADING", "false").lower() == "true"
    }


@router.post("/mock/test")
async def run_mock_test(scenario: str = Query(default="bullish", description="Test scenario")):
    """
    Run a complete mock test cycle.
    
    1. Enables mock mode with specified scenario
    2. Triggers analysis (LLM will use mock Tavily data)
    3. Returns the analysis result
    
    ⚠️ SAFETY: This endpoint BLOCKS execution if OKX trading is enabled.
    Mock tests only work with Paper Trader to prevent real money loss.
    """
    import os
    from app.core.trading.mock_tavily import enable_mock_mode, set_scenario
    
    # SAFETY CHECK: Block if OKX trading is enabled
    system = await get_trading_system()
    if system and system.trader_type == "okx":
        return {
            "success": False,
            "error": "⚠️ BLOCKED: Cannot run mock test while OKX trading is enabled!",
            "message": "Mock testing is only allowed with Paper Trader.",
            "action_required": "Set USE_OKX_TRADING=false in .env and restart the service",
            "current_trader": "okx"
        }
    
    if not system:
        return {"success": False, "error": "Trading system not initialized"}
    
    # Additional check - ensure we're not in OKX mode
    if os.getenv("USE_OKX_TRADING", "false").lower() == "true":
        return {
            "success": False,
            "error": "⚠️ BLOCKED: USE_OKX_TRADING is set to true in environment!",
            "message": "Cannot run mock test with OKX trading enabled.",
            "action_required": "Disable OKX trading first"
        }
    
    # Enable mock with scenario
    enable_mock_mode()
    set_scenario(scenario)
    
    try:
        # Trigger the analysis via scheduler
        if system.scheduler:
            await system.scheduler.trigger_now(reason=f"mock_test_{scenario}")
        else:
            return {"success": False, "error": "Scheduler not initialized"}
        
        return {
            "success": True,
            "scenario": scenario,
            "trader_type": system.trader_type,  # Should be "paper"
            "message": f"Mock test triggered with {scenario} scenario. Check WebSocket for signal.",
            "expected_behavior": {
                "bullish": "Should generate LONG signal with decision confirmation modal",
                "bearish": "Should generate SHORT signal with decision confirmation modal",
                "neutral": "Should generate HOLD signal (no modal)"
            }.get(scenario),
            "safety_note": "Using Paper Trader - no real money at risk"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/mock/test-tp-sl")
async def test_tp_sl_trigger(trigger_type: str = Query(default="tp", description="tp or sl")):
    """
    Test TP/SL trigger by simulating price movement.
    
    This endpoint manually sets the price to trigger TP or SL,
    verifying the position monitor works correctly.
    
    Args:
        trigger_type: 'tp' for take profit, 'sl' for stop loss
    """
    system = await get_trading_system()
    if not system or not system.paper_trader:
        return {"success": False, "error": "Trading system not initialized"}
    
    if system.trader_type == "okx":
        return {"success": False, "error": "Cannot test TP/SL with OKX - use Paper Trader"}
    
    position = await system.paper_trader.get_position()
    if not position or not position.get("has_position"):
        return {"success": False, "error": "No open position to test TP/SL"}
    
    direction = position.get("direction")
    entry_price = position.get("entry_price")
    tp_price = position.get("take_profit_price")
    sl_price = position.get("stop_loss_price")
    
    if trigger_type == "tp":
        if not tp_price:
            return {"success": False, "error": "No take profit price set"}
        # Set price to trigger TP
        if direction == "long":
            trigger_price = tp_price + 10  # Above TP for long
        else:
            trigger_price = tp_price - 10  # Below TP for short
        system.paper_trader.set_price(trigger_price)
    else:  # sl
        if not sl_price:
            return {"success": False, "error": "No stop loss price set"}
        # Set price to trigger SL
        if direction == "long":
            trigger_price = sl_price - 10  # Below SL for long
        else:
            trigger_price = sl_price + 10  # Above SL for short
        system.paper_trader.set_price(trigger_price)
    
    # Force check TP/SL immediately
    result = await system.paper_trader.check_tp_sl()
    
    # Get updated position
    new_position = await system.paper_trader.get_position()
    account = await system.paper_trader.get_account()
    
    return {
        "success": True,
        "trigger_type": trigger_type,
        "trigger_price": trigger_price,
        "original_position": {
            "direction": direction,
            "entry_price": entry_price,
            "tp_price": tp_price,
            "sl_price": sl_price
        },
        "result": result,
        "position_closed": not new_position.get("has_position"),
        "account_balance": account.get("balance"),
        "realized_pnl": account.get("realized_pnl")
    }


@router.post("/mock/test-cooldown")
async def test_cooldown(losses: int = Query(default=3, description="Number of consecutive losses to simulate")):
    """
    Test cooldown by simulating consecutive losses.
    
    After 3 consecutive losses (default), the system should enter cooldown
    and block new analysis cycles.
    """
    system = await get_trading_system()
    if not system:
        return {"success": False, "error": "Trading system not initialized"}
    
    # Simulate consecutive losses
    for i in range(losses):
        # Record a loss (-100 each)
        can_continue = system.cooldown_manager.record_trade_result(-100)
        logger.info(f"Recorded loss {i+1}/{losses}, can_continue={can_continue}")
    
    status = system.cooldown_manager.get_cooldown_status()
    
    return {
        "success": True,
        "simulated_losses": losses,
        "cooldown_status": status,
        "in_cooldown": status.get("in_cooldown"),
        "cooldown_until": status.get("cooldown_until"),
        "message": "Cooldown triggered!" if status.get("in_cooldown") else "Still trading"
    }


@router.post("/mock/reset-cooldown")
async def reset_cooldown():
    """Reset cooldown for testing purposes."""
    system = await get_trading_system()
    if not system:
        return {"success": False, "error": "Trading system not initialized"}
    
    system.cooldown_manager.force_end_cooldown()
    system.cooldown_manager._consecutive_losses = 0
    
    return {
        "success": True,
        "message": "Cooldown reset successfully",
        "cooldown_status": system.cooldown_manager.get_cooldown_status()
    }


@router.post("/mock/open-position")
async def open_test_position(
    direction: str = Query(default="long", description="long or short"),
    leverage: int = Query(default=3, description="Leverage 1-20"),
    amount_usdt: float = Query(default=1000, description="Amount in USDT")
):
    """
    Open a test position directly for TP/SL testing.
    This bypasses the full analysis cycle for quick testing.
    """
    system = await get_trading_system()
    if not system or not system.paper_trader:
        return {"success": False, "error": "Trading system not initialized"}
    
    if system.trader_type == "okx":
        return {"success": False, "error": "Cannot open test position with OKX - use Paper Trader"}
    
    # Check if already has position
    position = await system.paper_trader.get_position()
    if position and position.get("has_position"):
        return {"success": False, "error": "Already has open position. Close it first."}
    
    # Get current price for TP/SL calculation
    current_price = await system.paper_trader.get_current_price("BTC-USDT-SWAP")
    
    # Calculate TP/SL based on direction
    if direction == "long":
        tp_price = current_price * 1.05  # 5% profit
        sl_price = current_price * 0.98  # 2% loss
        result = await system.paper_trader.open_long(
            symbol="BTC-USDT-SWAP",
            leverage=leverage,
            amount_usdt=amount_usdt,
            tp_price=tp_price,
            sl_price=sl_price
        )
    else:
        tp_price = current_price * 0.95  # 5% profit (price goes down)
        sl_price = current_price * 1.02  # 2% loss (price goes up)
        result = await system.paper_trader.open_short(
            symbol="BTC-USDT-SWAP",
            leverage=leverage,
            amount_usdt=amount_usdt,
            tp_price=tp_price,
            sl_price=sl_price
        )
    
    # Get updated position
    new_position = await system.paper_trader.get_position()
    
    return {
        "success": True,
        "direction": direction,
        "leverage": leverage,
        "amount_usdt": amount_usdt,
        "entry_price": current_price,
        "take_profit_price": tp_price,
        "stop_loss_price": sl_price,
        "position": new_position,
        "message": f"Opened {direction} position for TP/SL testing"
    }

# ============================================
# User Decision Recording (RLHF Data Collection)
# ============================================

class UserDecision(BaseModel):
    """User decision on AI trading signal"""
    decision_id: str
    action: str  # "confirm", "modify", "defer"
    original_signal: Dict[str, Any]
    modified_leverage: Optional[int] = None
    defer_reason: Optional[str] = None
    timestamp: str


# In-memory storage for decisions (should be Redis in production)
_user_decisions: List[Dict[str, Any]] = []


@router.post("/decision")
async def record_user_decision(decision: UserDecision):
    """
    Record user's decision on AI trading signal.
    
    This data is valuable for RLHF training - each decision represents
    high-quality human feedback on AI trading recommendations.
    """
    decision_data = decision.model_dump()
    decision_data['recorded_at'] = datetime.now().isoformat()
    
    # Store decision
    _user_decisions.insert(0, decision_data)
    
    # Keep only last 1000 decisions in memory
    if len(_user_decisions) > 1000:
        _user_decisions.pop()
    
    logger.info(f"[RLHF] User decision recorded: {decision.action} for {decision.original_signal.get('direction', 'N/A')}")
    
    # Calculate statistics
    total = len(_user_decisions)
    confirms = len([d for d in _user_decisions if d['action'] == 'confirm'])
    defers = len([d for d in _user_decisions if d['action'] == 'defer'])
    modifies = len([d for d in _user_decisions if d['action'] == 'modify'])
    
    return {
        "success": True,
        "message": "Decision recorded for RLHF training",
        "statistics": {
            "total_decisions": total,
            "confirm_count": confirms,
            "defer_count": defers,
            "modify_count": modifies,
            "confirm_rate": round(confirms / total * 100, 1) if total > 0 else 0,
            "defer_rate": round(defers / total * 100, 1) if total > 0 else 0
        }
    }


@router.get("/decisions")
async def get_user_decisions(limit: int = Query(default=50, le=200)):
    """
    Get history of user decisions.
    
    This endpoint demonstrates the data collection capability to investors.
    """
    decisions = _user_decisions[:limit]
    
    # Calculate statistics
    total = len(_user_decisions)
    confirms = len([d for d in _user_decisions if d['action'] == 'confirm'])
    defers = len([d for d in _user_decisions if d['action'] == 'defer'])
    modifies = len([d for d in _user_decisions if d['action'] == 'modify'])
    
    # Analyze defer reasons
    defer_reasons = {}
    for d in _user_decisions:
        if d['action'] == 'defer' and d.get('defer_reason'):
            reason = d['defer_reason']
            defer_reasons[reason] = defer_reasons.get(reason, 0) + 1
    
    return {
        "decisions": decisions,
        "statistics": {
            "total_decisions": total,
            "confirm_count": confirms,
            "defer_count": defers,
            "modify_count": modifies,
            "confirm_rate": round(confirms / total * 100, 1) if total > 0 else 0,
            "defer_rate": round(defers / total * 100, 1) if total > 0 else 0,
            "defer_reasons": defer_reasons
        },
        "data_value": {
            "description": "每条决策记录代表高价值的金融推理标注数据 (RLHF)",
            "use_cases": [
                "微调模型提升胜率",
                "剔除导致亏损的幻觉推理",
                "训练垂直领域金融大模型"
            ]
        }
    }


@router.post("/execute")
async def execute_trade(request: Dict[str, Any]):
    """
    Execute a trade after user confirmation.
    
    This is called after user confirms or modifies the AI decision.
    """
    system = await get_trading_system()
    if not system or not system.paper_trader:
        return {"success": False, "error": "Trading system not initialized"}
    
    direction = request.get("direction", "long")
    leverage = request.get("leverage", 5)
    take_profit = request.get("take_profit")
    stop_loss = request.get("stop_loss")
    
    try:
        # Get account balance
        account = await system.paper_trader.get_account()
        available = account.get("available_balance", 0)
        amount_usdt = available * 0.3  # Use 30% of available balance
        
        if direction == "long":
            result = await system.paper_trader.open_long(
                symbol="BTC-USDT-SWAP",
                leverage=leverage,
                amount_usdt=amount_usdt,
                tp_price=take_profit,
                sl_price=stop_loss
            )
        else:
            result = await system.paper_trader.open_short(
                symbol="BTC-USDT-SWAP",
                leverage=leverage,
                amount_usdt=amount_usdt,
                tp_price=take_profit,
                sl_price=stop_loss
            )
        
        logger.info(f"[UserConfirm] Trade executed: {direction} {leverage}x, result={result.get('success')}")
        return result
        
    except Exception as e:
        logger.error(f"[UserConfirm] Trade execution failed: {e}")
        return {"success": False, "error": str(e)}
