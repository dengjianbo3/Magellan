import pytest
from fastapi.testclient import TestClient

from app.main import app, db, preferences_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_in_memory_stores():
    db.clear()
    preferences_db.clear()
    yield
    db.clear()
    preferences_db.clear()


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "User Service"}


def test_user_persona_roundtrip():
    payload = {
        "user_id": "u-smoke-1",
        "investment_style": "Value",
        "report_preference": "Deep Dive",
        "risk_tolerance": "Medium",
    }

    create_resp = client.post("/users/u-smoke-1", json=payload)
    assert create_resp.status_code == 200
    assert create_resp.json()["user_id"] == "u-smoke-1"

    get_resp = client.get("/users/u-smoke-1")
    assert get_resp.status_code == 200
    assert get_resp.json()["investment_style"] == "Value"


def test_user_persona_returns_default_when_missing():
    response = client.get("/users/not-exist")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "not-exist"
    assert body["investment_style"] == "Balanced"
    assert body["risk_tolerance"] == "Medium"


def test_user_persona_rejects_path_payload_mismatch():
    response = client.post(
        "/users/path-user",
        json={
            "user_id": "payload-user",
            "investment_style": "Growth",
            "report_preference": "Executive Summary",
            "risk_tolerance": "High",
        },
    )
    assert response.status_code == 400
    assert "does not match" in response.json()["detail"]


def test_preferences_crud_flow():
    user_id = "inst-smoke-1"

    create_resp = client.post(
        "/api/v1/preferences",
        json={
            "user_id": user_id,
            "investment_thesis": ["AI"],
            "preferred_stages": ["A"],
            "focus_industries": ["企业软件"],
            "excluded_industries": [],
            "geography_preference": ["北京"],
            "investment_range": {"min_amount": 1000, "max_amount": 5000, "currency": "CNY"},
            "min_team_size": 5,
            "require_revenue": False,
            "require_product": True,
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["success"] is True

    get_resp = client.get(f"/api/v1/preferences/{user_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["success"] is True
    assert get_resp.json()["preference"]["user_id"] == user_id

    update_resp = client.put(
        f"/api/v1/preferences/{user_id}",
        json={"focus_industries": ["人工智能", "企业软件"], "require_revenue": True},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["success"] is True
    assert update_resp.json()["preference"]["require_revenue"] is True

    delete_resp = client.delete(f"/api/v1/preferences/{user_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["success"] is True

    get_after_delete_resp = client.get(f"/api/v1/preferences/{user_id}")
    assert get_after_delete_resp.status_code == 200
    assert get_after_delete_resp.json()["success"] is False
