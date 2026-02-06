"""
Trading Logger - Redis-based logging for trading decisions and position events.

Provides persistent logging for debugging trading system behavior:
- Decision logs: Expert votes, consensus results, final signals
- Position logs: Open/close events with full context
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TradingLogger:
    """
    Redis-based trading logger for debugging and audit trail.
    
    Key Structure:
    - trading:decisions:latest - Last 100 decision records (LIST)
    - trading:positions:latest - Last 100 position events (LIST)
    """
    
    MAX_ENTRIES = 100  # Keep last 100 entries
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize Redis connection."""
        if self._initialized:
            return
            
        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("[TradingLogger] Connected to Redis")
            self._initialized = True
        except Exception as e:
            logger.warning(f"[TradingLogger] Redis not available: {e}")
            self._redis = None
    
    async def _ensure_connected(self):
        """Ensure Redis connection is established."""
        if not self._initialized:
            await self.initialize()
        return self._redis is not None
    
    async def log_decision(
        self,
        trigger_reason: str,
        symbol: str,
        market_price: float,
        votes: Dict[str, Dict[str, Any]],
        vote_summary: Dict[str, int],
        final_decision: Dict[str, Any],
        position_context: Optional[Dict[str, Any]] = None,
        leader_summary: str = ""
    ):
        """
        Log a trading decision to Redis.
        
        Args:
            trigger_reason: Why analysis was triggered (startup, scheduled, manual, etc.)
            symbol: Trading pair (e.g., BTC-USDT-SWAP)
            market_price: Current market price
            votes: Expert votes {agent_name: {direction, confidence, leverage}}
            vote_summary: Vote counts {long: N, short: N, hold: N}
            final_decision: Final decision {direction, confidence, leverage, reasoning}
            position_context: Current position info if any
            leader_summary: Leader's meeting summary
        """
        if not await self._ensure_connected():
            return
            
        try:
            timestamp = datetime.now()
            decision_id = f"decision_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            entry = {
                "id": decision_id,
                "timestamp": timestamp.isoformat(),
                "trigger_reason": trigger_reason,
                "symbol": symbol,
                "market_price": market_price,
                "votes": votes,
                "vote_summary": vote_summary,
                "final_decision": final_decision,
                "position_context": position_context or {},
                "leader_summary": leader_summary[:500] if leader_summary else ""  # Truncate for storage
            }
            
            # Add to list (newest first)
            await self._redis.lpush("trading:decisions:latest", json.dumps(entry))
            
            # Trim to MAX_ENTRIES
            await self._redis.ltrim("trading:decisions:latest", 0, self.MAX_ENTRIES - 1)
            
            logger.info(f"[TradingLogger] Decision logged: {decision_id} - {final_decision.get('direction', 'unknown')}")
            
        except Exception as e:
            logger.error(f"[TradingLogger] Failed to log decision: {e}")
    
    async def log_position_event(
        self,
        event_type: str,  # "open", "close", "add", "tp_hit", "sl_hit"
        symbol: str,
        direction: str,
        size: float,
        entry_price: float,
        leverage: int,
        margin: float,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        exit_price: Optional[float] = None,
        pnl: Optional[float] = None,
        close_reason: Optional[str] = None,
        duration_hours: Optional[float] = None,
        trigger_decision_id: Optional[str] = None,
        account_balance: Optional[float] = None
    ):
        """
        Log a position event (open/close/add) to Redis.
        
        Args:
            event_type: Type of event
            symbol: Trading pair
            direction: Position direction (long/short)
            size: Position size
            entry_price: Entry price
            leverage: Leverage used
            margin: Margin amount
            take_profit: TP price (for open events)
            stop_loss: SL price (for open events)
            exit_price: Exit price (for close events)
            pnl: Realized PnL (for close events)
            close_reason: Reason for closing (for close events)
            duration_hours: How long position was held (for close events)
            trigger_decision_id: ID of the decision that triggered this
            account_balance: Current account balance
        """
        if not await self._ensure_connected():
            return
            
        try:
            timestamp = datetime.now()
            event_id = f"pos_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}"
            
            entry = {
                "id": event_id,
                "timestamp": timestamp.isoformat(),
                "event_type": event_type,
                "symbol": symbol,
                "direction": direction,
                "size": size,
                "entry_price": entry_price,
                "leverage": leverage,
                "margin": margin,
                "take_profit": take_profit,
                "stop_loss": stop_loss,
                "exit_price": exit_price,
                "pnl": pnl,
                "close_reason": close_reason,
                "duration_hours": duration_hours,
                "trigger_decision_id": trigger_decision_id,
                "account_balance": account_balance
            }
            
            # Add to list (newest first)
            await self._redis.lpush("trading:positions:latest", json.dumps(entry))
            
            # Trim to MAX_ENTRIES
            await self._redis.ltrim("trading:positions:latest", 0, self.MAX_ENTRIES - 1)
            
            # Log summary
            if event_type == "close":
                pnl_str = f"PnL: ${pnl:.2f}" if pnl is not None else ""
                logger.info(f"[TradingLogger] Position closed: {event_id} - {direction} @ ${exit_price:.2f} {pnl_str}")
            else:
                logger.info(f"[TradingLogger] Position {event_type}: {event_id} - {direction} @ ${entry_price:.2f}")
            
        except Exception as e:
            logger.error(f"[TradingLogger] Failed to log position event: {e}")
    
    async def get_recent_decisions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent decision logs."""
        if not await self._ensure_connected():
            return []
            
        try:
            entries = await self._redis.lrange("trading:decisions:latest", 0, limit - 1)
            return [json.loads(e) for e in entries]
        except Exception as e:
            logger.error(f"[TradingLogger] Failed to get decisions: {e}")
            return []
    
    async def get_recent_positions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent position event logs."""
        if not await self._ensure_connected():
            return []
            
        try:
            entries = await self._redis.lrange("trading:positions:latest", 0, limit - 1)
            return [json.loads(e) for e in entries]
        except Exception as e:
            logger.error(f"[TradingLogger] Failed to get positions: {e}")
            return []


# Singleton instance
_trading_logger: Optional[TradingLogger] = None


async def get_trading_logger(redis_url: str = "redis://redis:6379") -> TradingLogger:
    """Get or create the singleton TradingLogger instance."""
    global _trading_logger
    
    if _trading_logger is None:
        _trading_logger = TradingLogger(redis_url)
        await _trading_logger.initialize()
    
    return _trading_logger
