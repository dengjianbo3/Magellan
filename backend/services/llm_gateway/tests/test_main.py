# backend/services/llm_gateway/tests/test_main.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the settings before importing the app
from app.core import config
config.settings.GOOGLE_API_KEY = "test-key"

from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_genai():
    with patch('google.genai.GenerativeModel') as mock_model:
        yield mock_model

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "LLM Gateway"}

def test_chat_handler_success(mock_genai):

    # Configure the mock to simulate a successful API call

    mock_chat = MagicMock()

    mock_chat.send_message_async = AsyncMock()

    mock_chat.send_message_async.return_value.text = "This is a mock summary."

    

    mock_model_instance = MagicMock()

    mock_model_instance.start_chat.return_value = mock_chat

    mock_genai.return_value = mock_model_instance



    # Define the request payload

    payload = {

        "model": "gemini-pro",

        "history": [

            {"role": "user", "parts": ["Summarize this document."]}

        ]

    }



    response = client.post("/chat", json=payload)



    assert response.status_code == 200

    data = response.json()

    assert data["role"] == "model"

    assert data["content"] == "This is a mock summary."



    # Verify that the genai library was called correctly

    mock_genai.assert_called_with(model_name="gemini-pro")

    mock_model_instance.start_chat.assert_called_once()

def test_chat_handler_api_error(mock_genai):
    # Configure the mock to simulate an API error
    mock_genai.side_effect = Exception("API connection failed")

    payload = {"history": [{"role": "user", "parts": ["Test prompt"]}]}
    response = client.post("/chat", json=payload)

    assert response.status_code == 500
    assert "API connection failed" in response.json()["detail"]
