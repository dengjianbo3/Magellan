"""
Memory governance helpers (value filtering, provenance, compaction-friendly writes).
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact_text(text: str, max_chars: int = 3200) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + " ..."


def memory_value_score(content: str) -> float:
    text = (content or "").strip()
    if not text:
        return 0.0
    score = min(1.0, len(text) / 1200.0)
    keywords = [
        "结论",
        "建议",
        "风险",
        "evidence",
        "recommendation",
        "risk",
        "confidence",
        "support",
        "resistance",
        "entry",
        "stop",
    ]
    lowered = text.lower()
    if any(k in lowered for k in keywords):
        score += 0.35
    if re.search(r"\b\d+(\.\d+)?%?\b", text):
        score += 0.15
    return min(1.0, score)


def should_persist_memory(content: str, min_score: float = 0.35) -> bool:
    return memory_value_score(content) >= min_score


def make_provenance_metadata(
    *,
    source: str,
    session_id: str = "",
    agent_id: str = "",
    tool: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = dict(extra or {})
    metadata.setdefault("source", source)
    metadata.setdefault("session_id", session_id)
    metadata.setdefault("agent_id", agent_id)
    if tool:
        metadata.setdefault("tool", tool)
    metadata.setdefault("timestamp", utc_now_iso())
    base = f"{metadata.get('source')}|{metadata.get('session_id')}|{metadata.get('agent_id')}|{metadata.get('timestamp')}"
    metadata.setdefault("provenance_id", hashlib.sha1(base.encode("utf-8")).hexdigest()[:16])
    return metadata

