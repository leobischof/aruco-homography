# Umzug auf einen C++-Rechenkern — Fahrplan

> **Stand:** 2026-09-07 · **Entschieden**, noch nicht begonnen.
> Die ausführbaren Pläne je Stufe liegen in [`docs/superpowers/plans/`](../superpowers/plans/).

Dieses Verzeichnis hält den *Warum*-Teil fest: was entschieden wurde, woraufhin, und
was den Umzug scheitern lassen würde. Die Schritt-für-Schritt-Anleitungen stehen
woanders — ein Fahrplan, der auch die Handgriffe enthält, wird von niemandem gelesen.

---

## 1 · Was den Ausschlag gegeben hat

Zwei Tatsachen, beide neu, beide vom Auftraggeber:

**Das Handy muss allein rechnen.** Ohne PC, ohne WLAN. Damit ist der Weg, der bis
hierher getragen hat — Python auf dem Rechner, Handy als Kamera und Anzeige — am Ende.
Er war nie falsch, er reicht nur für diese Anforderung nicht.

**Die Maßhaltigkeit ist am echten Ausdruck bestätigt.** `100 mm = 100 mm`, mit dem
Messschieber am gedruckten Kontrollmaßstab gemessen. Das ist der Satz, auf den dieses
Projekt seit dem ersten Tag gewartet hat: die zentrale Behauptung ist nicht mehr nur
gegen synthetische Szenen belegt, sondern gegen ein Lineal.

Die Reihenfolge war Glück oder Verstand, jedenfalls ist sie die richtige: **es gibt
jetzt eine geprüfte Referenz, gegen die portiert werden kann.** Wer eine Messung
portiert, die nie an der Wirklichkeit geprüft wurde, hat hinterher zwei
Implementierungen, von denen keine belegt ist, und keine Möglichkeit zu entscheiden,
welche recht hat, wenn sie sich widersprechen.

---

## 2 · Warum C++ und nicht Rust

Nicht wegen der Sprache. Wegen **einer** Abhängigkeit.

Der Rechenkern hängt an der ArUco-Erkennung **mit Subpixel-Verfeinerung**
(`app/vision/detect.py`, `CORNER_REFINE_SUBPIX`). Diese Subpixel *sind* die
Millimeter. Die Frage an jede Sprache lautet deshalb nur: gibt es dort eine
vertrauenswürdige ArUco-Implementierung — für **alle drei** Ziele?

| Weg | Windows | Android | Web | ArUco |
|---|---|---|---|---|
| **C++ + OpenCV** | nativ | offizielles Android-SDK | `opencv.js` (WASM) | **die echte, überall** |
| Rust + Tauri v2 | nativ | NDK | WASM | **muss nachgebaut werden** |
| Kotlin Multiplatform | JVM | nativ | schwach | Bindings je Ziel |
| Flutter / Dart | ok | ok | schwach | kein OpenCV, FFI je Plattform |
| C# / MAUI | gut | gut | — | OpenCvSharp, Desktop-lastig |

Rust ist die angenehmere Sprache und Tauri v2 die angenehmere Hülle. Aber
`opencv-rust` bindet an das **native** OpenCV und nimmt damit das WASM-Ziel wieder
weg. Rust hieße: ArUco-Detektor und Levenberg-Marquardt selbst schreiben. Das ist
die teure Sorte Risiko — es stürzte nicht ab, es wäre nur still um einen
Zehntelmillimeter daneben.

**C++ ist die einzige Wahl, bei der auf allen drei Zielen dieselbe, erprobte
Messtechnik läuft.** OpenCV *ist* C++; die anderen Wege binden es an oder bauen es nach.

---

## 3 · Wie die Architektur aussieht

```
                 ┌──────────────────────────────┐
                 │  shared/  — eine Wahrheit    │
                 │  constants.json · fixtures/  │
                 └──────────────────────────────┘
                     │            │           │
        ┌────────────┘            │           └────────────┐
        ▼                         ▼                        ▼
┌───────────────┐        ┌────────────────┐       ┌────────────────┐
│  core/  C++   │        │  web/  JS      │       │  py/  Python   │
│  Sehen:       │        │  Oberfläche,   │       │  geprüfte      │
│  erkennen,    │        │  Layout,       │       │  Referenz-     │
│  lösen,       │        │  Kachelung,    │       │  implementier. │
│  entzerren,   │        │  PDF, Marke    │       │  + Desktop-    │
│  aufbereiten  │        │                │       │    server      │
└───────────────┘        └────────────────┘       └────────────────┘
        │                         │
   ┌────┴────┬──────────┐         │
   ▼         ▼          ▼         ▼
Windows   Android     WASM    alle drei Hüllen
(nativ)   (NDK)   (Emscripten)
```

**Der Kern rechnet, die Oberfläche gestaltet.** Genau eine Grenze, und sie liegt da,
wo sie hingehört: C++ liefert das entzerrte Bild und die Geometrie, alles danach —
Layout, Kachelung, Maßstab, Markenstreifen, PDF — passiert in JavaScript, einmal
geschrieben, auf allen Zielen gleich.

### Was wohin geht

| heute | Zeilen | Ziel | warum |
|---|---:|---|---|
| `app/vision/` | ~1 020 | **C++** | muss auf Android und im Browser laufen |
| `app/pdf/` | ~960 | **JavaScript** | ReportLab gibt es auf Android nicht |
| `app/static/` | 1 753 | **bleibt** | schon portabel, kein Bauschritt |
| `app/main.py`, `session.py` | ~330 | bleibt Python | nur Desktop-Server |

### Entscheidungen, die schon gefallen sind

- **Ein Repo, kein zweites.** Die Grundwahrheiten dürfen nicht kopiert werden. Zwei
  Implementierungen derselben Homographie driften, und sie driften in Millimetern.
  Getrennte Repos hießen Submodul (Mühsal) oder doppelte Fixtures (Drift, an der
  einen Stelle, an der man ihn sich nicht leisten kann).
- **PDF nach JavaScript**, nicht nach C++. Einmal geschrieben, alle drei Ziele.
  `pdf-lib` setzt Seitenboxen exakt genug (0,01 mm ≈ 0,028 pt, weit über der
  Float-Grenze). Preis: die Invarianten 1, 2 und 3 wohnen in diesem Code und müssen
  neu belegt werden; `test_pdf_size.py` und `test_branding.py` ziehen mit um.
- **Python bleibt** — als *geprüfte Referenz*, nicht als Altlast. Es ist die einzige
  Implementierung, die je an einem Lineal gemessen wurde. Jede künftige Änderung am
  C++-Kern wird gegen sie belegt.
- **Ziele:** Windows-`.exe`, Android-`.apk` (erst Seitenladen, später eventuell Play
  Store), Browser. **Kein iOS** — nicht verlangt, und die Hüllenwahl bliebe offen.

---

## 4 · Was Drift verhindert

Das ist der Teil, an dem dieses Vorhaben scheitern oder gelingen wird.

**Keine zweite Testsuite.** Der C++-Kern bekommt eine `pybind11`-Bindung, und die
**vorhandenen Tests laufen gegen ihn**. Dieselben Tests, dieselben Fixtures,
dieselben Toleranzen — getauscht wird nur, was hinter `app/vision/` steckt.

Ein C++-Kern, der die Python-Suite unverändert besteht, ist belegte Übereinstimmung,
keine erhoffte. Und man hat sie, **bevor** eine Zeile Android oder WASM geschrieben ist.

**Die Fixtures messen gegen die Grundwahrheit, nicht gegeneinander.** Die
eingefrorenen Szenen tragen die Werte, aus denen sie *gebaut* wurden — nicht das, was
Python herausbekommt. Sonst erbte C++ jede Schiefe von Python und niemand sähe es.

---

## 5 · Die Stufen

Jede Stufe liefert etwas, das für sich funktioniert und geprüft werden kann. Keine
Stufe lässt den ausgelieferten Stand kaputt zurück.

### Stufe 0 · ✅ ERLEDIGT — ArUco mit Subpixel läuft im Browser

**Ergebnis: [`stage-0-opencv-js.md`](stage-0-opencv-js.md).** Der Browser findet
dieselben Ecken wie Python, auf **ein Millionstel Pixel** genau (größter Unterschied
1,2 · 10⁻⁴ px = ein `float32`-ULP). `CORNER_REFINE_SUBPIX` wird wirklich ausgeführt,
belegt dadurch, dass es ohne den Schalter **4,3-mal** schlechter wird — im Browser wie
in Python.

**Die Annahme, auf der diese Stufe stand, war falsch, und zwar zugunsten des Projekts.**
Hier stand, `aruco` stecke in `opencv_contrib` und brauche einen fummeligen eigenen
Emscripten-Bau. Das galt bis OpenCV 4.6. **Seit 4.7 liegt ArUco im Hauptbaum, im Modul
`objdetect`** — nachgeprüft an beiden Enden: das OpenCV 5.0.0 dieses Projekts baut
`… objdetect …` und **kein einziges** contrib-Modul, hat aber ein vollständiges
`cv2.aruco`.

Es war nie ein contrib-Problem, sondern ein **Bindungs**-Problem: der offizielle
`opencv.js` baut den Code mit, exportiert die ArUco-Klassen aber nicht. Wer die
Whitelist erweitert, bekommt sie — und das hat jemand bereits getan.

Benutzt wurde **`@techstark/opencv-js@5.0.0-release.1`**: OpenCV **5.0.0**, dieselbe
Hauptversion wie der Desktop. Kein Docker, kein emsdk, kein eigener Bau. **Die
teuerste Stufe des Fahrplans war ein `npm pack`.**

13,3 MB roh, 2,67 MB über Brotli, eine Datei ohne separate `.wasm`, in 111 ms
einsatzbereit. Erkennung 3,8–5,7× langsamer als nativ (einkernig, ohne SIMD) — für ein
Handyfoto **unter einer Sekunde**.

**Was der Spike ausdrücklich nicht zeigt:** nur die *Erkennung* wurde geprüft, gegen
eine *synthetische* Szene, in *einem* Browser. Homographie, Kamerazerlegung,
Dickenkorrektur und `least_squares → cv::LevMarq` sind unberührt.

### Stufe 1 · `shared/` — eine Wahrheit, sprachneutral — Tage

Konstanten und Fixtures aus Python herauslösen, **ohne** die Anwendung anzufassen.
Nützlich auch dann, wenn der Umzug hier stehenbliebe.

*Fertig, wenn:* `shared/constants.json` existiert, `config.py` liest daraus, die
eingefrorenen Szenen liegen als Dateien vor, und die Suite ist grün.

### Stufe 2 · Der C++-Kern — Wochen

`core/` in C++ gegen OpenCV, mit `pybind11`-Bindung. Python bleibt unverändert
lauffähig und liefert weiter aus.

*Fertig, wenn:* die vorhandene Python-Suite gegen den C++-Kern grün ist.

### Stufe 3 · ✅ PORTIERT — PDF nach JavaScript

`app/pdf/` liegt als `web/pdf/` vor (`pdf-lib`, reines ESM). Alle **33** PDF-Prüfungen
sind mit `ARUCO_PDF=js` grün — und die ganze Suite mit ihren 174 Prüfungen dazu.
`.\dev.ps1 run-tests-pdf-js` fährt sie so.

Was damit belegt ist: die Invarianten 1, 3 und 7 gelten auch im neuen Bau, an
denselben Prüfungen und mit denselben Toleranzen. Die aus beiden PDFs **gelesenen**
Platzierungen stimmen auf 0,00005 mm überein, die Marke steht auf jedem Blatt, und
ein aus JavaScript gebautes Markerblatt liefert durch den echten Detektor dieselben
Kantenlängen und Mittelpunktabstände wie das bisherige (auf vier Nachkommastellen).
`web/pdf/` wurde ausserdem in einem echten Browser ausgeführt.

Was damit **nicht** belegt ist: die Umstellung. Ausgeliefert wird weiter der
ReportLab-Bau (`ARUCO_PDF` steht auf `python`), und die eine gemessene Abweichung —
ein halbes Gerätepixel beim **Rastern** gekachelter Seiten, weil der Renderer
Bildkanten rundet — steht in `web/pdf/draw.js` mit ihrer Messreihe. Der Umbau der
Oberfläche auf den eigenen PDF-Bau gehört zu Stufe 4.

### Stufe 4 · Die Hüllen — Wochen

Desktop (webview), Android (WebView + NDK), Browser. Erst hier wird aus dem Kern
ein Produkt auf drei Zielen.

**Windows ist fertig und belegt:
[`stage-4-windows-exe.md`](stage-4-windows-exe.md).** Die gebaute `.exe` misst mit
dem C++-Kern — nicht behauptet, sondern gezeigt: nimmt man ihr die `aruco_core.pyd`
weg, startet sie nicht mehr, und ihre Messung ist Zahl für Zahl dieselbe wie die des
Quellbaums mit `ARUCO_CORE=cpp` (alle 32 Eckkoordinaten, rms 0,093 px). Der Preis
steht dort ebenfalls: der ausgelieferte Ordner wächst von rund 308 MB auf 388 MB,
weil `opencv_world500.dll` mit muss, solange `cv2` für alles außer dem Detektor
gebraucht wird.

**Die Werkzeugketten stehen bereits — vorgezogen und belegt:
[`stage-4-cross-targets.md`](stage-4-cross-targets.md).** Derselbe `core/` übersetzt
für alle drei Ziele, ohne ein einziges Ziel-`ifdef`; ausgeführt und Ecke für Ecke
verglichen sind Windows und WASM (unter Node **und** in Chrome). Sie stimmen bis auf
**5 von 64 Ecken zu je einem `float32`-ULP** überein — 0,000122 px, das ist
0,000048 mm und 6100-mal unter der Toleranz. **Android bindet für alle vier ABIs, ist
aber ungemessen:** auf dem Entwicklungsrechner gibt es weder Gerät noch Emulator.

Vorgezogen wurde das, weil es die Frage ist, für die der ganze Umzug betrieben wird.
Wäre sie erst hier gestellt worden, stünden die Stufen 2 und 3 auf einer Annahme.

### Stufe 5 · Aufräumen — Tage

`app/` → `py/`. **Zuletzt**, nicht zuerst: der Umzug bricht `dev.ps1`, die
PyInstaller-Vorschrift, den Inno-Installer und jeden Pfad in der Dokumentation. Das
tut man, wenn Python von *dem Produkt* zur *Referenz* geworden ist — vorher zahlt man
den Preis ohne den Gegenwert.

---

## 5a · Wie das Ergebnis ausgeliefert wird

**Der fertige Umzug ist `v0.1.0-alpha`** — und diese Fassung bringt **alle drei Ziele
auf einmal**: die Windows-`.exe`, die Android-`.apk` und den Browser-Bau.

Das ist Absicht und keine Bequemlichkeit. Der ganze Sinn dieses Umzugs ist, dass
dieselbe Messtechnik überall rechnet. Drei Ziele einzeln zu veröffentlichen hieße,
genau die Frage offenzulassen, für die der Aufwand betrieben wurde: rechnen sie
wirklich gleich? Eine Fassung, in der alle drei liegen, ist die Antwort — sie sind
zusammen gebaut, zusammen gegen `shared/fixtures/` geprüft und zusammen ausgeliefert.

Der Sprung von `0.0.x` auf `0.1.0` sagt dasselbe: nicht „ein bisschen mehr", sondern
ein anderes Produkt.

Bis dahin gilt die `0.0.x`-Reihe weiter und liefert wie bisher nur Windows.

---

## 6 · Aufwand, ehrlich

**Sechs bis zehn Wochen**, nicht die eine, nach der es aussieht. Es sind **zwei**
Portierungen (Sehen nach C++, PDF nach JavaScript), **drei** Werkzeugketten
(MSVC, Android-NDK, Emscripten) und eine Konformitätsprüfung, die von Anfang an
mitlaufen muss.

Was den Aufwand kleiner macht, als er klingt: der Python-Kern *ruft* im Wesentlichen
nur OpenCV auf — 46 verschiedene `cv2.*`-Symbole. Die Portierung schreibt Aufrufe um,
die es schon gibt; sie erfindet keinen Algorithmus. Die einzige Zahlenmethode
außerhalb von OpenCV ist `scipy.optimize.least_squares` an genau zwei Stellen
(`solve.py:179` und `:199`) — daraus wird `cv::LevMarq` (in OpenCV 5 im Modul
`geometry`; die Klasse hieß bis OpenCV 4 `cv::LMSolver` und lag in `calib3d`) oder Ceres.

## 7 · Woran es scheitern könnte

- ~~**`opencv.js` mit `aruco` lässt sich nicht bauen**~~ → **erledigt** (Stufe 0). An
  seine Stelle traten zwei kleinere — ~~der benutzte Bau ist das Werk *einer* Person und
  gehört für einen Auslieferungsstand eingefroren und mitgeliefert, nicht bei jedem
  Bau frisch aus npm gezogen~~; ~~und 2,7 MB liegen vor der ersten Messung~~ —,
  **und auch die sind erledigt** (Stufe 4), weil `@techstark/opencv-js`
  **gar nicht mehr gebraucht wird**. Der C++-Kern wird *in* das wasm hineinübersetzt;
  er ruft OpenCV direkt auf und braucht dessen JavaScript-Bindungen nicht. Nötig sind nur
  statische Bibliotheken, und die baut man selbst — sechs Module, **sieben Minuten**,
  ohne Docker. Damit hängt nichts mehr an einem fremden npm-Paket, und kleiner ist es
  auch: das wasm des Prüfstands wiegt 2,38 MB roh und 603 KB über Brotli, gegen 13,3 MB
  und 2,67 MB — und darin steckt sogar noch der Prüfstand selbst. Ein hineinübersetzter
  Kern nimmt eben nur mit, was er aufruft.
- **Zwei Befunde aus Stufe 0, die Stufe 2 jetzt schon binden:**
  - **`imgcodecs` ist im WASM-Bau abgeschaltet** — kein `imread`, `imencode`,
    `imwrite`. Der gemeinsame C++-Kern **darf sie nicht anfassen**: er nimmt einen
    rohen Pixelpuffer plus Maße und gibt einen solchen zurück. Kodieren und Dekodieren
    gehört auf jedes Ziel einzeln. Heute ist der Messkern schon sauber (`cv2.imread`
    steht nur in `pipeline.py` und `session.py`, beides Vorschaudateien). **Das muss er
    bleiben.**
  - **EXIF gibt es im Browser nicht.** Brennweite und Bildlage liest heute PIL, nicht
    OpenCV; der Canvas wirft die Metadaten weg. Das Web-Ziel braucht einen eigenen
    JS-EXIF-Leser. `camera.py` fällt bereits sauber auf die manuelle Eingabe zurück,
    aber die Arbeit stand im Fahrplan nirgends.
- **Der C++-Kern besteht die Python-Suite nicht** innerhalb der Toleranz → nicht
  weitergehen, sondern die Abweichung finden. Eine Stufe 3 auf einem Kern, der um
  einen Zehntelmillimeter danebenliegt, ist verlorene Arbeit.
- ~~**Die PDF-Invarianten lassen sich in JS nicht sauber belegen**~~ → **erledigt**
  (Stufe 3). Alle 33 PDF-Prüfungen sind mit `ARUCO_PDF=js` grün, mit denselben
  Toleranzen. An seine Stelle tritt eine kleinere Frage: das **Rastern** gekachelter
  Seiten weicht um bis zu ein halbes Gerätepixel ab, weil der Renderer Bildkanten auf
  ganze Pixel legt und das gerundete Rechteck im neuen Bau das ganze Bild statt der
  Kachel ist. Die Datei selbst stimmt auf 0,00005 mm; die Messreihe steht in
  `web/pdf/draw.js`.
- **Aufmerksamkeit.** Sechs bis zehn Wochen sind lang. Deshalb liefert jede Stufe
  etwas Brauchbares, statt erst am Ende.
