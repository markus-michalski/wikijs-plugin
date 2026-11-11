# Screenshots - Vorschlaege, Platzhalter, Freigabe

Diese Regeln gelten fuer ALLE Projekttypen, immer zusammen mit `DOCS_COMMON.md` laden. Sie
beschreiben, wie Screenshot-Vorschlaege entstehen und wie Seiten ohne fertige Screenshots als Draft
im Wiki liegen, bis du sie lieferst.

## Ablauf

1. Text fuer alle Seiten wird aus den Quellen erstellt (Schritt 5 im Skill)
2. Screenshot-Vorschlaege werden bestimmt, im Text als Marker gesetzt und dir als Liste gezeigt
3. Source-Check und Translation-Check laufen ueber den Text mit Markern
4. Die Seiten werden als **Draft** angelegt (`isPublished: false`), nichts ist oeffentlich
5. Du lieferst die Screenshots als fertige CDN-URLs, die Marker werden durch Bilder ersetzt
6. Veroeffentlicht wird erst nach dem Freigabe-Gate (siehe "Freigabe-Gate" in `DOCS_COMMON.md`)

## Was einen Screenshot verdient

Ein Screenshot gehoert dorthin, wo Lesende etwas **sehen** muessen, um weiterzukommen:

- Admin-Oberflaeche: Einstellungsseiten, Plugin-Konfiguration, Listen und Detailansichten
- Ergebnis im Frontend: so sieht es fuer Kunden oder Nutzer aus (Widget, Formular, Fehlermeldung)
- Mehrstufige Ablaeufe: ein Bild je Wizard-Schritt, an dem man sich verlaufen kann
- Fehlerbilder aus der Fehlerbehebung: die Meldung, nach der Lesende suchen

Kein Screenshot fuer Code, Terminal-Ausgaben, Tabellen und reinen Fliesstext. Das steht besser als
Codeblock oder Tabelle im Text. Pro Seite sind 1 bis 4 Screenshots ueblich, mehr nur bei echten
Wizard-Abfolgen.

### Kandidaten je Projekttyp

| Typ | Typische Motive |
|-----|-----------------|
| Shopware6 | Plugin-Konfiguration im Admin, Storefront-Ergebnis, Fehlermeldung, CMS-Element |
| Sylius | Admin-Seite des Plugins, Shop-Ergebnis, Checkout-Schritt |
| OXID | Modul-Einstellungen im Admin, Frontend-Ergebnis |
| osTicket | Admin-Panel-Einstellungen, Ticket-Ansicht mit dem Feature |
| MCP | Meist keine. Nur wenn es eine Oberflaeche gibt (z. B. Ausgabe in Claude Code) |
| Bash/Shell | Meist keine. Nur bei interaktiven Menues oder einer Ausgabe, die ein Bild braucht |
| Claude Agent | Meist keine. Nur bei sichtbarem Ergebnis |

Gibt es zu einem Projekt keine sinnvollen Motive, die Liste leer lassen und das so sagen. Nichts
vorschlagen, nur damit die Seite ein Bild hat.

## Platzhalter-Marker

Die CDN-URLs sind **signiert**: Das erste Pfadsegment haengt vom restlichen Pfad ab, eine
veraenderte oder geratene Signatur liefert 403. URLs werden deshalb **nie selbst erzeugt oder
geraten**, sie kommen fertig vom User. Bis dahin steht an der Stelle des Bildes ein Marker, als
eine einzige, unumbrochene Callout-Zeile (Regel "Callout Boxes NIE im Quelltext umbrechen"):

```markdown
> Screenshot folgt [altcha-admin_1]: Plugin-Konfiguration im Admin mit aktiviertem ALTCHA-Feld
{.is-info}
```

EN-Seite:

```markdown
> Screenshot pending [altcha-admin_1]: Plugin configuration in the admin with the ALTCHA field enabled
{.is-info}
```

- Die ID in eckigen Klammern ist auf DE- und EN-Seite **identisch**, sie ist der Schluessel fuer
  die Zuordnung der URL. Das Wort davor (`folgt` / `pending`) wird uebersetzt, die ID nie.
- Die ID folgt dem Muster `{projekt}-{motiv}_{nr}` (z. B. `altcha-admin_1`). Das entspricht dem
  Dateinamen auf dem CDN ohne Endung.
- Der Text nach dem Doppelpunkt beschreibt, was auf dem Bild zu sehen sein soll. Er wird spaeter zum
  Alt-Text (Pflicht, Barrierefreiheit).
- Ein Motiv, das auf DE- und EN-Seite vorkommt, hat eine ID und ein Bild. Die Screenshots sind
  sprachneutral, es sei denn, die Oberflaeche ist in der Sprache sichtbar. Dann zwei IDs mit
  Suffix `_de` / `_en`.

## Vorschlagsliste im Chat

Nach dem Setzen der Marker zeigt der Skill dir diese Tabelle, eine Zeile je Marker:

| ID | Seite | Motiv | Vorbereitung | Dateiname |
|----|-------|-------|--------------|-----------|
| `altcha-admin_1` | `shopware6/altcha/configuration` | Plugin-Konfiguration mit aktiviertem ALTCHA-Feld | Plugin installiert, Feld aktiviert, Beispielwerte gesetzt | `altcha-admin_1.webp` |

- **Seite:** Pfad der Seite, auf der der Marker steht
- **Motiv:** was zu sehen sein soll, inklusive des Bereichs, der im Ausschnitt sein muss
- **Vorbereitung:** welcher Zustand vorher herzustellen ist (Daten, Einstellungen, Sprache)
- **Dateiname:** `{ID}.webp`, wie es auf dem CDN liegen soll

Danach fragt der Skill nichts weiter ab. Die Seiten liegen als Draft im Wiki, du lieferst die URLs,
wenn die Bilder da sind.

## Aufnahme und Anzeigebreite

Damit die Schrift im Bild so gross wirkt wie im Fliesstext, haengt die Anzeigebreite nicht von
einer Zielbreite ab, sondern von der Aufnahme:

1. Browser-DevTools, Geraetemodus: Viewport **1200 px**, Device Pixel Ratio (**DPR**) **2**,
   Seite neu laden
2. Mit dem Screenshot-Button der DevTools den sichtbaren Bereich aufnehmen (ca. 2400 px breit). Der
   Element-Screenshot der DevTools und Werkzeuge wie das Snipping-Tool ignorieren DPR 2 und liefern
   Bilder in 1-facher Aufloesung
3. Auf den gewuenschten Ausschnitt zuschneiden, **ohne zu skalieren** (kein "Groesse aendern", keine
   automatische Verkleinerung beim Speichern). Hochskalieren auf eine einheitliche Breite ist der
   haeufigste Fehler: Die Schrift wird doppelt so gross und unscharf
4. Als WebP auf das CDN laden und die URL liefern

**Anzeigebreite = Pixelbreite / 2.** Ein Zahlart-Block mit 1075 px wird `=537x`, ein ganzer Screen
mit 2400 px bekommt keine Angabe (oder `=1200x`).

Das Hilfsskript `servers/wikijs-mcp-server/tools/screenshot_width.py` liest die Pixelbreite aus
PNG- und WebP-Dateien, nennt die passende Breite und warnt bei Dateien unter 800 px ohne
Breitenangabe (vermutlich nicht mit DPR 2 aufgenommen). Mit `--url` und `--alt` gibt es die fertige Markdown-Zeile aus. Es laedt
nichts hoch und signiert nichts:

Der Aufruf nutzt das venv des Plugins (`<SCRIPT>` steht fuer
`${CLAUDE_PLUGIN_ROOT}/servers/wikijs-mcp-server/tools/screenshot_width.py`):

- POSIX: `${CLAUDE_PLUGIN_ROOT}/bin/run-server <SCRIPT> block.png --url "{cdn-url}" --alt "{alt-text}"`
- Windows: `& "$env:USERPROFILE\.wikijs-plugin\venv\Scripts\python.exe" <SCRIPT> block.png --url "{cdn-url}" --alt "{alt-text}"`

Der Upload auf das CDN bleibt Sache des Users. Der Skill liest die Pixelbreite bei geliefertem Bild
selbst aus (siehe "Breitenpruefung" im Freigabe-Gate in `DOCS_COMMON.md`).

## Marker durch Bilder ersetzen

Lieferst du die URLs, ordnet der Skill sie ueber die ID zu: Der Dateiname im Pfad der URL (letztes
Pfadsegment ohne Endung, auch hinter einem Quellpfad wie `plain/s3://...`) ist die ID. Passt kein
Dateiname zu einer ID oder ist er in der URL nicht erkennbar, fragt der Skill nach, statt zu raten.

```markdown
![Plugin-Konfiguration im Admin mit aktiviertem ALTCHA-Feld]({url-vom-user})
```

- Die URL wird unveraendert uebernommen, inklusive Signatur
- Alt-Text = die Beschreibung aus dem Marker
- Breitenangabe nach der Bildart (Regeln unter "Aufnahme und Anzeigebreite"):
  - **Ganze Screens** (ca. 2400 px breit): keine Breitenangabe. Wiki.js zeigt sie in voller
    Spaltenbreite. Ein pauschales `=600x` wuerde sie auf die Haelfte verkleinern, die UI-Schrift
    waere unleserlich
  - **Ausschnitte** (ein Zahlart-Block, eine Hinweisbox, ein Formularfeld): immer `=Wx` mit
    W = Pixelbreite / 2. Ohne Angabe wuerde ein schmaler Ausschnitt auf die ganze Spaltenbreite
    gezogen, die Schrift im Bild waere doppelt so gross wie im Fliesstext
  - Kleine Dialoge folgen derselben Regel (W = Pixelbreite / 2). Logos und andere Bilder, die
    nicht aus einer Aufnahme stammen, bekommen eine kleine Festbreite, z. B. `=200x`, und werden
    von der Breitenpruefung ausgenommen
- Der Austausch ist ein inhaltliches Update der Draft-Seite (`wikijs_get_page`, ganzen Content
  anpassen, `wikijs_update_page` mit `isPublished: false`)
- Eine geloeste ID verschwindet aus der Vorschlagsliste, die offene Rest-Liste zeigt der Skill
  nach jeder Lieferung
