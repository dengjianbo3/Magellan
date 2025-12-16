"""
Enhanced Tools for Roundtable Discussion Agents - Phase 1

Contains:
1. ChinaMarketDataTool - China market data (A-shares/HK stocks)
2. QichaChaTool - Company info lookup
3. GitHubAnalyzerTool - GitHub project analysis
4. PatentSearchTool - Patent search
5. SentimentMonitorTool - Sentiment monitoring
"""
import os
import httpx
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from .tool import Tool


# ==================== 1. China Market Data Tool ====================

class ChinaMarketDataTool(Tool):
    """
    China Market Data Tool

    Supports A-share and HK stock data queries through multiple data sources:
    - Eastmoney
    - Sina Finance
    - 10jqka (backup)

    Features:
    - Real-time quotes
    - Historical K-lines
    - Financial statements
    - Company info
    """

    def __init__(self):
        super().__init__(
            name="china_market_data",
            description="""Get China A-share and Hong Kong stock market data.

Features:
- Real-time stock prices and quotes
- Historical K-line data
- Financial statements (balance sheet, income statement, cash flow)
- Company basic info

Supported markets:
- A-shares (Shanghai: SH, Shenzhen: SZ, e.g., 600519.SH, 000001.SZ)
- HK stocks (HK, e.g., 00700.HK, 09988.HK)

Examples:
- Query Kweichow Moutai: symbol="600519" or "600519.SH"
- Query Tencent: symbol="00700" or "00700.HK"
"""
        )
        # 东方财富API配置
        self.eastmoney_quote_url = "http://push2.eastmoney.com/api/qt/stock/get"
        self.eastmoney_kline_url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        self.eastmoney_finance_url = "http://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis"

    def _detect_market(self, symbol: str) -> tuple:
        """
        自动检测市场类型

        Returns:
            (secid, market_name)
        """
        symbol = symbol.upper().replace(" ", "")

        # 已经带后缀的情况
        if ".SH" in symbol:
            code = symbol.replace(".SH", "")
            return f"1.{code}", "A股(上海)"
        elif ".SZ" in symbol:
            code = symbol.replace(".SZ", "")
            return f"0.{code}", "A股(深圳)"
        elif ".HK" in symbol:
            code = symbol.replace(".HK", "")
            return f"116.{code}", "港股"

        # 纯数字，自动判断
        code = symbol.split(".")[0]
        if code.startswith("6"):
            return f"1.{code}", "A股(上海)"
        elif code.startswith(("0", "3")):
            return f"0.{code}", "A股(深圳)"
        elif len(code) == 5:
            return f"116.{code}", "港股"
        else:
            # 默认尝试上海
            return f"1.{code}", "A股(上海)"

    async def execute(
        self,
        symbol: str,
        action: str = "quote",
        **kwargs
    ) -> Dict[str, Any]:
        """
        获取中国市场数据

        Args:
            symbol: 股票代码 (如 600519, 00700.HK)
            action: 操作类型
                - "quote": 实时行情
                - "kline": 历史K线
                - "finance": 财务数据
                - "info": 公司资料
            **kwargs:
                - period: K线周期 (daily/weekly/monthly)
                - limit: K线数量限制
                - report_type: 财务报表类型 (income/balance/cashflow)

        Returns:
            市场数据
        """
        secid, market_name = self._detect_market(symbol)

        try:
            if action == "quote":
                return await self._get_quote(secid, symbol, market_name)
            elif action == "kline":
                period = kwargs.get("period", "daily")
                limit = kwargs.get("limit", 60)
                return await self._get_kline(secid, symbol, market_name, period, limit)
            elif action == "finance":
                return await self._get_finance(symbol, market_name)
            elif action == "info":
                return await self._get_company_info(symbol, market_name)
            else:
                return {
                    "success": False,
                    "error": f"不支持的操作类型: {action}",
                    "summary": f"请使用 quote/kline/finance/info 之一"
                }

        except Exception as e:
            print(f"[ChinaMarketDataTool] Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取{symbol}数据时出错: {str(e)}"
            }

    async def _get_quote(self, secid: str, symbol: str, market_name: str) -> Dict[str, Any]:
        """获取实时行情"""
        params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f60,f71,f116,f117,f162,f167,f168,f169,f170"
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(self.eastmoney_quote_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("data") is None:
                return {
                    "success": False,
                    "summary": f"未找到股票 {symbol} 的行情数据，请检查代码是否正确"
                }

            d = data["data"]

            # 解析数据 (东方财富返回的是整数，需要除以相应倍数)
            current_price = d.get("f43", 0) / 100 if d.get("f43") else 0
            change = d.get("f169", 0) / 100 if d.get("f169") else 0
            change_pct = d.get("f170", 0) / 100 if d.get("f170") else 0
            high = d.get("f44", 0) / 100 if d.get("f44") else 0
            low = d.get("f45", 0) / 100 if d.get("f45") else 0
            open_price = d.get("f46", 0) / 100 if d.get("f46") else 0
            prev_close = d.get("f60", 0) / 100 if d.get("f60") else 0
            volume = d.get("f47", 0)  # 成交量（手）
            amount = d.get("f48", 0)  # 成交额
            market_cap = d.get("f116", 0)  # 总市值
            float_cap = d.get("f117", 0)  # 流通市值
            pe_ratio = d.get("f162", 0) / 100 if d.get("f162") else 0  # 市盈率
            pb_ratio = d.get("f167", 0) / 100 if d.get("f167") else 0  # 市净率
            name = d.get("f58", symbol)

            # 格式化市值
            def format_cap(cap):
                if cap >= 100000000:
                    return f"{cap / 100000000:.2f}亿"
                elif cap >= 10000:
                    return f"{cap / 10000:.2f}万"
                return str(cap)

            summary = f"""【{name}({symbol})】{market_name} 实时行情

当前价格: {current_price:.2f}
涨跌额: {change:+.2f}
涨跌幅: {change_pct:+.2f}%

今开: {open_price:.2f}  |  昨收: {prev_close:.2f}
最高: {high:.2f}  |  最低: {low:.2f}

成交量: {volume:,}手
成交额: {format_cap(amount)}

总市值: {format_cap(market_cap)}
流通市值: {format_cap(float_cap)}

PE(市盈率): {pe_ratio:.2f}
PB(市净率): {pb_ratio:.2f}
"""

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "symbol": symbol,
                    "name": name,
                    "market": market_name,
                    "current_price": current_price,
                    "change": change,
                    "change_pct": change_pct,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "prev_close": prev_close,
                    "volume": volume,
                    "amount": amount,
                    "market_cap": market_cap,
                    "float_cap": float_cap,
                    "pe_ratio": pe_ratio,
                    "pb_ratio": pb_ratio
                }
            }

    async def _get_kline(
        self,
        secid: str,
        symbol: str,
        market_name: str,
        period: str = "daily",
        limit: int = 60
    ) -> Dict[str, Any]:
        """获取K线数据"""
        # 映射周期
        klt_map = {"daily": 101, "weekly": 102, "monthly": 103}
        klt = klt_map.get(period, 101)

        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": klt,
            "fqt": 1,  # 前复权
            "lmt": limit
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(self.eastmoney_kline_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("data") is None or not data["data"].get("klines"):
                return {
                    "success": False,
                    "summary": f"未找到 {symbol} 的K线数据"
                }

            klines = data["data"]["klines"]
            name = data["data"].get("name", symbol)

            # 解析K线数据
            parsed_klines = []
            for kline in klines[-limit:]:
                parts = kline.split(",")
                if len(parts) >= 7:
                    parsed_klines.append({
                        "date": parts[0],
                        "open": float(parts[1]),
                        "close": float(parts[2]),
                        "high": float(parts[3]),
                        "low": float(parts[4]),
                        "volume": int(parts[5]),
                        "amount": float(parts[6]),
                        "change_pct": float(parts[8]) if len(parts) > 8 else 0
                    })

            # 计算简单统计
            if parsed_klines:
                closes = [k["close"] for k in parsed_klines]
                latest = parsed_klines[-1]
                earliest = parsed_klines[0]
                period_return = ((latest["close"] - earliest["close"]) / earliest["close"]) * 100

                summary = f"""【{name}({symbol})】{market_name} K线数据 ({period})

数据范围: {earliest["date"]} ~ {latest["date"]}
数据条数: {len(parsed_klines)}条

最新价格: {latest["close"]:.2f}
区间涨跌: {period_return:+.2f}%
区间最高: {max(closes):.2f}
区间最低: {min(closes):.2f}

最近5日:
"""
                for k in parsed_klines[-5:]:
                    summary += f"  {k['date']}: 开{k['open']:.2f} 收{k['close']:.2f} 涨跌{k['change_pct']:+.2f}%\n"
            else:
                summary = f"未找到 {symbol} 的有效K线数据"

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "symbol": symbol,
                    "name": name,
                    "market": market_name,
                    "period": period,
                    "klines": parsed_klines
                }
            }

    async def _get_finance(self, symbol: str, market_name: str) -> Dict[str, Any]:
        """获取财务数据 - 使用新浪财经作为备选"""
        # 简化版：使用东方财富网页接口获取基本财务数据
        code = symbol.replace(".SH", "").replace(".SZ", "").replace(".HK", "")

        # 构建新浪财经接口
        if "港" in market_name:
            sina_url = f"http://hq.sinajs.cn/list=hk{code}"
        else:
            prefix = "sh" if symbol.endswith(".SH") or code.startswith("6") else "sz"
            sina_url = f"http://hq.sinajs.cn/list={prefix}{code}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    sina_url,
                    headers={"Referer": "http://finance.sina.com.cn"}
                )
                response.raise_for_status()

                # 解析新浪返回的数据
                content = response.text
                if "=" in content:
                    data_str = content.split("=")[1].strip().strip('"').strip(";")
                    if data_str:
                        parts = data_str.split(",")
                        if len(parts) > 30:
                            name = parts[0]
                            current = float(parts[3]) if parts[3] else 0

                            summary = f"""【{name}({symbol})】{market_name} 财务概要

⚠️ 注意: 详细财务报表建议访问东方财富或同花顺查看

当前股价: {current:.2f}
今日成交量: {parts[8]}手
今日成交额: {float(parts[9])/100000000:.2f}亿

提示: 如需完整财务报表（资产负债表、利润表、现金流量表），
建议使用 tavily_search 搜索 "{name} 财务报表 年报" 获取更详细信息。
"""
                            return {
                                "success": True,
                                "summary": summary,
                                "data": {"symbol": symbol, "name": name}
                            }

                return {
                    "success": False,
                    "summary": f"无法获取 {symbol} 的财务数据，建议使用搜索工具查询"
                }

        except Exception as e:
            return {
                "success": False,
                "summary": f"获取财务数据出错: {str(e)}，建议使用 tavily_search 搜索相关财报信息"
            }

    async def _get_company_info(self, symbol: str, market_name: str) -> Dict[str, Any]:
        """获取公司基本资料"""
        code = symbol.replace(".SH", "").replace(".SZ", "").replace(".HK", "")

        # 使用东方财富公司资料接口
        if "港" not in market_name:
            # A股
            market_code = "SH" if code.startswith("6") else "SZ"
            info_url = f"http://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax?code={market_code}{code}"
        else:
            # 港股信息较难获取，返回提示
            return {
                "success": True,
                "summary": f"""【{symbol}】港股公司资料

港股公司详细资料建议通过以下方式获取:
1. 使用 tavily_search 搜索 "{symbol} 公司简介"
2. 访问港交所官网或东方财富港股频道
""",
                "data": {"symbol": symbol, "market": market_name}
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(info_url)
                response.raise_for_status()
                data = response.json()

                if data.get("Result") and data.get("jbzl"):
                    info = data["jbzl"]

                    summary = f"""【{info.get('gsmc', symbol)}】公司资料

股票代码: {symbol} ({market_name})
公司全称: {info.get('gsmc', 'N/A')}
英文名称: {info.get('ywmc', 'N/A')}
曾用名: {info.get('cym', 'N/A')}

所属行业: {info.get('sshy', 'N/A')}
所属板块: {info.get('ssbk', 'N/A')}
上市日期: {info.get('ssrq', 'N/A')}
上市交易所: {info.get('ssjys', 'N/A')}

注册资本: {info.get('zczb', 'N/A')}
法定代表人: {info.get('frdb', 'N/A')}
董事长: {info.get('dsz', 'N/A')}
总经理: {info.get('zjl', 'N/A')}
董秘: {info.get('dm', 'N/A')}

注册地址: {info.get('zcdz', 'N/A')}
办公地址: {info.get('bgdz', 'N/A')}
公司网址: {info.get('gswz', 'N/A')}
电子邮箱: {info.get('dzyx', 'N/A')}

主营业务:
{info.get('zyyw', 'N/A')}
"""
                    return {
                        "success": True,
                        "summary": summary,
                        "data": info
                    }
                else:
                    return {
                        "success": False,
                        "summary": f"未找到 {symbol} 的公司资料"
                    }

        except Exception as e:
            return {
                "success": False,
                "summary": f"获取公司资料出错: {str(e)}"
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
                        "description": "Stock code, e.g., 600519 (Kweichow Moutai), 00700.HK (Tencent)"
                    },
                    "action": {
                        "type": "string",
                        "description": "Action type: quote(real-time quotes), kline(K-line), finance(financials), info(company info)",
                        "enum": ["quote", "kline", "finance", "info"],
                        "default": "quote"
                    },
                    "period": {
                        "type": "string",
                        "description": "K-line period (only for action=kline)",
                        "enum": ["daily", "weekly", "monthly"],
                        "default": "daily"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "K-line count limit",
                        "default": 60
                    }
                },
                "required": ["symbol"]
            }
        }


# ==================== 2. 企查查/天眼查工具 ====================

class CompanyRegistryTool(Tool):
    """
    Company Registry Information Tool

    Get company registration info, equity structure, and business status via public APIs
    Note: Uses free public data sources as Qichacha/Tianyancha APIs require payment
    """

    def __init__(self):
        super().__init__(
            name="company_registry",
            description="""Query company business registration information and background.

Features:
- Company basic info (registered capital, founding date, business scope, etc.)
- Shareholder information and equity structure
- Executive information
- Business abnormalities and legal litigation
- Related companies

Note: Currently uses public data sources. For more detailed info, recommend using with tavily_search.
"""
        )
        # 使用国家企业信用信息公示系统的公开接口
        self.api_url = "https://www.tianyancha.com/search"  # 需要实际配置

    async def execute(
        self,
        company_name: str,
        query_type: str = "basic",
        **kwargs
    ) -> Dict[str, Any]:
        """
        查询企业信息

        Args:
            company_name: 公司名称
            query_type: 查询类型
                - basic: 基本信息
                - shareholders: 股东信息
                - executives: 高管信息
                - legal: 法律诉讼
                - related: 关联企业
        """
        try:
            # 由于企查查/天眼查需要付费API，这里提供一个智能搜索方案
            # 实际使用时可以替换为真实API

            search_queries = {
                "basic": f"{company_name} 公司 注册资本 成立日期 经营范围",
                "shareholders": f"{company_name} 股东 股权结构 持股比例",
                "executives": f"{company_name} 高管 董事长 CEO 管理层",
                "legal": f"{company_name} 诉讼 法律纠纷 行政处罚",
                "related": f"{company_name} 关联公司 子公司 母公司 投资"
            }

            query = search_queries.get(query_type, search_queries["basic"])

            # 调用Tavily搜索获取企业信息
            from .mcp_tools import TavilySearchTool
            tavily = TavilySearchTool()
            result = await tavily.execute(query=query, max_results=5)

            if result.get("success"):
                summary = f"""【{company_name}】企业信息查询 ({query_type})

{result.get('summary', '未找到相关信息')}

---
提示: 如需更详细的工商信息，建议:
1. 访问国家企业信用信息公示系统 (http://www.gsxt.gov.cn)
2. 使用企查查/天眼查等专业平台
"""
                return {
                    "success": True,
                    "summary": summary,
                    "data": result.get("results", []),
                    "query_type": query_type
                }
            else:
                return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"查询企业 {company_name} 信息时出错: {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Company name"
                    },
                    "query_type": {
                        "type": "string",
                        "description": "Query type",
                        "enum": ["basic", "shareholders", "executives", "legal", "related"],
                        "default": "basic"
                    }
                },
                "required": ["company_name"]
            }
        }


# ==================== 3. GitHub分析工具 ====================

class GitHubAnalyzerTool(Tool):
    """
    GitHub Project Analysis Tool

    Analyze GitHub repository activity, code quality, contributors, etc.
    """

    def __init__(self):
        super().__init__(
            name="github_analyzer",
            description="""Analyze GitHub projects and organizations.

Features:
- Repository basic info (stars, forks, issues)
- Commit activity analysis
- Major contributors
- Code language distribution
- Recent update status

Use cases:
- Evaluate open source project activity
- Analyze technical team capabilities
- Verify technology claims
"""
        )
        self.api_base = "https://api.github.com"
        self.token = os.getenv("GITHUB_TOKEN", "")

    def _get_headers(self) -> dict:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Magellan-Agent"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    async def execute(
        self,
        repo: str = None,
        organization: str = None,
        action: str = "repo_info",
        **kwargs
    ) -> Dict[str, Any]:
        """
        分析GitHub项目

        Args:
            repo: 仓库地址 (格式: owner/repo 或完整URL)
            organization: 组织名称
            action: 操作类型
                - repo_info: 仓库信息
                - contributors: 贡献者分析
                - activity: 活跃度分析
                - languages: 语言分布
                - org_repos: 组织仓库列表
        """
        try:
            if action == "org_repos" and organization:
                return await self._get_org_repos(organization)
            elif repo:
                # 解析仓库地址
                if "github.com" in repo:
                    # 从URL提取 owner/repo
                    parts = repo.rstrip("/").split("github.com/")[-1].split("/")
                    if len(parts) >= 2:
                        repo = f"{parts[0]}/{parts[1]}"

                if action == "repo_info":
                    return await self._get_repo_info(repo)
                elif action == "contributors":
                    return await self._get_contributors(repo)
                elif action == "activity":
                    return await self._get_activity(repo)
                elif action == "languages":
                    return await self._get_languages(repo)
                else:
                    return await self._get_repo_info(repo)
            else:
                return {
                    "success": False,
                    "summary": "请提供仓库地址(repo)或组织名称(organization)"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"GitHub分析出错: {str(e)}"
            }

    async def _get_repo_info(self, repo: str) -> Dict[str, Any]:
        """获取仓库基本信息"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.api_base}/repos/{repo}",
                headers=self._get_headers()
            )

            if response.status_code == 404:
                return {
                    "success": False,
                    "summary": f"未找到仓库: {repo}"
                }

            response.raise_for_status()
            data = response.json()

            # 获取最近提交
            commits_resp = await client.get(
                f"{self.api_base}/repos/{repo}/commits",
                headers=self._get_headers(),
                params={"per_page": 5}
            )
            recent_commits = commits_resp.json() if commits_resp.status_code == 200 else []

            created = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            updated = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            days_since_update = (datetime.now(updated.tzinfo) - updated).days

            summary = f"""【GitHub仓库分析】{data['full_name']}

📊 基本指标:
  ⭐ Stars: {data['stargazers_count']:,}
  🍴 Forks: {data['forks_count']:,}
  👁️ Watchers: {data['subscribers_count']:,}
  🐛 Open Issues: {data['open_issues_count']:,}

📝 项目信息:
  描述: {data.get('description', 'N/A')}
  主要语言: {data.get('language', 'N/A')}
  License: {data.get('license', {}).get('name', 'N/A') if data.get('license') else 'N/A'}

📅 时间线:
  创建时间: {created.strftime('%Y-%m-%d')}
  最后更新: {updated.strftime('%Y-%m-%d')} ({days_since_update}天前)

🔗 链接:
  主页: {data.get('homepage', 'N/A')}
  仓库: {data['html_url']}
"""

            if recent_commits:
                summary += "\n📝 最近提交:\n"
                for commit in recent_commits[:3]:
                    msg = commit['commit']['message'].split('\n')[0][:50]
                    author = commit['commit']['author']['name']
                    date = commit['commit']['author']['date'][:10]
                    summary += f"  - [{date}] {msg}... by {author}\n"

            # 活跃度评估
            if days_since_update <= 7:
                activity_level = "🟢 非常活跃"
            elif days_since_update <= 30:
                activity_level = "🟡 活跃"
            elif days_since_update <= 90:
                activity_level = "🟠 一般"
            else:
                activity_level = "🔴 不活跃"

            summary += f"\n📈 活跃度评估: {activity_level}"

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "name": data["name"],
                    "full_name": data["full_name"],
                    "description": data.get("description"),
                    "stars": data["stargazers_count"],
                    "forks": data["forks_count"],
                    "watchers": data["subscribers_count"],
                    "open_issues": data["open_issues_count"],
                    "language": data.get("language"),
                    "created_at": data["created_at"],
                    "updated_at": data["updated_at"],
                    "days_since_update": days_since_update,
                    "url": data["html_url"]
                }
            }

    async def _get_contributors(self, repo: str) -> Dict[str, Any]:
        """获取贡献者信息"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.api_base}/repos/{repo}/contributors",
                headers=self._get_headers(),
                params={"per_page": 20}
            )

            if response.status_code != 200:
                return {"success": False, "summary": f"获取贡献者信息失败"}

            contributors = response.json()

            summary = f"【{repo}】贡献者分析\n\n"
            summary += f"贡献者总数: {len(contributors)}+ 人\n\n"
            summary += "Top 10 贡献者:\n"

            for i, c in enumerate(contributors[:10], 1):
                summary += f"  {i}. {c['login']} - {c['contributions']:,} commits\n"

            # 计算贡献集中度
            if contributors:
                total_commits = sum(c['contributions'] for c in contributors)
                top3_commits = sum(c['contributions'] for c in contributors[:3])
                concentration = (top3_commits / total_commits * 100) if total_commits > 0 else 0

                summary += f"\n📊 贡献集中度: Top 3 贡献者占 {concentration:.1f}% 的提交"
                if concentration > 80:
                    summary += " (⚠️ 高度依赖少数开发者)"
                elif concentration > 50:
                    summary += " (正常)"
                else:
                    summary += " (✅ 贡献分布均匀)"

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "total": len(contributors),
                    "contributors": [
                        {"login": c["login"], "contributions": c["contributions"]}
                        for c in contributors[:20]
                    ]
                }
            }

    async def _get_activity(self, repo: str) -> Dict[str, Any]:
        """获取活跃度分析"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 获取提交统计
            stats_resp = await client.get(
                f"{self.api_base}/repos/{repo}/stats/commit_activity",
                headers=self._get_headers()
            )

            # 获取最近的issues和PRs
            issues_resp = await client.get(
                f"{self.api_base}/repos/{repo}/issues",
                headers=self._get_headers(),
                params={"state": "all", "per_page": 30}
            )

            summary = f"【{repo}】活跃度分析\n\n"

            if stats_resp.status_code == 200:
                stats = stats_resp.json()
                if stats:
                    # 最近4周提交数
                    recent_weeks = stats[-4:] if len(stats) >= 4 else stats
                    recent_commits = sum(week.get("total", 0) for week in recent_weeks)
                    summary += f"📈 最近4周提交: {recent_commits} commits\n"

                    # 年度提交数
                    yearly_commits = sum(week.get("total", 0) for week in stats)
                    summary += f"📅 年度提交总数: {yearly_commits} commits\n"

            if issues_resp.status_code == 200:
                issues = issues_resp.json()
                open_issues = sum(1 for i in issues if i.get("state") == "open")
                closed_issues = sum(1 for i in issues if i.get("state") == "closed")
                prs = sum(1 for i in issues if i.get("pull_request"))

                summary += f"\n🐛 Issues (最近30条):\n"
                summary += f"  - 开放: {open_issues}\n"
                summary += f"  - 已关闭: {closed_issues}\n"
                summary += f"  - PR数量: {prs}\n"

            return {
                "success": True,
                "summary": summary,
                "data": {}
            }

    async def _get_languages(self, repo: str) -> Dict[str, Any]:
        """获取语言分布"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.api_base}/repos/{repo}/languages",
                headers=self._get_headers()
            )

            if response.status_code != 200:
                return {"success": False, "summary": "获取语言分布失败"}

            languages = response.json()
            total_bytes = sum(languages.values())

            summary = f"【{repo}】代码语言分布\n\n"

            for lang, bytes_count in sorted(languages.items(), key=lambda x: -x[1]):
                pct = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
                bar = "█" * int(pct / 5)
                summary += f"  {lang}: {pct:.1f}% {bar}\n"

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "languages": languages,
                    "total_bytes": total_bytes
                }
            }

    async def _get_org_repos(self, org: str) -> Dict[str, Any]:
        """获取组织的仓库列表"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.api_base}/orgs/{org}/repos",
                headers=self._get_headers(),
                params={"sort": "stars", "per_page": 20}
            )

            if response.status_code == 404:
                return {"success": False, "summary": f"未找到组织: {org}"}

            response.raise_for_status()
            repos = response.json()

            summary = f"【GitHub组织】{org}\n\n"
            summary += f"公开仓库数: {len(repos)}+\n\n"
            summary += "热门仓库 (按Stars排序):\n"

            total_stars = 0
            for repo in repos[:10]:
                total_stars += repo["stargazers_count"]
                summary += f"  ⭐ {repo['stargazers_count']:,} - {repo['name']}\n"
                if repo.get("description"):
                    summary += f"      {repo['description'][:60]}...\n"

            summary += f"\nTop 10 仓库总 Stars: {total_stars:,}"

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "organization": org,
                    "repos": [
                        {
                            "name": r["name"],
                            "stars": r["stargazers_count"],
                            "description": r.get("description"),
                            "language": r.get("language")
                        }
                        for r in repos
                    ]
                }
            }

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "仓库地址，格式: owner/repo 或完整GitHub URL"
                    },
                    "organization": {
                        "type": "string",
                        "description": "GitHub组织名称"
                    },
                    "action": {
                        "type": "string",
                        "description": "操作类型",
                        "enum": ["repo_info", "contributors", "activity", "languages", "org_repos"],
                        "default": "repo_info"
                    }
                }
            }
        }


# ==================== 4. 专利检索工具 ====================

class PatentSearchTool(Tool):
    """
    Patent Search Tool

    Search patent information via public APIs
    Supports: Google Patents, USPTO, CNIPA (China)
    """

    def __init__(self):
        super().__init__(
            name="patent_search",
            description="""Search and analyze patent information.

Features:
- Search patents by company/inventor
- Search technical patents by keywords
- View patent details
- Patent citation analysis

Supported patent offices:
- USPTO (United States)
- EPO (Europe)
- CNIPA (China)
- WIPO (World Intellectual Property Organization)
"""
        )

    async def execute(
        self,
        query: str,
        search_type: str = "keyword",
        patent_office: str = "all",
        limit: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        搜索专利

        Args:
            query: 搜索内容（公司名/发明人/关键词）
            search_type: 搜索类型
                - keyword: 关键词搜索
                - assignee: 按专利持有人搜索
                - inventor: 按发明人搜索
            patent_office: 专利局 (all/USPTO/EPO/CNIPA)
            limit: 返回数量限制
        """
        try:
            # 使用Google Patents搜索（通过Tavily代理）
            # 构建专业的专利搜索查询
            if search_type == "assignee":
                search_query = f"site:patents.google.com {query} assignee patent"
            elif search_type == "inventor":
                search_query = f"site:patents.google.com inventor:{query} patent"
            else:
                search_query = f"site:patents.google.com {query} patent"

            if patent_office != "all":
                office_map = {
                    "USPTO": "US patent",
                    "EPO": "EP patent",
                    "CNIPA": "CN patent",
                    "WIPO": "WO patent"
                }
                search_query += f" {office_map.get(patent_office, '')}"

            # 调用Tavily搜索专利信息
            from .mcp_tools import TavilySearchTool
            tavily = TavilySearchTool()
            result = await tavily.execute(query=search_query, max_results=limit)

            if result.get("success"):
                # 解析专利信息
                patents = []
                for res in result.get("results", []):
                    url = res.get("url", "")
                    if "patents.google.com" in url:
                        patents.append({
                            "title": res.get("title", ""),
                            "url": url,
                            "snippet": res.get("content", "")[:200]
                        })

                summary = f"""【专利搜索结果】查询: {query}

搜索类型: {search_type}
专利局范围: {patent_office}
找到专利: {len(patents)} 条

"""
                for i, p in enumerate(patents[:limit], 1):
                    summary += f"{i}. {p['title']}\n"
                    summary += f"   {p['snippet']}...\n"
                    summary += f"   链接: {p['url']}\n\n"

                if not patents:
                    summary += "未找到相关专利，建议:\n"
                    summary += "1. 尝试不同的关键词\n"
                    summary += "2. 使用英文搜索可能获得更多结果\n"
                    summary += "3. 直接访问 patents.google.com 搜索\n"

                return {
                    "success": True,
                    "summary": summary,
                    "data": {
                        "query": query,
                        "search_type": search_type,
                        "patents": patents
                    }
                }
            else:
                return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"专利搜索出错: {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索内容（公司名、发明人名或技术关键词）"
                    },
                    "search_type": {
                        "type": "string",
                        "description": "搜索类型",
                        "enum": ["keyword", "assignee", "inventor"],
                        "default": "keyword"
                    },
                    "patent_office": {
                        "type": "string",
                        "description": "专利局范围",
                        "enum": ["all", "USPTO", "EPO", "CNIPA", "WIPO"],
                        "default": "all"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }


# ==================== 5. 舆情监控工具 ====================

class SentimentMonitorTool(Tool):
    """
    Sentiment Monitoring Tool

    Monitor online sentiment for companies/projects, identify negative news and risk signals
    """

    def __init__(self):
        super().__init__(
            name="sentiment_monitor",
            description="""Monitor target company or project's online sentiment.

Features:
- Negative news tracking
- Social media sentiment analysis
- Risk signal identification
- Popularity trend analysis

Use cases:
- Sentiment check during investment due diligence
- Risk monitoring for portfolio companies
- Industry negative event tracking
"""
        )

    async def execute(
        self,
        target: str,
        monitor_type: str = "comprehensive",
        time_range: str = "week",
        focus_areas: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Monitor sentiment for a target

        Args:
            target: Monitoring target (company name/project name/person name)
            monitor_type: Monitoring type
                - comprehensive: Comprehensive sentiment
                - negative: Negative news
                - social: Social media
                - regulatory: Regulatory updates
            time_range: Time range (day/week/month)
            focus_areas: Focus areas (e.g. ["financial fraud", "executive departure", "litigation"])
        """
        try:
            results = {
                "negative_news": [],
                "regulatory_news": [],
                "social_sentiment": {},
                "risk_signals": []
            }

            # Build search query
            from .mcp_tools import TavilySearchTool
            tavily = TavilySearchTool()

            # 1. Negative news search
            negative_keywords = [
                "negative", "problem", "risk", "investigation", "penalty", "lawsuit", "layoff",
                "loss", "decline", "scandal", "violation", "fraud", "controversy"
            ]

            if monitor_type in ["comprehensive", "negative"]:
                neg_query = f"{target} ({' OR '.join(negative_keywords[:5])})"
                neg_result = await tavily.execute(
                    query=neg_query,
                    topic="news",
                    time_range=time_range,
                    max_results=5
                )
                if neg_result.get("success"):
                    results["negative_news"] = neg_result.get("results", [])

            # 2. Regulatory updates search
            if monitor_type in ["comprehensive", "regulatory"]:
                reg_query = f"{target} (regulatory OR penalty OR investigation OR compliance OR notice)"
                reg_result = await tavily.execute(
                    query=reg_query,
                    topic="news",
                    time_range=time_range,
                    max_results=5
                )
                if reg_result.get("success"):
                    results["regulatory_news"] = reg_result.get("results", [])

            # 3. Specific focus areas
            if focus_areas:
                for area in focus_areas[:3]:
                    area_result = await tavily.execute(
                        query=f"{target} {area}",
                        topic="news",
                        time_range=time_range,
                        max_results=3
                    )
                    if area_result.get("success") and area_result.get("results"):
                        results["risk_signals"].append({
                            "area": area,
                            "news": area_result.get("results", [])
                        })

            # Generate sentiment report
            time_range_label = {"day": "24 hours", "week": "1 week", "month": "1 month"}.get(time_range, time_range)
            summary = f"""【Sentiment Monitoring Report】{target}

📅 Monitoring Period: Last {time_range_label}
📊 Monitoring Type: {monitor_type}

"""

            # Negative news summary
            neg_count = len(results["negative_news"])
            summary += f"🔴 Negative News: Found {neg_count} items\n"
            if results["negative_news"]:
                for i, news in enumerate(results["negative_news"][:3], 1):
                    summary += f"   {i}. {news.get('title', 'N/A')}\n"
                    summary += f"      Source: {news.get('url', 'N/A')}\n"
            else:
                summary += "   No significant negative news found ✅\n"

            # Regulatory updates summary
            reg_count = len(results["regulatory_news"])
            summary += f"\n⚖️ Regulatory Updates: Found {reg_count} items\n"
            if results["regulatory_news"]:
                for i, news in enumerate(results["regulatory_news"][:3], 1):
                    summary += f"   {i}. {news.get('title', 'N/A')}\n"
            else:
                summary += "   No regulatory-related news found ✅\n"

            # Risk signals
            if results["risk_signals"]:
                summary += f"\n⚠️ Focus Areas:\n"
                for signal in results["risk_signals"]:
                    summary += f"   【{signal['area']}】: {len(signal['news'])} related news items\n"

            # Risk assessment
            total_negative = neg_count + reg_count + sum(len(s["news"]) for s in results["risk_signals"])
            if total_negative == 0:
                risk_level = "🟢 Low Risk - No significant negative sentiment found"
            elif total_negative <= 3:
                risk_level = "🟡 Low-Medium Risk - Some negative information exists"
            elif total_negative <= 7:
                risk_level = "🟠 Medium Risk - Multiple negative items, requires attention"
            else:
                risk_level = "🔴 High Risk - Dense negative sentiment, recommend in-depth investigation"

            summary += f"\n📈 Sentiment Risk Assessment: {risk_level}\n"
            summary += f"   Total Negative Items: {total_negative}\n"

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "target": target,
                    "time_range": time_range,
                    "negative_count": neg_count,
                    "regulatory_count": reg_count,
                    "total_negative": total_negative,
                    "results": results
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"Sentiment monitoring error: {str(e)}"
            }

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Monitoring target (company name/project name/person name)"
                    },
                    "monitor_type": {
                        "type": "string",
                        "description": "Monitoring type",
                        "enum": ["comprehensive", "negative", "social", "regulatory"],
                        "default": "comprehensive"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range",
                        "enum": ["day", "week", "month"],
                        "default": "week"
                    },
                    "focus_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Focus areas, e.g. ['financial fraud', 'executive departure']"
                    }
                },
                "required": ["target"]
            }
        }


# ==================== Export Tool List ====================

__all__ = [
    "ChinaMarketDataTool",
    "CompanyRegistryTool",
    "GitHubAnalyzerTool",
    "PatentSearchTool",
    "SentimentMonitorTool"
]
