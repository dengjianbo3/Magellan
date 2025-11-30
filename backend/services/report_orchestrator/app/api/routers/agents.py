"""
Agents Router
Agent 管理路由

提供 Agent 列表、配置和状态管理的 API
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Depends

from ...core.agents.registry import get_agent_registry
from ...services.storage import get_report_storage, ReportStorage

router = APIRouter()
logger = logging.getLogger(__name__)

# 内存中存储 Agent 状态和自定义配置
# 在生产环境中应该使用 Redis 持久化
_agent_status: Dict[str, bool] = {}  # agent_id -> enabled
_agent_custom_config: Dict[str, Dict[str, Any]] = {}  # agent_id -> custom config


class AgentConfigUpdate(BaseModel):
    """Agent 配置更新请求"""
    quick_mode: Optional[bool] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    custom_prompt: Optional[str] = None


class AgentStatusUpdate(BaseModel):
    """Agent 状态更新请求"""
    enabled: bool


def get_storage() -> ReportStorage:
    """依赖注入：获取报告存储服务"""
    return get_report_storage()


@router.get("")
async def list_agents(
    type_filter: Optional[str] = None,
    scope_filter: Optional[str] = None,
    storage: ReportStorage = Depends(get_storage)
):
    """
    获取所有 Agent 列表

    Query Parameters:
        type_filter: 类型过滤 (atomic/special)
        scope_filter: 范围过滤 (roundtable/analysis)
    """
    registry = get_agent_registry()
    agents = registry.list_agents(type_filter=type_filter, scope_filter=scope_filter)

    # 从报告中统计 Agent 使用情况
    all_reports = storage.get_all(limit=1000)
    agent_usage = {}

    for report in all_reports:
        for step in report.get("steps", []):
            agent_name = step.get("agent", step.get("agent_name", ""))
            if agent_name:
                if agent_name not in agent_usage:
                    agent_usage[agent_name] = {"count": 0, "success": 0}
                agent_usage[agent_name]["count"] += 1
                if step.get("status") in ["completed", "success"]:
                    agent_usage[agent_name]["success"] += 1

    # 增强 Agent 信息
    enhanced_agents = []
    for agent in agents:
        agent_id = agent.get("agent_id", "")

        # 获取使用统计
        usage = agent_usage.get(agent_id, {"count": 0, "success": 0})
        success_rate = (usage["success"] / usage["count"] * 100) if usage["count"] > 0 else 100

        # 获取状态
        enabled = _agent_status.get(agent_id, True)  # 默认启用

        # 获取自定义配置
        custom_config = _agent_custom_config.get(agent_id, {})

        enhanced_agents.append({
            "agent_id": agent_id,
            "type": agent.get("type", "atomic"),
            "scope": agent.get("scope", []),
            "name": agent.get("name", {}),
            "description": agent.get("description", {}),
            "capabilities": agent.get("capabilities", []),
            "tags": agent.get("tags", []),
            "quick_mode_support": agent.get("quick_mode_support", False),
            "estimated_duration": agent.get("estimated_duration", {}),
            # 运行时信息
            "enabled": enabled,
            "usage_count": usage["count"],
            "success_rate": round(success_rate, 1),
            "custom_config": custom_config,
            "status": "active" if enabled else "disabled"
        })

    return {
        "success": True,
        "count": len(enhanced_agents),
        "agents": enhanced_agents
    }


@router.get("/{agent_id}")
async def get_agent(agent_id: str, storage: ReportStorage = Depends(get_storage)):
    """
    获取指定 Agent 的详细信息
    """
    registry = get_agent_registry()
    agent_config = registry.get_agent_config(agent_id)

    if not agent_config:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # 从报告中统计使用情况
    all_reports = storage.get_all(limit=500)
    usage_count = 0
    success_count = 0
    recent_analyses = []

    for report in all_reports:
        for step in report.get("steps", []):
            step_agent = step.get("agent", step.get("agent_name", ""))
            if step_agent and agent_id.lower() in step_agent.lower():
                usage_count += 1
                if step.get("status") in ["completed", "success"]:
                    success_count += 1
                # 收集最近分析
                if len(recent_analyses) < 5:
                    recent_analyses.append({
                        "report_id": report.get("id"),
                        "company": report.get("company_name"),
                        "date": report.get("created_at"),
                        "status": step.get("status")
                    })

    success_rate = (success_count / usage_count * 100) if usage_count > 0 else 100

    return {
        "success": True,
        "agent": {
            **agent_config,
            "enabled": _agent_status.get(agent_id, True),
            "usage_count": usage_count,
            "success_rate": round(success_rate, 1),
            "custom_config": _agent_custom_config.get(agent_id, {}),
            "recent_analyses": recent_analyses
        }
    }


@router.put("/{agent_id}/config")
async def update_agent_config(agent_id: str, config: AgentConfigUpdate):
    """
    更新 Agent 配置
    """
    registry = get_agent_registry()
    agent_config = registry.get_agent_config(agent_id)

    if not agent_config:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # 更新自定义配置
    if agent_id not in _agent_custom_config:
        _agent_custom_config[agent_id] = {}

    update_data = config.model_dump(exclude_none=True)
    _agent_custom_config[agent_id].update(update_data)

    logger.info(f"Updated config for agent {agent_id}: {update_data}")

    return {
        "success": True,
        "message": f"Agent {agent_id} config updated",
        "config": _agent_custom_config[agent_id]
    }


@router.patch("/{agent_id}/status")
async def update_agent_status(agent_id: str, status: AgentStatusUpdate):
    """
    更新 Agent 状态 (启用/禁用)
    """
    registry = get_agent_registry()
    agent_config = registry.get_agent_config(agent_id)

    if not agent_config:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    _agent_status[agent_id] = status.enabled

    logger.info(f"Agent {agent_id} status changed to: {'enabled' if status.enabled else 'disabled'}")

    return {
        "success": True,
        "message": f"Agent {agent_id} {'enabled' if status.enabled else 'disabled'}",
        "agent_id": agent_id,
        "enabled": status.enabled
    }


@router.get("/scenarios/{scenario}")
async def get_agents_for_scenario(scenario: str):
    """
    获取某个场景需要的 Agent 列表

    场景:
        - early_stage: 早期投资
        - growth: 成长期投资
        - public_market: 公开市场
        - alternative: 另类投资
        - industry_research: 行业研究
        - roundtable: 圆桌讨论
    """
    registry = get_agent_registry()
    agent_ids = registry.get_agents_for_scenario(scenario)

    if not agent_ids:
        raise HTTPException(status_code=404, detail=f"No agents found for scenario: {scenario}")

    # 获取完整配置
    agents = []
    for agent_id in agent_ids:
        config = registry.get_agent_config(agent_id)
        if config:
            agents.append({
                "agent_id": agent_id,
                "name": config.get("name", {}),
                "description": config.get("description", {}),
                "type": config.get("type"),
                "enabled": _agent_status.get(agent_id, True)
            })

    return {
        "success": True,
        "scenario": scenario,
        "agent_ids": agent_ids,
        "agents": agents
    }


@router.get("/stats/summary")
async def get_agent_stats_summary(storage: ReportStorage = Depends(get_storage)):
    """
    获取 Agent 使用统计摘要
    """
    registry = get_agent_registry()
    all_agents = registry.list_agents()
    all_reports = storage.get_all(limit=1000)

    # 统计
    total_agents = len(all_agents)
    enabled_agents = sum(1 for a in all_agents if _agent_status.get(a.get("agent_id", ""), True))
    total_analyses = len(all_reports)

    # Agent 使用分布
    agent_usage = {}
    for report in all_reports:
        for step in report.get("steps", []):
            agent_name = step.get("agent", step.get("agent_name", "unknown"))
            agent_usage[agent_name] = agent_usage.get(agent_name, 0) + 1

    # 按使用量排序
    top_agents = sorted(agent_usage.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "success": True,
        "summary": {
            "total_agents": total_agents,
            "enabled_agents": enabled_agents,
            "disabled_agents": total_agents - enabled_agents,
            "atomic_agents": len([a for a in all_agents if a.get("type") == "atomic"]),
            "special_agents": len([a for a in all_agents if a.get("type") == "special"]),
            "total_analyses": total_analyses,
            "top_agents": [{"agent": name, "usage": count} for name, count in top_agents]
        }
    }
