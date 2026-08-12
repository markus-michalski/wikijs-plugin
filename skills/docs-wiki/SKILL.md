---
name: docs-wiki
description: |
  Create or update Wiki.js documentation using documentation agents with enhanced Markdown.
  Use when: (1) User types /docs-wiki, (2) "Wiki-Doku erstellen/aktualisieren",
  (3) "Dokumentation für Wiki.js", (4) "Qualitäts-Upgrade der Doku"
  Supports: osTicket, Shopware6, OXID, MCP, Bash/Shell, Claude Agents.
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
- Options: osTicket, Shopware6, OXID, MCP, Bash/Shell, Claude Agent

If the type IS already clear from context (e.g. the user just named the platform in the same or
a preceding message), proceed directly to Step 2 — do not ask again as a defensive
double-check. The question exists for genuine ambiguity, not habitual reconfirmation.

### 2. Identify Project

Ask user which specific project to document (Freitext).

Examples: "osticket-api-endpoints", "klaro-consent", "oxid7-sitemap", "wikijs-mcp-server"

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
| MCP | `MCP/MCP_DOCS.md` |
| Bash/Shell | `Bash/BASH_DOCS.md` |
| Claude Agent | `Agent/AGENT_DOCS.md` |

### 5. Execute Documentation Workflow

Based on loaded templates:

1. **Neue Doku:** Codebase analysieren → Content generieren → DE + EN erstellen → In Wiki.js publizieren
2. **Update:** Bestehende Seite laden → Änderungen einarbeiten → DE + EN updaten
3. **Qualitäts-Upgrade:** Bestehende Seite laden → Lücken identifizieren → Agents gezielt einsetzen → Updaten

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
  still run Steps 4-5 in full (load templates, run the agents, produce complete DE + EN content
  with all Enhanced Markdown features), then output that finished content as Markdown for manual
  copy instead of calling wikijs_create_page/wikijs_update_page. Do not stop early or ask the user
  to fix their MCP setup before continuing.
