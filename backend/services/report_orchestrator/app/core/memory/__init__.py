"""
Unified atomic memory provider factory.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from .interface import MemoryHit, MemoryStore, format_memory_hits
from .noop_store import NoopMemoryStore
from .qmd_store import QmdMemoryStore
from .redis_store import RedisMemoryStore

logger = logging.getLogger(__name__)

_memory_store: Optional[MemoryStore] = None
_memory_provider: Optional[str] = None


def get_memory_store(provider: Optional[str] = None) -> MemoryStore:
    """Return singleton memory store based on ATOMIC_MEMORY_PROVIDER."""
    global _memory_store, _memory_provider

    resolved = (provider or os.getenv("ATOMIC_MEMORY_PROVIDER", "auto")).strip().lower()
    if _memory_store is not None and _memory_provider == resolved:
        return _memory_store

    if resolved in {"auto", "gemini_vector"}:
        try:
            from .gemini_vector_store import GeminiVectorMemoryStore

            logger.info("[AtomicMemory] provider=gemini_vector")
            _memory_store = GeminiVectorMemoryStore(fallback_store=RedisMemoryStore())
        except Exception as e:
            logger.warning("[AtomicMemory] gemini_vector unavailable, fallback chain applies: %s", e)
            if resolved == "gemini_vector":
                _memory_store = RedisMemoryStore()
            else:
                # auto mode fallback order: redis -> noop
                _memory_store = RedisMemoryStore()
    elif resolved == "qmd":
        logger.info("[AtomicMemory] provider=qmd")
        _memory_store = QmdMemoryStore(fallback_store=RedisMemoryStore())
    elif resolved == "redis":
        logger.info("[AtomicMemory] provider=redis")
        _memory_store = RedisMemoryStore()
    else:
        logger.info("[AtomicMemory] provider=noop")
        _memory_store = NoopMemoryStore()

    _memory_provider = resolved
    return _memory_store


__all__ = [
    "MemoryHit",
    "MemoryStore",
    "format_memory_hits",
    "get_memory_store",
]
