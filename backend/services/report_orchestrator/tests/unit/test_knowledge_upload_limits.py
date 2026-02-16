from fastapi.testclient import TestClient

from app.main import app
from app.api.routers import knowledge


client = TestClient(app)


class _DummyStore:
    def add_document(self, text, metadata):
        return "dummy"


def test_knowledge_upload_enforces_size_limit(monkeypatch):
    knowledge.set_vector_store(_DummyStore())
    monkeypatch.setattr(knowledge, "KNOWLEDGE_UPLOAD_MAX_MB", 1)

    payload = b"x" * (1024 * 1024 + 1)
    response = client.post(
        "/api/knowledge/upload",
        files={"file": ("notes.txt", payload, "text/plain")},
        data={"title": "notes"},
    )
    assert response.status_code == 413
