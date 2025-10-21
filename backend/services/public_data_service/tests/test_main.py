# backend/services/public_data_service/tests/test_main.py
import pytest
import httpx
from fastapi.testclient import TestClient
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Public Data Service"}

def test_get_valid_ticker():
    response = client.post("/get_company_info", json={"ticker": "MSFT"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "single_result"
    assert data["data"]["ticker"] == "MSFT"
    assert "Microsoft" in data["data"]["company_name"]

def test_get_invalid_ticker():
    response = client.post("/get_company_info", json={"ticker": "INVALIDTICKERXYZ"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_found"

def test_get_ambiguous_ticker():
    response = client.post("/get_company_info", json={"ticker": "Apple"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "multiple_options"
    assert len(data["data"]) == 2
    assert data["data"][0]["ticker"] == "AAPL"
