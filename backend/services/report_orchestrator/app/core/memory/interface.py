"""
Unified atomic-agent memory interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MemoryHit:
    """Single memory retrieval hit."""

    content: str
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    collection: str = ""


class MemoryStore(ABC):
    """Abstract memory store for account-scoped, agent-scoped memory."""

    @abstractmethod
    async def add_agent_memory(
        self,
        user_id: str,
        agent_id: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
        collection: str = "episodic",
    ) -> str:
        """Persist one memory item for an agent."""

    @abstractmethod
    async def query_agent_memory(
        self,
        user_id: str,
        agent_id: str,
        query: str,
        top_k: int = 3,
        collection: str = "episodic",
    ) -> List[MemoryHit]:
        """Retrieve memory items for a specific agent."""

    @abstractmethod
    async def add_shared_evidence(
        self,
        user_id: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
    ) -> str:
        """Persist one shared-evidence item for cross-agent reuse."""

    @abstractmethod
    async def query_shared_evidence(
        self,
        user_id: str,
        query: str,
        top_k: int = 3,
    ) -> List[MemoryHit]:
        """Retrieve shared evidence under the same account."""

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """Return provider health/degraded status."""


def format_memory_hits(hits: List[MemoryHit], max_items: int = 3, max_chars: int = 2400) -> str:
    """Render compact memory snippets for prompt context injection."""
    if not hits:
        return ""

    lines: List[str] = []
    used = 0
    for idx, hit in enumerate(hits[:max_items], start=1):
        content = (hit.content or "").strip()
        if not content:
            continue
        block = f"[Memory {idx}] {content}"
        if used + len(block) > max_chars:
            break
        lines.append(block)
        used += len(block)
    return "\n".join(lines)
