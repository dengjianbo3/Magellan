"""
Compatibility registry shim.

This module preserves the legacy `app.core.agents.registry` interface while
delegating all runtime behavior to the unified registry in `app.core.agent_registry`.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..agent_registry import AgentRegistry as UnifiedAgentRegistry
from ..agent_registry import get_registry as get_unified_registry

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Legacy-compatible facade over the unified registry.
    """

    _instance: Optional["AgentRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._unified: UnifiedAgentRegistry = get_unified_registry()
        logger.info("[AgentRegistryCompat] Delegating to app.core.agent_registry")

    def _scenario_to_workflow_id(self, scenario: str) -> str:
        mapping = {
            "early_stage": "early-stage-investment",
            "growth": "growth-investment",
            "public_market": "public-market-investment",
            "alternative": "alternative-investment",
            "industry_research": "industry-research",
        }
        return mapping.get(str(scenario or "").strip(), str(scenario or "").strip())

    def get_agent_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self._unified.get_agent_config(agent_id)

    def create_agent(
        self,
        agent_id: str,
        language: str = "zh",
        quick_mode: bool = False,
        **kwargs,
    ) -> Any:
        params = dict(kwargs)
        params.setdefault("language", language)
        params.setdefault("quick_mode", quick_mode)
        return self._unified.create_agent(agent_id, **params)

    def list_agents(
        self,
        type_filter: Optional[str] = None,
        scope_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self._unified.list_agents(agent_type=type_filter, scope=scope_filter)

    def list_atomic_agents(self) -> List[Dict[str, Any]]:
        return self._unified.get_atomic_agents()

    def list_special_agents(self) -> List[Dict[str, Any]]:
        return self._unified.list_agents(agent_type="special")

    def get_agents_for_scenario(self, scenario: str) -> List[str]:
        # Roundtable is config-driven by scope rather than workflow.
        if str(scenario or "").strip() == "roundtable":
            agents = self._unified.list_agents(scope="roundtable")
            # Keep leader first for orchestration consistency.
            ids = [a.get("agent_id") for a in agents if a.get("agent_id")]
            if "leader" in ids:
                ids = ["leader"] + [a for a in ids if a != "leader"]
            return ids

        workflow_id = self._scenario_to_workflow_id(scenario)
        steps = self._unified.get_workflow_steps(workflow_id, mode="standard") or []
        ordered: List[str] = []
        for step in steps:
            agent_id = step.get("agent_id")
            if agent_id and agent_id not in ordered:
                ordered.append(agent_id)
        return ordered


def get_agent_registry() -> AgentRegistry:
    return AgentRegistry()
