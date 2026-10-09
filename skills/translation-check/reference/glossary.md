# Glossar: Natürlichkeits-Check für Wiki.js-Übersetzungen

Referenz für `/wikijs-plugin:translation-check`. Dieses Glossar ist die deterministische
Untergrenze der Prüfung, die Hauptprüfung ist das holistische Lesen (siehe `SKILL.md`). Es ergänzt
die Regel „technische Terme bleiben in beiden Versionen gleich“ aus `DOCS_COMMON.md`.

Eigene Ergänzungen gehören nicht in diese Datei (sie liegt im installierten Plugin und wird beim
Update überschrieben), sondern in `~/.wikijs-plugin/glossary.local.md`. Die lokale Datei nutzt
dieselben Tabellen, bei widersprüchlichen Einträgen gewinnt die lokale.

Nur die Spalte **Falsch (FAIL)** löst einen Fund aus. Was in **Akzeptabel** steht, ist ein
gebräuchlicher Alternativbegriff und kein Fund.

Ein Treffer zählt nur, wenn das Wort als ganzes Wort den Begriff der Zeile übersetzt. „Marke“ im
Sinn von Produktmarke, „Lager“ im Sinn von Lagerbestand oder „Bau“ in „Aufbau“ sind kein Fund.

## 1. IT-Fachbegriffe, die als Lehnwort bleiben

Diese Begriffe sind im deutschen Tech-Sprachgebrauch etabliert. Die wörtliche Übersetzung wirkt
für Entwickler und Admins ungewohnter als das Lehnwort selbst.

| Begriff | Falsch (FAIL) | Akzeptabel (kein Fund) | Richtig |
|---------|---------------|------------------------|---------|
| Cronjob | Kron-Auftrag, zeitgesteuerter Auftrag (durchgängig), Zeitplan-Job | „geplante Aufgabe“ einmalig als Erklärung in Klammern | **Cronjob** |
| Branch | Zweig, Ast | | **Branch** |
| Commit | Einreichung, Festschreibung | | **Commit** |
| Repository | Aufbewahrungsort, Lager | Repo | **Repository** |
| Pull Request | Zugriffsanfrage, Ziehungsantrag | PR | **Pull Request** |
| Merge | Verschmelzung | zusammenführen | **mergen** / **Merge** |
| Deployment | Einsatzbereitstellung, Entfaltung | Deploy | **Deployment** |
| Workaround | | Umgehungslösung | **Workaround** |
| Issue | Angelegenheit | | **Issue** |
| Backend / Frontend | Hintergrundsystem, Vordergrundsystem | | **Backend** / **Frontend** |
| Plugin | Zusatzprogramm | Erweiterung | **Plugin** |
| Skill | Fertigkeit, Fähigkeit | | **Skill** (Claude-Code-Kontext) |
| Token | Marke | | **Token** |
| Cache | Pufferspeicher | Zwischenspeicher (einmalig erklärt) | **Cache** |
| Build | Bau | Erstellung | **Build** |
| Release | | Veröffentlichung | **Release** |
| Feature-Flag | Merkmalsschalter | | **Feature-Flag** |
| Framework | Rahmenwerk | | **Framework** |
| Endpoint | | Endpunkt | **Endpoint** / **Endpunkt** |
| Webhook | Web-Haken | | **Webhook** |
| Queue | | Warteschlange | **Queue** / **Warteschlange** |
| Thread | Faden, Strang | | **Thread** |
| Bug | Wanze, Käfer | Fehler | **Bug** / **Fehler** |
| Hotfix | Sofortkorrektur | | **Hotfix** |
| Fallback | Rückfalloption | | **Fallback** |
| Timeout | | Zeitüberschreitung | **Timeout** |
| Dashboard | Instrumententafel, Armaturenbrett | | **Dashboard** |
| Sidebar | | Seitenleiste | **Sidebar** / **Seitenleiste** |

Plattformbegriffe wie „Scheduled Task“ bleiben so, wie die Oberfläche des dokumentierten Produkts
sie nennt.

## 2. Begriffe mit etablierter deutscher Form

Hier wirkt ein durchgängig unübersetzter Anglizismus im Fließtext unnötig anglisiert.

| Englisch | Falsch (FAIL, im Fließtext) | Richtig |
|----------|-----------------------------|---------|
| Settings | „die Settings konfigurieren“ | **Einstellungen** |
| File | „das File öffnen“ | **Datei** |
| Folder | „der Folder“ | **Ordner** |
| User | „der User klickt“ | **Nutzer** / **Benutzer** / **Anwender** |

Ausnahmen, die kein Fund sind: „User“ in Tabellenköpfen und UI-Strings, die so in der Oberfläche
stehen. „Passwort“ ist bereits Standard, „Kennwort“ wird nicht erzwungen.

## 3. Calque-Satzmuster (wörtliche Satzkonstruktion aus dem Englischen)

Diese Muster entstehen, wenn Satzbau statt Bedeutung übersetzt wird. Sie sind Signale für die
holistische Prüfung, kein Glossar-Treffer. Die Bewertung (WARN oder FAIL) richtet sich nach der
Dichte, siehe `SKILL.md` Schritt 3. Die Anrede (Sie oder Du) folgt der Konvention der geprüften
Seite, die Vorschläge unten stehen der Einfachheit halber in der Sie-Form.

| Calque (wörtlich aus dem Englischen) | Natürliches Deutsch |
|--------------------------------------|---------------------|
| „Das macht Sinn“ | „Das ist sinnvoll“, „Das ergibt Sinn“ |
| „Am Ende des Tages“ | „Letztlich“, „Im Endeffekt“ |
| „X ermöglicht es Ihnen, Y zu tun“ in jedem zweiten Satz | variieren: „Mit X können Sie Y“, „X erlaubt Y“ |
| Passiv-Häufung über mehrere Sätze („wird … gemacht“, „wird … ausgeführt“) | Aktiv: „Sie konfigurieren …“, „Das Plugin führt … aus“ |
| „Sie müssen“, „Sie sollten“, „Sie können“ in jedem Satz | Imperativ für Schritte („Öffnen Sie die Datei“), dazwischen Erklärung ohne Anrede |
| „Bitte stellen Sie sicher, dass …“ vor jedem Hinweis | direkt: „Prüfen Sie …“, oder als Callout-Box |
| Nominalketten wie „Konfigurationsdatei-Bearbeitungs-Workflow“ | „Workflow zum Bearbeiten der Konfigurationsdatei“ |
| Ad-hoc-Bindestrichbildungen mit Anglizismus: „Twig-Shop“, „Löschfrist-Befehl“ | beschreiben: „Shop mit Twig-Storefront“, „Befehl zum Löschen nach Ablauf der Aufbewahrungsfrist“ |
| Aufzählung mit Gedankenstrich statt Satz: „X – durchsuchbar im Admin – mit Löschbefehl“ | ausformulierte Sätze oder eine echte Liste |
| Schachtelsatz in einem Callout (mehrere Nebensätze, mehrere Gedanken) | ein Callout, ein Gedanke, höchstens zwei kurze Sätze |
| „Einsendung“ für eine Kontaktanfrage | „Anfrage“ oder „Nachricht“, so wie der Leser sie nennt |

## 4. Englische Version (EN)

Die EN-Prüfung nutzt nur diese Tabelle plus das holistische Lesen, nicht die Tabellen 1 bis 3.
Funde sind höchstens WARN. Typisch sind Germanismen und falsche Freunde:

| Germanismus / falscher Freund | Natürliches Englisch |
|-------------------------------|----------------------|
| „actual“ im Sinn von „aktuell“ | „current“ |
| „eventually“ im Sinn von „eventuell“ | „possibly“, „if needed“ |
| „become“ im Sinn von „bekommen“ | „get“, „receive“ |
| deutsche Satzstellung mit Verb am Ende („…, which by the plugin used is“) | Verb an der englischen Position |
