"""
Trading Mode API Router

Provides endpoints for:
- Getting trading mode (HITL-only)
- Managing pending trades (confirmation workflow)
- Confirming or rejecting pending trades
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.trading.mode_manager import (
    TradingMode,
    TradingModeManager,
    PendingTrade,
    get_mode_manager,
)
from app.core.trading.paper_trader import get_paper_trader
from app.core.trading.price_service import get_current_btc_price

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trading", tags=["Trading Mode"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ModeResponse(BaseModel):
    """Response for getting current mode."""
    mode: str
    description: str
    

class SetModeRequest(BaseModel):
    """Request to set trading mode."""
    mode: str = Field(..., description="Trading mode (HITL-only): semi_auto")
    user_id: Optional[str] = Field(None, description="User ID for audit")


class SetModeResponse(BaseModel):
    """Response after setting mode."""
    success: bool
    previous_mode: str
    new_mode: str
    message: str


class PendingTradeResponse(BaseModel):
    """Response for a pending trade."""
    id: str
    symbol: str = "BTC-USDT-SWAP"
    direction: str
    leverage: int
    confidence: int
    entry_price: float = 0.0
    take_profit_price: float = 0.0
    stop_loss_price: float = 0.0
    amount_percent: float = 0.5
    take_profit_percent: float
    stop_loss_percent: float
    reasoning: str
    created_at: str
    expires_at: str
    expires_in_seconds: int
    status: str


class PendingTradesResponse(BaseModel):
    """Response for listing pending trades."""
    count: int
    trades: List[PendingTradeResponse]


class ConfirmTradeRequest(BaseModel):
    """Request to confirm a pending trade."""
    user_id: str = Field(..., description="User confirming the trade")
    direction: Optional[str] = Field(None, description="Modified direction (long/short)")
    leverage: Optional[int] = Field(None, description="Modified leverage")
    amount_percent: Optional[float] = Field(None, description="Modified position size (0.1-1.0)")
    take_profit_percent: Optional[float] = Field(None, description="Modified TP")
    stop_loss_percent: Optional[float] = Field(None, description="Modified SL")


class ConfirmTradeResponse(BaseModel):
    """Response after confirming a trade."""
    success: bool
    trade_id: str
    message: str
    executed_signal: Optional[dict] = None


class RejectTradeRequest(BaseModel):
    """Request to reject a pending trade."""
    user_id: str
    reason: Optional[str] = ""


# ============================================================================
# Trade Execution Helper
# ============================================================================

async def execute_confirmed_trade(signal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a confirmed trade signal.

    Args:
        signal: The confirmed trade signal containing direction, leverage, etc.

    Returns:
        Execution result with success status and details
    """
    direction = signal.get("direction", "").lower()

    # Skip execution for hold signals
    if direction == "hold" or direction == "":
        logger.info("[TradeExecution] Hold signal - no trade to execute")
        return {
            "success": True,
            "action": "hold",
            "message": "No trade executed (hold signal)"
        }

    # Get paper trader instance
    paper_trader = await get_paper_trader()

    # Get current price for TP/SL calculation
    current_price = await get_current_btc_price()
    if not current_price or current_price <= 0:
        logger.error("[TradeExecution] Failed to get current price")
        return {
            "success": False,
            "error": "Failed to get current price"
        }

    # Extract trade parameters
    leverage = signal.get("leverage", 5)
    amount_percent = signal.get("amount_percent", 0.2)  # Default 20%
    tp_percent = signal.get("take_profit_percent", None)
    sl_percent = signal.get("stop_loss_percent", None)

    # Prefer explicit TP/SL prices from the signal (HITL workflow usually provides absolute prices).
    tp_price = signal.get("take_profit_price") or signal.get("tp_price")
    sl_price = signal.get("stop_loss_price") or signal.get("sl_price")

    # If percent-based overrides are present, prefer percent computation.
    if tp_percent is not None or sl_percent is not None:
        tp_price = None
        sl_price = None

    # Validate provided TP/SL prices against current execution price.
    if tp_price is not None and sl_price is not None:
        try:
            tp_price = float(tp_price)
            sl_price = float(sl_price)
        except (TypeError, ValueError):
            tp_price = None
            sl_price = None

    if tp_price is not None and sl_price is not None:
        if direction == "long":
            if tp_price <= current_price or sl_price >= current_price:
                tp_price = None
                sl_price = None
        else:  # short
            if tp_price >= current_price or sl_price <= current_price:
                tp_price = None
                sl_price = None

    # Get account status for position sizing.
    # PaperTrader.get_status() uses "balance", while some other traders may expose "available_balance".
    status = await paper_trader.get_status()
    available_balance = status.get("available_balance")
    if available_balance is None:
        available_balance = status.get("balance", 0)

    if available_balance <= 0:
        logger.error("[TradeExecution] No available balance")
        return {
            "success": False,
            "error": "Insufficient balance"
        }

    # Calculate position size in USDT
    amount_usdt = available_balance * amount_percent

    # If explicit prices aren't available/valid, fall back to percent-based TP/SL.
    if tp_price is None or sl_price is None:
        tp_percent = float(tp_percent if tp_percent is not None else 5.0)
        sl_percent = float(sl_percent if sl_percent is not None else 2.0)

        if direction == "long":
            tp_price = current_price * (1 + tp_percent / 100)
            sl_price = current_price * (1 - sl_percent / 100)
        else:  # short
            tp_price = current_price * (1 - tp_percent / 100)
            sl_price = current_price * (1 + sl_percent / 100)

    logger.info(
        f"[TradeExecution] Executing {direction.upper()} trade: "
        f"leverage={leverage}x, amount=${amount_usdt:.2f}, "
        f"TP=${tp_price:.2f}, SL=${sl_price:.2f}"
    )

    try:
        # Execute the trade
        if direction == "long":
            result = await paper_trader.open_long(
                symbol="BTC-USDT-SWAP",
                leverage=leverage,
                amount_usdt=amount_usdt,
                tp_price=tp_price,
                sl_price=sl_price
            )
        elif direction == "short":
            result = await paper_trader.open_short(
                symbol="BTC-USDT-SWAP",
                leverage=leverage,
                amount_usdt=amount_usdt,
                tp_price=tp_price,
                sl_price=sl_price
            )
        else:
            return {
                "success": False,
                "error": f"Invalid direction: {direction}"
            }

        if result.get("success"):
            logger.info(
                f"[TradeExecution] ✅ Trade executed successfully: "
                f"{direction.upper()} @ ${float(result.get('executed_price') or result.get('entry_price') or 0):.2f}"
            )
            return {
                "success": True,
                "action": direction,
                "entry_price": result.get("executed_price") or result.get("entry_price"),
                "size": result.get("executed_amount") or result.get("size"),
                "leverage": leverage,
                "tp_price": tp_price,
                "sl_price": sl_price,
                "message": f"Successfully opened {direction} position"
            }
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"[TradeExecution] ❌ Trade failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

    except Exception as e:
        logger.error(f"[TradeExecution] ❌ Exception during trade execution: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# Mode Description Mapping
# ============================================================================

MODE_DESCRIPTIONS = {
    TradingMode.SEMI_AUTO: "Trades require user confirmation before execution",
}


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/mode", response_model=ModeResponse)
async def get_trading_mode():
    """
    Get the current trading mode.
    
    Returns:
        Current mode and its description
    """
    manager = get_mode_manager()
    mode = await manager.get_mode()
    
    return ModeResponse(
        mode=mode.value,
        description=MODE_DESCRIPTIONS.get(mode, "Unknown mode")
    )


@router.post("/mode", response_model=SetModeResponse)
async def set_trading_mode(request: SetModeRequest):
    """
    Set the trading mode.
    
    Args:
        request: Contains the new mode and optional user_id
        
    Returns:
        Success status and mode change details
    """
    # HITL-only: only semi_auto is supported.
    if request.mode.lower() != TradingMode.SEMI_AUTO.value:
        raise HTTPException(
            status_code=400,
            detail="Only semi_auto (HITL) mode is supported.",
        )
    new_mode = TradingMode.SEMI_AUTO
    
    manager = get_mode_manager()
    previous_mode = await manager.get_mode()
    
    success = await manager.set_mode(new_mode, request.user_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to set trading mode. Check Redis connection."
        )
    
    return SetModeResponse(
        success=True,
        previous_mode=previous_mode.value,
        new_mode=new_mode.value,
        message=f"Mode changed from {previous_mode.value} to {new_mode.value}"
    )


@router.get("/pending", response_model=PendingTradesResponse)
async def get_pending_trades():
    """
    Get all pending trades awaiting confirmation.
    
    HITL-only: always applicable.
    """
    manager = get_mode_manager()
    trades = await manager.get_pending_trades()
    
    now = datetime.now()
    trade_responses = []
    
    for trade in trades:
        signal = trade.signal
        expires_in = int((trade.expires_at - now).total_seconds())

        direction = signal.get("direction", "unknown")
        entry_price = float(signal.get("entry_price") or 0.0)
        tp_price = float(signal.get("take_profit_price") or 0.0)
        sl_price = float(signal.get("stop_loss_price") or 0.0)

        # Keep legacy percent fields for backward compatibility (positive magnitudes).
        sign = -1 if direction == "short" else 1
        tp_pct = ((tp_price / entry_price - 1) * 100 * sign) if entry_price and tp_price else 0.0
        sl_pct = ((1 - sl_price / entry_price) * 100 * sign) if entry_price and sl_price else 0.0
        
        trade_responses.append(PendingTradeResponse(
            id=trade.id,
            symbol=signal.get("symbol", "BTC-USDT-SWAP"),
            direction=direction,
            leverage=signal.get("leverage", 1),
            confidence=signal.get("confidence", 0),
            entry_price=entry_price,
            take_profit_price=tp_price,
            stop_loss_price=sl_price,
            amount_percent=float(signal.get("amount_percent") or 0.5),
            take_profit_percent=float(tp_pct),
            stop_loss_percent=float(sl_pct),
            reasoning=signal.get("reasoning", ""),
            created_at=trade.created_at.isoformat(),
            expires_at=trade.expires_at.isoformat(),
            expires_in_seconds=max(0, expires_in),
            status=trade.status,
        ))
    
    return PendingTradesResponse(
        count=len(trade_responses),
        trades=trade_responses
    )


@router.get("/pending/{trade_id}", response_model=PendingTradeResponse)
async def get_pending_trade(trade_id: str):
    """Get a specific pending trade by ID."""
    manager = get_mode_manager()
    trade = await manager.get_pending_trade(trade_id)
    
    if not trade:
        raise HTTPException(status_code=404, detail="Pending trade not found")
    
    now = datetime.now()
    signal = trade.signal
    expires_in = int((trade.expires_at - now).total_seconds())

    direction = signal.get("direction", "unknown")
    entry_price = float(signal.get("entry_price") or 0.0)
    tp_price = float(signal.get("take_profit_price") or 0.0)
    sl_price = float(signal.get("stop_loss_price") or 0.0)
    sign = -1 if direction == "short" else 1
    tp_pct = ((tp_price / entry_price - 1) * 100 * sign) if entry_price and tp_price else 0.0
    sl_pct = ((1 - sl_price / entry_price) * 100 * sign) if entry_price and sl_price else 0.0

    return PendingTradeResponse(
        id=trade.id,
        symbol=signal.get("symbol", "BTC-USDT-SWAP"),
        direction=direction,
        leverage=signal.get("leverage", 1),
        confidence=signal.get("confidence", 0),
        entry_price=entry_price,
        take_profit_price=tp_price,
        stop_loss_price=sl_price,
        amount_percent=float(signal.get("amount_percent") or 0.5),
        take_profit_percent=float(tp_pct),
        stop_loss_percent=float(sl_pct),
        reasoning=signal.get("reasoning", ""),
        created_at=trade.created_at.isoformat(),
        expires_at=trade.expires_at.isoformat(),
        expires_in_seconds=max(0, expires_in),
        status=trade.status,
    )


@router.post("/pending/{trade_id}/confirm", response_model=ConfirmTradeResponse)
async def confirm_pending_trade(trade_id: str, request: ConfirmTradeRequest):
    """
    Confirm a pending trade for execution.

    Optionally modify leverage, TP, or SL before execution.
    This endpoint actually executes the trade after confirmation.
    """
    manager = get_mode_manager()

    # Build modifications dict
    modifications = {}
    if request.direction is not None:
        modifications["direction"] = request.direction
    if request.leverage is not None:
        modifications["leverage"] = request.leverage
    if request.amount_percent is not None:
        modifications["amount_percent"] = request.amount_percent
    if request.take_profit_percent is not None:
        modifications["take_profit_percent"] = request.take_profit_percent
    if request.stop_loss_percent is not None:
        modifications["stop_loss_percent"] = request.stop_loss_percent

    signal = await manager.confirm_trade(
        trade_id=trade_id,
        user_id=request.user_id,
        modifications=modifications if modifications else None
    )

    if signal is None:
        raise HTTPException(
            status_code=404,
            detail="Trade not found, expired, or already processed"
        )

    # Execute the confirmed trade
    execution_result = await execute_confirmed_trade(signal)

    # Broadcast WebSocket event for frontend
    try:
        from app.services.trading_system import get_trading_system
        system = await get_trading_system()
        if execution_result.get("success"):
            await system._broadcast({
                "type": "trade_confirmed",
                "trade_id": trade_id,
                "signal": signal,
                "trade_result": execution_result,
                "confirmed_by": request.user_id
            })
        else:
            await system._broadcast({
                "type": "trade_confirm_failed",
                "trade_id": trade_id,
                "error": execution_result.get("error", "Unknown error")
            })
    except Exception as ws_err:
        logger.warning(f"[ConfirmTrade] WebSocket broadcast failed: {ws_err}")

    if not execution_result.get("success"):
        logger.error(
            f"[ConfirmTrade] Trade {trade_id} confirmed but execution failed: "
            f"{execution_result.get('error')}"
        )
        return ConfirmTradeResponse(
            success=False,
            trade_id=trade_id,
            message=f"Trade confirmed but execution failed: {execution_result.get('error')}",
            executed_signal=signal
        )

    # Merge execution result into signal for response
    signal["execution_result"] = execution_result

    return ConfirmTradeResponse(
        success=True,
        trade_id=trade_id,
        message=f"Trade confirmed and executed: {execution_result.get('message', 'Success')}",
        executed_signal=signal
    )


@router.post("/pending/{trade_id}/reject")
async def reject_pending_trade(trade_id: str, request: RejectTradeRequest):
    """Reject a pending trade."""
    manager = get_mode_manager()

    success = await manager.reject_trade(
        trade_id=trade_id,
        user_id=request.user_id,
        reason=request.reason or ""
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Trade not found or already processed"
        )

    # Broadcast WebSocket event for frontend
    try:
        from app.services.trading_system import get_trading_system
        system = await get_trading_system()
        await system._broadcast({
            "type": "trade_rejected",
            "trade_id": trade_id,
            "rejected_by": request.user_id,
            "reason": request.reason or ""
        })
    except Exception as ws_err:
        logger.warning(f"[RejectTrade] WebSocket broadcast failed: {ws_err}")

    return {
        "success": True,
        "trade_id": trade_id,
        "message": "Trade rejected"
    }


# ============================================================================
# ATR Dynamic Stop-Loss (Phase 2.2)
# ============================================================================

class ATRStopLossRequest(BaseModel):
    """Request for ATR-based stop-loss calculation."""
    direction: str = Field(..., description="Trade direction: long or short")
    entry_price: float = Field(..., description="Entry price")
    leverage: int = Field(1, description="Leverage multiplier")
    symbol: str = Field("BTC-USDT-SWAP", description="Trading symbol")


class ATRStopLossResponse(BaseModel):
    """Response with calculated stop-loss."""
    stop_loss_price: float
    sl_percent: float
    atr_value: float
    atr_multiplier: float
    method: str  # "atr", "max_cap", or "liquidation"


@router.post("/calculate-sl", response_model=ATRStopLossResponse)
async def calculate_atr_stop_loss(request: ATRStopLossRequest):
    """
    Calculate dynamic stop-loss based on ATR (Average True Range).
    
    The stop-loss adapts to market volatility:
    - High ATR = wider stop-loss
    - Low ATR = tighter stop-loss
    
    Constraints:
    - Maximum SL: 5% of entry price
    - Minimum SL: 0.5% of entry price
    - Ensures SL triggers before liquidation
    """
    from app.core.trading.atr_stop_loss import get_atr_calculator
    
    if request.direction.lower() not in ("long", "short"):
        raise HTTPException(
            status_code=400,
            detail="Direction must be 'long' or 'short'"
        )
    
    calculator = get_atr_calculator()
    result = await calculator.calculate_stop_loss(
        direction=request.direction,
        entry_price=request.entry_price,
        leverage=request.leverage,
        symbol=request.symbol,
    )
    
    return ATRStopLossResponse(
        stop_loss_price=result.stop_loss_price,
        sl_percent=round(result.sl_percent, 2),
        atr_value=round(result.atr_value, 2),
        atr_multiplier=result.atr_multiplier_used,
        method=result.method,
    )


# ============================================================================
# Graceful Degradation Status (Phase 2.3)
# ============================================================================

class DegradationStatusResponse(BaseModel):
    """Response for system degradation status."""
    level: str
    capabilities: dict
    circuit_statuses: dict


@router.get("/degradation", response_model=DegradationStatusResponse)
async def get_degradation_status():
    """
    Get current system degradation status.
    
    Degradation levels:
    - FULL: All services healthy, full functionality
    - REDUCED: Some services degraded, limited analysis
    - MINIMAL: Only position closing allowed
    - OFFLINE: No operations possible
    """
    from app.core.resilience.degradation import get_degradation_manager
    
    manager = get_degradation_manager()
    status = manager.get_status_summary()
    
    return DegradationStatusResponse(
        level=status["level"],
        capabilities=status["capabilities"],
        circuit_statuses=status["circuit_statuses"],
    )


# ============================================================================
# Multi-Timeframe Analysis (Phase 3.1)
# ============================================================================

class MTFAnalysisResponse(BaseModel):
    """Response for multi-timeframe analysis."""
    overall_direction: str
    alignment_score: float
    confidence_modifier: float
    recommendation: str
    timeframes: dict


@router.get("/mtf-analysis", response_model=MTFAnalysisResponse)
async def get_mtf_analysis(symbol: str = "BTC-USDT-SWAP"):
    """
    Perform multi-timeframe analysis.
    
    Analyzes trend alignment across 15m, 1H, 4H, and 1D timeframes.
    
    Returns:
    - overall_direction: bullish/bearish/neutral
    - alignment_score: 0-100, how aligned are all timeframes
    - confidence_modifier: 0.7-1.3, multiplier for signal confidence
    """
    from app.core.trading.multi_timeframe import get_mtf_analyzer
    
    analyzer = get_mtf_analyzer()
    result = await analyzer.analyze(symbol)
    
    return MTFAnalysisResponse(
        overall_direction=result.overall_direction.value,
        alignment_score=round(result.alignment_score, 1),
        confidence_modifier=round(result.confidence_modifier, 2),
        recommendation=result.recommendation,
        timeframes=result.to_dict()["timeframes"],
    )


# ============================================================================
# Agent Weight Learning (Phase 3.2)
# ============================================================================

class AgentWeightsResponse(BaseModel):
    """Response for agent weights."""
    weights: dict
    performance: Optional[dict] = None


@router.get("/agent-weights", response_model=AgentWeightsResponse)
async def get_agent_weights(include_performance: bool = False):
    """
    Get current learned weights for all agents.
    
    Weights are adjusted based on historical prediction accuracy.
    Range: 0.5 (poor accuracy) to 2.0 (excellent accuracy)
    """
    from app.core.trading.weight_learner import get_weight_learner
    
    learner = get_weight_learner()
    weights = await learner.get_all_weights()
    
    performance = None
    if include_performance:
        performance = await learner.get_all_performance()
    
    return AgentWeightsResponse(
        weights=weights,
        performance=performance,
    )


class RecordOutcomeRequest(BaseModel):
    """Request to record trade outcome for learning."""
    agent_predictions: dict  # {agent_name: prediction}
    actual_outcome: str  # "profitable", "loss", "neutral"
    trade_direction: str  # "long" or "short"


@router.post("/agent-weights/record-outcome")
async def record_trade_outcome(request: RecordOutcomeRequest):
    """
    Record trade outcome to update agent weights.
    
    This should be called after each trade closes to train the system.
    """
    from app.core.trading.weight_learner import get_weight_learner
    
    if request.actual_outcome not in ("profitable", "loss", "neutral"):
        raise HTTPException(
            status_code=400,
            detail="actual_outcome must be 'profitable', 'loss', or 'neutral'"
        )
    
    learner = get_weight_learner()
    updated_weights = await learner.record_trade_outcome(
        agent_predictions=request.agent_predictions,
        actual_outcome=request.actual_outcome,
        trade_direction=request.trade_direction,
    )
    
    return {
        "success": True,
        "updated_weights": updated_weights,
        "message": f"Updated weights for {len(updated_weights)} agents",
    }


@router.post("/agent-weights/reset/{agent_name}")
async def reset_agent_weight(agent_name: str):
    """Reset an agent's weight to default (1.0)."""
    from app.core.trading.weight_learner import get_weight_learner
    
    learner = get_weight_learner()
    new_weight = await learner.reset_agent_weight(agent_name)
    
    return {
        "success": True,
        "agent": agent_name,
        "new_weight": new_weight,
    }


# ============================================================================
# User Preference Learning (Phase 3.3)
# ============================================================================

class UserPreferencesResponse(BaseModel):
    """Response for user preferences."""
    user_id: str
    leverage: dict
    direction: dict
    risk: dict
    confidence: dict
    stats: dict
    last_updated: Optional[str] = None


@router.get("/user-preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(user_id: str = "default"):
    """
    Get learned preferences for a user.
    
    Preferences are learned from SEMI_AUTO confirmation/rejection patterns.
    """
    from app.core.trading.preference_learner import get_preference_learner
    
    learner = get_preference_learner()
    prefs = await learner.get_preferences(user_id)
    prefs_dict = prefs.to_dict()
    
    return UserPreferencesResponse(
        user_id=prefs_dict["user_id"],
        leverage=prefs_dict["leverage"],
        direction=prefs_dict["direction"],
        risk=prefs_dict["risk"],
        confidence=prefs_dict["confidence"],
        stats=prefs_dict["stats"],
        last_updated=prefs_dict.get("last_updated"),
    )


class RecordDecisionRequest(BaseModel):
    """Request to record a trade decision."""
    trade_id: str
    user_id: str = "default"
    direction: str
    leverage: int
    confidence: int
    stop_loss_percent: float
    take_profit_percent: float
    action: str  # "confirmed", "rejected", "modified", "expired"
    modified_leverage: Optional[int] = None
    modified_sl: Optional[float] = None
    modified_tp: Optional[float] = None


@router.post("/user-preferences/record-decision")
async def record_user_decision(request: RecordDecisionRequest):
    """
    Record a user's trade decision to update preferences.
    
    Call this when user confirms/rejects/modifies a pending trade.
    """
    from app.core.trading.preference_learner import get_preference_learner
    
    if request.action not in ("confirmed", "rejected", "modified", "expired"):
        raise HTTPException(
            status_code=400,
            detail="action must be 'confirmed', 'rejected', 'modified', or 'expired'"
        )
    
    learner = get_preference_learner()
    prefs = await learner.record_decision(
        trade_id=request.trade_id,
        user_id=request.user_id,
        direction=request.direction,
        leverage=request.leverage,
        confidence=request.confidence,
        stop_loss_percent=request.stop_loss_percent,
        take_profit_percent=request.take_profit_percent,
        action=request.action,
        modified_leverage=request.modified_leverage,
        modified_sl=request.modified_sl,
        modified_tp=request.modified_tp,
    )
    
    return {
        "success": True,
        "action": request.action,
        "updated_preferences": prefs.to_dict(),
    }


@router.get("/user-preferences/recent-decisions")
async def get_recent_decisions(user_id: str = "default", limit: int = 20):
    """Get recent trade decisions for a user."""
    from app.core.trading.preference_learner import get_preference_learner
    
    learner = get_preference_learner()
    decisions = await learner.get_recent_decisions(user_id, limit)
    
    return {
        "user_id": user_id,
        "count": len(decisions),
        "decisions": decisions,
    }


class SuggestAdjustmentsRequest(BaseModel):
    """Request to get suggested adjustments for a signal."""
    direction: str
    leverage: int
    confidence: int
    stop_loss_percent: float
    take_profit_percent: float
    user_id: str = "default"


@router.post("/user-preferences/suggest")
async def suggest_signal_adjustments(request: SuggestAdjustmentsRequest):
    """
    Get suggested adjustments for a trade signal based on user preferences.
    
    Returns warnings and suggestions if signal doesn't match user's typical preferences.
    """
    from app.core.trading.preference_learner import get_preference_learner
    
    learner = get_preference_learner()
    prefs = await learner.get_preferences(request.user_id)
    
    signal = {
        "direction": request.direction,
        "leverage": request.leverage,
        "confidence": request.confidence,
        "stop_loss_percent": request.stop_loss_percent,
        "take_profit_percent": request.take_profit_percent,
    }
    
    suggestions = learner.suggest_adjustments(prefs, signal)
    
    return {
        "has_suggestions": len(suggestions) > 0,
        "suggestions": suggestions,
        "user_preferences_summary": {
            "direction_bias": prefs.direction_bias,
            "avg_leverage": round(prefs.avg_accepted_leverage, 1),
            "min_confidence": prefs.min_accepted_confidence,
        }
    }


@router.post("/user-preferences/reset")
async def reset_user_preferences(user_id: str = "default"):
    """Reset user preferences to defaults."""
    from app.core.trading.preference_learner import get_preference_learner
    
    learner = get_preference_learner()
    prefs = await learner.reset_preferences(user_id)
    
    return {
        "success": True,
        "user_id": user_id,
        "message": "Preferences reset to defaults",
        "preferences": prefs.to_dict(),
    }
