---
name: docs-wiki
description: |
  Create or update Wiki.js documentation using documentation agents with enhanced Markdown.
  Use when: (1) User types /docs-wiki, (2) "Wiki-Doku erstellen/aktualisieren",
  (3) "Dokumentation für Wiki.js", (4) "Qualitäts-Upgrade der Doku",
  (5) "Screenshots geliefert", "Seiten freigeben/veröffentlichen" (Freigabe eines Drafts)
  Supports: osTicket, Shopware6, OXID, Sylius, MCP, Bash/Shell, Claude Agents.
  Integrates Wiki.js MCP for DE + EN pages. New docs are created as drafts with screenshot
  suggestions and published only after the user delivers screenshots or explicitly approves.
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

Read THREE files from `{base_directory}/templates/`:

1. **IMMER:** `DOCS_COMMON.md` (gemeinsame Regeln, Agent-Orchestrierung, Qualitäts-Checkliste, Draft-first, Freigabe-Gate)
2. **IMMER:** `SCREENSHOTS.md` (Screenshot-Vorschläge, Platzhalter-Marker, Ersetzen durch CDN-Bilder)
3. **Typ-spezifisch:** Datei aus folgender Tabelle

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

1. **Neue Doku:** Codebase analysieren und dabei ein Inventar aus dem Code bauen (Explore-Subagent, Kategorien laut source-check 1a inkl. Projekttyp-Spezifika, siehe `skills/source-check/SKILL.md`) → Seiten-Plan (Hub + Unterseiten) auf Basis des Inventars: Jeder Inventarpunkt wird einer Seite zugeordnet oder als intern markiert → Content für alle Seiten generieren (DE + EN). Das Inventar geht als Daten in den Prompt jedes Doku-Agents, sonst sehen die Agents es nie.
2. **Update:** Bestehende Seite laden → ist sie eine Einzelseite, zuerst zu Hub + Unterseiten umbauen → Änderungen einarbeiten (DE + EN)
3. **Qualitäts-Upgrade:** Bestehende Seite laden → Einzelseite umbauen, Lücken identifizieren → Agents gezielt einsetzen (DE + EN)

Die Modi enden hier mit fertigem Content. Angelegt wird erst in Schritt 6, nach Screenshot-Vorschlägen (5c), Source-Check und Translation-Check.

### 5c. Screenshot-Vorschläge — vor Source-Check und Translation-Check

Nach der Content-Generierung und **vor** dem Source-Check (die Nummer 5c bleibt aus Kompatibilität
bestehen, der Schritt läuft zeitlich vor 5a): Regeln aus `SCREENSHOTS.md` anwenden.

- Im Content die Stellen bestimmen, an denen Lesende etwas sehen müssen, und dort Marker setzen
  (`> Screenshot folgt [{id}]: {Beschreibung}`, EN: `Screenshot pending`). Die ID ist auf DE- und
  EN-Seite identisch, außer bei Motiven, in denen die Sprache sichtbar ist (dann `_de` / `_en`).
- Dem User die Vorschlagsliste zeigen (ID, Seite, Motiv, Vorbereitung, Dateiname), danach nichts
  weiter abfragen. Gibt es keine sinnvollen Motive, das sagen und keine Marker setzen.
- Die CDN-URLs sind signiert: **nie selbst erzeugen oder raten**, sie kommen fertig vom User.
- Marker und Draft gelten bei **Neue Doku**. Bei Update und Qualitäts-Upgrade gibt es nur die
  Vorschlagsliste, und nur wenn der Text neue sichtbare Bedienschritte bekommt. Marker kommen
  nicht auf die live Seite, sie wird erst mit den gelieferten Bildern aktualisiert (siehe
  "Draft-first" in `DOCS_COMMON.md`).

### 5a. Source-Check — PFLICHT vor Translation-Check und Publish

Nach der Content-Generierung (egal welcher Modus) und **vor** dem Translation-Check:
`/wikijs-plugin:source-check` einmal über den gesamten Seiten-Satz des Laufs. Er behandelt die README
als Behauptung und prüft Pfade, Klassen, Config-Keys, Befehle und Beschreibungen gegen den
Quellcode des Projekts. Fehler, die in DE und EN gleich stehen, findet nur dieser Check. Reine
Link- oder Metadaten-Updates (z. B. die Kategorie-Karte) sind ausgenommen.

Zusätzlich hält der Check ein Inventar aus dem Code gegen den Seiten-Satz: Was im Code existiert und
nirgends steht, wird als undokumentiert gemeldet. Undokumentierte Punkte ändern weder das Verdikt
noch das Markieren, der User entscheidet nur, ob ergänzt wird. Das gilt in jedem Modus.

- **Neue Doku:** ein Explore-Subagent liest das Projekt einmal vollständig, der Hauptkontext bleibt klein. Der Check baut das Inventar unabhängig neu, statt das aus Schritt 5 wiederzuverwenden (hat Schritt 5 etwas übersehen, würde sonst auch der Check es übersehen).
- **Update / Qualitäts-Upgrade:** hat die Seite einen gültigen Verified Ref (`wikijs_get_verified_refs`,
  `page_updated_at` passt zum Live-`updatedAt`), wird der Code-Diff seit diesem Ref gelesen **und**
  jeder Abschnitt geprüft, dessen Text sich ändert, dazu das Inventar-Delta der geänderten Dateien.
  Steht ein im Diff entfernter oder umbenannter Punkt noch auf einer Seite außerhalb des Laufs, gehört
  diese Seite zum Update. Ohne gültigen Verified Ref laufen Claim-Check und Inventar-Check (1a)
  über den ganzen Seiten-Satz und werden zur Baseline.
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

### 6. Publish (Anlegen als Draft, Freigabe, Veröffentlichen)

Seiten in der Reihenfolge der Rezepte in `DOCS_COMMON.md` ("Wiki.js MCP-Workflow") schreiben:

- **Neue Doku:** zuerst alle DE-Seiten (Unterseiten, dann Hub), danach alle EN-Seiten, alles als
  **Draft** (`isPublished: false`). Danach endet der Lauf, der Skill nennt die Draft-Pfade und die
  offenen Screenshot-IDs. Veröffentlicht wird nur über das Freigabe-Gate (6a).
- **Update und Qualitäts-Upgrade:** die betroffenen Seiten in DE + EN mit `isPublished: true`
  aktualisieren. Bestehende live Seiten werden nie auf Draft zurückgesetzt.

`isPublished` wird bei jedem Aufruf explizit gesetzt, nie dem Default überlassen.

### 6a. Freigabe-Gate — nie ohne Freigabe veröffentlichen

Ein Draft wird **nie ohne Freigabe** veröffentlicht. Freigabe heißt: (a) der User hat die
Screenshots geliefert und die Prüfung ist bestanden, oder (b) der User hat **ausdrücklich** gesagt,
dass die Seiten veröffentlicht werden sollen. Schweigen, bestandene Checks, ein fertiger Text oder
nur ein Teil der Screenshots zählen nicht. Im Zweifel nachfragen. Die genaue Prüfung (keine offenen
Marker, jede Bild-URL liefert ein Bild, fail-closed) steht im "Freigabe-Gate" in `DOCS_COMMON.md`.

Wiedereinstieg, wenn der User später Screenshot-URLs liefert oder die Freigabe gibt (auch in einer
neuen Sitzung):

1. Die Seiten des Projekts finden: `wikijs_list_pages` (liefert `path` und `isPublished`, ist
   paginiert: mit `offset` weiterblättern, bis `has_more` false ist), nach Pfad-Präfix filtern. Gesucht sind Drafts (`isPublished` `false`) **und** live Seiten, auf denen
   noch ein Marker `Screenshot folgt [` / `Screenshot pending [` steht (z. B. nach einer Freigabe
   mit offenen Screenshots). Die Volltextsuche ist dafür nicht verlässlich
2. Die URLs über die ID den Markern zuordnen (`SCREENSHOTS.md`) und die Seite mit den Bildern
   aktualisieren (Draft bleibt `isPublished: false`, live Seiten bleiben live). Die Breitenangabe
   (`=Wx`) ergibt sich aus der Pixelbreite der Datei (Regel in `SCREENSHOTS.md`, Abschnitt
   "Aufnahme und Anzeigebreite")
3. Bei einem Draft das Gate durchlaufen. Dazu braucht es keinen neuen Lauf über Schritt 1 bis 5

Der `sourceRef` für das Veröffentlichen kommt aus `wikijs_get_page_history` (Eintrag, mit dem der
Draft angelegt wurde), nicht aus einem neuen `git rev-parse HEAD`. Das Ergebnis des Source-Checks
steht nicht im Draft: `wikijs_mark_verified` nur setzen, wenn PASS (oder ein vom User freigegebenes
WARN) für genau diesen Stand in dieser Sitzung feststeht. Sonst den Source-Check neu laufen lassen
oder das Markieren auslassen. Ein nie geprüfter Ref wird nie als verifiziert eingetragen.

Nach dem Veröffentlichen, in dieser Reihenfolge: `updatedAt` mit `wikijs_get_page` lesen und den
geprüften Ref mit `wikijs_mark_verified(..., pageUpdatedAt)` setzen (nur nach PASS oder vom User
freigegebenem WARN im Source-Check, und nicht bei uncommittetem Projekt-Checkout), danach die
Kategorie-Karte anlegen (erst jetzt, nie auf Draft-Seiten verlinken). Ohne die Markierung bleibt die
Seite unverifiziert und wird beim nächsten Update wieder komplett geprüft.

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
  content with all Enhanced Markdown features, screenshot suggestions with markers, the source-check
  and the translation-check), then output that finished content as Markdown for manual
  copy instead of calling wikijs_create_page/wikijs_update_page. Do not stop early or ask the user
  to fix their MCP setup before continuing.
- If the user delivers screenshot URLs that match no marker ID: ask which marker each belongs to,
  never guess an assignment and never build a CDN URL yourself (they are signed).
