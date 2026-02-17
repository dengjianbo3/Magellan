from fastapi.testclient import TestClient

from app.main import app
from app.api.routers import knowledge


client = TestClient(app)


class _DummyRAG:
    def __init__(self):
        self.calls = []

    def hybrid_search(self, *, query, top_k, use_reranking, filter_conditions):
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "use_reranking": use_reranking,
                "filter_conditions": filter_conditions,
            }
        )
        return [{"id": "1", "text": "doc", "metadata": {"category": "market"}, "score": 0.9}]


def test_search_and_hybrid_search_share_same_backend_path():
    rag = _DummyRAG()
    knowledge.set_rag_service(rag)

    search_resp = client.get("/api/knowledge/search?query=ai&limit=7&category=market")
    hybrid_resp = client.get("/api/knowledge/hybrid-search?query=ai&top_k=5&use_reranking=true&category=market")

    assert search_resp.status_code == 200
    assert hybrid_resp.status_code == 200

    assert len(rag.calls) == 2
    assert rag.calls[0]["top_k"] == 7
    assert rag.calls[0]["use_reranking"] is False
    assert rag.calls[1]["top_k"] == 5
    assert rag.calls[1]["use_reranking"] is True
