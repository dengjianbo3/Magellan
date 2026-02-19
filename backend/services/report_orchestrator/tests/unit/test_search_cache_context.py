from app.core.roundtable.search_cache import SearchCache


def test_search_cache_key_includes_search_params():
    cache = SearchCache(redis_url="redis://unused")

    key_general = cache._generate_key(
        "btc price",
        "normal",
        search_params={"topic": "general", "time_range": "day", "max_results": 5},
    )
    key_news = cache._generate_key(
        "btc price",
        "normal",
        search_params={"topic": "news", "time_range": "day", "max_results": 5},
    )

    assert key_general != key_news
