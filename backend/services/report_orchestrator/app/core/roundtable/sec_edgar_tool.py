"""
SEC EDGAR MCP Tool
获取美国上市公司官方财务披露文件
"""
import httpx
from typing import Any, Dict, Optional
from .tool import Tool


class SECEdgarTool(Tool):
    """
    SEC EDGAR API工具

    通过 SEC官方API 获取上市公司财务披露
    支持的文件类型: 10-K, 10-Q, 8-K, DEF 14A
    """

    def __init__(
        self,
        base_url: str = "https://data.sec.gov",
        user_agent: str = "Magellan AI Investment Platform contact@example.com"
    ):
        super().__init__(
            name="sec_edgar",
            description="获取美国上市公司的官方SEC财务披露文件，包括年报(10-K)、季报(10-Q)、重大事件(8-K)等。"
        )
        self.base_url = base_url
        self.headers = {
            "User-Agent": user_agent,  # SEC要求提供User-Agent
            "Accept-Encoding": "gzip, deflate"
        }

    async def execute(
        self,
        action: str,
        ticker: str = None,
        cik: str = None,
        form_type: str = "10-K",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行SEC EDGAR查询

        Args:
            action: 操作类型 (search_filings, get_company_facts)
            ticker: 股票代码 (如 AAPL)
            cik: CIK号码 (Central Index Key)
            form_type: 文件类型 (10-K, 10-Q, 8-K, DEF 14A)
            **kwargs: 其他参数

        Returns:
            查询结果
        """
        try:
            if action == "search_filings":
                return await self._search_filings(ticker, cik, form_type, **kwargs)
            elif action == "get_company_facts":
                return await self._get_company_facts(ticker, cik)
            elif action == "get_filing_content":
                filing_url = kwargs.get("filing_url")
                return await self._get_filing_content(filing_url)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "summary": f"不支持的操作: {action}"
                }

        except Exception as e:
            print(f"[SECEdgarTool] Error executing action '{action}': {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"SEC EDGAR查询失败: {str(e)}"
            }

    async def _search_filings(
        self,
        ticker: str,
        cik: str,
        form_type: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """搜索公司的财务披露文件"""
        # 如果提供ticker，先转换为CIK
        if ticker and not cik:
            cik = await self._ticker_to_cik(ticker)
            if not cik:
                return {
                    "success": False,
                    "summary": f"无法找到股票代码 {ticker} 对应的CIK号码。可能不是美国上市公司。"
                }

        # 格式化CIK (10位，前面补0)
        cik_padded = str(cik).zfill(10)

        # 搜索披露文件
        url = f"{self.base_url}/submissions/CIK{cik_padded}.json"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"无法获取CIK {cik}的数据: {str(e)}"
            }

        # 提取最近的指定类型文件
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        filing_dates = filings.get("filingDate", [])
        accession_numbers = filings.get("accessionNumber", [])
        primary_documents = filings.get("primaryDocument", [])

        # 过滤指定类型
        filtered_filings = []
        for i, form in enumerate(forms):
            if form == form_type and len(filtered_filings) < limit:
                # 移除accession number中的连字符
                accession_clean = accession_numbers[i].replace("-", "")
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{primary_documents[i]}"

                filtered_filings.append({
                    "form_type": form,
                    "filing_date": filing_dates[i],
                    "accession_number": accession_numbers[i],
                    "primary_document": primary_documents[i],
                    "url": filing_url
                })

        if not filtered_filings:
            return {
                "success": True,
                "summary": f"未找到 {data.get('name', ticker or cik)} 的 {form_type} 文件。",
                "company_name": data.get("name", ticker or cik),
                "cik": cik,
                "filings": []
            }

        # 构建摘要
        company_name = data.get("name", ticker or cik)
        summary = f"找到 {company_name} 的 {len(filtered_filings)} 个 {form_type} 文件:\n"
        for filing in filtered_filings:
            summary += f"\n- {filing['filing_date']}: {filing['url']}"

        return {
            "success": True,
            "summary": summary,
            "company_name": company_name,
            "cik": cik,
            "filings": filtered_filings
        }

    async def _get_company_facts(
        self,
        ticker: str,
        cik: str
    ) -> Dict[str, Any]:
        """获取公司的XBRL财务数据"""
        if ticker and not cik:
            cik = await self._ticker_to_cik(ticker)
            if not cik:
                return {
                    "success": False,
                    "summary": f"无法找到股票代码 {ticker} 对应的CIK号码。"
                }

        cik_padded = str(cik).zfill(10)
        url = f"{self.base_url}/api/xbrl/companyfacts/CIK{cik_padded}.json"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"无法获取CIK {cik}的财务数据: {str(e)}"
            }

        # 提取关键财务指标
        facts = data.get("facts", {})
        us_gaap = facts.get("us-gaap", {})

        # 常用指标
        key_metrics = {
            "Revenue": "Revenues",
            "NetIncome": "NetIncomeLoss",
            "Assets": "Assets",
            "Liabilities": "Liabilities",
            "StockholdersEquity": "StockholdersEquity",
            "OperatingCashFlow": "NetCashProvidedByUsedInOperatingActivities",
            "GrossProfit": "GrossProfit",
            "OperatingIncome": "OperatingIncomeLoss",
            "CashAndEquivalents": "CashAndCashEquivalentsAtCarryingValue"
        }

        extracted_data = {}
        for metric_name, xbrl_tag in key_metrics.items():
            if xbrl_tag in us_gaap:
                metric_data = us_gaap[xbrl_tag]
                # 获取最新年度数据
                units = metric_data.get("units", {})
                usd_data = units.get("USD", [])
                if usd_data:
                    # 按日期排序，取最新的年度数据(10-K)
                    annual_data = [d for d in usd_data if d.get("form") == "10-K"]
                    if annual_data:
                        latest = sorted(annual_data, key=lambda x: x.get("end", ""), reverse=True)[0]
                        extracted_data[metric_name] = {
                            "value": latest.get("val"),
                            "date": latest.get("end"),
                            "form": latest.get("form"),
                            "fy": latest.get("fy")  # Fiscal year
                        }

        if not extracted_data:
            return {
                "success": True,
                "summary": f"未能从 {data.get('entityName', ticker)} 提取到标准财务指标。",
                "company_name": data.get("entityName"),
                "cik": cik,
                "metrics": {}
            }

        # 构建摘要
        summary = f"提取了 {data.get('entityName', ticker)} 的关键财务指标:\n"
        for metric, info in extracted_data.items():
            value = info['value']
            # 格式化大数字
            if value > 1_000_000_000:
                formatted_value = f"${value/1_000_000_000:.2f}B"
            elif value > 1_000_000:
                formatted_value = f"${value/1_000_000:.2f}M"
            else:
                formatted_value = f"${value:,.0f}"

            summary += f"\n- {metric}: {formatted_value} (FY{info.get('fy', 'N/A')}, 截至 {info['date']})"

        return {
            "success": True,
            "summary": summary,
            "company_name": data.get("entityName"),
            "cik": cik,
            "metrics": extracted_data
        }

    async def _get_filing_content(self, filing_url: str) -> Dict[str, Any]:
        """获取文件内容 (简化版，只返回URL)"""
        # 注意: 完整实现需要解析HTML/XBRL，这里简化处理
        return {
            "success": True,
            "summary": f"文件URL: {filing_url}\n请访问该URL查看完整内容。",
            "url": filing_url
        }

    async def _ticker_to_cik(self, ticker: str) -> Optional[str]:
        """将股票代码转换为CIK

        使用备用映射，因为SEC API的company_tickers.json可能不稳定
        """
        # 常见股票的CIK映射（硬编码最常用的）
        ticker_to_cik_map = {
            "AAPL": "320193",
            "MSFT": "789019",
            "GOOGL": "1652044",
            "GOOG": "1652044",
            "AMZN": "1018724",
            "TSLA": "1318605",
            "META": "1326801",
            "FB": "1326801",
            "NVDA": "1045810",
            "JPM": "19617",
            "V": "1403161",
            "WMT": "104169",
            "JNJ": "200406",
            "PG": "80424",
            "MA": "1141391",
            "UNH": "731766",
            "HD": "354950",
            "DIS": "1744489",
            "BAC": "70858",
            "NFLX": "1065280",
            "ADBE": "796343",
            "CRM": "1108524",
            "CSCO": "858877",
            "PFE": "78003",
            "TMO": "97745",
            "ABBV": "1551152",
            "COST": "909832",
            "AVGO": "1730168",
            "NKE": "320187",
            "ORCL": "1341439"
        }

        ticker_upper = ticker.upper()

        # 先尝试从映射表获取
        if ticker_upper in ticker_to_cik_map:
            return ticker_to_cik_map[ticker_upper]

        # 尝试从SEC API获取（作为备选）
        url = f"https://www.sec.gov/cgi-bin/browse-edgar"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 使用搜索API
                params = {
                    "action": "getcompany",
                    "ticker": ticker,
                    "output": "json"
                }
                response = await client.get(url, params=params, headers=self.headers)

                # SEC的这个API可能返回HTML，我们简化处理
                # 如果ticker不在映射表中，返回None让用户手动提供CIK
                return None

        except Exception as e:
            print(f"[SECEdgarTool] Could not find CIK for ticker {ticker}: {e}")
            return None

    def to_schema(self) -> Dict[str, Any]:
        """返回工具的Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search_filings", "get_company_facts"],
                        "description": "操作类型: search_filings(搜索披露文件) 或 get_company_facts(获取财务数据)"
                    },
                    "ticker": {
                        "type": "string",
                        "description": "股票代码，如 AAPL, TSLA (仅限美股)"
                    },
                    "cik": {
                        "type": "string",
                        "description": "公司CIK号码 (可选，如果提供ticker则自动查询)"
                    },
                    "form_type": {
                        "type": "string",
                        "enum": ["10-K", "10-Q", "8-K", "DEF 14A"],
                        "description": "文件类型: 10-K(年报), 10-Q(季报), 8-K(重大事件), DEF 14A(代理声明)",
                        "default": "10-K"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回文件数量限制",
                        "default": 5
                    }
                },
                "required": ["action"]
            }
        }
