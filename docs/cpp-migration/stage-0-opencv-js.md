---
title: Stufe 0 · ArUco mit Subpixel im Browser — Ergebnis
description: Der Vorabversuch, der über den ganzen Umzug entschieden hat: läuft die Markererkennung im Browser, und rechnet sie gleich?
audience: developer
status: current
updated: 2026-09-08
---

# Stufe 0 · ArUco mit Subpixel im Browser — Ergebnis

> **Ja, es geht.** ArUco mit `CORNER_REFINE_SUBPIX` läuft im Browser und liefert
> **dieselben Ecken wie Python — auf ein Millionstel Pixel genau.** Zuversicht: **hoch**,
> weil die Zahlen aus einem echten Chrome kommen und nicht aus einem Bau, der übersetzt.

> **Stand:** 2026-09-08 · Spike, Zweig `spike/opencv-js` · Belege in [`spike/`](../../spike/)

---

## 1 · Die Annahme, auf der Stufe 0 stand, stimmt nicht mehr

Der Fahrplan sagt: *„Der Standardbau von `opencv.js` enthält **kein** `aruco` — das
Modul steckt in `opencv_contrib`."* Das war bis OpenCV 4.6 richtig. **Seit 4.7 ist
ArUco in den Hauptbaum gewandert, in das Modul `objdetect`.**

Das ist keine Spitzfindigkeit, es ist der ganze Unterschied zwischen „tagelanger
Emscripten-Bau mit `OPENCV_EXTRA_MODULES_PATH`" und „ein `npm pack`".

Der Beleg liegt auf beiden Seiten:

- Das **Python-OpenCV 5.0.0 dieses Projekts** baut ausweislich `getBuildInformation()`
  die Module `calib core dnn features flann geometry highgui imgcodecs imgproc
  objdetect photo ptcloud python3 stereo stitching video videoio` — **kein einziges
  contrib-Modul** — und hat trotzdem ein vollständiges `cv2.aruco`.
- Der **WASM-Bau** baut `… imgproc js objdetect …`, ebenfalls ohne contrib, und
  exportiert `aruco_ArucoDetector`, `aruco_DetectorParameters`, `aruco_RefineParameters`,
  `CORNER_REFINE_SUBPIX`, `DICT_4X4_50`, `getPredefinedDictionary`, `generateImageMarker`.

Es war also nie ein contrib-Problem. Es war ein **Bindungs-Problem**: der offizielle
`opencv.js` exportiert die ArUco-Klassen nicht, obwohl der Code mitgebaut wird. Wer
die Whitelist erweitert, bekommt sie — und genau das hat jemand schon getan.

### Was benutzt wurde

**[`@techstark/opencv-js@5.0.0-release.1`](https://www.npmjs.com/package/@techstark/opencv-js)**
— OpenCV **5.0.0**, gebaut am 2026-06-24 mit Emscripten 22.0.0 auf GitHub Actions.

**Dieselbe OpenCV-Hauptversion, die der Desktop heute fährt.** Kein 4.5.3, keine alte
API, kein `DetectorParameters_create`. Der `Hpmason/opencv-contrib-wasm`-Bau aus dem
Auftrag wurde nicht gebraucht und nicht angefasst.

```
npm pack @techstark/opencv-js@5.0.0-release.1
```

Kein Docker (auf dieser Maschine nicht installiert), kein WSL (nicht installiert),
kein emsdk, kein eigener Bau. **Die teuerste Stufe des Fahrplans war ein Download.**

---

## 2 · Die Zahlen

Testbild: `spike/scene.png`, 2400 × 1800, aus `tests/conftest.make_scene()`. Die
Grundwahrheit sind die **projizierten** Markerecken aus `ideal_markers()` — bekannte
Ecken durch die bekannte Homographie, analytisch exakt, nicht erkannt.

Browser und Python bekommen **byteweise dieselben Pixel**: die Graustufen liegen als
rohe `.raw`-Datei vor, damit kein PNG-Dekoder zwischen den beiden Messungen steht.

| Lauf | Python 5.0.0 (nativ) | Browser 5.0.0 (WASM) | |
|---|---|---|---|
| | mean / max px | mean / max px | |
| CLAHE + **Subpixel** | **0,1402 / 0,2337** | **0,1402 / 0,2337** | ✅ |
| Graustufen + Subpixel | 0,1601 / 0,2663 | 0,1601 / 0,2663 | ✅ |
| CLAHE **ohne** Subpixel | 0,5980 / 1,0679 | 0,5980 / 1,0679 | ✅ |
| 12 MP (4000 × 3000), CLAHE + Subpixel | 0,2088 / 0,3382 | 0,2088 / 0,3382 | ✅ |

**Ecke für Ecke** über alle 32 Koordinaten beträgt der größte Unterschied zwischen
nativem und WASM-Lauf **1,2 · 10⁻⁴ px**. Das ist genau ein `float32`-ULP in dieser
Größenordnung — die Ecken kommen auf beiden Seiten als `float32` heraus, und der
letzte Bit rundet unterschiedlich. Praktisch: **identisch.**

Alle 16 Ecken liegen innerhalb von **0,234 px** an der exakten Grundwahrheit. Das
Erfolgskriterium („innerhalb eines Pixels") ist um den Faktor vier unterschritten.

### Wird `CORNER_REFINE_SUBPIX` wirklich ausgeführt?

Ja, und das ist belegt statt behauptet. Die Zeile **ohne** Subpixel ist um den
Faktor **4,3 schlechter** (0,598 statt 0,140 px) — und zwar im Browser genauso wie in
Python. Ein still ignoriertes Flag hätte beide Zeilen gleich aussehen lassen.
Zusätzlich wurden die gesetzten Parameter aus dem Objekt **zurückgelesen**
(`cornerRefinementMethod: 1`, `WinSize: 5`, `MaxIterations: 50`, `MinAccuracy: 0.01`) —
sie kommen an, sie werden nicht verworfen.

`generateImageMarker(dict, 0, 120, borderBits=1)` liefert in beiden Welten dieselbe
Prüfsumme **816000**. Der Markerbogen ließe sich im Browser erzeugen.

---

## 3 · Größe und Geschwindigkeit

| | |
|---|---|
| `opencv.js` roh | **13,3 MB** (13 298 869 B) |
| gzip -9 | **3,75 MB** |
| brotli -q11 | **2,67 MB** |
| separate `.wasm` | **keine** — das Modul steckt als Zeichenkette in der JS-Datei (`findWasmBinary(){return binaryDecode('\0asm…')}`) |
| Laufzeit bis einsatzbereit | **111 ms** |

Eine Datei, ein Abruf, nichts nachzuladen. Über Brotli sind es **2,7 MB** — für eine
Anwendung, die man einmal öffnet und dann benutzt, vertretbar; für „mal eben im
Mobilfunknetz" spürbar. Ein eigener Bau mit engerer Modul-Whitelist (`dnn`, `photo`,
`stereo`, `video`, `ptcloud` werden hier nicht gebraucht) würde das deutlich drücken —
falls es je stört.

**Rechenzeit** (bester von mehreren Läufen, warm; Chrome 152, 8 Kerne):

| Bild | Python nativ | Browser WASM | Faktor |
|---|---:|---:|---:|
| 2400 × 1800 (4,3 MP) | 50 ms | 190 ms | 3,8 × |
| 4000 × 3000 (12 MP) | 140 ms | 798 ms | 5,7 × |

Der erste Lauf im Browser dauert **548 ms** statt 190 — das ist JIT-Aufwärmen, nicht
die Dauerleistung. Für ein Handyfoto heißt das **unter einer Sekunde** für die
Erkennung. Das ist für diese Anwendung unkritisch: der Benutzer fotografiert, wartet
kurz, bekommt ein PDF.

Warum überhaupt langsamer: der Bau meldet `Parallel framework: none` und eine **leere
SIMD-Baseline**. Er rechnet einkernig und skalar, während das native OpenCV acht
Threads und AVX benutzt. Der Browser *kann* WASM-SIMD (geprüft: `WebAssembly.validate`
sagt ja) — dieser Bau nutzt es nur nicht. Da liegt Reserve, falls sie je gebraucht wird.

---

## 4 · Die Fallen, die Zeit gekostet haben

Alle vier haben zugeschlagen. Wer das nachbaut, spart sich damit einen Nachmittag.

**1 · `Module.onRuntimeInitialized` feuert nie.** Dieser Bau ist `MODULARIZE`:
`window.cv` ist ein **Promise**, kein fertiges Modul. Das überall dokumentierte
Muster läuft ins Leere — ohne Fehlermeldung, die Seite bleibt einfach stehen. Richtig:

```js
window.cv = await window.cv;
```

**2 · Die Namen sind flach, nicht verschachtelt.** Es gibt kein `cv.aruco.*`. Der
Bindungsgenerator faltet den Namensraum in einen Unterstrich, Konstanten wandern nach
oben:

| Python | opencv.js |
|---|---|
| `cv2.aruco.ArucoDetector` | `cv.aruco_ArucoDetector` |
| `cv2.aruco.DetectorParameters()` | `new cv.aruco_DetectorParameters()` |
| `cv2.aruco.CORNER_REFINE_SUBPIX` | `cv.CORNER_REFINE_SUBPIX` |
| `cv2.aruco.DICT_4X4_50` | `cv.DICT_4X4_50` |

**3 · `new cv.aruco_Dictionary(cv.DICT_4X4_50)` wirft.**

```
BindingError: Tried to invoke ctor of aruco_Dictionary with invalid number of
parameters (1) - expected (0,3) parameters instead!
```

Der Weg ist derselbe wie in Python: `cv.getPredefinedDictionary(cv.DICT_4X4_50)`.

**4 · `cv.createCLAHE` gibt es nicht.**

```
TypeError: cv.createCLAHE is not a function
```

In opencv.js existiert nur die Klasse: `new cv.CLAHE(2.0, new cv.Size(8, 8))`.

**Und immer:** jedes `Mat`, jeder Detektor, jedes Parameterobjekt muss von Hand
`.delete()`-t werden. Emscripten hat keinen Sammler. In einer Schleife über Fotos ist
das der Unterschied zwischen „läuft" und „Tab stürzt ab".

---

## 5 · Zwei Befunde, die den C++-Kern betreffen

Diese beiden gehören **jetzt** in die Planung von Stufe 2, nicht in Woche 8.

### `imgcodecs` ist im WASM-Bau abgeschaltet

```
Disabled:  highgui imgcodecs stitching videoio world
```

Damit gibt es im Browser **kein `imdecode`, `imencode`, `imwrite`** (nachgeprüft: alle
`undefined`). Nur `cv.imread(canvasElement)` und `cv.matFromImageData` — beides
JS-Zutaten, die über den Browser-Dekoder gehen, nicht über OpenCV.

**Folge für `core/`:** der gemeinsame C++-Kern **darf `cv::imread`/`cv::imwrite` nicht
anfassen.** Er muss einen rohen Pixelpuffer plus Maße entgegennehmen und einen solchen
zurückgeben; das Dekodieren und Kodieren gehört auf jedes Ziel einzeln (Browser:
Canvas, Windows/Android: das jeweilige native OpenCV oder die Plattform).

Heute nutzt Python `cv2.imread`/`imwrite` nur in `pipeline.py:126` und `session.py:45`
— beides Vorschau-Dateien auf dem Server, nicht die Messung. Der Messkern ist also
schon sauber. **Das muss er bleiben.**

Nebenbei belegt: der Weg über den Canvas ist unbedenklich. Dieselbe Szene über
`<img>` → Canvas → `cv.imread()` geliefert ergibt Ecken mit Abweichung **0,000 px**
gegenüber den rohen Bytes. Der Browser-PNG-Dekoder verfälscht nichts.

### EXIF kommt nicht aus OpenCV — und im Browser aus gar nichts

Die Brennweite (`focal35_mm`, `app/vision/camera.py`, Weg A) und die Bildorientierung
liest heute **PIL**, nicht OpenCV (`app/vision/detect.py:67-70`,
`ImageOps.exif_transpose`). Im Browser gibt es beides nicht: der Canvas wendet die
Orientierung zwar an, wirft die Metadaten aber weg.

Also braucht das Web-Ziel einen **eigenen JS-EXIF-Leser**. Kein Beinbruch — `camera.py`
kennt bereits `source: "exif" | "manual" | "none"` und fällt sauber auf die manuelle
Eingabe zurück. Aber es ist ein Stück Arbeit, das im Fahrplan noch nirgends steht.

---

## 6 · Was das für den Fahrplan heißt

**Das erste Risiko aus §7 — *„`opencv.js` mit `aruco` lässt sich nicht bauen"* — ist
erledigt.** Es lässt sich nicht nur bauen, es ist schon gebaut, in derselben Version
wie der Desktop, und misst identisch. Der 6–10-Wochen-Plan behält seine Form; der
Browser ist ein Ziel und keine Hoffnung mehr.

Die Tabelle in §2 des Fahrplans („`opencv.js` (WASM) — die echte, überall") stimmt
also. Der Absatz zu Stufe 0 beschreibt allerdings eine Welt vor OpenCV 4.7 und sollte
korrigiert werden, damit niemand später einen contrib-Bau anwirft, den es nicht braucht.

**Was an die Stelle des erledigten Risikos tritt** — kleiner, aber nicht null:

- **Fremde Abhängigkeit — kleiner als hier zuerst stand.** `@techstark/opencv-js` ist
  der Bau *einer* Person, und dieser Absatz nannte das zunächst das verbleibende
  Hauptrisiko. **Das war zu hoch gegriffen:** der **offizielle** `opencv.js` von
  `docs.opencv.org/4.x/opencv.js` exportiert den vollen ArUco-Satz ebenfalls
  (`aruco_ArucoDetector`, `aruco_DetectorParameters`, `aruco_RefineParameters`,
  `getPredefinedDictionary`, `CORNER_REFINE_SUBPIX`, `DICT_4X4_50`). Es gibt also einen
  Rückfallweg, und er ist offiziell.

  **Wie das beinahe falsch hier gelandet wäre**, weil die Falle jeden trifft, der es
  nachprüft: eine Suche nach diesen Namen **in der Datei** findet null Treffer — die
  offiziellen Bauten legen ihr wasm als **base64** ab, also steht dort keine einzige
  Symbolzeichenkette. Auch `findHomography` findet man so nicht. Wer daraus schließt,
  ArUco fehle, schließt falsch; geladen und abgefragt ist es da. Der Kanarienvogel ist,
  nach einem Namen zu suchen, der ganz sicher enthalten sein *muss* — fehlt der auch,
  liegt es am Verfahren und nicht am Bau.

  **`@techstark` bleibt trotzdem die richtige Vorgabe**, aber aus einem anderen Grund als
  „es gibt nichts anderes": es ist **5.0.0** und damit dieselbe Hauptfassung wie der
  Desktop, während der offizielle Bau **4.13.0** ist. (Auch `docs.opencv.org/5.x/opencv.js`
  meldet `4.13.0-1274-g6a1a2754c8` — ein 4.13-Zwischenstand, kein OpenCV 5.)

  **Ungeprüft geblieben:** dass der offizielle Bau auch wirklich *erkennt*. Belegt ist
  nur, dass er die Bindungen führt und meldet; ein Durchlauf kam nicht zustande. Der
  Browser-Beleg oben ruht also weiterhin allein auf `@techstark` 5.0.0.

  Fällt beides weg, bleibt der normale Emscripten-Bau des **Hauptbaums** (kein contrib!)
  mit erweiterter Whitelist in `platforms/js/opencv_js.config.py` — unangenehm, aber
  weder exotisch noch riskant. Für einen Auslieferungsstand gehört die Datei ohnehin
  **eingefroren und mitgeliefert**, nicht bei jedem Bau frisch aus npm gezogen.
- **2,7 MB Brotli** liegen vor der ersten Messung. Eine engere Whitelist drückt das,
  falls es stört.
- **Einkernig und ohne SIMD.** Reicht heute. Wenn es je klemmt, gibt es zwei bekannte
  Hebel, bevor irgendetwas umgeschrieben werden muss.

---

## 6a · Symbolabgleich: was im WASM-Bau fehlt — und für wen

Nachgezählt: von den **50** `cv2.*`-Symbolen, die `app/` benutzt, sind **46** im
WASM-Bau vorhanden. Die vier fehlenden, und warum keines davon Millimeter kostet:

| fehlt | benutzt in | Bewertung |
|---|---|---|
| `imwrite`, `IMWRITE_JPEG_QUALITY` | `pipeline.py`, `session.py` | erwartet — `imgcodecs` ist aus. **Nur Vorschaudateien**, nicht die Messung. |
| `COLOR_BGR2LAB`, `COLOR_LAB2BGR` | `enhance.py:191,197` | ein Modul, dessen eigener Kopf **„KOSMETISCH, NIE GEOMETRISCH"** sagt (Invariante 6). **Kann die Messung nicht anfassen.** |

Ebenfalls **nicht** an der JS-Oberfläche: `cornerSubPix`, `calibrateCamera`,
`undistortPoints`, `LMSolver`, `estimatePoseSingleMarkers`. Vorhanden: `solvePnP`,
`solvePnPRansac`, `solvePnPRefineLM`, `Rodrigues`, `projectPoints`, `findHomography`,
`warpPerspective`.

### Die Unterscheidung, auf die es ankommt

**Diese Abwesenheiten binden nur, was *JavaScript* aufrufen kann.** Der C++-Kern wird
**in** das wasm hineinübersetzt und bindet gegen `imgproc` und `calib` — beide sind
gebaut. `cv::LevMarq` und `cv::cornerSubPix` stehen ihm also zur Verfügung, auf allen
drei Zielen.

**Berichtigung zum Namen.** Hier stand zuerst `cv::LMSolver`. Diesen Namen gibt es
in OpenCV 5.0.0 **nicht** — nachgemessen am SDK dieses Projekts: keine einzige
Fundstelle, auch nicht ohne Rücksicht auf Groß- und Kleinschreibung. Bis OpenCV 4
hieß die Klasse so und lag in `calib3d`; in 5.0.0 heißt sie **`cv::LevMarq`** und
steht in `opencv2/geometry/3d.hpp:512`. Der Weg ist offen, der Name war falsch —
abgeleitet aus einer Symbolliste, statt im Kopf-Verzeichnis nachgeschlagen.

**Und eine Verschiebung, die daran hängt:** `cv::contourArea` ist von `imgproc` in
das neue Modul **`geometry`** gewandert (`opencv2/geometry/2d.hpp`). Zusammen mit
`LevMarq` heißt das: **`geometry` muss auf jede WASM-Modul-Whitelist** — sonst
fehlen beide Hälften der Messung.

Das ist für Stufe 2 unmittelbar wichtig: der Fahrplan ersetzt
`scipy.optimize.least_squares` durch `cv::LevMarq`, und dieser Weg ist damit offen.

**Die echte Schranke bleibt das abgeschaltete Modul:** `imgcodecs` ist gar nicht erst
gelinkt. `cv::imread`/`imwrite` fehlen deshalb **auch dem C++-Kern**, nicht nur
JavaScript. Der Kern bleibt auf rohen Pixelpuffern.

### Eine Falle, die still zuschlägt

**Die Typkennungen haben sich zwischen OpenCV 4.x und 5.0.0 geändert:**

```
CV_32FC2 : 37 in 5.0.0, aber 13 in 4.x
CV_8UC3  : 64 in 5.0.0, aber 16 in 4.x
```

Die Datenanordnung ist unverändert — nur die Zahlen sind gewandert. Wer `mat.type()`
gegen eine **Zahl** vergleicht statt gegen das Makro, verzweigt beim Übersetzen gegen
eine andere OpenCV-Fassung falsch. Ohne Fehlermeldung. Und genau das tut Stufe 4, wenn
derselbe Quelltext für Android und WASM übersetzt wird.

**Also nur die benannten Makros, nie eine nackte Zahl** — in der Bibliothek wie im
Konformitätstest.

---

## 7 · Was dieser Spike **nicht** zeigt

Damit niemand mehr hineinliest, als drinsteht:

- Gemessen wurde gegen eine **synthetische Szene**, nicht gegen ein echtes Foto. Genau
  wie die Python-Suite. Der Messschieber-Beleg (100 mm = 100 mm) hängt weiterhin an
  der Python-Kette; die Browser-Kette erbt ihn erst, wenn sie ganz steht.
- Geprüft wurde **nur die Erkennung**. Homographie, Kamerazerlegung,
  Dickenkorrektur, `least_squares` → `cv::LevMarq` — alles ungeprüft. Der Spike hat
  die Frage beantwortet, die gestellt war, und keine weitere.
- Ein **Browser**, ein Gerät: Chrome 152 auf Windows 11. Safari und Android-Chrome sind
  nicht angefasst. Bei einer reinen WASM-Rechnung ohne Threads und ohne SIMD ist wenig
  zu erwarten, aber „wenig zu erwarten" ist keine Messung.
- **Nicht gemessen:** Speicherbedarf bei 12 MP, und ob ein Handy mit wenig RAM den
  13-MB-Bau plus mehrere Vollbild-`Mat`s verträgt.

---

## 8 · Nachvollziehen

```powershell
# 1 · Testbilder und Python-Vergleichswerte erzeugen (schreibt nach spike/)
python spike/make_scene.py

# 2 · Den Bau holen und alles in ein Verzeichnis legen
npm pack @techstark/opencv-js@5.0.0-release.1
tar xzf techstark-opencv-js-5.0.0-release.1.tgz
copy package\dist\opencv.js <serve>\
copy spike\index.html spike\scene.png spike\*-truth.json spike\*.raw <serve>\

# 3 · Ausliefern und im Browser oeffnen
python -m http.server 8731 --bind 127.0.0.1
#    -> http://127.0.0.1:8731/index.html   (Ergebnis steht auf der Seite und in window.SPIKE)
```

Die `.raw`-Dateien sind zusammen 16 MB und **nicht eingecheckt** (`.gitignore`);
`make_scene.py` stellt sie her. Der 13-MB-`opencv.js` ist ebenfalls nicht eingecheckt —
er kommt aus npm.

**Belege im Zweig:**

| Datei | was drinsteht |
|---|---|
| `spike/make_scene.py` | erzeugt Szenen, Grundwahrheit und die Python-Vergleichswerte |
| `spike/index.html` | die Browser-Messung, die alle Zahlen oben erzeugt hat |
| `spike/python-baseline.json` | Python: Ecken und Fehler je Marker |
| `spike/browser-results.json` | Browser: Ecken, Fehler, Zeiten, Bindungsliste |
| `spike/opencv-build-info.txt` | vollständiges `getBuildInformation()` des WASM-Baus |
| `spike/scene*.png`, `spike/scene*-truth.json` | die Szenen und ihre exakten Ecken |
