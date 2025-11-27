"""
Unified Agent Module
统一 Agent 模块

提供统一的 Agent 接口，整合:
- 7个原子 Agent (所有场景复用)
- 2个特殊 Agent (特定场景专用)
- Agent 工具集
- Agent 注册中心

使用示例:
    from app.core.agents import AgentRegistry, create_market_analyst

    # 使用注册中心
    registry = AgentRegistry()
    agent = registry.create_agent("market_analyst", quick_mode=True)

    # 直接使用工厂函数
    agent = create_market_analyst(llm_gateway_url="http://llm_gateway:8003")
"""

# 基础接口
from .base.interfaces import (
    AgentInput,
    AgentOutput,
    AgentConfig,
    AgentOutputStatus,
    AtomicAgent
)

# 基础类
from .base import Agent, ReWOOAgent

# 原子 Agent
from .atomic import (
    create_team_evaluator,
    create_market_analyst,
    create_financial_expert,
    create_risk_assessor,
    create_tech_specialist,
    create_legal_advisor,
    create_technical_analyst,
    AGENT_FACTORY_MAP,
    get_atomic_agent_factory,
    list_atomic_agents,
)

# 特殊 Agent
from .special import (
    create_leader,
    ReportSynthesizerAgent,
)

# 注册中心
from .registry import AgentRegistry, get_agent_registry

__all__ = [
    # 接口定义
    "AgentInput",
    "AgentOutput",
    "AgentConfig",
    "AgentOutputStatus",
    "AtomicAgent",

    # 基础类
    "Agent",
    "ReWOOAgent",

    # 原子 Agent 工厂
    "create_team_evaluator",
    "create_market_analyst",
    "create_financial_expert",
    "create_risk_assessor",
    "create_tech_specialist",
    "create_legal_advisor",
    "create_technical_analyst",

    # 特殊 Agent
    "create_leader",
    "ReportSynthesizerAgent",

    # 工具函数
    "AGENT_FACTORY_MAP",
    "get_atomic_agent_factory",
    "list_atomic_agents",

    # 注册中心
    "AgentRegistry",
    "get_agent_registry",
]
