"""
Gemini PDF Parser
使用 Gemini 3 API 直接解析文档文件（PDF 为主）

优点:
- 不走 Kafka，避免消息大小限制
- 直接利用 Gemini 的多模态文档理解能力（含 OCR）
- 更准确的结构化信息提取
"""
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Gemini 模型名称
GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-3.1-pro-preview")
GEMINI_API_VERSION = os.getenv("GEMINI_API_VERSION", "v1alpha")
GEMINI_PDF_MEDIA_RESOLUTION = os.getenv("GEMINI_PDF_MEDIA_RESOLUTION", "media_resolution_medium")
GEMINI_DOC_THINKING_LEVEL = os.getenv("GEMINI_DOC_THINKING_LEVEL", "low")


class GeminiPDFParser:
    """
    使用 Gemini 3 API 解析 PDF 文件
    
    利用 Gemini 的原生 PDF 理解能力提取结构化数据
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        初始化 Gemini PDF 解析器
        
        Args:
            api_key: Google API Key (默认从环境变量读取)
            model: 模型名称 (默认从环境变量读取)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model = model or GEMINI_MODEL
        
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        # Initialize Gemini client
        self._client = None
        
    def _get_client(self):
        """懒加载 Gemini 客户端"""
        if self._client is None:
            try:
                from google import genai
                # v1alpha is required for media_resolution in current Gemini SDK flow.
                self._client = genai.Client(
                    api_key=self.api_key,
                    http_options={"api_version": GEMINI_API_VERSION}
                )
                logger.info(f"Gemini client initialized with model: {self.model}")
            except ImportError:
                raise ImportError("google-genai package not installed. Run: pip install google-genai")
        return self._client

    @staticmethod
    def _guess_mime_type(filename: str) -> str:
        ext = os.path.splitext((filename or "").lower())[1]
        if ext == ".pdf":
            return "application/pdf"
        if ext in (".jpg", ".jpeg"):
            return "image/jpeg"
        if ext == ".png":
            return "image/png"
        if ext == ".webp":
            return "image/webp"
        if ext == ".txt":
            return "text/plain"
        return "application/pdf"
    
    async def parse_pdf(
        self, 
        file_content: bytes, 
        filename: str,
        company_name: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        解析 PDF 文件并提取结构化数据
        
        Args:
            file_content: PDF 文件内容 (bytes)
            filename: 文件名
            company_name: 公司名称 (用于验证)
            
        Returns:
            结构化 BP 数据字典
        """
        logger.info(f"📄 Parsing PDF with Gemini: {filename}, size: {len(file_content)} bytes")
        
        try:
            client = self._get_client()
            mime_type = self._guess_mime_type(filename)
            
            # Build the structured extraction prompt
            prompt = self._build_extraction_prompt(company_name)
            
            # Use Gemini's native PDF understanding via inline_data
            from google.genai import types

            file_part = types.Part(
                inline_data=types.Blob(
                    mime_type=mime_type,
                    data=file_content,
                ),
                media_resolution={"level": GEMINI_PDF_MEDIA_RESOLUTION},
            )

            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_level=GEMINI_DOC_THINKING_LEVEL),
            )

            try:
                # Preferred path: Gemini 3 multimodal document parsing with media resolution.
                response = client.models.generate_content(
                    model=self.model,
                    contents=[types.Content(parts=[types.Part(text=prompt), file_part])],
                    config=config,
                )
            except TypeError:
                # Backward compatible fallback for SDKs without media_resolution field.
                fallback_part = types.Part(
                    inline_data=types.Blob(
                        mime_type=mime_type,
                        data=file_content,
                    ),
                )
                response = client.models.generate_content(
                    model=self.model,
                    contents=[types.Content(parts=[types.Part(text=prompt), fallback_part])],
                    config=config,
                )
            
            # Extract response text
            response_text = (response.text or "").strip()
            logger.info(f"✅ Gemini response received: {len(response_text)} chars")
            
            # Parse JSON from response
            bp_data = self._parse_response(response_text, company_name)
            
            return bp_data
            
        except Exception as e:
            logger.error(f"❌ Gemini PDF parsing failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _build_extraction_prompt(self, company_name: str) -> str:
        """构建 PDF 信息提取的提示词"""
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
    
    def _parse_response(self, response_text: str, company_name: str) -> Dict[str, Any]:
        """解析 Gemini 返回的 JSON 响应"""
        try:
            # Try to parse JSON directly
            data = json.loads(response_text)
            return data
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            import re
            match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                return data
            
            # Try finding JSON object in text
            match = re.search(r'\{[\s\S]*\}', response_text)
            if match:
                try:
                    data = json.loads(match.group(0))
                    return data
                except json.JSONDecodeError:
                    pass

            # Handle occasional leading/trailing markdown-like wrappers.
            cleaned = response_text.strip().strip("`")
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            
            # If parsing fails, return minimal data
            logger.warning(f"Failed to parse Gemini response as JSON: {response_text[:200]}...")
            return {
                "company_name": company_name,
                "product_description": "解析失败，请人工检查 BP",
                "target_market": "未知",
                "team": [],
                "competitors": [],
                "parse_error": True,
                "raw_response": response_text[:500]
            }


# Singleton instance
_parser_instance: Optional[GeminiPDFParser] = None


def get_gemini_parser() -> GeminiPDFParser:
    """获取 Gemini PDF 解析器单例"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = GeminiPDFParser()
    return _parser_instance


async def parse_pdf_with_gemini(
    file_content: bytes,
    filename: str,
    company_name: str = "Unknown"
) -> Dict[str, Any]:
    """
    便捷函数：使用 Gemini 解析 PDF
    
    Args:
        file_content: PDF 文件内容
        filename: 文件名
        company_name: 公司名称
        
    Returns:
        结构化 BP 数据
    """
    parser = get_gemini_parser()
    return await parser.parse_pdf(file_content, filename, company_name)
