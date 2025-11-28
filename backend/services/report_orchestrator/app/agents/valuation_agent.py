# backend/services/report_orchestrator/app/agents/valuation_agent.py
"""
估值分析 Agent
使用可比公司法和 LLM 推理进行估值分析
"""
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ValuationRange(BaseModel):
    """估值区间"""
    low: float = Field(..., description="估值下限（元）")
    high: float = Field(..., description="估值上限（元）")
    currency: str = Field(default="CNY", description="货币单位")

class ComparableCompany(BaseModel):
    """可比公司"""
    name: str = Field(..., description="公司名称")
    pe_ratio: Optional[float] = Field(None, description="市盈率")
    ps_ratio: Optional[float] = Field(None, description="市销率")
    market_cap: Optional[str] = Field(None, description="市值")
    growth_rate: Optional[str] = Field(None, description="增长率")

class ValuationAnalysis(BaseModel):
    """估值分析结果"""
    valuation_range: ValuationRange
    methodology: str = Field(..., description="估值方法")
    comparable_companies: List[ComparableCompany]
    key_assumptions: List[str]
    risks: List[str]
    analysis_text: str = Field(..., description="详细分析文本")

class ValuationAgent:
    """估值分析 Agent"""
    
    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8003",
        llm_gateway_url: str = "http://llm_gateway:8001"
    ):
        self.web_search_url = web_search_url
        self.llm_gateway_url = llm_gateway_url
    
    async def analyze_valuation(
        self,
        bp_data: Dict[str, Any],
        market_analysis: str
    ) -> ValuationAnalysis:
        """
        执行估值分析
        
        Args:
            bp_data: BP 结构化数据
            market_analysis: 市场分析结果
        
        Returns:
            ValuationAnalysis: 估值分析结果
        """
        try:
            # 1. 搜索行业估值数据
            industry_data = await self._search_industry_valuation(bp_data)
            
            # 2. 构建分析 Prompt
            prompt = self._build_valuation_prompt(bp_data, market_analysis, industry_data)
            
            # 3. 调用 LLM 分析
            llm_response = await self._call_llm(prompt)
            
            # 4. 解析 LLM 响应
            analysis = self._parse_llm_response(llm_response, bp_data)
            
            return analysis
        
        except Exception as e:
            print(f"Error in valuation analysis: {e}")
            return self._create_fallback_analysis(bp_data)
    
    async def _search_industry_valuation(self, bp_data: Dict[str, Any]) -> str:
        """搜索行业估值数据"""
        try:
            target_market = bp_data.get("target_market", "科技")
            product_name = bp_data.get("product_name", "")
            
            query = f"{target_market} 行业 估值倍数 PE PS 可比公司 {product_name}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.web_search_url}/search",
                    json={"query": query, "max_results": 5}
                )
                
                if response.status_code == 200:
                    results = response.json().get("results", [])
                    # 提取搜索结果文本
                    search_text = "\n\n".join([
                        f"来源: {r.get('title', '')}\n{r.get('content', '')[:300]}"
                        for r in results[:3]
                    ])
                    return search_text
                else:
                    return "无法获取行业估值数据"
        
        except Exception as e:
            print(f"Error searching industry valuation: {e}")
            return "搜索失败"
    
    def _build_valuation_prompt(
        self,
        bp_data: Dict[str, Any],
        market_analysis: str,
        industry_data: str
    ) -> str:
        """构建估值分析 Prompt"""
        company_name = bp_data.get("company_name", "目标公司")
        target_market = bp_data.get("target_market", "未知市场")
        funding_request = bp_data.get("funding_request", "未提供")
        current_valuation = bp_data.get("current_valuation", "未提供")
        
        # 提取财务预测
        financial_projections = bp_data.get("financial_projections", [])
        financial_text = "无财务预测数据"
        if financial_projections:
            financial_text = "\n".join([
                f"- {proj.get('year')}年: 营收 {proj.get('revenue', 'N/A')}万元, "
                f"利润 {proj.get('profit', 'N/A')}万元"
                for proj in financial_projections[:3]
            ])
        
        prompt = f"""你是一位专业的投资分析师，擅长早期项目估值分析。

**项目信息**:
- 公司名称: {company_name}
- 目标市场: {target_market}
- 融资需求: {funding_request}
- 当前估值: {current_valuation}

**财务预测**:
{financial_text}

**市场分析摘要**:
{market_analysis[:500]}...

**行业估值参考数据**:
{industry_data[:800]}

**任务**: 请基于以上信息，进行估值分析，输出 JSON 格式：

{{
  "valuation_range": {{
    "low": 估值下限（单位：元）,
    "high": 估值上限（单位：元）
  }},
  "methodology": "估值方法（如：可比公司法、收入倍数法）",
  "comparable_companies": [
    {{
      "name": "可比公司名称",
      "pe_ratio": 市盈率（可选）,
      "ps_ratio": 市销率（可选）,
      "market_cap": "市值描述",
      "growth_rate": "增长率"
    }}
  ],
  "key_assumptions": [
    "关键假设1",
    "关键假设2",
    "关键假设3"
  ],
  "risks": [
    "估值风险1",
    "估值风险2"
  ],
  "analysis_text": "详细的估值分析，包括：\\n1. 估值方法论\\n2. 估值区间计算过程\\n3. 可比公司分析\\n4. 关键假设说明\\n5. 风险提示\\n\\n（用 Markdown 格式，500-800字）"
}}

**要求**:
1. 估值区间要合理，考虑早期项目的不确定性
2. 至少提供 2-3 个可比公司（可以是上市公司或融资案例）
3. 关键假设要明确（如收入倍数、增长率等）
4. 风险提示要具体
5. analysis_text 要详细、专业、结构化

请只输出 JSON，不要包含其他文字。
"""
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM Gateway"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.llm_gateway_url}/generate",
                    json={"prompt": prompt}
                )
                
                if response.status_code == 200:
                    return response.json().get("text", "")
                else:
                    raise Exception(f"LLM returned {response.status_code}")
        
        except Exception as e:
            print(f"Error calling LLM: {e}")
            raise
    
    def _parse_llm_response(self, response: str, bp_data: Dict[str, Any]) -> ValuationAnalysis:
        """解析 LLM 响应"""
        import json
        import re
        
        try:
            # 清理响应（移除可能的 markdown 代码块标记）
            cleaned = re.sub(r'```json\s*|\s*```', '', response.strip())
            data = json.loads(cleaned)
            
            return ValuationAnalysis(
                valuation_range=ValuationRange(**data["valuation_range"]),
                methodology=data.get("methodology", "可比公司法"),
                comparable_companies=[
                    ComparableCompany(**comp) 
                    for comp in data.get("comparable_companies", [])
                ],
                key_assumptions=data.get("key_assumptions", []),
                risks=data.get("risks", []),
                analysis_text=data.get("analysis_text", "")
            )
        
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return self._create_fallback_analysis(bp_data)
    
    def _create_fallback_analysis(self, bp_data: Dict[str, Any]) -> ValuationAnalysis:
        """创建后备分析结果"""
        # 基于融资需求估算一个简单的估值区间
        funding_str = bp_data.get("funding_request", "3000万元")
        
        # 提取数字（简单处理）
        import re
        numbers = re.findall(r'(\d+)', funding_str)
        funding_amount = int(numbers[0]) * 10000 if numbers else 30000000
        
        # 假设融资占比 15-20%，反推估值
        valuation_low = funding_amount / 0.20
        valuation_high = funding_amount / 0.15
        
        return ValuationAnalysis(
            valuation_range=ValuationRange(
                low=valuation_low,
                high=valuation_high
            ),
            methodology="收入倍数法（估算）",
            comparable_companies=[
                ComparableCompany(
                    name="行业平均水平",
                    ps_ratio=8.0,
                    market_cap="N/A",
                    growth_rate="30-40%"
                )
            ],
            key_assumptions=[
                "基于融资金额反推估值",
                "假设融资占比 15-20%",
                "参考早期项目估值区间"
            ],
            risks=[
                "数据不足，估值不确定性高",
                "实际估值需要更详细的财务分析"
            ],
            analysis_text=f"""## 估值分析（简化版）

由于数据有限，本次估值采用简化方法。

### 估值区间
- **估值范围**: {valuation_low/100000000:.1f} 亿元 - {valuation_high/100000000:.1f} 亿元
- **方法**: 基于融资金额反推

### 关键假设
- 融资金额: {funding_str}
- 假设融资占比: 15-20%
- 早期项目估值波动性大

### 风险提示
⚠️ 本估值为初步估算，建议进行更详细的财务尽调后重新评估。
"""
        )
