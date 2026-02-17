from app.core import service_endpoints


def test_get_web_search_url_defaults_and_env_override(monkeypatch):
    monkeypatch.delenv("WEB_SEARCH_URL", raising=False)
    assert service_endpoints.get_web_search_url() == service_endpoints.DEFAULT_WEB_SEARCH_URL

    monkeypatch.setenv("WEB_SEARCH_URL", "http://custom-search:9999")
    assert service_endpoints.get_web_search_url() == "http://custom-search:9999"


def test_get_internal_knowledge_url_defaults_and_env_override(monkeypatch):
    monkeypatch.delenv("INTERNAL_KNOWLEDGE_URL", raising=False)
    assert (
        service_endpoints.get_internal_knowledge_url()
        == service_endpoints.DEFAULT_INTERNAL_KNOWLEDGE_URL
    )

    monkeypatch.setenv("INTERNAL_KNOWLEDGE_URL", "http://custom-kb:9000")
    assert service_endpoints.get_internal_knowledge_url() == "http://custom-kb:9000"
