"""
Financial Expert Agent - 深度财务分析Agent
用于早期投资、成长期投资、公开市场的深度财务分析
支持多种场景: 商业模式评估、单位经济学、财务建模、DCF估值等
"""
from typing import Dict, Any, List, Optional
import httpx
from pydantic import BaseModel, Field


class UnitEconomics(BaseModel):
    """单位经济学"""
    cac: Optional[float] = Field(None, description="获客成本 (CAC)")
    ltv: Optional[float] = Field(None, description="客户生命周期价值 (LTV)")
    ltv_cac_ratio: Optional[float] = Field(None, description="LTV/CAC比率")
    payback_period: Optional[int] = Field(None, description="回本周期(月)")
    gross_margin: Optional[float] = Field(None, description="毛利率")


class FinancialModel(BaseModel):
    """财务模型"""
    revenue_forecast: List[float] = Field(default_factory=list, description="营收预测(未来3-5年)")
    cost_structure: Dict[str, Any] = Field(default_factory=dict, description="成本结构")
    break_even_point: Optional[str] = Field(None, description="盈亏平衡点")
    burn_rate: Optional[float] = Field(None, description="烧钱率(月)")
    runway: Optional[int] = Field(None, description="资金跑道(月)")


class DCFValuation(BaseModel):
    """DCF估值"""
    wacc: Optional[float] = Field(None, description="加权平均资本成本 (WACC)")
    terminal_growth_rate: Optional[float] = Field(None, description="永续增长率")
    dcf_value: Optional[float] = Field(None, description="DCF估值")
    valuation_range: Dict[str, float] = Field(default_factory=dict, description="估值区间")


class FinancialAnalysis(BaseModel):
    """财务分析结果"""
    unit_economics: Optional[UnitEconomics] = None
    financial_model: Optional[FinancialModel] = None
    dcf_valuation: Optional[DCFValuation] = None
    business_model_assessment: str = Field(..., description="商业模式评估")
    scalability_score: float = Field(..., description="可扩展性评分 0-1")
    financial_health_score: float = Field(..., description="财务健康评分 0-1")
    key_metrics: Dict[str, Any] = Field(default_factory=dict)
    risks: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class FinancialExpertAgent:
    """深度财务分析Agent - 支持多场景"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010",
        llm_gateway_url: str = "http://llm_gateway:8003"
    ):
        self.web_search_url = web_search_url
        self.llm_gateway_url = llm_gateway_url

    async def analyze(
        self,
        target: Dict[str, Any],
        context: Dict[str, Any],
        analysis_type: str = "business_model"
    ) -> FinancialAnalysis:
        """
        执行深度财务分析

        Args:
            target: 分析目标 (公司/项目信息)
            context: 上下文 (BP数据、市场分析等)
            analysis_type: 分析类型
                - "business_model": 商业模式评估 (早期投资)
                - "unit_economics": 单位经济学分析 (早期投资)
                - "financial_modeling": 财务建模 (成长期)
                - "dcf_valuation": DCF估值 (成长期、公开市场)

        Returns:
            FinancialAnalysis: 财务分析结果
        """
        try:
            if analysis_type == "business_model":
                return await self._analyze_business_model(target, context)
            elif analysis_type == "unit_economics":
                return await self._analyze_unit_economics(target, context)
            elif analysis_type == "financial_modeling":
                return await self._build_financial_model(target, context)
            elif analysis_type == "dcf_valuation":
                return await self._dcf_valuation(target, context)
            else:
                # 默认综合分析
                return await self._comprehensive_analysis(target, context)

        except Exception as e:
            print(f"[FinancialExpertAgent] Analysis failed: {e}")
            return self._fallback_result(target)

    async def _analyze_business_model(
        self,
        target: Dict[str, Any],
        context: Dict[str, Any]
    ) -> FinancialAnalysis:
        """商业模式评估 (早期投资)"""
        company_name = target.get('company_name', '目标公司')
        bp_data = context.get('bp_data', {})
        market_analysis = context.get('market_analysis', {})

        # 构建prompt
        prompt = f"""你是资深的财务分析专家,专注于早期项目的商业模式评估。

**分析对象**: {company_name}

**BP信息**:
{self._format_bp_data(bp_data)}

**市场分析**:
{self._format_market_analysis(market_analysis)}

**任务**: 深度评估商业模式,关注:
1. 收入模式: 如何赚钱?(订阅/交易/广告/SaaS等)
2. 成本结构: 主要成本项,固定vs可变成本
3. 单位经济学: CAC, LTV, LTV/CAC比率, 回本周期
4. 可扩展性: 边际成本递减,规模效应
5. 盈利路径: 何时盈亏平衡,何时正现金流

**输出格式** (严格JSON):
{{
  "business_model_assessment": "200字内评估商业模式的可行性和独特性",
  "scalability_score": 0.85,
  "financial_health_score": 0.75,
  "unit_economics": {{
    "cac": 500.0,
    "ltv": 2000.0,
    "ltv_cac_ratio": 4.0,
    "payback_period": 6,
    "gross_margin": 0.7
  }},
  "key_metrics": {{
    "revenue_model": "SaaS订阅+增值服务",
    "cost_drivers": ["人力成本", "云服务", "市场推广"],
    "break_even_timeline": "18-24个月"
  }},
  "risks": ["客户获取成本过高", "市场竞争激烈"],
  "recommendations": ["优化获客渠道", "提升客户留存率"]
}}

注意:
- scalability_score和financial_health_score都是0-1评分
- unit_economics要有具体数字
- 如果数据不足,标注为null
"""

        # 调用LLM
        result = await self._call_llm(prompt)
        return self._parse_result(result, "business_model")

    async def _analyze_unit_economics(
        self,
        target: Dict[str, Any],
        context: Dict[str, Any]
    ) -> FinancialAnalysis:
        """单位经济学深度分析"""
        # 类似business_model,但更专注于数字计算
        company_name = target.get('company_name', '目标公司')
        financials = context.get('financials', {})

        prompt = f"""你是资深的财务分析专家,专注于单位经济学分析。

**分析对象**: {company_name}

**财务数据**:
- 年营收: {financials.get('annual_revenue', 'N/A')}
- 客户数: {financials.get('customer_count', 'N/A')}
- 增长率: {financials.get('growth_rate', 'N/A')}

**任务**: 计算和评估关键单位经济学指标

**输出格式** (严格JSON):
{{
  "business_model_assessment": "基于单位经济学的商业模式评估",
  "scalability_score": 0.8,
  "financial_health_score": 0.7,
  "unit_economics": {{
    "cac": 估算的CAC,
    "ltv": 估算的LTV,
    "ltv_cac_ratio": LTV/CAC,
    "payback_period": 回本周期(月),
    "gross_margin": 毛利率
  }},
  "key_metrics": {{
    "arpu": "平均每用户收入",
    "churn_rate": "流失率",
    "retention_rate": "留存率"
  }},
  "risks": ["单位经济学风险"],
  "recommendations": ["改进建议"]
}}
"""

        result = await self._call_llm(prompt)
        return self._parse_result(result, "unit_economics")

    async def _build_financial_model(
        self,
        target: Dict[str, Any],
        context: Dict[str, Any]
    ) -> FinancialAnalysis:
        """财务建模 (成长期)"""
        company_name = target.get('company_name', '目标公司')
        financials = context.get('financials', {})

        prompt = f"""你是资深的财务建模专家,为成长期公司构建财务模型。

**分析对象**: {company_name}

**历史财务**:
{self._format_financials(financials)}

**任务**: 构建未来3-5年财务模型

**输出格式** (严格JSON):
{{
  "business_model_assessment": "基于历史数据的商业模式评估",
  "scalability_score": 0.8,
  "financial_health_score": 0.75,
  "financial_model": {{
    "revenue_forecast": [100, 150, 225, 340, 510],
    "cost_structure": {{
      "cogs": "成本占比",
      "sales_marketing": "销售营销占比",
      "rd": "研发占比",
      "general_admin": "行政占比"
    }},
    "break_even_point": "2025年Q2",
    "burn_rate": 每月烧钱,
    "runway": 资金跑道(月)
  }},
  "key_metrics": {{
    "revenue_cagr": "营收复合增长率",
    "operating_margin_trend": "经营利润率趋势"
  }},
  "risks": ["财务风险"],
  "recommendations": ["改进建议"]
}}
"""

        result = await self._call_llm(prompt)
        return self._parse_result(result, "financial_model")

    async def _dcf_valuation(
        self,
        target: Dict[str, Any],
        context: Dict[str, Any]
    ) -> FinancialAnalysis:
        """DCF估值 (成长期/公开市场)"""
        company_name = target.get('company_name', '目标公司')
        financials = context.get('financials', {})

        prompt = f"""你是资深的估值专家,使用DCF方法进行公司估值。

**分析对象**: {company_name}

**财务数据**:
{self._format_financials(financials)}

**任务**: DCF估值分析

**输出格式** (严格JSON):
{{
  "business_model_assessment": "基于DCF的价值评估",
  "scalability_score": 0.8,
  "financial_health_score": 0.75,
  "dcf_valuation": {{
    "wacc": 0.12,
    "terminal_growth_rate": 0.03,
    "dcf_value": 10000000000.0,
    "valuation_range": {{
      "low": 8000000000.0,
      "mid": 10000000000.0,
      "high": 12000000000.0
    }}
  }},
  "key_metrics": {{
    "fcf_yield": "自由现金流收益率",
    "ev_to_sales": "企业价值/销售额",
    "ev_to_ebitda": "企业价值/EBITDA"
  }},
  "risks": ["估值风险","假设风险"],
  "recommendations": ["投资建议"]
}}
"""

        result = await self._call_llm(prompt)
        return self._parse_result(result, "dcf_valuation")

    async def _comprehensive_analysis(
        self,
        target: Dict[str, Any],
        context: Dict[str, Any]
    ) -> FinancialAnalysis:
        """综合财务分析"""
        # 结合多种分析方法
        return await self._analyze_business_model(target, context)

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """调用LLM"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.llm_gateway_url}/chat",
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": "json",
                        "temperature": 0.3
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("content", {})
        except Exception as e:
            print(f"[FinancialExpertAgent] LLM call failed: {e}")

        return {"error": "LLM调用失败"}

    def _parse_result(
        self,
        llm_result: Dict[str, Any],
        analysis_type: str
    ) -> FinancialAnalysis:
        """解析LLM结果"""
        if "error" in llm_result:
            return FinancialAnalysis(
                business_model_assessment="分析未完成,数据不足",
                scalability_score=0.5,
                financial_health_score=0.5,
                risks=["自动分析失败"],
                recommendations=["需要人工复核"]
            )

        # 构建FinancialAnalysis对象
        return FinancialAnalysis(
            business_model_assessment=llm_result.get("business_model_assessment", "待评估"),
            scalability_score=llm_result.get("scalability_score", 0.5),
            financial_health_score=llm_result.get("financial_health_score", 0.5),
            unit_economics=UnitEconomics(**llm_result.get("unit_economics", {})) if llm_result.get("unit_economics") else None,
            financial_model=FinancialModel(**llm_result.get("financial_model", {})) if llm_result.get("financial_model") else None,
            dcf_valuation=DCFValuation(**llm_result.get("dcf_valuation", {})) if llm_result.get("dcf_valuation") else None,
            key_metrics=llm_result.get("key_metrics", {}),
            risks=llm_result.get("risks", []),
            recommendations=llm_result.get("recommendations", [])
        )

    def _fallback_result(self, target: Dict[str, Any]) -> FinancialAnalysis:
        """Fallback结果"""
        return FinancialAnalysis(
            business_model_assessment="自动分析失败,需要人工评估",
            scalability_score=0.5,
            financial_health_score=0.5,
            risks=["分析系统异常"],
            recommendations=["建议人工深度分析"]
        )

    def _format_bp_data(self, bp_data: Dict[str, Any]) -> str:
        """格式化BP数据"""
        if not bp_data:
            return "无BP数据"
        return f"产品: {bp_data.get('product_name', 'N/A')}\n收入模式: {bp_data.get('revenue_model', 'N/A')}"

    def _format_market_analysis(self, market_analysis: Dict[str, Any]) -> str:
        """格式化市场分析"""
        if not market_analysis:
            return "无市场分析数据"
        return f"市场规模: {market_analysis.get('market_size', 'N/A')}\n增长率: {market_analysis.get('growth_rate', 'N/A')}"

    def _format_financials(self, financials: Dict[str, Any]) -> str:
        """格式化财务数据"""
        if not financials:
            return "无财务数据"
        return f"营收: {financials.get('revenue', 'N/A')}\n净利润: {financials.get('net_income', 'N/A')}"
