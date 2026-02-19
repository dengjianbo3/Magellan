import pytest

from app.agents.risk_agent import RiskAgent


@pytest.mark.asyncio
async def test_risk_agent_call_llm_uses_unified_helper(monkeypatch):
    agent = RiskAgent(llm_gateway_url="http://llm_gateway:8003")

    async def _fake_llm_call(prompt: str, response_format: str = "text", **kwargs):
        assert response_format == "text"
        return {"content": "[]"}

    monkeypatch.setattr(agent.llm, "call", _fake_llm_call)

    content = await agent._call_llm("test prompt")
    assert content == "[]"
