"""
ATR Dynamic Stop-Loss Calculator

Calculates stop-loss prices based on Average True Range (ATR).
Adapts to market volatility - wider SL in volatile markets, tighter in calm markets.

Phase 2.2 of the architecture evolution roadmap.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
from datetime import datetime

import httpx
import structlog

from .trading_config import get_infra_config

logger = structlog.get_logger(__name__)


@dataclass
class ATRConfig:
    """Configuration for ATR-based stop-loss."""
    
    # ATR calculation
    period: int = 14                    # ATR period (candles)
    multiplier: float = 1.5             # ATR multiplier for SL distance
    
    # Safety limits
    max_sl_percent: float = 5.0         # Maximum SL as % of entry price
    min_sl_percent: float = 0.5         # Minimum SL as % of entry price
    
    # Liquidation protection
    liquidation_buffer_percent: float = 0.5  # Buffer above liquidation price
    
    # Data source
    timeframe: str = "4H"               # Candle timeframe for ATR


@dataclass
class StopLossResult:
    """Result of stop-loss calculation."""
    
    stop_loss_price: float
    sl_percent: float               # SL distance as % of entry
    atr_value: float                # Raw ATR value
    atr_multiplier_used: float      # Multiplier used
    method: str                     # "atr" | "max_cap" | "liquidation"
    
    def to_dict(self) -> dict:
        return {
            "stop_loss_price": self.stop_loss_price,
            "sl_percent": round(self.sl_percent, 2),
            "atr_value": round(self.atr_value, 2),
            "atr_multiplier": self.atr_multiplier_used,
            "method": self.method,
        }


class ATRStopLossCalculator:
    """
    Calculates dynamic stop-loss based on ATR.
    
    Features:
    - Adapts to market volatility
    - Respects maximum SL cap (5%)
    - Ensures SL is above liquidation price
    """
    
    def __init__(
        self,
        config: Optional[ATRConfig] = None,
        okx_base_url: Optional[str] = None,
    ):
        self.config = config or ATRConfig()
        self.okx_base_url = okx_base_url or get_infra_config().okx_base_url
        self._http_client: Optional[httpx.AsyncClient] = None
        self._atr_cache: dict = {}  # symbol -> (atr, timestamp)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def calculate_stop_loss(
        self,
        direction: str,          # "long" or "short"
        entry_price: float,
        leverage: int = 1,
        symbol: str = "BTC-USDT-SWAP",
        margin_amount: Optional[float] = None,
    ) -> StopLossResult:
        """
        Calculate dynamic stop-loss price.
        
        Args:
            direction: Trade direction ("long" or "short")
            entry_price: Entry price
            leverage: Leverage multiplier (for liquidation calc)
            symbol: Trading symbol
            margin_amount: Margin amount (for liquidation calc)
            
        Returns:
            StopLossResult with calculated SL price and metadata
        """
        # 1. Get ATR value
        atr = await self._get_atr(symbol)
        
        # 2. Calculate SL distance from ATR
        sl_distance = atr * self.config.multiplier
        sl_percent = (sl_distance / entry_price) * 100
        
        # 3. Determine method and apply limits
        method = "atr"
        
        # Apply maximum SL cap
        if sl_percent > self.config.max_sl_percent:
            sl_percent = self.config.max_sl_percent
            sl_distance = entry_price * (sl_percent / 100)
            method = "max_cap"
        
        # Apply minimum SL floor
        if sl_percent < self.config.min_sl_percent:
            sl_percent = self.config.min_sl_percent
            sl_distance = entry_price * (sl_percent / 100)
            method = "min_floor"
        
        # 4. Calculate SL price based on direction
        if direction.lower() == "long":
            sl_price = entry_price - sl_distance
        else:  # short
            sl_price = entry_price + sl_distance
        
        # 5. Ensure SL is above liquidation price
        if leverage > 1 and margin_amount:
            liq_price = self._calculate_liquidation_price(
                direction=direction,
                entry_price=entry_price,
                leverage=leverage,
                margin_amount=margin_amount,
            )
            
            if liq_price:
                sl_price = self._ensure_above_liquidation(
                    direction=direction,
                    sl_price=sl_price,
                    liq_price=liq_price,
                )
                
                # Recalculate percent after liquidation adjustment
                if direction.lower() == "long":
                    sl_distance = entry_price - sl_price
                else:
                    sl_distance = sl_price - entry_price
                sl_percent = (sl_distance / entry_price) * 100
                
                if method == "atr":
                    method = "liquidation"
        
        logger.info(
            "atr_stop_loss_calculated",
            direction=direction,
            entry_price=entry_price,
            sl_price=round(sl_price, 2),
            sl_percent=round(sl_percent, 2),
            atr=round(atr, 2),
            method=method
        )
        
        return StopLossResult(
            stop_loss_price=round(sl_price, 2),
            sl_percent=sl_percent,
            atr_value=atr,
            atr_multiplier_used=self.config.multiplier,
            method=method,
        )
    
    async def _get_atr(self, symbol: str = "BTC-USDT-SWAP") -> float:
        """
        Get ATR value for symbol.
        
        Uses 4H candles for stable ATR calculation.
        """
        # Check cache (valid for 1 hour)
        cache_key = f"{symbol}_{self.config.timeframe}"
        if cache_key in self._atr_cache:
            cached_atr, cached_time = self._atr_cache[cache_key]
            if (datetime.now() - cached_time).seconds < 3600:
                return cached_atr
        
        try:
            # Fetch klines from OKX
            klines = await self._fetch_klines(symbol, self.config.timeframe)
            
            if not klines or len(klines) < self.config.period:
                # Fallback: estimate ATR as 2% of current price
                logger.warning("insufficient_klines_for_atr", symbol=symbol)
                return await self._estimate_atr_fallback(symbol)
            
            # Calculate ATR
            atr = self._calculate_atr(klines)
            
            # Cache result
            self._atr_cache[cache_key] = (atr, datetime.now())
            
            return atr
            
        except Exception as e:
            logger.error("atr_calculation_failed", symbol=symbol, error=str(e))
            return await self._estimate_atr_fallback(symbol)
    
    async def _fetch_klines(
        self, 
        symbol: str, 
        timeframe: str
    ) -> List[Tuple[float, float, float, float]]:
        """
        Fetch klines from OKX.
        
        Returns list of (open, high, low, close) tuples.
        """
        client = await self._get_client()
        
        # Map timeframe to OKX bar format
        bar_map = {
            "1H": "1H", "4H": "4H", "1D": "1D",
            "1h": "1H", "4h": "4H", "1d": "1D"
        }
        bar = bar_map.get(timeframe, "4H")
        
        # OKX API endpoint
        url = f"{self.okx_base_url}/api/v5/market/candles"
        params = {
            "instId": symbol,
            "bar": bar,
            "limit": str(self.config.period + 5),  # Extra for safety
        }
        
        response = await client.get(url, params=params)
        
        if response.status_code != 200:
            raise Exception(f"OKX API error: {response.status_code}")
        
        data = response.json()
        
        if data.get("code") != "0":
            raise Exception(f"OKX API error: {data.get('msg')}")
        
        klines = []
        for candle in data.get("data", []):
            # OKX format: [ts, o, h, l, c, vol, ...]
            klines.append((
                float(candle[1]),  # open
                float(candle[2]),  # high
                float(candle[3]),  # low
                float(candle[4]),  # close
            ))
        
        return klines
    
    def _calculate_atr(
        self, 
        klines: List[Tuple[float, float, float, float]]
    ) -> float:
        """
        Calculate Average True Range from klines.
        
        True Range = max(H-L, |H-C_prev|, |L-C_prev|)
        ATR = SMA(TR, period)
        """
        if len(klines) < 2:
            return 0.0
        
        true_ranges = []
        
        for i in range(1, len(klines)):
            high = klines[i][1]
            low = klines[i][2]
            prev_close = klines[i - 1][3]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        # Use most recent 'period' TRs
        recent_trs = true_ranges[-self.config.period:]
        
        if not recent_trs:
            return 0.0
        
        return sum(recent_trs) / len(recent_trs)
    
    async def _estimate_atr_fallback(self, symbol: str) -> float:
        """
        Fallback ATR estimation when API fails.
        
        Uses 2% of current price as rough estimate.
        """
        try:
            client = await self._get_client()
            url = f"{self.okx_base_url}/api/v5/market/ticker"
            params = {"instId": symbol}
            
            response = await client.get(url, params=params)
            data = response.json()
            
            if data.get("code") == "0" and data.get("data"):
                price = float(data["data"][0]["last"])
                return price * 0.02  # 2% of price as fallback ATR
        except Exception as e:
            logger.warning(f"ATR fallback price fetch failed: {e}")
        
        # Ultimate fallback: assume BTC price ~$90,000
        return 1800.0  # 2% of $90,000
    
    def _calculate_liquidation_price(
        self,
        direction: str,
        entry_price: float,
        leverage: int,
        margin_amount: float,
    ) -> Optional[float]:
        """
        Calculate approximate liquidation price.
        
        This is a simplified calculation - actual liquidation depends on
        exchange-specific formulae.
        """
        if leverage <= 1:
            return None
        
        # Simplified: liquidation when loss = margin
        # For long: liq = entry * (1 - 1/leverage)
        # For short: liq = entry * (1 + 1/leverage)
        
        if direction.lower() == "long":
            liq_price = entry_price * (1 - 0.9 / leverage)  # 90% to be safe
        else:
            liq_price = entry_price * (1 + 0.9 / leverage)
        
        return liq_price
    
    def _ensure_above_liquidation(
        self,
        direction: str,
        sl_price: float,
        liq_price: float,
    ) -> float:
        """
        Ensure stop-loss triggers before liquidation.
        
        Adds buffer to prevent liquidation.
        """
        buffer = liq_price * (self.config.liquidation_buffer_percent / 100)
        
        if direction.lower() == "long":
            # For long: SL must be ABOVE liquidation price
            min_sl = liq_price + buffer
            return max(sl_price, min_sl)
        else:
            # For short: SL must be BELOW liquidation price
            max_sl = liq_price - buffer
            return min(sl_price, max_sl)
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
_atr_calculator: Optional[ATRStopLossCalculator] = None


def get_atr_calculator() -> ATRStopLossCalculator:
    """Get singleton ATRStopLossCalculator instance."""
    global _atr_calculator
    if _atr_calculator is None:
        _atr_calculator = ATRStopLossCalculator()
    return _atr_calculator


async def calculate_dynamic_sl(
    direction: str,
    entry_price: float,
    leverage: int = 1,
    symbol: str = "BTC-USDT-SWAP",
) -> StopLossResult:
    """Convenience function for ATR-based stop-loss calculation."""
    calculator = get_atr_calculator()
    return await calculator.calculate_stop_loss(
        direction=direction,
        entry_price=entry_price,
        leverage=leverage,
        symbol=symbol,
    )
