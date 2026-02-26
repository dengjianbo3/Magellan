"""
qmd-backed memory store (CLI adapter with graceful fallback).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .interface import MemoryHit, MemoryStore
from .noop_store import NoopMemoryStore

logger = logging.getLogger(__name__)


class QmdMemoryStore(MemoryStore):
    """Use qmd CLI as retrieval/index layer for agent memory."""

    def __init__(
        self,
        cli_path: Optional[str] = None,
        index_name: Optional[str] = None,
        memory_root: Optional[str] = None,
        cmd_timeout_seconds: int = 20,
        fallback_store: Optional[MemoryStore] = None,
    ) -> None:
        self.cli_path = cli_path or os.getenv("QMD_CLI_PATH", "qmd")
        self.index_name = index_name or os.getenv("QMD_INDEX_NAME", "magellan-memory")
        default_root = "/tmp/magellan_qmd_memory"
        self.memory_root = Path(memory_root or os.getenv("QMD_MEMORY_ROOT", default_root)).resolve()
        self.cmd_timeout_seconds = max(5, int(cmd_timeout_seconds))
        self._fallback = fallback_store or NoopMemoryStore()
        self._registered_collections: set[str] = set()
        self._degraded = False
        self.memory_root.mkdir(parents=True, exist_ok=True)

    async def add_agent_memory(
        self,
        user_id: str,
        agent_id: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
        collection: str = "episodic",
    ) -> str:
        text = (content or "").strip()
        if not text:
            return uuid.uuid4().hex

        raw_collection = f"u:{user_id}:a:{agent_id}:{collection}"
        try:
            collection_slug, collection_dir = await self._ensure_collection(raw_collection)
            record_id = uuid.uuid4().hex
            ts = datetime.now(timezone.utc).isoformat()
            payload = {
                "id": record_id,
                "user_id": str(user_id),
                "agent_id": str(agent_id),
                "collection": str(collection),
                "metadata": dict(metadata or {}),
                "timestamp": ts,
            }
            file_path = collection_dir / f"{ts.replace(':', '').replace('-', '')}_{record_id}.md"
            doc = self._render_markdown_doc(text=text, payload=payload)
            file_path.write_text(doc, encoding="utf-8")
            await self._qmd_update()
            self._degraded = False
            return record_id
        except Exception as e:
            logger.warning("[AtomicMemory] qmd add failed, fallback to noop: %s", e)
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
        raw_collection = f"u:{user_id}:a:{agent_id}:{collection}"
        try:
            collection_slug, _ = await self._ensure_collection(raw_collection)
            hits = await self._qmd_query(collection_slug, q, top_k=max(1, top_k))
            self._degraded = False
            return hits
        except Exception as e:
            logger.warning("[AtomicMemory] qmd query failed, fallback to noop: %s", e)
            self._degraded = True
            return await self._fallback.query_agent_memory(user_id, agent_id, q, top_k, collection)

    async def add_shared_evidence(
        self,
        user_id: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
    ) -> str:
        text = (content or "").strip()
        if not text:
            return uuid.uuid4().hex
        raw_collection = f"u:{user_id}:shared:evidence"
        try:
            collection_slug, collection_dir = await self._ensure_collection(raw_collection)
            record_id = uuid.uuid4().hex
            ts = datetime.now(timezone.utc).isoformat()
            payload = {
                "id": record_id,
                "user_id": str(user_id),
                "collection": "shared:evidence",
                "metadata": dict(metadata or {}),
                "timestamp": ts,
            }
            file_path = collection_dir / f"{ts.replace(':', '').replace('-', '')}_{record_id}.md"
            doc = self._render_markdown_doc(text=text, payload=payload)
            file_path.write_text(doc, encoding="utf-8")
            await self._qmd_update()
            self._degraded = False
            return record_id
        except Exception as e:
            logger.warning("[AtomicMemory] qmd shared-evidence add failed, fallback: %s", e)
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
        raw_collection = f"u:{user_id}:shared:evidence"
        try:
            collection_slug, _ = await self._ensure_collection(raw_collection)
            hits = await self._qmd_query(collection_slug, q, top_k=max(1, top_k))
            self._degraded = False
            return hits
        except Exception as e:
            logger.warning("[AtomicMemory] qmd shared-evidence query failed, fallback: %s", e)
            self._degraded = True
            return await self._fallback.query_shared_evidence(user_id, q, top_k)

    async def health(self) -> Dict[str, Any]:
        return {
            "provider": "qmd",
            "degraded": self._degraded,
            "index_name": self.index_name,
            "memory_root": str(self.memory_root),
            "cli_path": self.cli_path,
        }

    async def _ensure_collection(self, raw_collection: str) -> tuple[str, Path]:
        slug = self._collection_slug(raw_collection)
        directory = self.memory_root / slug
        directory.mkdir(parents=True, exist_ok=True)
        if slug in self._registered_collections:
            return slug, directory

        # Best effort: collection may already exist.
        result = await self._run_qmd(
            [
                "collection",
                "add",
                str(directory),
                "--name",
                slug,
            ],
            allow_failure=True,
        )
        if result["ok"]:
            self._registered_collections.add(slug)
            return slug, directory

        stderr = (result.get("stderr") or "").lower()
        stdout = (result.get("stdout") or "").lower()
        if "already exists" in stderr or "already exists" in stdout:
            self._registered_collections.add(slug)
            return slug, directory
        raise RuntimeError(f"qmd collection add failed: {result.get('stderr') or result.get('stdout')}")

    async def _qmd_update(self) -> None:
        result = await self._run_qmd(["update"], allow_failure=False)
        if not result["ok"]:
            raise RuntimeError(result.get("stderr") or result.get("stdout") or "qmd update failed")

    async def _qmd_query(self, collection_slug: str, query: str, top_k: int) -> List[MemoryHit]:
        result = await self._run_qmd(
            [
                "query",
                "--json",
                "--collection",
                collection_slug,
                "--limit",
                str(top_k),
                query,
            ],
            allow_failure=False,
        )
        if not result["ok"]:
            raise RuntimeError(result.get("stderr") or result.get("stdout") or "qmd query failed")

        payload = self._parse_json(result.get("stdout", ""))
        rows: List[Dict[str, Any]] = []
        if isinstance(payload, list):
            rows = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            if isinstance(payload.get("results"), list):
                rows = [item for item in payload["results"] if isinstance(item, dict)]
            elif isinstance(payload.get("items"), list):
                rows = [item for item in payload["items"] if isinstance(item, dict)]

        hits: List[MemoryHit] = []
        for row in rows[:top_k]:
            content = (
                str(row.get("snippet") or "")
                or str(row.get("content") or "")
                or str(row.get("text") or "")
            ).strip()
            if not content and row.get("path"):
                # Optional fallback for sparse JSON: try reading source file.
                try:
                    path = Path(str(row["path"]))
                    if path.exists():
                        content = path.read_text(encoding="utf-8")[:1800]
                except Exception:
                    content = ""
            if not content:
                continue
            score_val = row.get("score", 0.0)
            try:
                score = float(score_val)
            except Exception:
                score = 0.0
            metadata = {"path": row.get("path"), "title": row.get("title")}
            hits.append(
                MemoryHit(
                    content=content,
                    score=score,
                    metadata=metadata,
                    collection=collection_slug,
                )
            )
        return hits

    async def _run_qmd(self, args: List[str], allow_failure: bool) -> Dict[str, Any]:
        cmd = [self.cli_path, "--index", self.index_name] + args
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.memory_root),
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.cmd_timeout_seconds,
            )
        except Exception:
            proc.kill()
            await proc.communicate()
            raise

        stdout = (stdout_b or b"").decode("utf-8", errors="ignore").strip()
        stderr = (stderr_b or b"").decode("utf-8", errors="ignore").strip()
        ok = proc.returncode == 0
        if not ok and not allow_failure:
            logger.debug("[AtomicMemory:qmd] command failed: %s | stderr=%s", " ".join(cmd), stderr[:500])
        return {"ok": ok, "stdout": stdout, "stderr": stderr}

    @staticmethod
    def _render_markdown_doc(text: str, payload: Dict[str, Any]) -> str:
        metadata_json = json.dumps(payload, ensure_ascii=False)
        return (
            "---\n"
            f"id: {payload.get('id')}\n"
            f"user_id: {payload.get('user_id')}\n"
            f"agent_id: {payload.get('agent_id', '')}\n"
            f"collection: {payload.get('collection')}\n"
            f"timestamp: {payload.get('timestamp')}\n"
            "---\n\n"
            f"{text}\n\n"
            f"<!-- metadata: {metadata_json} -->\n"
        )

    @staticmethod
    def _parse_json(text: str) -> Any:
        stripped = (text or "").strip()
        if not stripped:
            return []
        try:
            return json.loads(stripped)
        except Exception:
            # Try extracting first JSON object/array from mixed output.
            m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", stripped)
            if not m:
                return []
            try:
                return json.loads(m.group(1))
            except Exception:
                return []

    @staticmethod
    def _collection_slug(raw: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9:_-]+", "_", (raw or "").strip())
        short = normalized[:80] if len(normalized) > 80 else normalized
        suffix = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
        return f"{short}_{suffix}".strip("_")
