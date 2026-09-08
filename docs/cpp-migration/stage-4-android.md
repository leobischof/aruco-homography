---
title: Stufe 4 · Die Android-App — Ergebnis
description: "Stufe 4: was die Android-App heute wirklich kann, was nur gebaut ist, und wie man sie auf ein Telefon bringt"
audience: developer
status: current
updated: 2026-09-08
---

# Stufe 4 · Die Android-App — Ergebnis

> **Die App rechnet die ganze Kette: Foto → Marker → Ausgleich → Kamerapose → Entzerren →
> Schablonen-PDF. Ohne Server, ohne Netz, im nativen Kern.** Die **C-Schnittstelle** und
> die **JNI-Schicht** kannten bis zu dieser Stufe nur `detect_markers` — `core/src/` konnte
> den Rest längst, aber allein der Browser-Bau kam über `embind` daran. Jetzt geht jeder
> Rechenschritt auch durch die C-Grenze. `web/vision/` hat dafür **drei neue Dateien
> bekommen und keine einzige geänderte**.
>
> **Am 08.09.2026 ist die App auf einem Telefon gelaufen.** Xiaomi 2312DRA50G, Android 15
> (API 35), System-WebView 152.0.7977.64, Seitengröße 4096 B, arm64-v8a. Der Prüfstand hat
> **bestanden**: beide Szenen `größter Eckfehler 0,2337 px` bei 0,7500 px Toleranz, 4/4
> Marker, 83 bzw. 84 ms — und **beide SHA-256 genau die, die [§6](#6--auf-ein-telefon-bringen)
> vorhergesagt hatte**. Der native Kern rechnet auf einem echten Gerät bitgleich zu dem auf
> diesem Rechner, und Androids PNG-Dekoder liefert dieselben Pixel wie `cv2`.
>
> **Derselbe Lauf hat zwei Fehler gefunden, die keine Prüfung hier finden konnte:** die App
> zeichnete unter Status- und Navigationsleiste, und der Export brach ab — nicht am Rechnen,
> sondern am Speicher, mit einer Meldung, die keinen Grund nannte. Beides ist behoben; auf
> einem Gerät nachgesehen ist keine der beiden Behebungen.
>
> **Auf diesem Rechner läuft weiterhin kein Android** — kein Gerät, kein Emulator, kein
> System-Abbild. Alles Übrige ist hier belegt: die **JNI-Schicht auf einer echten JVM**
> (bitgenau gegen denselben Kern durch pybind11) und die **JavaScript-Hälfte in einem echten
> Chromium**, geladen aus dem gebauten APK. Was das nicht misst, steht in
> [§7](#7--was-nicht-belegt-ist).

> **Stand:** 2026-09-08 · Zweig `feat/android-full-chain` · Belege in `core/`, `android/`,
> `web/vision/`, `dev.ps1`

---

## 1 · Gemessen gegen nur gebaut

Die Trennlinie ist die einzige Aussage dieses Dokuments, die zählt.

| | Status |
|---|---|
| **Die ganze Rechenkette** durch die **C-Schnittstelle** und die **JNI-Schicht** auf einer echten JVM | **gemessen**: 18 Größen je Szene, alle bitgenau gleich zu demselben Kern durch pybind11 |
| Die beiden Rasterbilder (entzerrt, aufbereitet) durch JNI | **gemessen**: 5 870 400 B und 6 067 200 B, SHA-256 identisch |
| `detect_markers` durch C-Schnittstelle und JNI | **gemessen**, 64/64 Ecken identisch, 0 float32-ULP |
| RGBA→BGR-Weg der JNI-Schicht (der, den Android geht) | **gemessen**, 36/36 Werte identisch zum BGR-Weg |
| Modulbits des Markerblatts gegen `cv2` | **gemessen**, 4/4 Muster byteweise gleich |
| Die vier Testläufe (`ARUCO_CORE` × `ARUCO_PDF`) | **gemessen**, je **183 passed** |
| Die JavaScript-Einheitentests, inkl. der neuen Brücke | **gemessen**, **24/24** |
| `libaruco_core.so` für vier ABIs: ELF, 16-KB-Ausrichtung, Symbole | **gemessen** am Erzeugnis |
| APK: Inhalt, ABIs, Rechte, `zipalign -P 16`, Signatur | **gemessen** am Erzeugnis |
| **Die Kette aus dem APK** in einem echten Chromium bis zum PDF | **gemessen** — mit **drei Ersatzstücken**, siehe [§5](#5--die-kette-im-chromium--was-der-beleg-wert-ist) |
| Das dabei entstandene Schablonen-PDF, an den Vektoren nachgemessen | **gemessen**: 3 Seiten je 210,000 × 297,000 mm, 13 Rasterabstände alle 50 mm |
| **Der Prüfstand auf einem echten Telefon** | **gemessen** (08.09.2026, Xiaomi 2312DRA50G, Android 15): BESTANDEN, 0,2337 px je Szene, beide SHA-256 wie vorhergesagt |
| Start, Importkarte und `CoreBridge` **auf dem Gerät** | **gelaufen** — die App startet, die Oberfläche lädt, Foto und Entzerren gehen durch |
| **Der Export bis zum PDF auf dem Telefon** | **abgebrochen** (Speicher), behoben — [§6](#und-der-fehler-den-nur-ein-telefon-finden-konnte) |
| **Der sichere Bereich auf dem Gerät** | **nicht gemessen** — die Wirkung ist in einem Chromium nachgemessen, die vier Zahlen dort gesetzt statt gemeldet ([§7](#7--was-nicht-belegt-ist)) |
| Die Kette **Foto → Marker → Millimeter** an einem Gegenstand bekannter Länge | **weiterhin offen** — auf jedem Ziel, nicht nur hier |

---

## 2 · Was die App heute tut

### Die vollständige Oberfläche, unverändert

Der Knopf **„Oberfläche öffnen"** führt in `app/static/` — Byte für Byte die Oberfläche vom
Rechner. Dort geht jetzt **alles**: Foto laden, entzerren, Regler, Zuschnitt, Umriss,
Vorschau, Export als gekacheltes Schablonen-PDF, Speichern und Teilen über die
Systemdialoge. Kein Schritt bricht mehr mit einer Meldung ab.

Dazu die eigene Seite der Hülle (`android/app/src/main/assets/www/native/`) mit vier
Abschnitten — Rechenkern, Prüfstand, Detektor am Foto, Markerblatt. Sie ist die Diagnose,
nicht das Produkt: **der Knopf, der den Satz „Android ist ungemessen" gestrichen hat.**
Am 08.09.2026 gedrückt — und er hat nicht nur `BESTANDEN` gesagt, sondern die
vorhergesagten Zahlen auf die Stelle genau geliefert. Ein Prüfstand, der nur
„in Ordnung" sagt, hätte das nicht gezeigt.

### Der Aufbau

```
WebView (https://appassets.androidplatform.net/  ->  assets/www/)
   |
   |-- /index.html          app/static/, unveraendert
   |-- /native/index.html   die eigene Seite der Huelle
   |-- /web/vision/         die Rechenkette in JavaScript
   |-- /web/pdf/            der PDF-Bau in JavaScript
   |-- /shared/             constants.json
   |
   |  bridge-shim.js (addDocumentStartJavaScript, laeuft vor jedem Seitenskript)
   |     - ARUCO_TRANSPORT = "local"   -> rechnen in der Seite, kein Server
   |     - Importkarte: core.js -> core-android.js, image.js -> image-android.js
   |     - window.__aruco: die Bruecke nach Java
   |     - blob:-Anker abfangen, PDF in Scheiben hinausreichen
   |     - window.__arucoInsets: der sichere Bereich als CSS-Variablen
   v
Java  (WebBridge -> MainActivity -> CoreBridge -> NativeImages)
   |
   v  JNI  (21 Einsprungpunkte)
libaruco_core.so   ->   derselbe core/ wie auf Windows und im Browser
```

### Die eine Datei, die den Unterschied macht

`web/vision/core.js` ist im Browser-Bau die **einzige** Datei, die den Rechenkern kennt.
Alles darüber — `solve.js`, `rectify.js`, `extent.js`, `contour.js`, `camera.js`,
`enhance.js`, `pipeline.js`, `local.js` — ruft nur sie. Der Android-Anteil ist deshalb
genau das: **ein zweites `core.js`**, das statt zu WebAssembly zu JNI greift.

```
web/vision/core-android.js    der Kern ueber die Bruecke statt ueber WASM
web/vision/image-android.js   Bildbytes aus Java statt aus einer Leinwand
web/vision/core-android.test.mjs
```

Drei neue Dateien, **null geänderte**:

```
$ git diff --stat 086a725 HEAD -- web/ app/static/
 app/static/i18n/de.json          |   3 +-
 app/static/i18n/en.json          |   3 +-
 web/vision/core-android.js       | 199 +++++
 web/vision/core-android.test.mjs | 286 +++++
 web/vision/image-android.js      |  90 +++
```

Die beiden Katalogzeilen sind die Meldung „dieser Schritt ist nicht nativ", die es nicht
mehr gibt, und der Abschnittstext, der sie ankündigte.

Getauscht werden die beiden Dateien durch eine **Importkarte mit URL-Schlüsseln**:

```json
{ "imports": {
    "/web/vision/core.js":  "/web/vision/core-android.js",
    "/web/vision/image.js": "/web/vision/image-android.js" } }
```

Die Karte löst beide Seiten gegen den Ursprung der Seite auf und vergleicht die
**aufgelösten** Adressen. `import { core } from "./core.js"` in `web/vision/solve.js` zeigt
damit auf `core-android.js`, ohne dass `solve.js` etwas davon wüsste. Das war die riskanteste
Annahme dieser Stufe und ist an einem echten Chromium nachgemessen: `core.js` wird nie
geholt — es liegt gar nicht erst im APK, und mit ihm nicht das 3,6 MB große `.wasm`.

**Greift die Karte nicht, scheitert die Seite laut** (Modul nicht gefunden). Das ist
Absicht. Die stille Alternative wäre ein zweiter Rechenkern im Gepäck.

### Der sichere Bereich — vier Zahlen von Java in die Stilvorlage

Android 15 zwingt jede App mit `targetSdk = 35` **unter die Systemleisten**; die Abmeldung
davon ist abgekündigt. Wer seinen Inhalt dann nicht selbst einrückt, legt die Kopfzeile
unter die Uhr und den Fuß hinter die Navigationsleiste. Genau so ist es von einem Xiaomi
2312DRA50G mit Android 15 gemeldet worden.

`env(safe-area-inset-*)` allein trägt das **nicht**: die WebView füllt daraus nur die
Display-Aussparung, nie die Systemleisten — der untere Wert, also genau der gemeldete
Fehler, bliebe 0. Deshalb misst `MainActivity` die Ränder selbst
(`systemBars() | displayCutout()`), rechnet sie in dip um und ruft `window.__arucoInsets`;
der Shim schreibt sie als Inline-Stil auf `:root`.

Für die Oberfläche ist das **kein zweiter Weg**. `app/static/css/tokens.css` erklärt
dieselben vier Namen aus `env()`, und ein Inline-Stil schlägt eine Regel:

| Ziel | woher `--safe-*` kommt | Wert |
|---|---|---|
| Desktop, Browser | `env(safe-area-inset-*)` in `tokens.css` | 0 (Fenster ohne Aussparung) |
| Android | `window.__arucoInsets` aus `MainActivity` | gemessen, in dip |

Benutzt werden sie an **drei** Stellen und nirgends sonst: `.app-header` addiert oben (damit
die Kartenfläche bis unter die Statusleiste reicht), `body` addiert unten, links und rechts.
Der Fuß bekommt nichts Eigenes — sonst zählte eine Seite mit Kopf *und* Fuß doppelt.

**Auf Android 14 und darunter ändert sich nichts:** dort fügt sich das Fenster weiter in die
Systemleisten ein, die Ränder kommen als 0 an, das CSS addiert 0.

---

## 3 · Die C-Schnittstelle — wem gehört das Bild?

`capi.h` wächst von 6 auf **21** Funktionen. Gerechnet wird in keiner davon: sie reichen an
`core/src/` durch, das dieselben Schritte für den Browser-Bau längst tut. Sie zerfallen in
zwei Gruppen, und nur die zweite hatte eine Entwurfsfrage.

**Zahlen rein, Zahlen raus** (`core/src/capi_geometry.cpp`): `homography_from_quad`,
`homography_lmeds`, `refine_homography`, `fit_free`, `pose_from_homography`, `plane_extent`,
`convex_hull`, `convex_intersection_area`, `local_px_per_mm`, `quad_area`, `output_size`.
Punktlisten flach als `x,y,x,y`, Homographien als neun Zahlen zeilenweise, Ergebnis über
Ausgabezeiger, Rückgabewert ist der Status. Nichts daran ist neu — es ist die Hausform aus
`capi.h`, elfmal angewandt.

**Bilder raus** (`core/src/capi_image.cpp`): `rectify`, `adjust`, `is_identity`,
`find_contour_mm`. Hier steht die Entscheidung:

> **Der Aufrufer stellt den Puffer.**

Der Browser-Bau (`core/bindings/web.cpp`) gibt ein `Raster` zurück, das JavaScript freigeben
muss; `web/vision/core.js` existiert unter anderem dafür, dass niemand sonst `delete()`
schreiben muss. Auf einem Telefon wäre derselbe Fehler teurer: ein entzerrtes 300-dpi-Raster
sind zweistellige Megabyte, und `pipeline.js` legt bei **jeder Reglerbewegung** ein neues an.
Drei vergessene, und Android beendet den Prozess. Was der Bediener meldet, ist dann „das
dritte Foto war schlecht".

Der Aufrufer *kann* den Puffer stellen, weil die Größe vorher feststeht: `aruco_output_size`
für das Entzerren, Breite mal Höhe mal drei für die Aufbereitung. Es gibt nichts freizugeben,
also nichts zu vergessen; ein zu kleiner Puffer ist ein Fehlercode (`ARUCO_ERR_CAPACITY`)
und keine halb gefüllte Bildzeile. `aruco_rectify` rechnet die Größe **vor** dem Warp und
weist einen zu kleinen Puffer ab, statt erst zu arbeiten und dann zu scheitern.

**Was das kostet, ehrlich:** der Kern legt das Bild intern an und kopiert es hinüber — die
Speicherspitze ist das Doppelte der Ausgabe. Denselben Faktor zahlt der Browser-Bau
ohnehin. Ihn zu halbieren hieße, einen Ausgabepuffer bis nach `aruco::rectify`
durchzureichen und alle drei Bindungen anzufassen; das gehört in einen eigenen Schritt.

### Und wer räumt auf der Java-Seite auf?

`pipeline.js` ist im Browser eine gewöhnliche Funktionskette und soll das bleiben —
**dieselbe Datei** läuft dort. Sie kann also keine Griffe freigeben. Deshalb steht auf der
Java-Seite eine **Arena mit fester Kapazität** (`NativeImages`, drei Plätze):

- Das Foto ist **angeheftet** und wird nie verdrängt — es ist die Eingabe jedes Schritts.
- Ein neues Bild verdrängt das älteste. Bei drei Plätzen heißt das: das entzerrte Bild und
  seine Aufbereitung leben gleichzeitig, der Vorgänger nicht.
- Ein Griff auf ein verdrängtes Bild wirft eine benannte Ausnahme. **Falsche Pixel wären
  schlimmer als ein Abbruch:** sie sähen aus wie ein Messfehler.

Über die JavaScript-Grenze gehen **niemals Pixel**, nur `{handle, width, height, channels}`.
Die JPEG-Bytes für die Vorschau holt `image-android.js` als gewöhnliches `GET` über den
`WebViewAssetLoader` (`/api/raster/<griff>/<güte>.jpg`); das fertige PDF geht in
192-KB-Scheiben hinaus.

---

## 4 · Die Zahlen

### Die Bibliothek

Alle vier gebaut und alle vier nachgemessen (`./dev.ps1 check-android-so`):

| ABI | `libaruco_core.so` | vorher (nur Erkennung) | LOAD-Ausrichtung | exportierte Symbole |
|---|---:|---:|---|---:|
| **arm64-v8a** (im APK) | **7,69 MB** | 5,93 MB | 0x4000 (16 KiB) | 21 |
| armeabi-v7a | 4,10 MB | 2,97 MB | 0x4000 | 21 |
| x86 | 16,24 MB | 13,25 MB | 0x4000 | 21 |
| x86_64 | 25,92 MB | 21,67 MB | 0x4000 | 21 |

**+1,76 MB für die ganze Messkette** auf arm64-v8a. Das ist der Preis dafür, dass jetzt
`warpPerspective`, `findHomography`, `solvePnP`, CLAHE und die Konturensuche mit
hineingebunden werden — vorher warf der Linker sie weg, weil niemand sie rief. Die
Intel-Zahlen sind größer, weil die x86-Bibliotheken des OpenCV-SDK SIMD-Verzweigungen für
mehrere Befehlssätze mitführen (`stage-4-cross-targets.md`, Abschnitt 4).

Die **21** exportierten Symbole sind genau die JNI-Einsprungpunkte, und
`check-android-so` liest ihre Zahl aus `NativeCore.java` statt sie abzutippen: eine neue
native Methode, die im Bau nicht ankommt, fällt damit auf.

### Das APK

```
package: name='com.bischofsnowboards.aruco' versionCode='1' versionName='0.0.3-alpha'
sdkVersion:'24'          targetSdkVersion:'35'          compileSdkVersion='35'
native-code: 'arm64-v8a'
application-label:'ArUco-Homographie'
uses-permission: name='com.bischofsnowboards.aruco.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION'
```

| | |
|---|---|
| Größe | **10,29 MB** (Debug, nur arm64-v8a) |
| Einträge | 179, davon 62 unter `assets/www/` |
| Rechte | **keine.** Die eine Zeile oben ist eine App-eigene Marke, die AGP ab targetSdk 33 selbst einträgt — sie erlaubt nichts. **Kein `INTERNET`**, kein `CAMERA`, kein Speicherrecht. |
| `zipalign -c -P 16 -v 4` | bestanden |
| `apksigner verify` | gültig, `CN=Android Debug` |
| Pflichtdateien | 16 von 16 vorhanden |
| Verbotene Dateien | 0 von 4 — **kein `.wasm`, kein `core.js`**, keine `.test.mjs`, keine `image.js` |
| `versionName` | aus `app/config.py` (`APP_VERSION`), nicht abgetippt |

Die vier verbotenen Einträge sind der Kern dieser Stufe als Prüfung: läge `core.js` im APK,
holte die Seite bei einem Fehler in der Importkarte still den WebAssembly-Weg — und die
Architekturentscheidung „nativ je Ziel" wäre lautlos rückgängig gemacht. `check-apk` zählt
deshalb nicht nur, was da sein muss, sondern auch, was nicht da sein darf.

**Ohne Netzberechtigung ist „offline" eine Zusicherung des Systems** und nicht eine des
Programmierers: die App *kann* nicht senden. Fotos kommen über `ACTION_OPEN_DOCUMENT`,
PDFs gehen über `ACTION_CREATE_DOCUMENT` — beide geben dem Benutzer die Wahl und der App
nur die eine Datei, ohne jedes Speicherrecht.

### Die JNI-Schicht auf einer echten JVM

`./dev.ps1 check-jni` übersetzt `jni.cpp` und `jni_chain.cpp` als Windows-DLL gegen die
`jni.h` des JDK und ruft sie aus einem echten Java-Prozess auf — mit `NativeCore.java`,
also der Klasse der App. Verglichen wird gegen **denselben Kern durch pybind11**, mit
`Double.compare(...) != 0`: null Toleranz.

```
Kette flat (2400x1800)              Kette thick (2400x1800)
  quad_area          4 Werte identisch        4 Werte identisch
  h_quad             9 Werte identisch        9 Werte identisch
  h_lmeds            9 Werte identisch        9 Werte identisch
  h_refined          9 Werte identisch        9 Werte identisch
  fit_free          15 Werte identisch       15 Werte identisch
  pose               4 Werte identisch        4 Werte identisch
  hull               8 Werte identisch        8 Werte identisch
  extent             4 Werte identisch        4 Werte identisch
  local_px_per_mm    1 Wert  identisch        1 Wert  identisch
  intersection       1 Wert  identisch        1 Wert  identisch
  preview_size       2 Werte identisch        2 Werte identisch
  export_size        2 Werte identisch        2 Werte identisch
  rectify_sha  5 870 400 B, SHA-256 gleich    5 870 400 B, SHA-256 gleich
  close_size         2 Werte identisch        2 Werte identisch
  close_sha    6 067 200 B, SHA-256 gleich    6 067 200 B, SHA-256 gleich
  is_identity        2 Werte identisch        2 Werte identisch
  adjust_sha   6 067 200 B, SHA-256 gleich    6 067 200 B, SHA-256 gleich
  contour            8 Werte identisch        8 Werte identisch
```

**Die Rasterbilder sind bytegleich, nicht nur ähnlich.** Ein Bild über eine Grenze zu
schieben, ohne eine Zeile zu verschieben oder Rot und Blau zu tauschen, ist genau die
Sorte Fehler, die eine Toleranzprüfung durchlässt und ein Messschieber findet — deshalb
SHA-256 und keine Norm.

Daneben, in Millimetern statt in Bits, gegen die **Python-Referenz**:

| | `flat` | `thick` |
|---|---:|---:|
| Ausdehnung der Ebene | 2,016e-06 mm | 1,693e-06 mm |
| Zuschnitt | 2,016e-06 mm | 1,693e-06 mm |
| Kamerahöhe | 8,012e-09 mm | 1,024e-08 mm |
| Maßstab | 5,400e-12 px/mm | 8,229e-12 px/mm |
| Rastergröße bei 300 dpi | 14860 × 11362 px, beide Seiten gleich | 14860 × 11362 px, beide Seiten gleich |

Zwei Nanometer auf einer Ausdehnung von rund 1250 mm. **Das ist kein Messunterschied,
und es ist auch nicht Rundung:** `refine_homography` ist in Python eine
scipy-Ausgleichsrechnung und in C++ `cv::LevMarq`. Zwei Verfahren auf demselben Problem
enden nicht auf demselben Bit, und die Ausdehnung ist die einzige Größe, die weit genug
hinter der Homographie steht, um es überhaupt zu zeigen. Dieselben vier Zahlen, in
derselben Größenordnung, misst `stage-4-windows-exe.md` an der ausgelieferten `.exe`.
Deshalb ist die JNI-Prüfung gegen den **C++-Kern** bitgenau und die gegen **Python** in
Millimetern angegeben: nur die erste darf null Toleranz haben.

Die Ecken bleiben, was sie waren:

```
C++ direkt  vs  C-Schnittstelle          64 Ecken, 0 verschieden, 0.0 px, 0 float32-ULP
C++ direkt  vs  JNI auf der JVM          64 Ecken, 0 verschieden, 0.0 px
RGBA-Weg    vs  BGR-Weg (in der JVM)     36 Werte, identisch, beide Szenen
Modulbits   vs  cv2                      4 Marker, 6x6, byteweise gleich
```

Der größte Eckfehler ist **0,2337 px** bei 0,75 px Toleranz — dieselbe Zahl wie auf Windows
und im Browser. Die neuen Schichten verschieben **nichts**.

### Die Testläufe

```
183 passed   ARUCO_CORE=python  ARUCO_PDF=python
183 passed   ARUCO_CORE=python  ARUCO_PDF=js
183 passed   ARUCO_CORE=cpp     ARUCO_PDF=python
183 passed   ARUCO_CORE=cpp     ARUCO_PDF=js
 18 passed   node --test  (web/**/*.test.mjs, davon 6 neu fuer die Android-Bruecke)
```

---

## 5 · Die Kette im Chromium — was der Beleg wert ist

`check-apk` misst das Erzeugnis, `check-jni` misst die native Schicht. Dazwischen liegt
alles, was in der WebView passiert: die Importkarte, die beiden Android-Dateien und
darüber die unveränderte Kette bis zum PDF. Das war der Teil, den nie jemand laufen sah.

`./dev.ps1 check-android-ui` **packt `assets/www/` aus dem gebauten APK aus**, liefert es
aus und fährt ein kopfloses Chromium durch Hochladen, Ausgleich, Regler, Export und die
Übergabe des Blobs. Geladen werden die Bytes, die ausgeliefert werden — der Baum wird
ausgepackt, nicht nachgebaut. Gesteuert wird der Browser über sein eigenes Debug-Protokoll
(CDP) aus Node 22; kein Playwright, keine 150 MB Nachladung.

```
upload: 2400x1800 px, Marker-Kante 67 mm
solve: 4 Marker, rms_px=0.095, rms_mm=0.0495, mm_per_px=0.52
adjust: Vorschau als Blob, 1.2717 px/mm
export: 3 Seiten, 210.000x297.000 mm, 155255 Bytes
uebergeben: schablone.pdf, 155255 Bytes, identisch zum Blob: true
```

`rms_px=0.095`, `rms_mm=0.0495` und `mm_per_px=0.52` sind **dieselben Zahlen**, die der
Server auf dem Rechner und der Browser-Bau für diese Szene liefern
(`stage-4-web.md`). Und die Übergabe verliert nichts: der Blob kommt auf der anderen Seite
der Brücke mit derselben Byte-Zahl an — die Scheiben sind Vielfache von 3, sonst ergäben
zwei aneinandergehängte Base64-Stücke Unsinn.

Danach zählt `android/tools/measure_template.py` nach, was auf dem Blatt steht — an den
**Vektoren** im PDF, nicht an einer Rasterung, die ihre eigene Ungenauigkeit mitbrächte:

```
3 Seiten, jede 210.000 x 297.000 mm
13 Rasterabstaende, alle 50 mm, groesste Abweichung 6.0000 nm
```

### Drei Ersatzstücke, und der Prüfer sagt sie bei jedem Lauf

1. **Die Java-Seite ist ein Nachbau** (`android/tools/bridge-stub.mjs`) — eine
   JavaScript-Nachbildung von `CoreBridge.java`. Sie ist mit
   `web/vision/core-android.test.mjs` **geteilt** und nicht zweimal geschrieben: zwei
   Nachbauten einer Klasse sind zwei Stellen, an denen sie auseinanderlaufen können.
2. **Der Rechenkern ist der WebAssembly-Bau desselben `core/`**, nicht
   `libaruco_core.so`. Dieselbe C++-Funktion, anderes Ziel. Dass die JNI-Schicht bitgenau
   dasselbe liefert, misst `check-jni` auf einer echten JVM — das ist die andere Hälfte
   des Belegs, und nur beide zusammen decken die Kette ab.
3. **Chromium auf Windows ist nicht die System-WebView eines Telefons.**

Was das **nicht** misst: Androids Linker, die WebView, die Kamera-Wege, den Speicherbedarf
auf einem Gerät. Was es misst: dass diese Kette, in dieser Reihenfolge, mit diesen Dateien
ein maßhaltiges PDF ergibt.

**Und was auch diese Messung nicht sehen kann**, weil es keine Messung dieser Art kann:
Raster und Seitengröße zeichnet die PDF-Schicht aus **denselben** Millimeterzahlen, in
denen der Zuschnitt angegeben ist. Läge die Homographie daneben, käme die Schablone falsch
groß heraus, und dieses Raster mäße trotzdem tadellos. Diesen Fehler fängt allein die
Bitgleichheit gegen Python und den C++-Kern.

---

## 6 · Auf ein Telefon bringen

**Der wichtigste Abschnitt dieses Dokuments.** Alles darüber ist Vorarbeit.

### Einmalig am Telefon

1. **Einstellungen → Über das Telefon → siebenmal auf „Build-Nummer" tippen.**
2. **Einstellungen → System → Entwickleroptionen → USB-Debugging einschalten.**
3. Telefon per USB anstecken, „USB-Debugging zulassen?" bestätigen.

### Am Rechner

```powershell
cd <repo>
.\dev.ps1 build-apk                 # baut .so + APK und misst beides nach

$adb = "..\_toolchain\android-sdk\platform-tools\adb.exe"
& $adb devices                      # muss das Telefon zeigen, nicht "unauthorized"
& $adb install -r android\out\aruco-homographie-debug.apk
& $adb shell am start -n com.bischofsnowboards.aruco/.MainActivity
& $adb logcat -s ArUco              # laufen lassen: hier landen alle Meldungen der Seite
```

Zum Schluss **`& $adb kill-server`** — der Dienst läuft sonst im Hintergrund weiter.

### Was der erste Lauf auf einem Telefon ergab

**08.09.2026 · Xiaomi 2312DRA50G · Android 15 (API 35) · WebView 152.0.7977.64 ·
arm64-v8a · Seitengröße 4096 B · App 0.1.0-alpha**

| | |
|---|---|
| **Prüfstand** | **BESTANDEN.** `flat` 0,2337 px in 83 ms, `thick` 0,2337 px in 84 ms, je 4/4 Marker, Toleranz 0,7500 px |
| Die beiden SHA-256 | **genau die vorhergesagten** — `da8c60f0…` und `c3695fe4…` |
| App starten, Oberfläche, Foto, Entzerren, Zuschnitt | **ging durch** |
| **Schablone erzeugen** | **brach ab** — siehe unten |

**Die beiden SHA-256 sind der eigentliche Fund.** Sie sagen, dass Androids PNG-Dekoder
**dieselben Pixel** geliefert hat wie `cv2` auf diesem Rechner — und erst deshalb ist der
gleiche Eckfehler eine Aussage über den *Detektor* und nicht über das *Laden*. Ohne die
Prüfsumme wäre ein abweichender Dekoder als Detektorfehler durchgegangen, oder umgekehrt.

#### Und der Fehler, den nur ein Telefon finden konnte

„Schablone erzeugen" brach ab mit:

```
Error invoking core: Java exception was raised during method invocation
```

**Dieser Satz stammt von Chromium, nicht von dieser App.** So meldet die WebView eine
`@JavascriptInterface`-Methode, die geworfen hat, ohne dass jemand fing — und mehr sagt sie
nicht. Der Bediener sah, *dass* etwas schiefging, und nie *was*.

Geworfen hatte `ByteBuffer.allocateDirect`: der Vorgabeausschnitt ergab bei 300 dpi ein
Raster von rund **169 Megapixeln**, also **506 MB** — und weil `runExport` das entzerrte
Raster und seine aufbereitete Fassung gleichzeitig hält, das Doppelte davon. Ein Telefon
hat das nicht.

**Zwei Fehler, die sich gegenseitig unsichtbar machten:**

1. **`WebBridge` fing `Exception`.** `OutOfMemoryError` ist ein `Error`, kein `Exception` —
   genau der Fall, um den es hier geht, fiel durch den Fang hindurch. Jetzt wird `Throwable`
   gefangen. Ein fehlgeschlagenes `allocateDirect` hat nichts halb geschrieben, die Arena in
   `NativeImages` ist unverändert, und die App darf danach weiterlaufen.
2. **Die Obergrenze war eine Aussage über das Format, nicht über die Maschine.**
   `checkOutputBudget` gab es längst, aber sie maß gegen `MAX_OUTPUT_MPX` = 300 aus
   `shared/constants.json`. 300 MPx sind auf dem Schreibtisch in Ordnung und auf einem
   Telefon der sichere Tod. Jetzt meldet `NativeImages.budgetMegapixels` den wirklich
   verfügbaren Speicher, `bridge-shim.js` reicht ihn an die Seite, und `outputBudgetMpx()`
   nimmt **die kleinere** der beiden Zahlen. Ein Gerät kann die Grenze senken, nie heben.

Der Abbruch fällt damit in `output_too_large` — eine übersetzte Meldung, die eine kleinere
Auflösung oder einen kleineren Ausschnitt vorschlägt, und zwar nur eine, die auch wirklich
passt. `web/vision/budget.test.mjs` hält das fest: bei 40 MPx Budget wird derselbe Export
mit `limit_mpx: 40` und `megapixels: 169` abgewiesen, bei 300 MPx geht er durch.

> **Was das NICHT ist: die eigentliche Lösung.** Die wäre, die Entzerrung zu kacheln, damit
> nie ein Riesenraster entsteht — `buildPdf` bettet heute ein einziges JPEG für alle Kacheln
> ein, das ginge also nicht ohne `web/pdf/build.js`. Bis dahin bekommt der Bediener eine
> verständliche Meldung statt eines Absturzes, und er kann die Auflösung senken. **Auf einem
> Telefon nachgemessen ist auch das noch nicht** — geprüft ist die JavaScript-Hälfte hier.

### Was zu tippen ist, und was dabei herauskommen muss

| Schritt | Erwartung | Wenn nicht |
|---|---|---|
| App startet | Die Seite **„Auf diesem Gerät"** mit gefüllter Tabelle: `OpenCV 5.0.0`, `DICT_4X4_50 (50)`, `67,0 mm`, `arm64-v8a` | Rote Zeile statt Tabelle: `libaruco_core.so` hat nicht geladen — siehe Falle 1 |
| **Seitengröße** in der Tabelle | `4096 B` oder `16384 B` | Bei `16384` ist es ein 16-KB-Gerät. Dass die App startet, ist dann der Beleg für die Ausrichtung. |
| **„Prüfstand laufen lassen"** | **BESTANDEN**, je Szene `größter Eckfehler 0,2337 px (Toleranz 0,7500 px)` | Andere Zahlen: **das ist ein Befund**, kein Rundungsfehler. Bitte melden. |
| Die SHA-256-Zeile darunter | `flat`: `da8c60f0d419cd7035f4bd1ee3bb13190e4507cd16507ddd0202e924601156f4`<br>`thick`: `c3695fe476f79854dc64c1c138303236b735a6c26c884a66fe8c0978ef18e374` | Weicht sie ab, hat Androids PNG-Dekoder **andere Pixel** geliefert als `cv2` — dann liegt der Unterschied im Laden, nicht im Detektor. |
| **„Oberfläche öffnen"** → Foto laden → **„Entzerren"** | Eine entzerrte Vorschau mit Maßstab in Millimetern. **Das ist der Schritt, der bis zu dieser Stufe abbrach.** | Eine Meldung „android_bridge_failed": die Brücke lief, der Kern nicht — der Grund steht im `logcat`. Eine Meldung über ein fehlendes Modul: die Importkarte hat nicht gegriffen (Falle 13). |
| Regler bewegen | Die Vorschau folgt. Nach ein paar Bewegungen **darf der Speicher nicht wachsen** — das ist die Arena, und sie ist auf einem Gerät ungemessen. | Stürzt die App nach mehreren Bewegungen ab, ist die Kapazität von `NativeImages` zu groß für dieses Gerät. |
| **Schablone erzeugen** bei 300 dpi und großem Ausschnitt | Entweder ein PDF — oder die Meldung *Die Ausgabe wäre zu groß* mit einem Vorschlag. **Beides ist richtig**; ein Abbruch ohne Grund ist es nicht. | Kommt wieder `Java exception was raised during method invocation`, wirft etwas anderes als der Speicher — der Grund steht dann im `logcat`. |
| **„Schablone erzeugen"** | Systemdialog, danach ein mehrseitiges PDF. Ausdrucken mit **100 %, nicht „an Seite anpassen"**. | Bleibt der Dialog aus, hat die `blob:`-Abfangstelle nicht gegriffen — siehe Falle 14. |
| Am Ausdruck: das **50-mm-Raster** mit dem Messschieber | 50,0 mm | — |
| Am Ausdruck: **ein Gegenstand bekannter Länge**, der mit auf dem Foto lag | seine wirkliche Länge | **Das ist die Messung, die dieses Projekt noch nie hatte** — auf keinem Ziel. Siehe [§7](#7--was-nicht-belegt-ist). |

**Die Zahlen, die zurückgemeldet gehören:** das Urteil des Prüfstands, der größte Eckfehler
je Szene, die beiden SHA-256 — und, falls ein Ausdruck entsteht, die nachgemessene Länge
des bekannten Gegenstands.

---

## 7 · Was **nicht** belegt ist

**Auf dem Bau-Rechner ist nichts von Android gelaufen.** `adb devices` leer, kein Emulator,
kein System-Abbild, kein WSL, kein Docker, kein `qemu-aarch64`. Was hier gemessen wurde, ist
am Erzeugnis gemessen (ELF, Zip, Signatur), auf einer JVM auf Windows gelaufen, oder in einem
Chromium auf Windows.

**Von einem Gerät gelaufen ist genau ein Weg: der aus
[§6](#was-der-erste-lauf-auf-einem-telefon-ergab)** — Start, Prüfstand, Oberfläche, Foto,
Entzerren, Zuschnitt, und der Export bis zu seinem Abbruch. Ein Gerät, ein Modell, eine
Android-Fassung. Die Zahlen dazu hat **das Gerät selbst** ausgerechnet und angezeigt; hierher
gekommen sind sie als Bildschirmfotos, nicht über ein Kabel.

Eingelöst durch diesen Lauf — hier nur, damit niemand sie zweimal aufschreibt:

- ~~Ob die App startet.~~ Sie startet, und die Tabelle war gefüllt: `libaruco_core.so` lädt.
- ~~Ob die Importkarte in der WebView des Geräts greift.~~ Sie greift, in WebView
  152.0.7977.64. **Eine ältere System-WebView ist damit nicht geprüft** — die kann es
  weiterhin zerlegen, und dann lädt die Seite gar nicht.
- ~~Ob `CoreBridge.java` dasselbe tut wie sein Nachbau.~~ Für die Wege, die der Prüfstand
  und das Entzerren nehmen: ja, und bitgenau. **Nicht** für die Wege, die der Lauf nie
  erreicht hat — die PDF-Scheiben, Speichern und Teilen.

Im Einzelnen weiterhin ungeprüft:

- **Ob der sichere Bereich auf dem Gerät richtig ankommt.** In einem Chromium ist die
  *Wirkung* nachgemessen — dieselbe `bridge-shim.js` aus dem APK, mit 38/0/48/0 dip
  aufgerufen: `padding-top` des Kopfes 14 → 52 px, `padding-bottom` des `body` 0 → 48 px,
  Unterkante des Fußes 844 → 796 px, und mit 0 wieder zurück auf den Ausgangswert.
  **Gemessen** hat die vier Zahlen dort niemand: Chromium meldet 0, und
  `WindowInsetsCompat` ist nicht nachgebaut.
- **Ob `NativeImages` mit drei Plätzen reicht.** Die Verdrängung ist nirgends unter Last
  gelaufen. Was der Lauf zeigte, ist die andere Hälfte: **ein einzelner Puffer kann zu groß
  sein**, und dagegen hilft die Kapazität nicht. Der Export begrenzt sich jetzt selbst
  ([§6](#und-der-fehler-den-nur-ein-telefon-finden-konnte)); ob die drei Plätze beim
  Reglerziehen reichen, ist damit nicht beantwortet. **Kein Speicher- und kein Zeitbedarf
  ist auf einem Gerät gemessen** — außer den 83 und 84 ms des Prüfstands.
- **Ob ein gekacheltes PDF in 192-KB-Scheiben durch die echte JavaScript-Brücke passt.**
  Im Chromium ja (155 kB in einem Stück Rechenzeit). `@JavascriptInterface` läuft auf dem
  JavaBridge-Faden und ist synchron; bei einem 40-MB-PDF sind das rund 220 Aufrufe, und wie
  sich das anfühlt, ist ungemessen.
- **Die Kamera-Wege** (`ACTION_IMAGE_CAPTURE`, `FileProvider`, `ACTION_CREATE_DOCUMENT`,
  `ACTION_SEND`) sind übersetzt, nicht ausgeführt.
- **Die EXIF-Drehung an einem echten Handyfoto.** Der Code löst alle acht Fälle auf; geprüft
  ist er gegen synthetische Bilder, nicht gegen eine Kamera.
- **Nur arm64-v8a im APK.** Die anderen drei ABIs sind gebaut und nachgemessen, aber nicht
  eingepackt (`./dev.ps1 build-apk arm64-v8a,armeabi-v7a`).
- **Kein Release-Bau, keine Signatur außer dem Debug-Schlüssel.**
- **Und die eine, die über allem steht: die Kette `Foto → Marker → Millimeter` ist nach wie
  vor nicht unabhängig belegt** — auf keinem Ziel. Belegt ist `PDF → Drucker → Papier`
  (Messschieber, 07.09.2026). Was fehlt, ist ein Gegenstand *bekannter* Länge mit auf dem
  Foto und derselbe Gegenstand auf dem Ausdruck nachgemessen. Alles in diesem Dokument sagt
  nur: **Android rechnet dasselbe wie Python.** Ob Python richtig rechnet, sagt es nicht.

---

## 8 · Fallen — gemessen, nicht geraten

**1 · Die `.so` muss auf 16 KiB ausgerichtet sein, sonst lädt sie GAR NICHT.** Neue
Android-Geräte legen Bibliotheken mit 16-KiB-Seiten ab; eine nur auf 4 KiB ausgerichtete
`.so` bringt die App beim Start zum Verschwinden, ohne dass ein Codefehler vorläge. Das NDK
r27 setzt `max-page-size=16384` per Vorgabe — hier steht es trotzdem ausdrücklich, und
`./dev.ps1 check-android-so` misst es mit `llvm-readelf -l` nach, statt es zu glauben. Dazu
gehört die **zweite, andere** Zusage: `zipalign -P 16`, also unkomprimiert und an einer
16-KiB-Grenze *im Zip*. Beide werden geprüft.

**2 · Ein Modul-Import über `file://` scheitert immer.** Der Ursprung einer file-URL ist
„opaque", und dagegen ist jeder `import` ein Verstoß gegen die Same-Origin-Regel.
`app/static/` IST ein Baum aus ES-Modulen. Deshalb der `WebViewAssetLoader` mit
`https://appassets.androidplatform.net/` — eine Adresse, die absichtlich nicht auflöst und
deshalb nie ins Netz geht.

**3 · Zwei MIME-Typen sind nicht verhandelbar.** `.js` muss `text/javascript` sein, sonst
weist die WebView das Modul ab; `.json` muss `application/json` sein, sonst scheitert
`import ... with { type: "json" }` — und daran hängt `shared/constants.json`, also jede
Konstante des Produkts. Beides steht in `MainActivity.mimeType`.

**4 · `shouldInterceptRequest` bekommt bei einem POST den Rumpf NICHT**, und
`PathHandler.handle(path)` sieht die **Abfrage nicht**. Beides sind Lücken im WebView-API,
und beide schneiden die Grenze: lesende Rasterbilder holt ein `GET`, dessen ganze Angabe im
**Pfad** steht (`/api/raster/<griff>/<güte>.jpg`, nicht `?q=`), alles andere geht über die
JavaScript-Brücke.

**5 · Ein `<input type="file">` tut in einer WebView von allein nichts.** Kein Dialog, keine
Meldung — bis `WebChromeClient.onShowFileChooser` da ist. Die dort gewählte URI wird
zusätzlich gemerkt, damit die Brücke das Bild daraus selbst laden kann: ein 12-MP-Foto als
Base64 durch die JavaScript-Grenze wären rund 48 MB Text.

**6 · Die EXIF-Drehung muss VOR der Erkennung angewandt werden.** `BitmapFactory` folgt der
EXIF-Marke nicht, Handys schreiben aber fast immer in Sensor-Ausrichtung.
`Photo.applyExifOrientation` löst alle acht Fälle auf, auch die gespiegelten: eine
Spiegelung dreht die Eckenreihenfolge um, und die Homographie wäre dann ebenfalls
gespiegelt — ein Ergebnis, das plausibel aussieht und in der Breite stimmt. `inScaled =
false` gehört dazu.

**7 · Ein direkter `ByteBuffer`, kein `byte[]`.** `GetByteArrayElements` darf kopieren (auf
Android tut es das), `GetPrimitiveArrayCritical` hält stattdessen den Speicherbereiniger an
— während einer Erkennung, die Sekunden dauert. Die JNI-Seite weist einen Heap-Puffer
deshalb ausdrücklich ab; dass sie das tut, ist gemessen.

**8 · Keine C++-Ausnahme darf durch einen JNI-Rahmen.** Sie ist dort nicht definiert; in der
Praxis stirbt der Prozess wortlos. Alle 21 C-Funktionen laufen deshalb durch dieselbe
`guarded`-Hülle und machen aus jeder Ausnahme einen Code plus Klartext. Dass ein falscher
Puffer eine `IllegalArgumentException` gibt und der Prozess weiterläuft, ist gemessen.

**9 · Gradle trägt aus `assets.srcDir()` KEINE Aufgabenabhängigkeit mit.** Weder aus einem
`TaskProvider` noch aus einem `Provider<File>`. Der Bau lief beide Male grün durch,
`gatherWebAssets` lief gar nicht, und im APK lag von der Oberfläche **nichts**. Ein leeres
APK ist von einem vollen nur an seiner Größe zu unterscheiden. Die Abhängigkeit steht jetzt
von Hand an den Merge-Aufgaben, und `check-apk` zählt 16 Pflichtdateien nach.

**10 · `apksigner` ist ein Java-Programm in einer `.bat`-Hülle.** Ohne `JAVA_HOME` bricht es
mit Rückgabewert 1 ab und sagt kein Wort über den Grund — das sieht nach einer ungültigen
Signatur aus und ist eine fehlende Werkzeugkette.

**11 · MAX_PATH.** Das Repo liegt rund 105 Zeichen tief, AGPs Zwischenpfade sind lang.
Gradle baut deshalb neben dem Repo (`aruco.buildRoot`), und `build-apk` holt das APK nach
`android/out/` zurück.

**12 · Die Kataloge liegen zweimal im APK.** Einmal unter `/i18n/` für die Oberfläche, einmal
unter `/app/static/i18n/` — dorthin zeigt der relative Import in `web/pdf/i18n.js`. Rund
30 KB. Der Ausweg wäre ein Bundler, den dieses Projekt bewusst nicht hat.

**13 · Eine Importkarte muss vor dem ERSTEN Modul-Import im Dokument stehen** — und zu dem
Zeitpunkt, zu dem `addDocumentStartJavaScript` läuft, ist `<head>` noch nicht geparst.
Deshalb hängt sie an `documentElement`, den es ab dem ersten Augenblick gibt. Eine zu spät
gesetzte Karte wird **stillschweigend ignoriert**: die Seite lädt dann `core.js`, sucht das
`.wasm` und bricht mit einem Ladefehler ab, der nach einem fehlenden Verzeichnis aussieht.

**14 · Ein `<a download>` mit `blob:`-Adresse tut in einer WebView nichts** — es gibt keinen
Downloadordner und keinen Betrachter dahinter. Und Java kann eine `blob:`-Adresse nicht
lesen; sie gilt nur im Fenster, das sie vergeben hat. Abgefangen werden **zwei** Wege: der
Klick auf einen Anker *im* Dokument (der steigt auf) und `link.click()` auf einen Anker, den
niemand eingehängt hat (der steigt **nirgendwohin** auf). Der zweite Fall ist der Export.
Wer nur die erste Stelle baut, bekommt einen Knopf, der still nichts tut.

**15 · `JSON.stringify` einer `Float64Array` ergibt ein Objekt mit Ziffernschlüsseln, keine
Liste.** `{"0":1.5,"1":2.5}` kommt auf der Java-Seite als leeres `JSONArray` an — also als
null Punkte, nicht als ein Fehler. Jede Punktliste geht deshalb durch `Array.from()`. Das
ist die stillste Falle dieser Stufe: die Kette rechnet weiter und liefert Unsinn.

**16 · Gleitkommazahlen überleben den Umweg über Text.** `Double.toString`,
`JSON.stringify` und Pythons `repr` schreiben alle die **kürzeste Zeichenkette, die sich
zurück in dieselbe Zahl liest**; `Double.parseDouble` liest sie zurück. Deshalb darf die
Brücke JSON sprechen, ohne ein Bit zu verlieren — und deshalb ist der Vergleich in
`ChainCheck.java` mit `Double.compare(...) != 0` möglich und nicht nur mit einer Toleranz.

---

## 9 · Nachvollziehen

```powershell
# 1 · Die ganze Kette durch die JNI-Schicht auf einer echten JVM (baut den Kern mit)
.\dev.ps1 check-jni
#   BESTANDEN - die JNI-Schicht liefert die Ecken der Grundwahrheit und die ganze
#   Kette bitgenau.
#   BESTANDEN - alle 4 Muster stimmen mit cv2 ueberein.

# 2 · Ecke fuer Ecke, beide Wege
.\core\build\aruco_conformance.exe core\build\fixtures\fixtures.txt --ecken `
    | Select-String '^ecke ' | Set-Content cpp.txt
.\core\build\aruco_conformance.exe core\build\fixtures\fixtures.txt --ecken --capi `
    | Select-String '^ecke ' | Set-Content capi.txt
.\venv\Scripts\python.exe core\tools\compare_corners.py cpp.txt capi.txt "C++" "C-API"
#   Ecken verglichen: 64 · davon verschieden: 0 · 0 float32-ULP · 0.000e+00 mm

# 3 · Die .so und das APK
.\dev.ps1 build-android-libs "arm64-v8a,armeabi-v7a,x86,x86_64"
.\dev.ps1 check-android-so  "arm64-v8a,armeabi-v7a,x86,x86_64"
.\dev.ps1 build-apk         # baut und misst nach; APK in android/out/
.\dev.ps1 check-apk

# 4 · Die Kette aus dem APK in einem Chromium, bis zum nachgemessenen PDF
.\dev.ps1 check-android-ui

# 5 · Die Testlaeufe
.\venv\Scripts\python.exe -m pytest -o "addopts=" -q                       # 183 passed
$env:ARUCO_PDF='js';   .\venv\Scripts\python.exe -m pytest -o "addopts=" -q  # 183 passed
$env:ARUCO_CORE='cpp'; .\venv\Scripts\python.exe -m pytest -o "addopts=" -q  # 183 passed
.\dev.ps1 run-tests-js                                                     # 24/24
```

Der Gradle-Bau braucht beim ersten Lauf Netz (AGP 8.7.3, Gradle 8.9, `androidx.webkit`) und
ein `npm install` im Wurzelverzeichnis (`pdf-lib` wandert ins APK). Danach baut er offline.
`check-android-ui` braucht ein installiertes Chrome oder Edge und den WASM-Bau des Kerns
(`.\dev.ps1 build-core-wasm`); es startet einen Dateiserver auf Port 8030 und beendet ihn
selbst.

Gelaufen am 2026-09-08: alle fünf Blöcke, Ergebnisse wie angegeben.
