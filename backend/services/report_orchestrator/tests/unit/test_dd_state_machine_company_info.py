import pytest

from app.core.dd_state_machine import DDStateMachine


@pytest.mark.asyncio
async def test_search_company_info_uses_normalized_search_fields(monkeypatch):
    sm = DDStateMachine(
        session_id="s1",
        company_name="Acme",
        bp_file_content=None,
        bp_filename="none.txt",
        user_id="u1",
    )

    captured = {}

    async def fake_search_web(web_search_url, *, query, max_results=5, **kwargs):
        captured["query"] = query
        captured["max_results"] = max_results
        return [
            {
                "title": "Acme 官方介绍",
                "content": "Acme 主要提供工业自动化 SaaS 服务。",
                "url": "https://example.com/acme",
                "score": 0.9,
            }
        ]

    async def fake_llm_call(*, prompt, response_format="json", **kwargs):
        captured["prompt"] = prompt
        assert response_format == "json"
        return {
            "company_name": "Acme Inc",
            "product_description": "工业自动化 SaaS 平台",
            "target_market": "制造业",
            "current_stage": "A轮",
            "founding_year": "2020",
            "key_members": ["Alice CEO"],
        }

    monkeypatch.setattr("app.core.dd_state_machine.shared_search_web", fake_search_web)
    monkeypatch.setattr(sm._llm_helper, "call", fake_llm_call)

    result = await sm._search_company_info("Acme")

    assert captured["query"] == "Acme 公司简介 业务 产品"
    assert "内容: Acme 主要提供工业自动化 SaaS 服务。" in captured["prompt"]
    assert "链接: https://example.com/acme" in captured["prompt"]
    assert result.company_name == "Acme Inc"
    assert result.founding_date == "2020"
    assert len(result.team) == 1
