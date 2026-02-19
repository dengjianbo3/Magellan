from app.services.vector_store import VectorStoreService


class _Point:
    def __init__(self, point_id, payload):
        self.id = point_id
        self.payload = payload


class _FakeQdrantClient:
    def __init__(self):
        self.calls = []
        self.pages = {
            None: (
                [
                    _Point("id1", {"text": "a" * 250, "title": "doc1"}),
                    _Point("id2", {"text": "short-2", "title": "doc2"}),
                ],
                "cursor-2",
            ),
            "cursor-2": (
                [
                    _Point("id3", {"text": "short-3", "title": "doc3"}),
                    _Point("id4", {"text": "short-4", "title": "doc4"}),
                ],
                None,
            ),
        }

    def scroll(self, **kwargs):
        self.calls.append(kwargs)
        return self.pages.get(kwargs.get("offset"), ([], None))


def _build_service_with_fake_client():
    svc = VectorStoreService.__new__(VectorStoreService)
    svc.client = _FakeQdrantClient()
    svc.collection_name = "kb"
    return svc


def test_list_documents_offset_limit_pagination_works():
    svc = _build_service_with_fake_client()

    docs = svc.list_documents(limit=2, offset=1, include_full_text=False)

    assert [d["id"] for d in docs] == ["id2", "id3"]
    # short text should not be forced with ellipsis
    assert docs[0]["text"] == "short-2"


def test_list_documents_include_full_text_returns_untruncated_text():
    svc = _build_service_with_fake_client()

    docs = svc.list_documents(limit=1, offset=0, include_full_text=True)

    assert docs[0]["id"] == "id1"
    assert docs[0]["text"] == "a" * 250
