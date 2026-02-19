from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "External Data Service"}


def test_get_company_info_requires_query():
    response = client.post("/get_company_info", json={})
    assert response.status_code == 400
    assert "company_name" in response.json()["detail"]


def test_get_company_info_returns_501_when_mock_disabled():
    response = client.post("/get_company_info", json={"ticker": "MSFT"})
    assert response.status_code == 501
    assert "External data provider is not configured" in response.json()["detail"]


def test_get_company_info_mock_found(monkeypatch):
    monkeypatch.setattr("app.main.ALLOW_MOCK_EXTERNAL_DATA", True)
    response = client.post("/get_company_info", json={"ticker": "Apple"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "found"
    assert "苹果电脑贸易" in data["data"]["company_name"]


def test_get_company_info_mock_not_found(monkeypatch):
    monkeypatch.setattr("app.main.ALLOW_MOCK_EXTERNAL_DATA", True)
    response = client.post("/get_company_info", json={"ticker": "MSFT"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_found"
