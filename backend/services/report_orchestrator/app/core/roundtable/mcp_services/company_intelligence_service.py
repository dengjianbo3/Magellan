"""
企业信息 MCP 服务
提供企业工商信息、背景调查、关联分析等功能
"""
import os
import re
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging
from app.services.web_search_access import search_web as shared_search_web
from app.core.service_endpoints import get_web_search_url

logger = logging.getLogger(__name__)


class CompanyStatus(Enum):
    """企业状态"""
    ACTIVE = "active"           # 正常经营
    SUSPENDED = "suspended"     # 暂停营业
    REVOKED = "revoked"         # 吊销
    CANCELLED = "cancelled"     # 注销
    UNKNOWN = "unknown"         # 未知


@dataclass
class CompanyBasicInfo:
    """企业基本信息"""
    name: str
    legal_representative: str
    registered_capital: str
    establishment_date: str
    status: CompanyStatus
    unified_credit_code: str
    company_type: str
    industry: str
    address: str
    business_scope: str


class CompanyIntelligenceService:
    """
    企业信息服务

    提供企业工商信息、背景调查、风险信息等
    通过整合多个数据源提供全面的企业画像
    """

    def __init__(self, tavily_api_key: str = None, web_search_url: str = None):
        self.timeout = 30
        self.tavily_api_key = tavily_api_key or os.environ.get("TAVILY_API_KEY", "")
        self.web_search_url = web_search_url or get_web_search_url()
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 3600  # 缓存1小时

    def _get_cache_key(self, method: str, **params) -> str:
        """生成缓存键"""
        param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()) if v)
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

    async def _search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """执行网络搜索"""
        try:
            return await shared_search_web(
                self.web_search_url,
                query=query,
                max_results=max_results,
                include_date=True,
                timeout=float(self.timeout),
            )
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return []

    async def get_company_basic_info(self, company_name: str) -> Dict[str, Any]:
        """
        获取企业基本信息

        Args:
            company_name: 企业名称

        Returns:
            企业基本信息
        """
        cache_key = self._get_cache_key("basic_info", company=company_name)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # 通过搜索获取企业基本信息
            query = f"{company_name} 企业工商信息 注册资本 法定代表人 经营范围"
            search_results = await self._search_web(query, max_results=5)

            # 解析搜索结果提取关键信息
            info = await self._extract_company_info(company_name, search_results)

            result = {
                "success": True,
                "data": info,
                "summary": self._format_company_summary(info)
            }

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Failed to get company info for {company_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取企业信息失败: {str(e)}"
            }

    async def _extract_company_info(
        self,
        company_name: str,
        search_results: List[Dict]
    ) -> Dict[str, Any]:
        """从搜索结果中提取企业信息"""
        info = {
            "name": company_name,
            "legal_representative": "",
            "registered_capital": "",
            "establishment_date": "",
            "status": "active",
            "unified_credit_code": "",
            "company_type": "",
            "industry": "",
            "address": "",
            "business_scope": "",
            "sources": []
        }

        combined_content = ""
        for result in search_results:
            combined_content += result.get("content", "") + "\n"
            info["sources"].append({
                "title": result.get("title", ""),
                "url": result.get("url", "")
            })

        # 使用正则表达式提取关键信息
        patterns = {
            "legal_representative": [
                r"法定代表人[：:]\s*([^\s,，。]+)",
                r"法人[：:]\s*([^\s,，。]+)"
            ],
            "registered_capital": [
                r"注册资本[：:]\s*([^\s,，。]+(?:万|亿)?(?:人民币|美元|港元)?)",
                r"注册资金[：:]\s*([^\s,，。]+)"
            ],
            "establishment_date": [
                r"成立(?:日期|时间)[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]?\d{0,2}日?)",
                r"注册(?:日期|时间)[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]?\d{0,2}日?)"
            ],
            "unified_credit_code": [
                r"统一社会信用代码[：:]\s*([A-Z0-9]{18})",
                r"信用代码[：:]\s*([A-Z0-9]{18})"
            ],
            "industry": [
                r"行业[：:]\s*([^\s,，。]+)",
                r"所属行业[：:]\s*([^\s,，。]+)"
            ],
            "address": [
                r"(?:注册)?地址[：:]\s*([^。\n]+)",
                r"经营地址[：:]\s*([^。\n]+)"
            ]
        }

        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, combined_content)
                if match:
                    info[field] = match.group(1).strip()
                    break

        return info

    def _format_company_summary(self, info: Dict) -> str:
        """格式化企业信息摘要"""
        parts = [f"【企业信息】{info.get('name', 'N/A')}"]

        if info.get("legal_representative"):
            parts.append(f"\n法定代表人: {info['legal_representative']}")
        if info.get("registered_capital"):
            parts.append(f"注册资本: {info['registered_capital']}")
        if info.get("establishment_date"):
            parts.append(f"成立日期: {info['establishment_date']}")
        if info.get("industry"):
            parts.append(f"行业: {info['industry']}")
        if info.get("status"):
            parts.append(f"经营状态: {info['status']}")

        return "\n".join(parts)

    async def get_shareholders(self, company_name: str) -> Dict[str, Any]:
        """
        获取股东信息

        Args:
            company_name: 企业名称

        Returns:
            股东信息
        """
        try:
            query = f"{company_name} 股东 股权结构 持股比例"
            search_results = await self._search_web(query, max_results=5)

            shareholders = []
            combined_content = ""
            for result in search_results:
                combined_content += result.get("content", "") + "\n"

            # 尝试提取股东信息
            shareholder_patterns = [
                r"([^\s,，]+)\s*(?:持股|占股|股份)\s*(\d+\.?\d*)[%％]",
                r"股东[：:]?\s*([^\s,，]+)"
            ]

            found_shareholders = set()
            for pattern in shareholder_patterns:
                matches = re.findall(pattern, combined_content)
                for match in matches:
                    if isinstance(match, tuple):
                        name, ratio = match
                        if name not in found_shareholders:
                            shareholders.append({
                                "name": name,
                                "ratio": f"{ratio}%"
                            })
                            found_shareholders.add(name)
                    else:
                        if match not in found_shareholders:
                            shareholders.append({"name": match, "ratio": "未知"})
                            found_shareholders.add(match)

            return {
                "success": True,
                "data": {
                    "company": company_name,
                    "shareholders": shareholders[:10],  # 最多10个
                    "sources": [{"title": r.get("title"), "url": r.get("url")} for r in search_results[:3]]
                },
                "summary": f"【股东信息】{company_name}\n" + "\n".join(
                    f"  • {s['name']}: {s['ratio']}" for s in shareholders[:5]
                ) if shareholders else f"未找到 {company_name} 的股东信息"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取股东信息失败: {str(e)}"
            }

    async def get_executives(self, company_name: str) -> Dict[str, Any]:
        """
        获取高管信息

        Args:
            company_name: 企业名称

        Returns:
            高管信息
        """
        try:
            query = f"{company_name} 高管 管理层 CEO 创始人 董事"
            search_results = await self._search_web(query, max_results=5)

            executives = []
            combined_content = ""
            for result in search_results:
                combined_content += result.get("content", "") + "\n"

            # 提取高管职位模式
            position_patterns = [
                r"(CEO|首席执行官|总经理|董事长|总裁|创始人|联合创始人|CTO|CFO|COO)[：:,，]?\s*([^\s,，。]+)",
                r"([^\s,，]+)\s*(?:担任|出任|现任)\s*(CEO|首席执行官|总经理|董事长|总裁|CTO|CFO|COO)"
            ]

            found_executives = {}
            for pattern in position_patterns:
                matches = re.findall(pattern, combined_content)
                for match in matches:
                    position, name = match if match[0] in ["CEO", "首席执行官", "总经理", "董事长", "总裁", "创始人", "联合创始人", "CTO", "CFO", "COO"] else (match[1], match[0])
                    if name and len(name) <= 10:  # 名字长度合理性检查
                        if name not in found_executives:
                            found_executives[name] = position

            executives = [{"name": name, "position": pos} for name, pos in found_executives.items()]

            return {
                "success": True,
                "data": {
                    "company": company_name,
                    "executives": executives[:10],
                    "sources": [{"title": r.get("title"), "url": r.get("url")} for r in search_results[:3]]
                },
                "summary": f"【高管信息】{company_name}\n" + "\n".join(
                    f"  • {e['position']}: {e['name']}" for e in executives[:5]
                ) if executives else f"未找到 {company_name} 的高管信息"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取高管信息失败: {str(e)}"
            }

    async def get_legal_cases(self, company_name: str) -> Dict[str, Any]:
        """
        获取法律诉讼信息

        Args:
            company_name: 企业名称

        Returns:
            法律诉讼信息
        """
        try:
            query = f"{company_name} 诉讼 法律纠纷 被执行 失信"
            search_results = await self._search_web(query, max_results=5)

            legal_cases = []
            for result in search_results:
                title = result.get("title", "")
                content = result.get("content", "")

                # 检查是否与法律案件相关
                legal_keywords = ["诉讼", "被告", "原告", "执行", "判决", "裁定", "仲裁", "失信"]
                if any(kw in title or kw in content for kw in legal_keywords):
                    legal_cases.append({
                        "title": title,
                        "content": content[:200],
                        "url": result.get("url", ""),
                        "date": result.get("published_date", "")
                    })

            risk_level = "低" if len(legal_cases) == 0 else "中" if len(legal_cases) <= 2 else "高"

            return {
                "success": True,
                "data": {
                    "company": company_name,
                    "cases_count": len(legal_cases),
                    "risk_level": risk_level,
                    "cases": legal_cases[:5]
                },
                "summary": f"【法律风险】{company_name}\n" +
                          f"风险等级: {risk_level}\n" +
                          f"相关案件/信息: {len(legal_cases)}条\n" +
                          ("\n".join(f"  • {c['title'][:50]}" for c in legal_cases[:3]) if legal_cases else "  暂未发现法律诉讼信息")
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取法律诉讼信息失败: {str(e)}"
            }

    async def get_investments(self, company_name: str) -> Dict[str, Any]:
        """
        获取对外投资信息

        Args:
            company_name: 企业名称

        Returns:
            对外投资信息
        """
        try:
            query = f"{company_name} 投资 子公司 控股 参股"
            search_results = await self._search_web(query, max_results=5)

            investments = []
            combined_content = ""
            for result in search_results:
                combined_content += result.get("content", "") + "\n"

            # 提取投资信息
            investment_patterns = [
                r"投资(?:了)?([^\s,，。]+(?:公司|集团|有限))",
                r"控股([^\s,，。]+(?:公司|集团|有限))",
                r"参股([^\s,，。]+(?:公司|集团|有限))"
            ]

            found_companies = set()
            for pattern in investment_patterns:
                matches = re.findall(pattern, combined_content)
                for match in matches:
                    if match and match != company_name and match not in found_companies:
                        investments.append({"company": match})
                        found_companies.add(match)

            return {
                "success": True,
                "data": {
                    "company": company_name,
                    "investments_count": len(investments),
                    "investments": investments[:10],
                    "sources": [{"title": r.get("title"), "url": r.get("url")} for r in search_results[:3]]
                },
                "summary": f"【对外投资】{company_name}\n" +
                          f"发现投资/参股企业: {len(investments)}家\n" +
                          ("\n".join(f"  • {i['company']}" for i in investments[:5]) if investments else "  暂未发现对外投资信息")
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取对外投资信息失败: {str(e)}"
            }

    async def get_risk_info(self, company_name: str) -> Dict[str, Any]:
        """
        获取企业风险信息综合报告

        Args:
            company_name: 企业名称

        Returns:
            风险信息汇总
        """
        try:
            # 并行获取多类风险信息
            tasks = [
                self._search_web(f"{company_name} 经营异常 行政处罚", 3),
                self._search_web(f"{company_name} 失信被执行人 老赖", 3),
                self._search_web(f"{company_name} 负面新闻 风险 问题", 3)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            risk_items = []
            risk_score = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    continue
                category = ["经营异常/行政处罚", "失信被执行", "负面舆情"][i]
                for item in result:
                    risk_items.append({
                        "category": category,
                        "title": item.get("title", ""),
                        "content": item.get("content", "")[:150],
                        "url": item.get("url", ""),
                        "date": item.get("published_date", "")
                    })
                    risk_score += 1

            # 计算风险等级
            if risk_score == 0:
                risk_level = "低风险 🟢"
            elif risk_score <= 3:
                risk_level = "中低风险 🟡"
            elif risk_score <= 6:
                risk_level = "中高风险 🟠"
            else:
                risk_level = "高风险 🔴"

            return {
                "success": True,
                "data": {
                    "company": company_name,
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                    "risk_items": risk_items[:10]
                },
                "summary": f"""【企业风险报告】{company_name}

📊 风险等级: {risk_level}
📋 发现风险信号: {len(risk_items)}条

风险详情:
""" + ("\n".join(f"  [{r['category']}] {r['title'][:40]}" for r in risk_items[:5]) if risk_items else "  暂未发现明显风险信号 ✅")
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取风险信息失败: {str(e)}"
            }

    async def get_full_profile(self, company_name: str) -> Dict[str, Any]:
        """
        获取企业完整画像

        Args:
            company_name: 企业名称

        Returns:
            企业完整信息
        """
        try:
            # 并行获取所有信息
            tasks = [
                self.get_company_basic_info(company_name),
                self.get_shareholders(company_name),
                self.get_executives(company_name),
                self.get_legal_cases(company_name),
                self.get_risk_info(company_name)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            basic_info = results[0] if not isinstance(results[0], Exception) else {"success": False}
            shareholders = results[1] if not isinstance(results[1], Exception) else {"success": False}
            executives = results[2] if not isinstance(results[2], Exception) else {"success": False}
            legal_cases = results[3] if not isinstance(results[3], Exception) else {"success": False}
            risk_info = results[4] if not isinstance(results[4], Exception) else {"success": False}

            # 构建完整画像
            profile = {
                "company": company_name,
                "basic_info": basic_info.get("data", {}) if basic_info.get("success") else {},
                "shareholders": shareholders.get("data", {}).get("shareholders", []) if shareholders.get("success") else [],
                "executives": executives.get("data", {}).get("executives", []) if executives.get("success") else [],
                "legal_risk": {
                    "cases_count": legal_cases.get("data", {}).get("cases_count", 0),
                    "risk_level": legal_cases.get("data", {}).get("risk_level", "未知")
                } if legal_cases.get("success") else {},
                "overall_risk": {
                    "level": risk_info.get("data", {}).get("risk_level", "未知"),
                    "score": risk_info.get("data", {}).get("risk_score", 0)
                } if risk_info.get("success") else {}
            }

            summary = f"""【企业完整画像】{company_name}
═══════════════════════════════════════

📋 基本信息:
{basic_info.get('summary', '  信息获取失败')}

👥 股东结构:
{shareholders.get('summary', '  信息获取失败').split(chr(10), 1)[-1] if shareholders.get('success') else '  信息获取失败'}

👔 管理层:
{executives.get('summary', '  信息获取失败').split(chr(10), 1)[-1] if executives.get('success') else '  信息获取失败'}

⚖️ 法律风险:
{legal_cases.get('summary', '  信息获取失败').split(chr(10), 1)[-1] if legal_cases.get('success') else '  信息获取失败'}

🔍 综合风险:
{risk_info.get('summary', '  信息获取失败').split(chr(10), 1)[-1] if risk_info.get('success') else '  信息获取失败'}
"""

            return {
                "success": True,
                "data": profile,
                "summary": summary
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"获取企业画像失败: {str(e)}"
            }


# 创建全局服务实例
_company_service: Optional[CompanyIntelligenceService] = None


def get_company_intelligence_service() -> CompanyIntelligenceService:
    """获取企业信息服务实例"""
    global _company_service
    if _company_service is None:
        _company_service = CompanyIntelligenceService()
    return _company_service
