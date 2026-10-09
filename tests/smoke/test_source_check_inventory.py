"""Smoke: the inventory check (source-check step 1a) is bounded, non-blocking and wired consistently.

The claim check goes page -> code. The inventory goes code -> page and finds features the page never
mentions. These tests guard the decisions that make it usable: undocumented items never block
marking a page as verified, the inventory is limited to what the project itself defines for users,
matching always uses the whole page set, and the flows that skip verified pages still run it.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SKILL_MD = ROOT / "skills" / "source-check" / "SKILL.md"
DOCS_WIKI_SKILL = ROOT / "skills" / "docs-wiki" / "SKILL.md"
CLAUDE_MD = ROOT / "CLAUDE.md"
DOCS_COMMON = ROOT / "skills" / "docs-wiki" / "templates" / "DOCS_COMMON.md"


def _flat(path: Path) -> str:
    """File text with whitespace collapsed, so assertions survive line wrapping."""
    return " ".join(path.read_text(encoding="utf-8").split())


def _section(path: Path, start: str, end: str) -> str:
    text = path.read_text(encoding="utf-8")
    begin = text.index(start)
    return " ".join(text[begin : text.index(end, begin)].split())


def _inventory() -> str:
    return _section(SKILL_MD, "### 1a. Inventar-Check", "### 2. Verified Ref")


def _diff_mode() -> str:
    return _section(SKILL_MD, "### 3. Update aus dem Diff", "### 4. Baseline-Lauf")


def _baseline() -> str:
    return _section(SKILL_MD, "### 4. Baseline-Lauf", "### 5. Neue Seiten")


def _verdict() -> str:
    return _section(SKILL_MD, "### 6. Verdikt und Ausgabe", "## Quick Start")


def _bullet(text: str, label: str) -> str:
    start = text.index(f"- **{label}**")
    following = [text.find(f"- **{other}**", start + 1) for other in ("FAIL", "WARN", "PASS", "Undokumentiert")]
    ends = [pos for pos in following if pos > start]
    return text[start : min(ends)] if ends else text[start:]


# --- undocumented items never block ------------------------------------------------------------


def test_undocumented_items_change_neither_the_verdict_nor_the_marking():
    verdict = _verdict()
    assert "ändern weder das Verdikt noch das Markieren" in verdict


def test_verdict_bullets_do_not_treat_undocumented_items_as_findings():
    """The verdict logic lives in the FAIL/WARN/PASS bullets of section 6: none of them may turn
    an undocumented item or a missing inventory point into a reason to block."""
    verdict = _verdict()
    for label in ("FAIL", "WARN"):
        bullet = _bullet(verdict, label).lower()
        assert "undokumentiert" not in bullet, f"{label} bullet must not cover them"
        assert "inventar" not in bullet, f"{label} bullet must not cover missing inventory points"
    assert "Undokumentiert" in verdict


def test_the_user_decides_on_additions_but_publishing_and_marking_continue():
    inventory = _inventory()
    assert "ergänzt" in inventory
    assert "veröffentlicht und markiert wird in beiden Fällen" in inventory


def test_baseline_page_buckets_count_claims_only_and_undocumented_items_are_reported_per_project():
    """An undocumented item 'steht nirgends', so no page owns it. Attributing it to pages would make the
    totals arbitrary. Pages are bucketed by their claims; the items are a per-project count."""
    baseline = _baseline()
    assert "bereits verifiziert (übersprungen) | bestanden | mit Fundstellen | nicht prüfbar" in baseline
    assert "bestanden, mit undokumentierten Punkten" not in baseline
    assert "undokumentierte Punkte pro Projekt" in baseline
    assert "außerhalb der Summe" in baseline
    assert "Summe muss zur Gesamtzahl passen" in baseline


def test_docs_wiki_5a_states_the_rule_for_every_mode_not_only_new_docs():
    step = _section(DOCS_WIKI_SKILL, "### 5a. Source-Check", "### 5b.")
    rule = "ändern weder das Verdikt noch das Markieren"
    assert rule in step
    assert step.index(rule) < step.index("**Neue Doku:**"), "the rule must stand above the per-mode bullets"


# --- scope: what counts as inventory ---------------------------------------------------------


def test_inventory_is_limited_to_what_the_project_itself_defines_for_users():
    inventory = _inventory()
    assert "was das Projekt selbst definiert" in inventory
    assert "Framework" in inventory
    assert "konfiguriert, aufruft oder erweitert" in inventory


def test_migrations_are_not_listed_one_by_one():
    inventory = _inventory()
    assert "DB-Schema" in inventory
    assert "Sammelzeile" in inventory


def test_dev_and_release_tooling_is_not_user_facing():
    assert "Entwicklungs-, Build- und Release-Skripte" in _inventory()


def test_report_groups_by_category_and_caps_long_lists():
    inventory = _inventory()
    assert "je Kategorie" in inventory
    assert "mehr als 10" in inventory


def test_categories_are_given_per_project_type():
    inventory = _inventory()
    # The row names must match the project types docs-wiki offers, or the model cannot map them.
    for project_type in ("Bash/Shell", "MCP", "osTicket", "Sylius", "Shopware", "OXID", "Claude Agent"):
        assert project_type in inventory, f"no inventory categories for {project_type}"
    assert "Parameter" in inventory, "MCP tools are only useful with their parameters"
    assert "Exit-Codes" in inventory, "the user-facing surface of a shell tool"


def test_matching_uses_the_qualified_identifier():
    """A generic name like `enabled` or `index` must not count as documented because it occurs in prose."""
    assert "qualifizierten" in _inventory()


def test_internals_decision_is_not_stored_and_its_consequence_is_stated():
    inventory = _inventory()
    assert "speichert sie nicht" in inventory
    assert "erscheinen dieselben Punkte erneut" in inventory


# --- matching against the whole page set ----------------------------------------------------


def test_matching_always_uses_the_whole_page_set_even_when_only_some_pages_are_checked():
    inventory = _inventory()
    assert "vollständigen Seiten-Satz" in inventory
    assert "wikijs_get_page" in inventory, "unchanged subpages have to be loaded for the lookup"


def test_diff_mode_matches_against_the_page_set_not_the_single_page():
    diff = _diff_mode()
    assert "im Seiten-Satz" in diff
    assert "Der Rest bleibt ungeprüft stehen" not in diff, "contradicts the inventory delta that follows"


def test_removed_item_still_named_on_a_page_outside_the_run_joins_the_update():
    """A command renamed in the diff that an unchanged subpage still names is a wrong claim on that
    subpage. If the claim check only sees the pages of the run, nobody reports it."""
    diff = _diff_mode()
    assert "außerhalb des Laufs" in diff
    assert "gehört zum Update-Satz" in diff


def test_update_recipes_add_pages_that_still_name_removed_items():
    docs_common = DOCS_COMMON.read_text(encoding="utf-8")
    for start, end in (
        ("### Bestehende Doku updaten", "### Qualitaets-Upgrade"),
        ("### Qualitaets-Upgrade", "## Qualitaets-Checkliste"),
    ):
        recipe = " ".join(docs_common[docs_common.index(start) : docs_common.index(end)].split())
        assert "auf denen entfernte Inventarpunkte stehen" in recipe, f"{start}: recipe misses the rule"


def test_de_en_difference_is_left_to_translation_check():
    """translation-check section 5 already makes a DE/EN content mismatch a FAIL. A second, differently
    graded verdict in source-check would ask the user twice."""
    inventory = _inventory()
    assert "nur in einer der beiden Sprachen" not in inventory
    assert "translation-check" in inventory


# --- the flows that skip verified pages still run the inventory ---------------------------------


def test_page_without_verified_ref_gets_claim_check_and_inventory():
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.index("Seite **ohne** Verified Ref:")
    paragraph = " ".join(text[start : text.index("###", start)].split())
    assert "Schritt 1 und 1a" in paragraph


def test_baseline_runs_the_inventory_even_when_all_pages_of_a_project_are_verified():
    assert "auch wenn alle Seiten des Projekts schon verifiziert sind" in _baseline()


def test_baseline_splits_inventory_and_claims_into_two_subagents():
    baseline = _baseline()
    assert "zwei Explore-Subagents" in baseline
    assert "Configuration-Klassen vollständig" in baseline


def test_baseline_passes_the_text_of_all_pages_but_checks_only_unverified_ones():
    """Verified pages are skipped for the claim check, but the matching needs their text, otherwise every
    item documented only on a verified page is reported as undocumented."""
    baseline = _baseline()
    assert "Text aller Seiten des Projekts" in baseline
    assert "nur dem Abgleich" in baseline
    assert "Sind alle Seiten verifiziert" in baseline


def test_full_reads_of_configuration_classes_are_required_in_the_inventory_step_itself():
    """Explore reads excerpts by default. The requirement must hold for new docs and updates too."""
    assert "Configuration-Klassen vollständig" in _inventory()


def test_diff_delta_covers_all_inventory_categories_and_grades_removals_as_findings():
    diff = _diff_mode()
    assert "alle Kategorien aus 1a" in diff
    assert "abweichende Behauptung" in diff


# --- new pages and the docs-wiki wiring ---------------------------------------------------


def test_new_pages_rebuild_the_inventory_independently_for_the_check():
    """Reusing the inventory that fed the doc agents would let a miss in step 5 repeat in the check."""
    section = _section(SKILL_MD, "### 5. Neue Seiten", "### 6. Verdikt und Ausgabe")
    assert "unabhängig" in section
    assert "vor der Content-Generierung" in section


def test_docs_wiki_hands_the_inventory_to_every_doc_agent():
    modes = _section(DOCS_WIKI_SKILL, "### 5. Execute Documentation Workflow", "### 5a.")
    assert "Prompt jedes Doku-Agents" in modes
    assert "Kategorien laut source-check 1a" in modes
    assert "skills/source-check/SKILL.md" in modes, "name the file so the model loads the skill text"


def test_undocumented_table_has_no_column_for_a_page_that_by_definition_does_not_exist():
    verdict = _verdict()
    assert "Auf der Seite" not in verdict
    assert "Vorgeschlagene Seite" in verdict


def test_unverified_pages_get_claim_check_and_inventory_in_every_mode():
    """source-check section 3 requires both; docs-wiki and the recipes used to say claim check only."""
    step = _section(DOCS_WIKI_SKILL, "### 5a. Source-Check", "### 5b.")
    assert "Claim-Check und Inventar-Check (1a)" in step
    docs_common = DOCS_COMMON.read_text(encoding="utf-8")
    for start, end in (
        ("### Bestehende Doku updaten", "### Qualitaets-Upgrade"),
        ("### Qualitaets-Upgrade", "## Qualitaets-Checkliste"),
    ):
        recipe = " ".join(docs_common[docs_common.index(start) : docs_common.index(end)].split())
        assert "Claim-Check und Inventar-Check (1a)" in recipe, f"{start}: recipe says claim check only"


def test_readme_states_the_real_coverage():
    readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())
    assert "only the delta of the changed files" in readme


def test_docs_wiki_5a_rebuilds_the_inventory_instead_of_reusing_it():
    step = _section(DOCS_WIKI_SKILL, "### 5a. Source-Check", "### 5b.")
    assert "unabhängig neu" in step


# --- discoverability ----------------------------------------------------------------------


def test_skill_description_and_routing_mention_completeness():
    skill = _flat(SKILL_MD)
    frontmatter = skill[: skill.index("# Source Check")]
    assert "fehlt etwas in der Doku" in frontmatter
    assert "fehlt etwas in der Doku" in _flat(CLAUDE_MD)
