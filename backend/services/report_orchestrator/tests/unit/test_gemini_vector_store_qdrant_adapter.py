import sys
import types as py_types


if "google" not in sys.modules:
    google_mod = py_types.ModuleType("google")
    genai_mod = py_types.ModuleType("google.genai")
    genai_mod.types = py_types.SimpleNamespace(EmbedContentConfig=object)
    genai_mod.Client = object
    google_mod.genai = genai_mod
    sys.modules["google"] = google_mod
    sys.modules["google.genai"] = genai_mod

if "qdrant_client" not in sys.modules:
    qdrant_mod = py_types.ModuleType("qdrant_client")
    models_mod = py_types.ModuleType("qdrant_client.models")

    class _Dummy:
        def __init__(self, *args, **kwargs):
            pass

    qdrant_mod.QdrantClient = _Dummy
    models_mod.Distance = _Dummy
    models_mod.FieldCondition = _Dummy
    models_mod.Filter = _Dummy
    models_mod.MatchValue = _Dummy
    models_mod.PointStruct = _Dummy
    models_mod.Range = _Dummy
    models_mod.VectorParams = _Dummy

    sys.modules["qdrant_client"] = qdrant_mod
    sys.modules["qdrant_client.models"] = models_mod


from app.core.memory.gemini_vector_store import GeminiVectorMemoryStore


class _Row:
    def __init__(self, payload=None, score=0.0):
        self.payload = payload or {}
        self.score = score


class _PointsResponse:
    def __init__(self, points):
        self.points = points


def _build_store_with_client(client):
    store = GeminiVectorMemoryStore.__new__(GeminiVectorMemoryStore)
    store.client = client
    store.collection_name = "atomic_memory"
    return store


def test_qdrant_adapter_uses_query_points_when_available():
    row = _Row(payload={"content": "hello"}, score=0.88)

    class _Client:
        def query_points(self, **kwargs):
            assert kwargs["collection_name"] == "atomic_memory"
            assert "query" in kwargs
            return _PointsResponse([row])

    store = _build_store_with_client(_Client())
    rows = store._query_points_sync(vector=[0.1, 0.2], q_filter=None, limit=3, score_threshold=0.2)
    assert len(rows) == 1
    assert store._row_payload(rows[0])["content"] == "hello"
    assert store._row_score(rows[0]) == 0.88


def test_qdrant_adapter_falls_back_to_search_when_query_points_missing():
    row = {"payload": {"content": "fallback"}, "score": 0.51}

    class _Client:
        def search(self, **kwargs):
            assert kwargs["collection_name"] == "atomic_memory"
            assert "query_vector" in kwargs
            return [row]

    store = _build_store_with_client(_Client())
    rows = store._query_points_sync(vector=[0.3], q_filter=None, limit=2, score_threshold=0.1)
    assert len(rows) == 1
    assert store._row_payload(rows[0])["content"] == "fallback"
    assert store._row_score(rows[0]) == 0.51
