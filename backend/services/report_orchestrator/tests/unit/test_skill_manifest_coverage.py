from pathlib import Path
import re


def _load_agent_ids(agents_yaml: Path) -> set[str]:
    text = agents_yaml.read_text(encoding="utf-8")
    return {
        m.group(1).strip()
        for m in re.finditer(r"^\s*-\s*agent_id:\s*([a-zA-Z0-9_-]+)\s*$", text, flags=re.MULTILINE)
    }


def test_all_agents_have_skill_manifest():
    root = Path(__file__).resolve().parents[2]
    agents_yaml = root / "config" / "agents.yaml"
    skills_dir = root / "config" / "skills"

    agent_ids = _load_agent_ids(agents_yaml)
    skill_ids = {path.stem for path in skills_dir.glob("*.yaml")}

    missing = sorted(agent_ids - skill_ids)
    assert not missing, f"Missing skills manifests for agents: {missing}"
