from app.services.storage.report_storage import ReportStorage


def test_memory_backend_get_delete_are_user_scoped():
    storage = ReportStorage(session_store=None)

    storage.save("r1", {"id": "r1", "user_id": "u1", "title": "u1-report"})
    storage.save("r2", {"id": "r2", "user_id": "u2", "title": "u2-report"})

    assert storage.get("r1", user_id="u1")["title"] == "u1-report"
    assert storage.get("r1", user_id="u2") is None

    assert storage.delete("r1", user_id="u2") is False
    assert storage.get("r1", user_id="u1") is not None

    assert storage.delete("r1", user_id="u1") is True
    assert storage.get("r1", user_id="u1") is None
