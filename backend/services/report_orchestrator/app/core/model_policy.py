"""
Role-based LLM model routing policy.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import yaml

_CACHE: Optional[Dict[str, str]] = None


def _default_policy() -> Dict[str, str]:
    return {
        "leader_router": "flash",
        "leader_chat": "flash",
        "specialist_chat": "default",
        "roundtable_summary": "pro",
        "attachment_vision": "flash",
    }


def _policy_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "config" / "model_policy.yaml"


def _normalize_model(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "default"
    lower = text.lower()
    if lower in {"default", "pro", "flash"}:
        return lower
    return text


def load_model_policy(force_reload: bool = False) -> Dict[str, str]:
    global _CACHE
    if _CACHE is not None and not force_reload:
        return _CACHE

    policy = _default_policy()
    file_path = _policy_path()
    if file_path.exists():
        try:
            data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
            file_policy = data.get("roles", {}) if isinstance(data, dict) else {}
            if isinstance(file_policy, dict):
                for key, value in file_policy.items():
                    policy[str(key).strip()] = _normalize_model(str(value))
        except Exception:
            pass

    # Env overrides: MODEL_POLICY_LEADER_ROUTER=flash, etc.
    for key in list(policy.keys()):
        env_key = f"MODEL_POLICY_{key.upper()}"
        if env_key in os.environ:
            policy[key] = _normalize_model(os.getenv(env_key, "default"))

    _CACHE = policy
    return policy


def resolve_model_for_role(role: str, fallback: str = "default") -> Optional[str]:
    policy = load_model_policy()
    raw = policy.get(role, fallback)
    normalized = _normalize_model(raw)
    if normalized == "default":
        return None
    return normalized

