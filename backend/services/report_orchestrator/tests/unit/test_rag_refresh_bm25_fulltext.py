from app.services.rag_service import RAGService


class _FakeVectorStore:
    def __init__(self):
        self.kwargs = None

    def list_documents(self, **kwargs):
        self.kwargs = kwargs
        return [{"id": "d1", "text": "full text"}]


def test_refresh_bm25_uses_full_text_documents():
    vector_store = _FakeVectorStore()
    rag = RAGService(vector_store_service=vector_store)

    captured = {}

    def _fake_build_index(documents):
        captured["documents"] = documents

    rag._build_bm25_index = _fake_build_index

    ok = rag.refresh_bm25_index()

    assert ok is True
    assert vector_store.kwargs == {"limit": 10000, "include_full_text": True}
    assert captured["documents"] == [{"id": "d1", "text": "full text"}]
