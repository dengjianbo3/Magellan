"""
AkShare China A-Share Market Data Tool
Free access to China A-share market data

AkShare is an open-source Python financial data interface library
Official docs: https://akshare.akfamily.xyz/
"""
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from .tool import Tool


class AkShareTool(Tool):
    """
    AkShare China A-Share Data Tool

    Supported features:
    - Real-time stock quotes
    - Historical K-line data
    - Financial statement data
    - Industry sector data
    - Northbound capital flow data
    - Dragon Tiger List data
    """

    def __init__(self):
        super().__init__(
            name="akshare_a_stock",
            description="Get China A-share market data including real-time quotes, historical K-lines, financial statements, northbound capital flow, etc. Supports all stocks in Shanghai and Shenzhen markets."
        )
        self._ak = None

    def _get_akshare(self):
        """Lazy import akshare"""
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                raise ImportError("akshare not installed, please run: pip install akshare")
        return self._ak

    async def execute(
        self,
        action: str,
        symbol: str = None,
        start_date: str = None,
        end_date: str = None,
        period: str = "daily",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行A股数据查询

        Args:
            action: 操作类型
                - quote: 获取实时行情
                - history: 获取历史K线
                - financials: 获取财务数据
                - north_flow: 获取北向资金
                - industry: 获取行业板块
                - top_list: 获取龙虎榜
            symbol: 股票代码 (如 600519, 000001)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            period: K线周期 (daily, weekly, monthly)
        """
        try:
            if action == "quote":
                return await self._get_quote(symbol)
            elif action == "history":
                return await self._get_history(symbol, start_date, end_date, period)
            elif action == "financials":
                return await self._get_financials(symbol)
            elif action == "north_flow":
                return await self._get_north_flow()
            elif action == "industry":
                return await self._get_industry_data()
            elif action == "top_list":
                return await self._get_top_list(kwargs.get("date"))
            elif action == "stock_info":
                return await self._get_stock_info(symbol)
            else:
                return {
                    "success": False,
                    "error": f"未知操作: {action}",
                    "summary": f"不支持的操作类型: {action}"
                }
        except ImportError as e:
            return {
                "success": False,
                "error": str(e),
                "summary": "akshare库未安装，请先安装: pip install akshare"
            }
        except Exception as e:
            print(f"[AkShareTool] Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取A股数据失败: {str(e)}"
            }

    async def _get_quote(self, symbol: str) -> Dict[str, Any]:
        """获取实时行情"""
        ak = self._get_akshare()

        def _fetch():
            # 获取实时行情
            df = ak.stock_zh_a_spot_em()
            # 根据代码筛选
            code = symbol.replace("SH", "").replace("SZ", "").replace(".", "")
            row = df[df["代码"] == code]

            if row.empty:
                return None

            row = row.iloc[0]
            return {
                "code": row["代码"],
                "name": row["名称"],
                "price": float(row["最新价"]) if row["最新价"] else 0,
                "change_pct": float(row["涨跌幅"]) if row["涨跌幅"] else 0,
                "change": float(row["涨跌额"]) if row["涨跌额"] else 0,
                "volume": float(row["成交量"]) if row["成交量"] else 0,
                "amount": float(row["成交额"]) if row["成交额"] else 0,
                "open": float(row["今开"]) if row["今开"] else 0,
                "high": float(row["最高"]) if row["最高"] else 0,
                "low": float(row["最低"]) if row["最低"] else 0,
                "prev_close": float(row["昨收"]) if row["昨收"] else 0,
                "turnover_rate": float(row["换手率"]) if row["换手率"] else 0,
                "pe_ratio": float(row["市盈率-动态"]) if row["市盈率-动态"] else 0,
                "pb_ratio": float(row["市净率"]) if row["市净率"] else 0,
                "market_cap": float(row["总市值"]) if row["总市值"] else 0,
                "circulating_cap": float(row["流通市值"]) if row["流通市值"] else 0,
            }

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _fetch)

        if result is None:
            return {
                "success": False,
                "summary": f"未找到股票 {symbol}"
            }

        # 格式化市值
        market_cap_str = self._format_large_number(result["market_cap"])

        summary = f"""
{result['name']} ({result['code']}) 实时行情:
- 最新价: ¥{result['price']:.2f} ({result['change_pct']:+.2f}%)
- 今开: ¥{result['open']:.2f} | 最高: ¥{result['high']:.2f} | 最低: ¥{result['low']:.2f}
- 成交量: {result['volume']/10000:.2f}万手 | 成交额: {result['amount']/100000000:.2f}亿
- 换手率: {result['turnover_rate']:.2f}%
- 市盈率: {result['pe_ratio']:.2f} | 市净率: {result['pb_ratio']:.2f}
- 总市值: {market_cap_str}
"""

        return {
            "success": True,
            "summary": summary.strip(),
            "data": result
        }

    async def _get_history(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        period: str = "daily"
    ) -> Dict[str, Any]:
        """获取历史K线数据"""
        ak = self._get_akshare()

        # 默认获取最近60个交易日
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")

        # 格式化日期
        start_date = start_date.replace("-", "")
        end_date = end_date.replace("-", "")

        def _fetch():
            code = symbol.replace("SH", "").replace("SZ", "").replace(".", "")

            # 根据周期选择接口
            if period == "daily":
                df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                        start_date=start_date, end_date=end_date,
                                        adjust="qfq")  # 前复权
            elif period == "weekly":
                df = ak.stock_zh_a_hist(symbol=code, period="weekly",
                                        start_date=start_date, end_date=end_date,
                                        adjust="qfq")
            elif period == "monthly":
                df = ak.stock_zh_a_hist(symbol=code, period="monthly",
                                        start_date=start_date, end_date=end_date,
                                        adjust="qfq")
            else:
                df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                        start_date=start_date, end_date=end_date,
                                        adjust="qfq")

            return df.to_dict("records") if not df.empty else []

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _fetch)

        if not data:
            return {
                "success": False,
                "summary": f"未找到股票 {symbol} 的历史数据"
            }

        # 计算统计信息
        closes = [d.get("收盘", 0) for d in data]
        highs = [d.get("最高", 0) for d in data]
        lows = [d.get("最低", 0) for d in data]

        latest = data[-1] if data else {}

        summary = f"""
股票 {symbol} 历史K线数据 ({period}):
- 数据范围: {data[0].get('日期', 'N/A')} ~ {data[-1].get('日期', 'N/A')}
- 共 {len(data)} 条记录
- 最新收盘: ¥{latest.get('收盘', 0):.2f}
- 区间最高: ¥{max(highs):.2f} | 区间最低: ¥{min(lows):.2f}
- 区间涨跌幅: {((closes[-1] - closes[0]) / closes[0] * 100) if closes[0] else 0:.2f}%
"""

        # 返回最近10条数据作为示例
        recent_data = data[-10:] if len(data) > 10 else data

        return {
            "success": True,
            "summary": summary.strip(),
            "data": {
                "total_records": len(data),
                "period": period,
                "recent": recent_data,
                "statistics": {
                    "high": max(highs),
                    "low": min(lows),
                    "latest_close": closes[-1] if closes else 0,
                    "change_pct": ((closes[-1] - closes[0]) / closes[0] * 100) if closes and closes[0] else 0
                }
            }
        }

    async def _get_financials(self, symbol: str) -> Dict[str, Any]:
        """获取财务数据"""
        ak = self._get_akshare()

        def _fetch():
            code = symbol.replace("SH", "").replace("SZ", "").replace(".", "")

            # 获取主要财务指标
            df = ak.stock_financial_analysis_indicator(symbol=code)

            if df.empty:
                return None

            # 取最近4个季度
            recent = df.head(4).to_dict("records")
            return recent

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _fetch)

        if not data:
            return {
                "success": False,
                "summary": f"未找到股票 {symbol} 的财务数据"
            }

        latest = data[0] if data else {}

        summary = f"""
股票 {symbol} 财务指标 (最新报告期):
- 报告期: {latest.get('日期', 'N/A')}
- 每股收益(EPS): ¥{latest.get('摊薄每股收益', 0):.4f}
- 净资产收益率(ROE): {latest.get('净资产收益率', 0):.2f}%
- 毛利率: {latest.get('销售毛利率', 0):.2f}%
- 净利率: {latest.get('销售净利率', 0):.2f}%
- 资产负债率: {latest.get('资产负债率', 0):.2f}%
- 营收增长率: {latest.get('营业收入增长率', 0):.2f}%
- 净利润增长率: {latest.get('净利润增长率', 0):.2f}%
"""

        return {
            "success": True,
            "summary": summary.strip(),
            "data": data
        }

    async def _get_north_flow(self) -> Dict[str, Any]:
        """获取北向资金数据"""
        ak = self._get_akshare()

        def _fetch():
            # 获取北向资金历史数据
            df = ak.stock_em_hsgt_north_net_flow_in()

            if df.empty:
                return None

            # 取最近10天
            recent = df.head(10).to_dict("records")
            return recent

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _fetch)

        if not data:
            return {
                "success": False,
                "summary": "获取北向资金数据失败"
            }

        latest = data[0] if data else {}

        # 计算最近5日累计
        recent_5_flow = sum(d.get("北向资金", 0) for d in data[:5])

        summary = f"""
北向资金最新动态:
- 日期: {latest.get('日期', 'N/A')}
- 当日净流入: {latest.get('北向资金', 0):.2f}亿
- 沪股通: {latest.get('沪股通', 0):.2f}亿
- 深股通: {latest.get('深股通', 0):.2f}亿
- 近5日累计: {recent_5_flow:.2f}亿
"""

        return {
            "success": True,
            "summary": summary.strip(),
            "data": data
        }

    async def _get_industry_data(self) -> Dict[str, Any]:
        """获取行业板块数据"""
        ak = self._get_akshare()

        def _fetch():
            # 获取行业板块行情
            df = ak.stock_board_industry_name_em()

            if df.empty:
                return None

            return df.head(20).to_dict("records")

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _fetch)

        if not data:
            return {
                "success": False,
                "summary": "获取行业板块数据失败"
            }

        # 按涨跌幅排序
        top_gainers = sorted(data, key=lambda x: x.get("涨跌幅", 0), reverse=True)[:5]
        top_losers = sorted(data, key=lambda x: x.get("涨跌幅", 0))[:5]

        summary = "行业板块涨跌榜:\n\n领涨板块:\n"
        for i, item in enumerate(top_gainers, 1):
            summary += f"{i}. {item.get('板块名称', 'N/A')}: {item.get('涨跌幅', 0):+.2f}%\n"

        summary += "\n领跌板块:\n"
        for i, item in enumerate(top_losers, 1):
            summary += f"{i}. {item.get('板块名称', 'N/A')}: {item.get('涨跌幅', 0):+.2f}%\n"

        return {
            "success": True,
            "summary": summary.strip(),
            "data": {
                "top_gainers": top_gainers,
                "top_losers": top_losers,
                "all": data
            }
        }

    async def _get_top_list(self, date: str = None) -> Dict[str, Any]:
        """获取龙虎榜数据"""
        ak = self._get_akshare()

        if not date:
            date = datetime.now().strftime("%Y%m%d")

        def _fetch():
            # 获取龙虎榜数据
            df = ak.stock_lhb_detail_em(date=date.replace("-", ""))

            if df.empty:
                return None

            return df.head(20).to_dict("records")

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _fetch)

        if not data:
            return {
                "success": True,
                "summary": f"日期 {date} 无龙虎榜数据 (可能是非交易日)",
                "data": []
            }

        summary = f"龙虎榜 ({date}):\n"
        for i, item in enumerate(data[:10], 1):
            summary += f"{i}. {item.get('名称', 'N/A')}({item.get('代码', 'N/A')}): "
            summary += f"涨跌幅 {item.get('涨跌幅', 0):+.2f}% | "
            summary += f"上榜原因: {item.get('上榜原因', 'N/A')}\n"

        return {
            "success": True,
            "summary": summary.strip(),
            "data": data
        }

    async def _get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取股票基本信息"""
        ak = self._get_akshare()

        def _fetch():
            code = symbol.replace("SH", "").replace("SZ", "").replace(".", "")

            # 获取个股信息
            df = ak.stock_individual_info_em(symbol=code)

            if df.empty:
                return None

            # 转换为字典
            info = {}
            for _, row in df.iterrows():
                info[row["item"]] = row["value"]

            return info

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _fetch)

        if not data:
            return {
                "success": False,
                "summary": f"未找到股票 {symbol} 的基本信息"
            }

        summary = f"""
股票基本信息:
- 股票代码: {data.get('股票代码', 'N/A')}
- 股票简称: {data.get('股票简称', 'N/A')}
- 所属行业: {data.get('行业', 'N/A')}
- 上市时间: {data.get('上市时间', 'N/A')}
- 总股本: {data.get('总股本', 'N/A')}
- 流通股本: {data.get('流通股', 'N/A')}
- 总市值: {data.get('总市值', 'N/A')}
- 流通市值: {data.get('流通市值', 'N/A')}
"""

        return {
            "success": True,
            "summary": summary.strip(),
            "data": data
        }

    def _format_large_number(self, num: float) -> str:
        """格式化大数字"""
        if num >= 1e12:
            return f"¥{num/1e12:.2f}万亿"
        elif num >= 1e8:
            return f"¥{num/1e8:.2f}亿"
        elif num >= 1e4:
            return f"¥{num/1e4:.2f}万"
        else:
            return f"¥{num:.2f}"

    def to_schema(self) -> Dict[str, Any]:
        """Return tool schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["quote", "history", "financials", "north_flow", "industry", "top_list", "stock_info"],
                        "description": "Action type: quote(real-time quotes), history(historical K-line), financials(financial data), north_flow(northbound capital), industry(industry sectors), top_list(Dragon Tiger List), stock_info(stock info)"
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Stock code, e.g., 600519 (Kweichow Moutai), 000001 (Ping An Bank)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD format)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD format)"
                    },
                    "period": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": "K-line period: daily, weekly, monthly",
                        "default": "daily"
                    },
                    "date": {
                        "type": "string",
                        "description": "Query date (for Dragon Tiger List etc., YYYYMMDD format)"
                    }
                },
                "required": ["action"]
            }
        }
