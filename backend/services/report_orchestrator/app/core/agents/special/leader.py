"""
Leader Agent
圆桌主持人 Agent

职责：主持圆桌会议讨论，协调各专家Agent，引导讨论方向，形成共识

注意：此Agent仅用于圆桌会议场景
"""
from typing import List
from app.core.roundtable.investment_agents import create_leader
from app.core.roundtable.agent import Agent

# 类型别名 (Leader 使用基础 Agent，不需要 ReWOO)
LeaderAgent = Agent

# 导出工厂函数
__all__ = ["create_leader", "LeaderAgent"]

# Agent 元数据
AGENT_METADATA = {
    "agent_id": "leader",
    "type": "special",
    "scope": ["roundtable"],  # 仅圆桌会议使用
    "name": {
        "zh": "圆桌主持人",
        "en": "Roundtable Leader"
    },
    "description": {
        "zh": "主持圆桌会议讨论，协调各专家Agent，引导讨论方向，形成共识",
        "en": "Moderate roundtable discussions, coordinate expert agents, guide discussion direction, form consensus"
    },
    "capabilities": [
        "会议流程主持",
        "专家观点协调",
        "讨论方向引导",
        "共识形成",
        "最终决策建议"
    ],
    "tags": ["roundtable", "coordination", "consensus"],
    "quick_mode_support": False
}
