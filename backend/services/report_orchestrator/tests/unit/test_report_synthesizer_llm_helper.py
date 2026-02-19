import pytest

from app.agents.report_synthesizer_agent import ReportSynthesizerAgent


@pytest.mark.asyncio
async def test_quick_synthesis_parses_json_from_llm_helper(monkeypatch):
    agent = ReportSynthesizerAgent(quick_mode=True)

    async def _fake_call(prompt, response_format="text"):
        return {
            "content": '```json {"investment_score": 88, "overall_recommendation": "invest"} ```'
        }

    monkeypatch.setattr(agent.llm, "call", _fake_call)

    result = await agent._call_llm_for_quick_synthesis({"target": {"company_name": "ACME"}})

    assert result["investment_score"] == 88
    assert result["overall_recommendation"] == "invest"


@pytest.mark.asyncio
async def test_synthesis_returns_none_when_llm_helper_has_no_content(monkeypatch):
    agent = ReportSynthesizerAgent(quick_mode=False)

    async def _fake_call(prompt, response_format="text"):
        return {"error": "timeout"}

    monkeypatch.setattr(agent.llm, "call", _fake_call)

    result = await agent._call_llm_for_synthesis({"target": {"company_name": "ACME"}})

    assert result is None
