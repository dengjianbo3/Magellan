# backend/services/pdf_parser/tests/test_main.py
import pytest
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import patch, mock_open, MagicMock

# Add the app directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "PDF Parser Service"}

@patch('app.main.os.path.exists', return_value=True)
@patch('app.main.fitz.open')
def test_parse_pdf_success(mock_fitz_open, mock_path_exists):
    # Mock the PDF document and its pages
    mock_page = MagicMock()
    mock_page.get_text.return_value = "This is page text. "
    mock_doc = MagicMock()
    mock_doc.__enter__.return_value = [mock_page, mock_page] # Simulate a 2-page doc
    mock_fitz_open.return_value = mock_doc

    response = client.post("/parse_pdf", json={"file_id": "test.pdf"})

    assert response.status_code == 200
    data = response.json()
    assert data["file_id"] == "test.pdf"
    assert data["extracted_text"] == "This is page text. This is page text. "
    mock_path_exists.assert_called_once()
    mock_fitz_open.assert_called_once()

def test_parse_pdf_not_found():
    response = client.post("/parse_pdf", json={"file_id": "nonexistent.pdf"})
    assert response.status_code == 404
    assert "File not found" in response.json()["detail"]
