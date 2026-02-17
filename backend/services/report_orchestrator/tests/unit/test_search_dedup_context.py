from app.core.roundtable.search_dedup import SearchDedup


def test_search_dedup_respects_context_signature():
    dedup = SearchDedup(similarity_threshold=0.8, dedup_window_minutes=5)
    session_id = "s1"
    result_payload = {"success": True, "results": [{"title": "A"}]}

    dedup.add(
        "bitcoin news",
        session_id,
        result_payload,
        context={"topic": "news", "time_range": "day"},
    )

    # Same query but different context should not dedup hit.
    miss = dedup.find_similar(
        "bitcoin news",
        session_id,
        context={"topic": "general", "time_range": "day"},
    )
    assert miss is None

    # Matching context should dedup hit.
    hit = dedup.find_similar(
        "bitcoin news",
        session_id,
        context={"topic": "news", "time_range": "day"},
    )
    assert hit is not None
    assert hit.get("_dedup") is True
