import pytest

from app.core.intent_recognizer import IntentRecognizer, IntentType


@pytest.mark.asyncio
async def test_intent_recognizer_llm_classify_parses_intent(monkeypatch):
    recognizer = IntentRecognizer(llm_gateway_url="http://llm_gateway:8003")

    async def _fake_llm_call(prompt: str, response_format: str = "text", **kwargs):
        return {"content": "dd_analysis"}

    monkeypatch.setattr(recognizer.llm, "call", _fake_llm_call)

    intent, confidence = await recognizer._llm_classify("帮我做尽调")

    assert intent == IntentType.DD_ANALYSIS
    assert confidence == 0.85
