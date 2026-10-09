"""Smoke: translation-check skill ships a glossary and is wired in before every publish.

docs-wiki must run translation-check after generating content and before the first
wikijs_create_page/wikijs_update_page call. These tests guard against the skill being added but
never reached by the publish recipes the model actually follows, and against the glossary losing
the case it exists for.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SKILL_DIR = ROOT / "skills" / "translation-check"
DOCS_WIKI_SKILL = ROOT / "skills" / "docs-wiki" / "SKILL.md"
DOCS_COMMON = ROOT / "skills" / "docs-wiki" / "templates" / "DOCS_COMMON.md"

RECIPES = [
    ("### Neue Doku erstellen", "### Bestehende Doku updaten", "wikijs_create_page("),
    ("### Bestehende Doku updaten", "### Qualitaets-Upgrade", "wikijs_update_page("),
    ("### Qualitaets-Upgrade", "## Qualitaets-Checkliste", "wikijs_update_page("),
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    return text[begin : text.index(end, begin)]


def test_glossary_exists_and_nonempty():
    glossary = SKILL_DIR / "reference" / "glossary.md"
    assert glossary.exists(), "skills/translation-check/reference/glossary.md not found"
    assert _read(glossary).strip(), "glossary.md is empty"


def test_glossary_has_cronjob_row_in_loanword_table():
    glossary = _read(SKILL_DIR / "reference" / "glossary.md")
    assert re.search(r"^\| Cronjob \|", glossary, re.MULTILINE), (
        "glossary.md needs a table row for Cronjob, the case this skill was built for"
    )


def test_glossary_has_fail_column_header():
    glossary = _read(SKILL_DIR / "reference" / "glossary.md")
    assert "Falsch (FAIL)" in glossary, "glossary tables must mark which column triggers a FAIL"


def test_skill_does_not_write_into_shipped_glossary():
    skill_md = _read(SKILL_DIR / "SKILL.md")
    assert "glossary.local.md" in skill_md, "custom entries must go to the user-local glossary"
    assert "Nie in `reference/glossary.md` schreiben" in skill_md


def test_skill_checks_de_en_drift_and_escaped_quotes():
    skill_md = _read(SKILL_DIR / "SKILL.md")
    assert "### 5. DE/EN-Abgleich" in skill_md, "DE and EN versions must be compared against each other"
    assert "### 6. Zeichenprüfung" in skill_md
    assert '`\\"`' in skill_md, "the escaped-quote leftover (backslash before a quote) must be named"


def test_skill_states_that_factual_correctness_is_out_of_scope():
    assert "Nicht Teil dieses Checks" in _read(SKILL_DIR / "SKILL.md")


def test_glossary_covers_reported_phrasing_patterns():
    glossary = _read(SKILL_DIR / "reference" / "glossary.md")
    for pattern in ("Twig-Shop", "Löschfrist-Befehl", "Einsendung", "Schachtelsatz"):
        assert pattern in glossary, f"glossary.md lacks the reported pattern: {pattern}"


def test_skill_does_not_reference_private_memory_links():
    for path in (SKILL_DIR / "SKILL.md", SKILL_DIR / "reference" / "glossary.md"):
        assert "[[" not in _read(path), f"{path.name} contains a [[wiki-link]] to private notes"


def test_each_publish_recipe_runs_translation_check_before_first_publish_call():
    docs_common = _read(DOCS_COMMON)
    for start, end, publish_call in RECIPES:
        recipe = _section(docs_common, start, end)
        assert "translation-check" in recipe, f"{start}: recipe has no translation-check step"
        assert recipe.index("translation-check") < recipe.index(publish_call), (
            f"{start}: translation-check must come before the first {publish_call}"
        )


def test_new_doc_recipe_repeats_only_the_publish_steps_per_subpage():
    recipe = _section(_read(DOCS_COMMON), "### Neue Doku erstellen", "### Bestehende Doku updaten")
    assert "Schritte 5-6 werden also pro Unterseite wiederholt" in recipe, (
        "the per-subpage repeat note must cover the create calls (5-6), not the once-per-run check (4)"
    )


def test_checklist_references_translation_check():
    docs_common = _read(DOCS_COMMON)
    checklist = docs_common[docs_common.index("## Qualitaets-Checkliste") :]
    assert "translation-check" in checklist


def test_docs_wiki_runs_check_before_publish_step():
    skill_md = _read(DOCS_WIKI_SKILL)
    check = skill_md.index("### 5a. Translation-Check")
    publish = skill_md.index("### 6. Publish")
    assert check < publish, "docs-wiki must run translation-check (5a) before the publish step (6)"


def test_docs_wiki_mode_bullets_do_not_publish():
    skill_md = _read(DOCS_WIKI_SKILL)
    modes = _section(skill_md, "### 5. Execute Documentation Workflow", "### 5a.")
    assert "publizieren" not in modes, "step 5 must end with generated content, publishing belongs to step 6"


def test_docs_wiki_fallback_without_mcp_still_runs_check():
    skill_md = _read(DOCS_WIKI_SKILL)
    start = skill_md.index("If Wiki.js MCP not available")
    fallback = skill_md[start : start + 400]
    assert "5a" in fallback, "the no-MCP fallback must include the translation-check step"


def test_claude_md_routes_to_translation_check():
    assert "/wikijs-plugin:translation-check" in _read(ROOT / "CLAUDE.md")
