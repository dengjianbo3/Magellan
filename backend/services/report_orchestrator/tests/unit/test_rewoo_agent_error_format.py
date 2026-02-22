import httpx

from app.core.roundtable.rewoo_agent import ReWOOAgent


def test_format_exception_never_returns_empty_string():
    err = ValueError()
    text = ReWOOAgent._format_exception(err)
    assert text
    assert text == "ValueError"


def test_format_exception_http_status_contains_status_code():
    request = httpx.Request("POST", "http://llm_gateway:8003/chat")
    response = httpx.Response(401, request=request, text="Authentication required")
    err = httpx.HTTPStatusError("Unauthorized", request=request, response=response)

    text = ReWOOAgent._format_exception(err)
    assert "HTTP 401" in text
    assert "Authentication required" in text


def test_truncate_text_marks_truncated_suffix():
    text = "x" * 100
    truncated = ReWOOAgent._truncate_text(text, 10)
    assert truncated.startswith("x" * 10)
    assert "TRUNCATED" in truncated
