# backend/services/report_orchestrator/app/parsers/bp_parser.py
"""
Business Plan (BP) Parser using LLM Gateway's file understanding capability.
使用 LLM Gateway 的文件理解能力解析商业计划书
"""
import httpx
import json
import io
from typing import Dict, Any
from ..models.dd_models import BPStructuredData, TeamMember, FinancialProjection


class BPParser:
    """Parser for Business Plan documents"""
    
    def __init__(self, llm_gateway_url: str):
        self.llm_gateway_url = llm_gateway_url
    
    async def parse_bp(
        self, 
        file_content: bytes, 
        filename: str,
        company_name: str
    ) -> BPStructuredData:
        """
        Parse BP PDF and extract structured data.
        
        Args:
            file_content: PDF file content as bytes
            filename: Original filename
            company_name: Company name (for validation)
        
        Returns:
            BPStructuredData with extracted information
        """
        # Construct structured prompt
        prompt = self._build_extraction_prompt(company_name)
        
        # Call LLM Gateway's file understanding endpoint
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Prepare file
            files = {
                "file": (filename, io.BytesIO(file_content), "application/pdf")
            }
            data = {
                "prompt": prompt
            }
            
            response = await client.post(
                f"{self.llm_gateway_url}/generate_from_file",
                files=files,
                data=data
            )
            
            if response.status_code != 200:
                raise Exception(f"LLM Gateway returned {response.status_code}: {response.text}")
            
            result = response.json()
            content = result.get("content", "")
            
            # Parse JSON from LLM response
            bp_data = self._parse_llm_response(content, company_name)
            
            return bp_data
    
    def _build_extraction_prompt(self, company_name: str) -> str:
        """Build structured extraction prompt for LLM"""
        return f"""你是一位专业的投资分析师，正在阅读 {company_name} 的商业计划书（BP）。

**任务**: 从这份 BP 中提取关键结构化信息。请仔细阅读整份文档，提取以下信息。

**输出格式**: 请严格按照以下 JSON 格式输出（不要包含 markdown 代码块标记，只输出纯 JSON）：

{{
  "company_name": "{company_name}",
  "founding_date": "成立日期，如：2023-03（如果找不到则为 null）",
  "team": [
    {{
      "name": "创始人/核心成员姓名",
      "title": "职位（如：CEO, CTO, COO）",
      "background": "教育背景和工作经历的详细描述"
    }}
  ],
  "product_name": "产品名称",
  "product_description": "产品功能和价值主张的描述",
  "core_technology": "核心技术或技术壁垒的说明",
  "target_market": "目标市场/行业（如：企业SaaS、消费互联网）",
  "market_size_tam": "市场规模TAM的文字描述（包含数字和单位，如：'2025年预计1000亿元'）",
  "target_customers": "目标客户群体描述",
  "competitors": ["主要竞品公司名称1", "竞品2", "竞品3"],
  "competitive_advantages": "相对竞品的差异化优势说明",
  "funding_request": "本轮融资金额（文字描述，如：'A轮3000万元'）",
  "current_valuation": "当前估值（文字描述，如：'投前估值2亿元'）",
  "use_of_funds": "融资资金的使用计划",
  "financial_projections": [
    {{
      "year": 2024,
      "revenue": 1000.0,
      "profit": -200.0,
      "user_count": 10000,
      "notes": "其他备注"
    }}
  ],
  "current_stage": "当前业务阶段（如：MVP已完成、已上线、已盈利）",
  "key_metrics": {{
    "mrr": "月经常性收入（如有）",
    "user_count": "当前用户数",
    "growth_rate": "增长率"
  }}
}}

**提取要点**:
1. **团队 (team)**: 至少提取 CEO、CTO 等核心创始人，背景描述要详细（包括教育、工作经历、成就）
2. **市场规模 (market_size_tam)**: 用文字描述（如"2025年1000亿元"），不要只写数字
3. **融资 (funding_request, current_valuation)**: 用文字描述，包含轮次和单位
4. **财务预测 (financial_projections)**: 如果 BP 有财务预测表格，提取至少3年的数据
5. **如果某字段在 BP 中找不到，设为 null**
6. **competitors 必须是数组，即使只有一个竞品**
7. **确保输出是有效的 JSON，可以被 json.loads() 解析**

开始分析：
"""
    
    def _parse_llm_response(self, content: str, company_name: str) -> BPStructuredData:
        """Parse LLM response and create BPStructuredData"""
        try:
            # Try to parse JSON directly
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            import re
            match = re.search(r"```json\n(.*)\n```", content, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
            else:
                # If parsing fails, return minimal data
                print(f"Warning: Failed to parse LLM response as JSON: {content[:200]}")
                return BPStructuredData(
                    company_name=company_name,
                    product_description="解析失败，请人工检查 BP",
                    target_market="未知"
                )
        
        # Convert to BPStructuredData
        team = [TeamMember(**member) for member in data.get("team", [])]
        
        financial_projections = []
        for proj in data.get("financial_projections", []):
            financial_projections.append(FinancialProjection(**proj))
        
        # Convert numeric fields to strings if needed
        market_size_tam = data.get("market_size_tam")
        if isinstance(market_size_tam, (int, float)):
            market_size_tam = str(market_size_tam)
        
        funding_request = data.get("funding_request")
        if isinstance(funding_request, (int, float)):
            funding_request = str(funding_request)
        
        current_valuation = data.get("current_valuation")
        if isinstance(current_valuation, (int, float)):
            current_valuation = str(current_valuation)
        
        return BPStructuredData(
            company_name=data.get("company_name", company_name),
            founding_date=data.get("founding_date"),
            team=team,
            product_name=data.get("product_name"),
            product_description=data.get("product_description", ""),
            core_technology=data.get("core_technology"),
            target_market=data.get("target_market", ""),
            market_size_tam=market_size_tam,
            target_customers=data.get("target_customers"),
            competitors=data.get("competitors", []),
            competitive_advantages=data.get("competitive_advantages"),
            funding_request=funding_request,
            current_valuation=current_valuation,
            use_of_funds=data.get("use_of_funds"),
            financial_projections=financial_projections,
            current_stage=data.get("current_stage"),
            key_metrics=data.get("key_metrics", {})
        )
