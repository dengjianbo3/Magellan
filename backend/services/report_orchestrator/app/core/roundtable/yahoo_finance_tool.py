"""
Yahoo Finance MCP Tool for Financial Data Retrieval
"""
import httpx
import yfinance as yf
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from .tool import Tool


class YahooFinanceTool(Tool):
    """
    Yahoo Finance Data Retrieval Tool

    Provides stock prices, financial statements, company info, market data, etc.
    """

    def __init__(self):
        """Initialize Yahoo Finance Tool"""
        super().__init__(
            name="yahoo_finance",
            description="Get real-time stock prices, historical data, financial statements, company info, market news, etc. Supports major global stock markets."
        )

    async def execute(self, action: str, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        执行 Yahoo Finance 数据获取

        Args:
            action: 操作类型 (price, history, financials, info, news, valuation, dividends, holders)
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
            elif action == "valuation":
                return await self._get_valuation_metrics(ticker, symbol)
            elif action == "dividends":
                return await self._get_dividend_info(ticker, symbol)
            elif action == "holders":
                return await self._get_holders_info(ticker, symbol)
            else:
                return {
                    "success": False,
                    "error": f"未知操作类型: {action}",
                    "summary": f"不支持的操作: {action}。支持的操作: price, history, financials, info, news, valuation, dividends, holders"
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

    async def _get_valuation_metrics(self, ticker, symbol: str) -> Dict[str, Any]:
        """获取全面的估值指标"""
        try:
            info = ticker.info

            # 基础估值指标
            pe_trailing = info.get('trailingPE')
            pe_forward = info.get('forwardPE')
            peg_ratio = info.get('pegRatio')
            pb_ratio = info.get('priceToBook')
            ps_ratio = info.get('priceToSalesTrailing12Months')

            # 企业价值倍数
            ev = info.get('enterpriseValue', 0)
            ebitda = info.get('ebitda', 0)
            revenue = info.get('totalRevenue', 0)
            ev_to_ebitda = ev / ebitda if ev and ebitda else None
            ev_to_revenue = ev / revenue if ev and revenue else None

            # 盈利能力指标
            roe = info.get('returnOnEquity')
            roa = info.get('returnOnAssets')
            profit_margin = info.get('profitMargins')
            operating_margin = info.get('operatingMargins')
            gross_margin = info.get('grossMargins')

            # 成长性指标
            earnings_growth = info.get('earningsGrowth')
            revenue_growth = info.get('revenueGrowth')
            earnings_quarterly_growth = info.get('earningsQuarterlyGrowth')

            # 财务健康指标
            current_ratio = info.get('currentRatio')
            quick_ratio = info.get('quickRatio')
            debt_to_equity = info.get('debtToEquity')
            total_debt = info.get('totalDebt', 0)
            total_cash = info.get('totalCash', 0)

            # 股息指标
            dividend_yield = info.get('dividendYield')
            dividend_rate = info.get('dividendRate')
            payout_ratio = info.get('payoutRatio')

            # 市值和流动性
            market_cap = info.get('marketCap', 0)
            enterprise_value = info.get('enterpriseValue', 0)
            beta = info.get('beta')
            avg_volume = info.get('averageVolume', 0)

            # 自由现金流收益率
            free_cash_flow = info.get('freeCashflow', 0)
            fcf_yield = (free_cash_flow / market_cap * 100) if market_cap and free_cash_flow else None

            # 每股指标
            eps_trailing = info.get('trailingEps')
            eps_forward = info.get('forwardEps')
            book_value_per_share = info.get('bookValue')

            # 构建摘要
            summary = f"""
{symbol} 估值分析报告:

📊 估值倍数:
  - P/E (TTM): {pe_trailing:.2f if pe_trailing else 'N/A'}
  - P/E (Forward): {pe_forward:.2f if pe_forward else 'N/A'}
  - PEG: {peg_ratio:.2f if peg_ratio else 'N/A'}
  - P/B: {pb_ratio:.2f if pb_ratio else 'N/A'}
  - P/S: {ps_ratio:.2f if ps_ratio else 'N/A'}
  - EV/EBITDA: {ev_to_ebitda:.2f if ev_to_ebitda else 'N/A'}
  - EV/Revenue: {ev_to_revenue:.2f if ev_to_revenue else 'N/A'}

💰 盈利能力:
  - ROE: {roe*100:.2f}% if ROE else 'N/A'
  - ROA: {roa*100:.2f}% if roa else 'N/A'
  - 净利率: {profit_margin*100:.2f}% if profit_margin else 'N/A'
  - 毛利率: {gross_margin*100:.2f}% if gross_margin else 'N/A'
  - 营业利润率: {operating_margin*100:.2f}% if operating_margin else 'N/A'

📈 成长性:
  - 营收增长: {revenue_growth*100:.2f}% if revenue_growth else 'N/A'
  - 盈利增长: {earnings_growth*100:.2f}% if earnings_growth else 'N/A'
  - 季度盈利增长: {earnings_quarterly_growth*100:.2f}% if earnings_quarterly_growth else 'N/A'

🏦 财务健康:
  - 流动比率: {current_ratio:.2f if current_ratio else 'N/A'}
  - 速动比率: {quick_ratio:.2f if quick_ratio else 'N/A'}
  - 负债/权益比: {debt_to_equity:.2f if debt_to_equity else 'N/A'}
  - 净现金: ${(total_cash - total_debt):,.0f}

💵 股息与现金流:
  - 股息率: {dividend_yield*100:.2f}% if dividend_yield else 'N/A'
  - 派息率: {payout_ratio*100:.2f}% if payout_ratio else 'N/A'
  - FCF收益率: {fcf_yield:.2f}% if fcf_yield else 'N/A'

📋 每股指标:
  - EPS (TTM): ${eps_trailing:.2f if eps_trailing else 'N/A'}
  - EPS (Forward): ${eps_forward:.2f if eps_forward else 'N/A'}
  - 每股净资产: ${book_value_per_share:.2f if book_value_per_share else 'N/A'}

📊 市场数据:
  - 市值: ${market_cap:,.0f}
  - 企业价值: ${enterprise_value:,.0f}
  - Beta: {beta:.2f if beta else 'N/A'}
"""

            return {
                "success": True,
                "summary": summary.strip(),
                "data": {
                    "symbol": symbol,
                    "valuation_multiples": {
                        "pe_trailing": pe_trailing,
                        "pe_forward": pe_forward,
                        "peg_ratio": peg_ratio,
                        "pb_ratio": pb_ratio,
                        "ps_ratio": ps_ratio,
                        "ev_to_ebitda": ev_to_ebitda,
                        "ev_to_revenue": ev_to_revenue
                    },
                    "profitability": {
                        "roe": roe,
                        "roa": roa,
                        "profit_margin": profit_margin,
                        "operating_margin": operating_margin,
                        "gross_margin": gross_margin
                    },
                    "growth": {
                        "revenue_growth": revenue_growth,
                        "earnings_growth": earnings_growth,
                        "earnings_quarterly_growth": earnings_quarterly_growth
                    },
                    "financial_health": {
                        "current_ratio": current_ratio,
                        "quick_ratio": quick_ratio,
                        "debt_to_equity": debt_to_equity,
                        "total_debt": total_debt,
                        "total_cash": total_cash,
                        "net_cash": total_cash - total_debt
                    },
                    "dividends": {
                        "dividend_yield": dividend_yield,
                        "dividend_rate": dividend_rate,
                        "payout_ratio": payout_ratio
                    },
                    "cash_flow": {
                        "free_cash_flow": free_cash_flow,
                        "fcf_yield": fcf_yield
                    },
                    "per_share": {
                        "eps_trailing": eps_trailing,
                        "eps_forward": eps_forward,
                        "book_value": book_value_per_share
                    },
                    "market_data": {
                        "market_cap": market_cap,
                        "enterprise_value": enterprise_value,
                        "beta": beta,
                        "avg_volume": avg_volume
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取 {symbol} 估值数据失败: {str(e)}"
            }

    async def _get_dividend_info(self, ticker, symbol: str) -> Dict[str, Any]:
        """获取股息信息"""
        try:
            info = ticker.info
            dividends = ticker.dividends

            dividend_yield = info.get('dividendYield')
            dividend_rate = info.get('dividendRate')
            payout_ratio = info.get('payoutRatio')
            ex_dividend_date = info.get('exDividendDate')

            # 获取历史股息
            recent_dividends = []
            if not dividends.empty:
                recent_div = dividends.tail(8)  # 最近8次派息
                for date, amount in recent_div.items():
                    recent_dividends.append({
                        "date": date.strftime('%Y-%m-%d'),
                        "amount": float(amount)
                    })

            # 计算股息增长率
            dividend_growth = None
            if len(recent_dividends) >= 4:
                old_div = sum(d['amount'] for d in recent_dividends[:4])
                new_div = sum(d['amount'] for d in recent_dividends[-4:])
                if old_div > 0:
                    dividend_growth = ((new_div / old_div) - 1) * 100

            summary = f"""
{symbol} 股息分析:

💰 当前股息:
  - 股息率: {dividend_yield*100:.2f}% if dividend_yield else 'N/A'
  - 每股股息: ${dividend_rate:.2f if dividend_rate else 'N/A'}
  - 派息率: {payout_ratio*100:.2f}% if payout_ratio else 'N/A'

📅 历史派息 (最近8次):
"""
            for div in recent_dividends[-8:]:
                summary += f"  - {div['date']}: ${div['amount']:.4f}\n"

            if dividend_growth is not None:
                summary += f"\n📈 年度股息增长率: {dividend_growth:.2f}%"

            return {
                "success": True,
                "summary": summary.strip(),
                "data": {
                    "symbol": symbol,
                    "current": {
                        "yield": dividend_yield,
                        "rate": dividend_rate,
                        "payout_ratio": payout_ratio,
                        "ex_date": ex_dividend_date
                    },
                    "history": recent_dividends,
                    "growth_rate": dividend_growth
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取 {symbol} 股息数据失败: {str(e)}"
            }

    async def _get_holders_info(self, ticker, symbol: str) -> Dict[str, Any]:
        """获取持股人信息"""
        try:
            # 机构持股
            institutional = ticker.institutional_holders
            # 内部人持股
            insiders = ticker.insider_transactions

            info = ticker.info
            insider_pct = info.get('heldPercentInsiders')
            institution_pct = info.get('heldPercentInstitutions')

            summary = f"""
{symbol} 持股分析:

📊 持股比例:
  - 机构持股: {institution_pct*100:.2f}% if institution_pct else 'N/A'
  - 内部人持股: {insider_pct*100:.2f}% if insider_pct else 'N/A'

🏛️ 主要机构持股:
"""
            if institutional is not None and not institutional.empty:
                for _, row in institutional.head(5).iterrows():
                    holder = row.get('Holder', 'Unknown')
                    shares = row.get('Shares', 0)
                    value = row.get('Value', 0)
                    summary += f"  - {holder}: {shares:,.0f}股 (${value:,.0f})\n"
            else:
                summary += "  无机构持股数据\n"

            summary += "\n👔 最近内部人交易:\n"
            if insiders is not None and not insiders.empty:
                for _, row in insiders.head(5).iterrows():
                    insider = row.get('Insider', 'Unknown')
                    trans = row.get('Transaction', 'Unknown')
                    shares = row.get('Shares', 0)
                    summary += f"  - {insider}: {trans} {shares:,.0f}股\n"
            else:
                summary += "  无内部人交易数据\n"

            return {
                "success": True,
                "summary": summary.strip(),
                "data": {
                    "symbol": symbol,
                    "ownership": {
                        "insider_percent": insider_pct,
                        "institution_percent": institution_pct
                    },
                    "institutional_holders": institutional.to_dict('records') if institutional is not None and not institutional.empty else [],
                    "insider_transactions": insiders.to_dict('records') if insiders is not None and not insiders.empty else []
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取 {symbol} 持股数据失败: {str(e)}"
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
                        "description": "操作类型: price(实时价格), history(历史K线), financials(财务报表), info(公司信息), news(新闻), valuation(估值分析), dividends(股息分析), holders(持股分析)",
                        "enum": ["price", "history", "financials", "info", "news", "valuation", "dividends", "holders"]
                    },
                    "symbol": {
                        "type": "string",
                        "description": "股票代码（如 AAPL, TSLA, 0700.HK, BTC-USD）"
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
