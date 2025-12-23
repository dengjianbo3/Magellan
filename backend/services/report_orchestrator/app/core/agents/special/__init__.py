"""
Special Agents Module
特殊 Agent 模块

定义2个特殊 Agent - 用于特定场景
1. leader - 圆桌主持人（仅用于圆桌会议）
2. synthesizer - 报告综合Agent（仅用于分析模块）
"""

from .leader import create_leader, LeaderAgent
from .synthesizer import ReportSynthesizerAgent, create_report_synthesizer

__all__ = [
    "create_leader",
    "LeaderAgent",
    "ReportSynthesizerAgent",
    "create_report_synthesizer",
]

# 特殊 Agent ID 到工厂函数的映射
SPECIAL_AGENT_MAP = {
    "leader": create_leader,
    "report_synthesizer": create_report_synthesizer,
}
