"""
Trading System Service

Central trading system manager extracted from trading_routes.py.
Coordinates scheduler, position monitor, and trading meetings.
Supports both local PaperTrader and OKX Demo trading.
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from fastapi import APIRouter, WebSocket

from app.core.auth import get_current_user_id
from app.core.trading.paper_trader import PaperTrader, get_paper_trader
from app.core.trading.okx_trader import OKXTrader, get_okx_trader
from app.core.trading.trading_tools import TradingToolkit
from app.core.trading.trading_agents import create_trading_agents, get_trading_agent_config
from app.core.trading.trading_meeting import TradingMeeting, TradingMeetingConfig
from app.core.trading.agent_memory import get_memory_store
from app.core.trading.decision_store import get_decision_store
from app.core.trading.scheduler import TradingScheduler, CooldownManager
from app.core.trading.trigger import TriggerScheduler, TriggerAgent
from app.models.trading_models import TradingConfig, TradingSignal
from app.core.trading.okx_credentials_store import get_okx_credentials_store
from app.core.trading.trading_settings_store import get_trading_settings_store, TradingSettings
from app.services.web_search_access import search_web as shared_search_web
from app.core.service_endpoints import get_web_search_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trading", tags=["trading"])

# Global state
_trading_systems: Dict[str, "TradingSystem"] = {}
_trading_systems_lock = asyncio.Lock()


class TradingSystem:
    """
    Central trading system manager.

    Coordinates scheduler, position monitor, and trading meetings.
    Supports both local PaperTrader and OKX Demo trading.
    """

    def __init__(self, llm_service=None, user_id: Optional[str] = None):
        self.llm_service = llm_service
        self.user_id = get_current_user_id(user_id)
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
        self._settings: TradingSettings = TradingSettings()

    async def initialize(self):
        """Initialize the trading system"""
        if self._initialized:
            return

        # Load persisted settings (survive /api/trading/reset)
        try:
            self._settings = await get_trading_settings_store().get(self.user_id)
        except Exception:
            self._settings = TradingSettings()

        # Apply settings overrides onto config (env remains as defaults)
        if self._settings.analysis_interval_hours is not None:
            self.config.analysis_interval_hours = int(self._settings.analysis_interval_hours)
        if self._settings.max_leverage is not None:
            self.config.risk_limits.max_leverage = int(self._settings.max_leverage)
        if self._settings.max_position_percent is not None:
            self.config.risk_limits.max_position_percent = float(self._settings.max_position_percent)
        if self._settings.enabled is not None:
            self.config.enabled = bool(self._settings.enabled)
        if self._settings.okx_demo_mode is not None:
            self.config.demo_mode = bool(self._settings.okx_demo_mode)

        use_okx_requested = bool(self._settings.use_okx_trading)

        if use_okx_requested:
            creds = await get_okx_credentials_store().get(self.user_id)
            if creds and creds.is_configured():
                logger.info("Initializing trading system with OKX Demo Trading (user-configured credentials)...")
                self.trader_type = "okx"
                self.trader = await get_okx_trader(
                    initial_balance=self.config.initial_capital,
                    demo_mode=bool(creds.demo_mode),
                    okx_api_key=creds.api_key,
                    okx_secret_key=creds.secret_key,
                    okx_passphrase=creds.passphrase,
                    user_id=self.user_id,
                )
            else:
                logger.warning("OKX trading requested but credentials not configured. Falling back to PaperTrader.")
                self.trader_type = "paper"
                self.trader = await get_paper_trader(
                    initial_balance=self.config.initial_capital,
                    user_id=self.user_id,
                )
        else:
            logger.info("Initializing trading system with Paper Trader...")
            self.trader_type = "paper"
            self.trader = await get_paper_trader(
                initial_balance=self.config.initial_capital,
                user_id=self.user_id,
            )

        # Set alias for compatibility
        self.paper_trader = self.trader

        # Set callbacks
        self.trader.on_position_closed = self._on_position_closed
        self.trader.on_tp_hit = self._on_tp_hit
        self.trader.on_sl_hit = self._on_sl_hit

        # Initialize toolkit with trader
        self.toolkit = TradingToolkit(paper_trader=self.trader, user_id=self.user_id)

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
        logger.info(f"Trading system initialized with {self.trader_type} trader for user={self.user_id}")

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

                # HITL-only: always broadcast as semi_auto.
                from app.core.trading.mode_manager import get_mode_manager
                mode_manager = get_mode_manager(self.user_id)

                await self._broadcast({
                    "type": "signal_generated",
                    "signal": signal.model_dump(),
                    "mode": "semi_auto",
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
                    # HITL-only: always create a pending trade for confirmation.
                    logger.info(f"[HITL] Creating pending trade for confirmation: {signal.direction}")
                    pending_trade = await mode_manager.add_pending_trade(
                        direction=signal.direction,
                        leverage=signal.leverage,
                        entry_price=signal.entry_price,
                        take_profit=signal.take_profit_price,
                        stop_loss=signal.stop_loss_price,
                        confidence=signal.confidence,
                        reasoning=signal.reasoning,
                        amount_percent=signal.amount_percent,
                    )

                    self._trade_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "signal": signal.model_dump(),
                        "status": "pending_confirmation",
                        "trade_id": pending_trade.trade_id,
                        "trade_result": {"action": "pending", "message": "等待用户确认"},
                    })

                    await self._broadcast({
                        "type": "pending_trade_created",
                        "signal": signal.model_dump(),
                        "trade_id": pending_trade.trade_id,
                        "mode": "semi_auto",
                        "message": "请确认或拒绝此交易",
                    })
                    logger.info(f"[HITL] Pending trade created: {pending_trade.trade_id}")
                    return
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
        can_continue = self.cooldown_manager.record_trade_result(pnl)

        # Do not block trade close on reflection/LLM calls; run heavy work asynchronously.
        asyncio.create_task(self._post_close_processing(position, pnl, can_continue, reason))

        # Immediate broadcast for UI responsiveness.
        await self._broadcast({
            "type": "position_closed",
            "pnl": pnl,
            "can_continue": can_continue,
            "reason": reason,
            "lessons": {},  # Populated later via position_closed_lessons/reflection events.
        })

    async def _post_close_processing(self, position, pnl: float, can_continue: bool, reason: str = None):
        """Best-effort post-close processing: reflection, memory update, and optional next trigger."""
        lessons: Dict[str, str] = {}

        try:
            lessons = await self._run_reflection_meeting(position, pnl)
        except Exception as e:
            logger.warning(f"Reflection meeting failed: {e}")
            lessons = {}

        try:
            # Update agent memory with lessons learned
            memory_store = await get_memory_store(self.user_id)
            trade_id = str(uuid.uuid4())

            # Use correct PascalCase agent IDs
            trading_agents = ["TechnicalAnalyst", "MacroEconomist", "SentimentAnalyst", "QuantStrategist", "RiskAssessor"]
            direction = getattr(position, "direction", None) or (position.get("direction") if isinstance(position, dict) else None)

            for agent_id in trading_agents:
                lesson = lessons.get(agent_id, f"交易结果: {'盈利' if pnl > 0 else '亏损'} ${abs(pnl):.2f}")
                await memory_store.record_trade_result(
                    agent_id=agent_id,
                    agent_name=agent_id,
                    trade_id=trade_id,
                    prediction={"direction": direction},
                    actual_outcome={"pnl": pnl},
                    pnl=pnl,
                    lesson=lesson,
                )

            await self._broadcast({
                "type": "position_closed_lessons",
                "pnl": pnl,
                "reason": reason,
                "lessons": lessons,
            })
        except Exception as e:
            logger.warning(f"Post-close memory update failed: {e}")

        if can_continue:
            try:
                await self.scheduler.trigger_now(reason="position_closed")
            except Exception as e:
                logger.warning(f"Post-close trigger_now failed: {e}")

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

        # Build reflection context (PaperPosition doesn't expose current_price, so compute exit price defensively)
        direction = getattr(position, "direction", None) or (position.get("direction") if isinstance(position, dict) else "unknown")
        entry_price = getattr(position, "entry_price", None) or (position.get("entry_price") if isinstance(position, dict) else None) or 0.0
        leverage = getattr(position, "leverage", None) or (position.get("leverage") if isinstance(position, dict) else None) or 1

        exit_price = getattr(position, "current_price", None) or getattr(position, "exit_price", None)
        if exit_price is None and isinstance(position, dict):
            exit_price = position.get("current_price") or position.get("exit_price")

        if exit_price is None:
            size = getattr(position, "size", None) or (position.get("size") if isinstance(position, dict) else None)
            try:
                size = float(size) if size not in (None, 0) else None
            except Exception:
                size = None
            try:
                entry_f = float(entry_price) if entry_price is not None else 0.0
            except Exception:
                entry_f = 0.0

            if size and direction in ("long", "short"):
                # pnl = (exit-entry)*size for long, pnl = (entry-exit)*size for short
                exit_price = entry_f + (pnl / size) if direction == "long" else entry_f - (pnl / size)
            else:
                exit_price = float(entry_price or 0.0)

        reflection_context = f"""## Trade Reflection Meeting

### Trade Result
- **Outcome**: {outcome_type}
- **Direction**: {direction}
- **Entry Price**: {float(entry_price):.2f}
- **Exit Price**: {float(exit_price):.2f}
- **PnL**: ${pnl:.2f}
- **Leverage**: {leverage}x

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
        
        web_search_url = get_web_search_url()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try health endpoint first; a degraded status should not be treated as healthy.
                try:
                    response = await client.get(f"{web_search_url}/health")
                    if response.status_code == 200:
                        payload = response.json() if response.content else {}
                        status = str(payload.get("status", "")).lower()
                        if status in {"ok", "healthy"}:
                            logger.info("✅ Tavily/MCP search service is healthy")
                            return True
                        logger.warning(f"Search health endpoint reported non-healthy status: {status or 'unknown'}")
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"Failed to call search health endpoint: {e}")

        # Fallback: execute one real search through the shared access layer.
        try:
            results = await shared_search_web(
                web_search_url,
                query="bitcoin price",
                max_results=1,
                timeout=15.0,
            )
            if results:
                logger.info("✅ Tavily/MCP search service operational (search test passed)")
                return True
        except Exception as e:
            logger.warning(f"Tavily search test failed: {e}")

        logger.error("❌ Tavily/MCP search service is unavailable")
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
                # Use default=str to handle datetime objects
                await ws.send_text(json.dumps(message, default=str))
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


async def get_trading_system(llm_service=None, user_id: Optional[str] = None) -> TradingSystem:
    """Get or create trading system singleton scoped by user."""
    scope = get_current_user_id(user_id)
    system = _trading_systems.get(scope)
    if system is not None:
        return system

    async with _trading_systems_lock:
        system = _trading_systems.get(scope)
        if system is None:
            system = TradingSystem(llm_service=llm_service, user_id=scope)
            await system.initialize()
            _trading_systems[scope] = system
    return system
