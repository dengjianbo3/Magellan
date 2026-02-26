"""
Prometheus exposition snapshot cache.

Goal:
- Reduce `/metrics` scrape timeout risk under high load.
- Avoid recomputing full exposition for every scrape request.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


class MetricsSnapshotCache:
    def __init__(self, ttl_seconds: float = 2.0):
        self._ttl_seconds = max(0.1, float(ttl_seconds))
        self._payload: bytes = b""
        self._ts: float = 0.0
        self._lock = asyncio.Lock()

    def _is_fresh(self, now: float) -> bool:
        return bool(self._payload) and (now - self._ts) < self._ttl_seconds

    async def response(self) -> Response:
        now = time.monotonic()
        if self._is_fresh(now):
            return Response(content=self._payload, media_type=CONTENT_TYPE_LATEST)

        async with self._lock:
            now = time.monotonic()
            if self._is_fresh(now):
                return Response(content=self._payload, media_type=CONTENT_TYPE_LATEST)
            self._payload = await asyncio.to_thread(generate_latest)
            self._ts = now

        return Response(content=self._payload, media_type=CONTENT_TYPE_LATEST)
