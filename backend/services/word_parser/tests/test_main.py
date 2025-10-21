# backend/services/word_parser/tests/test_main.py
import pytest
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import patch, MagicMock

# Add the app directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Word Parser Service"}

@patch('app.main.os.path.exists', return_value=True)
@patch('app.main.Document')
def test_parse_word_success(mock_document, mock_path_exists):
    # Mock the Document object and its paragraphs
    mock_para1 = MagicMock()
    mock_para1.text = "This is the first paragraph."
    mock_para2 = MagicMock()
    mock_para2.text = "This is the second paragraph."
    
    mock_doc_instance = MagicMock()
    mock_doc_instance.paragraphs = [mock_para1, mock_para2]
    mock_document.return_value = mock_doc_instance

    response = client.post("/parse_word", json={"file_id": "test.docx"})

    assert response.status_code == 200
    data = response.json()
    assert data["file_id"] == "test.docx"
    assert "first paragraph" in data["extracted_text"]
    assert "second paragraph" in data["extracted_text"]
    mock_document.assert_called_once()

def test_parse_word_not_found():
    response = client.post("/parse_word", json={"file_id": "nonexistent.docx"})
    assert response.status_code == 404
    assert "File not found" in response.json()["detail"]
