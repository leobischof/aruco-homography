# Stufe 3: Der PDF-Bau nach JavaScript

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Ziel:** `app/pdf/` (~960 Zeilen ReportLab) als JavaScript-Modul in `web/pdf/`, damit
**ein** PDF-Bau alle drei Ziele bedient — Windows, Android und Browser.

**Warum nicht C++:** ReportLab gibt es auf Android nicht, und ein C++-PDF-Bau (libharu,
PoDoFo) wäre derselbe Neuschrieb, hülfe dem Browser-Ziel aber nicht und verschöbe
Schrifteinbettung und SVG-Zeichnen nach C++ — genau das, was ReportLab und svglib heute
umsonst erledigen. JavaScript deckt alle drei auf einmal ab, und die Oberfläche, in der
es wohnen wird, ist schon geschrieben und schon portabel.

**Tech Stack:** Node 22+, `pdf-lib`, `@pdf-lib/fontkit` (Schrifteinbettung), reines ESM
ohne Bündler — wie der Rest der Oberfläche.

## Global Constraints

- **Invariante 1:** Das entzerrte Bild belegt auf der Seite **exakt** `crop_w × crop_h`
  Millimeter. Der Streifen darunter vergrößert die *Seite*, nie das *Bild*.
- **Invariante 2:** Es wird nichts hochgerechnet.
- **Invariante 3:** Logo und „Made with Bischof Snowboards Software" stehen auf **jedem**
  Blatt — Einzelseite, jede Kachel, Klebeplan, Markerblatt. Maßstab und Fußzeile sind
  abschaltbar, diese beiden nicht.
- **Invariante 7:** Jede sichtbare Zeichenkette kommt aus dem Katalog.
- **Konstanten aus `shared/constants.json`.** JavaScript liest die Datei direkt — kein
  Abtippen, keine zweite Fassung.
- Genauigkeit: 1 mm = 2,834645669 pt. Die Prüfung verlangt **< 0,01 mm** — das sind
  0,028 pt, weit über der Auflösung von `double`.
- Git: PRs zielen auf `develop`. Autor `Leo Bischof <leo@bischof-snowboards.com>`.

---

## Wie belegt wird, dass der neue Bau dasselbe liefert

**Wieder keine zweite Testsuite.** Die vorhandenen **33** PDF-Tests
(`test_pdf_size.py` 6, `test_branding.py` 9, `test_layout.py` 11,
`test_markersheet.py` 7) lesen das fertige PDF mit `pypdf`/`pymupdf` zurück und prüfen
die Geometrie. Sie interessiert **nicht**, wer das PDF gebaut hat.

```
ARUCO_PDF=python  (Vorgabe)  ->  app/pdf/          ReportLab, wie bisher
ARUCO_PDF=js                 ->  web/pdf/          ueber node
```

Bei `js` ruft `app/pdf/build.py` Node auf, übergibt Bild und Geometrie und bekommt die
PDF-Bytes zurück. **Dieselben 33 Prüfungen, derselbe Maßstab.**

Das ist bewusst der Weg über den Umweg: Node aus Python heraus aufzurufen ist im
Auslieferungsbetrieb *nicht* gewollt (dort baut die Oberfläche das PDF selbst). Es ist
ein **Prüfstand**, und er erlaubt, den neuen Bau gegen genau die Zusicherungen zu
messen, die der alte erfüllt — bevor irgendetwas umgestellt wird.

`.\dev.ps1 run-tests-pdf-js` fährt die Suite so.

---

## `web/pdf/` — Aufbau

Spiegelt `app/pdf/` bewusst Modul für Modul. Wer den einen Satz Dateien kennt, findet
sich im anderen zurecht, und ein Unterschied fällt beim Nebeneinanderlegen auf.

```
web/pdf/
├─ constants.js     # laedt shared/constants.json
├─ units.js         # mm <-> pt, EINE Stelle
├─ layout.js        # <- app/pdf/layout.py    (Rect, PageLayout, Tile, TileLayout)
├─ branding.js      # <- app/pdf/branding.py  (Logo, Markenblock, Verlinkung)
├─ overlays.js      # <- app/pdf/overlays.py  (Streifen, Massstab, Raster, Kontur)
├─ markersheet.js   # <- app/pdf/markersheet.py
├─ build.js         # <- app/pdf/build.py     (Einzelseite, Kacheln, Klebeplan)
└─ assets/
   ├─ montserrat.js # Schrift als base64 — im Browser gibt es kein Dateisystem
   └─ logo.js       # das Logo als Pfaddaten, nicht als SVG-Datei
```

**Zu `assets/`:** im Browser gibt es keinen Dateizugriff. Schrift und Logo müssen
**im Modul** liegen. `svglib` rendert heute die SVG-Datei; in JavaScript wird der
Logo-Pfad einmal aus `logo-dark.svg` extrahiert und als Pfaddaten hinterlegt — das Logo
ist eine feste Zeichnung, keine wechselnde Eingabe.

---

## Aufgabe 1: Einheiten, Konstanten, Layout — die Rechnung ohne Zeichnen

**Files:** `web/pdf/{units,constants,layout}.js`, `web/pdf/layout.test.mjs`

Reine Rechnung, kein PDF. `app/pdf/layout.py` ist frei von ReportLab und lässt sich
Zeile für Zeile übertragen — deshalb zuerst: es ist die Hälfte des Risikos ohne die
Hälfte der Werkzeuge.

`tests/test_layout.py` (11 Prüfungen) ist die Vorlage; dieselben Fälle in Node
nachziehen, mit denselben Zahlen. Erst wenn Kachelzahl, Überlappung und Abdeckung
stimmen, lohnt sich eine einzige Zeile `pdf-lib`.

- [ ] Schritt 1: `units.js` — `mmToPt`, `ptToMm`, und **nichts sonst**
- [ ] Schritt 2: `constants.js` — lädt `shared/constants.json`
- [ ] Schritt 3: `layout.js` portieren
- [ ] Schritt 4: `node --test web/pdf/layout.test.mjs`, die 11 Fälle nachgestellt
- [ ] Schritt 5: Commit

## Aufgabe 2: Eine Seite, exakt vermessen

**Files:** `web/pdf/{branding,overlays,build}.js`, `web/pdf/assets/*`, `tools/pdf_js_bridge.py`

Die Einzelseite mit Bild, Streifen, Maßstab, Raster und Markenblock — und der Brücke,
über die die Python-Tests sie prüfen.

**Der kritische Punkt ist Invariante 1.** Das Bild muss `crop_w × crop_h` mm belegen,
auf 0,01 mm. `pdf-lib` setzt die MediaBox in Punkt; die Umrechnung geht durch
`units.js` und nirgends sonst.

- [ ] Schritt 1: Schrift und Logo nach `assets/` überführen, Aussehen gegen ein
      ReportLab-PDF prüfen (beide rendern, PNG vergleichen, **ansehen**)
- [ ] Schritt 2: `branding.js` — Invariante 3 ist hier zu Hause
- [ ] Schritt 3: `overlays.js`
- [ ] Schritt 4: `build.js`, Einzelseite
- [ ] Schritt 5: `tools/pdf_js_bridge.py` + `ARUCO_PDF` in `app/pdf/build.py`
- [ ] Schritt 6: `ARUCO_PDF=js` gegen `test_pdf_size.py` und `test_branding.py`
- [ ] Schritt 7: Commit

## Aufgabe 3: Kacheln und Klebeplan

**Files:** `web/pdf/build.js` (erweitert)

- [ ] Schritt 1: Kachelung mit Überlappung
- [ ] Schritt 2: Klebeplan als erste Seite
- [ ] Schritt 3: **Invariante 3 auf jeder Kachel** — `test_branding.py` prüft genau das
- [ ] Schritt 4: `ARUCO_PDF=js` gegen alle 33
- [ ] Schritt 5: Commit

## Aufgabe 4: Markerblatt

**Files:** `web/pdf/markersheet.js`

Die Marker selbst muss JavaScript zeichnen können. Stufe 0 hat belegt, dass
`generateImageMarker` im WASM-Bau vorhanden ist und dieselbe Prüfsumme liefert
(**816000**) — der Weg steht also offen.

- [ ] Schritt 1: Marker über `opencv.js` erzeugen
- [ ] Schritt 2: Blatt setzen, Anleitung, Kontrollmaßstab
- [ ] Schritt 3: `test_markersheet.py` (7) gegen den JS-Bau — **einschließlich** der
      Prüfung, die das erzeugte Blatt rastert und durch den echten Detektor schickt
- [ ] Schritt 4: Commit

---

## Fertig, wenn

- Alle **33** PDF-Prüfungen sind mit `ARUCO_PDF=js` grün, mit denselben Toleranzen.
- Ein JS-PDF und ein ReportLab-PDF derselben Eingabe wurden **nebeneinander angesehen**
  (nicht nur vermessen) und unterscheiden sich nicht sichtbar.
- `web/pdf/` hängt an keiner Node-eigenen Zutat, die es im Browser nicht gibt —
  kein `fs`, kein `path` im Bau-Pfad. Der Prüfstand darf beides, das Modul nicht.
