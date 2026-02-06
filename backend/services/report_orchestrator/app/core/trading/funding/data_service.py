"""
Funding Rate Data Service

Provides OKX API integration for funding rate data collection.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import aiohttp

from .models import FundingRate, FundingBill, RateTrend
from .config import get_funding_config

logger = logging.getLogger(__name__)


class FundingDataService:
    """
    Funding Rate Data Service
    
    Fetches funding rate data from OKX API including:
    - Current funding rate
    - Historical rates (for trend analysis)
    - Position funding bills
    """
    
    BASE_URL = "https://www.okx.com"
    
    def __init__(self):
        self.config = get_funding_config()
        self._session: Optional[aiohttp.ClientSession] = None
        
        # API credentials (for authenticated endpoints like bills)
        self.api_key = os.getenv("OKX_API_KEY", "")
        self.secret_key = os.getenv("OKX_SECRET_KEY", "")
        self.passphrase = os.getenv("OKX_PASSPHRASE", "")
        
        # Proxy for network access
        self.use_proxy = os.getenv("USE_PROXY", "false").lower() == "true"
        self.proxy_url = os.getenv("PROXY_URL", "")
    
    def _get_proxy(self) -> Optional[str]:
        """Get proxy URL if configured"""
        if self.use_proxy and self.proxy_url:
            return self.proxy_url
        return None
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
    
    async def get_current_rate(self, symbol: str = "BTC-USDT-SWAP") -> Optional[FundingRate]:
        """
        Get current funding rate from OKX
        
        OKX API: GET /api/v5/public/funding-rate
        
        Args:
            symbol: Trading pair (e.g., "BTC-USDT-SWAP")
            
        Returns:
            FundingRate object or None if failed
        """
        try:
            await self._ensure_session()
            
            url = f"{self.BASE_URL}/api/v5/public/funding-rate?instId={symbol}"
            proxy = self._get_proxy()
            
            async with self._session.get(url, proxy=proxy) as resp:
                data = await resp.json()
                
                if data.get('code') == '0' and data.get('data'):
                    rate_data = data['data'][0]
                    
                    # Parse rate
                    rate = float(rate_data.get('fundingRate', 0) or 0)
                    next_rate = float(rate_data.get('nextFundingRate', rate) or rate)
                    
                    # Parse next settlement time
                    next_time_ms = int(rate_data.get('fundingTime', 0) or 0)
                    next_settlement = datetime.fromtimestamp(next_time_ms / 1000) if next_time_ms else None
                    
                    # Get historical rates for averages
                    history = await self.get_rate_history(symbol, hours=168)  # 7 days
                    
                    avg_24h = self._calculate_avg_rate(history, hours=24)
                    avg_7d = self._calculate_avg_rate(history, hours=168)
                    trend = self._determine_trend(history)
                    
                    funding_rate = FundingRate(
                        symbol=symbol,
                        rate=rate,
                        next_settlement_time=next_settlement,
                        avg_24h=avg_24h,
                        avg_7d=avg_7d,
                        trend=trend
                    )
                    
                    logger.info(
                        f"[FundingData] {symbol}: rate={rate*100:.4f}%, "
                        f"next_settlement={funding_rate.minutes_to_settlement}min, "
                        f"avg_24h={avg_24h*100:.4f}%, trend={trend.value}"
                    )
                    
                    return funding_rate
                else:
                    logger.error(f"[FundingData] API error: {data.get('msg')}")
                    return None
                    
        except Exception as e:
            logger.error(f"[FundingData] Error fetching current rate: {e}")
            return None
    
    async def get_rate_history(
        self, 
        symbol: str = "BTC-USDT-SWAP", 
        hours: int = 72
    ) -> List[FundingRate]:
        """
        Get historical funding rates
        
        OKX API: GET /api/v5/public/funding-rate-history
        
        Args:
            symbol: Trading pair
            hours: How many hours of history to fetch
            
        Returns:
            List of FundingRate objects (newest first)
        """
        try:
            await self._ensure_session()
            
            # Calculate limit (3 per day for 8h intervals)
            limit = min(hours // 8 + 1, 100)  # Max 100 records
            
            url = f"{self.BASE_URL}/api/v5/public/funding-rate-history?instId={symbol}&limit={limit}"
            proxy = self._get_proxy()
            
            async with self._session.get(url, proxy=proxy) as resp:
                data = await resp.json()
                
                if data.get('code') == '0' and data.get('data'):
                    rates = []
                    for item in data['data']:
                        rate = float(item.get('fundingRate', 0) or 0)
                        timestamp_ms = int(item.get('fundingTime', 0) or 0)
                        timestamp = datetime.fromtimestamp(timestamp_ms / 1000) if timestamp_ms else datetime.now()
                        
                        rates.append(FundingRate(
                            symbol=symbol,
                            rate=rate,
                            next_settlement_time=None,
                            timestamp=timestamp
                        ))
                    
                    logger.debug(f"[FundingData] Fetched {len(rates)} historical rates for {symbol}")
                    return rates
                else:
                    logger.warning(f"[FundingData] History API error: {data.get('msg')}")
                    return []
                    
        except Exception as e:
            logger.error(f"[FundingData] Error fetching rate history: {e}")
            return []
    
    async def get_position_funding_bills(
        self, 
        symbol: str = "BTC-USDT-SWAP",
        since: Optional[datetime] = None
    ) -> List[FundingBill]:
        """
        Get funding fee bills for current/recent positions
        
        OKX API: GET /api/v5/account/bills (type=8 for funding)
        
        Note: This requires authenticated API access
        
        Args:
            symbol: Trading pair
            since: Only fetch bills after this time
            
        Returns:
            List of FundingBill objects
        """
        # This requires authenticated API - to be implemented
        # For now, return empty list
        logger.warning("[FundingData] get_position_funding_bills requires authenticated API - not yet implemented")
        return []
    
    def _calculate_avg_rate(self, history: List[FundingRate], hours: int) -> float:
        """Calculate average rate over specified hours"""
        if not history:
            return 0.0
        
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [r for r in history if r.timestamp > cutoff]
        
        if not recent:
            return 0.0
        
        return sum(r.rate for r in recent) / len(recent)
    
    def _determine_trend(self, history: List[FundingRate]) -> RateTrend:
        """Determine rate trend from history"""
        if len(history) < 6:  # Need at least 2 days of data
            return RateTrend.STABLE
        
        # Compare recent 24h avg vs previous 24h avg
        recent = history[:9]  # Last ~3 days
        older = history[9:18] if len(history) >= 18 else history[9:]
        
        if not older:
            return RateTrend.STABLE
        
        recent_avg = sum(r.rate for r in recent) / len(recent) if recent else 0
        older_avg = sum(r.rate for r in older) / len(older) if older else 0
        
        diff = recent_avg - older_avg
        threshold = 0.0001  # 0.01% change is significant
        
        if diff > threshold:
            return RateTrend.RISING
        elif diff < -threshold:
            return RateTrend.FALLING
        return RateTrend.STABLE
    
    async def close(self):
        """Close aiohttp session"""
        if self._session:
            await self._session.close()
            self._session = None


# Global singleton
_data_service: Optional[FundingDataService] = None


async def get_funding_data_service() -> FundingDataService:
    """Get or create funding data service singleton"""
    global _data_service
    if _data_service is None:
        _data_service = FundingDataService()
    return _data_service
