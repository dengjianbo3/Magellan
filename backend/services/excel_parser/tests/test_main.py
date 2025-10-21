# backend/services/excel_parser/tests/test_main.py
import pytest
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import patch, MagicMock
import pandas as pd

# Add the app directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Excel Parser Service"}

@patch('app.main.os.path.exists', return_value=True)
@patch('app.main.pd.ExcelFile')
@patch('app.main.pd.read_excel')
def test_parse_excel_success(mock_read_excel, mock_excel_file, mock_path_exists):
    # Mock the ExcelFile object and its sheet_names
    mock_xls = MagicMock()
    mock_xls.sheet_names = ['Sheet1', 'Sheet2']
    mock_excel_file.return_value = mock_xls

    # Mock the read_excel function to return a sample DataFrame
    mock_df = pd.DataFrame({'col1': [1, 2], 'col2': ['A', 'B']})
    mock_read_excel.return_value = mock_df

    response = client.post("/parse_excel", json={"file_id": "test.xlsx"})

    assert response.status_code == 200
    data = response.json()
    assert data["file_id"] == "test.xlsx"
    assert "Sheet1" in data["extracted_data"]
    assert "Sheet2" in data["extracted_data"]
    assert data["extracted_data"]["Sheet1"][0]["col1"] == 1
    assert mock_read_excel.call_count == 2

def test_parse_excel_not_found():
    response = client.post("/parse_excel", json={"file_id": "nonexistent.xlsx"})
    assert response.status_code == 404
    assert "File not found" in response.json()["detail"]
