"""
Phase 4 高级工具 (免费替代方案)
为圆桌讨论专家提供的高级分析工具
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
    人员背景调查工具 (LinkedIn免费替代方案)

    通过公开信息搜索、GitHub分析、新闻检索获取人员背景
    """

    def __init__(self, web_search_url: str = "http://web_search_service:8010"):
        super().__init__(
            name="person_background",
            description="""人员背景调查工具。

功能:
- 公开履历搜索 (教育、工作经历)
- GitHub技术贡献分析
- 媒体报道和公开演讲
- 创业/投资历史
- 社交影响力评估

使用场景:
- 创始人背景调查
- 核心团队评估
- 关键人风险分析

注: 使用公开信息源，不包含LinkedIn私密数据"""
        )
        self.web_search_url = web_search_url
        self.github_api = "https://api.github.com"

    async def _search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """执行网络搜索"""
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
        """搜索GitHub用户"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # 搜索用户
                response = await client.get(
                    f"{self.github_api}/search/users",
                    params={"q": name, "per_page": 3}
                )
                if response.status_code != 200:
                    return {"found": False}

                data = response.json()
                if data.get("total_count", 0) == 0:
                    return {"found": False}

                # 获取第一个匹配用户的详细信息
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
        执行人员背景调查

        Args:
            name: 人员姓名
            company: 所属公司（可选，提高搜索准确性）
            role: 职位（可选）

        Returns:
            背景调查结果
        """
        if not name:
            return {
                "success": False,
                "error": "请提供人员姓名",
                "summary": "人员背景调查需要指定姓名"
            }

        try:
            # 构建搜索查询
            base_query = name
            if company:
                base_query += f" {company}"
            if role:
                base_query += f" {role}"

            # 并行执行多个搜索
            tasks = [
                self._search_web(f"{base_query} 履历 背景 教育", 5),
                self._search_web(f"{base_query} 创业 融资 投资", 3),
                self._search_web(f"{base_query} 演讲 采访 报道", 3),
                self._search_github(name)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            background_results = results[0] if not isinstance(results[0], Exception) else []
            startup_results = results[1] if not isinstance(results[1], Exception) else []
            media_results = results[2] if not isinstance(results[2], Exception) else []
            github_info = results[3] if not isinstance(results[3], Exception) else {"found": False}

            # 提取关键信息
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

            # 解析背景信息
            all_content = ""
            for result in background_results + startup_results:
                all_content += result.get("content", "") + "\n"
                profile["sources"].append({
                    "title": result.get("title", ""),
                    "url": result.get("url", "")
                })

            # 提取教育背景
            edu_patterns = [
                r"毕业于([^\s,，。]+(?:大学|学院|University|College))",
                r"([^\s,，。]+(?:大学|学院|University|College))\s*(?:毕业|学士|硕士|博士|MBA|PhD)",
                r"(?:本科|硕士|博士|MBA)\s*[：:]\s*([^\s,，。]+)"
            ]
            for pattern in edu_patterns:
                matches = re.findall(pattern, all_content)
                profile["education"].extend([m for m in matches if m not in profile["education"]])

            # 提取创业历史
            startup_patterns = [
                r"创办(?:了)?([^\s,，。]+(?:公司|科技|网络))",
                r"(?:联合)?创始人[^\s]*([^\s,，。]+(?:公司|科技|网络))",
                r"创立(?:了)?([^\s,，。]+)"
            ]
            for pattern in startup_patterns:
                matches = re.findall(pattern, all_content)
                profile["startup_history"].extend([m for m in matches if m not in profile["startup_history"] and len(m) > 2])

            # 添加媒体报道
            for result in media_results[:3]:
                profile["media_coverage"].append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "date": result.get("published_date", "")
                })

            # 构建摘要
            summary = f"""【人员背景调查】{name}
{"公司: " + company if company else ""}
{"职位: " + role if role else ""}

📚 教育背景:
{chr(10).join(f"  • {e}" for e in profile["education"][:3]) if profile["education"] else "  暂未找到公开教育信息"}

🏢 创业/工作经历:
{chr(10).join(f"  • {s}" for s in profile["startup_history"][:3]) if profile["startup_history"] else "  暂未找到公开创业信息"}

💻 GitHub (技术背景):
{self._format_github(github_info)}

📰 媒体报道:
{chr(10).join(f"  • {m['title'][:40]}" for m in profile["media_coverage"][:3]) if profile["media_coverage"] else "  暂未找到相关报道"}

📋 信息来源: {len(profile["sources"])}个公开来源"""

            return {
                "success": True,
                "data": profile,
                "summary": summary
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"人员背景调查失败: {str(e)}"
            }

    def _format_github(self, info: Dict) -> str:
        """格式化GitHub信息"""
        if not info.get("found"):
            return "  未找到匹配的GitHub账号"
        return f"""  用户名: {info.get('username', 'N/A')}
  公开仓库: {info.get('public_repos', 0)}个
  关注者: {info.get('followers', 0)}
  简介: {info.get('bio', 'N/A')[:50] if info.get('bio') else 'N/A'}"""

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "人员姓名"
                    },
                    "company": {
                        "type": "string",
                        "description": "所属公司（可选，提高搜索准确性）"
                    },
                    "role": {
                        "type": "string",
                        "description": "职位（可选）"
                    }
                },
                "required": ["name"]
            }
        }


class RegulationSearchTool(Tool):
    """
    法规检索工具 (使用政府公开数据)

    通过搜索政府法规网站获取法律法规信息
    """

    def __init__(self, web_search_url: str = "http://web_search_service:8010"):
        super().__init__(
            name="regulation_search",
            description="""法规检索工具。

功能:
- 法律法规搜索
- 部门规章查询
- 司法解释检索
- 监管政策追踪

支持领域:
- 公司法/证券法
- 金融监管
- 数据安全/隐私
- 行业特定法规

数据源: 政府公开法规数据库 + 官方网站"""
        )
        self.web_search_url = web_search_url

        # 政府法规网站域名
        self.gov_domains = [
            "gov.cn",
            "moj.gov.cn",      # 司法部
            "pbc.gov.cn",      # 央行
            "csrc.gov.cn",     # 证监会
            "cbirc.gov.cn",    # 银保监会
            "samr.gov.cn",     # 市场监管总局
            "miit.gov.cn",     # 工信部
            "cac.gov.cn"       # 网信办
        ]

    async def _search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """执行网络搜索"""
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
        执行法规检索

        Args:
            keywords: 搜索关键词
            law_type: 法规类型 (law/regulation/interpretation/policy/all)
            industry: 行业领域 (fintech/healthcare/ecommerce/ai等)

        Returns:
            法规检索结果
        """
        if not keywords:
            return {
                "success": False,
                "error": "请提供搜索关键词",
                "summary": "法规检索需要指定关键词"
            }

        try:
            # 构建搜索查询
            type_keywords = {
                "law": "法律 法",
                "regulation": "条例 规定 办法",
                "interpretation": "司法解释 批复",
                "policy": "政策 通知 意见",
                "all": ""
            }

            industry_keywords = {
                "fintech": "金融 支付 借贷",
                "healthcare": "医疗 药品 医疗器械",
                "ecommerce": "电子商务 网络交易",
                "ai": "人工智能 算法 数据",
                "crypto": "虚拟货币 数字资产",
                "education": "教育 培训"
            }

            base_query = keywords
            if law_type != "all" and law_type in type_keywords:
                base_query += f" {type_keywords[law_type]}"
            if industry and industry in industry_keywords:
                base_query += f" {industry_keywords[industry]}"

            # 搜索政府网站
            gov_query = f"{base_query} site:gov.cn"
            general_query = f"{base_query} 法规 法律"

            tasks = [
                self._search_web(gov_query, 5),
                self._search_web(general_query, 5)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            gov_results = results[0] if not isinstance(results[0], Exception) else []
            general_results = results[1] if not isinstance(results[1], Exception) else []

            # 合并结果，优先政府来源
            regulations = []
            seen_urls = set()

            # 处理政府来源
            for result in gov_results:
                url = result.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    regulations.append({
                        "title": result.get("title", ""),
                        "content": result.get("content", "")[:300],
                        "url": url,
                        "source_type": "政府官方",
                        "date": result.get("published_date", "")
                    })

            # 处理一般来源（非政府）
            for result in general_results:
                url = result.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    is_gov = any(domain in url for domain in self.gov_domains)
                    regulations.append({
                        "title": result.get("title", ""),
                        "content": result.get("content", "")[:300],
                        "url": url,
                        "source_type": "政府官方" if is_gov else "其他来源",
                        "date": result.get("published_date", "")
                    })

            # 分类统计
            gov_count = sum(1 for r in regulations if r["source_type"] == "政府官方")

            summary = f"""【法规检索结果】关键词: {keywords}

📋 检索类型: {law_type}
🏭 行业领域: {industry or "通用"}
📊 找到结果: {len(regulations)}条 (官方来源: {gov_count}条)

📜 相关法规:
"""
            for i, reg in enumerate(regulations[:5], 1):
                summary += f"\n{i}. [{reg['source_type']}] {reg['title'][:50]}"
                if reg.get("date"):
                    summary += f" ({reg['date']})"

            summary += f"""

⚠️ 提示:
- 建议核实法规的最新版本和生效状态
- 复杂法律问题请咨询专业律师
- 政府官方来源更具权威性"""

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
                "summary": f"法规检索失败: {str(e)}"
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
                        "description": "搜索关键词，如 '个人信息保护', '支付牌照'"
                    },
                    "law_type": {
                        "type": "string",
                        "description": "法规类型",
                        "enum": ["law", "regulation", "interpretation", "policy", "all"],
                        "default": "all"
                    },
                    "industry": {
                        "type": "string",
                        "description": "行业领域",
                        "enum": ["fintech", "healthcare", "ecommerce", "ai", "crypto", "education"]
                    }
                },
                "required": ["keywords"]
            }
        }


class MultiExchangeTool(Tool):
    """
    多交易所数据工具

    获取多个加密货币交易所的行情和数据
    """

    def __init__(self):
        super().__init__(
            name="multi_exchange_data",
            description="""多交易所加密货币数据工具。

功能:
- 多交易所价格对比
- 价差套利机会发现
- 成交量分布分析
- 资金费率对比

支持交易所:
- Binance
- OKX
- Coinbase
- Bybit

支持交易对: BTC, ETH 等主流币种"""
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
        """获取Binance价格"""
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
        """获取OKX价格"""
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
        """获取Bybit价格"""
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
        获取多交易所数据

        Args:
            symbol: 币种 (BTC/ETH/等)
            exchanges: 指定交易所列表（可选）

        Returns:
            多交易所数据对比
        """
        symbol = symbol.upper()
        if exchanges is None:
            exchanges = ["binance", "okx", "bybit"]

        try:
            # 并行获取各交易所数据
            tasks = []
            if "binance" in exchanges:
                tasks.append(self._get_binance_price(symbol))
            if "okx" in exchanges:
                tasks.append(self._get_okx_price(symbol))
            if "bybit" in exchanges:
                tasks.append(self._get_bybit_price(symbol))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 过滤有效结果
            valid_results = [r for r in results if r and not isinstance(r, Exception)]

            if not valid_results:
                return {
                    "success": False,
                    "error": "无法获取任何交易所数据",
                    "summary": f"获取 {symbol} 数据失败，请检查币种代码是否正确"
                }

            # 计算价差
            prices = [r["price"] for r in valid_results if r["price"] > 0]
            if prices:
                max_price = max(prices)
                min_price = min(prices)
                spread = (max_price - min_price) / min_price * 100 if min_price > 0 else 0
                avg_price = sum(prices) / len(prices)
            else:
                spread = 0
                avg_price = 0

            # 构建摘要
            summary = f"""【多交易所数据】{symbol}/USDT

📊 价格对比:
"""
            for r in valid_results:
                price_diff = ((r["price"] - avg_price) / avg_price * 100) if avg_price > 0 else 0
                summary += f"  {r['exchange']:10} ${r['price']:,.2f} ({price_diff:+.2f}%)\n"

            summary += f"""
📈 价差分析:
  最高价: ${max_price:,.2f}
  最低价: ${min_price:,.2f}
  价差: {spread:.3f}%
  {"⚠️ 存在套利空间" if spread > 0.5 else "✅ 价差正常"}

📊 24h成交量:
"""
            for r in valid_results:
                summary += f"  {r['exchange']:10} {r['volume_24h']:,.0f} {symbol}\n"

            summary += f"""
📉 24h涨跌:
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
                "summary": f"多交易所数据获取失败: {str(e)}"
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
                        "description": "币种代码，如 BTC, ETH, SOL",
                        "default": "BTC"
                    },
                    "exchanges": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "指定交易所列表 (binance/okx/bybit)"
                    }
                },
                "required": []
            }
        }


class OrderbookAnalyzerTool(Tool):
    """
    订单簿深度分析工具

    分析交易所订单簿数据，识别支撑/阻力位
    """

    def __init__(self):
        super().__init__(
            name="orderbook_analyzer",
            description="""订单簿深度分析工具。

功能:
- 买卖盘深度分析
- 支撑位/阻力位识别
- 大单监控
- 买卖压力比较

使用场景:
- 短期交易决策
- 市场情绪分析
- 流动性评估"""
        )

    async def _get_binance_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """获取Binance订单簿"""
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
        """获取OKX订单簿 (备用)"""
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
        """获取Bybit订单簿 (备用)"""
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
        """获取订单簿 (带fallback)"""
        # 1. 尝试 Binance
        orderbook = await self._get_binance_orderbook(symbol, limit)
        if orderbook:
            return orderbook

        logger.info(f"Binance failed for {symbol}, trying OKX...")

        # 2. 尝试 OKX
        orderbook = await self._get_okx_orderbook(symbol, limit)
        if orderbook:
            return orderbook

        logger.info(f"OKX failed for {symbol}, trying Bybit...")

        # 3. 尝试 Bybit
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
        分析订单簿

        Args:
            symbol: 币种
            depth: 深度层数

        Returns:
            订单簿分析结果
        """
        symbol = symbol.upper()

        try:
            # 使用带fallback的方法获取订单簿
            orderbook = await self._get_orderbook_with_fallback(symbol, min(depth * 5, 100))

            if not orderbook:
                return {
                    "success": False,
                    "error": "无法获取订单簿数据 (所有交易所均失败)",
                    "summary": f"获取 {symbol} 订单簿失败 (Binance/OKX/Bybit)"
                }

            # 获取数据来源交易所
            exchange = orderbook.get("_exchange", "Unknown")

            bids = [[float(p), float(q)] for p, q in orderbook.get("bids", [])[:depth]]
            asks = [[float(p), float(q)] for p, q in orderbook.get("asks", [])[:depth]]

            if not bids or not asks:
                return {
                    "success": False,
                    "error": "订单簿数据为空",
                    "summary": f"{symbol} 订单簿无数据"
                }

            # 计算买卖盘总量
            total_bid_volume = sum(q for _, q in bids)
            total_ask_volume = sum(q for _, q in asks)

            # 计算买卖压力比
            pressure_ratio = total_bid_volume / total_ask_volume if total_ask_volume > 0 else 0

            # 找出大单 (超过平均值3倍)
            avg_bid = total_bid_volume / len(bids)
            avg_ask = total_ask_volume / len(asks)

            large_bids = [[p, q] for p, q in bids if q > avg_bid * 3]
            large_asks = [[p, q] for p, q in asks if q > avg_ask * 3]

            # 计算支撑位和阻力位
            bid_prices = [p for p, _ in bids]
            ask_prices = [p for p, _ in asks]

            best_bid = max(bid_prices) if bid_prices else 0
            best_ask = min(ask_prices) if ask_prices else 0
            spread = (best_ask - best_bid) / best_bid * 100 if best_bid > 0 else 0

            # 找到量最大的价格作为关键支撑/阻力
            support_level = max(bids, key=lambda x: x[1])[0] if bids else 0
            resistance_level = max(asks, key=lambda x: x[1])[0] if asks else 0

            summary = f"""【订单簿分析】{symbol}/USDT ({exchange})

📊 当前报价:
  买一: ${best_bid:,.2f}
  卖一: ${best_ask:,.2f}
  价差: {spread:.4f}%

📈 深度统计 (前{depth}档):
  买盘总量: {total_bid_volume:,.2f} {symbol}
  卖盘总量: {total_ask_volume:,.2f} {symbol}
  买卖比: {pressure_ratio:.2f}

🎯 关键价位:
  主要支撑: ${support_level:,.2f}
  主要阻力: ${resistance_level:,.2f}

🐋 大单监控:
  大买单: {len(large_bids)}个
  大卖单: {len(large_asks)}个

💡 市场情绪:
  {"🟢 买盘强势" if pressure_ratio > 1.2 else "🔴 卖盘强势" if pressure_ratio < 0.8 else "⚪ 买卖均衡"}
  {"⚠️ 发现大买单支撑" if large_bids else ""}
  {"⚠️ 发现大卖单压力" if large_asks else ""}"""

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
                "summary": f"订单簿分析失败: {str(e)}"
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
                        "description": "币种代码",
                        "default": "BTC"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "分析深度层数",
                        "default": 20
                    }
                },
                "required": []
            }
        }


class BlackSwanScannerTool(Tool):
    """
    黑天鹅事件扫描工具

    监控可能影响投资的重大异常事件
    """

    def __init__(self, web_search_url: str = "http://web_search_service:8010"):
        super().__init__(
            name="black_swan_scanner",
            description="""黑天鹅事件扫描工具。

功能:
- 重大风险事件监控
- 监管政策突变追踪
- 行业危机预警
- 宏观经济异常检测

扫描类型:
- regulatory: 监管政策
- market: 市场异常
- company: 企业危机
- macro: 宏观经济
- all: 全面扫描"""
        )
        self.web_search_url = web_search_url

        # 黑天鹅关键词
        self.risk_keywords = {
            "regulatory": ["监管 处罚", "政策 收紧", "禁止 叫停", "整顿 清理", "约谈 警告"],
            "market": ["暴跌 崩盘", "爆仓 清算", "挤兑 跑路", "流动性危机", "黑天鹅"],
            "company": ["暴雷 违约", "破产 清算", "高管 被查", "财务造假", "数据泄露"],
            "macro": ["金融危机", "经济衰退", "货币贬值", "通胀飙升", "地缘冲突"]
        }

    async def _search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """执行网络搜索"""
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
        扫描黑天鹅事件

        Args:
            target: 目标公司/行业/币种（可选）
            scan_type: 扫描类型 (regulatory/market/company/macro/all)
            time_range: 时间范围 (day/week/month)

        Returns:
            黑天鹅事件扫描结果
        """
        try:
            # 确定扫描类型
            if scan_type == "all":
                types_to_scan = list(self.risk_keywords.keys())
            else:
                types_to_scan = [scan_type] if scan_type in self.risk_keywords else ["regulatory"]

            # 构建搜索任务
            tasks = []
            for scan_type in types_to_scan:
                for keywords in self.risk_keywords[scan_type]:
                    query = keywords
                    if target:
                        query = f"{target} {keywords}"
                    tasks.append(self._search_web(query, 3))

            # 执行搜索
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
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

                    # 计算风险等级
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

            # 按风险等级排序
            events.sort(key=lambda x: x["risk_score"], reverse=True)
            events = events[:10]  # 保留前10条

            # 统计
            high_risk = sum(1 for e in events if e["risk_score"] >= 3)
            medium_risk = sum(1 for e in events if 1 <= e["risk_score"] < 3)

            # 构建摘要
            time_range_label = {"day": "24小时", "week": "一周", "month": "一个月"}.get(time_range, time_range)
            summary = f"""【黑天鹅事件扫描】{"目标: " + target if target else "全市场"}

📊 扫描范围: {", ".join(types_to_scan)}
📅 时间范围: 最近{time_range_label}

⚠️ 风险统计:
  高风险事件: {high_risk}条
  中风险事件: {medium_risk}条
  总计: {len(events)}条

🚨 重要风险事件:
"""
            for i, event in enumerate(events[:5], 1):
                level_icon = "🔴" if event["risk_score"] >= 3 else "🟠" if event["risk_score"] >= 1 else "🟡"
                summary += f"\n{i}. {level_icon} {event['title'][:50]}"
                if event.get("date"):
                    summary += f" ({event['date']})"

            if not events:
                summary += "\n  ✅ 暂未发现重大风险事件"
            else:
                summary += f"""

💡 建议:
  {"⚠️ 发现高风险事件，建议立即关注!" if high_risk > 0 else ""}
  {"⚠️ 存在中风险事件，建议持续监控" if medium_risk > 0 else ""}
  {"✅ 风险水平正常" if high_risk == 0 and medium_risk == 0 else ""}"""

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
                "summary": f"黑天鹅扫描失败: {str(e)}"
            }

    def _calculate_risk_score(self, text: str) -> int:
        """计算风险分数"""
        score = 0
        high_risk_words = ["暴雷", "崩盘", "破产", "跑路", "被查", "爆仓", "危机", "禁止", "叫停"]
        medium_risk_words = ["处罚", "下跌", "亏损", "整顿", "约谈", "警告", "收紧"]

        for word in high_risk_words:
            if word in text:
                score += 2

        for word in medium_risk_words:
            if word in text:
                score += 1

        return min(score, 5)  # 最高5分

    def _score_to_level(self, score: int) -> str:
        """分数转风险等级"""
        if score >= 3:
            return "高风险"
        elif score >= 1:
            return "中风险"
        else:
            return "低风险"

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "扫描目标（公司/行业/币种），不指定则全市场扫描"
                    },
                    "scan_type": {
                        "type": "string",
                        "description": "扫描类型",
                        "enum": ["regulatory", "market", "company", "macro", "all"],
                        "default": "all"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "时间范围",
                        "enum": ["day", "week", "month"],
                        "default": "week"
                    }
                },
                "required": []
            }
        }
