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
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel

from app.core.trading.paper_trader import PaperTrader, get_paper_trader
from app.core.trading.okx_trader import OKXTrader, get_okx_trader
from app.core.trading.trading_tools import TradingToolkit
from app.core.trading.trading_agents import create_trading_agents, get_trading_agent_config
from app.core.trading.trading_meeting import TradingMeeting, TradingMeetingConfig
from app.core.trading.agent_memory import get_memory_store
from app.core.trading.scheduler import TradingScheduler, CooldownManager
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
        self.cooldown_manager = CooldownManager()

        self._ws_clients: Dict[str, WebSocket] = {}
        self._current_meeting: Optional[TradingMeeting] = None
        self._trade_history: List[Dict] = []
        self._discussion_messages: List[Dict] = []  # Store discussion messages for persistence
        self._monitor_task: Optional[asyncio.Task] = None
        self._initialized = False

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

        self._initialized = True
        logger.info(f"Trading system initialized with {self.trader_type} trader")

    async def start(self):
        """Start the trading system"""
        if not self._initialized:
            await self.initialize()

        if not self.config.enabled:
            logger.warning("Trading system is disabled")
            return

        logger.info("Starting trading system...")
        await self.scheduler.start()

        # Start position monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        await self._broadcast({
            "type": "system_started",
            "timestamp": datetime.now().isoformat()
        })

    async def stop(self):
        """Stop the trading system"""
        logger.info("Stopping trading system...")

        if self.scheduler:
            await self.scheduler.stop()

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
                        await self.scheduler.trigger_now(reason=f"{trigger}_triggered")

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

    async def _on_analysis_cycle(self, cycle_number: int, reason: str, timestamp: datetime):
        """Handle analysis cycle"""
        logger.info(f"Starting analysis cycle #{cycle_number}, reason: {reason}")

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
            signal = await self._run_trading_meeting(reason)

            if signal:
                await self._broadcast({
                    "type": "signal_generated",
                    "signal": signal.model_dump()
                })

                # Execute trade if not hold
                if signal.direction != "hold":
                    trade_result = await self._execute_signal(signal)
                    self._trade_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "signal": signal.model_dump(),
                        "status": "executed" if trade_result.get("success") else "failed",
                        "trade_result": trade_result
                    })

                    # Broadcast trade executed event so frontend can refresh data
                    await self._broadcast({
                        "type": "trade_executed",
                        "signal": signal.model_dump(),
                        "success": trade_result.get("success", False),
                        "trade_result": trade_result
                    })

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
                # Close existing position first if direction changed
                existing_direction = position.get("direction")
                if existing_direction and existing_direction != signal.direction:
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
            on_message=self._on_meeting_message
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
        asyncio.create_task(self._broadcast({
            "type": "scheduler_state",
            "old_state": old_state.value,
            "new_state": new_state.value
        }))

    async def _on_position_closed(self, position, pnl: float):
        """Handle position closed"""
        logger.info(f"Position closed with PnL: {pnl}")

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

        outcome_type = "止盈" if pnl > 0 else "止损"
        lessons = {}

        # Build reflection context
        reflection_context = f"""## 交易反思会议

### 交易结果
- **结果**: {outcome_type}
- **方向**: {position.direction}
- **入场价**: {position.entry_price:.2f}
- **出场价**: {position.current_price:.2f}
- **盈亏**: ${pnl:.2f}
- **杠杆**: {position.leverage}x

### 请回答以下问题（50字以内）:
1. 你当时的判断依据是什么？
2. 判断{'正确' if pnl > 0 else '错误'}的原因是什么？
3. 从这笔交易中学到什么？
"""

        # Create agents with toolkit
        agents = create_trading_agents(toolkit=self.toolkit)

        await self._broadcast({
            "type": "reflection_started",
            "pnl": pnl,
            "outcome": outcome_type
        })

        # Have each agent reflect
        for agent in agents.values():
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
                lesson = content[:200] if content else f"需要进一步分析{outcome_type}原因"
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
                lessons[agent.id] = f"反思过程出错: {str(e)[:50]}"

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

    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        # Determine actual running state based on scheduler state
        # enabled should reflect if the system is actually running, not just configured
        is_running = False
        if self.scheduler:
            scheduler_state = self.scheduler.state.value
            # Consider running if scheduler is in RUNNING, ANALYZING, or EXECUTING state
            is_running = scheduler_state in ["running", "analyzing", "executing"]

        trader_status = self.paper_trader.get_status() if self.paper_trader else None

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
    return system.get_status()


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

    # Get actual closed trades from paper trader
    actual_trades = []
    if system.paper_trader:
        actual_trades = await system.paper_trader.get_trade_history(limit)

    return {
        "trades": actual_trades,  # Actual closed trades with real PnL
        "signals": system._trade_history[-limit:]  # Signal history for reference
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
        "status": system.get_status()
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
