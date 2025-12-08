"""
Phase 4 Advanced Tools (Free Alternatives)
Advanced analysis tools for roundtable discussion experts
"""
import os
import re
import httpx
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from .tool import Tool

logger = logging.getLogger(__name__)


class PersonBackgroundTool(Tool):
    """
    Person Background Check Tool (LinkedIn-free alternative)

    Get person background through public info search, GitHub analysis, news search
    """

    def __init__(self, web_search_url: str = "http://web_search_service:8010"):
        super().__init__(
            name="person_background",
            description="""Person background check tool.

Features:
- Public resume search (education, work experience)
- GitHub technical contribution analysis
- Media coverage and public speeches
- Startup/investment history
- Social influence assessment

Use cases:
- Founder background check
- Core team evaluation
- Key person risk analysis

Note: Uses public information sources, does not include LinkedIn private data"""
        )
        self.web_search_url = web_search_url
        self.github_api = "https://api.github.com"

    async def _search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """Execute web search"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.web_search_url}/search",
                    json={"query": query, "max_results": max_results}
                )
                response.raise_for_status()
                return response.json().get("results", [])
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return []

    async def _search_github(self, name: str) -> Dict[str, Any]:
        """Search GitHub user"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Search users
                response = await client.get(
                    f"{self.github_api}/search/users",
                    params={"q": name, "per_page": 3}
                )
                if response.status_code != 200:
                    return {"found": False}

                data = response.json()
                if data.get("total_count", 0) == 0:
                    return {"found": False}

                # Get first matching user's details
                user = data["items"][0]
                user_detail = await client.get(f"{self.github_api}/users/{user['login']}")
                if user_detail.status_code == 200:
                    detail = user_detail.json()
                    return {
                        "found": True,
                        "username": detail.get("login"),
                        "name": detail.get("name"),
                        "bio": detail.get("bio"),
                        "company": detail.get("company"),
                        "location": detail.get("location"),
                        "public_repos": detail.get("public_repos", 0),
                        "followers": detail.get("followers", 0),
                        "following": detail.get("following", 0),
                        "created_at": detail.get("created_at"),
                        "profile_url": detail.get("html_url")
                    }
                return {"found": False}
        except Exception as e:
            logger.warning(f"GitHub search failed: {e}")
            return {"found": False}

    async def execute(
        self,
        name: str = None,
        company: str = None,
        role: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute person background check

        Args:
            name: Person's name
            company: Company affiliation (optional, improves search accuracy)
            role: Job title (optional)

        Returns:
            Background check results
        """
        if not name:
            return {
                "success": False,
                "error": "Please provide a person's name",
                "summary": "Person background check requires a name"
            }

        try:
            # Build search query
            base_query = name
            if company:
                base_query += f" {company}"
            if role:
                base_query += f" {role}"

            # Execute multiple searches in parallel
            tasks = [
                self._search_web(f"{base_query} resume background education", 5),
                self._search_web(f"{base_query} startup funding investment", 3),
                self._search_web(f"{base_query} interview news coverage", 3),
                self._search_github(name)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            background_results = results[0] if not isinstance(results[0], Exception) else []
            startup_results = results[1] if not isinstance(results[1], Exception) else []
            media_results = results[2] if not isinstance(results[2], Exception) else []
            github_info = results[3] if not isinstance(results[3], Exception) else {"found": False}

            # Extract key information
            profile = {
                "name": name,
                "company": company,
                "role": role,
                "education": [],
                "work_history": [],
                "startup_history": [],
                "media_coverage": [],
                "github": github_info if github_info.get("found") else None,
                "sources": []
            }

            # Parse background information
            all_content = ""
            for result in background_results + startup_results:
                all_content += result.get("content", "") + "\n"
                profile["sources"].append({
                    "title": result.get("title", ""),
                    "url": result.get("url", "")
                })

            # Extract education background
            edu_patterns = [
                r"毕业于([^\s,，。]+(?:大学|学院|University|College))",
                r"([^\s,，。]+(?:大学|学院|University|College))\s*(?:毕业|学士|硕士|博士|MBA|PhD)",
                r"(?:本科|硕士|博士|MBA)\s*[：:]\s*([^\s,，。]+)"
            ]
            for pattern in edu_patterns:
                matches = re.findall(pattern, all_content)
                profile["education"].extend([m for m in matches if m not in profile["education"]])

            # Extract startup history
            startup_patterns = [
                r"创办(?:了)?([^\s,，。]+(?:公司|科技|网络))",
                r"(?:联合)?创始人[^\s]*([^\s,，。]+(?:公司|科技|网络))",
                r"创立(?:了)?([^\s,，。]+)"
            ]
            for pattern in startup_patterns:
                matches = re.findall(pattern, all_content)
                profile["startup_history"].extend([m for m in matches if m not in profile["startup_history"] and len(m) > 2])

            # Add media coverage
            for result in media_results[:3]:
                profile["media_coverage"].append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "date": result.get("published_date", "")
                })

            # Build summary
            summary = f"""【Person Background Check】{name}
{"Company: " + company if company else ""}
{"Role: " + role if role else ""}

📚 Education:
{chr(10).join(f"  • {e}" for e in profile["education"][:3]) if profile["education"] else "  No public education info found"}

🏢 Startup/Work History:
{chr(10).join(f"  • {s}" for s in profile["startup_history"][:3]) if profile["startup_history"] else "  No public startup info found"}

💻 GitHub (Technical Background):
{self._format_github(github_info)}

📰 Media Coverage:
{chr(10).join(f"  • {m['title'][:40]}" for m in profile["media_coverage"][:3]) if profile["media_coverage"] else "  No relevant coverage found"}

📋 Sources: {len(profile["sources"])} public sources"""

            return {
                "success": True,
                "data": profile,
                "summary": summary
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"Person background check failed: {str(e)}"
            }

    def _format_github(self, info: Dict) -> str:
        """Format GitHub info"""
        if not info.get("found"):
            return "  No matching GitHub account found"
        return f"""  Username: {info.get('username', 'N/A')}
  Public Repos: {info.get('public_repos', 0)}
  Followers: {info.get('followers', 0)}
  Bio: {info.get('bio', 'N/A')[:50] if info.get('bio') else 'N/A'}"""

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Person's name"
                    },
                    "company": {
                        "type": "string",
                        "description": "Company affiliation (optional, improves search accuracy)"
                    },
                    "role": {
                        "type": "string",
                        "description": "Job title (optional)"
                    }
                },
                "required": ["name"]
            }
        }


class RegulationSearchTool(Tool):
    """
    Regulation Search Tool (using government public data)

    Get legal and regulatory information by searching government regulation websites
    """

    def __init__(self, web_search_url: str = "http://web_search_service:8010"):
        super().__init__(
            name="regulation_search",
            description="""Regulation search tool.

Features:
- Laws and regulations search
- Departmental rules query
- Judicial interpretation search
- Regulatory policy tracking

Supported areas:
- Company law/Securities law
- Financial regulation
- Data security/Privacy
- Industry-specific regulations

Data sources: Government public regulation databases + Official websites"""
        )
        self.web_search_url = web_search_url

        # Government regulation website domains
        self.gov_domains = [
            "gov.cn",
            "moj.gov.cn",      # Ministry of Justice
            "pbc.gov.cn",      # Central Bank
            "csrc.gov.cn",     # Securities Commission
            "cbirc.gov.cn",    # Banking/Insurance Commission
            "samr.gov.cn",     # Market Regulation
            "miit.gov.cn",     # Ministry of Industry
            "cac.gov.cn"       # Cyberspace Administration
        ]

    async def _search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """Execute web search"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.web_search_url}/search",
                    json={"query": query, "max_results": max_results}
                )
                response.raise_for_status()
                return response.json().get("results", [])
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return []

    async def execute(
        self,
        keywords: str = None,
        law_type: str = "all",
        industry: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute regulation search

        Args:
            keywords: Search keywords
            law_type: Regulation type (law/regulation/interpretation/policy/all)
            industry: Industry sector (fintech/healthcare/ecommerce/ai etc)

        Returns:
            Regulation search results
        """
        if not keywords:
            return {
                "success": False,
                "error": "Please provide search keywords",
                "summary": "Regulation search requires keywords"
            }

        try:
            # Build search query
            type_keywords = {
                "law": "law legislation",
                "regulation": "regulation rules",
                "interpretation": "judicial interpretation",
                "policy": "policy notice guidance",
                "all": ""
            }

            industry_keywords = {
                "fintech": "finance payment lending",
                "healthcare": "medical pharmaceutical",
                "ecommerce": "e-commerce online trading",
                "ai": "artificial intelligence algorithm data",
                "crypto": "cryptocurrency digital assets",
                "education": "education training"
            }

            base_query = keywords
            if law_type != "all" and law_type in type_keywords:
                base_query += f" {type_keywords[law_type]}"
            if industry and industry in industry_keywords:
                base_query += f" {industry_keywords[industry]}"

            # Search government websites
            gov_query = f"{base_query} site:gov.cn"
            general_query = f"{base_query} regulation law"

            tasks = [
                self._search_web(gov_query, 5),
                self._search_web(general_query, 5)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            gov_results = results[0] if not isinstance(results[0], Exception) else []
            general_results = results[1] if not isinstance(results[1], Exception) else []

            # Merge results, prioritize government sources
            regulations = []
            seen_urls = set()

            # Process government sources
            for result in gov_results:
                url = result.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    regulations.append({
                        "title": result.get("title", ""),
                        "content": result.get("content", "")[:300],
                        "url": url,
                        "source_type": "Government",
                        "date": result.get("published_date", "")
                    })

            # Process general sources (non-government)
            for result in general_results:
                url = result.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    is_gov = any(domain in url for domain in self.gov_domains)
                    regulations.append({
                        "title": result.get("title", ""),
                        "content": result.get("content", "")[:300],
                        "url": url,
                        "source_type": "Government" if is_gov else "Other",
                        "date": result.get("published_date", "")
                    })

            # Classification stats
            gov_count = sum(1 for r in regulations if r["source_type"] == "Government")

            summary = f"""【Regulation Search Results】Keywords: {keywords}

📋 Search Type: {law_type}
🏭 Industry: {industry or "General"}
📊 Results Found: {len(regulations)} (Government sources: {gov_count})

📜 Related Regulations:
"""
            for i, reg in enumerate(regulations[:5], 1):
                summary += f"\n{i}. [{reg['source_type']}] {reg['title'][:50]}"
                if reg.get("date"):
                    summary += f" ({reg['date']})"

            summary += f"""

⚠️ Notes:
- Verify the latest version and effective status of regulations
- Consult professional lawyers for complex legal issues
- Government sources are more authoritative"""

            return {
                "success": True,
                "data": {
                    "keywords": keywords,
                    "law_type": law_type,
                    "industry": industry,
                    "total_count": len(regulations),
                    "gov_count": gov_count,
                    "regulations": regulations[:10]
                },
                "summary": summary
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"Regulation search failed: {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "Search keywords, e.g. 'data protection', 'payment license'"
                    },
                    "law_type": {
                        "type": "string",
                        "description": "Regulation type",
                        "enum": ["law", "regulation", "interpretation", "policy", "all"],
                        "default": "all"
                    },
                    "industry": {
                        "type": "string",
                        "description": "Industry sector",
                        "enum": ["fintech", "healthcare", "ecommerce", "ai", "crypto", "education"]
                    }
                },
                "required": ["keywords"]
            }
        }


class MultiExchangeTool(Tool):
    """
    Multi-Exchange Data Tool

    Get market data from multiple cryptocurrency exchanges
    """

    def __init__(self):
        super().__init__(
            name="multi_exchange_data",
            description="""Multi-exchange cryptocurrency data tool.

Features:
- Multi-exchange price comparison
- Price spread and arbitrage opportunity detection
- Volume distribution analysis
- Funding rate comparison

Supported exchanges:
- Binance
- OKX
- Coinbase
- Bybit

Supported pairs: BTC, ETH and other major cryptocurrencies"""
        )

        self.exchanges = {
            "binance": {
                "ticker": "https://api.binance.com/api/v3/ticker/24hr",
                "price": "https://api.binance.com/api/v3/ticker/price"
            },
            "okx": {
                "ticker": "https://www.okx.com/api/v5/market/ticker"
            },
            "coinbase": {
                "ticker": "https://api.coinbase.com/v2/prices/{symbol}/spot"
            },
            "bybit": {
                "ticker": "https://api.bybit.com/v5/market/tickers"
            }
        }

    async def _get_binance_price(self, symbol: str) -> Dict[str, Any]:
        """Get Binance price"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    self.exchanges["binance"]["ticker"],
                    params={"symbol": f"{symbol}USDT"}
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "exchange": "Binance",
                        "price": float(data.get("lastPrice", 0)),
                        "volume_24h": float(data.get("volume", 0)),
                        "change_24h": float(data.get("priceChangePercent", 0)),
                        "high_24h": float(data.get("highPrice", 0)),
                        "low_24h": float(data.get("lowPrice", 0))
                    }
        except Exception as e:
            logger.warning(f"Binance API error: {e}")
        return None

    async def _get_okx_price(self, symbol: str) -> Dict[str, Any]:
        """Get OKX price"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    self.exchanges["okx"]["ticker"],
                    params={"instId": f"{symbol}-USDT"}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data"):
                        ticker = data["data"][0]
                        return {
                            "exchange": "OKX",
                            "price": float(ticker.get("last", 0)),
                            "volume_24h": float(ticker.get("vol24h", 0)),
                            "change_24h": float(ticker.get("sodUtc0", 0)),
                            "high_24h": float(ticker.get("high24h", 0)),
                            "low_24h": float(ticker.get("low24h", 0))
                        }
        except Exception as e:
            logger.warning(f"OKX API error: {e}")
        return None

    async def _get_bybit_price(self, symbol: str) -> Dict[str, Any]:
        """Get Bybit price"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    self.exchanges["bybit"]["ticker"],
                    params={"category": "spot", "symbol": f"{symbol}USDT"}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("result", {}).get("list"):
                        ticker = data["result"]["list"][0]
                        return {
                            "exchange": "Bybit",
                            "price": float(ticker.get("lastPrice", 0)),
                            "volume_24h": float(ticker.get("volume24h", 0)),
                            "change_24h": float(ticker.get("price24hPcnt", 0)) * 100,
                            "high_24h": float(ticker.get("highPrice24h", 0)),
                            "low_24h": float(ticker.get("lowPrice24h", 0))
                        }
        except Exception as e:
            logger.warning(f"Bybit API error: {e}")
        return None

    async def execute(
        self,
        symbol: str = "BTC",
        exchanges: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get multi-exchange data

        Args:
            symbol: Coin symbol (BTC/ETH/etc) or pair format (BTC-USDT)
            exchanges: List of exchanges (optional)

        Returns:
            Multi-exchange data comparison
        """
        # Handle different input formats: BTC-USDT / BTC/USDT / BTCUSDT / BTC
        symbol = symbol.upper()
        # Remove common separators and USDT suffix
        symbol = symbol.replace('-USDT', '').replace('/USDT', '').replace('USDT', '')
        # Handle other possible formats
        symbol = symbol.replace('-', '').replace('/', '').strip()
        if exchanges is None:
            exchanges = ["binance", "okx", "bybit"]

        try:
            # Get data from exchanges in parallel
            tasks = []
            if "binance" in exchanges:
                tasks.append(self._get_binance_price(symbol))
            if "okx" in exchanges:
                tasks.append(self._get_okx_price(symbol))
            if "bybit" in exchanges:
                tasks.append(self._get_bybit_price(symbol))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter valid results
            valid_results = [r for r in results if r and not isinstance(r, Exception)]

            if not valid_results:
                return {
                    "success": False,
                    "error": "Unable to get data from any exchange",
                    "summary": f"Failed to get {symbol} data, please check if the symbol is correct"
                }

            # Calculate spread
            prices = [r["price"] for r in valid_results if r["price"] > 0]
            if prices:
                max_price = max(prices)
                min_price = min(prices)
                spread = (max_price - min_price) / min_price * 100 if min_price > 0 else 0
                avg_price = sum(prices) / len(prices)
            else:
                spread = 0
                avg_price = 0

            # Build summary
            summary = f"""【Multi-Exchange Data】{symbol}/USDT

📊 Price Comparison:
"""
            for r in valid_results:
                price_diff = ((r["price"] - avg_price) / avg_price * 100) if avg_price > 0 else 0
                summary += f"  {r['exchange']:10} ${r['price']:,.2f} ({price_diff:+.2f}%)\n"

            summary += f"""
📈 Spread Analysis:
  High: ${max_price:,.2f}
  Low: ${min_price:,.2f}
  Spread: {spread:.3f}%
  {"⚠️ Arbitrage opportunity" if spread > 0.5 else "✅ Normal spread"}

📊 24h Volume:
"""
            for r in valid_results:
                summary += f"  {r['exchange']:10} {r['volume_24h']:,.0f} {symbol}\n"

            summary += f"""
📉 24h Change:
"""
            for r in valid_results:
                summary += f"  {r['exchange']:10} {r['change_24h']:+.2f}%\n"

            return {
                "success": True,
                "data": {
                    "symbol": symbol,
                    "exchanges": valid_results,
                    "spread": {
                        "max_price": max_price,
                        "min_price": min_price,
                        "spread_percent": spread,
                        "avg_price": avg_price
                    },
                    "timestamp": datetime.now().isoformat()
                },
                "summary": summary
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"Multi-exchange data fetch failed: {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Coin symbol, e.g. BTC, ETH, SOL",
                        "default": "BTC"
                    },
                    "exchanges": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of exchanges (binance/okx/bybit)"
                    }
                },
                "required": []
            }
        }


class OrderbookAnalyzerTool(Tool):
    """
    Orderbook Depth Analysis Tool

    Analyze exchange orderbook data to identify support/resistance levels
    """

    def __init__(self):
        super().__init__(
            name="orderbook_analyzer",
            description="""Orderbook depth analysis tool.

Features:
- Bid/ask depth analysis
- Support/resistance level identification
- Large order monitoring
- Buy/sell pressure comparison

Use cases:
- Short-term trading decisions
- Market sentiment analysis
- Liquidity assessment"""
        )

    async def _get_binance_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get Binance orderbook"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.binance.com/api/v3/depth",
                    params={"symbol": f"{symbol}USDT", "limit": limit}
                )
                if response.status_code == 200:
                    data = response.json()
                    data["_exchange"] = "Binance"
                    return data
        except Exception as e:
            logger.warning(f"Binance orderbook error: {e}")
        return None

    async def _get_okx_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get OKX orderbook (fallback)"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://www.okx.com/api/v5/market/books",
                    params={"instId": f"{symbol}-USDT", "sz": str(min(limit, 400))}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data") and len(data["data"]) > 0:
                        book = data["data"][0]
                        return {
                            "bids": [[b[0], b[1]] for b in book.get("bids", [])],
                            "asks": [[a[0], a[1]] for a in book.get("asks", [])],
                            "_exchange": "OKX"
                        }
        except Exception as e:
            logger.warning(f"OKX orderbook error: {e}")
        return None

    async def _get_bybit_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get Bybit orderbook (fallback)"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.bybit.com/v5/market/orderbook",
                    params={"category": "spot", "symbol": f"{symbol}USDT", "limit": str(min(limit, 200))}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("result"):
                        book = data["result"]
                        return {
                            "bids": [[b[0], b[1]] for b in book.get("b", [])],
                            "asks": [[a[0], a[1]] for a in book.get("a", [])],
                            "_exchange": "Bybit"
                        }
        except Exception as e:
            logger.warning(f"Bybit orderbook error: {e}")
        return None

    async def _get_orderbook_with_fallback(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get orderbook with fallback"""
        # 1. Try Binance
        orderbook = await self._get_binance_orderbook(symbol, limit)
        if orderbook:
            return orderbook

        logger.info(f"Binance failed for {symbol}, trying OKX...")

        # 2. Try OKX
        orderbook = await self._get_okx_orderbook(symbol, limit)
        if orderbook:
            return orderbook

        logger.info(f"OKX failed for {symbol}, trying Bybit...")

        # 3. Try Bybit
        orderbook = await self._get_bybit_orderbook(symbol, limit)
        if orderbook:
            return orderbook

        return None

    async def execute(
        self,
        symbol: str = "BTC",
        depth: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze orderbook

        Args:
            symbol: Coin symbol
            depth: Number of depth levels

        Returns:
            Orderbook analysis results
        """
        # Normalize symbol - handle formats like BTC/USDT, BTC-USDT, BTCUSDT, BTC
        symbol = symbol.upper()
        symbol = symbol.replace('-USDT', '').replace('/USDT', '').replace('USDT', '')
        symbol = symbol.replace('-', '').replace('/', '').strip()

        try:
            # Get orderbook with fallback
            orderbook = await self._get_orderbook_with_fallback(symbol, min(depth * 5, 100))

            if not orderbook:
                return {
                    "success": False,
                    "error": "Unable to get orderbook data (all exchanges failed)",
                    "summary": f"Failed to get {symbol} orderbook (Binance/OKX/Bybit)"
                }

            # Get source exchange
            exchange = orderbook.get("_exchange", "Unknown")

            bids = [[float(p), float(q)] for p, q in orderbook.get("bids", [])[:depth]]
            asks = [[float(p), float(q)] for p, q in orderbook.get("asks", [])[:depth]]

            if not bids or not asks:
                return {
                    "success": False,
                    "error": "Orderbook data is empty",
                    "summary": f"{symbol} orderbook has no data"
                }

            # Calculate total bid/ask volume
            total_bid_volume = sum(q for _, q in bids)
            total_ask_volume = sum(q for _, q in asks)

            # Calculate bid/ask pressure ratio
            pressure_ratio = total_bid_volume / total_ask_volume if total_ask_volume > 0 else 0

            # Find large orders (>3x average)
            avg_bid = total_bid_volume / len(bids)
            avg_ask = total_ask_volume / len(asks)

            large_bids = [[p, q] for p, q in bids if q > avg_bid * 3]
            large_asks = [[p, q] for p, q in asks if q > avg_ask * 3]

            # Calculate support and resistance levels
            bid_prices = [p for p, _ in bids]
            ask_prices = [p for p, _ in asks]

            best_bid = max(bid_prices) if bid_prices else 0
            best_ask = min(ask_prices) if ask_prices else 0
            spread = (best_ask - best_bid) / best_bid * 100 if best_bid > 0 else 0

            # Find price with max volume as key support/resistance
            support_level = max(bids, key=lambda x: x[1])[0] if bids else 0
            resistance_level = max(asks, key=lambda x: x[1])[0] if asks else 0

            summary = f"""【Orderbook Analysis】{symbol}/USDT ({exchange})

📊 Current Quote:
  Best Bid: ${best_bid:,.2f}
  Best Ask: ${best_ask:,.2f}
  Spread: {spread:.4f}%

📈 Depth Stats (Top {depth} levels):
  Total Bid Volume: {total_bid_volume:,.2f} {symbol}
  Total Ask Volume: {total_ask_volume:,.2f} {symbol}
  Bid/Ask Ratio: {pressure_ratio:.2f}

🎯 Key Levels:
  Major Support: ${support_level:,.2f}
  Major Resistance: ${resistance_level:,.2f}

🐋 Large Order Monitor:
  Large Buy Orders: {len(large_bids)}
  Large Sell Orders: {len(large_asks)}

💡 Market Sentiment:
  {"🟢 Bullish (Strong Bids)" if pressure_ratio > 1.2 else "🔴 Bearish (Strong Asks)" if pressure_ratio < 0.8 else "⚪ Neutral (Balanced)"}
  {"⚠️ Large buy order support detected" if large_bids else ""}
  {"⚠️ Large sell order pressure detected" if large_asks else ""}"""

            return {
                "success": True,
                "data": {
                    "symbol": symbol,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "spread_percent": spread,
                    "total_bid_volume": total_bid_volume,
                    "total_ask_volume": total_ask_volume,
                    "pressure_ratio": pressure_ratio,
                    "support_level": support_level,
                    "resistance_level": resistance_level,
                    "large_bids": large_bids,
                    "large_asks": large_asks,
                    "bids": bids[:10],
                    "asks": asks[:10]
                },
                "summary": summary
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"Orderbook analysis failed: {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Coin symbol",
                        "default": "BTC"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Number of depth levels to analyze",
                        "default": 20
                    }
                },
                "required": []
            }
        }


class BlackSwanScannerTool(Tool):
    """
    Black Swan Event Scanner Tool

    Monitor major abnormal events that may affect investments
    """

    def __init__(self, web_search_url: str = "http://web_search_service:8010"):
        super().__init__(
            name="black_swan_scanner",
            description="""Black swan event scanning tool.

Features:
- Major risk event monitoring
- Regulatory policy change tracking
- Industry crisis early warning
- Macroeconomic anomaly detection

Scan types:
- regulatory: Regulatory policies
- market: Market anomalies
- company: Corporate crises
- macro: Macroeconomic events
- all: Comprehensive scan"""
        )
        self.web_search_url = web_search_url

        # Black swan keywords
        self.risk_keywords = {
            "regulatory": ["regulation penalty", "policy tightening", "ban halt", "crackdown", "warning"],
            "market": ["crash collapse", "liquidation", "bank run", "liquidity crisis", "black swan"],
            "company": ["default", "bankruptcy", "executive arrested", "fraud", "data breach"],
            "macro": ["financial crisis", "recession", "currency devaluation", "inflation surge", "geopolitical"]
        }

    async def _search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """Execute web search"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.web_search_url}/search",
                    json={
                        "query": query,
                        "max_results": max_results,
                        "topic": "news",
                        "days": 7
                    }
                )
                response.raise_for_status()
                return response.json().get("results", [])
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return []

    async def execute(
        self,
        target: str = None,
        scan_type: str = "all",
        time_range: str = "week",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Scan for black swan events

        Args:
            target: Target company/industry/coin (optional)
            scan_type: Scan type (regulatory/market/company/macro/all)
            time_range: Time range (day/week/month)

        Returns:
            Black swan event scan results
        """
        try:
            # Determine scan types
            if scan_type == "all":
                types_to_scan = list(self.risk_keywords.keys())
            else:
                types_to_scan = [scan_type] if scan_type in self.risk_keywords else ["regulatory"]

            # Build search tasks
            tasks = []
            for scan_type in types_to_scan:
                for keywords in self.risk_keywords[scan_type]:
                    query = keywords
                    if target:
                        query = f"{target} {keywords}"
                    tasks.append(self._search_web(query, 3))

            # Execute search
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            events = []
            seen_urls = set()

            for result in results:
                if isinstance(result, Exception):
                    continue
                for item in result:
                    url = item.get("url", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    title = item.get("title", "")
                    content = item.get("content", "")

                    # Calculate risk level
                    risk_score = self._calculate_risk_score(title + content)

                    if risk_score > 0:
                        events.append({
                            "title": title,
                            "content": content[:200],
                            "url": url,
                            "date": item.get("published_date", ""),
                            "risk_score": risk_score,
                            "risk_level": self._score_to_level(risk_score)
                        })

            # Sort by risk level
            events.sort(key=lambda x: x["risk_score"], reverse=True)
            events = events[:10]  # Keep top 10

            # Statistics
            high_risk = sum(1 for e in events if e["risk_score"] >= 3)
            medium_risk = sum(1 for e in events if 1 <= e["risk_score"] < 3)

            # Build summary
            time_range_label = {"day": "24 hours", "week": "1 week", "month": "1 month"}.get(time_range, time_range)
            summary = f"""【Black Swan Event Scan】{"Target: " + target if target else "All Markets"}

📊 Scan Scope: {", ".join(types_to_scan)}
📅 Time Range: Last {time_range_label}

⚠️ Risk Summary:
  High Risk Events: {high_risk}
  Medium Risk Events: {medium_risk}
  Total: {len(events)}

🚨 Important Risk Events:
"""
            for i, event in enumerate(events[:5], 1):
                level_icon = "🔴" if event["risk_score"] >= 3 else "🟠" if event["risk_score"] >= 1 else "🟡"
                summary += f"\n{i}. {level_icon} {event['title'][:50]}"
                if event.get("date"):
                    summary += f" ({event['date']})"

            if not events:
                summary += "\n  ✅ No major risk events detected"
            else:
                summary += f"""

💡 Recommendations:
  {"⚠️ High risk events detected, immediate attention required!" if high_risk > 0 else ""}
  {"⚠️ Medium risk events found, continue monitoring" if medium_risk > 0 else ""}
  {"✅ Risk level normal" if high_risk == 0 and medium_risk == 0 else ""}"""

            return {
                "success": True,
                "data": {
                    "target": target,
                    "scan_type": scan_type,
                    "time_range": time_range,
                    "high_risk_count": high_risk,
                    "medium_risk_count": medium_risk,
                    "total_events": len(events),
                    "events": events
                },
                "summary": summary
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"Black swan scan failed: {str(e)}"
            }

    def _calculate_risk_score(self, text: str) -> int:
        """Calculate risk score"""
        score = 0
        high_risk_words = ["crash", "collapse", "bankruptcy", "fraud", "arrested", "liquidation", "crisis", "ban", "halt"]
        medium_risk_words = ["penalty", "decline", "loss", "crackdown", "warning", "tightening"]

        for word in high_risk_words:
            if word.lower() in text.lower():
                score += 2

        for word in medium_risk_words:
            if word.lower() in text.lower():
                score += 1

        return min(score, 5)  # Max 5 points

    def _score_to_level(self, score: int) -> str:
        """Convert score to risk level"""
        if score >= 3:
            return "High Risk"
        elif score >= 1:
            return "Medium Risk"
        else:
            return "Low Risk"

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Scan target (company/industry/coin), leave empty for all markets"
                    },
                    "scan_type": {
                        "type": "string",
                        "description": "Scan type",
                        "enum": ["regulatory", "market", "company", "macro", "all"],
                        "default": "all"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range",
                        "enum": ["day", "week", "month"],
                        "default": "week"
                    }
                },
                "required": []
            }
        }
