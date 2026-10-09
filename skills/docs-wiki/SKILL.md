---
name: docs-wiki
description: |
  Create or update Wiki.js documentation using documentation agents with enhanced Markdown.
  Use when: (1) User types /docs-wiki, (2) "Wiki-Doku erstellen/aktualisieren",
  (3) "Dokumentation für Wiki.js", (4) "Qualitäts-Upgrade der Doku"
  Supports: osTicket, Shopware6, OXID, Sylius, MCP, Bash/Shell, Claude Agents.
  Integrates Wiki.js MCP for direct publishing in DE + EN.
model: claude-sonnet-5
user-invocable: true
---

# Wiki.js Documentation Skill

Create, update, or upgrade Wiki.js documentation using specialized documentation agents.

## Templates Location

Templates are in the `templates/` subdirectory of this skill.
Use `{base_directory}/templates/` to build full paths.

## Workflow

### 1. Detect or Ask Project Type

Check context for clues (current directory, user message, recent conversation).

If not detectable, ask with AskUserQuestion:
- Options: osTicket, Shopware6, OXID, Sylius, MCP, Bash/Shell, Claude Agent

If the type IS already clear from context (e.g. the user just named the platform in the same or
a preceding message), proceed directly to Step 2 — do not ask again as a defensive
double-check. The question exists for genuine ambiguity, not habitual reconfirmation.

### 2. Identify Project

Ask user which specific project to document (Freitext).

Examples: "osticket-api-endpoints", "klaro-consent", "oxid7-sitemap", "wikijs-mcp-server"

Klär dabei auch den **lokalen Checkout** des Projekts (Pfad, ist es ein Git-Repo?). Den Pfad beim
User erfragen oder aus dem Kontext übernehmen, nie erraten: Der Source-Check (Schritt 5a) braucht den
Quellcode, sonst bleibt nur die README als Quelle.

### 3. Choose Mode

Ask with AskUserQuestion:
- **Neue Doku** - Wiki.js-Seite von Grund auf erstellen
- **Update** - Bestehende Seite aktualisieren (neues Feature, geänderte Config, etc.)
- **Qualitäts-Upgrade** - Bestehende Seite mit Agents aufwerten (Diagramme, Callouts, Tutorials ergänzen)

### 4. Load Templates

Read TWO files from `{base_directory}/templates/`:

1. **IMMER:** `DOCS_COMMON.md` (gemeinsame Regeln, Agent-Orchestrierung, Qualitäts-Checkliste)
2. **Typ-spezifisch:** Datei aus folgender Tabelle

#### Template-Mapping

| Typ | File |
|-----|------|
| osTicket | `osTicket/OSTICKET_DOCS.md` |
| Shopware6 | `Shopware6/SHOPWARE6_DOCS.md` |
| OXID | `OXID/OXID_DOCS.md` |
| Sylius | `Sylius/SYLIUS_DOCS.md` |
| MCP | `MCP/MCP_DOCS.md` |
| Bash/Shell | `Bash/BASH_DOCS.md` |
| Claude Agent | `Agent/AGENT_DOCS.md` |

### 5. Execute Documentation Workflow

Based on loaded templates:

**Alle Modi arbeiten mit Hub + Unterseiten** (Regel "Hub + Unterseiten - PFLICHT" in `DOCS_COMMON.md`):
der Projektpfad ist eine kurze Startseite, Installation/Konfiguration/Fehlerbehebung/Technik und
typ-spezifische Themen liegen auf Unterseiten, die Kategorie-Karte verlinkt direkt darauf.

1. **Neue Doku:** Codebase analysieren → Seiten-Plan (Hub + Unterseiten) → Content für alle Seiten generieren (DE + EN)
2. **Update:** Bestehende Seite laden → ist sie eine Einzelseite, zuerst zu Hub + Unterseiten umbauen → Änderungen einarbeiten (DE + EN)
3. **Qualitäts-Upgrade:** Bestehende Seite laden → Einzelseite umbauen, Lücken identifizieren → Agents gezielt einsetzen (DE + EN)

Die Modi enden hier mit fertigem Content. Publiziert wird erst in Schritt 6, nach Source-Check und Translation-Check.

### 5a. Source-Check — PFLICHT vor Translation-Check und Publish

Nach der Content-Generierung (egal welcher Modus) und **vor** dem Translation-Check:
`/wikijs-plugin:source-check` einmal über den gesamten Seiten-Satz des Laufs. Er behandelt die README
als Behauptung und prüft Pfade, Klassen, Config-Keys, Befehle und Beschreibungen gegen den
Quellcode des Projekts. Fehler, die in DE und EN gleich stehen, findet nur dieser Check. Reine
Link- oder Metadaten-Updates (z. B. die Kategorie-Karte) sind ausgenommen.

- **Neue Doku:** ein Explore-Subagent liest das Projekt einmal vollständig, der Hauptkontext bleibt klein.
- **Update / Qualitäts-Upgrade:** hat die Seite einen gültigen Verified Ref (`wikijs_get_verified_refs`,
  `page_updated_at` passt zum Live-`updatedAt`), wird der Code-Diff seit diesem Ref gelesen **und**
  jeder Abschnitt geprüft, dessen Text sich ändert. Ohne gültigen Verified Ref läuft der Claim-Check
  über die ganze Seite und wird zur Baseline.
- **FAIL** → Content mit dem Wert aus dem Code korrigieren, erneut prüfen. Nicht publizieren.
- **WARN** → Fundstellen gesammelt dem User zeigen, Entscheidung einholen. Ein vom User
  freigegebenes WARN zählt für das Markieren als bestanden.
- **PASS** → weiter mit 5b. Nach dem Publish wird der geprüfte Ref mit `wikijs_mark_verified` gesetzt.

Für alle bereits vorhandenen Seiten gibt es den Baseline-Lauf: `/wikijs-plugin:source-check baseline`.
Er ändert keine Seite, meldet nur Fundstellen; Korrekturen laufen über den normalen Update-Ablauf.

### 5b. Translation-Check — PFLICHT vor jedem Publish

Nach dem Source-Check und **vor** dem ersten
`wikijs_create_page`/`wikijs_update_page`-Aufruf: `/wikijs-plugin:translation-check` einmal über den
gesamten Seiten-Satz des Laufs (alle DE-Seiten, alle EN-Seiten) laufen lassen. Der Check fängt
unnatürlich oder wörtlich übersetzte Texte ab, etwa Fachbegriffe wie "Cronjob", die als Lehnwort
bleiben müssen. Reine Link- oder Metadaten-Updates (z. B. die Kategorie-Karte) sind ausgenommen.

- **FAIL** → Content anhand der Fundstellen überarbeiten, danach erneut prüfen. Nicht publizieren.
- **WARN** → Fundstellen gesammelt dem User zeigen, Entscheidung einholen (übernehmen oder "passt so").
- **PASS** → Mit Schritt 6 fortfahren.

Siehe auch "Qualitaets-Checkliste (vor Publish)" in `DOCS_COMMON.md`.

### 6. Publish

Seiten in der Reihenfolge der Rezepte in `DOCS_COMMON.md` ("Wiki.js MCP-Workflow") publizieren:
Neue Doku legt zuerst alle DE-Seiten an (Unterseiten, dann Hub), danach alle EN-Seiten und zuletzt die Kategorie-Karte,
Update und Qualitäts-Upgrade aktualisieren die betroffenen Seiten in DE + EN.

Nach dem letzten Publish jeder Seite: `updatedAt` mit `wikijs_get_page` lesen und den geprüften Ref
mit `wikijs_mark_verified(..., pageUpdatedAt)` setzen (nur nach PASS oder vom User freigegebenem WARN
im Source-Check, und nicht bei uncommittetem Projekt-Checkout). Ohne diesen Schritt bleibt die Seite
unverifiziert und wird beim nächsten Update wieder komplett geprüft.

## Quick Start

If user provides info like "/docs-wiki osTicket api-endpoints Qualitäts-Upgrade":
- Parse the input directly
- Skip questions for provided values
- Only ask for missing information

## Adding New Project Types

1. Create folder: `templates/NewType/`
2. Create template: `templates/NewType/NEWTYPE_DOCS.md` (follow existing template pattern)
3. Add row to Template-Mapping table above
4. Done - no other changes needed

## Error Handling

- If template not found: Output error, suggest checking template directory
- If Wiki.js page not found (Update/Upgrade mode): Offer to create new page instead
- If Wiki.js MCP not available: this blocks only the *publish* step, not the whole workflow —
  still run Steps 4, 5, 5a and 5b in full (load templates, run the agents, produce complete DE + EN
  content with all Enhanced Markdown features, run the source-check and the translation-check), then output that
  finished content as Markdown for manual
  copy instead of calling wikijs_create_page/wikijs_update_page. Do not stop early or ask the user
  to fix their MCP setup before continuing.
