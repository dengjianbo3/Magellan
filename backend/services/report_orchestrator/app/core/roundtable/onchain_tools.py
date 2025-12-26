"""
On-Chain Data Tools for OnchainAnalyst
链上数据工具 - 用于增强 OnchainAnalyst 的分析能力

P0 Implementation:
- Fear & Greed Index (Alternative.me) - FREE
- DeFi TVL Data (DefiLlama) - FREE
"""

import httpx
from typing import Any, Dict, Optional
from .tool import Tool


class FearGreedIndexTool(Tool):
    """
    Crypto Fear & Greed Index Tool
    
    获取加密货币恐慌与贪婪指数
    数据来源: Alternative.me (免费, 无需 API Key)
    
    指数解读:
    - 0-24: Extreme Fear (极度恐慌) - 通常是买入机会
    - 25-49: Fear (恐慌)
    - 50-74: Greed (贪婪)
    - 75-100: Extreme Greed (极度贪婪) - 通常是卖出信号
    """
    
    def __init__(self):
        super().__init__(
            name="get_fear_greed_index",
            description="""Get the Crypto Fear & Greed Index.
This index measures market sentiment from 0 (Extreme Fear) to 100 (Extreme Greed).
- 0-24: Extreme Fear - potential buying opportunity
- 25-49: Fear
- 50-74: Greed  
- 75-100: Extreme Greed - potential sell signal
Useful for contrarian trading strategies."""
        )
        self.api_url = "https://api.alternative.me/fng/"
    
    async def execute(self, limit: int = 1, **kwargs) -> Dict[str, Any]:
        """
        Get Fear & Greed Index
        
        Args:
            limit: Number of days to fetch (1 = today only, 7 = last week, etc.)
        
        Returns:
            Dict with index value and classification
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.api_url,
                    params={"limit": limit, "format": "json"}
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("data"):
                    today = data["data"][0]
                    value = int(today.get("value", 50))
                    classification = today.get("value_classification", "Neutral")
                    timestamp = today.get("timestamp", "")
                    
                    # Generate analysis
                    analysis = self._generate_analysis(value, classification)
                    
                    # Build summary
                    summary = f"""📊 Crypto Fear & Greed Index: {value} ({classification})

{analysis}

Historical data (last {len(data['data'])} days):"""
                    
                    for i, day in enumerate(data["data"][:7]):
                        summary += f"\n  - Day {i}: {day.get('value')} ({day.get('value_classification')})"
                    
                    return {
                        "success": True,
                        "value": value,
                        "classification": classification,
                        "timestamp": timestamp,
                        "analysis": analysis,
                        "summary": summary,
                        "history": data["data"][:7]
                    }
                else:
                    return {
                        "success": False,
                        "summary": "Failed to fetch Fear & Greed Index data"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"Error fetching Fear & Greed Index: {str(e)}"
            }
    
    def _generate_analysis(self, value: int, classification: str) -> str:
        """Generate trading-relevant analysis based on index value"""
        if value <= 24:
            return """🔴 EXTREME FEAR detected!
- Market is in panic mode - historically a good buying opportunity
- Contrarian signal: Consider LONG positions
- Risk: Trend may continue lower before reversal"""
        elif value <= 49:
            return """🟡 FEAR in the market
- Sentiment is negative but not extreme
- Neutral to bullish bias for contrarians
- Watch for a shift toward extreme fear for better entries"""
        elif value <= 74:
            return """🟢 GREED in the market
- Optimism is high, prices may be stretched
- Be cautious with new LONG positions
- Consider taking some profits"""
        else:
            return """🔵 EXTREME GREED detected!
- Market euphoria - historically a sell signal
- High risk of correction
- Consider reducing positions or going SHORT"""
    
    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of days of history to fetch (default: 1, max: 30)",
                        "default": 1
                    }
                },
                "required": []
            }
        }


class DefiLlamaTVLTool(Tool):
    """
    DeFi TVL (Total Value Locked) Tool
    
    获取 DeFi 协议总锁仓量数据
    数据来源: DefiLlama (免费, 无需 API Key)
    
    用途:
    - 追踪 DeFi 生态健康度
    - 监控资金流入/流出趋势
    - 识别市场情绪变化
    """
    
    def __init__(self):
        super().__init__(
            name="get_defi_tvl",
            description="""Get DeFi Total Value Locked (TVL) data from DefiLlama.
Useful for:
- Tracking overall DeFi ecosystem health
- Monitoring capital inflows/outflows
- Identifying market sentiment shifts
- Chain-specific TVL analysis"""
        )
        self.base_url = "https://api.llama.fi"
    
    async def execute(self, query_type: str = "overview", **kwargs) -> Dict[str, Any]:
        """
        Get DeFi TVL data
        
        Args:
            query_type: Type of query
                - "overview": Get global DeFi TVL overview
                - "chains": Get TVL by blockchain
                - "protocol": Get specific protocol TVL (requires protocol_name)
            protocol_name: Protocol slug (e.g., "aave", "lido", "uniswap")
        
        Returns:
            Dict with TVL data and analysis
        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if query_type == "overview":
                    return await self._get_overview(client)
                elif query_type == "chains":
                    return await self._get_chains(client)
                elif query_type == "protocol":
                    protocol_name = kwargs.get("protocol_name", "")
                    if not protocol_name:
                        return {
                            "success": False,
                            "summary": "Protocol name required for protocol query"
                        }
                    return await self._get_protocol(client, protocol_name)
                else:
                    return await self._get_overview(client)
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"Error fetching DeFi TVL data: {str(e)}"
            }
    
    async def _get_overview(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Get global DeFi overview"""
        response = await client.get(f"{self.base_url}/v2/historicalChainTvl")
        response.raise_for_status()
        data = response.json()
        
        if data:
            # Get latest and calculate change
            latest = data[-1] if data else {}
            yesterday = data[-2] if len(data) > 1 else {}
            week_ago = data[-8] if len(data) > 7 else {}
            
            current_tvl = latest.get("tvl", 0)
            yesterday_tvl = yesterday.get("tvl", 0)
            week_ago_tvl = week_ago.get("tvl", 0)
            
            daily_change = ((current_tvl - yesterday_tvl) / yesterday_tvl * 100) if yesterday_tvl > 0 else 0
            weekly_change = ((current_tvl - week_ago_tvl) / week_ago_tvl * 100) if week_ago_tvl > 0 else 0
            
            # Generate analysis
            analysis = self._analyze_tvl_trend(daily_change, weekly_change)
            
            summary = f"""📊 Global DeFi TVL Overview

💰 Total TVL: ${current_tvl / 1e9:.2f}B
📈 24h Change: {daily_change:+.2f}%
📊 7d Change: {weekly_change:+.2f}%

{analysis}"""
            
            return {
                "success": True,
                "tvl_usd": current_tvl,
                "tvl_billions": current_tvl / 1e9,
                "daily_change_pct": round(daily_change, 2),
                "weekly_change_pct": round(weekly_change, 2),
                "analysis": analysis,
                "summary": summary
            }
        
        return {"success": False, "summary": "No TVL data available"}
    
    async def _get_chains(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Get TVL by chain"""
        response = await client.get(f"{self.base_url}/v2/chains")
        response.raise_for_status()
        chains = response.json()
        
        # Sort by TVL descending
        chains_sorted = sorted(chains, key=lambda x: x.get("tvl", 0), reverse=True)[:10]
        
        summary = "📊 Top 10 Chains by TVL:\n\n"
        for i, chain in enumerate(chains_sorted, 1):
            name = chain.get("name", "Unknown")
            tvl = chain.get("tvl", 0)
            change = chain.get("change_1d", 0) or 0
            summary += f"{i}. {name}: ${tvl/1e9:.2f}B ({change:+.2f}% 24h)\n"
        
        return {
            "success": True,
            "top_chains": chains_sorted,
            "summary": summary
        }
    
    async def _get_protocol(self, client: httpx.AsyncClient, protocol_name: str) -> Dict[str, Any]:
        """Get specific protocol TVL"""
        response = await client.get(f"{self.base_url}/protocol/{protocol_name}")
        
        if response.status_code == 404:
            return {
                "success": False,
                "summary": f"Protocol '{protocol_name}' not found on DefiLlama"
            }
        
        response.raise_for_status()
        data = response.json()
        
        name = data.get("name", protocol_name)
        tvl = data.get("tvl", 0)
        change_1d = data.get("change_1d", 0) or 0
        change_7d = data.get("change_7d", 0) or 0
        category = data.get("category", "Unknown")
        chains = data.get("chains", [])
        
        summary = f"""📊 Protocol: {name}
Category: {category}
Chains: {', '.join(chains[:5])}

💰 TVL: ${tvl/1e6:.2f}M
📈 24h: {change_1d:+.2f}%
📊 7d: {change_7d:+.2f}%"""
        
        return {
            "success": True,
            "name": name,
            "tvl": tvl,
            "change_1d": change_1d,
            "change_7d": change_7d,
            "category": category,
            "chains": chains,
            "summary": summary
        }
    
    def _analyze_tvl_trend(self, daily_change: float, weekly_change: float) -> str:
        """Analyze TVL trend and provide trading insights"""
        if weekly_change > 5:
            return """🟢 BULLISH SIGNAL: TVL is Growing Rapidly
- Strong capital inflows into DeFi
- Indicates increasing confidence in crypto
- Supports LONG bias for BTC/ETH"""
        elif weekly_change > 0:
            return """🟡 NEUTRAL-BULLISH: TVL is Stable/Growing
- Steady capital in DeFi ecosystem
- No major concerns
- Suggests stable market conditions"""
        elif weekly_change > -5:
            return """🟠 NEUTRAL-BEARISH: TVL is Declining Slightly
- Some capital leaving DeFi
- Watch for acceleration of outflows
- Consider reducing risk exposure"""
        else:
            return """🔴 BEARISH SIGNAL: TVL is Dropping Significantly
- Capital exodus from DeFi
- Risk-off sentiment in crypto
- Consider SHORT positions or cash"""
    
    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "description": "Type of query: 'overview' (global TVL), 'chains' (by chain), 'protocol' (specific protocol)",
                        "enum": ["overview", "chains", "protocol"],
                        "default": "overview"
                    },
                    "protocol_name": {
                        "type": "string",
                        "description": "Protocol slug for protocol query (e.g., 'aave', 'lido', 'uniswap')"
                    }
                },
                "required": []
            }
        }


class OnchainDataTool(Tool):
    """
    Unified On-Chain Data Tool
    
    统一链上数据工具 - 一站式获取所有链上指标
    集成 Fear & Greed + DefiLlama + 其他来源
    """
    
    def __init__(self):
        super().__init__(
            name="get_onchain_data",
            description="""Get comprehensive on-chain data for crypto analysis.
Fetches:
- Fear & Greed Index (market sentiment)
- DeFi TVL (ecosystem health)
- Combined analysis for trading decisions"""
        )
        self.fear_greed = FearGreedIndexTool()
        self.defi_tvl = DefiLlamaTVLTool()
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Get comprehensive on-chain data
        
        Returns:
            Dict with all on-chain metrics and analysis
        """
        try:
            # Fetch all data in parallel would be better, but sequential is simpler
            fear_greed_data = await self.fear_greed.execute(limit=7)
            tvl_data = await self.defi_tvl.execute(query_type="overview")
            
            # Combine analysis
            fg_value = fear_greed_data.get("value", 50)
            fg_class = fear_greed_data.get("classification", "Neutral")
            tvl_change = tvl_data.get("weekly_change_pct", 0)
            tvl_billions = tvl_data.get("tvl_billions", 0)
            
            # Generate combined signal
            signal = self._generate_combined_signal(fg_value, tvl_change)
            
            summary = f"""📊 ON-CHAIN DATA SUMMARY

🎭 SENTIMENT
Fear & Greed Index: {fg_value} ({fg_class})
{fear_greed_data.get('analysis', '')}

💰 DEFI ECOSYSTEM  
Total TVL: ${tvl_billions:.2f}B
7D Change: {tvl_change:+.2f}%
{tvl_data.get('analysis', '')}

🎯 COMBINED SIGNAL
{signal}"""
            
            return {
                "success": True,
                "fear_greed": {
                    "value": fg_value,
                    "classification": fg_class
                },
                "defi_tvl": {
                    "value_billions": tvl_billions,
                    "weekly_change": tvl_change
                },
                "combined_signal": signal,
                "summary": summary
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"Error fetching on-chain data: {str(e)}"
            }
    
    def _generate_combined_signal(self, fear_greed: int, tvl_change: float) -> str:
        """Generate trading signal from combined on-chain data"""
        # Scoring: -2 to +2 for each metric
        fg_score = 0
        if fear_greed <= 24:
            fg_score = 2  # Extreme fear = contrarian buy
        elif fear_greed <= 40:
            fg_score = 1
        elif fear_greed >= 75:
            fg_score = -2  # Extreme greed = contrarian sell
        elif fear_greed >= 60:
            fg_score = -1
            
        tvl_score = 0
        if tvl_change > 5:
            tvl_score = 2
        elif tvl_change > 0:
            tvl_score = 1
        elif tvl_change > -5:
            tvl_score = -1
        else:
            tvl_score = -2
        
        total = fg_score + tvl_score
        
        if total >= 3:
            return "🟢 STRONG BULLISH - High conviction LONG opportunity"
        elif total >= 1:
            return "🟢 BULLISH - Favor LONG positions"
        elif total >= -1:
            return "🟡 NEUTRAL - Wait for clearer signals"
        elif total >= -3:
            return "🔴 BEARISH - Favor SHORT or reduce exposure"
        else:
            return "🔴 STRONG BEARISH - High conviction SHORT opportunity"
    
    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
