"""
Data Fetcher Agent - 股票数据获取Agent
用于公开市场投资的股票数据获取(Yahoo Finance/SEC Edgar)
"""
from typing import Dict, Any, Optional
import httpx
from datetime import datetime, timedelta


class DataFetcherAgent:
    """股票数据获取Agent - 用于公开市场投资"""

    def __init__(
        self,
        yahoo_finance_url: str = "http://yahoo_finance_service:8012",
        sec_edgar_url: str = "http://sec_edgar_service:8013"
    ):
        self.yahoo_finance_url = yahoo_finance_url
        self.sec_edgar_url = sec_edgar_url

    async def fetch(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取股票数据

        Args:
            target: 分析目标,包含:
                - ticker: 股票代码 (如: AAPL, NVDA)
                - exchange: 交易所 (可选,如: NASDAQ, NYSE)
                - asset_type: 资产类型 (默认: stock)

        Returns:
            股票数据结果
        """
        ticker = target.get('ticker', '').upper()
        if not ticker:
            return self._error_result("缺少股票代码 (ticker)")

        # 并行获取多个数据源
        stock_data = await self._fetch_stock_data(ticker)
        financials = await self._fetch_financials(ticker)
        company_info = await self._fetch_company_info(ticker)

        # 合并结果
        return {
            "ticker": ticker,
            "stock_data": stock_data,
            "financials": financials,
            "company_info": company_info,
            "fetched_at": datetime.utcnow().isoformat(),
            "data_sources": self._get_data_sources_status(
                stock_data,
                financials,
                company_info
            )
        }

    async def _fetch_stock_data(self, ticker: str) -> Dict[str, Any]:
        """
        获取股票价格数据 (Yahoo Finance)

        Returns:
            - current_price: 当前价格
            - prev_close: 前收盘价
            - day_high: 日内最高价
            - day_low: 日内最低价
            - volume: 成交量
            - market_cap: 市值
            - historical_data: 历史数据 (最近1年)
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.yahoo_finance_url}/quote/{ticker}"
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "current_price": data.get("regularMarketPrice"),
                        "prev_close": data.get("regularMarketPreviousClose"),
                        "day_high": data.get("regularMarketDayHigh"),
                        "day_low": data.get("regularMarketDayLow"),
                        "volume": data.get("regularMarketVolume"),
                        "market_cap": data.get("marketCap"),
                        "pe_ratio": data.get("trailingPE"),
                        "dividend_yield": data.get("dividendYield"),
                        "52_week_high": data.get("fiftyTwoWeekHigh"),
                        "52_week_low": data.get("fiftyTwoWeekLow"),
                        "source": "yahoo_finance",
                        "success": True
                    }
        except Exception as e:
            print(f"[DataFetcherAgent] Yahoo Finance fetch failed: {e}")

        # Fallback: 返回Mock数据
        return {
            "current_price": None,
            "message": "Yahoo Finance数据获取失败,使用Mock数据",
            "source": "mock",
            "success": False
        }

    async def _fetch_financials(self, ticker: str) -> Dict[str, Any]:
        """
        获取财务数据 (SEC Edgar)

        Returns:
            - revenue: 营收
            - net_income: 净利润
            - total_assets: 总资产
            - total_debt: 总负债
            - cash: 现金及等价物
            - operating_cash_flow: 经营性现金流
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.sec_edgar_url}/financials/{ticker}"
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "revenue": data.get("revenue"),
                        "net_income": data.get("netIncome"),
                        "total_assets": data.get("totalAssets"),
                        "total_debt": data.get("totalDebt"),
                        "cash": data.get("cash"),
                        "operating_cash_flow": data.get("operatingCashFlow"),
                        "gross_margin": data.get("grossMargin"),
                        "ebitda": data.get("ebitda"),
                        "fiscal_year": data.get("fiscalYear"),
                        "source": "sec_edgar",
                        "success": True
                    }
        except Exception as e:
            print(f"[DataFetcherAgent] SEC Edgar fetch failed: {e}")

        # Fallback: 返回Mock数据
        return {
            "revenue": None,
            "message": "SEC Edgar数据获取失败,使用Mock数据",
            "source": "mock",
            "success": False
        }

    async def _fetch_company_info(self, ticker: str) -> Dict[str, Any]:
        """
        获取公司基本信息

        Returns:
            - company_name: 公司名称
            - sector: 所属行业
            - industry: 细分行业
            - description: 公司简介
            - website: 官网
            - employees: 员工数
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.yahoo_finance_url}/info/{ticker}"
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "company_name": data.get("longName"),
                        "sector": data.get("sector"),
                        "industry": data.get("industry"),
                        "description": data.get("longBusinessSummary"),
                        "website": data.get("website"),
                        "employees": data.get("fullTimeEmployees"),
                        "country": data.get("country"),
                        "exchange": data.get("exchange"),
                        "source": "yahoo_finance",
                        "success": True
                    }
        except Exception as e:
            print(f"[DataFetcherAgent] Company info fetch failed: {e}")

        # Fallback: 返回基本Mock数据
        return {
            "company_name": ticker,
            "message": "公司信息获取失败,使用Mock数据",
            "source": "mock",
            "success": False
        }

    def _get_data_sources_status(
        self,
        stock_data: Dict[str, Any],
        financials: Dict[str, Any],
        company_info: Dict[str, Any]
    ) -> Dict[str, bool]:
        """获取数据源状态"""
        return {
            "yahoo_finance": stock_data.get("success", False),
            "sec_edgar": financials.get("success", False),
            "company_info": company_info.get("success", False)
        }

    def _error_result(self, message: str) -> Dict[str, Any]:
        """返回错误结果"""
        return {
            "error": True,
            "message": message,
            "stock_data": {"success": False},
            "financials": {"success": False},
            "company_info": {"success": False}
        }
