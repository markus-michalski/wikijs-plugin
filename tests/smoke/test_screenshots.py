"""Smoke: Neue Doku läuft Draft-first, mit Screenshot-Vorschlägen und Freigabe-Gate."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SKILL = ROOT / "skills" / "docs-wiki" / "SKILL.md"
TEMPLATES = ROOT / "skills" / "docs-wiki" / "templates"
COMMON = TEMPLATES / "DOCS_COMMON.md"
SCREENSHOTS = TEMPLATES / "SCREENSHOTS.md"
CLAUDE_MD = ROOT / "CLAUDE.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    """Return the body of the `###`/`##` section starting with `heading`."""
    match = re.search(rf"^(#{{2,3}}) {re.escape(heading)}.*$", text, re.MULTILINE)
    assert match, f"Section '{heading}' not found"
    level = len(match.group(1))
    rest = text[match.end():]
    end = re.search(rf"^#{{2,{level}}} ", rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


def test_screenshots_template_exists():
    assert SCREENSHOTS.is_file(), f"Missing {SCREENSHOTS}"


def test_skill_loads_screenshots_template():
    assert "SCREENSHOTS.md" in _read(SKILL)


def test_skill_has_screenshot_suggestion_step():
    skill = _read(SKILL)
    assert "### 5c." in skill
    assert "Screenshot" in _section(skill, "5c.")


def test_placeholder_marker_convention_documented():
    lines = _read(SCREENSHOTS).splitlines()
    for prefix in ("> Screenshot folgt [", "> Screenshot pending ["):
        idx = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
        assert idx, f"Marker-Beispiel '{prefix}' als Callout-Zeile fehlt"
        for i in idx:
            # Marker ist eine einzige unumbrochene Callout-Zeile, direkt gefolgt vom Callout-Typ
            assert lines[i + 1] == "{.is-info}", f"Marker in Zeile {i + 1} nicht einzeilig: {lines[i + 1]!r}"


def test_signed_cdn_urls_are_delivered_by_user_not_generated():
    text = _read(SCREENSHOTS)
    assert "signiert" in text
    assert "nie selbst" in text or "nie erzeugen" in text


def test_suggestion_list_columns_documented():
    text = _read(SCREENSHOTS)
    for column in ("ID", "Seite", "Motiv", "Vorbereitung", "Dateiname"):
        assert column in text, f"Spalte '{column}' fehlt in der Vorschlagsliste"


def test_neue_doku_creates_drafts():
    recipe = _section(_read(COMMON), "Neue Doku erstellen")
    assert "isPublished: false" in recipe
    assert "isPublished: true" in recipe, "Freigabe-Schritt (true) fehlt im Rezept"
    create_calls = re.findall(r"wikijs_create_page\([^)]*\)", recipe, re.DOTALL)
    assert create_calls
    assert all("isPublished: true" not in c for c in create_calls), (
        "wikijs_create_page darf in Neue Doku nie direkt veröffentlichen"
    )


def test_no_create_page_example_publishes_directly_anywhere_in_common():
    text = _read(COMMON)
    calls = re.findall(r"wikijs_create_page\([^)]*\)", text, re.DOTALL)
    assert calls
    offenders = [c for c in calls if "isPublished: true" in c]
    assert not offenders, "create_page + isPublished: true widerspricht Draft-first:\n" + "\n".join(offenders)


def test_publish_gate_documented_in_common_and_skill():
    for path in (COMMON, SKILL):
        assert "nie ohne freigabe" in _read(path).lower(), f"{path.name}: hartes Freigabe-Gate nicht formuliert"


def test_gate_is_fail_closed_on_open_markers_and_dead_urls():
    gate = _section(_read(COMMON), "Freigabe-Gate")
    assert "Screenshot folgt [" in gate, "Offene Marker müssen das Publish blockieren"
    assert "Screenshot pending [" in gate, "Offene EN-Marker müssen das Publish blockieren"
    assert "curl" in gate, "Bild-URLs müssen vor dem Publish geprüft werden"
    assert "image/" in gate, "Content-Type muss ein Bild sein, Status 200 allein reicht nicht"
    assert "-I" not in gate.replace("--", ""), "HEAD (-I) ist bei signierten CDNs unzuverlässig, GET verwenden"
    assert "nicht bestanden" in gate, "Eine nicht lauffähige Prüfung muss als nicht bestanden zählen (fail-closed)"
    assert "ohne `content`" in gate, "Veröffentlichen muss ein reines Metadaten-Update sein"
    assert "ausdruecklich" in gate.lower(), "Ausdrückliche Freigabe als Ausweg fehlt"
    assert "wikijs_get_page_history" in gate, "Wiedereinstieg muss den sourceRef aus der Historie holen"


def test_category_card_only_after_release():
    common = _read(COMMON)
    gate = _section(common, "Freigabe-Gate")
    assert "erst nach der Freigabe" in gate
    recipe = _section(common, "Neue Doku erstellen")
    publish = recipe.index("10. wikijs_update_page")
    card = recipe.index("Kategorie-Seite: Karte")
    assert publish < card, "Kategorie-Karte muss nach dem Veröffentlichen kommen"


def test_screenshot_suggestions_come_before_source_check_in_recipe():
    recipe = _section(_read(COMMON), "Neue Doku erstellen")
    assert recipe.index("4. Screenshot-Vorschlaege") < recipe.index("5. /wikijs-plugin:source-check")


def test_update_and_upgrade_stay_live():
    text = _read(COMMON)
    assert "Update und Qualitaets-Upgrade" in text
    section = _section(text, "Draft-first")
    assert "Update und Qualitaets-Upgrade** bleiben unveraendert" in section
    assert "nie auf Draft" in section
    assert "bereits live stehenden Inhalt" in section, "Umbau: Unterseiten mit Bestandsinhalt nie als Draft"


def test_claude_md_routes_and_lists_smoke_test():
    text = _read(CLAUDE_MD)
    assert "tests/smoke/test_screenshots.py" in text
    assert "Screenshot" in text
