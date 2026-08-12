"""Smoke: skill frontmatter has required fields, valid model IDs, no duplicates."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent.parent
SKILLS_DIR = ROOT / "skills"

REQUIRED_FIELDS = {"name", "description", "model", "user-invocable"}
VALID_MODELS = {
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-sonnet-5",
    "claude-haiku-4-5",
    "claude-haiku-4-5-20251001",
}


def _load_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def _all_skills() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def test_skills_directory_exists():
    assert SKILLS_DIR.exists(), f"skills/ directory not found: {SKILLS_DIR}"


def test_at_least_one_skill():
    skills = _all_skills()
    assert skills, "No SKILL.md files found under skills/"


def test_docs_wiki_and_setup_skills_present():
    names = {p.parent.name for p in _all_skills()}
    assert {"docs-wiki", "setup"} <= names, f"Expected docs-wiki and setup skills, found: {names}"


def test_all_skills_have_required_fields():
    failures = []
    for skill_md in _all_skills():
        fm = _load_frontmatter(skill_md)
        missing = REQUIRED_FIELDS - set(fm.keys())
        if missing:
            failures.append(f"{skill_md.parent.name}: missing {sorted(missing)}")
    assert not failures, "Skills with missing frontmatter fields:\n" + "\n".join(failures)


def test_all_skills_have_valid_model():
    failures = []
    for skill_md in _all_skills():
        fm = _load_frontmatter(skill_md)
        model = fm.get("model", "")
        if model not in VALID_MODELS:
            failures.append(f"{skill_md.parent.name}: invalid model '{model}'")
    assert not failures, "Skills with invalid model IDs:\n" + "\n".join(failures)


def test_no_duplicate_skill_names():
    names = [_load_frontmatter(s).get("name", "") for s in _all_skills()]
    names = [n for n in names if n]
    assert len(names) == len(set(names)), (
        f"Duplicate skill names: {[n for n in names if names.count(n) > 1]}"
    )


def test_user_invocable_is_boolean():
    failures = []
    for skill_md in _all_skills():
        fm = _load_frontmatter(skill_md)
        value = fm.get("user-invocable")
        if not isinstance(value, bool):
            failures.append(f"{skill_md.parent.name}: user-invocable={value!r} (must be bool)")
    assert not failures, "Skills with non-boolean user-invocable:\n" + "\n".join(failures)
