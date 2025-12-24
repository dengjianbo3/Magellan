"""
Price Service

Fetches real-time BTC price from multiple APIs.
Uses Binance as primary, OKX as secondary, CoinGecko as tertiary.
NO hardcoded fallback prices - raises error if all sources fail.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import httpx

logger = logging.getLogger(__name__)


class PriceServiceError(Exception):
    """Raised when all price sources fail"""
    pass


class PriceService:
    """
    Real-time price service for BTC.

    Features:
    - Multiple API sources: Binance (primary), OKX (secondary), CoinGecko (tertiary)
    - Caching to avoid rate limits
    - NO hardcoded fallback prices - raises error if all sources fail
    """

    # API endpoints
    BINANCE_URL = "https://api.binance.com/api/v3/ticker/price"
    OKX_URL = "https://www.okx.com/api/v5/market/ticker"
    COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

    # Cache settings
    CACHE_TTL_SECONDS = 30  # Cache price for 30 seconds

    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self._cache: Dict[str, Any] = {}
        self._last_fetch: Optional[datetime] = None
        self._last_valid_price: Optional[float] = None  # Store last valid price for short-term failures
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_btc_price(self) -> float:
        """
        Get current BTC price in USD.

        Tries multiple sources in order: Binance -> OKX -> CoinGecko
        Raises PriceServiceError if all sources fail.

        Returns:
            Current BTC price

        Raises:
            PriceServiceError: If all price sources fail
        """
        # Check cache first
        if self._is_cache_valid():
            cached_price = self._cache.get("btc_price")
            if cached_price is not None:
                return cached_price

        # Try multiple sources in order
        errors: List[str] = []

        # 1. Try Binance (most reliable for crypto)
        price = await self._fetch_binance_price()
        if price:
            self._update_cache(price)
            self._last_valid_price = price
            return price
        errors.append("Binance failed")

        # 2. Try OKX
        price = await self._fetch_okx_price()
        if price:
            self._update_cache(price)
            self._last_valid_price = price
            return price
        errors.append("OKX failed")

        # 3. Try CoinGecko
        price = await self._fetch_coingecko_price()
        if price:
            self._update_cache(price)
            self._last_valid_price = price
            return price
        errors.append("CoinGecko failed")

        # 4. Use last valid price if within 5 minutes (grace period for temporary outages)
        if self._last_valid_price and self._last_fetch:
            time_since_fetch = datetime.now() - self._last_fetch
            if time_since_fetch < timedelta(minutes=5):
                logger.warning(f"All price sources failed, using last valid price from {time_since_fetch.seconds}s ago")
                return self._last_valid_price

        # All sources failed - raise error
        error_msg = f"All price sources failed: {', '.join(errors)}"
        logger.error(error_msg)
        raise PriceServiceError(error_msg)

    async def _fetch_binance_price(self) -> Optional[float]:
        """Fetch BTC price from Binance API (primary source)"""
        try:
            client = await self._get_client()
            response = await client.get(
                self.BINANCE_URL,
                params={"symbol": "BTCUSDT"}
            )

            if response.status_code == 200:
                data = response.json()
                price = data.get("price")
                if price:
                    price_float = float(price)
                    logger.info(f"Fetched BTC price from Binance: ${price_float:,.2f}")
                    return price_float
            else:
                logger.warning(f"Binance API returned status {response.status_code}")

        except Exception as e:
            logger.warning(f"Failed to fetch price from Binance: {e}")

        return None

    async def _fetch_okx_price(self) -> Optional[float]:
        """Fetch BTC price from OKX API (secondary source)"""
        try:
            client = await self._get_client()
            response = await client.get(
                self.OKX_URL,
                params={"instId": "BTC-USDT"}
            )

            if response.status_code == 200:
                data = response.json()
                # OKX response format: {"code": "0", "data": [{"last": "95000", ...}]}
                if data.get("code") == "0" and data.get("data"):
                    price = data["data"][0].get("last")
                    if price:
                        price_float = float(price)
                        logger.info(f"Fetched BTC price from OKX: ${price_float:,.2f}")
                        return price_float
            else:
                logger.warning(f"OKX API returned status {response.status_code}")

        except Exception as e:
            logger.warning(f"Failed to fetch price from OKX: {e}")

        return None

    async def _fetch_coingecko_price(self) -> Optional[float]:
        """Fetch BTC price from CoinGecko API (tertiary source)"""
        try:
            client = await self._get_client()
            response = await client.get(
                self.COINGECKO_URL,
                params={
                    "ids": "bitcoin",
                    "vs_currencies": "usd"
                }
            )

            if response.status_code == 200:
                data = response.json()
                price = data.get("bitcoin", {}).get("usd")
                if price:
                    price_float = float(price)
                    logger.info(f"Fetched BTC price from CoinGecko: ${price_float:,.2f}")
                    return price_float
            else:
                logger.warning(f"CoinGecko API returned status {response.status_code}")

        except Exception as e:
            logger.warning(f"Failed to fetch price from CoinGecko: {e}")

        return None

    def _is_cache_valid(self) -> bool:
        """Check if cached price is still valid"""
        if not self._last_fetch:
            return False
        return datetime.now() - self._last_fetch < timedelta(seconds=self.CACHE_TTL_SECONDS)

    def _update_cache(self, price: float):
        """Update price cache"""
        self._cache["btc_price"] = price
        self._last_fetch = datetime.now()

    async def get_price_history(self, hours: int = 24) -> list:
        """
        Get historical price data from multiple sources.

        Tries: Binance -> CoinGecko
        Raises PriceServiceError if all sources fail.

        Args:
            hours: Number of hours of history to fetch

        Returns:
            List of {timestamp, price} dictionaries

        Raises:
            PriceServiceError: If all history sources fail
        """
        errors: List[str] = []

        # 1. Try Binance klines
        history = await self._fetch_binance_history(hours)
        if history:
            return history
        errors.append("Binance history failed")

        # 2. Try CoinGecko
        history = await self._fetch_coingecko_history(hours)
        if history:
            return history
        errors.append("CoinGecko history failed")

        # All sources failed
        error_msg = f"All price history sources failed: {', '.join(errors)}"
        logger.error(error_msg)
        raise PriceServiceError(error_msg)

    async def _fetch_binance_history(self, hours: int = 24) -> Optional[list]:
        """Fetch price history from Binance klines API"""
        try:
            client = await self._get_client()
            # Determine interval based on hours
            if hours <= 24:
                interval = "1h"
                limit = hours
            elif hours <= 168:  # 1 week
                interval = "4h"
                limit = hours // 4
            else:
                interval = "1d"
                limit = hours // 24

            response = await client.get(
                "https://api.binance.com/api/v3/klines",
                params={
                    "symbol": "BTCUSDT",
                    "interval": interval,
                    "limit": min(limit, 500)
                }
            )

            if response.status_code == 200:
                klines = response.json()
                if klines:
                    history = [
                        {
                            "timestamp": datetime.fromtimestamp(k[0] / 1000).isoformat(),
                            "price": float(k[4])  # Close price
                        }
                        for k in klines
                    ]
                    logger.info(f"Fetched {len(history)} price history points from Binance")
                    return history

        except Exception as e:
            logger.warning(f"Failed to fetch price history from Binance: {e}")

        return None

    async def _fetch_coingecko_history(self, hours: int = 24) -> Optional[list]:
        """Fetch price history from CoinGecko"""
        try:
            client = await self._get_client()
            days = max(1, hours // 24)

            response = await client.get(
                "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
                params={
                    "vs_currency": "usd",
                    "days": days
                }
            )

            if response.status_code == 200:
                data = response.json()
                prices = data.get("prices", [])
                if prices:
                    history = [
                        {
                            "timestamp": datetime.fromtimestamp(p[0] / 1000).isoformat(),
                            "price": p[1]
                        }
                        for p in prices
                    ]
                    logger.info(f"Fetched {len(history)} price history points from CoinGecko")
                    return history

        except Exception as e:
            logger.warning(f"Failed to fetch price history from CoinGecko: {e}")

        return None


# Singleton instance
_price_service: Optional[PriceService] = None


async def get_price_service(demo_mode: bool = False) -> PriceService:
    """Get or create price service singleton"""
    global _price_service
    if _price_service is None:
        _price_service = PriceService(demo_mode=demo_mode)
    return _price_service


async def get_current_btc_price(demo_mode: bool = False) -> float:
    """Convenience function to get current BTC price"""
    service = await get_price_service(demo_mode)
    return await service.get_btc_price()
