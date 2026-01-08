"""
Trading Mode API Router

Provides endpoints for:
- Getting/setting trading mode (FULL_AUTO, SEMI_AUTO, MANUAL)
- Managing pending trades in SEMI_AUTO mode
- Confirming or rejecting pending trades
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.trading.mode_manager import (
    TradingMode,
    TradingModeManager,
    PendingTrade,
    get_mode_manager,
)

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
    mode: str = Field(..., description="Trading mode: full_auto, semi_auto, manual")
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
    direction: str
    leverage: int
    confidence: int
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
    leverage: Optional[int] = Field(None, description="Modified leverage")
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
# Mode Description Mapping
# ============================================================================

MODE_DESCRIPTIONS = {
    TradingMode.FULL_AUTO: "Trades are executed automatically without user intervention",
    TradingMode.SEMI_AUTO: "Trades require user confirmation before execution",
    TradingMode.MANUAL: "Analysis only - no trades are executed automatically",
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
    # Validate mode
    try:
        new_mode = TradingMode(request.mode.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {request.mode}. Valid modes: full_auto, semi_auto, manual"
        )
    
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
    
    Only applicable in SEMI_AUTO mode.
    """
    manager = get_mode_manager()
    trades = await manager.get_pending_trades()
    
    now = datetime.now()
    trade_responses = []
    
    for trade in trades:
        signal = trade.signal
        expires_in = int((trade.expires_at - now).total_seconds())
        
        trade_responses.append(PendingTradeResponse(
            id=trade.id,
            direction=signal.get("direction", "unknown"),
            leverage=signal.get("leverage", 1),
            confidence=signal.get("confidence", 0),
            take_profit_percent=signal.get("take_profit_percent", 0),
            stop_loss_percent=signal.get("stop_loss_percent", 0),
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
    
    return PendingTradeResponse(
        id=trade.id,
        direction=signal.get("direction", "unknown"),
        leverage=signal.get("leverage", 1),
        confidence=signal.get("confidence", 0),
        take_profit_percent=signal.get("take_profit_percent", 0),
        stop_loss_percent=signal.get("stop_loss_percent", 0),
        reasoning=signal.get("reasoning", ""),
        created_at=trade.created_at.isoformat(),
        expires_at=trade.expires_at.isoformat(),
        expires_in_seconds=max(0, expires_in),
        status=trade.status,
    )


@router.post("/confirm/{trade_id}", response_model=ConfirmTradeResponse)
async def confirm_pending_trade(trade_id: str, request: ConfirmTradeRequest):
    """
    Confirm a pending trade for execution.
    
    Optionally modify leverage, TP, or SL before execution.
    """
    manager = get_mode_manager()
    
    # Build modifications dict
    modifications = {}
    if request.leverage is not None:
        modifications["leverage"] = request.leverage
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
    
    # TODO: Trigger actual trade execution here
    # For now, return the confirmed signal
    
    return ConfirmTradeResponse(
        success=True,
        trade_id=trade_id,
        message="Trade confirmed and queued for execution",
        executed_signal=signal
    )


@router.post("/reject/{trade_id}")
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

