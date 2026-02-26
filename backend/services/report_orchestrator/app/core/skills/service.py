"""
Skill manifest loader and lightweight selector.

Goal:
- Keep atomic-agent architecture unchanged.
- Inject only task-relevant skill cards into runtime prompts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except Exception:  # pragma: no cover - optional dependency fallback
    yaml = None

from ..metrics import record_cache_event


@dataclass(frozen=True)
class SkillCard:
    skill_id: str
    title_zh: str
    title_en: str
    guidance_zh: str
    guidance_en: str
    triggers: List[str]
    default: bool = False


@dataclass(frozen=True)
class AgentSkillManifest:
    agent_id: str
    cards: List[SkillCard]


class SkillService:
    def __init__(self, skills_dir: Path | None = None):
        base_dir = Path(__file__).resolve().parents[3]
        self._skills_dir = skills_dir or (base_dir / "config" / "skills")
        self._loaded = False
        self._manifests: Dict[str, AgentSkillManifest] = {}

    @staticmethod
    def _normalize_agent_id(agent_id: str) -> str:
        return str(agent_id or "").strip().lower().replace("-", "_")

    def _load(self) -> None:
        self._loaded = True
        self._manifests = {}
        if yaml is None:
            return
        if not self._skills_dir.exists():
            return

        for path in sorted(self._skills_dir.glob("*.yaml")):
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                manifest = self._parse_manifest(raw, fallback_agent_id=path.stem)
                if manifest.cards:
                    normalized_id = self._normalize_agent_id(manifest.agent_id)
                    self._manifests[normalized_id] = manifest
            except Exception:
                # Keep runtime resilient: bad one file should not block all agents.
                continue

    @staticmethod
    def _parse_manifest(raw: Dict[str, Any], fallback_agent_id: str) -> AgentSkillManifest:
        agent_id = str(raw.get("agent_id") or fallback_agent_id).strip()
        cards: List[SkillCard] = []
        for item in raw.get("skills", []) or []:
            if not isinstance(item, dict):
                continue
            skill_id = str(item.get("skill_id") or "").strip()
            if not skill_id:
                continue
            cards.append(
                SkillCard(
                    skill_id=skill_id,
                    title_zh=str(item.get("title_zh") or skill_id),
                    title_en=str(item.get("title_en") or skill_id),
                    guidance_zh=str(item.get("guidance_zh") or "").strip(),
                    guidance_en=str(item.get("guidance_en") or "").strip(),
                    triggers=[str(t).strip() for t in (item.get("triggers") or []) if str(t).strip()],
                    default=bool(item.get("default", False)),
                )
            )
        return AgentSkillManifest(agent_id=agent_id, cards=cards)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load()

    def select_cards(self, agent_id: str, user_message: str, max_cards: int = 3) -> List[SkillCard]:
        self._ensure_loaded()
        safe_agent_id = self._normalize_agent_id(agent_id)
        manifest = self._manifests.get(safe_agent_id)
        if not manifest:
            record_cache_event(layer="skills_manifest", event="miss")
            return []

        record_cache_event(layer="skills_manifest", event="hit")
        msg = str(user_message or "")
        msg_norm = msg.casefold()

        scored: List[tuple[float, SkillCard]] = []
        fallback_defaults: List[SkillCard] = []
        for card in manifest.cards:
            score = 0.0
            for trig in card.triggers:
                if trig.casefold() in msg_norm:
                    score += 1.0
            if score > 0:
                scored.append((score, card))
            elif card.default:
                fallback_defaults.append(card)

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [card for _, card in scored[:max_cards]]
        if not selected and fallback_defaults:
            selected = fallback_defaults[:max_cards]
        return selected[:max_cards]

    def build_context(self, agent_id: str, user_message: str, language: str, max_cards: int = 3, max_chars: int = 1400) -> str:
        cards = self.select_cards(agent_id=agent_id, user_message=user_message, max_cards=max_cards)
        if not cards:
            return ""

        zh = str(language or "").lower().startswith("zh")
        lines: List[str] = []
        for idx, card in enumerate(cards, start=1):
            title = card.title_zh if zh else card.title_en
            guidance = card.guidance_zh if zh else card.guidance_en
            if not guidance:
                continue
            lines.append(f"{idx}. {title}: {guidance}")

        text = "\n".join(lines).strip()
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 16] + "\n...[trimmed]"


_skill_service = SkillService()


def get_skill_service() -> SkillService:
    return _skill_service


def build_skill_instruction_context(agent_id: str, user_message: str, language: str) -> str:
    return _skill_service.build_context(
        agent_id=agent_id,
        user_message=user_message,
        language=language,
    )
