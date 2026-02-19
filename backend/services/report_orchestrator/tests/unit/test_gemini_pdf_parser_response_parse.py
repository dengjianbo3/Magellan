from app.parsers.gemini_pdf_parser import GeminiPDFParser


def _parser():
    return GeminiPDFParser(api_key="unit-test-key", model="gemini-3-flash-preview")


def test_parse_response_accepts_plain_json():
    parser = _parser()
    data = parser._parse_response('{"company_name":"A","team":[],"competitors":[]}', "A")
    assert data["company_name"] == "A"


def test_parse_response_accepts_markdown_json_block():
    parser = _parser()
    text = """```json
{"company_name":"B","team":[],"competitors":[]}
```"""
    data = parser._parse_response(text, "B")
    assert data["company_name"] == "B"


def test_parse_response_returns_fallback_when_not_json():
    parser = _parser()
    data = parser._parse_response("not-a-json", "Demo Co")
    assert data["company_name"] == "Demo Co"
    assert data["parse_error"] is True
