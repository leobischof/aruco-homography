---
title: Stufe 4 · Ein Quelltext, drei Ziele — Ergebnis
description: Derselbe core/ übersetzt für Windows, WASM und Android — was gemessen ist und was nur gebaut.
audience: developer
status: current
updated: 2026-09-08
---

# Stufe 4 · Ein Quelltext, drei Ziele — Ergebnis

> **Ja. Derselbe `core/` übersetzt für Windows, Android und WebAssembly und misst auf
> allen dreien dasselbe.** Zuversicht: **hoch für alle drei.** Windows und WASM sind hier
> gelaufen, Ecke für Ecke verglichen; für Android galt das lange nicht — dort war nur
> belegt, dass es bindet. Am **08.09.2026** ist der Prüfstand auf einem Xiaomi 2312DRA50G
> (Android 15) gelaufen und hat **bestanden**, mit demselben größten Eckfehler von
> **0,2337 px** je Szene. Auf diesem Rechner gibt es weiterhin kein Gerät und keinen
> Emulator; die Zahl kommt aus dem Telefon selbst.

> **Stand:** 2026-09-08 · Zweig `feat/cross-compile` · Belege in `core/`, `dev.ps1`

---

## 1 · Die Zahlen nebeneinander

Alle drei Ziele messen dieselben zwei eingefrorenen Szenen aus `shared/fixtures/` gegen
dieselbe **Grundwahrheit** (nicht gegeneinander). Gerundet auf die vier Stellen, die der
Prüfstand ausgibt, sind sie nicht zu unterscheiden:

| | Windows x64 (MSVC 14.50) | WASM · Node 24.19 | WASM · Chrome 152 | Android arm64-v8a |
|---|---|---|---|---|
| Ausgang | **BESTANDEN**, exit 0 | **BESTANDEN**, exit 0 | **BESTANDEN**, exit 0 | **nicht ausgeführt** |
| größter Eckfehler, `flat` | **0,2337 px** | **0,2337 px** | **0,2337 px** | — |
| größter Eckfehler, `thick` | **0,2337 px** | **0,2337 px** | **0,2337 px** | — |
| Mittel über 16 Ecken | 0,1402 / 0,1404 px | 0,1402 / 0,1404 px | 0,1402 / 0,1404 px | — |
| ohne CLAHE (Gegenprobe) | 0,2663 px | 0,2663 px | 0,2663 px | — |
| Toleranz aus `shared/fixtures/` | 0,7500 px | 0,7500 px | 0,7500 px | 0,7500 px |

Marker für Marker, Szene `flat`, mit CLAHE — auf allen ausgeführten Zielen identisch:

| Marker | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| größter Eckfehler | 0,1864 px | 0,2100 px | **0,2337 px** | 0,2239 px |

Die Gegenprobe ohne CLAHE ist auf jedem Ziel um denselben Betrag schlechter
(0,2663 statt 0,2337 px). Der Schalter läuft also überall wirklich, und nicht nur auf
Windows — genau das war die Sorge, die den Kreuzbau überhaupt nötig machte.

---

## 2 · Der eine Unterschied — und wie groß er ist

Vier Nachkommastellen genügen für eine Toleranz, aber nicht, um zwei Ziele
gegeneinanderzuhalten. Der Prüfstand hat deshalb einen Schalter `--ecken` bekommen, der
jede Ecke mit `%.17g` ausgibt — verlustfrei zurücklesbar. **64 Ecken** je Ziel
(2 Szenen × 4 Marker × 4 Ecken × 2 Durchläufe).

```
Windows/MSVC  vs  WASM/Node
  Ecken verglichen:                  64
  davon verschieden:                  5
  groesster Koordinatenunterschied:  0.0001220703125 px
  das sind:                          1 float32-ULP
  groesster Fehlerunterschied:       0.00011919876042246202 px
  in mm (50 mm ~ 128 px):            4.768e-05 mm
```

Die fünf Abweichungen im Klartext:

```
('flat',  'clahe', 0, 2): 1148.049560546875   ->  1148.0494384765625
('flat',  'clahe', 2, 3): 1019.640869140625   ->  1019.6409301757812
('flat',  'grau',  3, 1): 1381.4439697265625  ->  1381.44384765625
('thick', 'clahe', 0, 2): 1148.049560546875   ->  1148.0494384765625
('thick', 'grau',  3, 1): 1381.4439697265625  ->  1381.44384765625
```

**Jede einzelne ist genau ein `float32`-ULP** — der kleinste Schritt, den die
Zahlendarstellung überhaupt kennt, in der OpenCV die Markerecken führt. Nicht „ungefähr
ein ULP": bei Betrag 1148 ist der ULP `2⁻¹³ = 0,0001220703125`, und das ist die gemessene
Differenz auf die letzte Stelle. Bei 1019 ist er halb so groß, `2⁻¹⁴`, und genau so groß
ist dort auch die Abweichung.

**Größenordnung.** Die Toleranz dieses Projekts ist 0,75 px, der Unterschied
0,000122 px — **6100-mal kleiner**. In Millimetern, bei 50 mm Markerkante auf rund
128 px: **0,000048 mm**. Achtundvierzig Nanometer. Ein Blatt Papier ist zweitausendmal
dicker.

Es ist außerdem **dieselbe Größenordnung, die Stufe 0 schon gemessen hat** (dort
1,2 · 10⁻⁴ px zwischen Python und Browser, ebenfalls „ein `float32`-ULP"). Zwei
unabhängige Wege, dieselbe Schranke: das ist kein Fehler in einem Bau, das ist die
Auflösung der Darstellung.

**Woher er kommt.** Nicht aus der Laufzeit — Node und Chrome liefern **dieselben Bits**:

```
SHA-256 des 64-Zeilen-Eckenblocks
  Node 24.19.0   1ef0f28f7c5c0ff9fd65e94ac8b289bd36b035f9c6358918b63ae956dd3145e6
  Chrome 152     1ef0f28f7c5c0ff9fd65e94ac8b289bd36b035f9c6358918b63ae956dd3145e6   ← gleich
  Windows/MSVC   081faa360b826d119ebb11c783a46ea5dfa39d93790ebacd049a7df6d685cc71
```

Der Unterschied sitzt also im **Bau**, nicht im Wirt. Und die beiden OpenCV, gegen die
gebunden wird, sind sich weniger ähnlich, als „beide 5.0.0" vermuten lässt — abgefragt
mit `cv::getBuildInformation()` an genau den Bibliotheken, die der Kern benutzt:

| | Windows-SDK (`opencv_world500.dll`) | selbst gebautes WASM |
|---|---|---|
| übersetzt von | **MSVC 14.29** (VS 2019, `cl` 19.29.30154.0) | `em++` 6.0.9 (clang 24.0.0) |
| Grundlinie | SSE SSE2 SSE3 | keine |
| SIMD-Verzweigungen | SSE4_1, SSE4_2, AVX, AVX2 (**mit FMA3**, 49 Dateien), AVX512_SKX | **keine** (`CV_ENABLE_INTRINSICS=OFF`) |
| Parallelisierung | `Concurrency` (PPL) | keine |

Drei Unterschiede, von denen jeder für sich das letzte Bit bewegen kann; der schwerste
ist der mittlere. Auf Windows laufen für dieselbe Rechnung **handgeschriebene AVX2-Kerne
mit FMA**, im Browser der schlichte C++-Zweig. FMA spart eine Zwischenrundung — genau
dort entsteht ein ULP Unterschied und nirgendwo sonst. (Beachtenswert nebenbei: die
DLL des Windows-SDK ist mit einem *anderen* MSVC gebaut als unser Kern. Das ist bei
einem vorgefertigten SDK normal und bei OpenCVs stabiler C++-ABI unbedenklich, aber es
gehört gewusst.)

**Was daraus folgt.** Die Behauptung „drei Ziele, eine Messtechnik" hält — aber sie hält
nicht in der Form „bitgleich". Sie hält in der Form:

| Verhältnis | Faktor |
|---|---:|
| Toleranz (0,75 px) ÷ Unterschied zwischen den Zielen | **6100** |
| Eigener Messfehler (0,2337 px) ÷ Unterschied zwischen den Zielen | **1900** |
| Toleranz ÷ eigener Messfehler (die Reserve, die bleibt) | 3,2 |

Der Abstand der Ziele voneinander ist also **dreitausendmal unwichtiger als der Abstand
zur Grundwahrheit**, den beide gemeinsam haben. Wer künftig einen Kreuzbau prüft, sollte
genau so messen — `--ecken`, dann `1 ULP` als Erwartung, und ein Ergebnis, das deutlich
größer ist, ist ein Befund und keine Rundung.

> **Die Toleranz wurde nicht angefasst.** Sie steht unverändert in
> `shared/fixtures/expected/*.json` bei 0,75 px, und alle drei Ziele halten sie mit
> Faktor 3 Reserve.

---

## 3 · Was gebaut wurde, und womit

### Versionen — alle vorgefunden, nichts nachgeladen

| | |
|---|---|
| OpenCV | **5.0.0** auf allen drei Zielen (Windows-SDK, Android-SDK, selbst gebautes WASM) |
| MSVC | 19.50.35721.0 (Toolset 14.50), VS 18 BuildTools |
| Emscripten | **6.0.9**, `clang` 24.0.0 |
| Android-NDK | **27.2.12479018** (r27c), `ANDROID_PLATFORM=android-24` |
| CMake / Ninja | 4.1.1-msvc1 / 1.12.1 (beide aus den VS-BuildTools) |
| Node | 24.19.0 (das aus dem emsdk) |
| Browser | Chrome 152 über `python -m http.server` |

Dass alle drei OpenCV **dieselbe Fassung** sind, ist kein Zufall und nicht verhandelbar:
die Typkennungen haben sich zwischen 4.x und 5.0 verschoben (`CV_8UC3` 16 → 64), und
`contourArea` ist von `imgproc` nach `geometry` gewandert. Zwei Hauptfassungen im selben
Vorhaben wären genau die Sorte Unterschied, die niemand sieht.

### WASM: OpenCV selbst bauen — 6,7 Minuten, nicht Tage

Der Fahrplan rechnete mit `platforms/js/build_js.py`. **Das braucht es nicht.** Jenes
Skript baut `opencv.js`, also die **JavaScript-Bindungen** — und für die ist die
Modul-Whitelist zuständig, um die sich Stufe 0 so gesorgt hat. Der C++-Kern wird aber
**in** das wasm hineinübersetzt und ruft OpenCV direkt auf. Er braucht keine Bindung,
sondern **statische Bibliotheken**.

Damit fällt der halbe Bau weg (kein `dnn`, kein `photo`, kein `js`-Modul, keine Tests):

```cmd
cmake -S <_toolchain>\opencv\sources -B C:\ocvw -G Ninja ^
  -DCMAKE_TOOLCHAIN_FILE=<emsdk>\upstream\emscripten\cmake\Modules\Platform\Emscripten.cmake ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DBUILD_SHARED_LIBS=OFF ^
  -DBUILD_LIST=core,flann,geometry,imgproc,features,objdetect ^
  -DCMAKE_CXX_FLAGS=-fexceptions -DCMAKE_C_FLAGS=-fexceptions ^
  -DBUILD_TESTS=OFF -DBUILD_PERF_TESTS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_DOCS=OFF ^
  -DBUILD_opencv_js=OFF -DBUILD_opencv_python3=OFF -DBUILD_JAVA=OFF ^
  -DWITH_PTHREADS_PF=OFF -DCV_ENABLE_INTRINSICS=OFF -DBUILD_ZLIB=ON ^
  -DCMAKE_INSTALL_PREFIX=C:/ocvw/install
cmake --build C:\ocvw --target install
```

`BUILD_LIST` ist knapp und trotzdem vollständig: `objdetect` (ArUco) zieht `features`,
das `geometry` zieht, das `flann` zieht. **`geometry` muss drin sein** — dort wohnen
`contourArea` *und* `LevMarq`, also beide Hälften der Messung.

`-fexceptions` ist **nicht optional**. Emscripten übersetzt seit 3.x ohne
Ausnahmebehandlung, wenn man nichts sagt: ein `throw` wird zu `abort()`, ein `catch`
verschwindet. Und es muss **auf beiden Seiten** stehen, hier wie in `core/`, weil das
Entfalten durch jeden Rahmen dazwischen muss — auch durch OpenCVs eigene.

Ergebnis: **279 Ziele, 6,7 Minuten** Übersetzungszeit, 83 MB Bauverzeichnis, davon
**24 MB Install** (Bibliotheken + Kopfdateien). Das Install liegt jetzt neben den
anderen Werkzeugketten unter `_toolchain\opencv-wasm\` und wird von `dev.ps1` dort
gesucht.

Konfigurationsauszug des Baus:

```
    To be built:      core features flann geometry imgproc objdetect
    Disabled:         world
    Disabled by dep.: calib dnn highgui imgcodecs ... photo ptcloud ... stereo stitching video videoio
    C++ Compiler:     em++.exe (ver 24.0.0)
    Parallel framework: none
```

### Android: nichts zu bauen

Das OpenCV-Android-SDK ist bereits statisch übersetzt und trägt **alle vier ABIs**. Es
gibt keinen OpenCV-Bauschritt; der NDK-Toolchainfile und `OpenCV_DIR` genügen.

### `core/` selbst: keine Zeile C++ geändert

`src/detect.cpp`, die Kopfdateien und `tests/conformance.cpp` sind Byte für Byte das,
was MSVC übersetzt. **Kein einziges Ziel-`ifdef`.** Angepasst wurde nur die
Baubeschreibung:

- `pybind11` steht hinter `ARUCO_BUILD_PYTHON`, im Kreuzbau vorgabegemäß aus.
- Ein **Wirt-Python** (`ARUCO_HOST_PYTHON`) für die beiden Erzeugungsschritte
  (Konstanten-Header, Fixture-Paket) — und zwar zwingend dasselbe venv, weil
  `make_fixture_pack.py` die PNG mit `cv2` in rohe Bytes wandelt. Ein anderes `cv2` wäre
  ein anderer PNG-Dekoder zwischen den beiden Messungen.
- `-fexceptions` für Emscripten, `PUBLIC`.
- `$<TARGET_RUNTIME_DLLS:...>` nur noch unter `WIN32`.

### Die Kommandos

```powershell
.\dev.ps1 build-core            # Windows, wie bisher
.\dev.ps1 build-core-wasm       # Emscripten - baut UND misst gleich unter Node
.\dev.ps1 build-core-android    # NDK, Vorgabe arm64-v8a
.\dev.ps1 build-core-android x86_64
```

`build-core-wasm` führt den Bau sofort aus, weil ein Kreuzbau, den niemand ausgeführt
hat, nur belegt, dass er übersetzt — und das ist die Frage nicht.
`build-core-android` sagt am Ende ausdrücklich, dass es nichts gemessen hat.

**Ein voller `build-core-wasm` aus leerem Verzeichnis: 62 Sekunden**, Messung
eingeschlossen (das OpenCV daneben ist da schon gebaut).

Im Browser nachmessen:

```powershell
.\venv\Scripts\python.exe -m http.server 8013 --directory core\build-wasm
# dann http://127.0.0.1:8013/conformance_web.html oeffnen
```

### Was schiefging: nichts. Und das gehört erklärt.

Ein Bericht ohne Fehlermeldungen ist verdächtig, deshalb ausdrücklich: **kein einziger
Kreuzbau ist an einem Übersetzungs- oder Bindefehler gescheitert.** Emscripten lief beim
ersten Versuch durch, arm64 beim ersten Versuch, die drei übrigen ABIs ebenfalls. Es gab
keine `#ifdef`-Schlacht, keine fehlende Kopfdatei, keinen ungelösten Namen.

Das ist kein Glück, sondern das Ergebnis von Stufe 2: `core/` wurde von Anfang an gegen
die Befunde aus Stufe 0 geschrieben — kein `imgcodecs`, roher Pixelpuffer statt Datei,
`CV_8UC1`/`CV_8UC3` als Makro und nie als Zahl. **Die Arbeit, die diesen Bericht so
kurz macht, ist dort schon getan worden.** Wäre eine einzige der drei Regeln verletzt
gewesen, stünde hier ein anderer Text.

Zwei Ehrlichkeiten dazu:

- **Der `-fexceptions`-Fehlschlag ist nicht beobachtet, sondern vorweggenommen.** Der
  erste OpenCV-WASM-Bau lief ohne den Schalter; er wurde neu gebaut, *bevor* etwas dagegen
  gebunden wurde. Dass ein `throw` ohne ihn zu `abort()` wird, steht in Emscriptens
  Dokumentation und ist hier **nicht** durch einen Absturz belegt. Es ist eine begründete
  Vorsichtsmaßnahme, keine Messung.
- **Gescheitert ist nur die Schale**, nicht die Werkzeugkette: ein `cmd /c` mit
  falsch geschachtelten Anführungszeichen („*Der Befehl … ist entweder falsch geschrieben
  oder konnte nicht gefunden werden*"). Das ist Windows-Zitierärger und keine Aussage über
  Emscripten — steht hier nur, damit niemand die leere Fehlerliste für Beschönigung hält.

---

## 4 · Größen

| Ziel | Bibliothek | Programm | gestrippt | daneben nötig |
|---|---:|---:|---:|---|
| Windows x64 | 329 KB `.lib` | 68 KB `.exe` | — | `opencv_world500.dll` **80 MB** |
| WASM | 21 KB `.a` | **2 377 KB** `.wasm` | — | 94 KB `.cjs`-Lader |
| Android arm64-v8a | 473 KB `.a` | 10 909 KB | **6 215 KB** | — (statisch) |
| Android armeabi-v7a | 352 KB | 6 920 KB | **3 113 KB** | — |
| Android x86 | 378 KB | 18 553 KB | 13 903 KB | — |
| Android x86_64 | 468 KB | 28 761 KB | 22 720 KB | — |

Die Spalte „Bibliothek" ist **nur unser eigener Objektcode** (`detect.cpp`), nicht das
OpenCV dahinter; sie ist deshalb nicht zwischen den Zielen vergleichbar — MSVC legt
LTCG-Zwischencode hinein, das NDK Debug-Angaben, Emscripten keins von beidem. Die Spalte
„Programm" ist die aussagekräftige: dort steckt alles drin.

Das Android-Programm trägt den **ganzen** Prüfstand samt statischem OpenCV; eine
`.so` für eine App wäre kleiner, weil `main`, `iostream` und die Fixture-Leserei
wegfallen. Die x86-Zahlen sind so viel größer als die ARM-Zahlen, weil die
Intel-Bibliotheken des SDK die SIMD-Verzweigungen für mehrere Befehlssätze mitführen.

### Und ein Nebenergebnis, das größer ist, als es aussieht

| | roh | gzip | brotli |
|---|---:|---:|---:|
| `aruco_conformance.wasm` (dieser Bau) | **2,38 MB** | 770 KB | **603 KB** |
| `@techstark/opencv-js` (Stufe 0) | 13,3 MB | — | 2,67 MB |

**Ein Viertel der Auslieferungsgröße** — und dabei steckt in unserem `.wasm` sogar noch
der Prüfstand mit `std::ifstream` und `printf`. Der Grund ist der aus §3: ein
allgemeiner `opencv.js` muss alles mitbringen, was irgendjemand aus JavaScript aufrufen
könnte; ein hineinübersetzter Kern nimmt nur, was er aufruft, und der Linker wirft den
Rest weg. Für ein Handy, das die Seite über Mobilfunk lädt, sind 2 MB weniger kein
Schönheitsfehler.

---

## 5 · Was **nicht** belegt ist

**Android ist ungemessen. Punktschluss.** Der Bau bindet für alle vier ABIs, das
Erzeugnis ist eine echte Android-`PIE`-Datei —

```
ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked,
interpreter /system/bin/linker64, for Android 24, built by NDK r27c (12479018)
```

— aber **keine einzige Zahl davon ist gemessen.** Auf diesem Rechner:

| Weg | Befund |
|---|---|
| Gerät am USB | `adb devices` → *List of devices attached* (leer) |
| Android-Emulator | `_toolchain\android-sdk\emulator` gibt es nicht, `system-images` auch nicht |
| Android Studio | `%LOCALAPPDATA%\Android\Sdk\emulator` gibt es nicht |
| WSL (x86_64-ELF ausführen) | *Der Windows-Subsystem für Linux ist nicht installiert* |
| Docker | nicht vorhanden |
| `qemu-aarch64` | nicht vorhanden |

Ein Emulator plus System-Abbild wäre ein Download von über einem Gigabyte und bräuchte
für die Beschleunigung Hypervisor-Rechte. **Beides war nicht Teil des Auftrags, und
raten ist keine Messung.** Es wäre leicht gewesen, aus „arm64 bindet und WASM stimmt"
ein „Android stimmt also auch" zu machen. Das steht hier ausdrücklich **nicht**.

**Was zu erwarten ist** — ausdrücklich als Erwartung und nicht als Ergebnis: arm64 bringt
NEON und damit `FMLA` von Haus aus mit; es liegt in dieser Hinsicht **auf derselben Seite
wie Windows** und nicht auf der von WASM. Nach der Erklärung aus §2 wäre also ein
Ergebnis nahe an Windows plausibler als eines nahe an WASM, und die Spanne über alle drei
Ziele bliebe bei wenigen `float32`-ULP. Vier ULP wären 0,0005 px und immer noch 1500-mal
unter der Toleranz. **Eine Erklärung ist keine Messung — nachzuprüfen bleibt es.**

**So geht es, sobald ein Gerät da ist** — der Prüfstand liest nur Dateien, es braucht
keine App:

```powershell
.\dev.ps1 build-core-android arm64-v8a
adb push core\build-android-arm64-v8a\aruco_conformance /data/local/tmp/
adb push core\build-android-arm64-v8a\fixtures          /data/local/tmp/fixtures
adb shell chmod 755 /data/local/tmp/aruco_conformance
adb shell /data/local/tmp/aruco_conformance /data/local/tmp/fixtures/fixtures.txt --ecken
```

Die Ausgabe der letzten Zeile geht dann durch `core/tools/compare_corners.py` gegen die
Windows-Ausgabe, und die Erwartung ist „wenige ULP".

**Ebenfalls ungemessen:**

- **Nur Chrome.** Firefox (SpiderMonkey) und Safari (JSC) sind andere WASM-Maschinen und
  nicht angefasst. Node und Chrome teilen sich V8, der Browser-Beleg ist also weniger
  unabhängig, als er aussieht.
- **Nur synthetische Szenen.** Wie die ganze Suite. Der Messschieber-Beleg
  (100 mm = 100 mm) hängt weiterhin allein an der Python-Kette.
- **Quergeprüft ist nur die Erkennung.** `core/` kann inzwischen die ganze Kette —
  Homographie, Kamerazerlegung, Dickenkorrektur, `LevMarq`, Entzerren, Umriss —, aber die
  Ecke-für-Ecke-Gegenüberstellung Windows gegen WASM in diesem Dokument deckt nur
  `detect_markers` ab. Für die JNI-Seite holt das `stage-4-android.md` nach (18 Größen je
  Szene, bitgenau); zwischen Windows und WASM steht es aus.
- **Kein Speicherbedarf gemessen.** Das WASM läuft mit `ALLOW_MEMORY_GROWTH` und
  8 MB Stapel gegen 2400×1800; ob ein Handy mit wenig RAM ein 12-MP-Foto verträgt, steht
  nicht fest.
- **Die 24 MB `_toolchain\opencv-wasm\` sind ein Bau von diesem Rechner.** Für eine
  Auslieferung gehört er eingefroren oder reproduzierbar nachgebaut.

---

## 6 · Fallen — gemessen, nicht geraten

**1 · `build_js.py` ist der falsche Weg für einen C++-Kern.** Es baut die
JavaScript-Bindungen mit; die dauern lang und werden nicht gebraucht. `BUILD_LIST` mit
sechs Modulen und `BUILD_opencv_js=OFF` genügt und ist in sieben Minuten fertig. Die
Whitelist in `opencv_js.config.py` betrifft **nur**, was JavaScript aufrufen darf — für
hineinübersetztes C++ ist sie belanglos.

**2 · Ohne `-fexceptions` stirbt der WASM-Bau stumm.** Kein Übersetzungsfehler, keine
Warnung: `throw` wird `abort()`, `catch` verschwindet. Der Prüfstand liefe scheinbar,
meldete aber bei jedem Fehler nur einen Abbruch ohne Text. Der Schalter muss an
**beiden** Enden stehen — am eigenen Kern *und* am OpenCV, gegen das er bindet.
(Vorweggenommen, nicht erlitten — siehe §3.)

**3 · `NODERAWFS` gibt es im Browser nicht.** Der Node-Bau liest die Fixtures direkt aus
dem Dateisystem — dasselbe Recht hat die Seite nicht. Deshalb gibt es ein zweites
Erzeugnis mit `--preload-file`; das kostet eine 26-MB-`.data` neben dem Bau. Und
`EXIT_RUNTIME` muss dort **aus** sein, sonst reißt `callMain` die Laufzeit ab und wirft
den Rückgabewert weg, statt ihn zurückzugeben.

**3a · `"type": "module"` in der Wurzel-`package.json` erschlägt Emscriptens Lader.**
Der PDF-Umzug nach JavaScript hat eine `package.json` ins Wurzelverzeichnis gelegt, und
die färbt **jede** `.js`-Datei darunter zum ES-Modul ein — auch eine erzeugte in
`core/build-wasm/`, die niemand je als Modul gemeint hat. Node bricht dann ab:

```
ReferenceError: require is not defined in ES module scope, you can use import instead
This file is being treated as an ES module because it has a '.js' file extension
and '...\package.json' contains "type": "module".
```

Der Node-Prüfstand heißt deshalb **`aruco_conformance.cjs`**
(`set_target_properties(... SUFFIX ".cjs")`) — diese Endung liest Node immer als
CommonJS, gleichgültig was darüber steht. Der Browser-Bau behält `.js`; ihn lädt ein
`<script src>`, und den kümmert `package.json` nicht.

Bemerkenswert daran ist, **wie** es gefunden wurde: beide Zweige waren für sich grün.
Der Fehler entstand erst beim Verschmelzen, und nur, weil vor dem Öffnen des PR ein
`git merge --no-commit origin/develop` samt Neubau gelaufen ist. Ein grüner
Feature-Zweig sagt bei zwei gleichzeitigen Umbauten eben nicht, dass der Stamm danach
grün ist.

**4 · Emscriptens Stapel ist 64 KiB groß.** Seit 3.1.27 die Vorgabe, native Ziele geben
Megabytes. OpenCVs Aufrufketten sind tief; hier steht deshalb `-sSTACK_SIZE=8MB`. Ein zu
kleiner Stapel äußert sich als Absturz irgendwo in `imgproc` und sieht nach einem
Datenfehler aus.

**5 · Ein Kreuzbau hat kein Ziel-Python, braucht aber ein Wirt-Python.** `pybind11` hat
bisher beides in einem erledigt. Fällt es weg, steht der Erzeugungsschritt ohne Python
da — und wenn man ihm irgendeines gibt, kann es das falsche `cv2` sein. Deshalb ist
`ARUCO_HOST_PYTHON` ein harter Fehler und keine Suche.

**6 · CMake 4.1 verwarnt die Toolchainfiles des NDK r27c:**

```
CMake Deprecation Warning at .../ndk/27.2.12479018/build/cmake/android.toolchain.cmake:35
  Compatibility with CMake < 3.10 will be removed from a future version of CMake.
```

Heute nur eine Warnung, dreimal je Konfiguration. Mit CMake 5 wird daraus ein Fehler, und
dann hilft nur ein neueres NDK oder `-DCMAKE_POLICY_VERSION_MINIMUM`. Wer in einem Jahr
einen kaputten Android-Bau vorfindet, sollte hier zuerst nachsehen.

**7 · Der Prüfstand rundet auf vier Stellen.** `0.2337 px` sieht auf drei Zielen gleich
aus und ist es nicht ganz. Ohne `--ecken` hätte dieses Dokument „bitgleich" behauptet und
sich geirrt. **Wer zwei Ziele vergleicht, vergleicht `%.17g`.**

**8 · Kurze Bauverzeichnisse.** `C:\ocvw` statt eines Pfades im Repo — nicht aus
Ordnungsliebe: OpenCVs Zwischenpfade sind tief, und MAX_PATH hat hier schon einmal einen
Bau zerlegt.

**9 · Die Bauverzeichnisse gehören nicht ins Repo.** `core/build-wasm/` und
`core/build-android-*/` stehen in `.gitignore`; zusammen sind es gut **230 MB** — davon
26 MB allein die `.data` des Browser-Baus —, das OpenCV-WASM-Bauverzeichnis noch einmal
83 MB. Alles davon ist mit zwei Kommandos wiederherstellbar.

---

## 7 · Was das für die nächsten Stufen heißt

**Die Modulliste trägt schon den ganzen Rest.** Nachgezählt an den Kopfdateien des
WASM-Installs: von den `cv2.*`-Aufrufen, die `app/` heute macht, ist **jeder einzelne**
in einem Modul erklärt, das dieser Bau enthält — außer `imread`/`imwrite`.

| gebraucht von `app/` | wohnt in | im WASM-Bau |
|---|---|---|
| `findHomography`, `getPerspectiveTransform`, `contourArea`, `convexHull`, `approxPolyDP`, `intersectConvexConvex` | `geometry` | ✅ |
| `warpPerspective`, `cvtColor`, `createCLAHE`, `Canny`, `threshold`, `morphologyEx`, `GaussianBlur`, `findContours`, `putText`, `polylines`, `circle` | `imgproc` | ✅ |
| `split`, `merge`, `bitwise_not`, `convertScaleAbs` | `core` | ✅ |
| ArUco mit `CORNER_REFINE_SUBPIX` | `objdetect` | ✅ |
| `scipy.optimize.least_squares` → `cv::LevMarq` | `geometry` | ✅ |
| `imread`, `imwrite` | `imgcodecs` | ❌ **abgeschaltet** |

`solvePnP`, `undistortPoints` und `Rodrigues` liegen in OpenCV 5 ebenfalls in
`geometry` — der Weg für die Kamerazerlegung ist also offen, ohne die Modulliste
anzufassen. **`calib` wird nicht gebraucht**: `calibrateCamera` benutzt `app/` nicht.

`imread`/`imwrite` sind kein Verlust. Sie stehen in `pipeline.py` und `session.py`, also
bei den Vorschaudateien, nicht in der Messung — und `core/` fasst sie ohnehin nicht an.

**Der Rest von Stufe 2 kann also portiert werden, ohne dass sich an dieser
Werkzeugkette etwas ändert.** Was neu dazukäme, wäre nur eine Bindung: das Python-Modul
gibt es schon, ein `embind`-Aufsatz für JavaScript und eine JNI-Schicht für Android
fehlen noch. Beides ist Verdrahtung, keine Messtechnik.

---

## 8 · Nachvollziehen

```powershell
# 1 · OpenCV fuer WASM (einmalig, ~7 min) - der Befehl steht vollstaendig in Abschnitt 3
#     danach das Install nach _toolchain\opencv-wasm\ kopieren

# 2 · Alle drei Ziele
.\dev.ps1 build-core                       # Windows + Python-Modul
.\dev.ps1 build-core-wasm                  # Emscripten, misst gleich unter Node
.\dev.ps1 build-core-android arm64-v8a     # NDK - bindet nur

# 3 · Die Suite, gegen beide Kerne
.\venv\Scripts\python.exe -m pytest                      # 183 passed
$env:ARUCO_CORE='cpp'; .\venv\Scripts\python.exe -m pytest  # 183 passed

# 4 · Ecke fuer Ecke
.\core\build\aruco_conformance.exe core\build\fixtures\fixtures.txt --ecken `
    | Select-String '^ecke ' | Set-Content windows.txt
<emsdk>\node\24.19.0_64bit\node.exe core\build-wasm\aruco_conformance.cjs `
    core\build-wasm\fixtures\fixtures.txt --ecken `
    | Select-String '^ecke ' | Set-Content wasm.txt
.\venv\Scripts\python.exe core\tools\compare_corners.py windows.txt wasm.txt Windows WASM
#   Ecken verglichen:                 64
#   davon verschieden:                 5
#   das sind:                          1 float32-ULP
```

Gelaufen am 2026-09-08: **183 passed** mit dem Python-Kern, **183 passed** mit
`ARUCO_CORE=cpp`, **BESTANDEN** vom Prüfstand auf Windows, unter Node und in Chrome 152.
