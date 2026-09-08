---
title: Stufe 4 · Der Browser-Bau — Ergebnis
description: "Stufe 4: die ganze Kette ohne Server im Browser — was gemessen ist, wie gebaut wird, und was der Bau nicht kann"
audience: developer
status: current
updated: 2026-09-08
---

# Stufe 4 · Der Browser-Bau — Ergebnis

> **Die ganze Kette läuft in der Seite: Foto laden, entzerren, aufbereiten, Zuschnitt
> wählen, maßhaltiges PDF ausgeben — ohne Server, ohne Netz.** Gemessen gegen den
> Desktop-Server auf derselben Szene, und nicht am Protokoll, sondern am Papier: beide
> PDFs bei 600 dpi gerastert und durch den echten Detektor geschickt ergeben dieselben
> Millimeter bis zur letzten Stelle.

> **Stand:** 2026-09-08 · Zweig `feat/web-target` · Belege in `web/`, `tools/build_web.py`

---

## 1 · Die Zahlen nebeneinander

Dieselbe Szene (`shared/fixtures/scenes/flat.png`), dieselbe Anfrage, derselbe
Zuschnitt. Links der Server über seine echten HTTP-Routen, rechts die Seite im
Browser über dieselbe Oberfläche.

| Größe | Server (Python) | Browser (WASM) |
|---|---|---|
| Marker gefunden | 4 (Blatt) | 4 (Blatt) |
| `rms_px` | 0,095 | 0,095 |
| `rms_mm` | 0,0495 | 0,0495 |
| `mm_per_px` | 0,5200 | 0,5200 |
| Seiten im PDF | 29 | 29 |
| Seitengröße | 210,000 × 297,000 mm | 210,000 × 297,000 mm |

Eine der 32 erkannten Eckkoordinaten weicht ab: **1148,049560546875 gegen
1148,0494384765625**. Das ist genau ein float32-ULP — derselbe Unterschied, den
[Stufe 4](stage-4-cross-targets.md) zwischen MSVC und Emscripten gefunden hat, hier
aber durch das Produkt statt durch einen Prüfstand.

### Und die Prüfung, die zählt

Ein gleiches Protokoll ist kein gleiches Werkstück. Beide PDFs wurden deshalb bei
600 dpi gerastert und durch den **echten** ArUco-Detektor geschickt — derselbe Weg,
den `tests/test_markersheet.py` für das Markerblatt geht:

| Gemessen im Ausdruck | Server | Browser | Unterschied |
|---|---|---|---|
| Kante Marker 0 | 67,0561 mm | 67,0561 mm | 0,000 nm |
| Kante Marker 1 | 67,0318 mm | 67,0318 mm | 0,000 nm |
| Kante Marker 2 | 67,0140 mm | 67,0140 mm | 0,000 nm |
| Kante Marker 3 | 66,9928 mm | 66,9928 mm | 0,000 nm |
| Mittelpunktabstand waagerecht | 121,0626 mm | 121,0626 mm | 0,000 nm |
| Mittelpunktabstand senkrecht | 171,0813 mm | 171,0813 mm | 0,000 nm |

Beide liegen dieselben **62,6 µm** bzw. **81,3 µm** neben der Wahrheit (121,0 und
171,0 mm). Das ist der Fehler der Messung selbst und kein Unterschied zwischen den
Zielen.

Was sich **nicht** vergleichen lässt, ist das eingebettete Bildrechteck: reportlab
schneidet das Bild vor dem Einbetten zu, pdf-lib bettet es ganz ein und beschneidet
mit einem Pfad. Wer die Rechtecke nebeneinanderlegt, sieht deshalb Unterschiede von
Zentimetern und misst dabei nichts als zwei Bauweisen. Gemessen wird auf der
gerasterten Seite.

---

## 2 · Was dafür nach C++ musste

Der Auftrag ging davon aus, `core/` messe bereits die ganze Kette. Das war nicht so:
**`core/` konnte `detect_markers`, sonst nichts.** Homographie, Ausgleich,
Kamerazerlegung, Ausdehnung, Entzerrung, Bildaufbereitung und Umrissverfolgung
standen allein in Python — und ein Browser-Bau, der die Messung in JavaScript
nachbaut, wäre eine zweite Fassung der Millimeter gewesen.

Portiert wurden deshalb, jeweils hinter `backend.implementation`:

`homography_from_quad` · `homography_lmeds` · `refine_homography` · `fit_free` ·
`pose_from_homography` · `plane_extent` · `convex_hull` ·
`convex_intersection_area` · `local_px_per_mm` · `quad_area` · `rectify` ·
`output_size` · `adjust` · `find_contour_mm` · `marker_bits`

Der Vergleich beider Kerne auf `shared/fixtures/`, beide Seiten direkt aufgerufen:

| Funktion | größter Unterschied (`flat` / `thick`) |
|---|---|
| `detect_markers` | 0 / 0 |
| `homography_from_quad` | 0 / 0 |
| `homography_lmeds` | 0 / 0 |
| `convex_hull`, `convex_intersection_area`, `output_size` | 0 / 0 |
| `pose_from_homography` (Höhe) | 1,1e-08 mm |
| `plane_extent` | 2,1e-06 mm |
| `local_px_per_mm` | 8,4e-10 px/mm |
| `refine_homography` (scipy gegen `cv::LevMarq`) | 5,6e-08 (Matrixeintrag) |

Nur der nichtlineare Ausgleich verwendet auf beiden Seiten ein **anderes Verfahren**
— `scipy.optimize.least_squares` gegen `cv::LevMarq`. Was das am Werkstück kostet,
steht nicht in der Matrix: eine 500-mm-Kante durch beide Abbildungen geschickt liegt
**1,6e-06 px auseinander, das sind 0,8 Nanometer**. Der Restfehler beider Fassungen
gegen dieselben Messpunkte ist auf fünf Stellen gleich (0,095243 px bzw.
0,095088 px) — keine der beiden ist „besser", sie runden anders.

`tests/test_backend.py` vergleicht weiterhin nur `detect_markers`; das genügt für den
Rest nicht und soll es auch nicht. Die neuen Funktionen sind dadurch belegt, dass die
**ganze** Testsuite zweimal läuft: `ARUCO_CORE=python` und `ARUCO_CORE=cpp`, beide
183 Tests grün. Wer eine Funktion falsch portiert, bricht einen fachlichen Test und
nicht bloß einen Vergleich.

---

## 3 · Wie der Bau entsteht

`./dev.ps1 build-web` ruft `tools/build_web.py`. Zwei Dinge entstehen dabei:

1. **`web/index.html`** aus `app/static/index.html`. Drei Unterschiede, mehr nicht:
   `window.ARUCO_TRANSPORT = "local"`, eine Import-Karte für `pdf-lib`, und die
   absoluten Verweise `/css/…` werden zu `../app/static/css/…`. Die Datei ist
   **erzeugt und nicht eingecheckt** — 352 Zeilen Markup zweimal im Repo laufen
   auseinander, und zwar an der Stelle, an der es niemand merkt.
2. **`dist/web/`** mit `--dist`: der ausgelieferte Bau, 4,5 MB. Er **spiegelt den
   Quellbaum** — dieselben Verzeichnisse an denselben Stellen. Das ist Bedingung und
   nicht Bequemlichkeit: `web/pdf/i18n.js` holt seine Kataloge mit
   `../../app/static/i18n/`, `api.js` den Ortsbetrieb mit `../../../web/vision/`. Wer
   die Tiefe ändert, bricht Importe, die kein Übersetzer prüft.

### Eingecheckt ist genau eines

| Datei | Größe | eingecheckt? |
|---|---|---|
| `web/vendor/core/aruco_core.wasm` | 3 635 422 B | **ja** |
| `web/vendor/core/aruco_core.mjs` | 129 479 B | **ja** |
| `web/vendor/pdf-lib.esm.min.js` | 523 417 B | nein — beim Bauen aus `node_modules/` |
| `web/index.html` | 16 970 B | nein — erzeugt |

Das `wasm` liegt im Repo, weil es das Ergebnis einer Werkzeugkette ist, die niemand
nebenbei nachbaut, und weil ein Auslieferungsstand, dessen **Rechenkern** beim Bauen
frisch entsteht, keiner ist. `pdf-lib` liegt nicht im Repo, weil `package-lock.json`
es bereits auf die Ziffer festnagelt: eine eingecheckte Kopie wäre eine zweite
Fassung derselben Abhängigkeit, frei, von der abzuweichen, die die Node-Tests
benutzen.

Der Browser-Bau ist **nicht** Teil der `.exe`: `aruco-homographie.spec` bündelt
`app/static` und `shared`, sonst nichts.

---

## 4 · Läuft es wirklich ohne Netz?

Ja. Geprüft mit einem Chromium, in dem **jede** HTTP-Anfrage abgebrochen wird, sobald
die Seite steht — auch die an den eigenen Ursprung. Zwei Stufen, weil „offline"
zweierlei heißen kann:

- **Beim Laden** wurde jede Anfrage an einen *fremden* Host abgebrochen. Es gab keine:
  alle **56** Anfragen gingen an den Ursprung, aus dem die Seite kam. Im ganzen
  ausgelieferten Baum steht kein einziger fremder Verweis, der geladen würde — die
  drei Treffer für `bischof-snowboards.com` sind `<a href>` in der Fußzeile, die
  Schrift liegt als `.woff2` daneben.
- **Beim Rechnen** war das Netz restlos aus. Zuschnitt, Reglerwechsel („Kontrast" auf
  +0,30, Vorschau neu entzerrt) und der PDF-Bau liefen danach. Abgewiesen wurde dabei
  **nichts** — es hat gar nichts mehr gefragt: `0` Anfragen zwischen dem Abschalten
  und dem fertigen PDF (29 Seiten, 210,000 × 297,000 mm, als `schablone.pdf`
  heruntergeladen), keine Meldung in der Konsole.

Auch die Messung am Papier oben stammt aus einem solchen Lauf: enger Zuschnitt
(0 / 15 / 210 / 282 mm), Einzelseite, über die echten Bedienfelder eingestellt,
nachdem das Netz aus war.

Was das **nicht** zeigt: die Seite muss von irgendwo kommen. Ein reiner Dateiserver
genügt (`./dev.ps1 start-web`, Vorgabeport 8020); `file://` genügt **nicht**, weil
ES-Module an der Ursprungsprüfung scheitern.

---

## 5 · Die Fallen

- **Emscripten hat keine Speicherbereinigung.** Jede `Mat`, jeder Detektor, jedes
  Rasterbild wird von Hand freigegeben. `web/vision/core.js` ist die einzige Datei,
  die das weiß: `withImage` gibt in einem `finally` frei, `takeRaster` **kopiert** die
  Haldensicht, bevor es löscht — `ALLOW_MEMORY_GROWTH` tauscht den `ArrayBuffer` unter
  jeder Sicht weg, die eine Zuteilung überlebt.
- **EXIF überlebt die Leinwand nicht.** Brennweite und Kameramodell werden aus den
  **Originalbytes** gelesen (`web/vision/exif.js`, nur JPEG), bevor irgendetwas
  dekodiert wird. Ohne sie übernimmt der Weg B aus `camera.py`.
- **`createImageBitmap(file, { imageOrientation: "from-image" })`** ist das Gegenstück
  zu PILs `exif_transpose`. Der Leinwand-Umweg wurde in Stufe 0 mit 0,000 px gemessen.
- **`main.js` hängt seine Zuhörer erst nach `await initI18n()` an.** Wer eine Datei
  vorher in `#file` legt, löst nichts aus — das `change`-Ereignis geht ins Leere und
  die Seite steht still. Das trifft jeden automatisierten Durchlauf.
- **Das Schema am Server ist kein Formalismus, sondern Teil der Schnittstelle.**
  `main.js` schickt Ausrichtung, Druckerrand und Seitenrand *nicht* mit — die füllt
  `app/schemas.py` nach. Im Ortsbetrieb tut das `web/vision/request.js`, und als es
  fehlte, gab es keine Fehlermeldung: `exportOptions` verteilt seine
  Überschreibungen mit `...overrides`, und ein ausdrückliches `undefined`
  **überschreibt die Vorgabe**. Aus dem fehlenden Druckerrand wurde ein NaN, das erst
  zehn Aufrufe später beim Zeichnen des Klebeplans auffiel
  (`options.x must be of type number`). Wer eine zweite Betriebsart baut, spiegelt
  das Schema mit — sonst prüft man einen Weg, den die Bedienung nie geht.
- **Ein Vergleich mit selbstgebautem Aufruf ist kein Vergleich der Bedienung.** Genau
  dieser Fehler blieb verborgen, weil die erste Gegenüberstellung Server und Browser
  mit *demselben, vollständig ausgefüllten* Auftrag fütterte — die Zahlen stimmten,
  und der Knopf war trotzdem kaputt.
- **Der Modul-Zwischenspeicher des Browsers** verbirgt Änderungen an `web/vision/*.js`
  zuverlässig. Beim Prüfen den Zwischenspeicher abschalten.

---

## 6 · Was hier **nicht** gemessen ist

- **Nur Chromium.** Safari und Firefox sind ungeprüft. Der Zuschnitt hängt an
  `createImageBitmap` mit `imageOrientation`, und die PDF-Ausgabe an einem
  Blob-Download — beides ist verbreitet, aber nicht nachgemessen.
- **Kein Telefon.** Der Bau ist für die Werkstatt gedacht; ob ein 168-MPixel-Zuschnitt
  auf einem Mobilbrowser durchläuft, weiß niemand.
- **HEIC** hängt am Browser. Was er nicht dekodiert, kann die Seite nicht messen; der
  Server konnte es über Pillow.
- **Die Wertebereiche des Schemas.** `web/vision/request.js` spiegelt die *Vorgaben*
  aus `app/schemas.py`, nicht die Grenzen (`ge=0.0`, `gt=0.0`). Der Server weist eine
  negative Überlappung mit 422 ab, der Ortsbetrieb nimmt sie an. Die Eingabefelder
  tragen `min`, also ist das über die Bedienung nicht herbeizuführen — aber es ist
  ein Unterschied, und er steht hier, statt unbemerkt zu bleiben.
- **Der Ausdruck.** Wie überall in diesem Repo ist die Maßhaltigkeit bis heute nur
  gegen gerasterte PDFs belegt, nicht gegen Papier und Messschieber.
