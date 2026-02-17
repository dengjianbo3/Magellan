"""
Shared service endpoint defaults.

Keep URL defaults in one place to avoid drift across agents/tools.
"""

import os

DEFAULT_WEB_SEARCH_URL = "http://web_search_service:8010"
DEFAULT_INTERNAL_KNOWLEDGE_URL = "http://internal_knowledge_service:8009"


def get_web_search_url() -> str:
    return (os.getenv("WEB_SEARCH_URL") or DEFAULT_WEB_SEARCH_URL).strip()


def get_internal_knowledge_url() -> str:
    return (os.getenv("INTERNAL_KNOWLEDGE_URL") or DEFAULT_INTERNAL_KNOWLEDGE_URL).strip()
