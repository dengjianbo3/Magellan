from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "Orchestrator Agent"
    assert isinstance(data.get("version"), str)


def test_analysis_scenarios_available():
    response = client.get("/api/v2/analysis/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("scenarios"), list)
    assert any(s.get("id") == "early-stage-investment" for s in data["scenarios"])


def test_legacy_start_analysis_removed():
    response = client.post("/start_analysis", json={"ticker": "MSFT"})
    assert response.status_code == 404
