import asyncio

import pytest

from app.core.observability import metrics_snapshot as metrics_snapshot_module
from app.core.observability.metrics_snapshot import MetricsSnapshotCache


@pytest.mark.asyncio
async def test_metrics_snapshot_cache_reuses_payload_within_ttl(monkeypatch):
    calls = {"count": 0}

    def fake_generate_latest():
        calls["count"] += 1
        return f"metrics-{calls['count']}".encode("utf-8")

    monkeypatch.setattr(metrics_snapshot_module, "generate_latest", fake_generate_latest)

    cache = MetricsSnapshotCache(ttl_seconds=1.0)
    first = await cache.response()
    second = await cache.response()

    assert calls["count"] == 1
    assert first.body == b"metrics-1"
    assert second.body == b"metrics-1"


@pytest.mark.asyncio
async def test_metrics_snapshot_cache_refreshes_after_ttl(monkeypatch):
    calls = {"count": 0}

    def fake_generate_latest():
        calls["count"] += 1
        return f"metrics-{calls['count']}".encode("utf-8")

    monkeypatch.setattr(metrics_snapshot_module, "generate_latest", fake_generate_latest)

    cache = MetricsSnapshotCache(ttl_seconds=0.1)
    first = await cache.response()
    await asyncio.sleep(0.12)
    second = await cache.response()

    assert calls["count"] == 2
    assert first.body == b"metrics-1"
    assert second.body == b"metrics-2"
