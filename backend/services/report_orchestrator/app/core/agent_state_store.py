"""
Agent State Store (Redis-backed with in-memory fallback)

Stores:
- enabled/disabled status per agent_id
- user custom config per agent_id

Rationale:
Agents UI should not lose state across process/container restarts.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict, Optional

import redis


class AgentStateStore:
    ENABLED_KEY = "agents:enabled"          # Hash: agent_id -> "1"/"0"
    CUSTOM_CONFIG_KEY = "agents:custom_cfg" # Hash: agent_id -> json

    def __init__(self, redis_url: Optional[str] = None):
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379")

        self._redis = None
        self._enabled_mem: Dict[str, bool] = {}
        self._cfg_mem: Dict[str, Dict[str, Any]] = {}

        try:
            self._redis = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self._redis.ping()
        except Exception:
            # Keep running with in-memory fallback.
            self._redis = None

    @property
    def redis_available(self) -> bool:
        return self._redis is not None

    def _enabled_key(self, user_id: Optional[str]) -> str:
        if not user_id:
            return self.ENABLED_KEY
        return f"{self.ENABLED_KEY}:{user_id}"

    def _custom_config_key(self, user_id: Optional[str]) -> str:
        if not user_id:
            return self.CUSTOM_CONFIG_KEY
        return f"{self.CUSTOM_CONFIG_KEY}:{user_id}"

    def get_enabled(self, agent_id: str, default: bool = True, user_id: Optional[str] = None) -> bool:
        if not agent_id:
            return default
        if self._redis is None:
            mem_key = f"{user_id or '__global__'}:{agent_id}"
            return self._enabled_mem.get(mem_key, default)
        try:
            v = self._redis.hget(self._enabled_key(user_id), agent_id)
            if v is None:
                return default
            return str(v) == "1"
        except Exception:
            return default

    def set_enabled(self, agent_id: str, enabled: bool, user_id: Optional[str] = None) -> None:
        if not agent_id:
            return
        if self._redis is None:
            mem_key = f"{user_id or '__global__'}:{agent_id}"
            self._enabled_mem[mem_key] = bool(enabled)
            return
        try:
            self._redis.hset(self._enabled_key(user_id), agent_id, "1" if enabled else "0")
        except Exception:
            mem_key = f"{user_id or '__global__'}:{agent_id}"
            self._enabled_mem[mem_key] = bool(enabled)

    def get_custom_config(self, agent_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        if not agent_id:
            return {}
        if self._redis is None:
            mem_key = f"{user_id or '__global__'}:{agent_id}"
            return self._cfg_mem.get(mem_key, {}).copy()
        try:
            raw = self._redis.hget(self._custom_config_key(user_id), agent_id)
            if not raw:
                return {}
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def update_custom_config(
        self,
        agent_id: str,
        patch: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        current = self.get_custom_config(agent_id, user_id=user_id)
        current.update(patch or {})
        if self._redis is None:
            mem_key = f"{user_id or '__global__'}:{agent_id}"
            self._cfg_mem[mem_key] = current
            return current
        try:
            self._redis.hset(
                self._custom_config_key(user_id),
                agent_id,
                json.dumps(current, ensure_ascii=False, default=str),
            )
        except Exception:
            mem_key = f"{user_id or '__global__'}:{agent_id}"
            self._cfg_mem[mem_key] = current
        return current


@lru_cache
def get_agent_state_store() -> AgentStateStore:
    return AgentStateStore()
