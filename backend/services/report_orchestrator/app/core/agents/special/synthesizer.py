"""
Report Synthesizer Agent
报告综合 Agent

职责：综合所有原子Agent的分析结果，生成结构化投资分析报告

注意：此Agent仅用于分析模块workflow的最后一步
"""
from typing import Dict, Any, List, Optional

# 从现有实现导入
from app.agents.report_synthesizer_agent import (
    ReportSynthesizerAgent,
    synthesize_report
)

# 导出
__all__ = ["ReportSynthesizerAgent", "synthesize_report"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "report_synthesizer",
    "type": "special",
    "scope": ["analysis"],  # 仅分析模块使用
    "name": {
        "zh": "报告综合Agent",
        "en": "Report Synthesizer"
    },
    "description": {
        "zh": "综合所有原子Agent的分析结果，生成结构化投资分析报告",
        "en": "Synthesize all atomic agent outputs into structured investment analysis report"
    },
    "capabilities": [
        "多维分析整合",
        "SWOT分析生成",
        "投资建议形成",
        "风险机会识别",
        "结构化报告输出"
    ],
    "tags": ["synthesis", "report", "analysis"],
    "quick_mode_support": True
}
