# backend/services/llm_gateway/tests/test_main.py
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "LLM Gateway", "version": "5.0.0"}


def test_chat_handler_success():
    payload = {
        "history": [{"role": "user", "parts": ["Summarize this document."]}],
        "provider": "gemini",
    }

    with patch("app.main.call_gemini", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "This is a mock summary."
        response = client.post("/chat", json=payload)

    assert response.status_code == 200
    assert response.json() == {"content": "This is a mock summary."}
    mock_call.assert_awaited_once()


def test_chat_handler_api_error():
    payload = {
        "history": [{"role": "user", "parts": ["Test prompt"]}],
        "provider": "gemini",
    }

    with patch("app.main.call_gemini", new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = HTTPException(status_code=503, detail="Gemini unavailable")
        response = client.post("/chat", json=payload)

    assert response.status_code == 503
    assert response.json()["detail"] == "Gemini unavailable"
