"""
Gemini-embedding + Qdrant backed memory store.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)

from .interface import MemoryHit, MemoryStore
from .redis_store import RedisMemoryStore

logger = logging.getLogger(__name__)


class GeminiVectorMemoryStore(MemoryStore):
    """Semantic memory powered by Gemini embeddings and Qdrant."""

    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        collection_name: Optional[str] = None,
        fallback_store: Optional[MemoryStore] = None,
    ) -> None:
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://qdrant:6333")
        self.collection_name = collection_name or os.getenv(
            "ATOMIC_MEMORY_VECTOR_COLLECTION", "atomic_memory"
        )
        self.embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
        self.vector_size = int(os.getenv("GEMINI_EMBEDDING_DIMENSION", "768"))
        self.document_task_type = os.getenv("GEMINI_EMBEDDING_TASK_DOCUMENT", "RETRIEVAL_DOCUMENT")
        self.query_task_type = os.getenv("GEMINI_EMBEDDING_TASK_QUERY", "RETRIEVAL_QUERY")
        self.auto_recreate_on_dim_mismatch = (
            os.getenv("QDRANT_AUTO_RECREATE_COLLECTION", "true").lower() == "true"
        )
        self.ttl_seconds = max(0, int(os.getenv("ATOMIC_MEMORY_TTL_SECONDS", str(30 * 24 * 3600))))
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for gemini_vector memory provider")

        self.client = QdrantClient(url=self.qdrant_url)
        self.genai_client = genai.Client(api_key=api_key)
        self._fallback = fallback_store or RedisMemoryStore()
        self._degraded = False
        self._collection_ready = False

    async def add_agent_memory(
        self,
        user_id: str,
        agent_id: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
        collection: str = "episodic",
    ) -> str:
        text = (content or "").strip()
        record_id = uuid.uuid4().hex
        if not text:
            return record_id
        payload = {
            "memory_id": record_id,
            "user_id": str(user_id),
            "agent_id": str(agent_id),
            "collection": str(collection),
            "content": text,
            "metadata": dict(metadata or {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ts_epoch": int(datetime.now(timezone.utc).timestamp()),
        }
        try:
            await self._ensure_collection()
            vector = await self._embed_text(text, task_type=self.document_task_type)
            point = PointStruct(id=record_id, vector=vector, payload=payload)
            await asyncio.to_thread(
                self.client.upsert,
                collection_name=self.collection_name,
                points=[point],
            )
            self._degraded = False
            return record_id
        except Exception as e:
            logger.warning("[AtomicMemory] gemini_vector add failed, fallback: %s", e)
            self._degraded = True
            return await self._fallback.add_agent_memory(user_id, agent_id, text, metadata, collection)

    async def query_agent_memory(
        self,
        user_id: str,
        agent_id: str,
        query: str,
        top_k: int = 3,
        collection: str = "episodic",
    ) -> List[MemoryHit]:
        q = (query or "").strip()
        if not q:
            return []
        try:
            await self._ensure_collection()
            vector = await self._embed_text(q, task_type=self.query_task_type)
            must_conditions = [
                FieldCondition(key="user_id", match=MatchValue(value=str(user_id))),
                FieldCondition(key="agent_id", match=MatchValue(value=str(agent_id))),
                FieldCondition(key="collection", match=MatchValue(value=str(collection))),
            ]
            if self.ttl_seconds > 0:
                cutoff = int(datetime.now(timezone.utc).timestamp()) - self.ttl_seconds
                must_conditions.append(FieldCondition(key="ts_epoch", range=Range(gte=cutoff)))
            q_filter = Filter(must=must_conditions)
            results = await asyncio.to_thread(
                self._query_points_sync,
                vector,
                q_filter,
                max(1, top_k),
                float(os.getenv("ATOMIC_MEMORY_SCORE_THRESHOLD", "0.25")),
            )
            self._degraded = False
            hits: List[MemoryHit] = []
            for row in results or []:
                payload = self._row_payload(row)
                content = str(payload.get("content", "")).strip()
                if not content:
                    continue
                hits.append(
                    MemoryHit(
                        content=content,
                        score=self._row_score(row),
                        metadata=dict(payload.get("metadata") or {}),
                        collection=str(payload.get("collection", collection)),
                    )
                )
            return hits
        except Exception as e:
            logger.warning("[AtomicMemory] gemini_vector query failed, fallback: %s", e)
            self._degraded = True
            return await self._fallback.query_agent_memory(user_id, agent_id, q, top_k, collection)

    async def add_shared_evidence(
        self,
        user_id: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
    ) -> str:
        text = (content or "").strip()
        record_id = uuid.uuid4().hex
        if not text:
            return record_id
        payload = {
            "memory_id": record_id,
            "user_id": str(user_id),
            "agent_id": "__shared__",
            "collection": "shared:evidence",
            "content": text,
            "metadata": dict(metadata or {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ts_epoch": int(datetime.now(timezone.utc).timestamp()),
        }
        try:
            await self._ensure_collection()
            vector = await self._embed_text(text, task_type=self.document_task_type)
            point = PointStruct(id=record_id, vector=vector, payload=payload)
            await asyncio.to_thread(
                self.client.upsert,
                collection_name=self.collection_name,
                points=[point],
            )
            self._degraded = False
            return record_id
        except Exception as e:
            logger.warning("[AtomicMemory] gemini_vector add shared evidence failed, fallback: %s", e)
            self._degraded = True
            return await self._fallback.add_shared_evidence(user_id, text, metadata)

    async def query_shared_evidence(
        self,
        user_id: str,
        query: str,
        top_k: int = 3,
    ) -> List[MemoryHit]:
        q = (query or "").strip()
        if not q:
            return []
        try:
            await self._ensure_collection()
            vector = await self._embed_text(q, task_type=self.query_task_type)
            must_conditions = [
                FieldCondition(key="user_id", match=MatchValue(value=str(user_id))),
                FieldCondition(key="collection", match=MatchValue(value="shared:evidence")),
            ]
            if self.ttl_seconds > 0:
                cutoff = int(datetime.now(timezone.utc).timestamp()) - self.ttl_seconds
                must_conditions.append(FieldCondition(key="ts_epoch", range=Range(gte=cutoff)))
            q_filter = Filter(must=must_conditions)
            results = await asyncio.to_thread(
                self._query_points_sync,
                vector,
                q_filter,
                max(1, top_k),
                float(os.getenv("ATOMIC_MEMORY_SCORE_THRESHOLD", "0.25")),
            )
            self._degraded = False
            hits: List[MemoryHit] = []
            for row in results or []:
                payload = self._row_payload(row)
                content = str(payload.get("content", "")).strip()
                if not content:
                    continue
                hits.append(
                    MemoryHit(
                        content=content,
                        score=self._row_score(row),
                        metadata=dict(payload.get("metadata") or {}),
                        collection="shared:evidence",
                    )
                )
            return hits
        except Exception as e:
            logger.warning("[AtomicMemory] gemini_vector query shared evidence failed, fallback: %s", e)
            self._degraded = True
            return await self._fallback.query_shared_evidence(user_id, q, top_k)

    async def health(self) -> Dict[str, Any]:
        return {
            "provider": "gemini_vector",
            "degraded": self._degraded,
            "collection_name": self.collection_name,
            "qdrant_url": self.qdrant_url,
            "embedding_model": self.embedding_model,
        }

    async def _ensure_collection(self) -> None:
        if self._collection_ready:
            return
        await asyncio.to_thread(self._ensure_collection_sync)
        self._collection_ready = True

    def _ensure_collection_sync(self) -> None:
        collections = self.client.get_collections().collections
        names = [c.name for c in collections]
        if self.collection_name not in names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )
            return

        info = self.client.get_collection(collection_name=self.collection_name)
        existing_size = self._extract_vector_size(info)
        if existing_size is None or existing_size == self.vector_size:
            return

        if not self.auto_recreate_on_dim_mismatch:
            raise RuntimeError(
                f"Collection '{self.collection_name}' dim mismatch: "
                f"existing={existing_size}, expected={self.vector_size}"
            )
        logger.warning(
            "[AtomicMemory] Recreating collection '%s' due to dim mismatch existing=%s expected=%s",
            self.collection_name,
            existing_size,
            self.vector_size,
        )
        self.client.delete_collection(collection_name=self.collection_name)
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
        )

    @staticmethod
    def _extract_vector_size(collection_info: Any) -> Optional[int]:
        try:
            vectors_cfg = collection_info.config.params.vectors
            if hasattr(vectors_cfg, "size"):
                return int(vectors_cfg.size)
            if isinstance(vectors_cfg, dict):
                for _, cfg in vectors_cfg.items():
                    if hasattr(cfg, "size"):
                        return int(cfg.size)
            return None
        except Exception:
            return None

    async def _embed_text(self, text: str, task_type: str) -> List[float]:
        return await asyncio.to_thread(self._embed_text_sync, text, task_type)

    def _embed_text_sync(self, text: str, task_type: str) -> List[float]:
        cleaned = text if text and text.strip() else " "
        try:
            config = types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.vector_size,
            )
            response = self.genai_client.models.embed_content(
                model=self.embedding_model,
                contents=[cleaned],
                config=config,
            )
        except TypeError:
            config = types.EmbedContentConfig(task_type=task_type)
            response = self.genai_client.models.embed_content(
                model=self.embedding_model,
                contents=[cleaned],
                config=config,
            )

        embedding_items = getattr(response, "embeddings", None) or []
        if not embedding_items:
            single = getattr(response, "embedding", None)
            if single is not None:
                embedding_items = [single]
        if not embedding_items:
            raise RuntimeError("Gemini embedding response is empty")
        raw = list(embedding_items[0].values)
        fitted = self._fit_dimension(raw)
        return self._normalize_vector(fitted)

    def _fit_dimension(self, values: List[float]) -> List[float]:
        if len(values) == self.vector_size:
            return values
        if len(values) > self.vector_size:
            return values[: self.vector_size]
        return values + [0.0] * (self.vector_size - len(values))

    @staticmethod
    def _normalize_vector(values: List[float]) -> List[float]:
        norm = math.sqrt(sum(v * v for v in values))
        if norm <= 0:
            return values
        return [v / norm for v in values]

    def _query_points_sync(
        self,
        vector: List[float],
        q_filter: Filter,
        limit: int,
        score_threshold: float,
    ) -> List[Any]:
        """Qdrant query adapter compatible with old/new client APIs."""
        if hasattr(self.client, "query_points"):
            try:
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=vector,
                    query_filter=q_filter,
                    limit=limit,
                    score_threshold=score_threshold,
                )
            except TypeError:
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=vector,
                    filter=q_filter,
                    limit=limit,
                    score_threshold=score_threshold,
                )
            return self._extract_query_rows(response)

        if hasattr(self.client, "search"):
            return self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                query_filter=q_filter,
                limit=limit,
                score_threshold=score_threshold,
            )

        raise RuntimeError("Qdrant client does not support query_points/search APIs")

    @staticmethod
    def _extract_query_rows(response: Any) -> List[Any]:
        if response is None:
            return []
        if isinstance(response, list):
            return response
        points = getattr(response, "points", None)
        if points is not None:
            return list(points)
        result = getattr(response, "result", None)
        if result is None:
            return []
        if isinstance(result, list):
            return result
        result_points = getattr(result, "points", None)
        if result_points is not None:
            return list(result_points)
        return []

    @staticmethod
    def _row_payload(row: Any) -> Dict[str, Any]:
        if isinstance(row, dict):
            return dict(row.get("payload") or {})
        return dict(getattr(row, "payload", None) or {})

    @staticmethod
    def _row_score(row: Any) -> float:
        if isinstance(row, dict):
            return float(row.get("score", 0.0) or 0.0)
        return float(getattr(row, "score", 0.0) or 0.0)
