---
title: Stufe 4 · Die Windows-Hülle misst mit C++
description: Wie die ausgelieferte .exe an den C++-Kern kommt, womit das belegt ist und was es an Größe kostet.
audience: developer
status: current
updated: 2026-09-08
---

# Stufe 4 · Die Windows-Hülle misst mit C++

**Ergebnis: die gebaute `.exe` rechnet mit dem C++-Kern, und das ist belegt — nicht
behauptet.** Nimmt man ihr die `aruco_core.pyd` weg, startet sie nicht mehr. Ihre
Messung ist Zahl für Zahl dieselbe wie die des Quellbaums mit `ARUCO_CORE=cpp`.

**Was das kostet: der ausgelieferte Ordner wächst von rund 308 MB auf 388 MB**, weil
`opencv_world500.dll` (80,1 MB) mit muss. Dazu unten mehr — das ist der ehrliche Preis
dieser Stufe und keine Nebensache.

> **Nachtrag 08.09.2026:** inzwischen liegt die **ganze** Messkette in `core/` (PR #30),
> nicht mehr nur der Detektor. Die `.exe` rechnet damit von der Markererkennung bis zur
> Kontur in C++. An der Größe ändert das nichts — der Kern ist 0,18 MB, die DLL daneben
> war schon vorher der ganze Preis. An Abschnitt 2.4 ändert es alles.

---

## 1 · Was sich geändert hat

Vorher lag der C++-Kern nur in `core/build/` und wurde ausschließlich von der
Testsuite benutzt. Die ausgelieferte `.exe` rechnete weiter in Python. Der Umzug war
damit an genau der Stelle unsichtbar, an der er ankommen soll.

Vier Stellen, mehr war es nicht:

| Datei | Was |
|---|---|
| `app/config.py` | `FROZEN` / `BUNDLE_DIR` — die eine Stelle, die `sys._MEIPASS` liest |
| `app/vision/backend.py` | findet den Kern auch im Bundle; **Vorgabe im Bundle ist `cpp`** |
| `aruco-homographie.spec` | legt `.pyd` und `opencv_world500.dll` ins Bundle |
| `dev.ps1` | `build-exe` baut den Kern mit; die Frischeprüfung sieht ihn |

Dazu eine Zeile im Startbanner, die sagt, welcher Kern gerade misst.

An diesen vier Stellen hat sich seither nichts geändert; erweitert wurde nur, **was**
der Kern kann (PR #30, fünfzehn Funktionen hinter `backend.implementation`).

### Die Vorgabe hängt am Ort, nicht an einer Umgebungsvariablen

```
im Quellbaum   ->  ARUCO_CORE=python   die Referenz, gegen die geprüft wird
in der .exe    ->  ARUCO_CORE=cpp      ausgeliefert wird der C++-Kern
```

Der Quellbaum bleibt bei Python, weil `./dev.ps1 run-tests` sonst je nach Bauzustand
von `core/build/` etwas anderes messen würde als gestern — ein Lauf, der sich selbst
nicht gleicht, belegt nichts. Die `.exe` nimmt C++, weil genau das ausgeliefert wird.
`./dev.ps1 run-tests-cpp` prüft weiterhin denselben Fall im Quellbaum.

**Kein Rückfall.** Fehlt die `.pyd` im Bundle, bricht der Start ab. Still auf Python
zurückzufallen wäre hier der teuerste Ausgang, den es gibt: alles sähe grün aus, und
ausgeliefert wäre der Kern, den niemand geprüft hat. Dieselbe Haltung wie bei den
Konstanten (`AGENTS.md`, Invariante 4).

---

## 2 · Der Beleg

`./dev.ps1 build-exe` und danach die drei Fragen. Die dritte ist die einzige, die
wirklich etwas belegt.

### 2.1 Sagt sie es? — das Banner

```
  ArUco-Homographie 0.0.3-alpha laeuft
  Lokal:       http://127.0.0.1:63021
  Im Netzwerk: http://192.168.0.110:63021
  Rechenkern:  C++ (core/)
```

### 2.2 Rechnet sie dasselbe? — die Zahlen

Dieselbe synthetische Szene (`tests/conftest.py::make_scene`), einmal durch den
Quellbaum mit `ARUCO_CORE=cpp` und einmal durch die gebaute `.exe` über HTTP. Nicht
verglichen werden Sitzungskennung, Zeitstempel und Laufzeit; **alles andere ist
deckungsgleich**, einschließlich aller 32 Eckkoordinaten:

```
Marker      : 4
rms         : 0.093 px  /  0.0482 mm
Ausschnitt  : 1258.042 x 961.788 mm
Export      : 673 783 B, 29 Seiten, 210.000x297.000 mm
              Bildrechteck 5.000,23.000,200.000,269.000
```

### 2.4 Und die beiden Kerne gegeneinander

> **Nachgetragen am 08.09.2026.** Als dieses Dokument entstand, umfasste `core/` genau
> eine Rechnung, und die beiden Kerne waren auf allen Feldern bitgleich. Seither sind
> **fünfzehn** Funktionen dazugekommen (PR #30) — die `.exe` misst jetzt die
> **vollständige** Kette in C++. Damit stimmt der frühere Satz, kein einziger gemessener
> Wert weiche ab, nicht mehr — und was an seine Stelle tritt, ist die eigentliche
> Aussage dieses Abschnitts.

Dieselbe Szene durch `ARUCO_CORE=python` und `ARUCO_CORE=cpp`, Feld für Feld über den
ganzen Antwortkörper verglichen. **Von allen Zahlen weichen genau vier ab**, jede
dreimal aufgeführt (Ausschnitt, Ausdehnung, Vorschau):

| Feld | Python | C++ | Δ |
|---|---|---|---|
| `extent_mm.x1` | 716,8210079205405 | 716,8210104374368 | 2,517·10⁻⁶ mm |
| `extent_mm.y1` | 625,7669995023339 | 625,7669974898539 | 2,012·10⁻⁶ mm |
| `extent_mm.x0` | −541,221446669155 | −541,2214474138532 | 7,447·10⁻⁷ mm |
| `extent_mm.y0` | −336,0211545042241 | −336,0211550054414 | 5,012·10⁻⁷ mm |

**Alles andere ist identisch** — alle 32 Eckkoordinaten, `rms_px` 0,093, `rms_mm`
0,0482, jede gemessene Markerkante, jedes Residuum, die Seitengeometrie.

**Die größte Abweichung ist 2,5 Nanometer** auf einem 1258 mm breiten Ausschnitt, also
relativ 2,0·10⁻⁹ — und **155 000-mal kleiner als die Toleranz** einer einzelnen
Markerecke (0,75 px ≈ 0,39 mm).

Dass sie überhaupt auftritt, ist erwartbar und kein Mangel: `refine_homography` ist in
Python eine `scipy`-Ausgleichsrechnung und in C++ `cv::LevMarq`. Zwei verschiedene
Verfahren auf demselben Problem enden nicht auf demselben Bit; sie enden hier auf
demselben Nanometer. Die Ausdehnung der Ebene ist die einzige Größe, die weit genug
hinter der Homographie steht, um es überhaupt zu zeigen.

### 2.3 Lädt sie ihn wirklich? — der Gegenbeweis

Die beiden Prüfungen oben bestünde auch eine `.exe`, die den Kern mitschleppt und
stillschweigend in Python weiterrechnet. Sie rechnet ja richtig — nur eben nicht mit
dem, was hier ausgeliefert werden soll. Also:

```
_internal\aruco_core.cp313-win_amd64.pyd  ->  ...pyd.weg
```

```
[ok] Server kommt NICHT hoch
[ok] RuntimeError: Der C++-Kern fehlt in dieser Installation (gesucht in ...)
```

**Das ist der Beleg.** Ohne ihn wären 2.1 und 2.2 wertlos.

---

## 3 · Was das kostet

| | vorher | nachher |
|---|---|---|
| `dist/ArUco-Homographie/` | rund 308 MB | **388,5 MB** |
| Installer (eine Datei) | rund 78 MB | **102,9 MB** (102 871 884 Byte) |
| davon neu | — | `opencv_world500.dll` 80,1 MB + `aruco_core.pyd` 0,18 MB |

Der Installer wächst also um gut ein Viertel — 80 MB DLL, die Inno Setup auf rund
25 MB zusammendrückt. Gemessen an einem Bau vom 08.09.2026 auf diesem Rechner; die
Zahl ist eine Messung und keine Zusage (PyInstaller bettet Zeitstempel ein, zwei
Bauten derselben Quelle sind nie byteweise gleich).

Der Ordner trägt jetzt **zwei** OpenCV-Fassungen: `cv2.pyd` (85,8 MB, OpenCV statisch
einübersetzt) für alles, was noch in Python rechnet, und `opencv_world500.dll` aus dem
Windows-SDK für den C++-Kern. Beide sind OpenCV 5.0.0, aber es sind zwei Bauten, und
im selben Prozess sind sie zwei voneinander unabhängige Bibliotheken.

Das ist verkraftbar, weil nichts zwischen ihnen überquert: die Bindung nimmt ein
numpy-Array entgegen und gibt Zahlen zurück — kein `cv::Mat` wandert über die Grenze
(`core/bindings/python.cpp`).

**Der Doppelbestand bleibt, auch jetzt, wo die ganze Messung in C++ liegt.** `cv2`
wird weiterhin außerhalb von `app/vision/` gebraucht, und zwar an fünf Stellen, die
mit Messen nichts zu tun haben:

| Datei | wofür |
|---|---|
| `app/session.py` | Foto dekodieren |
| `app/pipeline.py` | Vorschau kodieren |
| `app/pdf/build.py` | Bild ins PDF |
| `app/pdf/markersheet.py` | Marker zeichnen |
| `app/config.py` | Wörterbuchnamen auflösen |

Das ist Ein- und Ausgabe, nicht Geometrie. Solange die Python-Fassung überhaupt
ausgeliefert wird — und sie ist die geprüfte Referenz —, müssen beide OpenCV-Bauten
mit. Ein schlanker OpenCV-Bau (nur `core`, `imgproc`, `objdetect` statt `world`) wäre
die andere Hälfte der Ersparnis und verlangt, OpenCV selbst neu zu übersetzen —
mehrere Stunden, und deshalb hier nicht getan.

---

## 4 · Fallstricke, die hier zugeschlagen haben

1. **`.pyd` und DLL müssen beisammen liegen.** Windows durchsucht das Verzeichnis der
   `.pyd`, bevor es den `PATH` befragt — das ist die ganze Wegfindung für
   `opencv_world500.dll`, und sie ist der Grund, warum beide in die Wurzel des Bundles
   (`_internal/`) gehen und nicht in einen Unterordner.

2. **`python313.dll` liegt auch in `core/build/`** — CMake kopiert sie über
   `$<TARGET_RUNTIME_DLLS:aruco_core>` dorthin. Sie darf **nicht** ins Bundle:
   PyInstaller bringt seine eigene mit. Deshalb sammelt die Spec `*.dll` ein und
   schließt `python*.dll` ausdrücklich aus.

3. **Das Banner stand nicht in der umgeleiteten Datei.** Nicht das Banner war schuld,
   sondern die Pufferung: `uvicorn` protokolliert nach stderr (ungepuffert), `print()`
   geht nach stdout (blockweise gepuffert, sobald das Ziel keine Konsole ist). In einer
   Datei kamen die beiden in verkehrter Reihenfolge an. Die Banner-Zeile schreibt jetzt
   mit `flush=True`; ausgerechnet sie soll man sofort lesen können.

4. **`dict(response.headers)`** findet `X-Pages` nie — der Kopf kommt kleingeschrieben
   zurück. `response.headers.get(...)` sucht ohne Rücksicht auf Groß- und Kleinschreibung.

---

## 5 · Was hier NICHT belegt ist

- **Der Installer.** Gebaut und gewogen (§ 3), aber **nicht installiert und nicht
  danach gestartet**. Die gebaute Datei wurde anschließend gelöscht: sie trägt
  `0.0.3-alpha` im Namen, enthält aber den C++-Kern, den die veröffentlichte
  `0.0.3-alpha` nicht hat — zwei verschiedene Dinge unter einem Namen sind genau die
  Verwechslung, die später niemand mehr aufklärt.
- **Die Maßhaltigkeit am echten Ausdruck.** Unverändert offen und von dieser Stufe
  nicht berührt: belegt ist `PDF → Drucker → Papier` (Messschieber am Kontrollmaßstab),
  nicht `Foto → Marker → Millimeter`. Siehe `CLAUDE.md`.
- **Dass C++ schneller wäre.** `elapsed_s` liegt bei 0,18 s gegen 0,19 s — auf einem
  einzelnen Durchlauf ist das Rauschen, keine Aussage. Der Umzug wird nicht wegen der
  Geschwindigkeit betrieben, sondern damit Android und Browser dieselbe Rechnung
  bekommen.
