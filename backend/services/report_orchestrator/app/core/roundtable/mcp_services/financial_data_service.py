"""
金融数据 MCP 服务
提供统一的金融数据访问接口，聚合多个数据源
"""
import os
import re
import httpx
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Market(Enum):
    """市场类型"""
    CN_A = "cn_a"      # A股
    CN_HK = "cn_hk"    # 港股
    US = "us"          # 美股
    CRYPTO = "crypto"  # 加密货币


@dataclass
class StockQuote:
    """股票报价"""
    symbol: str
    name: str
    market: Market
    price: float
    change: float
    change_percent: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    market_cap: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    timestamp: str = ""


class FinancialDataService:
    """
    金融数据服务

    聚合多个数据源，提供统一接口:
    - A股: 东方财富/新浪财经
    - 港股: 东方财富
    - 美股: Yahoo Finance
    """

    def __init__(self):
        self.timeout = 30
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 60  # 缓存60秒

    def _get_cache_key(self, method: str, **params) -> str:
        """生成缓存键"""
        param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{method}:{param_str}"

    def _get_cached(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self._cache:
            data, expire_time = self._cache[key]
            if datetime.now().timestamp() < expire_time:
                return data
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any):
        """设置缓存"""
        expire_time = datetime.now().timestamp() + self._cache_ttl
        self._cache[key] = (data, expire_time)

    def _detect_market(self, symbol: str) -> Market:
        """检测股票市场"""
        symbol = symbol.upper()

        # A股: 6位数字
        if re.match(r'^\d{6}$', symbol):
            if symbol.startswith(('60', '68')):
                return Market.CN_A  # 上海
            elif symbol.startswith(('00', '30')):
                return Market.CN_A  # 深圳
            elif symbol.startswith(('8', '4')):
                return Market.CN_A  # 北交所/新三板

        # 港股: 5位数字或以0开头
        if re.match(r'^\d{5}$', symbol) or re.match(r'^0\d{4}$', symbol):
            return Market.CN_HK

        # 美股: 字母
        if re.match(r'^[A-Z]+$', symbol):
            return Market.US

        # 带后缀
        if symbol.endswith('.SH') or symbol.endswith('.SZ'):
            return Market.CN_A
        if symbol.endswith('.HK'):
            return Market.CN_HK

        return Market.CN_A  # 默认A股

    async def get_quote(self, symbol: str, market: str = None) -> Dict[str, Any]:
        """
        获取股票实时行情

        Args:
            symbol: 股票代码
            market: 市场 (cn_a/cn_hk/us)，不指定则自动检测

        Returns:
            行情数据
        """
        cache_key = self._get_cache_key("quote", symbol=symbol, market=market)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        detected_market = Market(market) if market else self._detect_market(symbol)

        try:
            if detected_market == Market.CN_A:
                result = await self._get_china_a_quote(symbol)
            elif detected_market == Market.CN_HK:
                result = await self._get_hk_quote(symbol)
            elif detected_market == Market.US:
                result = await self._get_us_quote(symbol)
            else:
                result = {"success": False, "error": f"Unsupported market: {detected_market}"}

            if result.get("success"):
                self._set_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取{symbol}行情失败: {str(e)}"
            }

    async def _get_china_a_quote(self, symbol: str) -> Dict[str, Any]:
        """获取A股行情（东方财富）"""
        # 确定市场代码
        clean_symbol = symbol.replace('.SH', '').replace('.SZ', '')
        if clean_symbol.startswith(('60', '68')):
            market_code = "1"  # 上海
        else:
            market_code = "0"  # 深圳

        url = f"https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": f"{market_code}.{clean_symbol}",
            "fields": "f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f60,f116,f117,f162,f167,f170,f171",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("rc") != 0 or not data.get("data"):
            return {
                "success": False,
                "error": "No data returned",
                "summary": f"未找到股票 {symbol} 的数据"
            }

        d = data["data"]
        name = d.get("f58", "")
        price = d.get("f43", 0) / 100 if d.get("f43") else 0
        prev_close = d.get("f60", 0) / 100 if d.get("f60") else 0
        change = price - prev_close
        change_pct = d.get("f170", 0) / 100 if d.get("f170") else 0

        return {
            "success": True,
            "data": {
                "symbol": clean_symbol,
                "name": name,
                "market": "A股",
                "price": price,
                "change": round(change, 2),
                "change_percent": change_pct,
                "open": d.get("f46", 0) / 100 if d.get("f46") else 0,
                "high": d.get("f44", 0) / 100 if d.get("f44") else 0,
                "low": d.get("f45", 0) / 100 if d.get("f45") else 0,
                "prev_close": prev_close,
                "volume": d.get("f47", 0),
                "amount": d.get("f48", 0),
                "market_cap": d.get("f116", 0),
                "float_cap": d.get("f117", 0),
                "pe": d.get("f162", 0) / 100 if d.get("f162") else None,
                "pb": d.get("f167", 0) / 100 if d.get("f167") else None,
                "timestamp": datetime.now().isoformat()
            },
            "summary": f"【{name}({clean_symbol})】价格: {price}, 涨跌: {change_pct}%"
        }

    async def _get_hk_quote(self, symbol: str) -> Dict[str, Any]:
        """获取港股行情"""
        clean_symbol = symbol.replace('.HK', '').zfill(5)

        url = f"https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": f"116.{clean_symbol}",
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f116,f170",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("rc") != 0 or not data.get("data"):
            return {
                "success": False,
                "error": "No data returned",
                "summary": f"未找到港股 {symbol} 的数据"
            }

        d = data["data"]
        name = d.get("f58", "")
        price = d.get("f43", 0) / 1000 if d.get("f43") else 0
        prev_close = d.get("f60", 0) / 1000 if d.get("f60") else 0
        change = price - prev_close
        change_pct = d.get("f170", 0) / 100 if d.get("f170") else 0

        return {
            "success": True,
            "data": {
                "symbol": clean_symbol,
                "name": name,
                "market": "港股",
                "price": price,
                "change": round(change, 3),
                "change_percent": change_pct,
                "open": d.get("f46", 0) / 1000 if d.get("f46") else 0,
                "high": d.get("f44", 0) / 1000 if d.get("f44") else 0,
                "low": d.get("f45", 0) / 1000 if d.get("f45") else 0,
                "prev_close": prev_close,
                "volume": d.get("f47", 0),
                "amount": d.get("f48", 0),
                "market_cap": d.get("f116", 0),
                "timestamp": datetime.now().isoformat()
            },
            "summary": f"【{name}({clean_symbol}.HK)】价格: {price} HKD, 涨跌: {change_pct}%"
        }

    async def _get_us_quote(self, symbol: str) -> Dict[str, Any]:
        """获取美股行情（Yahoo Finance）"""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "interval": "1d",
            "range": "1d"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        chart = data.get("chart", {})
        result = chart.get("result", [{}])[0]
        meta = result.get("meta", {})

        if not meta:
            return {
                "success": False,
                "error": "No data returned",
                "summary": f"未找到美股 {symbol} 的数据"
            }

        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("previousClose", 0)
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0

        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "name": meta.get("shortName", symbol),
                "market": "美股",
                "currency": meta.get("currency", "USD"),
                "price": price,
                "change": round(change, 2),
                "change_percent": round(change_pct, 2),
                "open": meta.get("regularMarketOpen", 0),
                "high": meta.get("regularMarketDayHigh", 0),
                "low": meta.get("regularMarketDayLow", 0),
                "prev_close": prev_close,
                "volume": meta.get("regularMarketVolume", 0),
                "market_cap": meta.get("marketCap", 0),
                "timestamp": datetime.now().isoformat()
            },
            "summary": f"【{meta.get('shortName', symbol)}({symbol})】价格: ${price}, 涨跌: {change_pct:.2f}%"
        }

    async def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        limit: int = 100,
        market: str = None
    ) -> Dict[str, Any]:
        """
        获取K线数据

        Args:
            symbol: 股票代码
            period: 周期 (daily/weekly/monthly)
            limit: 数据条数
            market: 市场

        Returns:
            K线数据
        """
        detected_market = Market(market) if market else self._detect_market(symbol)

        try:
            if detected_market == Market.CN_A:
                return await self._get_china_a_kline(symbol, period, limit)
            elif detected_market == Market.US:
                return await self._get_us_kline(symbol, period, limit)
            else:
                return {"success": False, "error": f"K线数据暂不支持: {detected_market}"}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取K线数据失败: {str(e)}"
            }

    async def _get_china_a_kline(
        self,
        symbol: str,
        period: str,
        limit: int
    ) -> Dict[str, Any]:
        """获取A股K线数据"""
        clean_symbol = symbol.replace('.SH', '').replace('.SZ', '')
        if clean_symbol.startswith(('60', '68')):
            market_code = "1"
        else:
            market_code = "0"

        klt_map = {"daily": "101", "weekly": "102", "monthly": "103"}
        klt = klt_map.get(period, "101")

        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": f"{market_code}.{clean_symbol}",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": klt,
            "fqt": "1",  # 前复权
            "lmt": limit,
            "end": "20500101",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("rc") != 0 or not data.get("data"):
            return {"success": False, "error": "No kline data"}

        klines = data["data"].get("klines", [])
        parsed_klines = []

        for kline in klines:
            parts = kline.split(",")
            if len(parts) >= 7:
                parsed_klines.append({
                    "date": parts[0],
                    "open": float(parts[1]),
                    "close": float(parts[2]),
                    "high": float(parts[3]),
                    "low": float(parts[4]),
                    "volume": int(parts[5]),
                    "amount": float(parts[6])
                })

        return {
            "success": True,
            "data": {
                "symbol": clean_symbol,
                "period": period,
                "count": len(parsed_klines),
                "klines": parsed_klines
            },
            "summary": f"获取 {clean_symbol} {period} K线 {len(parsed_klines)} 条"
        }

    async def _get_us_kline(
        self,
        symbol: str,
        period: str,
        limit: int
    ) -> Dict[str, Any]:
        """获取美股K线数据"""
        interval_map = {"daily": "1d", "weekly": "1wk", "monthly": "1mo"}
        interval = interval_map.get(period, "1d")

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "interval": interval,
            "range": "1y" if limit <= 252 else "5y"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        chart = data.get("chart", {})
        result = chart.get("result", [{}])[0]
        timestamps = result.get("timestamp", [])
        indicators = result.get("indicators", {})
        quote = indicators.get("quote", [{}])[0]

        if not timestamps:
            return {"success": False, "error": "No kline data"}

        parsed_klines = []
        for i in range(min(len(timestamps), limit)):
            parsed_klines.append({
                "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                "open": quote.get("open", [None])[i],
                "close": quote.get("close", [None])[i],
                "high": quote.get("high", [None])[i],
                "low": quote.get("low", [None])[i],
                "volume": quote.get("volume", [None])[i]
            })

        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "period": period,
                "count": len(parsed_klines),
                "klines": parsed_klines[-limit:]
            },
            "summary": f"获取 {symbol} {period} K线 {len(parsed_klines)} 条"
        }

    async def get_financial_report(
        self,
        symbol: str,
        report_type: str = "income"
    ) -> Dict[str, Any]:
        """
        获取财务报表

        Args:
            symbol: 股票代码
            report_type: 报表类型 (income/balance/cashflow)

        Returns:
            财务数据
        """
        detected_market = self._detect_market(symbol)

        try:
            if detected_market == Market.CN_A:
                return await self._get_china_a_financial(symbol, report_type)
            elif detected_market == Market.US:
                return await self._get_us_financial(symbol, report_type)
            else:
                return {"success": False, "error": f"财报数据暂不支持: {detected_market}"}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取财报失败: {str(e)}"
            }

    async def _get_china_a_financial(
        self,
        symbol: str,
        report_type: str
    ) -> Dict[str, Any]:
        """获取A股财报数据"""
        clean_symbol = symbol.replace('.SH', '').replace('.SZ', '')

        # 使用东方财富财报接口
        type_map = {
            "income": "RPT_DMSK_FN_INCOME",
            "balance": "RPT_DMSK_FN_BALANCE",
            "cashflow": "RPT_DMSK_FN_CASHFLOW"
        }
        report_name = type_map.get(report_type, "RPT_DMSK_FN_INCOME")

        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            "reportName": report_name,
            "columns": "ALL",
            "filter": f'(SECURITY_CODE="{clean_symbol}")',
            "pageNumber": 1,
            "pageSize": 4,
            "sortTypes": "-1",
            "sortColumns": "REPORT_DATE"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        result = data.get("result", {})
        reports = result.get("data", [])

        if not reports:
            return {
                "success": False,
                "error": "No financial data",
                "summary": f"未找到 {symbol} 的财报数据"
            }

        # 简化返回数据
        formatted_reports = []
        for report in reports[:4]:
            formatted_reports.append({
                "report_date": report.get("REPORT_DATE", ""),
                "report_type": report.get("REPORT_TYPE", ""),
                # 根据报表类型返回关键指标
                "data": {k: v for k, v in report.items() if v is not None and k not in ["SECURITY_CODE", "SECURITY_NAME_ABBR"]}
            })

        return {
            "success": True,
            "data": {
                "symbol": clean_symbol,
                "report_type": report_type,
                "reports": formatted_reports
            },
            "summary": f"获取 {symbol} {report_type} 报表 {len(formatted_reports)} 期"
        }

    async def _get_us_financial(
        self,
        symbol: str,
        report_type: str
    ) -> Dict[str, Any]:
        """获取美股财报数据 (Yahoo Finance)"""
        module_map = {
            "income": "incomeStatementHistory",
            "balance": "balanceSheetHistory",
            "cashflow": "cashflowStatementHistory"
        }
        module = module_map.get(report_type, "incomeStatementHistory")

        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
        params = {"modules": module}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        result = data.get("quoteSummary", {}).get("result", [{}])[0]
        statements = result.get(module, {}).get(f"{module.replace('History', 'Statements')}", [])

        if not statements:
            return {
                "success": False,
                "error": "No financial data",
                "summary": f"未找到 {symbol} 的财报数据"
            }

        formatted_reports = []
        for stmt in statements[:4]:
            report = {"end_date": stmt.get("endDate", {}).get("fmt", "")}
            for key, value in stmt.items():
                if isinstance(value, dict) and "raw" in value:
                    report[key] = value["raw"]
            formatted_reports.append(report)

        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "report_type": report_type,
                "reports": formatted_reports
            },
            "summary": f"获取 {symbol} {report_type} 报表 {len(formatted_reports)} 期"
        }

    async def get_market_overview(self, market: str = "cn_a") -> Dict[str, Any]:
        """
        获取市场概览

        Args:
            market: 市场 (cn_a/cn_hk/us)

        Returns:
            市场概览数据
        """
        try:
            if market == "cn_a":
                return await self._get_china_market_overview()
            else:
                return {"success": False, "error": f"市场概览暂不支持: {market}"}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取市场概览失败: {str(e)}"
            }

    async def _get_china_market_overview(self) -> Dict[str, Any]:
        """获取A股市场概览"""
        indices = [
            ("1.000001", "上证指数"),
            ("0.399001", "深证成指"),
            ("0.399006", "创业板指"),
            ("1.000688", "科创50")
        ]

        overview = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for secid, name in indices:
                url = "https://push2.eastmoney.com/api/qt/stock/get"
                params = {
                    "secid": secid,
                    "fields": "f43,f44,f45,f46,f170",
                    "ut": "fa5fd1943c7b386f172d6893dbfba10b"
                }
                response = await client.get(url, params=params)
                data = response.json()

                if data.get("data"):
                    d = data["data"]
                    overview.append({
                        "name": name,
                        "price": d.get("f43", 0) / 100,
                        "change_percent": d.get("f170", 0) / 100,
                        "high": d.get("f44", 0) / 100,
                        "low": d.get("f45", 0) / 100
                    })

        return {
            "success": True,
            "data": {
                "market": "A股",
                "indices": overview,
                "timestamp": datetime.now().isoformat()
            },
            "summary": f"A股主要指数: " + ", ".join(
                f"{i['name']} {i['change_percent']:+.2f}%" for i in overview
            )
        }


# 创建全局服务实例
_financial_service: Optional[FinancialDataService] = None


def get_financial_data_service() -> FinancialDataService:
    """获取金融数据服务实例"""
    global _financial_service
    if _financial_service is None:
        _financial_service = FinancialDataService()
    return _financial_service
