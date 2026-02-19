"""
BP Parser Agent
商业计划书解析 Agent

作为分析流程的第一步，解析 BP 并提取结构化数据
所有后续 Agent 将基于 BP 数据进行分析

使用 Gemini 3 API 直接解析 PDF，不走 Kafka
"""
import base64
import logging
from typing import Dict, Any

from app.parsers.gemini_pdf_parser import get_gemini_parser
from app.core.uploaded_file_locator import locate_uploaded_file

logger = logging.getLogger(__name__)


class BPParserAgent:
    """
    BP 解析 Agent
    
    使用 Gemini 3 API 直接解析 PDF 文件，
    作为后续所有分析 Agent 的数据基础
    """
    
    def __init__(
        self,
        llm_gateway_url: str = "http://llm_gateway:8003",  # 保留参数但不使用
        quick_mode: bool = False,
        language: str = "zh"
    ):
        self.quick_mode = quick_mode
        self.language = language
        # 使用 Gemini PDF 解析器
        self.parser = get_gemini_parser()
        
    async def analyze(self, target: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        解析 BP 文件并返回结构化数据
        
        Args:
            target: 包含 bp_file_id 或 bp_file_base64 的 dict
            context: 上下文信息（本 Agent 不需要）
            
        Returns:
            解析后的 BP 结构化数据
        """
        logger.info(f"🔍 BPParserAgent starting analysis...")
        
        bp_filename = target.get('bp_filename', target.get('bp_file_name', 'business_plan.pdf'))
        company_name = target.get('company_name', 'Unknown Company')
        
        # Method 1: Read file from disk using file_id (preferred, avoids Kafka size limits)
        bp_file_id = target.get('bp_file_id')
        bp_content = None

        if bp_file_id:
            file_path = locate_uploaded_file(bp_file_id)
            if file_path:
                with open(file_path, 'rb') as f:
                    bp_content = f.read()
                bp_filename = bp_filename or file_path.rsplit("/", 1)[-1]
                logger.info(f"📄 Loaded BP from disk: {file_path}, size: {len(bp_content)} bytes")
            else:
                logger.error(f"File not found for file_id: {bp_file_id}")
                return {
                    "success": False,
                    "error": f"找不到文件: {bp_file_id}",
                    "bp_data": None
                }
        
        # Method 2: Legacy - decode from base64 (may fail with large files)
        if not bp_content:
            bp_base64 = target.get('bp_file_base64')
            if bp_base64:
                bp_content = base64.b64decode(bp_base64)
                logger.info(f"📄 Decoded BP from base64, size: {len(bp_content)} bytes")
        
        if not bp_content:
            logger.error("No BP file provided in target (neither file_id nor base64)")
            return {
                "success": False,
                "error": "未提供商业计划书文件",
                "bp_data": None
            }
        
        try:
            # 调用 Gemini PDF 解析器
            bp_data = await self.parser.parse_pdf(
                file_content=bp_content,
                filename=bp_filename,
                company_name=company_name
            )
            
            # 转换为 dict
            bp_dict = bp_data.dict() if hasattr(bp_data, 'dict') else bp_data
            
            logger.info(f"✅ BP parsed successfully: {len(bp_dict.get('team', []))} team members extracted")
            
            return {
                "success": True,
                "bp_data": bp_dict,
                "company_name": bp_dict.get('company_name', company_name),
                "product_name": bp_dict.get('product_name'),
                "product_description": bp_dict.get('product_description'),
                "target_market": bp_dict.get('target_market'),
                "competitors": bp_dict.get('competitors', []),
                "team": bp_dict.get('team', []),
                "funding_request": bp_dict.get('funding_request'),
                "current_stage": bp_dict.get('current_stage'),
                # 关键信息摘要，方便后续 Agent 使用
                "summary": self._generate_summary(bp_dict)
            }
            
        except Exception as e:
            logger.error(f"❌ BP parsing failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "bp_data": None
            }
    
    def _generate_summary(self, bp_dict: Dict[str, Any]) -> str:
        """生成 BP 内容摘要，供后续 Agent 参考"""
        parts = []
        
        if bp_dict.get('company_name'):
            parts.append(f"公司: {bp_dict['company_name']}")
        if bp_dict.get('product_name'):
            parts.append(f"产品: {bp_dict['product_name']}")
        if bp_dict.get('target_market'):
            parts.append(f"目标市场: {bp_dict['target_market']}")
        if bp_dict.get('current_stage'):
            parts.append(f"阶段: {bp_dict['current_stage']}")
        if bp_dict.get('funding_request'):
            parts.append(f"融资: {bp_dict['funding_request']}")
        
        team = bp_dict.get('team', [])
        if team:
            team_names = [m.get('name', '') for m in team[:3]]
            parts.append(f"核心团队: {', '.join(team_names)}")
        
        competitors = bp_dict.get('competitors', [])
        if competitors:
            parts.append(f"竞品: {', '.join(competitors[:3])}")
        
        return "; ".join(parts)


def create_bp_parser(
    llm_gateway_url: str = "http://llm_gateway:8003",
    quick_mode: bool = False,
    language: str = "zh"
) -> BPParserAgent:
    """工厂函数：创建 BPParserAgent 实例"""
    return BPParserAgent(
        llm_gateway_url=llm_gateway_url,
        quick_mode=quick_mode,
        language=language
    )


# Agent 元数据
AGENT_METADATA = {
    "agent_id": "bp_parser",
    "name": {
        "zh": "商业计划书解析器",
        "en": "Business Plan Parser"
    },
    "description": {
        "zh": "解析商业计划书，提取公司、产品、团队、市场等结构化信息",
        "en": "Parse business plan to extract structured company, product, team, market information"
    },
    "capabilities": [
        "PDF解析",
        "结构化信息提取",
        "团队信息提取",
        "市场数据提取",
        "融资信息提取"
    ],
    "tags": ["parser", "bp", "extraction"],
    "quick_mode_support": True
}
