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

### Stufe 0 · Das größte Risiko zuerst anfassen — Tage

**`opencv.js` mit `aruco` bauen und im Browser laufen sehen.**

Der Standardbau von `opencv.js` enthält **kein** `aruco` — das Modul steckt in
`opencv_contrib`. Ein eigener Emscripten-Bau ist möglich und wird durchweg als
fummelig beschrieben; der einzige fertige, den es gibt, steht auf OpenCV **4.5.3**
und ist damit alt (dieser Code nutzt die `ArucoDetector`-API ab 4.7).

**Bis das läuft, ist das Web-Ziel eine Hoffnung und kein Plan.** Deshalb steht es
vorn: scheitert es, ändert sich der Zuschnitt — und zwar in Woche 1 statt in Woche 8.

*Fertig, wenn:* ein Browser eine der eingefrorenen Szenen lädt, vier Marker findet
und dieselben Ecken meldet wie Python, innerhalb der Toleranz.

### Stufe 1 · `shared/` — eine Wahrheit, sprachneutral — Tage

Konstanten und Fixtures aus Python herauslösen, **ohne** die Anwendung anzufassen.
Nützlich auch dann, wenn der Umzug hier stehenbliebe.

*Fertig, wenn:* `shared/constants.json` existiert, `config.py` liest daraus, die
eingefrorenen Szenen liegen als Dateien vor, und die Suite ist grün.

### Stufe 2 · Der C++-Kern — Wochen

`core/` in C++ gegen OpenCV, mit `pybind11`-Bindung. Python bleibt unverändert
lauffähig und liefert weiter aus.

*Fertig, wenn:* die vorhandene Python-Suite gegen den C++-Kern grün ist.

### Stufe 3 · PDF nach JavaScript — Wochen

`app/pdf/` nach `web/pdf/`. Die Invarianten 1, 2 und 3 neu belegen.

*Fertig, wenn:* ein in JS gebautes PDF Seite für Seite dieselben Maße hat wie das
heutige, und der Markenstreifen auf jedem Blatt steht.

### Stufe 4 · Die Hüllen — Wochen

Desktop (webview), Android (WebView + NDK), Browser. Erst hier wird aus dem Kern
ein Produkt auf drei Zielen.

### Stufe 5 · Aufräumen — Tage

`app/` → `py/`. **Zuletzt**, nicht zuerst: der Umzug bricht `dev.ps1`, die
PyInstaller-Vorschrift, den Inno-Installer und jeden Pfad in der Dokumentation. Das
tut man, wenn Python von *dem Produkt* zur *Referenz* geworden ist — vorher zahlt man
den Preis ohne den Gegenwert.

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
(`solve.py:179` und `:199`) — daraus wird `cv::LMSolver` oder Ceres.

## 7 · Woran es scheitern könnte

- **`opencv.js` mit `aruco` lässt sich nicht bauen** → Web-Ziel muss anders gelöst
  werden. Deshalb Stufe 0.
- **Der C++-Kern besteht die Python-Suite nicht** innerhalb der Toleranz → nicht
  weitergehen, sondern die Abweichung finden. Eine Stufe 3 auf einem Kern, der um
  einen Zehntelmillimeter danebenliegt, ist verlorene Arbeit.
- **Die PDF-Invarianten lassen sich in JS nicht sauber belegen** → dann bleibt PDF
  vorerst in Python und Android bekommt später eine eigene Antwort.
- **Aufmerksamkeit.** Sechs bis zehn Wochen sind lang. Deshalb liefert jede Stufe
  etwas Brauchbares, statt erst am Ende.
