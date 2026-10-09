"""Smoke: source-check skill is wired in before translation-check and before every publish.

docs-wiki must verify page claims against the source code (not the README) after generating
content, before translation-check and before the first wikijs_create_page/wikijs_update_page
call. A stored source_ref only counts as a baseline once wikijs_mark_verified recorded it. These
tests guard against the skill being added but never reached by the recipes the model follows.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SKILL_MD = ROOT / "skills" / "source-check" / "SKILL.md"
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


def test_skill_exists_with_matching_name():
    assert SKILL_MD.exists(), "skills/source-check/SKILL.md not found"
    assert "name: source-check" in _read(SKILL_MD)


def test_skill_has_all_five_parts_of_the_issue():
    skill = _read(SKILL_MD)
    for heading in (
        "### 1. Claim-Check",
        "### 2. Verified Ref",
        "### 3. Update aus dem Diff",
        "### 4. Baseline-Lauf",
        "### 5. Neue Seiten",
    ):
        assert heading in skill, f"source-check lacks section: {heading}"


def test_skill_treats_code_as_truth_and_readme_as_claim():
    skill = _read(SKILL_MD)
    assert "Der Code gewinnt" in skill
    assert "README" in skill


def test_skill_searches_the_places_where_routes_hooks_and_wiring_live():
    skill = _read(SKILL_MD)
    for location in ("config/**/*.yaml", "config/services.php", "templates/**/*.twig"):
        assert location in skill, f"claim check must explicitly cover {location}"


def test_skill_reports_the_file_with_the_real_value():
    assert "Datei" in _read(SKILL_MD) and "Istwert" in _read(SKILL_MD)


def test_skill_only_marks_verified_after_a_passing_check():
    skill = _read(SKILL_MD)
    assert "wikijs_mark_verified" in skill
    assert "wikijs_get_verified_refs" in skill
    assert "source_ref" in skill and "nicht als verifiziert" in skill, (
        "existing written-at refs must be stated as not verified"
    )


def test_skill_update_reads_only_changed_files_via_diff_against_the_verified_ref():
    section = _section(_read(SKILL_MD), "### 3. Update aus dem Diff", "### 4. Baseline-Lauf")
    assert "git diff --stat" in section
    assert "HEAD" in section


def test_baseline_mode_changes_nothing_and_lists_unchecked_pages():
    section = _section(_read(SKILL_MD), "### 4. Baseline-Lauf", "### 5. Neue Seiten")
    assert "Explore" in section
    assert "ändert nichts" in section
    assert "kein lokaler Checkout" in section, "pages without a local checkout must be listed separately"
    assert "pro Projekt" in section


def test_diff_mode_also_checks_every_section_whose_text_changed():
    """An empty code diff must not mark newly written text as verified: sections the agents
    just wrote or changed are claim-checked regardless of which code files changed."""
    section = _section(_read(SKILL_MD), "### 3. Update aus dem Diff", "### 4. Baseline-Lauf")
    assert "jeden Abschnitt, dessen Text sich gegenüber der veröffentlichten Version ändert" in section
    assert "Ein leerer Code-Diff" in section
    assert "wikijs_get_page" in section, "the published text to compare against comes from wikijs_get_page"


def test_docs_wiki_source_check_step_repeats_the_changed_text_rule():
    step = _section(_read(DOCS_WIKI_SKILL), "### 5a. Source-Check", "### 5b.")
    assert "Text sich ändert" in step or "geänderten Text" in step


def test_verified_marker_is_bound_to_the_page_state_it_covered():
    skill = _read(SKILL_MD)
    section = _section(skill, "### 2. Verified Ref", "### 3. Update aus dem Diff")
    assert "pageUpdatedAt" in section and "updatedAt" in section
    assert "außerhalb" in section, "edits outside the gated flow must be named as the reason"
    assert "Live-Wert" in skill, "a mismatching updatedAt must make the page count as unverified"


def test_recipes_pass_the_page_state_when_marking_verified():
    docs_common = _read(DOCS_COMMON)
    for start, end, publish_call in RECIPES:
        recipe = _section(docs_common, start, end)
        assert "pageUpdatedAt" in recipe, f"{start}: wikijs_mark_verified needs pageUpdatedAt"
        after_publish = recipe[recipe.rindex(publish_call) :]
        assert "wikijs_get_page" in after_publish, (
            f"{start}: updatedAt must be read with wikijs_get_page after the last publish call"
        )


def test_dirty_checkout_is_never_marked_verified_silently():
    section = _section(_read(SKILL_MD), "### 0. Vorbereitung", "### 1. Claim-Check")
    assert "git status --short" in section
    assert "nicht als verifiziert" in section


def test_restructure_recipe_does_not_publish_before_the_checks():
    """Umbau used to create the new subpages at its own step 3, i.e. before the source-check of the
    surrounding recipe ran. Publishing must wait for both checks."""
    docs_common = _read(DOCS_COMMON)
    umbau = _section(docs_common, "### Bestehende Einzelseite umbauen", "Reihenfolge beim **Neu-Anlegen**")
    assert "source-check" in umbau and "translation-check" in umbau
    assert umbau.index("source-check") < umbau.index("wikijs_create_page"), (
        "Umbau must name the source-check before its first wikijs_create_page"
    )


def test_dirty_checkout_has_no_user_override_for_marking():
    prep = _section(_read(SKILL_MD), "### 0. Vorbereitung", "### 1. Claim-Check")
    assert "außer der User bestätigt" not in prep, "docs-wiki and the checklist forbid marking a dirty checkout"
    assert "erst einchecken" in prep or "erst committen" in prep


def test_skill_names_plugin_own_link_and_metadata_updates_as_marker_resets():
    section = _section(_read(SKILL_MD), "### 2. Verified Ref", "### 3. Update aus dem Diff")
    assert "Link" in section and "Tag" in section and "Kategorie-Karte" in section


def test_claim_check_searches_the_whole_repository_not_just_the_directory_the_page_names():
    """Found in a live trial: a page located the IPv6 /64 counting in the rate-limit directory,
    the logic lives in the request directory. A search scoped to the named directory misses it."""
    section = _section(_read(SKILL_MD), "### 1. Claim-Check", "### 2. Verified Ref")
    assert "gesamte Repository" in section
    for excluded in ("vendor/", "var/", "node_modules/"):
        assert excluded in section, f"the search must exclude {excluded}"
    assert "Tests" in section, "tests document behaviour but do not replace the code"


def test_claim_check_reports_missing_entries_in_lists_and_trees():
    """A directory tree or list on a page can omit an entry (e.g. a source directory the page
    never mentions). Wrong entries and missing entries are both findings."""
    section = _section(_read(SKILL_MD), "### 1. Claim-Check", "### 2. Verified Ref")
    assert "fehlende Einträge" in section
    assert "Verzeichnisbäume" in section


def _inventory_section() -> str:
    return _section(_read(SKILL_MD), "### 1a. Inventar-Check", "### 2. Verified Ref")


def test_inventory_check_sits_between_claim_check_and_verified_ref():
    skill = _read(SKILL_MD)
    claim = skill.index("### 1. Claim-Check")
    inventory = skill.index("### 1a. Inventar-Check")
    verified = skill.index("### 2. Verified Ref")
    assert claim < inventory < verified


def test_inventory_is_built_from_the_code_and_not_the_readme():
    """The claim check goes page -> code and cannot see a feature the page never mentions.
    The inventory goes code -> page and finds exactly those."""
    section = _inventory_section()
    assert "aus dem Code" in section
    assert "nicht aus der README" in section
    assert "Explore" in section


def test_inventory_covers_the_user_facing_surface():
    section = _inventory_section()
    for item in ("Console-Commands", "Routen", "Config-Keys", "Umgebungsvariablen", "Events", "Twig", "Entities"):
        assert item in section, f"inventory must cover {item}"


def test_internals_are_excluded_and_intern_is_a_user_decision():
    section = _inventory_section()
    assert "undokumentiert" in section
    assert "Interna" in section, "internal classes are not expected on a page"
    assert "bewusst intern" in section


def test_inventory_states_that_it_is_heuristic():
    assert "heuristisch" in _inventory_section()


def test_new_pages_build_the_inventory_before_the_content_is_generated():
    section = _section(_read(SKILL_MD), "### 5. Neue Seiten", "### 6. Verdikt und Ausgabe")
    assert "Inventar" in section
    assert "vor der Content-Generierung" in section


def test_diff_mode_and_baseline_use_the_inventory_too():
    skill = _read(SKILL_MD)
    diff = _section(skill, "### 3. Update aus dem Diff", "### 4. Baseline-Lauf")
    baseline = _section(skill, "### 4. Baseline-Lauf", "### 5. Neue Seiten")
    assert "Inventar" in diff, "new or removed user-facing items in the diff must show up on the page"
    assert "Inventar" in baseline


def test_verdict_output_lists_undocumented_items():
    section = _section(_read(SKILL_MD), "### 6. Verdikt und Ausgabe", "## Quick Start")
    assert "Undokumentiert" in section


def test_docs_wiki_new_doc_mode_starts_from_the_code_inventory():
    modes = _section(_read(DOCS_WIKI_SKILL), "### 5. Execute Documentation Workflow", "### 5a.")
    new_doc = modes[modes.index("**Neue Doku:**") :].splitlines()[0]
    assert "Inventar" in new_doc


def test_new_doc_recipe_builds_the_inventory_before_generating_and_checking():
    recipe = _section(_read(DOCS_COMMON), "### Neue Doku erstellen", "### Bestehende Doku updaten")
    assert "Inventar" in recipe
    inventory = recipe.index("Inventar")
    assert inventory < recipe.index("Seiten-Plan"), "the plan is made from the inventory"
    assert inventory < recipe.index("/wikijs-plugin:source-check"), "the inventory exists before the check runs"


def test_baseline_pages_through_the_page_list_and_reports_totals():
    section = _section(_read(SKILL_MD), "### 4. Baseline-Lauf", "### 5. Neue Seiten")
    assert "has_more" in section
    assert "Gesamtzahl" in section


def test_checkout_path_is_resolved_not_guessed():
    prep = _section(_read(SKILL_MD), "### 0. Vorbereitung", "### 1. Claim-Check")
    assert "nicht raten" in prep or "nicht erraten" in prep
    docs_wiki_step2 = _section(_read(DOCS_WIKI_SKILL), "### 2. Identify Project", "### 3. Choose Mode")
    assert "Checkout" in docs_wiki_step2


def test_diff_uses_the_oldest_verified_ref_of_the_locale_set():
    section = _section(_read(SKILL_MD), "### 3. Update aus dem Diff", "### 4. Baseline-Lauf")
    assert "ältesten" in section


def test_skill_states_ref_is_the_checked_state_not_the_newest_commit():
    assert "nicht zwingend der neueste Commit" in _read(SKILL_MD)


def test_warn_released_by_the_user_counts_as_passed_for_marking():
    for text in (_read(DOCS_COMMON), _read(DOCS_WIKI_SKILL)):
        assert "freigegebenes WARN" in text


def test_docs_wiki_publish_step_mentions_marking_verified():
    publish = _read(DOCS_WIKI_SKILL)
    publish = publish[publish.index("### 6. Publish") :]
    assert "wikijs_mark_verified" in publish


def test_translation_check_points_at_the_renumbered_docs_wiki_step():
    skill_md = _read(ROOT / "skills" / "translation-check" / "SKILL.md")
    assert "docs-wiki/SKILL.md` Schritt 5b" in skill_md, "docs-wiki step 5a is now the source-check"


def test_translation_check_scope_note_points_to_source_check():
    skill_md = _read(ROOT / "skills" / "translation-check" / "SKILL.md")
    note = skill_md[skill_md.index("Nicht Teil dieses Checks") :][:600]
    assert "/wikijs-plugin:source-check" in note


def test_skill_does_not_reference_private_memory_links():
    assert "[[" not in _read(SKILL_MD)


def test_each_publish_recipe_runs_source_check_before_translation_check_and_publish():
    docs_common = _read(DOCS_COMMON)
    for start, end, publish_call in RECIPES:
        recipe = _section(docs_common, start, end)
        assert "source-check" in recipe, f"{start}: recipe has no source-check step"
        assert recipe.index("source-check") < recipe.index("translation-check"), (
            f"{start}: source-check must run before translation-check"
        )
        assert recipe.index("translation-check") < recipe.index(publish_call)


def test_each_publish_recipe_marks_verified_after_the_last_publish_call():
    docs_common = _read(DOCS_COMMON)
    for start, end, publish_call in RECIPES:
        recipe = _section(docs_common, start, end)
        assert "wikijs_mark_verified(" in recipe, f"{start}: recipe never records the verified ref"
        assert recipe.rindex("wikijs_mark_verified(") > recipe.rindex(publish_call), (
            f"{start}: wikijs_mark_verified must come after the publish calls"
        )


def test_checklist_references_source_check():
    docs_common = _read(DOCS_COMMON)
    checklist = docs_common[docs_common.index("## Qualitaets-Checkliste") :]
    assert "source-check" in checklist


def test_docs_wiki_runs_source_check_before_translation_check_before_publish():
    skill_md = _read(DOCS_WIKI_SKILL)
    source = skill_md.index("### 5a. Source-Check")
    translation = skill_md.index("### 5b. Translation-Check")
    publish = skill_md.index("### 6. Publish")
    assert source < translation < publish


def test_docs_wiki_fallback_without_mcp_still_runs_source_check():
    skill_md = _read(DOCS_WIKI_SKILL)
    start = skill_md.index("If Wiki.js MCP not available")
    assert "5a" in skill_md[start : start + 500]


def test_docs_wiki_offers_baseline_mode():
    assert "Baseline" in _read(DOCS_WIKI_SKILL)


def test_claude_md_routes_to_source_check():
    assert "/wikijs-plugin:source-check" in _read(ROOT / "CLAUDE.md")
