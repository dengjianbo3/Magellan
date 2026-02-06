"""
Multi-Timeframe Analysis

Analyzes price action across multiple timeframes to improve signal confidence.
Aligns short-term and long-term trends for higher probability trades.

Phase 3.1 of the architecture evolution roadmap.

Timeframe Weights:
- 15m: 0.1 (short-term momentum)
- 1H: 0.3 (intraday trend)
- 4H: 0.4 (swing trend) - primary
- 1D: 0.2 (major trend direction)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Tuple, Any
import os

import httpx
import structlog

logger = structlog.get_logger(__name__)


class TrendDirection(Enum):
    """Trend direction for a timeframe."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class TimeframeTrend:
    """Trend analysis for a single timeframe."""
    timeframe: str
    direction: TrendDirection
    strength: float  # 0-100
    ema_fast: float
    ema_slow: float
    rsi: float
    close: float
    change_percent: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "strength": round(self.strength, 1),
            "ema_fast": round(self.ema_fast, 2),
            "ema_slow": round(self.ema_slow, 2),
            "rsi": round(self.rsi, 1),
            "close": round(self.close, 2),
            "change_percent": round(self.change_percent, 2),
        }


@dataclass
class MTFAnalysisResult:
    """Multi-timeframe analysis result."""
    overall_direction: TrendDirection
    alignment_score: float  # 0-100, how aligned are all timeframes
    confidence_modifier: float  # Multiplier for signal confidence (0.5-1.5)
    timeframes: Dict[str, TimeframeTrend]
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_direction": self.overall_direction.value,
            "alignment_score": round(self.alignment_score, 1),
            "confidence_modifier": round(self.confidence_modifier, 2),
            "recommendation": self.recommendation,
            "timeframes": {
                tf: trend.to_dict() 
                for tf, trend in self.timeframes.items()
            },
        }


# Timeframe configuration
TIMEFRAME_CONFIG = {
    "15m": {"weight": 0.1, "ema_fast": 9, "ema_slow": 21, "candles": 50},
    "1H": {"weight": 0.3, "ema_fast": 9, "ema_slow": 21, "candles": 50},
    "4H": {"weight": 0.4, "ema_fast": 9, "ema_slow": 21, "candles": 50},
    "1D": {"weight": 0.2, "ema_fast": 9, "ema_slow": 21, "candles": 30},
}


class MultiTimeframeAnalyzer:
    """
    Analyzes multiple timeframes to determine overall trend alignment.
    
    Used to:
    - Confirm signal direction across timeframes
    - Adjust confidence based on alignment
    - Identify potential reversals or continuations
    """
    
    def __init__(self, okx_base_url: Optional[str] = None):
        self.okx_base_url = okx_base_url or os.environ.get(
            "OKX_BASE_URL", 
            "https://www.okx.com"
        )
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def analyze(
        self,
        symbol: str = "BTC-USDT-SWAP",
        timeframes: Optional[List[str]] = None,
    ) -> MTFAnalysisResult:
        """
        Perform multi-timeframe analysis.
        
        Args:
            symbol: Trading symbol
            timeframes: List of timeframes to analyze (default: all)
            
        Returns:
            MTFAnalysisResult with alignment score and confidence modifier
        """
        if timeframes is None:
            timeframes = list(TIMEFRAME_CONFIG.keys())
        
        # Analyze each timeframe
        tf_trends: Dict[str, TimeframeTrend] = {}
        
        for tf in timeframes:
            if tf not in TIMEFRAME_CONFIG:
                continue
            
            try:
                trend = await self._analyze_timeframe(symbol, tf)
                tf_trends[tf] = trend
            except Exception as e:
                logger.warning(
                    "mtf_timeframe_analysis_failed",
                    timeframe=tf,
                    error=str(e)
                )
        
        if not tf_trends:
            # Fallback if all failed
            return MTFAnalysisResult(
                overall_direction=TrendDirection.NEUTRAL,
                alignment_score=50.0,
                confidence_modifier=1.0,
                timeframes={},
                recommendation="Insufficient data for MTF analysis",
            )
        
        # Calculate alignment
        result = self._calculate_alignment(tf_trends)
        
        logger.info(
            "mtf_analysis_complete",
            symbol=symbol,
            overall_direction=result.overall_direction.value,
            alignment_score=result.alignment_score,
            confidence_modifier=result.confidence_modifier
        )
        
        return result
    
    async def _analyze_timeframe(
        self, 
        symbol: str, 
        timeframe: str
    ) -> TimeframeTrend:
        """Analyze a single timeframe."""
        config = TIMEFRAME_CONFIG[timeframe]
        
        # Fetch candles
        candles = await self._fetch_candles(
            symbol, 
            timeframe, 
            config["candles"]
        )
        
        if len(candles) < config["ema_slow"]:
            raise ValueError(f"Insufficient candles for {timeframe}")
        
        # Extract closes
        closes = [c[3] for c in candles]  # close is index 3 (o, h, l, c)
        
        # Calculate EMAs
        ema_fast = self._calculate_ema(closes, config["ema_fast"])
        ema_slow = self._calculate_ema(closes, config["ema_slow"])
        
        # Calculate RSI
        rsi = self._calculate_rsi(closes, period=14)
        
        # Current close and change
        current_close = closes[0]
        prev_close = closes[1] if len(closes) > 1 else current_close
        change_percent = ((current_close - prev_close) / prev_close) * 100
        
        # Determine trend direction
        if ema_fast > ema_slow and rsi > 50:
            direction = TrendDirection.BULLISH
            strength = min(100, 50 + (ema_fast - ema_slow) / ema_slow * 500 + (rsi - 50))
        elif ema_fast < ema_slow and rsi < 50:
            direction = TrendDirection.BEARISH
            strength = min(100, 50 + (ema_slow - ema_fast) / ema_slow * 500 + (50 - rsi))
        else:
            direction = TrendDirection.NEUTRAL
            strength = 50 - abs(rsi - 50)
        
        return TimeframeTrend(
            timeframe=timeframe,
            direction=direction,
            strength=max(0, min(100, strength)),
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            rsi=rsi,
            close=current_close,
            change_percent=change_percent,
        )
    
    async def _fetch_candles(
        self, 
        symbol: str, 
        timeframe: str, 
        limit: int
    ) -> List[Tuple[float, float, float, float]]:
        """Fetch candles from OKX."""
        client = await self._get_client()
        
        # Map timeframe to OKX bar format
        bar_map = {
            "15m": "15m", "1H": "1H", "4H": "4H", "1D": "1D",
            "15M": "15m", "1h": "1H", "4h": "4H", "1d": "1D"
        }
        bar = bar_map.get(timeframe, "4H")
        
        url = f"{self.okx_base_url}/api/v5/market/candles"
        params = {
            "instId": symbol,
            "bar": bar,
            "limit": str(limit),
        }
        
        response = await client.get(url, params=params)
        
        if response.status_code != 200:
            raise Exception(f"OKX API error: {response.status_code}")
        
        data = response.json()
        
        if data.get("code") != "0":
            raise Exception(f"OKX API error: {data.get('msg')}")
        
        candles = []
        for candle in data.get("data", []):
            # OKX format: [ts, o, h, l, c, vol, ...]
            candles.append((
                float(candle[1]),  # open
                float(candle[2]),  # high
                float(candle[3]),  # low
                float(candle[4]),  # close
            ))
        
        return candles
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate EMA for the most recent price."""
        if len(prices) < period:
            return prices[0] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[-period:]) / period  # Start with SMA
        
        for price in reversed(prices[:-period]):
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI."""
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(min(period, len(prices) - 1)):
            change = prices[i] - prices[i + 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_alignment(
        self, 
        tf_trends: Dict[str, TimeframeTrend]
    ) -> MTFAnalysisResult:
        """Calculate overall alignment from all timeframes."""
        
        # Count directions with weights
        bullish_weight = 0.0
        bearish_weight = 0.0
        total_weight = 0.0
        
        for tf, trend in tf_trends.items():
            weight = TIMEFRAME_CONFIG.get(tf, {}).get("weight", 0.25)
            total_weight += weight
            
            if trend.direction == TrendDirection.BULLISH:
                bullish_weight += weight * (trend.strength / 100)
            elif trend.direction == TrendDirection.BEARISH:
                bearish_weight += weight * (trend.strength / 100)
        
        # Normalize
        if total_weight > 0:
            bullish_weight /= total_weight
            bearish_weight /= total_weight
        
        # Determine overall direction
        if bullish_weight > bearish_weight + 0.2:
            overall = TrendDirection.BULLISH
        elif bearish_weight > bullish_weight + 0.2:
            overall = TrendDirection.BEARISH
        else:
            overall = TrendDirection.NEUTRAL
        
        # Calculate alignment score (how unified are all timeframes)
        max_weight = max(bullish_weight, bearish_weight)
        alignment_score = max_weight * 100
        
        # Confidence modifier based on alignment
        if alignment_score >= 80:
            confidence_modifier = 1.3  # Strong alignment, boost confidence
            recommendation = f"Strong {overall.value} alignment across all timeframes"
        elif alignment_score >= 60:
            confidence_modifier = 1.1  # Moderate alignment
            recommendation = f"Moderate {overall.value} alignment, proceed with caution"
        elif alignment_score >= 40:
            confidence_modifier = 0.9  # Weak alignment
            recommendation = "Mixed signals across timeframes, consider reducing size"
        else:
            confidence_modifier = 0.7  # Divergence
            recommendation = "Timeframe divergence detected, consider holding"
        
        return MTFAnalysisResult(
            overall_direction=overall,
            alignment_score=alignment_score,
            confidence_modifier=confidence_modifier,
            timeframes=tf_trends,
            recommendation=recommendation,
        )
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
_mtf_analyzer: Optional[MultiTimeframeAnalyzer] = None


def get_mtf_analyzer() -> MultiTimeframeAnalyzer:
    """Get singleton MultiTimeframeAnalyzer instance."""
    global _mtf_analyzer
    if _mtf_analyzer is None:
        _mtf_analyzer = MultiTimeframeAnalyzer()
    return _mtf_analyzer


async def analyze_multi_timeframe(
    symbol: str = "BTC-USDT-SWAP",
) -> MTFAnalysisResult:
    """Convenience function for MTF analysis."""
    analyzer = get_mtf_analyzer()
    return await analyzer.analyze(symbol)
