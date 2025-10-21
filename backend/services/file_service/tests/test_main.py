# backend/services/file_service/tests/test_main.py
import pytest
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import patch, mock_open

# Add the app directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "File Service"}

@patch('app.main.os.makedirs')
@patch('app.main.shutil.copyfileobj')
@patch('builtins.open', new_callable=mock_open)
@patch('app.main.uuid.uuid4', return_value='mock-uuid')
def test_upload_file_success(mock_uuid, mock_file, mock_copy, mock_makedirs):
    file_content = b"file content"
    files = {'file': ('test.txt', file_content, 'text/plain')}
    
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["file_id"] == "mock-uuid.txt"
    assert data["original_filename"] == "test.txt"
    
    mock_file.assert_called_with('/var/uploads/mock-uuid.txt', 'wb+')
    mock_copy.assert_called_once()
