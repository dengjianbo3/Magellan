"""
In-process fallback memory store.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any, Dict, List

from .interface import MemoryHit, MemoryStore


class NoopMemoryStore(MemoryStore):
    """
    Lightweight in-memory store.

    Intended as a degraded fallback when external providers are unavailable.
    """

    def __init__(self, max_items_per_bucket: int = 200, ttl_seconds: int | None = None) -> None:
        self._max_items = max(20, int(max_items_per_bucket))
        self._ttl_seconds = int(
            ttl_seconds
            if ttl_seconds is not None
            else os.getenv("ATOMIC_MEMORY_TTL_SECONDS", str(30 * 24 * 3600))
        )
        self._lock = asyncio.Lock()
        self._agent_buckets: Dict[str, List[Dict[str, Any]]] = {}
        self._shared_buckets: Dict[str, List[Dict[str, Any]]] = {}

    def _prune_expired(self, bucket: List[Dict[str, Any]]) -> None:
        if self._ttl_seconds <= 0:
            return
        cutoff = time.time() - self._ttl_seconds
        bucket[:] = [item for item in bucket if float(item.get("ts", 0.0)) >= cutoff]

    def _agent_key(self, user_id: str, agent_id: str, collection: str) -> str:
        return f"u:{user_id}:a:{agent_id}:{collection}"

    def _shared_key(self, user_id: str) -> str:
        return f"u:{user_id}:shared:evidence"

    async def add_agent_memory(
        self,
        user_id: str,
        agent_id: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
        collection: str = "episodic",
    ) -> str:
        record_id = uuid.uuid4().hex
        payload = {
            "id": record_id,
            "content": (content or "").strip(),
            "metadata": dict(metadata or {}),
            "ts": time.time(),
            "collection": collection,
        }
        if not payload["content"]:
            return record_id

        key = self._agent_key(str(user_id), str(agent_id), str(collection))
        async with self._lock:
            bucket = self._agent_buckets.setdefault(key, [])
            self._prune_expired(bucket)
            bucket.append(payload)
            if len(bucket) > self._max_items:
                del bucket[:-self._max_items]
        return record_id

    async def query_agent_memory(
        self,
        user_id: str,
        agent_id: str,
        query: str,
        top_k: int = 3,
        collection: str = "episodic",
    ) -> List[MemoryHit]:
        key = self._agent_key(str(user_id), str(agent_id), str(collection))
        q = (query or "").strip().lower()
        if not q:
            return []
        async with self._lock:
            bucket = self._agent_buckets.setdefault(key, [])
            self._prune_expired(bucket)
            items = list(bucket)
        ranked = sorted(
            items,
            key=lambda row: self._score_text(q, row.get("content", "")),
            reverse=True,
        )
        hits: List[MemoryHit] = []
        for row in ranked[: max(1, top_k)]:
            score = self._score_text(q, row.get("content", ""))
            if score <= 0:
                continue
            hits.append(
                MemoryHit(
                    content=str(row.get("content", "")),
                    score=score,
                    metadata=dict(row.get("metadata") or {}),
                    collection=str(row.get("collection", collection)),
                )
            )
        return hits

    async def add_shared_evidence(
        self,
        user_id: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
    ) -> str:
        record_id = uuid.uuid4().hex
        payload = {
            "id": record_id,
            "content": (content or "").strip(),
            "metadata": dict(metadata or {}),
            "ts": time.time(),
            "collection": "shared:evidence",
        }
        if not payload["content"]:
            return record_id
        key = self._shared_key(str(user_id))
        async with self._lock:
            bucket = self._shared_buckets.setdefault(key, [])
            self._prune_expired(bucket)
            bucket.append(payload)
            if len(bucket) > self._max_items:
                del bucket[:-self._max_items]
        return record_id

    async def query_shared_evidence(
        self,
        user_id: str,
        query: str,
        top_k: int = 3,
    ) -> List[MemoryHit]:
        key = self._shared_key(str(user_id))
        q = (query or "").strip().lower()
        if not q:
            return []
        async with self._lock:
            bucket = self._shared_buckets.setdefault(key, [])
            self._prune_expired(bucket)
            items = list(bucket)
        ranked = sorted(
            items,
            key=lambda row: self._score_text(q, row.get("content", "")),
            reverse=True,
        )
        hits: List[MemoryHit] = []
        for row in ranked[: max(1, top_k)]:
            score = self._score_text(q, row.get("content", ""))
            if score <= 0:
                continue
            hits.append(
                MemoryHit(
                    content=str(row.get("content", "")),
                    score=score,
                    metadata=dict(row.get("metadata") or {}),
                    collection="shared:evidence",
                )
            )
        return hits

    async def health(self) -> Dict[str, Any]:
        return {
            "provider": "noop",
            "degraded": True,
            "reason": "in_process_fallback",
        }

    @staticmethod
    def _score_text(query: str, content: str) -> float:
        text = (content or "").lower()
        if not text:
            return 0.0
        if query in text:
            return 1.0
        query_tokens = {tok for tok in query.split() if tok}
        if not query_tokens:
            return 0.0
        overlap = sum(1 for tok in query_tokens if tok in text)
        return overlap / max(1, len(query_tokens))
