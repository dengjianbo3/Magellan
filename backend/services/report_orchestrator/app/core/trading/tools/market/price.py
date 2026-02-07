"""
Price Tool

Gets current market price for a trading pair.
"""

from typing import List
import logging

from ..base import BaseTool, ToolResult, ToolParameter, ToolCategory
from ...trading_config import get_infra_config

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
    description = "Get current funding rate for perpetual swap. Returns rate value and payment direction (positive = longs pay shorts, negative = shorts pay longs)"
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
                base_url = get_infra_config().okx_base_url
                url = f"{base_url}/api/v5/public/funding-rate?instId={symbol}"
                response = await client.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == "0" and data.get("data"):
                        rate_data = data["data"][0]
                        funding_rate = float(rate_data.get("fundingRate", 0))
                        next_rate = float(rate_data.get("nextFundingRate", 0))
                        
                        # Provide objective description without directional interpretation
                        if funding_rate > 0:
                            interpretation = f"Positive ({funding_rate*100:.4f}%) - Longs pay shorts"
                        elif funding_rate < 0:
                            interpretation = f"Negative ({funding_rate*100:.4f}%) - Shorts pay longs"
                        else:
                            interpretation = "Zero - No funding payment"
                        
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
    description = "Get Fear & Greed Index for crypto market. Returns index value 0-100 with classification (Extreme Fear/Fear/Neutral/Greed/Extreme Greed)"
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
                        
                        # Provide objective description without directional interpretation
                        # Agent should determine trading implications based on context
                        interpretation = f"Fear & Greed Index: {value} ({classification})"
                        
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
