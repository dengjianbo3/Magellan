import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.routers import analysis
from app.core.auth import CurrentUser


class _FakeSessionStore:
    def __init__(self, session_data):
        self._session_data = session_data
        self.closed = False

    def save_session(self, session_id, context, ttl_days=30):
        self._session_data = context
        return True

    def get_session(self, session_id, user_id=None):
        if not self._session_data:
            return None
        if self._session_data.get("session_id") != session_id:
            return None
        owner = self._session_data.get("user_id") or (self._session_data.get("request") or {}).get("user_id")
        if user_id is not None and str(owner or "") != str(user_id):
            return None
        return self._session_data

    def close(self):
        self.closed = True


def _build_request_payload():
    return {
        "project_name": "UnitTest Analysis",
        "scenario": "early-stage-investment",
        "target": {"company_name": "ACME", "stage": "seed"},
        "config": {"depth": "quick", "language": "zh"},
        "user_id": "u_test",
    }


@pytest.mark.asyncio
async def test_get_status_returns_real_session_data(monkeypatch):
    session_data = {
        "session_id": "early_test_001",
        "scenario": "early-stage-investment",
        "user_id": "u_test",
        "status": "running",
        "started_at": "2026-02-16T10:00:00",
        "updated_at": "2026-02-16T10:01:00",
        "workflow": [
            {"id": "1", "name": "step1", "status": "success", "progress": 100},
            {"id": "2", "name": "step2", "status": "running", "progress": 60},
        ],
    }
    fake_store = _FakeSessionStore(session_data)
    monkeypatch.setattr(analysis, "_safe_session_store", lambda: fake_store)

    result = await analysis.get_analysis_status_v2(
        "early_test_001",
        current_user=CurrentUser(id="u_test"),
    )

    assert result["session_id"] == "early_test_001"
    assert result["status"] == "running"
    assert result["progress"] == 80
    assert result["current_step"]["id"] == "2"
    assert fake_store.closed is True


@pytest.mark.asyncio
async def test_get_status_returns_404_when_missing(monkeypatch):
    fake_store = _FakeSessionStore(None)
    monkeypatch.setattr(analysis, "_safe_session_store", lambda: fake_store)

    with pytest.raises(HTTPException) as exc_info:
        await analysis.get_analysis_status_v2(
            "missing_session",
            current_user=CurrentUser(id="u_test"),
        )

    assert exc_info.value.status_code == 404
    assert fake_store.closed is True


def test_start_analysis_builds_ws_url_from_forwarded_headers():
    app = FastAPI()
    app.include_router(analysis.router, prefix="/api/v2/analysis")
    client = TestClient(app)
    fake_store = _FakeSessionStore(None)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(analysis, "_safe_session_store", lambda: fake_store)
        resp = client.post(
            "/api/v2/analysis/start",
            json=_build_request_payload(),
            headers={
                "host": "example.test:443",
                "x-forwarded-proto": "https",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ws_url"].startswith("wss://example.test:443/ws/v2/analysis/")
    assert data["session_id"] in data["ws_url"]
    assert fake_store.closed is True


def test_start_analysis_normalizes_public_ws_base_url_https():
    app = FastAPI()
    app.include_router(analysis.router, prefix="/api/v2/analysis")
    client = TestClient(app)
    fake_store = _FakeSessionStore(None)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(analysis, "_safe_session_store", lambda: fake_store)
        mp.setenv("PUBLIC_WS_BASE_URL", "https://api.magellan.example")
        resp = client.post("/api/v2/analysis/start", json=_build_request_payload())

    assert resp.status_code == 200
    data = resp.json()
    assert data["ws_url"].startswith("wss://api.magellan.example/ws/v2/analysis/")
    assert fake_store.closed is True


def test_start_analysis_handles_multi_value_forwarded_proto():
    app = FastAPI()
    app.include_router(analysis.router, prefix="/api/v2/analysis")
    client = TestClient(app)
    fake_store = _FakeSessionStore(None)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(analysis, "_safe_session_store", lambda: fake_store)
        mp.delenv("PUBLIC_WS_BASE_URL", raising=False)
        resp = client.post(
            "/api/v2/analysis/start",
            json=_build_request_payload(),
            headers={
                "host": "proxy.example",
                "x-forwarded-proto": "https,http",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ws_url"].startswith("wss://proxy.example/ws/v2/analysis/")
    assert fake_store.closed is True


def test_start_analysis_supports_host_only_public_ws_base():
    app = FastAPI()
    app.include_router(analysis.router, prefix="/api/v2/analysis")
    client = TestClient(app)
    fake_store = _FakeSessionStore(None)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(analysis, "_safe_session_store", lambda: fake_store)
        mp.setenv("PUBLIC_WS_BASE_URL", "api.magellan.example:8443")
        resp = client.post(
            "/api/v2/analysis/start",
            json=_build_request_payload(),
            headers={"x-forwarded-proto": "https"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ws_url"].startswith("wss://api.magellan.example:8443/ws/v2/analysis/")
    assert fake_store.closed is True


def test_scenarios_mark_experimental_as_coming_soon_by_default():
    app = FastAPI()
    app.include_router(analysis.router, prefix="/api/v2/analysis")
    client = TestClient(app)

    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("ANALYSIS_ENABLE_EXPERIMENTAL_SCENARIOS", raising=False)
        resp = client.get("/api/v2/analysis/scenarios")

    assert resp.status_code == 200
    data = resp.json()
    scenarios = {s["id"]: s for s in data["scenarios"]}
    assert scenarios["early-stage-investment"]["status"] == "active"
    assert scenarios["growth-investment"]["status"] == "coming_soon"
    assert scenarios["public-market-investment"]["status"] == "coming_soon"
    assert scenarios["alternative-investment"]["status"] == "coming_soon"
    assert scenarios["industry-research"]["status"] == "coming_soon"


def test_scenarios_enable_experimental_when_env_is_true():
    app = FastAPI()
    app.include_router(analysis.router, prefix="/api/v2/analysis")
    client = TestClient(app)

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("ANALYSIS_ENABLE_EXPERIMENTAL_SCENARIOS", "true")
        resp = client.get("/api/v2/analysis/scenarios")

    assert resp.status_code == 200
    data = resp.json()
    scenarios = {s["id"]: s for s in data["scenarios"]}
    assert scenarios["early-stage-investment"]["status"] == "active"
    assert scenarios["growth-investment"]["status"] == "active"
    assert scenarios["public-market-investment"]["status"] == "active"
    assert scenarios["alternative-investment"]["status"] == "active"
    assert scenarios["industry-research"]["status"] == "active"
