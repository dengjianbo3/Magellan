"""
Tech Specialist Agent
技术专家 Agent

职责：评估技术架构、产品能力、技术壁垒和技术债务
"""
from typing import List
from app.core.roundtable.investment_agents import create_tech_specialist
from app.core.roundtable.rewoo_agent import ReWOOAgent

# 类型别名
TechSpecialistAgent = ReWOOAgent

# 导出工厂函数
__all__ = ["create_tech_specialist", "TechSpecialistAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "tech_specialist",
    "name": {
        "zh": "技术专家",
        "en": "Tech Specialist"
    },
    "description": {
        "zh": "评估技术架构、产品能力、技术壁垒和技术债务",
        "en": "Evaluate technical architecture, product capabilities, technical barriers and technical debt"
    },
    "capabilities": [
        "技术架构评估",
        "产品能力分析",
        "技术壁垒识别",
        "技术债务评估",
        "研发效率分析"
    ],
    "tags": ["technology", "product", "innovation"],
    "quick_mode_support": True
}
