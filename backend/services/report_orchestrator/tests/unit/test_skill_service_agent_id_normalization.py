from pathlib import Path

from app.core.skills.service import SkillService


def test_skill_service_supports_hyphen_and_underscore_agent_ids():
    skills_dir = Path(__file__).resolve().parents[2] / "config" / "skills"
    svc = SkillService(skills_dir=skills_dir)

    cards_underscore = svc.select_cards("technical_analyst", "RSI MACD 交易策略")
    cards_hyphen = svc.select_cards("technical-analyst", "RSI MACD 交易策略")

    assert cards_underscore
    assert cards_hyphen
    assert [c.skill_id for c in cards_underscore] == [c.skill_id for c in cards_hyphen]

