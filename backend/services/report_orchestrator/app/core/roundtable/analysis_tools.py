"""
Phase 2 分析计算工具
为圆桌讨论专家提供的分析和计算类工具
"""
from typing import Any, Dict, List

from .tool import Tool
from ..service_endpoints import DEFAULT_WEB_SEARCH_URL


class DCFCalculatorTool(Tool):
    """
    DCF Discounted Cash Flow Valuation Tool

    Calculate intrinsic value of enterprises, supports multiple valuation scenarios
    """

    def __init__(self):
        super().__init__(
            name="dcf_calculator",
            description="""DCF (Discounted Cash Flow) valuation calculator.

Features:
- Calculate enterprise value based on free cash flow
- Sensitivity analysis (WACC and terminal growth rate)
- Equity value and per-share valuation calculation
- Support for multiple scenario analysis

Use cases:
- Evaluate target company's intrinsic value
- Investment decision support
- Valuation range analysis"""
        )

    async def execute(
        self,
        base_revenue: float = None,
        revenue_growth_rates: List[float] = None,
        operating_margin: float = None,
        tax_rate: float = 0.25,
        depreciation_ratio: float = 0.05,
        capex_ratio: float = 0.08,
        nwc_ratio: float = 0.10,
        wacc: float = 0.10,
        terminal_growth: float = 0.03,
        shares_outstanding: float = None,
        net_debt: float = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行DCF估值计算

        Args:
            base_revenue: 基准年营收（百万元/美元）
            revenue_growth_rates: 未来5年营收增长率列表 [0.3, 0.25, 0.2, 0.15, 0.1]
            operating_margin: 营业利润率
            tax_rate: 有效税率 (默认25%)
            depreciation_ratio: 折旧占营收比例 (默认5%)
            capex_ratio: 资本支出占营收比例 (默认8%)
            nwc_ratio: 净营运资本变动占营收增量比例 (默认10%)
            wacc: 加权平均资本成本 (默认10%)
            terminal_growth: 永续增长率 (默认3%)
            shares_outstanding: 总股本（百万股）
            net_debt: 净债务（百万元/美元）

        Returns:
            估值结果和敏感性分析
        """
        try:
            # 验证必要参数
            if base_revenue is None:
                return {
                    "success": False,
                    "error": "缺少必要参数: base_revenue (基准年营收)",
                    "summary": "DCF计算失败: 请提供基准年营收数据"
                }

            if revenue_growth_rates is None:
                # 默认增长率假设
                revenue_growth_rates = [0.20, 0.15, 0.12, 0.10, 0.08]

            if operating_margin is None:
                return {
                    "success": False,
                    "error": "缺少必要参数: operating_margin (营业利润率)",
                    "summary": "DCF计算失败: 请提供营业利润率数据"
                }

            # 计算预测期现金流
            projections = []
            revenue = base_revenue
            total_pv_fcf = 0

            for year, growth in enumerate(revenue_growth_rates, 1):
                prev_revenue = revenue
                revenue = revenue * (1 + growth)

                # 计算各项
                ebit = revenue * operating_margin
                taxes = ebit * tax_rate
                nopat = ebit - taxes
                depreciation = revenue * depreciation_ratio
                capex = revenue * capex_ratio
                delta_nwc = (revenue - prev_revenue) * nwc_ratio

                # 自由现金流 = NOPAT + 折旧 - 资本支出 - 营运资本变动
                fcf = nopat + depreciation - capex - delta_nwc

                # 现值
                discount_factor = (1 + wacc) ** year
                pv_fcf = fcf / discount_factor
                total_pv_fcf += pv_fcf

                projections.append({
                    "year": year,
                    "revenue": round(revenue, 2),
                    "growth_rate": f"{growth*100:.1f}%",
                    "ebit": round(ebit, 2),
                    "nopat": round(nopat, 2),
                    "fcf": round(fcf, 2),
                    "pv_fcf": round(pv_fcf, 2)
                })

            # 计算终值
            terminal_year_fcf = projections[-1]["fcf"]
            terminal_value = terminal_year_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
            pv_terminal_value = terminal_value / ((1 + wacc) ** len(revenue_growth_rates))

            # 企业价值
            enterprise_value = total_pv_fcf + pv_terminal_value

            # 股权价值
            equity_value = enterprise_value - net_debt

            # 每股价值
            per_share_value = None
            if shares_outstanding and shares_outstanding > 0:
                per_share_value = equity_value / shares_outstanding

            # 敏感性分析
            sensitivity = self._calculate_sensitivity(
                terminal_year_fcf,
                wacc,
                terminal_growth,
                total_pv_fcf,
                len(revenue_growth_rates),
                net_debt,
                shares_outstanding
            )

            # 构建结果摘要
            summary = f"""【DCF估值分析结果】

📊 核心假设:
  基准营收: {base_revenue:,.2f}百万
  营业利润率: {operating_margin*100:.1f}%
  WACC: {wacc*100:.1f}%
  永续增长率: {terminal_growth*100:.1f}%

📈 预测期现金流现值: {total_pv_fcf:,.2f}百万
📈 终值现值: {pv_terminal_value:,.2f}百万

💰 企业价值(EV): {enterprise_value:,.2f}百万
💰 净债务: {net_debt:,.2f}百万
💰 股权价值: {equity_value:,.2f}百万"""

            if per_share_value:
                summary += f"\n💰 每股价值: {per_share_value:,.2f}"

            summary += f"""

📉 敏感性分析 (WACC vs 永续增长率):
{self._format_sensitivity_table(sensitivity)}

⚠️ 注意事项:
- DCF对假设高度敏感，需谨慎使用
- 建议结合可比公司法交叉验证
- 高增长公司DCF估值波动较大"""

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "assumptions": {
                        "base_revenue": base_revenue,
                        "revenue_growth_rates": revenue_growth_rates,
                        "operating_margin": operating_margin,
                        "tax_rate": tax_rate,
                        "wacc": wacc,
                        "terminal_growth": terminal_growth
                    },
                    "projections": projections,
                    "valuation": {
                        "pv_fcf": round(total_pv_fcf, 2),
                        "terminal_value": round(terminal_value, 2),
                        "pv_terminal_value": round(pv_terminal_value, 2),
                        "enterprise_value": round(enterprise_value, 2),
                        "net_debt": round(net_debt, 2),
                        "equity_value": round(equity_value, 2),
                        "per_share_value": round(per_share_value, 2) if per_share_value else None
                    },
                    "sensitivity": sensitivity
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"DCF计算出错: {str(e)}"
            }

    def _calculate_sensitivity(
        self,
        terminal_fcf: float,
        base_wacc: float,
        base_growth: float,
        pv_fcf: float,
        years: int,
        net_debt: float,
        shares: float
    ) -> Dict[str, Any]:
        """计算敏感性分析矩阵"""
        wacc_range = [base_wacc - 0.02, base_wacc - 0.01, base_wacc, base_wacc + 0.01, base_wacc + 0.02]
        growth_range = [base_growth - 0.01, base_growth - 0.005, base_growth, base_growth + 0.005, base_growth + 0.01]

        matrix = []
        for wacc in wacc_range:
            row = []
            for growth in growth_range:
                if wacc <= growth:
                    row.append(None)  # Invalid combination
                    continue
                terminal_value = terminal_fcf * (1 + growth) / (wacc - growth)
                pv_terminal = terminal_value / ((1 + wacc) ** years)
                ev = pv_fcf + pv_terminal
                equity = ev - net_debt
                if shares and shares > 0:
                    row.append(round(equity / shares, 2))
                else:
                    row.append(round(equity, 2))
            matrix.append(row)

        return {
            "wacc_range": [f"{w*100:.1f}%" for w in wacc_range],
            "growth_range": [f"{g*100:.2f}%" for g in growth_range],
            "matrix": matrix
        }

    def _format_sensitivity_table(self, sensitivity: Dict) -> str:
        """格式化敏感性分析表格"""
        wacc_labels = sensitivity["wacc_range"]
        growth_labels = sensitivity["growth_range"]
        matrix = sensitivity["matrix"]

        # 表头
        header = "WACC\\Growth | " + " | ".join(growth_labels)
        separator = "-" * len(header)

        rows = [header, separator]
        for i, wacc in enumerate(wacc_labels):
            values = [f"{v:,.0f}" if v else "N/A" for v in matrix[i]]
            rows.append(f"{wacc:>10} | " + " | ".join(f"{v:>6}" for v in values))

        return "\n".join(rows)

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "base_revenue": {
                        "type": "number",
                        "description": "基准年营收（百万元/美元）"
                    },
                    "revenue_growth_rates": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "未来5年营收增长率列表，如 [0.3, 0.25, 0.2, 0.15, 0.1]"
                    },
                    "operating_margin": {
                        "type": "number",
                        "description": "营业利润率，如 0.15 表示15%"
                    },
                    "tax_rate": {
                        "type": "number",
                        "description": "有效税率，默认0.25"
                    },
                    "wacc": {
                        "type": "number",
                        "description": "加权平均资本成本，如 0.10 表示10%"
                    },
                    "terminal_growth": {
                        "type": "number",
                        "description": "永续增长率，如 0.03 表示3%"
                    },
                    "shares_outstanding": {
                        "type": "number",
                        "description": "总股本（百万股）"
                    },
                    "net_debt": {
                        "type": "number",
                        "description": "净债务（百万元/美元），债务为正"
                    }
                },
                "required": ["base_revenue", "operating_margin"]
            }
        }


class ComparableAnalysisTool(Tool):
    """
    Comparable Company Analysis Tool

    Calculate target company's fair valuation by comparing industry peer multiples
    """

    def __init__(self, web_search_url: str = DEFAULT_WEB_SEARCH_URL):
        super().__init__(
            name="comparable_analysis",
            description="""Comparable company valuation analysis.

Features:
- Get comparable company multiples (P/E, P/S, EV/EBITDA, P/B)
- Calculate industry median and average
- Estimate target company's implied valuation range
- Support multiple valuation metrics

Use cases:
- Cross-validate with DCF valuation
- Quick estimate of fair valuation range
- IPO pricing reference"""
        )
        self.web_search_url = web_search_url

    async def execute(
        self,
        target_metrics: Dict[str, float] = None,
        comparable_companies: List[Dict] = None,
        industry: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行可比公司分析

        Args:
            target_metrics: 目标公司财务指标
                {
                    "revenue": 营收（百万）,
                    "net_income": 净利润（百万）,
                    "ebitda": EBITDA（百万）,
                    "book_value": 账面价值（百万）,
                    "shares_outstanding": 总股本（百万股）
                }
            comparable_companies: 可比公司数据列表（可选，如不提供则使用行业平均）
                [
                    {
                        "name": "公司A",
                        "market_cap": 市值,
                        "pe": P/E,
                        "ps": P/S,
                        "ev_ebitda": EV/EBITDA,
                        "pb": P/B
                    }
                ]
            industry: 行业（用于获取行业平均倍数）

        Returns:
            估值分析结果
        """
        try:
            if target_metrics is None:
                return {
                    "success": False,
                    "error": "缺少目标公司财务指标",
                    "summary": "可比公司分析失败: 请提供目标公司的财务指标"
                }

            # 如果没有提供可比公司，使用行业平均倍数
            if comparable_companies is None or len(comparable_companies) == 0:
                comparable_companies = self._get_industry_multiples(industry)

            # 计算可比公司倍数统计
            multiples_stats = self._calculate_multiples_stats(comparable_companies)

            # 计算目标公司隐含估值
            valuations = self._calculate_implied_valuations(target_metrics, multiples_stats)

            # 构建结果摘要
            summary = f"""【可比公司估值分析】

📊 可比公司样本: {len(comparable_companies)}家
{self._format_comparable_table(comparable_companies)}

📈 估值倍数统计:
{self._format_multiples_stats(multiples_stats)}

💰 目标公司隐含估值:
{self._format_valuations(valuations, target_metrics)}

⚠️ 注意事项:
- 可比公司的选择对结果影响显著
- 建议选择业务模式、规模、增长阶段相似的公司
- 不同估值方法可能给出差异较大的结果，需综合判断"""

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "comparable_companies": comparable_companies,
                    "multiples_stats": multiples_stats,
                    "implied_valuations": valuations
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"可比公司分析出错: {str(e)}"
            }

    def _get_industry_multiples(self, industry: str) -> List[Dict]:
        """获取行业平均估值倍数"""
        # 预设行业倍数数据
        industry_data = {
            "technology": [
                {"name": "行业高位", "pe": 45, "ps": 12, "ev_ebitda": 25, "pb": 8},
                {"name": "行业中位", "pe": 30, "ps": 8, "ev_ebitda": 18, "pb": 5},
                {"name": "行业低位", "pe": 20, "ps": 4, "ev_ebitda": 12, "pb": 3}
            ],
            "saas": [
                {"name": "高增长SaaS", "pe": 60, "ps": 15, "ev_ebitda": 35, "pb": 10},
                {"name": "成熟SaaS", "pe": 35, "ps": 8, "ev_ebitda": 20, "pb": 6},
                {"name": "传统软件", "pe": 20, "ps": 4, "ev_ebitda": 12, "pb": 3}
            ],
            "fintech": [
                {"name": "头部Fintech", "pe": 40, "ps": 10, "ev_ebitda": 22, "pb": 6},
                {"name": "中等Fintech", "pe": 25, "ps": 6, "ev_ebitda": 15, "pb": 4},
                {"name": "传统金融", "pe": 12, "ps": 2, "ev_ebitda": 8, "pb": 1.5}
            ],
            "consumer": [
                {"name": "高端消费", "pe": 35, "ps": 5, "ev_ebitda": 18, "pb": 5},
                {"name": "大众消费", "pe": 22, "ps": 2, "ev_ebitda": 12, "pb": 3},
                {"name": "传统零售", "pe": 15, "ps": 0.8, "ev_ebitda": 8, "pb": 2}
            ],
            "healthcare": [
                {"name": "生物医药", "pe": 50, "ps": 15, "ev_ebitda": 30, "pb": 8},
                {"name": "医疗器械", "pe": 35, "ps": 8, "ev_ebitda": 20, "pb": 5},
                {"name": "医疗服务", "pe": 25, "ps": 4, "ev_ebitda": 14, "pb": 3}
            ],
            "default": [
                {"name": "成长型", "pe": 35, "ps": 6, "ev_ebitda": 18, "pb": 5},
                {"name": "稳健型", "pe": 20, "ps": 3, "ev_ebitda": 12, "pb": 3},
                {"name": "价值型", "pe": 12, "ps": 1.5, "ev_ebitda": 8, "pb": 1.5}
            ]
        }

        industry_lower = (industry or "default").lower()
        for key in industry_data:
            if key in industry_lower:
                return industry_data[key]

        return industry_data["default"]

    def _calculate_multiples_stats(self, companies: List[Dict]) -> Dict:
        """计算估值倍数统计"""
        metrics = ["pe", "ps", "ev_ebitda", "pb"]
        stats = {}

        for metric in metrics:
            values = [c.get(metric) for c in companies if c.get(metric) is not None and c.get(metric) > 0]
            if values:
                sorted_values = sorted(values)
                n = len(sorted_values)
                stats[metric] = {
                    "min": round(sorted_values[0], 2),
                    "max": round(sorted_values[-1], 2),
                    "median": round(sorted_values[n//2], 2),
                    "mean": round(sum(values) / n, 2)
                }

        return stats

    def _calculate_implied_valuations(self, target: Dict, stats: Dict) -> Dict:
        """计算隐含估值"""
        valuations = {}
        shares = target.get("shares_outstanding", 1)

        # P/E估值
        if target.get("net_income") and stats.get("pe"):
            pe_stats = stats["pe"]
            valuations["pe_based"] = {
                "low": round(target["net_income"] * pe_stats["min"], 2),
                "median": round(target["net_income"] * pe_stats["median"], 2),
                "high": round(target["net_income"] * pe_stats["max"], 2),
                "per_share_low": round(target["net_income"] * pe_stats["min"] / shares, 2),
                "per_share_median": round(target["net_income"] * pe_stats["median"] / shares, 2),
                "per_share_high": round(target["net_income"] * pe_stats["max"] / shares, 2)
            }

        # P/S估值
        if target.get("revenue") and stats.get("ps"):
            ps_stats = stats["ps"]
            valuations["ps_based"] = {
                "low": round(target["revenue"] * ps_stats["min"], 2),
                "median": round(target["revenue"] * ps_stats["median"], 2),
                "high": round(target["revenue"] * ps_stats["max"], 2),
                "per_share_low": round(target["revenue"] * ps_stats["min"] / shares, 2),
                "per_share_median": round(target["revenue"] * ps_stats["median"] / shares, 2),
                "per_share_high": round(target["revenue"] * ps_stats["max"] / shares, 2)
            }

        # EV/EBITDA估值
        if target.get("ebitda") and stats.get("ev_ebitda"):
            ev_stats = stats["ev_ebitda"]
            valuations["ev_ebitda_based"] = {
                "low": round(target["ebitda"] * ev_stats["min"], 2),
                "median": round(target["ebitda"] * ev_stats["median"], 2),
                "high": round(target["ebitda"] * ev_stats["max"], 2)
            }

        # P/B估值
        if target.get("book_value") and stats.get("pb"):
            pb_stats = stats["pb"]
            valuations["pb_based"] = {
                "low": round(target["book_value"] * pb_stats["min"], 2),
                "median": round(target["book_value"] * pb_stats["median"], 2),
                "high": round(target["book_value"] * pb_stats["max"], 2)
            }

        return valuations

    def _format_comparable_table(self, companies: List[Dict]) -> str:
        """格式化可比公司表格"""
        lines = ["  公司名称      | P/E   | P/S  | EV/EBITDA | P/B"]
        lines.append("  " + "-" * 50)
        for c in companies[:5]:  # 最多显示5家
            name = c.get("name", "N/A")[:12].ljust(12)
            pe = f"{c.get('pe', 'N/A'):>5}" if c.get('pe') else "  N/A"
            ps = f"{c.get('ps', 'N/A'):>4}" if c.get('ps') else " N/A"
            ev = f"{c.get('ev_ebitda', 'N/A'):>9}" if c.get('ev_ebitda') else "      N/A"
            pb = f"{c.get('pb', 'N/A'):>4}" if c.get('pb') else " N/A"
            lines.append(f"  {name} | {pe} | {ps} | {ev} | {pb}")
        return "\n".join(lines)

    def _format_multiples_stats(self, stats: Dict) -> str:
        """格式化倍数统计"""
        lines = []
        metric_names = {
            "pe": "P/E",
            "ps": "P/S",
            "ev_ebitda": "EV/EBITDA",
            "pb": "P/B"
        }
        for metric, name in metric_names.items():
            if metric in stats:
                s = stats[metric]
                lines.append(f"  {name}: 最低 {s['min']} | 中位数 {s['median']} | 平均 {s['mean']} | 最高 {s['max']}")
        return "\n".join(lines)

    def _format_valuations(self, valuations: Dict, target: Dict) -> str:
        """格式化估值结果"""
        lines = []

        if "pe_based" in valuations:
            v = valuations["pe_based"]
            lines.append(f"  基于P/E: {v['low']:,.0f} - {v['median']:,.0f} - {v['high']:,.0f} 百万")
            lines.append(f"          每股: {v['per_share_low']:.2f} - {v['per_share_median']:.2f} - {v['per_share_high']:.2f}")

        if "ps_based" in valuations:
            v = valuations["ps_based"]
            lines.append(f"  基于P/S: {v['low']:,.0f} - {v['median']:,.0f} - {v['high']:,.0f} 百万")
            lines.append(f"          每股: {v['per_share_low']:.2f} - {v['per_share_median']:.2f} - {v['per_share_high']:.2f}")

        if "ev_ebitda_based" in valuations:
            v = valuations["ev_ebitda_based"]
            lines.append(f"  基于EV/EBITDA: {v['low']:,.0f} - {v['median']:,.0f} - {v['high']:,.0f} 百万")

        if "pb_based" in valuations:
            v = valuations["pb_based"]
            lines.append(f"  基于P/B: {v['low']:,.0f} - {v['median']:,.0f} - {v['high']:,.0f} 百万")

        return "\n".join(lines) if lines else "  无法计算（缺少财务数据）"

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "target_metrics": {
                        "type": "object",
                        "description": "目标公司财务指标: revenue(营收), net_income(净利润), ebitda, book_value(账面价值), shares_outstanding(股本)",
                        "properties": {
                            "revenue": {"type": "number"},
                            "net_income": {"type": "number"},
                            "ebitda": {"type": "number"},
                            "book_value": {"type": "number"},
                            "shares_outstanding": {"type": "number"}
                        }
                    },
                    "comparable_companies": {
                        "type": "array",
                        "description": "可比公司列表，每个包含name, pe, ps, ev_ebitda, pb",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "pe": {"type": "number"},
                                "ps": {"type": "number"},
                                "ev_ebitda": {"type": "number"},
                                "pb": {"type": "number"}
                            }
                        }
                    },
                    "industry": {
                        "type": "string",
                        "description": "行业类型: technology, saas, fintech, consumer, healthcare"
                    }
                },
                "required": ["target_metrics"]
            }
        }


class RiskScoringTool(Tool):
    """
    Risk Quantification Scoring Model

    Convert qualitative risk assessment to quantitative scores, supports multi-dimensional risk analysis
    """

    def __init__(self):
        super().__init__(
            name="risk_scoring_model",
            description="""Risk quantification scoring model.

Features:
- Multi-dimensional risk scoring (market, technology, team, financial, legal, operational)
- Weighted composite risk score
- Risk level classification
- Risk matrix visualization data

Use cases:
- Risk assessment for investment decisions
- Risk comparison across different projects
- Risk monitoring and early warning"""
        )

        # 默认权重
        self.default_weights = {
            "market_risk": 0.20,
            "tech_risk": 0.15,
            "team_risk": 0.20,
            "financial_risk": 0.20,
            "legal_risk": 0.10,
            "operational_risk": 0.15
        }

    async def execute(
        self,
        risk_factors: Dict[str, Dict] = None,
        weights: Dict[str, float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行风险评分计算

        Args:
            risk_factors: 各类风险因子评分
                {
                    "market_risk": {"score": 7, "details": "市场竞争激烈"},
                    "tech_risk": {"score": 5, "details": "技术壁垒中等"},
                    ...
                }
                score: 1-10, 10表示风险最高
            weights: 自定义权重（可选）

        Returns:
            综合风险评估结果
        """
        try:
            if risk_factors is None:
                return {
                    "success": False,
                    "error": "缺少风险因子数据",
                    "summary": "风险评分失败: 请提供各维度风险评分"
                }

            # 使用提供的权重或默认权重
            use_weights = weights if weights else self.default_weights

            # 计算加权得分
            total_score = 0
            total_weight = 0
            risk_details = []

            for factor, data in risk_factors.items():
                if isinstance(data, dict):
                    score = data.get("score", 5)
                    details = data.get("details", "")
                else:
                    score = data
                    details = ""

                weight = use_weights.get(factor, 0.1)
                weighted_score = score * weight
                total_score += weighted_score
                total_weight += weight

                risk_details.append({
                    "factor": factor,
                    "score": score,
                    "weight": weight,
                    "weighted_score": round(weighted_score, 2),
                    "details": details,
                    "level": self._score_to_level(score)
                })

            # 归一化总分
            if total_weight > 0:
                normalized_score = total_score / total_weight
            else:
                normalized_score = total_score

            # 风险等级
            overall_level = self._score_to_level(normalized_score)

            # 排序：风险从高到低
            risk_details.sort(key=lambda x: x["score"], reverse=True)

            # 生成风险矩阵数据
            risk_matrix = self._generate_risk_matrix(risk_details)

            # 构建摘要
            summary = f"""【风险量化评估报告】

📊 综合风险得分: {normalized_score:.1f}/10
📊 风险等级: {overall_level}

📋 各维度风险评估:
{self._format_risk_details(risk_details)}

🔺 主要风险因子 (Top 3):
{self._format_top_risks(risk_details[:3])}

📈 风险分布:
{self._format_risk_distribution(risk_details)}

💡 风险管理建议:
{self._generate_recommendations(risk_details, overall_level)}"""

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "overall_score": round(normalized_score, 2),
                    "overall_level": overall_level,
                    "risk_details": risk_details,
                    "risk_matrix": risk_matrix,
                    "weights_used": use_weights
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"风险评分出错: {str(e)}"
            }

    def _score_to_level(self, score: float) -> str:
        """将分数转换为风险等级"""
        if score <= 3:
            return "低风险 🟢"
        elif score <= 5:
            return "中低风险 🟡"
        elif score <= 7:
            return "中高风险 🟠"
        else:
            return "高风险 🔴"

    def _generate_risk_matrix(self, details: List[Dict]) -> Dict:
        """生成风险矩阵数据"""
        matrix = {
            "dimensions": [],
            "scores": [],
            "max_score": 10
        }

        factor_names = {
            "market_risk": "市场风险",
            "tech_risk": "技术风险",
            "team_risk": "团队风险",
            "financial_risk": "财务风险",
            "legal_risk": "法律风险",
            "operational_risk": "运营风险"
        }

        for d in details:
            matrix["dimensions"].append(factor_names.get(d["factor"], d["factor"]))
            matrix["scores"].append(d["score"])

        return matrix

    def _format_risk_details(self, details: List[Dict]) -> str:
        """格式化风险详情"""
        factor_names = {
            "market_risk": "市场风险",
            "tech_risk": "技术风险",
            "team_risk": "团队风险",
            "financial_risk": "财务风险",
            "legal_risk": "法律风险",
            "operational_risk": "运营风险"
        }

        lines = []
        for d in details:
            name = factor_names.get(d["factor"], d["factor"])
            bar = "█" * int(d["score"]) + "░" * (10 - int(d["score"]))
            lines.append(f"  {name}: [{bar}] {d['score']}/10 ({d['level']})")
            if d.get("details"):
                lines.append(f"         └─ {d['details']}")

        return "\n".join(lines)

    def _format_top_risks(self, top_risks: List[Dict]) -> str:
        """格式化主要风险"""
        factor_names = {
            "market_risk": "市场风险",
            "tech_risk": "技术风险",
            "team_risk": "团队风险",
            "financial_risk": "财务风险",
            "legal_risk": "法律风险",
            "operational_risk": "运营风险"
        }

        lines = []
        for i, r in enumerate(top_risks, 1):
            name = factor_names.get(r["factor"], r["factor"])
            lines.append(f"  {i}. {name}: {r['score']}/10")
            if r.get("details"):
                lines.append(f"     {r['details']}")

        return "\n".join(lines)

    def _format_risk_distribution(self, details: List[Dict]) -> str:
        """格式化风险分布"""
        high = sum(1 for d in details if d["score"] >= 7)
        medium = sum(1 for d in details if 4 <= d["score"] < 7)
        low = sum(1 for d in details if d["score"] < 4)

        return f"  高风险: {high}项 | 中风险: {medium}项 | 低风险: {low}项"

    def _generate_recommendations(self, details: List[Dict], level: str) -> str:
        """生成风险管理建议"""
        recommendations = []

        # 基于整体风险等级的建议
        if "高风险" in level:
            recommendations.append("  ⚠️ 建议重新评估投资决策，或设置更严格的投资条款")
        elif "中高风险" in level:
            recommendations.append("  ⚠️ 建议增加尽调深度，关注关键风险因子")

        # 基于具体风险的建议
        factor_recommendations = {
            "market_risk": "关注市场竞争态势和行业周期，建议定期监控",
            "tech_risk": "建议进行技术尽调，评估技术壁垒和替代风险",
            "team_risk": "关注核心团队稳定性，建议设置关键人条款",
            "financial_risk": "加强财务监控，关注现金流和融资能力",
            "legal_risk": "建议法律尽调，确认合规性和潜在纠纷",
            "operational_risk": "关注业务执行能力，建议设置里程碑条款"
        }

        for d in details[:3]:  # Top 3 风险
            if d["score"] >= 6:
                rec = factor_recommendations.get(d["factor"])
                if rec:
                    recommendations.append(f"  • {rec}")

        return "\n".join(recommendations) if recommendations else "  暂无特别建议"

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "risk_factors": {
                        "type": "object",
                        "description": "各维度风险评分（1-10，10为最高风险）",
                        "properties": {
                            "market_risk": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number", "minimum": 1, "maximum": 10},
                                    "details": {"type": "string"}
                                }
                            },
                            "tech_risk": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number", "minimum": 1, "maximum": 10},
                                    "details": {"type": "string"}
                                }
                            },
                            "team_risk": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number", "minimum": 1, "maximum": 10},
                                    "details": {"type": "string"}
                                }
                            },
                            "financial_risk": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number", "minimum": 1, "maximum": 10},
                                    "details": {"type": "string"}
                                }
                            },
                            "legal_risk": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number", "minimum": 1, "maximum": 10},
                                    "details": {"type": "string"}
                                }
                            },
                            "operational_risk": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number", "minimum": 1, "maximum": 10},
                                    "details": {"type": "string"}
                                }
                            }
                        }
                    },
                    "weights": {
                        "type": "object",
                        "description": "自定义权重（可选，默认平均分配）"
                    }
                },
                "required": ["risk_factors"]
            }
        }


class ComplianceCheckerTool(Tool):
    """
    Compliance Checker Tool

    Provide compliance checklists and recommendations based on industry and region
    """

    def __init__(self):
        super().__init__(
            name="compliance_checker",
            description="""Compliance checklist generation tool.

Features:
- Generate required licenses/qualifications by industry
- List key compliance requirements
- Identify common legal risks
- Provide action recommendations

Supported industries:
- fintech (Financial Technology)
- healthcare (Healthcare)
- ecommerce (E-commerce)
- edtech (Education Technology)
- crypto (Cryptocurrency)
- ai (Artificial Intelligence)"""
        )

        # 行业合规数据库
        self.compliance_db = self._init_compliance_database()

    def _init_compliance_database(self) -> Dict:
        """初始化合规数据库"""
        return {
            "fintech": {
                "licenses": [
                    {"name": "支付业务许可证", "authority": "中国人民银行", "required": True, "difficulty": "高"},
                    {"name": "网络小贷牌照", "authority": "地方金融办", "required": "视业务", "difficulty": "高"},
                    {"name": "基金销售牌照", "authority": "证监会", "required": "视业务", "difficulty": "高"},
                    {"name": "保险经纪牌照", "authority": "银保监会", "required": "视业务", "difficulty": "中"}
                ],
                "requirements": [
                    "实缴注册资本要求（支付: 1亿元）",
                    "反洗钱(AML)系统建设",
                    "KYC身份验证系统",
                    "数据本地化存储",
                    "信息安全等级保护(等保三级)",
                    "消费者权益保护机制"
                ],
                "risks": [
                    "无证经营金融业务",
                    "非法集资认定风险",
                    "利率超过法定上限",
                    "数据泄露和隐私侵权",
                    "跨境支付合规问题"
                ],
                "regulations": [
                    "《非银行支付机构条例》",
                    "《网络借贷信息中介机构业务活动管理暂行办法》",
                    "《个人金融信息保护技术规范》"
                ]
            },
            "healthcare": {
                "licenses": [
                    {"name": "医疗器械经营许可证", "authority": "药监局", "required": "视产品", "difficulty": "中"},
                    {"name": "互联网医院牌照", "authority": "卫健委", "required": "视业务", "difficulty": "高"},
                    {"name": "药品经营许可证", "authority": "药监局", "required": "视业务", "difficulty": "高"},
                    {"name": "医疗机构执业许可证", "authority": "卫健委", "required": "视业务", "difficulty": "高"}
                ],
                "requirements": [
                    "医疗器械产品注册/备案",
                    "临床试验审批（创新器械）",
                    "GMP/GSP认证",
                    "医疗广告审批",
                    "医疗数据安全管理",
                    "不良反应监测上报"
                ],
                "risks": [
                    "产品未获批上市销售",
                    "虚假医疗广告",
                    "医疗事故责任",
                    "患者隐私泄露",
                    "价格违规"
                ],
                "regulations": [
                    "《医疗器械监督管理条例》",
                    "《互联网诊疗管理办法》",
                    "《药品管理法》"
                ]
            },
            "ecommerce": {
                "licenses": [
                    {"name": "ICP经营许可证", "authority": "通信管理局", "required": True, "difficulty": "中"},
                    {"name": "EDI许可证", "authority": "通信管理局", "required": "视业务", "difficulty": "中"},
                    {"name": "食品经营许可证", "authority": "市场监管局", "required": "视品类", "difficulty": "低"},
                    {"name": "网络文化经营许可证", "authority": "文化部门", "required": "视业务", "difficulty": "中"}
                ],
                "requirements": [
                    "电子商务经营者登记",
                    "商品信息真实性保证",
                    "消费者七天无理由退货",
                    "用户数据保护",
                    "知识产权保护机制",
                    "平台责任与治理"
                ],
                "risks": [
                    "假冒伪劣商品责任",
                    "消费者投诉和纠纷",
                    "价格欺诈",
                    "不正当竞争",
                    "跨境电商合规"
                ],
                "regulations": [
                    "《电子商务法》",
                    "《消费者权益保护法》",
                    "《网络交易监督管理办法》"
                ]
            },
            "crypto": {
                "licenses": [
                    {"name": "注意：中国大陆禁止加密货币交易", "authority": "N/A", "required": True, "difficulty": "N/A"}
                ],
                "requirements": [
                    "⚠️ 中国大陆：禁止加密货币交易所和ICO",
                    "海外运营需符合当地法规",
                    "美国: FinCEN MSB注册",
                    "新加坡: MAS牌照",
                    "香港: SFC虚拟资产服务牌照"
                ],
                "risks": [
                    "监管政策突变风险",
                    "反洗钱合规风险",
                    "证券法认定风险（Token是否为证券）",
                    "税务合规风险",
                    "跨境资金流动限制"
                ],
                "regulations": [
                    "《关于防范代币发行融资风险的公告》(中国)",
                    "《关于进一步防范和处置虚拟货币交易炒作风险的通知》(中国)",
                    "MiCA法规(欧盟)",
                    "Travel Rule(FATF)"
                ]
            },
            "ai": {
                "licenses": [
                    {"name": "算法备案", "authority": "网信办", "required": True, "difficulty": "中"},
                    {"name": "生成式AI服务备案", "authority": "网信办", "required": "视业务", "difficulty": "中"},
                    {"name": "深度合成服务备案", "authority": "网信办", "required": "视业务", "difficulty": "中"}
                ],
                "requirements": [
                    "算法推荐服务备案",
                    "AI生成内容标识",
                    "训练数据合规",
                    "算法公平性和透明度",
                    "用户隐私保护",
                    "内容安全审核"
                ],
                "risks": [
                    "算法歧视和偏见",
                    "虚假信息生成",
                    "知识产权侵权（训练数据）",
                    "个人信息违规处理",
                    "内容安全责任"
                ],
                "regulations": [
                    "《生成式人工智能服务管理暂行办法》",
                    "《互联网信息服务深度合成管理规定》",
                    "《互联网信息服务算法推荐管理规定》"
                ]
            },
            "edtech": {
                "licenses": [
                    {"name": "在线教育ICP许可", "authority": "通信管理局", "required": True, "difficulty": "中"},
                    {"name": "校外培训机构许可", "authority": "教育部门", "required": "视业务", "difficulty": "高"},
                    {"name": "职业培训许可", "authority": "人社部门", "required": "视业务", "difficulty": "中"}
                ],
                "requirements": [
                    "⚠️ K12学科类培训受严格限制",
                    "教师资质公示",
                    "课程内容审核",
                    "收费规范（不超过3个月）",
                    "未成年人保护",
                    "广告合规"
                ],
                "risks": [
                    "双减政策合规风险",
                    "预收费监管风险",
                    "虚假宣传",
                    "教师资质问题",
                    "内容违规"
                ],
                "regulations": [
                    "《关于进一步减轻义务教育阶段学生作业负担和校外培训负担的意见》",
                    "《校外培训行政处罚暂行办法》",
                    "《关于规范校外培训机构发展的意见》"
                ]
            }
        }

    async def execute(
        self,
        industry: str = None,
        business_model: str = None,
        operating_regions: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行合规检查

        Args:
            industry: 行业类型
            business_model: 业务模式描述
            operating_regions: 运营地区列表

        Returns:
            合规检查清单和建议
        """
        try:
            if industry is None:
                return {
                    "success": False,
                    "error": "请指定行业类型",
                    "summary": "合规检查失败: 请指定行业类型 (fintech, healthcare, ecommerce, crypto, ai, edtech)"
                }

            industry_lower = industry.lower()

            # 查找匹配的行业
            matched_industry = None
            for key in self.compliance_db:
                if key in industry_lower or industry_lower in key:
                    matched_industry = key
                    break

            if matched_industry is None:
                # 返回通用合规检查
                return self._generic_compliance_check(industry, business_model, operating_regions)

            compliance_data = self.compliance_db[matched_industry]

            # 构建合规报告
            summary = f"""【合规性检查报告】

📋 行业: {industry}
📍 运营地区: {', '.join(operating_regions) if operating_regions else '中国大陆'}

🏛️ 必需资质/牌照:
{self._format_licenses(compliance_data['licenses'])}

📜 核心合规要求:
{self._format_list(compliance_data['requirements'])}

⚠️ 常见法律风险:
{self._format_list(compliance_data['risks'])}

📚 相关法规:
{self._format_list(compliance_data['regulations'])}

💡 行动建议:
{self._generate_action_items(compliance_data, business_model)}"""

            return {
                "success": True,
                "summary": summary,
                "data": {
                    "industry": matched_industry,
                    "licenses": compliance_data["licenses"],
                    "requirements": compliance_data["requirements"],
                    "risks": compliance_data["risks"],
                    "regulations": compliance_data["regulations"]
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"合规检查出错: {str(e)}"
            }

    def _generic_compliance_check(self, industry: str, business_model: str, regions: List[str]) -> Dict:
        """通用合规检查"""
        summary = f"""【通用合规性检查报告】

📋 行业: {industry}
📍 运营地区: {', '.join(regions) if regions else '未指定'}

🏛️ 通用资质要求:
  • 营业执照（工商注册）
  • ICP备案（网站运营必需）
  • ICP经营许可证（经营性网站）
  • 相关行业特定资质（需进一步确认）

📜 基础合规要求:
  • 企业所得税合规
  • 社会保险缴纳
  • 劳动用工合规
  • 数据安全与个人信息保护
  • 知识产权保护
  • 反不正当竞争

⚠️ 需关注的风险领域:
  • 行业准入资质
  • 税务合规
  • 数据跨境传输
  • 外资准入限制（如适用）

💡 建议:
  1. 咨询专业律师确认具体资质要求
  2. 进行全面的法律尽职调查
  3. 建立合规管理体系

⚠️ 注意: 该行业({industry})不在预设数据库中，建议进行专项合规研究。"""

        return {
            "success": True,
            "summary": summary,
            "data": {
                "industry": industry,
                "note": "使用通用合规检查，建议进行专项研究"
            }
        }

    def _format_licenses(self, licenses: List[Dict]) -> str:
        """格式化资质列表"""
        lines = []
        for lic in licenses:
            required = "必需" if lic["required"] == True else lic["required"]
            difficulty = lic.get("difficulty", "")
            lines.append(f"  • {lic['name']}")
            lines.append(f"    审批机构: {lic['authority']} | 要求: {required} | 难度: {difficulty}")
        return "\n".join(lines)

    def _format_list(self, items: List[str]) -> str:
        """格式化列表"""
        return "\n".join(f"  • {item}" for item in items)

    def _generate_action_items(self, data: Dict, business_model: str) -> str:
        """生成行动建议"""
        items = [
            "1. 确认业务模式对应的具体资质要求",
            "2. 评估现有资质缺口",
            "3. 制定资质申请时间表",
            "4. 建立合规管理制度",
            "5. 定期进行合规自查"
        ]

        # 如果有高难度牌照，添加特别提醒
        high_difficulty = [lic["name"] for lic in data["licenses"] if lic.get("difficulty") == "高"]
        if high_difficulty:
            items.append(f"⚠️ 重点关注高难度资质: {', '.join(high_difficulty)}")

        return "\n  ".join(items)

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "行业类型: fintech, healthcare, ecommerce, crypto, ai, edtech",
                        "enum": ["fintech", "healthcare", "ecommerce", "crypto", "ai", "edtech"]
                    },
                    "business_model": {
                        "type": "string",
                        "description": "业务模式简述"
                    },
                    "operating_regions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "运营地区列表，如 ['中国大陆', '香港', '新加坡']"
                    }
                },
                "required": ["industry"]
            }
        }


class SummaryChartTool(Tool):
    """
    Summary Chart Generation Tool

    Generate investment analysis summary charts and reports for the Leader
    """

    def __init__(self):
        super().__init__(
            name="generate_summary_chart",
            description="""Generate investment analysis summary charts.

Features:
- Generate multi-dimensional scoring radar chart data
- Generate comparison analysis tables
- Generate timeline chart data
- Support multiple visualization formats

Use cases:
- Roundtable discussion results summary
- Investment recommendation visualization
- Multi-project comparison analysis"""
        )

    async def execute(
        self,
        chart_type: str = "radar",
        data: Dict = None,
        title: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成图表数据

        Args:
            chart_type: 图表类型 (radar/comparison/scorecard/timeline)
            data: 图表数据
            title: 图表标题

        Returns:
            图表数据和渲染信息
        """
        try:
            if data is None:
                return {
                    "success": False,
                    "error": "缺少图表数据",
                    "summary": "图表生成失败: 请提供图表数据"
                }

            if chart_type == "radar":
                return self._generate_radar_chart(data, title)
            elif chart_type == "comparison":
                return self._generate_comparison_table(data, title)
            elif chart_type == "scorecard":
                return self._generate_scorecard(data, title)
            elif chart_type == "timeline":
                return self._generate_timeline(data, title)
            else:
                return {
                    "success": False,
                    "error": f"不支持的图表类型: {chart_type}",
                    "summary": f"请使用支持的图表类型: radar, comparison, scorecard, timeline"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"图表生成出错: {str(e)}"
            }

    def _generate_radar_chart(self, data: Dict, title: str) -> Dict:
        """生成雷达图数据"""
        dimensions = data.get("dimensions", [])
        scores = data.get("scores", [])

        if len(dimensions) != len(scores):
            return {
                "success": False,
                "error": "维度和分数数量不匹配",
                "summary": "雷达图生成失败: 维度和分数数量必须一致"
            }

        # 生成ASCII雷达图表示
        ascii_chart = self._draw_ascii_radar(dimensions, scores)

        summary = f"""【{title or '多维度评分雷达图'}】

{ascii_chart}

📊 各维度得分:
{self._format_dimension_scores(dimensions, scores)}

📈 评分统计:
  最高分: {max(scores):.1f} ({dimensions[scores.index(max(scores))]})
  最低分: {min(scores):.1f} ({dimensions[scores.index(min(scores))]})
  平均分: {sum(scores)/len(scores):.1f}"""

        return {
            "success": True,
            "summary": summary,
            "data": {
                "chart_type": "radar",
                "title": title,
                "dimensions": dimensions,
                "scores": scores,
                "chart_config": {
                    "type": "radar",
                    "data": {
                        "labels": dimensions,
                        "datasets": [{
                            "data": scores,
                            "fill": True,
                            "backgroundColor": "rgba(54, 162, 235, 0.2)",
                            "borderColor": "rgb(54, 162, 235)"
                        }]
                    }
                }
            }
        }

    def _draw_ascii_radar(self, dimensions: List[str], scores: List[float]) -> str:
        """绘制ASCII雷达图"""
        lines = []
        max_score = 10

        for i, (dim, score) in enumerate(zip(dimensions, scores)):
            bar_length = int(score / max_score * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            lines.append(f"  {dim[:10]:>10}: [{bar}] {score:.1f}")

        return "\n".join(lines)

    def _format_dimension_scores(self, dimensions: List[str], scores: List[float]) -> str:
        """格式化维度分数"""
        lines = []
        for dim, score in zip(dimensions, scores):
            level = "优秀" if score >= 8 else "良好" if score >= 6 else "一般" if score >= 4 else "较差"
            lines.append(f"  • {dim}: {score:.1f}/10 ({level})")
        return "\n".join(lines)

    def _generate_comparison_table(self, data: Dict, title: str) -> Dict:
        """生成对比分析表"""
        items = data.get("items", [])
        metrics = data.get("metrics", [])

        if not items or not metrics:
            return {
                "success": False,
                "error": "缺少对比项目或指标",
                "summary": "对比表生成失败: 请提供items和metrics"
            }

        # 生成表格
        table = self._draw_comparison_table(items, metrics)

        summary = f"""【{title or '对比分析表'}】

{table}"""

        return {
            "success": True,
            "summary": summary,
            "data": {
                "chart_type": "comparison",
                "title": title,
                "items": items,
                "metrics": metrics
            }
        }

    def _draw_comparison_table(self, items: List[Dict], metrics: List[str]) -> str:
        """绘制对比表"""
        # 表头
        header = "| 项目 |"
        for metric in metrics:
            header += f" {metric[:8]:^8} |"

        separator = "|" + "-" * 8 + "|" + (("-" * 10 + "|") * len(metrics))

        rows = [header, separator]

        for item in items:
            row = f"| {item.get('name', 'N/A')[:6]:^6} |"
            for metric in metrics:
                value = item.get(metric, "N/A")
                if isinstance(value, (int, float)):
                    row += f" {value:^8.1f} |"
                else:
                    row += f" {str(value)[:8]:^8} |"
            rows.append(row)

        return "\n".join(rows)

    def _generate_scorecard(self, data: Dict, title: str) -> Dict:
        """生成评分卡"""
        categories = data.get("categories", {})
        overall_score = data.get("overall_score", 0)
        recommendation = data.get("recommendation", "")

        # 生成评分卡
        scorecard = []
        scorecard.append(f"╔{'═' * 50}╗")
        scorecard.append(f"║{(title or '投资评分卡'):^50}║")
        scorecard.append(f"╠{'═' * 50}╣")

        for category, score in categories.items():
            bar = "●" * int(score) + "○" * (10 - int(score))
            scorecard.append(f"║ {category[:15]:<15} [{bar}] {score:>4.1f}/10 ║")

        scorecard.append(f"╠{'═' * 50}╣")
        scorecard.append(f"║ {'综合评分':^15} {overall_score:^30.1f}/10 ║")
        scorecard.append(f"╠{'═' * 50}╣")
        scorecard.append(f"║ 投资建议: {recommendation[:38]:<38} ║")
        scorecard.append(f"╚{'═' * 50}╝")

        summary = "\n".join(scorecard)

        return {
            "success": True,
            "summary": summary,
            "data": {
                "chart_type": "scorecard",
                "title": title,
                "categories": categories,
                "overall_score": overall_score,
                "recommendation": recommendation
            }
        }

    def _generate_timeline(self, data: Dict, title: str) -> Dict:
        """生成时间线"""
        events = data.get("events", [])

        if not events:
            return {
                "success": False,
                "error": "缺少时间线事件",
                "summary": "时间线生成失败: 请提供events数据"
            }

        # 生成时间线
        timeline = [f"【{title or '关键事件时间线'}】\n"]

        for i, event in enumerate(events):
            date = event.get("date", "")
            desc = event.get("description", "")
            event_type = event.get("type", "milestone")

            icon = "🔵" if event_type == "milestone" else "🟢" if event_type == "positive" else "🔴" if event_type == "negative" else "⚪"

            if i == 0:
                timeline.append(f"  {icon} {date}")
                timeline.append(f"  │  └─ {desc}")
            elif i == len(events) - 1:
                timeline.append(f"  │")
                timeline.append(f"  {icon} {date}")
                timeline.append(f"     └─ {desc}")
            else:
                timeline.append(f"  │")
                timeline.append(f"  {icon} {date}")
                timeline.append(f"  │  └─ {desc}")

        summary = "\n".join(timeline)

        return {
            "success": True,
            "summary": summary,
            "data": {
                "chart_type": "timeline",
                "title": title,
                "events": events
            }
        }

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "description": "图表类型",
                        "enum": ["radar", "comparison", "scorecard", "timeline"]
                    },
                    "data": {
                        "type": "object",
                        "description": "图表数据。radar需要dimensions和scores; comparison需要items和metrics; scorecard需要categories和overall_score; timeline需要events"
                    },
                    "title": {
                        "type": "string",
                        "description": "图表标题"
                    }
                },
                "required": ["chart_type", "data"]
            }
        }
