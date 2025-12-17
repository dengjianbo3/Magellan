"""
Price Tool

Gets current market price for a trading pair.
"""

from typing import List
import logging

from ..base import BaseTool, ToolResult, ToolParameter, ToolCategory

logger = logging.getLogger(__name__)


class GetPriceTool(BaseTool):
    """
    Get current market price for a trading pair.
    
    Returns current price, 24h change, high/low, and volume.
    """
    
    name = "get_market_price"
    description = "Get current market price and 24h data including price, change percentage, high, low, and volume"
    category = ToolCategory.MARKET
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="symbol",
                type="string",
                description="Trading pair (e.g., 'BTC-USDT-SWAP')",
                required=False,
                default="BTC-USDT-SWAP"
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Fetch current market price."""
        symbol = kwargs.get("symbol", "BTC-USDT-SWAP")
        
        try:
            # Import here to avoid circular imports
            from app.core.trading.price_service import get_current_btc_price
            
            price_data = await get_current_btc_price()
            
            if price_data:
                return ToolResult.success_result({
                    "symbol": symbol,
                    "price": price_data.get("price", 0),
                    "change_24h": price_data.get("change_24h", 0),
                    "change_percent": price_data.get("change_percent", 0),
                    "high_24h": price_data.get("high_24h", 0),
                    "low_24h": price_data.get("low_24h", 0),
                    "volume_24h": price_data.get("volume_24h", 0),
                    "timestamp": price_data.get("timestamp", "")
                }, self.name)
            else:
                return ToolResult.error_result(
                    "Failed to fetch price data",
                    self.name
                )
                
        except Exception as e:
            logger.error(f"Price fetch error: {e}")
            return ToolResult.error_result(str(e), self.name)


class GetFundingRateTool(BaseTool):
    """
    Get current funding rate for perpetual swaps.
    
    Positive = longs pay shorts, negative = shorts pay longs.
    """
    
    name = "get_funding_rate"
    description = "Get current funding rate for perpetual swap. Positive means longs pay shorts (bearish signal), negative means shorts pay longs (bullish signal)"
    category = ToolCategory.MARKET
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="symbol",
                type="string",
                description="Trading pair (e.g., 'BTC-USDT-SWAP')",
                required=False,
                default="BTC-USDT-SWAP"
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Fetch funding rate."""
        symbol = kwargs.get("symbol", "BTC-USDT-SWAP")
        
        try:
            # Try to get from OKX API
            import httpx
            
            async with httpx.AsyncClient() as client:
                # OKX funding rate endpoint
                url = f"https://www.okx.com/api/v5/public/funding-rate?instId={symbol}"
                response = await client.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == "0" and data.get("data"):
                        rate_data = data["data"][0]
                        funding_rate = float(rate_data.get("fundingRate", 0))
                        next_rate = float(rate_data.get("nextFundingRate", 0))
                        
                        # Interpret the rate  
                        if funding_rate > 0.0001:  # > 0.01%
                            interpretation = "Positive (longs pay) - Bearish signal, market may be overleveraged long"
                        elif funding_rate < -0.0001:  # < -0.01%
                            interpretation = "Negative (shorts pay) - Bullish signal, market may be overleveraged short"
                        else:
                            interpretation = "Neutral - Market is balanced"
                        
                        return ToolResult.success_result({
                            "symbol": symbol,
                            "funding_rate": funding_rate,
                            "funding_rate_percent": funding_rate * 100,
                            "next_funding_rate": next_rate,
                            "next_funding_rate_percent": next_rate * 100,
                            "interpretation": interpretation
                        }, self.name)
            
            return ToolResult.error_result(
                "Failed to fetch funding rate",
                self.name
            )
                
        except Exception as e:
            logger.error(f"Funding rate fetch error: {e}")
            return ToolResult.error_result(str(e), self.name)


class GetFearGreedTool(BaseTool):
    """
    Get Fear & Greed Index.
    
    0-25: Extreme Fear, 25-45: Fear, 45-55: Neutral, 55-75: Greed, 75-100: Extreme Greed
    """
    
    name = "get_fear_greed_index"
    description = "Get Fear & Greed Index for crypto market. 0-25=Extreme Fear (potential buy), 75-100=Extreme Greed (potential sell)"
    category = ToolCategory.MARKET
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []  # No parameters needed
    
    async def execute(self, **kwargs) -> ToolResult:
        """Fetch Fear & Greed Index."""
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                url = "https://api.alternative.me/fng/?limit=1"
                response = await client.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data"):
                        fng_data = data["data"][0]
                        value = int(fng_data.get("value", 50))
                        classification = fng_data.get("value_classification", "Neutral")
                        
                        # Add trading interpretation
                        if value <= 25:
                            interpretation = "Extreme Fear - Potential contrarian buy signal, market may be oversold"
                        elif value <= 45:
                            interpretation = "Fear - Market is cautious, could be accumulation zone"
                        elif value <= 55:
                            interpretation = "Neutral - Market is balanced, no clear signal"
                        elif value <= 75:
                            interpretation = "Greed - Market is optimistic, be cautious with new longs"
                        else:
                            interpretation = "Extreme Greed - Potential contrarian sell signal, market may be overbought"
                        
                        return ToolResult.success_result({
                            "value": value,
                            "classification": classification,
                            "interpretation": interpretation,
                            "timestamp": fng_data.get("timestamp", "")
                        }, self.name)
            
            return ToolResult.error_result(
                "Failed to fetch Fear & Greed Index",
                self.name
            )
                
        except Exception as e:
            logger.error(f"FGI fetch error: {e}")
            return ToolResult.error_result(str(e), self.name)
