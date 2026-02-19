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
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from app.core.auth import get_current_user, resolve_user_from_token, get_current_user_id

from app.core.trading.paper_trader import PaperTrader
from app.core.trading.okx_trader import OKXTrader
from app.core.trading.trading_agents import get_trading_agent_config
from app.core.trading.agent_memory import get_memory_store
from app.core.trading.decision_store import get_decision_store  # Redis persistence for signals
from app.core.trading.okx_credentials_store import get_okx_credentials_store, OkxCredentials
from app.core.trading.trading_settings_store import get_trading_settings_store, TradingSettings
from app.core.trading.scheduler import CooldownManager
from app.models.trading_models import TradingConfig, TradingSignal

logger = logging.getLogger(__name__)

# Import TradingSystem from new service module
from app.services.trading_system import TradingSystem, get_trading_system

router = APIRouter(prefix="/api/trading", tags=["trading"])
AUTH_DEPENDENCIES = [Depends(get_current_user)]


async def _get_system():
    return await get_trading_system(user_id=get_current_user_id())


# ===== REST API Endpoints =====

@router.get("/status", dependencies=AUTH_DEPENDENCIES)
async def get_status():
    """Get trading system status"""
    system = await _get_system()
    return await system.get_status()


@router.get("/funding", dependencies=AUTH_DEPENDENCIES)
async def get_funding_rate():
    """Get current funding rate and cost analysis"""
    try:
        from app.core.trading.funding import (
            get_funding_data_service,
            get_funding_calculator,
            get_funding_config
        )
        scope = get_current_user_id()
        
        # Get funding rate data
        data_service = await get_funding_data_service(scope)
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


@router.get("/account", dependencies=AUTH_DEPENDENCIES)
async def get_account():
    """Get account information"""
    system = await _get_system()
    if system.paper_trader:
        account = await system.paper_trader.get_account()
        return account
    return {"error": "Paper trader not initialized"}


@router.get("/position", dependencies=AUTH_DEPENDENCIES)
async def get_position(symbol: str = "BTC-USDT-SWAP"):
    """Get current position"""
    system = await _get_system()
    if system.paper_trader:
        position = await system.paper_trader.get_position()
        if position:
            return position
        return {"has_position": False}
    return {"error": "Paper trader not initialized"}


@router.get("/history", dependencies=AUTH_DEPENDENCIES)
async def get_trade_history(limit: int = Query(default=50, le=100)):
    """Get trade history including signals and actual closed trades"""
    system = await _get_system()

    # 🔧 CRITICAL FIX: Always use async get_trade_history() for REAL OKX data
    # The old get_filtered_trade_history() returned local estimates without fees
    actual_trades = []
    if system.paper_trader:
        # Call the async method that fetches from OKX API
        actual_trades = await system.paper_trader.get_trade_history(limit)

    # 🆕 Get signals from Redis for persistence across restarts
    signals = []
    try:
        decision_store = await get_decision_store(user_id=get_current_user_id())
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


@router.get("/messages", dependencies=AUTH_DEPENDENCIES)
async def get_discussion_messages(limit: int = Query(default=100, le=200)):
    """Get discussion messages history for state restoration"""
    system = await _get_system()
    return {"messages": system._discussion_messages[-limit:]}

# NOTE: SEMI_AUTO pending trade endpoints have been consolidated into
# app/api/routers/trading_mode.py to avoid route conflicts.
# Endpoints: GET /pending, POST /confirm/{trade_id}, POST /reject/{trade_id}


@router.get("/equity", dependencies=AUTH_DEPENDENCIES)
async def get_equity_history(limit: int = Query(default=100, le=500)):
    """Get equity history for charting"""
    system = await _get_system()
    if system.paper_trader:
        return {"data": await system.paper_trader.get_equity_history(limit)}
    return {"data": []}


@router.get("/drawdown", dependencies=AUTH_DEPENDENCIES)
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
    system = await _get_system()
    
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
                except (ValueError, TypeError):
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


@router.get("/performance", dependencies=AUTH_DEPENDENCIES)
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
    system = await _get_system()
    
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


@router.post("/start", dependencies=AUTH_DEPENDENCIES)
async def start_trading():
    """Start auto trading"""
    system = await _get_system()
    await system.start()
    return {"status": "started", "message": "Trading system started"}


@router.post("/stop", dependencies=AUTH_DEPENDENCIES)
async def stop_trading():
    """Stop auto trading"""
    system = await _get_system()
    await system.stop()
    return {"status": "stopped", "message": "Trading system stopped"}


@router.post("/trigger", dependencies=AUTH_DEPENDENCIES)
async def manual_trigger(reason: str = "manual"):
    """Manually trigger analysis cycle"""
    system = await _get_system()
    if system.scheduler:
        success = await system.scheduler.trigger_now(reason=reason)
        return {"triggered": success}
    return {"error": "Scheduler not initialized"}


@router.post("/close", dependencies=AUTH_DEPENDENCIES)
async def close_position():
    """Manually close current position"""
    system = await _get_system()
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


@router.post("/reset-metrics", dependencies=AUTH_DEPENDENCIES)
async def reset_metrics_baseline():
    """
    Reset metrics baseline - all performance metrics will be calculated from this point.
    
    Use this when:
    1. Trade history is corrupted/polluted by bugs
    2. Starting fresh evaluation after system issues
    3. Beginning a new performance tracking period
    
    Returns the new baseline timestamp.
    """
    system = await _get_system()
    if not system.paper_trader:
        return {"error": "Trader not initialized"}

    try:
        result = await system.paper_trader.reset_metrics_baseline()
        logger.info(f"[API] Metrics baseline reset: {result}")
        return result
    except Exception as e:
        logger.error(f"Error resetting metrics baseline: {e}")
        return {"error": str(e)}


@router.get("/agents", dependencies=AUTH_DEPENDENCIES)
async def get_agents():
    """Get trading agent configuration"""
    return {"agents": get_trading_agent_config()}


@router.get("/agents/memory", dependencies=AUTH_DEPENDENCIES)
async def get_agent_memories():
    """Get agent memories and performance stats"""
    memory_store = await get_memory_store(get_current_user_id())
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
    okx_demo_mode: Optional[bool] = None
    okx_api_key: Optional[str] = None
    okx_secret_key: Optional[str] = None
    okx_passphrase: Optional[str] = None
    clear_okx_credentials: Optional[bool] = None


@router.get("/config", dependencies=AUTH_DEPENDENCIES)
async def get_config():
    """Get current trading configuration"""
    scope = get_current_user_id()
    system = await _get_system()
    okx_masked = await get_okx_credentials_store().get_masked(scope)
    persisted = await get_trading_settings_store().get(scope)
    return {
        "analysis_interval_hours": system.config.analysis_interval_hours,
        "max_leverage": system.config.risk_limits.max_leverage,
        "max_position_percent": system.config.risk_limits.max_position_percent,
        "enabled": system.config.enabled,
        "trader_type": system.trader_type,  # "paper" or "okx"
        "use_okx_trading": bool(persisted.use_okx_trading),
        "okx": okx_masked,
        "symbol": system.config.symbol,
        "initial_capital": system.config.initial_capital,
        "risk_limits": {
            "max_daily_loss_percent": system.config.risk_limits.max_daily_loss_percent,
            "consecutive_loss_limit": system.config.risk_limits.consecutive_loss_limit,
            "min_confidence": system.config.risk_limits.min_confidence
        }
    }


@router.patch("/config", dependencies=AUTH_DEPENDENCIES)
async def update_config(update: TradingConfigUpdate):
    """Update trading configuration"""
    scope = get_current_user_id()
    system = await _get_system()
    needs_reset = False

    # OKX creds update/clear
    if update.clear_okx_credentials:
        await get_okx_credentials_store().clear(scope)
        try:
            from app.core.trading.funding.data_service import get_funding_data_service
            await get_funding_data_service(scope)
        except Exception:
            pass
        # Safer default: revert to paper.
        update.use_okx_trading = False

    okx_key_fields_present = any(
        v is not None for v in (update.okx_api_key, update.okx_secret_key, update.okx_passphrase)
    )

    # OKX credentials: allow updating demo_mode without re-entering keys (if already stored).
    if okx_key_fields_present:
        # Partial updates not supported to avoid accidentally mixing old/new secrets.
        if not (update.okx_api_key and update.okx_secret_key and update.okx_passphrase):
            raise HTTPException(status_code=400, detail="OKX credentials require api_key, secret_key, and passphrase")
        await get_okx_credentials_store().set(
            OkxCredentials(
                api_key=update.okx_api_key,
                secret_key=update.okx_secret_key,
                passphrase=update.okx_passphrase,
                demo_mode=True if update.okx_demo_mode is None else bool(update.okx_demo_mode),
            ),
            scope,
        )
        needs_reset = True
    elif update.okx_demo_mode is not None:
        existing = await get_okx_credentials_store().get(scope)
        if existing and existing.is_configured():
            await get_okx_credentials_store().set(
                OkxCredentials(
                    api_key=existing.api_key,
                    secret_key=existing.secret_key,
                    passphrase=existing.passphrase,
                    demo_mode=bool(update.okx_demo_mode),
                ),
                scope,
            )
            needs_reset = True
        else:
            # No stored credentials yet. Only error if user is trying to enable OKX without creds.
            if update.use_okx_trading:
                raise HTTPException(status_code=400, detail="OKX demo mode provided but credentials are not configured")

    # Keep funding service in sync (uses OKX keys for authenticated bills endpoints).
    if okx_key_fields_present or update.okx_demo_mode is not None or update.clear_okx_credentials:
        try:
            from app.core.trading.funding.data_service import get_funding_data_service
            await get_funding_data_service(scope)
        except Exception:
            pass

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

    # Persist settings across reset
    persisted = await get_trading_settings_store().update(
        TradingSettings(
            analysis_interval_hours=update.analysis_interval_hours,
            max_leverage=update.max_leverage,
            max_position_percent=update.max_position_percent,
            enabled=update.enabled,
            use_okx_trading=update.use_okx_trading,
            okx_demo_mode=update.okx_demo_mode,
        ),
        scope,
    )

    # Handle OKX trading switch (requires reset)
    if update.use_okx_trading is not None:
        desired_okx = bool(update.use_okx_trading)
        current_is_okx = system.trader_type == "okx"
        if desired_okx != current_is_okx:
            needs_reset = True
            if desired_okx:
                okx = await get_okx_credentials_store().get(scope)
                if not okx or not okx.is_configured():
                    raise HTTPException(status_code=400, detail="OKX trading requested but credentials are not configured")
            logger.info(f"Trader type will switch after reset: {'OKX Demo' if desired_okx else 'Paper Trader'}")

    response = {
        "status": "updated",
        "config": system.config.model_dump(),
        "trader_type": system.trader_type,
        "needs_reset": needs_reset,
        "persisted": persisted.to_dict(),
        "okx": await get_okx_credentials_store().get_masked(scope),
    }

    if needs_reset:
        response["message"] = "Settings saved. Please reset the trading system to apply OKX/Paper switch."

    return response


@router.post("/cooldown/end", dependencies=AUTH_DEPENDENCIES)
async def end_cooldown():
    """Force end cooldown period"""
    system = await _get_system()
    system.cooldown_manager.force_end_cooldown()
    return {"status": "cooldown_ended"}


@router.post("/reset-daily-pnl", dependencies=AUTH_DEPENDENCIES)
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
    system = await _get_system()
    
    if not system.trader:
        return {"success": False, "error": "Trading system not initialized"}
    
    # OKXTrader has reset_daily_pnl method
    if hasattr(system.trader, 'reset_daily_pnl'):
        result = await system.trader.reset_daily_pnl()
        return result
    else:
        return {"success": False, "error": "Trader does not support daily PnL reset"}


@router.post("/reset", dependencies=AUTH_DEPENDENCIES)
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
    import app.services.trading_system as ts_module
    scope = get_current_user_id()

    logger.info("Resetting trading system...")

    try:
        _trading_system = ts_module._trading_systems.get(scope)
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
        memory_store = await get_memory_store(scope)
        await memory_store.clear_all_memories()

        # Reset user-scoped singleton to force re-initialization
        ts_module._trading_systems.pop(scope, None)

        # Re-initialize
        system = await get_trading_system(user_id=scope)

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

async def _resolve_websocket_user(websocket: WebSocket):
    authorization = (websocket.headers.get("authorization") or "").strip()
    token = ""
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()

    if not token:
        token = (websocket.query_params.get("token") or "").strip()

    if not token:
        return None

    try:
        return await resolve_user_from_token(token)
    except HTTPException:
        return None


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
    current_user = await _resolve_websocket_user(websocket)
    if not current_user:
        await websocket.close(code=4401, reason="Not authenticated")
        return

    await websocket.accept()
    client_id = f"{current_user.id}:{session_id}"
    logger.info(f"Trading WebSocket connected: {client_id}")

    system = await get_trading_system(user_id=current_user.id)
    system.register_ws_client(client_id, websocket)

    # Send initial status
    await websocket.send_json({
        "type": "connected",
        "status": await system.get_status()
    })

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            logger.debug(f"Received from {client_id}: {data}")

            # Handle commands
            import json
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception:
                pass

    except WebSocketDisconnect:
        logger.info(f"Trading WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Trading WebSocket error: {e}")
    finally:
        system.unregister_ws_client(client_id)


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

@router.get("/dashboard", dependencies=AUTH_DEPENDENCIES, response_class=HTMLResponse)
async def trading_dashboard():
    """Mobile-friendly trading status dashboard"""
    return MOBILE_STATUS_HTML


# ============================================
# Mock Testing APIs
# ============================================

def _require_test_endpoints_enabled():
    # Hide these endpoints by default for PoC/hosted environments.
    if os.getenv("ENABLE_TEST_ENDPOINTS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/mock/enable", dependencies=AUTH_DEPENDENCIES)
async def enable_mock_mode(scenario: str = Query(default="random", description="Scenario: bullish, bearish, neutral, random")):
    """
    Enable mock Tavily mode for testing.
    
    This allows testing the full trading flow without Tavily API costs.
    The LLM will receive mock news data designed to lead to LONG/SHORT/HOLD decisions.
    
    Args:
        scenario: 'bullish' (leads to LONG), 'bearish' (leads to SHORT), 
                  'neutral' (leads to HOLD), 'random' (random each time)
    """
    _require_test_endpoints_enabled()
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


@router.post("/mock/disable", dependencies=AUTH_DEPENDENCIES)
async def disable_mock_mode():
    """Disable mock mode and use real Tavily API"""
    _require_test_endpoints_enabled()
    from app.core.trading.mock_tavily import disable_mock_mode
    
    disable_mock_mode()
    
    return {
        "success": True,
        "mock_mode": False,
        "message": "Mock mode disabled, using real Tavily API"
    }


@router.get("/mock/status", dependencies=AUTH_DEPENDENCIES)
async def get_mock_status():
    """Get current mock mode status"""
    _require_test_endpoints_enabled()
    from app.core.trading.mock_tavily import is_mock_mode_enabled
    from app.core.trading.trading_settings_store import get_trading_settings_store
    
    persisted = await get_trading_settings_store().get(get_current_user_id())
    return {
        "mock_mode": is_mock_mode_enabled(),
        "scenario": os.getenv("MOCK_SCENARIO", "random"),
        "okx_trading": bool(persisted.use_okx_trading)
    }


@router.post("/mock/test", dependencies=AUTH_DEPENDENCIES)
async def run_mock_test(scenario: str = Query(default="bullish", description="Test scenario")):
    """
    Run a complete mock test cycle.
    
    1. Enables mock mode with specified scenario
    2. Triggers analysis (LLM will use mock Tavily data)
    3. Returns the analysis result
    
    ⚠️ SAFETY: This endpoint BLOCKS execution if OKX trading is enabled.
    Mock tests only work with Paper Trader to prevent real money loss.
    """
    _require_test_endpoints_enabled()
    from app.core.trading.mock_tavily import enable_mock_mode, set_scenario
    from app.core.trading.trading_settings_store import get_trading_settings_store
    
    # SAFETY CHECK: Block if OKX trading is enabled
    system = await _get_system()
    if system and system.trader_type == "okx":
        return {
            "success": False,
            "error": "⚠️ BLOCKED: Cannot run mock test while OKX trading is enabled!",
            "message": "Mock testing is only allowed with Paper Trader.",
            "action_required": "Disable OKX trading in Trading Settings and reset the system.",
            "current_trader": "okx"
        }
    
    if not system:
        return {"success": False, "error": "Trading system not initialized"}
    
    # Additional check - ensure persisted settings do not request OKX
    persisted = await get_trading_settings_store().get(get_current_user_id())
    if persisted.use_okx_trading:
        return {
            "success": False,
            "error": "⚠️ BLOCKED: OKX trading is enabled in settings!",
            "message": "Cannot run mock test with OKX trading enabled.",
            "action_required": "Disable OKX trading in Trading Settings and reset the system."
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


@router.post("/mock/create-pending", dependencies=AUTH_DEPENDENCIES)
async def create_mock_pending_trade(
    direction: str = Query(default="long", description="long or short"),
    leverage: int = Query(default=3, ge=1, le=50, description="Leverage 1-50"),
    amount_percent: float = Query(default=0.2, gt=0, le=1.0, description="Position size as percent of balance"),
    tp_percent: float = Query(default=5.0, gt=0, le=50, description="Take profit percent magnitude"),
    sl_percent: float = Query(default=2.0, gt=0, le=50, description="Stop loss percent magnitude"),
    symbol: str = Query(default="BTC-USDT-SWAP", description="Trading symbol"),
):
    """
    Create a HITL pending trade without running the full LLM analysis cycle.

    This is intended for E2E testing of the HITL confirmation loop + PaperTrader execution.
    It is blocked when OKX trading is enabled.
    """
    _require_test_endpoints_enabled()
    from app.core.trading.mode_manager import get_mode_manager
    from app.core.trading.trading_settings_store import get_trading_settings_store

    system = await _get_system()
    if not system or not system.paper_trader:
        return {"success": False, "error": "Trading system not initialized"}

    # SAFETY CHECK: Block if OKX trading is enabled (active) OR requested in settings.
    scope = get_current_user_id()
    persisted = await get_trading_settings_store().get(scope)
    if system.trader_type == "okx" or persisted.use_okx_trading:
        return {
            "success": False,
            "error": "⚠️ BLOCKED: Cannot create mock pending trade while OKX trading is enabled!",
            "message": "This endpoint is only allowed with Paper Trader.",
            "action_required": "Disable OKX trading in Trading Settings and reset the system.",
            "current_trader": system.trader_type,
        }

    direction = (direction or "").lower()
    if direction not in ("long", "short"):
        return {"success": False, "error": f"Invalid direction: {direction}"}

    current_price = await system.paper_trader.get_current_price(symbol)
    if not current_price or current_price <= 0:
        return {"success": False, "error": "Failed to get current price"}

    # Compute absolute TP/SL prices based on current price.
    if direction == "long":
        tp_price = current_price * (1 + tp_percent / 100.0)
        sl_price = current_price * (1 - sl_percent / 100.0)
    else:
        tp_price = current_price * (1 - tp_percent / 100.0)
        sl_price = current_price * (1 + sl_percent / 100.0)

    manager = get_mode_manager(scope)
    pending = await manager.add_pending_trade(
        direction=direction,
        leverage=leverage,
        entry_price=current_price,
        take_profit=tp_price,
        stop_loss=sl_price,
        confidence=75,
        reasoning="E2E mock pending trade (HITL)",
        amount_percent=amount_percent,
        symbol=symbol,
    )

    # Broadcast to websocket listeners for UI parity.
    try:
        await system._broadcast(
            {
                "type": "pending_trade_created",
                "trade_id": pending.trade_id,
                "signal": pending.pending_trade.signal,
                "expires_at": pending.pending_trade.expires_at.isoformat(),
            }
        )
    except Exception as e:
        logger.warning(f"[mock/create-pending] WebSocket broadcast failed: {e}")

    return {
        "success": True,
        "trade_id": pending.trade_id,
        "pending_trade": pending.pending_trade.to_dict(),
        "message": "Pending trade created. Confirm via /api/trading/pending/{trade_id}/confirm",
    }


@router.post("/mock/test-tp-sl", dependencies=AUTH_DEPENDENCIES)
async def test_tp_sl_trigger(trigger_type: str = Query(default="tp", description="tp or sl")):
    """
    Test TP/SL trigger by simulating price movement.
    
    This endpoint manually sets the price to trigger TP or SL,
    verifying the position monitor works correctly.
    
    Args:
        trigger_type: 'tp' for take profit, 'sl' for stop loss
    """
    _require_test_endpoints_enabled()
    system = await _get_system()
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
        "position_closed": (not new_position) or (not new_position.get("has_position")),
        "account_balance": account.get("balance"),
        "realized_pnl": account.get("realized_pnl")
    }


@router.post("/mock/test-cooldown", dependencies=AUTH_DEPENDENCIES)
async def test_cooldown(losses: int = Query(default=3, description="Number of consecutive losses to simulate")):
    """
    Test cooldown by simulating consecutive losses.
    
    After 3 consecutive losses (default), the system should enter cooldown
    and block new analysis cycles.
    """
    _require_test_endpoints_enabled()
    system = await _get_system()
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


@router.post("/mock/reset-cooldown", dependencies=AUTH_DEPENDENCIES)
async def reset_cooldown():
    """Reset cooldown for testing purposes."""
    _require_test_endpoints_enabled()
    system = await _get_system()
    if not system:
        return {"success": False, "error": "Trading system not initialized"}
    
    system.cooldown_manager.force_end_cooldown()
    system.cooldown_manager._consecutive_losses = 0
    
    return {
        "success": True,
        "message": "Cooldown reset successfully",
        "cooldown_status": system.cooldown_manager.get_cooldown_status()
    }


@router.post("/mock/open-position", dependencies=AUTH_DEPENDENCIES)
async def open_test_position(
    direction: str = Query(default="long", description="long or short"),
    leverage: int = Query(default=3, description="Leverage 1-20"),
    amount_usdt: float = Query(default=1000, description="Amount in USDT")
):
    """
    Open a test position directly for TP/SL testing.
    This bypasses the full analysis cycle for quick testing.
    """
    _require_test_endpoints_enabled()
    system = await _get_system()
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


def _normalize_preference_action(action: str) -> str:
    normalized = (action or "").strip().lower()
    if normalized in ("confirm", "confirmed"):
        return "confirmed"
    if normalized in ("defer", "reject", "rejected"):
        return "rejected"
    if normalized in ("modify", "modified"):
        return "modified"
    if normalized == "expired":
        return "expired"
    return "rejected"


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@router.post("/decision", dependencies=AUTH_DEPENDENCIES)
async def record_user_decision(
    decision: UserDecision,
    current_user=Depends(get_current_user),
):
    """
    Record user's decision on AI trading signal.
    
    This data is valuable for RLHF training - each decision represents
    high-quality human feedback on AI trading recommendations.
    """
    from app.core.trading.preference_learner import get_preference_learner

    learner = get_preference_learner()
    original_signal = decision.original_signal or {}
    mapped_action = _normalize_preference_action(decision.action)

    direction = str(
        original_signal.get("direction")
        or original_signal.get("final_direction")
        or "hold"
    )
    leverage = _safe_int(
        original_signal.get("leverage")
        or original_signal.get("final_leverage")
        or 1,
        1,
    )
    confidence = _safe_int(original_signal.get("confidence") or 50, 50)
    stop_loss_percent = _safe_float(
        original_signal.get("stop_loss_percent")
        or original_signal.get("sl_percent")
        or original_signal.get("stop_loss")
        or 3.0,
        3.0,
    )
    take_profit_percent = _safe_float(
        original_signal.get("take_profit_percent")
        or original_signal.get("tp_percent")
        or original_signal.get("take_profit")
        or 6.0,
        6.0,
    )

    metadata = {
        "raw_action": decision.action,
        "defer_reason": decision.defer_reason,
        "recorded_at": datetime.now().isoformat(),
    }

    prefs = await learner.record_decision(
        trade_id=decision.decision_id,
        user_id=current_user.id,
        direction=direction,
        leverage=leverage,
        confidence=confidence,
        stop_loss_percent=stop_loss_percent,
        take_profit_percent=take_profit_percent,
        action=mapped_action,
        modified_leverage=decision.modified_leverage,
        metadata=metadata,
    )

    confirm_only = max(0, prefs.confirmed_count - prefs.modified_count)
    total = prefs.total_decisions
    confirms = confirm_only
    defers = prefs.rejected_count
    modifies = prefs.modified_count
    logger.info(f"[RLHF] User decision recorded: {decision.action} for {direction}")
    
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


@router.get("/decisions", dependencies=AUTH_DEPENDENCIES)
async def get_user_decisions(
    limit: int = Query(default=50, le=200),
    current_user=Depends(get_current_user),
):
    """
    Get history of user decisions.
    
    This endpoint demonstrates the data collection capability to investors.
    """
    from app.core.trading.preference_learner import get_preference_learner

    learner = get_preference_learner()
    decisions = await learner.get_recent_decisions(current_user.id, limit)
    prefs = await learner.get_preferences(current_user.id)

    total = prefs.total_decisions
    confirms = max(0, prefs.confirmed_count - prefs.modified_count)
    defers = prefs.rejected_count
    modifies = prefs.modified_count

    defer_reasons = {}
    for d in decisions:
        if d.get("action") != "rejected":
            continue
        metadata = d.get("metadata") or {}
        reason = metadata.get("defer_reason")
        if reason:
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


@router.post("/execute", dependencies=AUTH_DEPENDENCIES, deprecated=True)
async def execute_trade(request: Dict[str, Any]):
    """
    [DEPRECATED] Direct trade execution — use POST /pending/{trade_id}/confirm instead.

    Kept for backward compatibility with legacy frontend paths.
    New code should use the HITL pending trade confirmation flow.
    """
    # HITL-only: direct execution is intentionally disabled to avoid bypassing confirmation flow.
    raise HTTPException(
        status_code=410,
        detail="Direct execution is disabled. Use POST /api/trading/pending/{trade_id}/confirm.",
    )
