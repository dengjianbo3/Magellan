# backend/services/report_orchestrator/tests/test_main.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Orchestrator Agent"}

# This is the standard and correct way to patch an async context manager
@patch('app.main.httpx.AsyncClient')
def test_start_analysis_success(MockAsyncClient):
    # 1. Configure the mock for the 'async with' block
    mock_client_instance = MockAsyncClient.return_value.__aenter__.return_value
    
    # 2. Configure the async methods that will be called on the instance
    mock_client_instance.get = AsyncMock()
    mock_client_instance.post = AsyncMock()

    # 3. Set the return values for the awaited calls
    mock_client_instance.get.return_value.text = "mock-uuid-123"
    mock_client_instance.post.return_value.json.return_value = {
        "status": "single_result",
        "data": {"company_name": "Microsoft"}
    }
    # This mock is needed because the code calls .raise_for_status()
    mock_client_instance.post.return_value.raise_for_status = MagicMock()

    # 4. Run the test
    response = client.post("/start_analysis", json={"ticker": "MSFT"})

    # 5. Assert the results
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["steps"][0]["status"] == "success"
    assert "Microsoft" in data["steps"][0]["result"]

@patch('app.main.httpx.AsyncClient')
def test_start_analysis_hitl(MockAsyncClient):
    mock_client_instance = MockAsyncClient.return_value.__aenter__.return_value
    mock_client_instance.get = AsyncMock()
    mock_client_instance.post = AsyncMock()

    mock_client_instance.get.return_value.text = "mock-uuid-456"
    mock_client_instance.post.return_value.json.return_value = {
        "status": "multiple_options",
        "data": [{"ticker": "AAPL", "name": "Apple Inc."}]
    }
    mock_client_instance.post.return_value.raise_for_status = MagicMock()

    response = client.post("/start_analysis", json={"ticker": "Apple"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "hitl_required"
    assert data["steps"][0]["status"] == "paused"
    assert data["steps"][0]["options"][0]["ticker"] == "AAPL"
