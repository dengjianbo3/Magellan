from fastapi.testclient import TestClient

from app.main import app
from app.api.routers import files_multipart


client = TestClient(app)


def test_upload_bp_v2_rejects_unsupported_extension():
    response = client.post(
        "/api/v2/upload/bp",
        files={"file": ("payload.exe", b"abc", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_bp_v2_enforces_hard_cap(monkeypatch):
    monkeypatch.setattr(files_multipart, "MAX_UPLOAD_MB_HARD_CAP", 1)
    payload = b"x" * (1024 * 1024 + 1)

    response = client.post(
        "/api/v2/upload/bp?max_size_mb=999",
        files={"file": ("doc.pdf", payload, "application/pdf")},
    )
    assert response.status_code == 413


def test_upload_bp_v2_forwards_to_file_service(monkeypatch):
    async def _fake_forward_to_file_service(*, filename, content_type, temp_path):
        assert filename == "doc.pdf"
        assert content_type == "application/pdf"
        assert temp_path
        return {"file_id": "file_123"}

    monkeypatch.setattr(files_multipart, "_forward_to_file_service", _fake_forward_to_file_service)

    response = client.post(
        "/api/v2/upload/bp",
        files={"file": ("doc.pdf", b"%PDF-1.4\nhello", "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["file_id"] == "file_123"
