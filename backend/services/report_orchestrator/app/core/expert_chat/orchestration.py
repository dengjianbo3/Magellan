"""
Expert-chat orchestration utilities.

Includes:
- Dependency-aware stage planning (DAG-like batching with bounded parallelism).
- Lightweight evidence packet extraction to support cross-specialist reuse.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


INTERNAL_EVIDENCE_BLOCK_RE = re.compile(
    r"\[INTERNAL_EVIDENCE_PACKET\]\s*(\{[\s\S]*?\})\s*\[/INTERNAL_EVIDENCE_PACKET\]",
    re.IGNORECASE,
)

# Use chat ids (hyphen style) because expert-chat routes on chat ids.
DEFAULT_SPECIALIST_DEPENDENCIES: Dict[str, List[str]] = {
    "quant-strategist": [
        "technical-analyst",
        "onchain-analyst",
        "market-analyst",
        "macro-economist",
        "sentiment-analyst",
    ],
    "risk-assessor": [
        "technical-analyst",
        "onchain-analyst",
        "market-analyst",
        "macro-economist",
        "financial-expert",
        "legal-advisor",
        "tech-specialist",
        "team-evaluator",
        "esg-analyst",
        "quant-strategist",
        "deal-structurer",
        "ma-advisor",
        "contrarian-analyst",
    ],
    "deal-structurer": [
        "risk-assessor",
        "financial-expert",
        "legal-advisor",
        "market-analyst",
        "ma-advisor",
    ],
    "ma-advisor": [
        "market-analyst",
        "financial-expert",
        "legal-advisor",
    ],
    "contrarian-analyst": [
        "market-analyst",
        "technical-analyst",
        "onchain-analyst",
        "macro-economist",
        "sentiment-analyst",
        "quant-strategist",
    ],
}


def _normalize_chat_agent_id(agent_id: str) -> str:
    return str(agent_id or "").strip().lower().replace("_", "-")


def build_execution_stages(
    agent_ids: List[str],
    max_parallel: int = 2,
    dependency_map: Optional[Dict[str, List[str]]] = None,
) -> List[List[str]]:
    """
    Build dependency-aware execution stages.

    Rules:
    - Preserve original order where possible.
    - Respect dependencies inside selected agent set.
    - Apply bounded parallelism by splitting large ready sets into chunks.
    - If cycle detected, fall back to order-based single-step release.
    """
    ordered = [_normalize_chat_agent_id(a) for a in agent_ids if str(a or "").strip()]
    if not ordered:
        return []

    max_parallel = max(1, int(max_parallel or 1))
    selected = set(ordered)
    deps_src = dependency_map or DEFAULT_SPECIALIST_DEPENDENCIES
    deps: Dict[str, set[str]] = {}

    for aid in ordered:
        raw = deps_src.get(aid, [])
        deps[aid] = {dep for dep in (_normalize_chat_agent_id(x) for x in raw) if dep in selected and dep != aid}

    pending = set(ordered)
    stages: List[List[str]] = []
    index = {aid: i for i, aid in enumerate(ordered)}

    while pending:
        ready = sorted([aid for aid in pending if not deps.get(aid)], key=lambda x: index[x])
        if not ready:
            # Cycle fallback: release one agent by original order.
            ready = [sorted(list(pending), key=lambda x: index[x])[0]]

        # Split by max_parallel for bounded concurrency.
        while ready:
            batch = ready[:max_parallel]
            ready = ready[max_parallel:]
            stages.append(batch)
            for done in batch:
                pending.discard(done)
                for other in pending:
                    deps.setdefault(other, set()).discard(done)

    return stages


def _safe_json_loads(payload: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(payload)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None
    return None


def _extract_internal_evidence_block(content: str) -> tuple[str, Optional[Dict[str, Any]]]:
    if not content:
        return "", None
    match = INTERNAL_EVIDENCE_BLOCK_RE.search(content)
    if not match:
        return content.strip(), None
    evidence = _safe_json_loads(match.group(1))
    cleaned = INTERNAL_EVIDENCE_BLOCK_RE.sub("", content).strip()
    return cleaned, evidence


def _extract_key_points(text: str, max_items: int = 6) -> List[str]:
    if not text:
        return []
    out: List[str] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-*•").strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if len(line) < 8:
            continue
        out.append(line[:220])
        if len(out) >= max_items:
            break
    return out


def _extract_risk_points(text: str, max_items: int = 3) -> List[str]:
    if not text:
        return []
    out: List[str] = []
    patterns = ("风险", "risk", "警惕", "warning", "止损", "invalidat")
    for raw in text.splitlines():
        line = raw.strip().lstrip("-*•").strip()
        if not line:
            continue
        norm = line.lower()
        if any(p in norm for p in patterns):
            out.append(line[:220])
            if len(out) >= max_items:
                break
    return out


def _extract_confidence(text: str) -> Optional[int]:
    if not text:
        return None
    patterns = [
        r"置信度[:：\s]*([0-9]{1,3})\s*%?",
        r"confidence[:\s]*([0-9]{1,3})\s*%?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            value = int(match.group(1))
            return max(0, min(100, value))
        except Exception:
            continue
    return None


def extract_specialist_response(
    agent_id: str,
    agent_name: str,
    raw_content: str,
    language: str,
) -> Dict[str, Any]:
    """
    Parse specialist content into:
    - `content`: display content for user chat.
    - `summary`: compact summary for history/context budget.
    - `evidence_packet`: structured evidence board item.
    """
    cleaned, explicit_packet = _extract_internal_evidence_block(raw_content or "")
    key_points = _extract_key_points(cleaned)
    risk_points = _extract_risk_points(cleaned)
    confidence = _extract_confidence(cleaned)
    summary = (cleaned or "").strip().replace("\n", " ")
    summary = summary[:260]

    packet: Dict[str, Any] = {
        "agent_id": _normalize_chat_agent_id(agent_id),
        "agent_name": str(agent_name or agent_id),
        "summary": summary,
        "key_points": key_points[:6],
        "risks": risk_points[:3],
        "confidence": confidence,
        "language": "zh" if str(language or "").lower().startswith("zh") else "en",
    }
    if explicit_packet:
        # Keep explicit fields if model returned them; fallback fields still preserved.
        for key in ("summary", "key_points", "risks", "confidence", "next_questions"):
            if key in explicit_packet and explicit_packet.get(key) not in (None, "", []):
                packet[key] = explicit_packet.get(key)

    return {
        "content": cleaned.strip(),
        "summary": packet.get("summary") or summary,
        "evidence_packet": packet,
    }


def format_shared_evidence_context(
    evidence_packets: List[Dict[str, Any]],
    language: str,
    max_items: int = 6,
    max_chars: int = 1800,
) -> str:
    if not evidence_packets:
        return ""
    zh = str(language or "").lower().startswith("zh")
    lines: List[str] = []
    for item in evidence_packets[-max_items:]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("agent_name") or item.get("agent_id") or "Expert").strip()
        summary = str(item.get("summary") or "").strip()
        if not summary:
            continue
        confidence = item.get("confidence")
        key_points = item.get("key_points") if isinstance(item.get("key_points"), list) else []
        point_text = " | ".join(str(x).strip() for x in key_points[:3] if str(x).strip())
        if zh:
            row = f"[{name}] 摘要: {summary}"
            if point_text:
                row += f"；关键点: {point_text}"
            if confidence is not None:
                row += f"；置信度: {confidence}"
        else:
            row = f"[{name}] Summary: {summary}"
            if point_text:
                row += f"; key points: {point_text}"
            if confidence is not None:
                row += f"; confidence: {confidence}"
        lines.append(row[:420])

    text = "\n".join(lines).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 16] + "\n...[trimmed]"

