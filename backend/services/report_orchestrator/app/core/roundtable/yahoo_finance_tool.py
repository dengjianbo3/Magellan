"""
Yahoo Finance MCP Tool for Financial Data Retrieval
雅虎财经MCP工具，用于获取实时金融数据
"""
import httpx
import yfinance as yf
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from .tool import Tool


class YahooFinanceTool(Tool):
    """
    Yahoo Finance 数据获取工具

    提供股票价格、财务报表、公司信息、市场数据等功能
    """

    def __init__(self):
        """初始化 Yahoo Finance 工具"""
        super().__init__(
            name="yahoo_finance",
            description="获取股票实时价格、历史数据、财务报表、公司信息、市场新闻等。支持全球主要股票市场。"
        )

    async def execute(self, action: str, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        执行 Yahoo Finance 数据获取

        Args:
            action: 操作类型 (price, history, financials, info, news)
            symbol: 股票代码 (如 AAPL, TSLA, 0700.HK)
            **kwargs: 其他参数

        Returns:
            查询结果
        """
        try:
            ticker = yf.Ticker(symbol)

            if action == "price":
                return await self._get_current_price(ticker, symbol)
            elif action == "history":
                period = kwargs.get("period", "1mo")  # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
                return await self._get_price_history(ticker, symbol, period)
            elif action == "financials":
                statement = kwargs.get("statement", "income")  # income, balance, cash
                return await self._get_financials(ticker, symbol, statement)
            elif action == "info":
                return await self._get_company_info(ticker, symbol)
            elif action == "news":
                return await self._get_news(ticker, symbol)
            else:
                return {
                    "success": False,
                    "error": f"未知操作类型: {action}",
                    "summary": f"不支持的操作: {action}。支持的操作: price, history, financials, info, news"
                }

        except Exception as e:
            print(f"[YahooFinanceTool] Error for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取 {symbol} 的 {action} 数据时出错: {str(e)}"
            }

    async def _get_current_price(self, ticker, symbol: str) -> Dict[str, Any]:
        """获取当前股价"""
        try:
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close = info.get('previousClose')

            if current_price is None:
                return {
                    "success": False,
                    "summary": f"无法获取 {symbol} 的当前价格，可能是股票代码错误或市场未开盘"
                }

            change = current_price - previous_close if previous_close else 0
            change_percent = (change / previous_close * 100) if previous_close else 0

            summary = (
                f"{symbol} 当前价格信息:\n"
                f"  - 当前价格: ${current_price:.2f}\n"
                f"  - 昨收价格: ${previous_close:.2f}\n"
                f"  - 涨跌额: ${change:.2f} ({change_percent:+.2f}%)\n"
                f"  - 52周最高: ${info.get('fiftyTwoWeekHigh', 'N/A')}\n"
                f"  - 52周最低: ${info.get('fiftyTwoWeekLow', 'N/A')}\n"
                f"  - 市值: ${info.get('marketCap', 0):,.0f}"
            )

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "symbol": symbol,
                    "current_price": current_price,
                    "previous_close": previous_close,
                    "change": change,
                    "change_percent": change_percent,
                    "fifty_two_week_high": info.get('fiftyTwoWeekHigh'),
                    "fifty_two_week_low": info.get('fiftyTwoWeekLow'),
                    "market_cap": info.get('marketCap')
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取 {symbol} 价格失败: {str(e)}"
            }

    async def _get_price_history(self, ticker, symbol: str, period: str) -> Dict[str, Any]:
        """获取历史价格"""
        try:
            hist = ticker.history(period=period)

            if hist.empty:
                return {
                    "success": False,
                    "summary": f"没有找到 {symbol} 在 {period} 期间的历史数据"
                }

            latest = hist.iloc[-1]
            earliest = hist.iloc[0]

            price_change = latest['Close'] - earliest['Close']
            price_change_pct = (price_change / earliest['Close'] * 100)

            summary = (
                f"{symbol} {period} 历史数据:\n"
                f"  - 期间: {earliest.name.strftime('%Y-%m-%d')} 至 {latest.name.strftime('%Y-%m-%d')}\n"
                f"  - 起始价: ${earliest['Close']:.2f}\n"
                f"  - 最新价: ${latest['Close']:.2f}\n"
                f"  - 涨跌: ${price_change:.2f} ({price_change_pct:+.2f}%)\n"
                f"  - 期间最高: ${hist['High'].max():.2f}\n"
                f"  - 期间最低: ${hist['Low'].min():.2f}\n"
                f"  - 平均成交量: {hist['Volume'].mean():,.0f}"
            )

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "symbol": symbol,
                    "period": period,
                    "start_date": earliest.name.strftime('%Y-%m-%d'),
                    "end_date": latest.name.strftime('%Y-%m-%d'),
                    "start_price": float(earliest['Close']),
                    "end_price": float(latest['Close']),
                    "change": float(price_change),
                    "change_percent": float(price_change_pct),
                    "high": float(hist['High'].max()),
                    "low": float(hist['Low'].min()),
                    "avg_volume": float(hist['Volume'].mean())
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取 {symbol} 历史数据失败: {str(e)}"
            }

    async def _get_financials(self, ticker, symbol: str, statement: str) -> Dict[str, Any]:
        """获取财务报表"""
        try:
            if statement == "income":
                df = ticker.income_stmt
                stmt_name = "利润表"
            elif statement == "balance":
                df = ticker.balance_sheet
                stmt_name = "资产负债表"
            elif statement == "cash":
                df = ticker.cashflow
                stmt_name = "现金流量表"
            else:
                return {
                    "success": False,
                    "summary": f"不支持的财务报表类型: {statement}。支持: income, balance, cash"
                }

            if df.empty:
                return {
                    "success": False,
                    "summary": f"{symbol} 没有可用的{stmt_name}数据"
                }

            # 获取最新一期数据
            latest_period = df.columns[0]
            latest_data = df[latest_period]

            # 构建摘要
            summary_parts = [f"{symbol} 最新{stmt_name} ({latest_period.strftime('%Y-%m-%d')}):\n"]

            # 根据报表类型显示关键指标
            if statement == "income":
                revenue = latest_data.get('Total Revenue', 0)
                net_income = latest_data.get('Net Income', 0)
                gross_profit = latest_data.get('Gross Profit', 0)
                operating_income = latest_data.get('Operating Income', 0)

                summary_parts.append(
                    f"  - 总收入: ${revenue:,.0f}\n"
                    f"  - 毛利润: ${gross_profit:,.0f}\n"
                    f"  - 营业利润: ${operating_income:,.0f}\n"
                    f"  - 净利润: ${net_income:,.0f}\n"
                )

            elif statement == "balance":
                total_assets = latest_data.get('Total Assets', 0)
                total_liabilities = latest_data.get('Total Liabilities Net Minority Interest', 0)
                stockholder_equity = latest_data.get('Stockholders Equity', 0)

                summary_parts.append(
                    f"  - 总资产: ${total_assets:,.0f}\n"
                    f"  - 总负债: ${total_liabilities:,.0f}\n"
                    f"  - 股东权益: ${stockholder_equity:,.0f}\n"
                )

            elif statement == "cash":
                operating_cf = latest_data.get('Operating Cash Flow', 0)
                investing_cf = latest_data.get('Investing Cash Flow', 0)
                financing_cf = latest_data.get('Financing Cash Flow', 0)

                summary_parts.append(
                    f"  - 经营活动现金流: ${operating_cf:,.0f}\n"
                    f"  - 投资活动现金流: ${investing_cf:,.0f}\n"
                    f"  - 筹资活动现金流: ${financing_cf:,.0f}\n"
                )

            return {
                "success": True,
                "summary": "".join(summary_parts),
                "data": {
                    "symbol": symbol,
                    "statement_type": statement,
                    "period": latest_period.strftime('%Y-%m-%d'),
                    "data": latest_data.to_dict()
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取 {symbol} 财务数据失败: {str(e)}"
            }

    async def _get_company_info(self, ticker, symbol: str) -> Dict[str, Any]:
        """获取公司基本信息"""
        try:
            info = ticker.info

            summary = (
                f"{symbol} 公司信息:\n"
                f"  - 公司全称: {info.get('longName', 'N/A')}\n"
                f"  - 行业: {info.get('industry', 'N/A')}\n"
                f"  - 板块: {info.get('sector', 'N/A')}\n"
                f"  - 国家: {info.get('country', 'N/A')}\n"
                f"  - 网站: {info.get('website', 'N/A')}\n"
                f"  - 员工数: {info.get('fullTimeEmployees', 'N/A'):,}\n"
                f"  - 简介: {info.get('longBusinessSummary', 'N/A')[:200]}..."
            )

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "symbol": symbol,
                    "name": info.get('longName'),
                    "industry": info.get('industry'),
                    "sector": info.get('sector'),
                    "country": info.get('country'),
                    "website": info.get('website'),
                    "employees": info.get('fullTimeEmployees'),
                    "description": info.get('longBusinessSummary')
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取 {symbol} 公司信息失败: {str(e)}"
            }

    async def _get_news(self, ticker, symbol: str) -> Dict[str, Any]:
        """获取公司新闻"""
        try:
            news = ticker.news

            if not news:
                return {
                    "success": True,
                    "summary": f"暂无 {symbol} 的最新新闻",
                    "news": []
                }

            # 限制显示前5条新闻
            top_news = news[:5]

            summary_parts = [f"{symbol} 最新新闻 (共 {len(top_news)} 条):\n"]
            for i, article in enumerate(top_news, 1):
                published_time = datetime.fromtimestamp(article.get('providerPublishTime', 0))
                summary_parts.append(
                    f"\n{i}. {article.get('title', 'N/A')}\n"
                    f"   发布时间: {published_time.strftime('%Y-%m-%d %H:%M')}\n"
                    f"   来源: {article.get('publisher', 'N/A')}\n"
                    f"   链接: {article.get('link', 'N/A')}"
                )

            return {
                "success": True,
                "summary": "".join(summary_parts),
                "news": top_news
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取 {symbol} 新闻失败: {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        """返回工具的 Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "操作类型",
                        "enum": ["price", "history", "financials", "info", "news"]
                    },
                    "symbol": {
                        "type": "string",
                        "description": "股票代码（如 AAPL, TSLA, 0700.HK）"
                    },
                    "period": {
                        "type": "string",
                        "description": "历史数据周期（仅用于history操作）",
                        "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
                        "default": "1mo"
                    },
                    "statement": {
                        "type": "string",
                        "description": "财务报表类型（仅用于financials操作）",
                        "enum": ["income", "balance", "cash"],
                        "default": "income"
                    }
                },
                "required": ["action", "symbol"]
            }
        }
