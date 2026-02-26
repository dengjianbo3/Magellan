"""
Configuration-backed orchestration templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

_CACHE: Dict[str, Dict[str, Any]] | None = None


def _default_templates() -> Dict[str, Dict[str, Any]]:
    return {
        "expert_chat": {
            "max_history": 24,
            "max_attachments": 3,
            "max_attachment_bytes": 6 * 1024 * 1024,
            "leader_followup_after_delegation": False,
            "turn_timeout_seconds": 600,
            "route_strategy": "leader_first",
        },
        "roundtable": {
            "default_max_rounds": 5,
            "seconds_per_round": 600,
            "minimum_duration_seconds": 3600,
            "history_excerpt_chars": 2000,
        },
    }


def _template_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "config" / "orchestration_templates.yaml"


def get_orchestration_templates(force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
    global _CACHE
    if _CACHE is not None and not force_reload:
        return _CACHE

    merged = _default_templates()
    file_path = _template_path()
    if file_path.exists():
        data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict):
            for section, config in data.items():
                if not isinstance(config, dict):
                    continue
                base = merged.setdefault(str(section), {})
                base.update(config)

    _CACHE = merged
    return merged

