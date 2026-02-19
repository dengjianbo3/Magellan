import pytest

from app.core.agents.atomic.bp_parser_agent import BPParserAgent


class _FakeParser:
    async def parse_pdf(self, file_content, filename, company_name):
        assert file_content
        return {
            "company_name": company_name,
            "product_name": "Demo Product",
            "team": [],
            "competitors": [],
        }


@pytest.mark.asyncio
async def test_bp_parser_agent_loads_file_via_locator(monkeypatch, tmp_path):
    file_path = tmp_path / "demo.pdf"
    file_path.write_bytes(b"%PDF-1.4 test")

    monkeypatch.setattr(
        "app.core.agents.atomic.bp_parser_agent.locate_uploaded_file",
        lambda _file_id: str(file_path),
    )
    monkeypatch.setattr(
        "app.core.agents.atomic.bp_parser_agent.get_gemini_parser",
        lambda: _FakeParser(),
    )

    agent = BPParserAgent()

    result = await agent.analyze(
        {
            "company_name": "Demo Co",
            "bp_file_id": "demo.pdf",
            "bp_filename": "demo.pdf",
        }
    )

    assert result["success"] is True
    assert result["company_name"] == "Demo Co"


@pytest.mark.asyncio
async def test_bp_parser_agent_returns_not_found_when_locator_misses(monkeypatch):
    monkeypatch.setattr(
        "app.core.agents.atomic.bp_parser_agent.locate_uploaded_file",
        lambda _file_id: None,
    )
    monkeypatch.setattr(
        "app.core.agents.atomic.bp_parser_agent.get_gemini_parser",
        lambda: _FakeParser(),
    )

    agent = BPParserAgent()

    result = await agent.analyze(
        {
            "company_name": "Demo Co",
            "bp_file_id": "missing.pdf",
            "bp_filename": "missing.pdf",
        }
    )

    assert result["success"] is False
    assert "找不到文件" in result["error"]
