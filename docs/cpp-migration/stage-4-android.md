---
title: Stufe 4 · Die Android-Hülle — Ergebnis
description: Was die Android-App heute wirklich kann, was nur gebaut ist, und wie man sie auf ein Telefon bringt.
audience: developer
status: current
updated: 2026-09-08
---

# Stufe 4 · Die Android-Hülle — Ergebnis

> **Es gibt ein installierbares APK (8,48 MB, arm64-v8a), und der native Kern darin ist
> auf einer echten JVM gemessen — aber die App baut noch KEINE Schablone.** Der
> C++-Kern misst bis heute nur die Markerecken; Ausgleich, Kamerapose, Entzerrung und
> Schablonen-PDF stehen weiterhin allein in Python. Was die App fertig kann, ist das
> **Markerblatt**; was sie beweisen kann, ist der **Prüfstand auf dem Gerät**.
>
> **Auf einem Telefon gelaufen ist bis jetzt nichts.** Auf diesem Rechner gibt es kein
> Android. Alles unten steht entweder unter „gemessen" oder unter „nur gebaut" — dazwischen
> gibt es nichts.

> **Stand:** 2026-09-08 · Zweig `feat/android-app` · Belege in `core/`, `android/`, `dev.ps1`

---

## 1 · Gemessen gegen nur gebaut

Die Trennlinie ist die einzige Aussage dieses Dokuments, die zählt.

| | Status |
|---|---|
| `detect_markers` durch die **C-Schnittstelle** (`aruco/capi.h`) | **gemessen**, Windows, 64/64 Ecken identisch |
| `detect_markers` durch die **JNI-Schicht** auf einer echten JVM | **gemessen**, Windows, 64/64 Ecken identisch |
| RGBA→BGR-Weg der JNI-Schicht (der, den Android geht) | **gemessen**, 36/36 Werte identisch zum BGR-Weg |
| Modulbits des Markerblatts gegen `cv2` | **gemessen**, 4/4 Muster byteweise gleich |
| Die drei Testsuiten (Python-Kern, C++-Kern, PDF aus JS) | **gemessen**, je **183 passed** |
| `libaruco_core.so` für vier ABIs: ELF, 16-KB-Ausrichtung, Symbole | **gemessen** am Erzeugnis |
| APK: Inhalt, ABIs, Rechte, `zipalign -P 16`, Signatur | **gemessen** am Erzeugnis |
| Oberfläche + Brücke im **Desktop-Chromium** (Chrome 152) | **gemessen**: Seite baut auf, Markerblatt entsteht |
| **Irgendetwas auf einem Android-Gerät** | **nicht gelaufen.** Kein Gerät, kein Emulator. |
| Die App als Messgerät (Foto → Schablone) | **existiert nicht** — der Kern kann es nicht |

---

## 2 · Was die App heute tut

Sie startet auf einer eigenen Seite (`android/app/src/main/assets/www/native/`), und die
hat vier Abschnitte:

1. **Der Rechenkern** — OpenCV-Fassung, Wörterbuch, Markerkante, ABI, Seitengröße des
   Systems, WebView-Fassung. Alle Werte kommen aus der `.so`, keiner ist abgetippt.
2. **Prüfstand** — die eingefrorenen Szenen aus `shared/fixtures/` durch den nativen Kern,
   gegen die Grundwahrheit. **Das ist der Knopf, der den Satz „Android ist ungemessen"
   streicht** (`stage-4-cross-targets.md`, Abschnitt 5).
3. **Detektor am Foto** — Foto wählen oder aufnehmen, nativ Marker suchen, gefundene IDs
   und mittlere Kantenlänge in Pixeln anzeigen. Beantwortet die Frage, die kein Prüfstand
   beantwortet: findet der Kern die Marker auf einem echten Bild *dieser* Kamera?
4. **Markerblatt** — das A4-Blatt, im Gerät gebaut (`web/pdf/markersheet.js` plus die
   Modulbits aus dem nativen Kern), zum Speichern oder Teilen. **Vollständig, kein Stück
   fehlt.**

Dazu ein Knopf, der **die unveränderte Oberfläche** öffnet (`app/static/`, Byte für Byte
die vom Rechner). Dort gehen Sprache, Thema, Layout und die Fotowahl; beim Entzerren
bricht sie mit einer übersetzten Meldung ab, weil dieser Schritt nicht nativ vorliegt.

### Der Aufbau

```
WebView (https://appassets.androidplatform.net/  ->  assets/www/)
   |
   |-- /index.html          app/static/, unveraendert
   |-- /native/index.html   die eigene Seite der Huelle
   |-- /web/pdf/            der PDF-Bau in JavaScript
   |-- /shared/             constants.json
   |
   |  bridge-shim.js (addDocumentStartJavaScript, laeuft vor jedem Seitenskript)
   |     - Importkarte fuer "pdf-lib"
   |     - fetch("/api/...") -> Bruecke statt Server
   v
Java  (WebBridge -> MainActivity)
   |
   v  JNI
libaruco_core.so   ->   derselbe core/ wie auf Windows und im Browser
```

**`app/static/` bleibt unangetastet.** Kein eingefügtes `<script>`, keine Android-Fassung
von `index.html`. Das leistet `WebViewCompat.addDocumentStartJavaScript`: die Brücke läuft,
bevor das erste Modul der Seite läuft, und ersetzt dort `fetch` für die `/api/`-Pfade. Eine
zweite Fassung der Oberfläche wäre die teuerste Art, dieses Vorhaben zu verlieren.

---

## 3 · Die Zahlen

### Die Bibliothek

Alle vier gebaut und alle vier nachgemessen (`./dev.ps1 check-android-so`):

| ABI | `libaruco_core.so` | LOAD-Ausrichtung | exportierte Symbole |
|---|---:|---|---:|
| **arm64-v8a** (im APK) | **5,93 MB** | 0x4000 (16 KiB) | 6 |
| armeabi-v7a | 2,97 MB | 0x4000 | 6 |
| x86 | 13,25 MB | 0x4000 | 6 |
| x86_64 | 21,67 MB | 0x4000 | 6 |

Die Intel-Zahlen sind so viel größer, weil die x86-Bibliotheken des OpenCV-SDK die
SIMD-Verzweigungen für mehrere Befehlssätze mitführen — dasselbe Bild wie beim Prüfstand
in `stage-4-cross-targets.md`, Abschnitt 4.

**Halb so groß, weil sie nichts mehr exportiert.** Der erste Bau war 12,81 MB und trug
**4383** dynamische Symbole — die ganze Symboltabelle des statisch gebundenen OpenCV. Weil
jedes davon als von außen erreichbar galt, durfte der Linker auch nichts wegwerfen. Mit
`-Wl,--exclude-libs,ALL`, `-Wl,--gc-sections` und `-ffunction-sections` bleiben **6**
Symbole (genau die JNI-Einsprungpunkte) und **6,21 MB** — gestrippt 5,93 MB im APK.

| | vorher | nachher |
|---|---:|---:|
| `libaruco_core.so` (arm64-v8a) | 12 806 576 B | **6 213 760 B** |
| dynamische Symbole | 4383 | **6** |

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
| Größe | **8,48 MB** (Debug, nur arm64-v8a) |
| Einträge | 163 |
| Rechte | **keine.** Die eine Zeile oben ist eine App-eigene Marke, die AGP ab targetSdk 33 selbst einträgt — sie erlaubt nichts. **Kein `INTERNET`**, kein `CAMERA`, kein Speicherrecht. |
| `zipalign -c -P 16 -v 4` | bestanden |
| `apksigner verify` | gültig, v2-Schema, `CN=Android Debug` |
| `versionName` | aus `app/config.py` (`APP_VERSION`), nicht abgetippt |

**Ohne Netzberechtigung ist „offline" eine Zusicherung des Systems** und nicht eine des
Programmierers: die App *kann* nicht senden. Fotos werden über `ACTION_OPEN_DOCUMENT`
gelesen und PDFs über `ACTION_CREATE_DOCUMENT` geschrieben — beide geben dem Benutzer die
Wahl und der App nur die eine Datei, ohne jedes Speicherrecht. Die Kamera macht
`ACTION_IMAGE_CAPTURE`, also die Kamera-App des Systems; erst ein deklariertes
`CAMERA`-Recht würde es auch verlangen.

### Die Messungen

```
C++ direkt  vs  C-Schnittstelle          64 Ecken, 0 verschieden, 0.0 px
C++ direkt  vs  JNI auf der JVM          64 Ecken, 0 verschieden, 0.0 px
RGBA-Weg    vs  BGR-Weg (in der JVM)     36 Werte, identisch, beide Szenen
Modulbits   vs  cv2                      4 Marker, 6x6, byteweise gleich
```

Der größte Eckfehler bleibt **0,2337 px** bei 0,75 px Toleranz — dieselbe Zahl wie auf
Windows und im Browser (`stage-4-cross-targets.md`, Abschnitt 1). Die neuen Schichten
verschieben **nichts**: nicht ein einziges Bit über 64 Ecken.

```
183 passed   pytest (Python-Kern)
183 passed   pytest mit ARUCO_CORE=cpp
183 passed   pytest mit ARUCO_PDF=js
```

---

## 4 · Auf ein Telefon bringen

**Der wichtigste Abschnitt dieses Dokuments.** Alles darüber ist Vorarbeit.

### Einmalig am Telefon

1. **Einstellungen → Über das Telefon → siebenmal auf „Build-Nummer" tippen.**
   Das schaltet die Entwickleroptionen frei.
2. **Einstellungen → System → Entwickleroptionen → USB-Debugging einschalten.**
3. Telefon per USB anstecken. Auf dem Telefon erscheint „USB-Debugging zulassen?" —
   bestätigen (und „Von diesem Computer immer zulassen" ankreuzen).

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

### Was zu tippen ist, und was dabei herauskommen muss

| Schritt | Erwartung | Wenn nicht |
|---|---|---|
| App startet | Die Seite **„Auf diesem Gerät"** mit gefüllter Tabelle: `OpenCV 5.0.0`, `DICT_4X4_50 (50)`, `67,0 mm`, `arm64-v8a` | Steht dort eine rote Zeile statt der Tabelle, hat `libaruco_core.so` nicht geladen — siehe Falle 1 |
| **Seitengröße** in der Tabelle | `4096 B` oder `16384 B` | Bei `16384` ist das Gerät ein 16-KB-Gerät. Dass die App überhaupt startet, ist dann der Beleg für die Ausrichtung. |
| **„Prüfstand laufen lassen"** | **BESTANDEN**, und je Szene `größter Eckfehler 0,2337 px (Toleranz 0,7500 px)` | Andere Zahlen: **das ist ein Befund**, kein Rundungsfehler. Bitte melden. |
| Die SHA-256-Zeile darunter | `flat`: `da8c60f0d419cd7035f4bd1ee3bb13190e4507cd16507ddd0202e924601156f4`<br>`thick`: `c3695fe476f79854dc64c1c138303236b735a6c26c884a66fe8c0978ef18e374` | Weicht sie ab, hat Androids PNG-Dekoder **andere Pixel** geliefert als `cv2` — dann sind die Eckenzahlen nicht direkt mit Windows vergleichbar, und der Unterschied liegt im Laden, nicht im Detektor. |
| **„Als PDF speichern"** unter *Markerblatt* | Systemdialog, danach ein A4-PDF. Ausdrucken mit **100 %, nicht „an Seite anpassen"**, und einen Marker mit dem Messschieber nachmessen. | — |
| **„Foto wählen"** → **„Marker suchen"** | `4 Marker in <n> ms`, vier ähnlich große Kanten | Findet er nichts, war das Blatt zu klein im Bild, zu schräg oder unscharf. |
| **„Oberfläche öffnen"** | Die vertraute Oberfläche vom Rechner, auf dem Handy-Layout | — |
| Dort ein Foto laden und **„Entzerren"** | Eine übersetzte Meldung: *dieser Schritt steckt noch nicht im nativen Rechenkern* | Ein Netzwerkfehler statt dieser Meldung heißt, die Brücke lief nicht — siehe Falle 2 |

**Die drei Zahlen, die zurückgemeldet gehören:** das Urteil des Prüfstands, der größte
Eckfehler je Szene, und die beiden SHA-256. Damit ist Android nicht mehr ungemessen.

---

## 5 · Fallen — gemessen, nicht geraten

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
deshalb nie ins Netz geht. Wer stattdessen `loadUrl("file:///android_asset/...")` schreibt,
bekommt eine leere Seite und in der Konsole eine CORS-Meldung, die nach einem Serverproblem
aussieht.

**3 · Zwei MIME-Typen sind nicht verhandelbar.** `.js` muss `text/javascript` sein, sonst
weist die WebView das Modul ab; `.json` muss `application/json` sein, sonst scheitert
`import ... with { type: "json" }` — und daran hängt `shared/constants.json`, also jede
Konstante des Produkts. Beides steht in `MainActivity.mimeType`.

**4 · `shouldInterceptRequest` bekommt bei einem POST den Rumpf NICHT.** Das ist eine Lücke
im WebView-API. Deshalb ist die Grenze so geschnitten: lesende `/api/`-Pfade
(`/api/preview/...`) bedient der `WebViewAssetLoader`, alles Schreibende geht über die
JavaScript-Brücke. Wer das übersieht, baut einen Upload, der die Datei nie sieht.

**5 · Ein `<input type="file">` tut in einer WebView von allein nichts.** Kein Dialog, keine
Meldung — bis `WebChromeClient.onShowFileChooser` da ist. Die dort gewählte URI wird
zusätzlich gemerkt, damit die Brücke das Bild daraus selbst laden kann: ein 12-MP-Foto als
Base64 durch die JavaScript-Grenze wären rund 48 MB Text.

**6 · Die EXIF-Drehung muss VOR der Erkennung angewandt werden.** `BitmapFactory` folgt der
EXIF-Marke nicht, Handys schreiben aber fast immer in Sensor-Ausrichtung. Ohne das sucht
der Detektor in einem gedrehten Bild. `Photo.applyExifOrientation` löst alle acht Fälle auf,
auch die gespiegelten: eine Spiegelung dreht die Eckenreihenfolge um (TL,TR,BR,BL wird
TR,TL,BL,BR), und die Homographie wäre dann ebenfalls gespiegelt — ein Ergebnis, das
plausibel aussieht und in der Breite stimmt. `inScaled = false` gehört dazu, sonst skaliert
Android nach Bildschirmdichte.

**7 · Ein direkter `ByteBuffer`, kein `byte[]`.** `GetByteArrayElements` darf kopieren (auf
Android tut es das), `GetPrimitiveArrayCritical` hält stattdessen den Speicherbereiniger an
— während einer Erkennung, die Sekunden dauert. Bei 48 MB ist beides spürbar. Die JNI-Seite
weist einen Heap-Puffer deshalb ausdrücklich ab; dass sie das tut, ist gemessen.

**8 · Keine C++-Ausnahme darf durch einen JNI-Rahmen.** Sie ist dort nicht definiert; in der
Praxis stirbt der Prozess wortlos, und der Bediener sieht die App verschwinden. `capi.cpp`
fängt deshalb ausnahmslos alles und macht daraus Code plus Klartext. Dass ein falscher
Puffer eine `IllegalArgumentException` gibt und der Prozess weiterläuft, ist gemessen.

**9 · Gradle trägt aus `assets.srcDir()` KEINE Aufgabenabhängigkeit mit.** Weder aus einem
`TaskProvider` noch aus einem `Provider<File>`. Beides wurde probiert: der Bau lief beide
Male grün durch, `gatherWebAssets` lief gar nicht, und im APK lag von der Oberfläche
**nichts**. Ein leeres APK ist von einem vollen nur an seiner Größe zu unterscheiden — und
die hätte hier niemand nachgesehen. Die Abhängigkeit steht jetzt von Hand an den
Merge-Aufgaben, und `./dev.ps1 check-apk` zählt zwölf Pflichtdateien im fertigen APK nach.
**Das war der einzige echte Fehler dieser Stufe, und er wäre ohne die Nachzählung
unbemerkt ausgeliefert worden.**

**10 · `apksigner` ist ein Java-Programm in einer `.bat`-Hülle.** Ohne `JAVA_HOME` bricht es
mit Rückgabewert 1 ab und sagt kein Wort über den Grund — das sieht nach einer ungültigen
Signatur aus und ist eine fehlende Werkzeugkette. `aapt` und `zipalign` sind native
Programme und brauchen es nicht, deshalb fällt es genau an dieser einen Stelle auf.

**11 · MAX_PATH.** Das Repo liegt rund 105 Zeichen tief, AGPs Zwischenpfade sind lang. Gradle
baut deshalb neben dem Repo (`aruco.buildRoot` in `android/gradle.properties`), und
`build-apk` holt das APK nach `android/out/` zurück.

**12 · Die Kataloge liegen zweimal im APK.** Einmal unter `/i18n/` für die Oberfläche, einmal
unter `/app/static/i18n/` — dorthin zeigt der relative Import in `web/pdf/i18n.js`. Rund
30 KB. Der Ausweg wäre ein Bundler, den dieses Projekt bewusst nicht hat.

---

## 6 · Was **nicht** belegt ist

**Auf einem Android-Gerät ist nichts gelaufen.** Weiterhin: `adb devices` leer, kein
Emulator, kein System-Abbild, kein WSL, kein Docker, kein `qemu-aarch64`. Was hier steht,
ist am Erzeugnis gemessen (ELF, Zip, Signatur) oder auf einer JVM auf Windows gelaufen.
**Es gibt keine Zahl aus einem Telefon.**

Im Einzelnen ungeprüft:

- **Ob die App startet.** Der Java-Teil ist übersetzt und dexed, nicht ausgeführt.
- **Ob die WebView `addDocumentStartJavaScript` kann.** Das Merkmal wird zur Laufzeit
  abgefragt; kann sie es nicht, fehlt die Brücke, und das steht dann im `logcat`. Auf einer
  aktuellen WebView ist es vorhanden — geprüft ist es nicht.
- **Ob `import ... with { type: "json" }` in der WebView des Geräts geht.** Im
  Desktop-Chromium 152 geht es (gemessen). Chromium kann es seit 123; eine ältere
  System-WebView könnte scheitern.
- **Kein Speicher- und kein Zeitbedarf gemessen.** Ein 12-MP-Foto sind 48 MB RGBA plus das,
  was der Detektor daneben anlegt. Ob ein Telefon mit wenig RAM das verträgt, steht nicht
  fest.
- **Die Kamera-Wege** (`ACTION_IMAGE_CAPTURE`, `FileProvider`, `ACTION_CREATE_DOCUMENT`)
  sind übersetzt, nicht ausgeführt.
- **Nur arm64-v8a im APK.** Die anderen drei ABIs sind gebaut und nachgemessen, aber nicht
  eingepackt (`./dev.ps1 build-apk arm64-v8a,armeabi-v7a`).
- **Kein Release-Bau, keine Signatur ausser dem Debug-Schlüssel.** Für eine Auslieferung
  fehlen ein eigener Schlüssel und `isMinifyEnabled`-Überlegungen.
- **Der Browser-Beleg ist ein Ersatz und kein Gerät.** Chromium auf Windows ist nicht die
  System-WebView eines Telefons, und die Java-Seite war dabei ein Stub.
- **Das im Browser gebaute Markerblatt ist nicht nachgemessen worden.** Es entstand
  (gültiges PDF, 5,4 KB, 663 ms) — dass es maßhaltig ist, folgt aus
  `tests/test_markersheet.py` über `ARUCO_PDF=js` und daraus, dass die Modulbits des
  nativen Kerns byteweise denen aus `cv2` entsprechen. Ein direkter Messschieber-Beleg an
  einem auf dem Telefon gebauten Blatt steht aus.
- **Und weiterhin: nur synthetische Szenen.** Der Messschieber-Beleg (100 mm = 100 mm)
  hängt nach wie vor allein an der Python-Kette.

---

## 7 · Was jetzt als Nächstes kommt

**Der Kern muss den Rest der Messung lernen.** Die Hülle ist fertig und wartet: sobald
`solve`, `resolve_pose`, `effective_homography`, `plane_extent`, `rectify` und
`find_contour_mm` in `core/` stehen, wächst die C-Schnittstelle um ein paar Funktionen, die
JNI-Schicht um ebenso viele, und die Brücke ersetzt drei `notInNativeCore`-Zeilen durch
Aufrufe. Nichts an der Oberfläche, nichts am Gradle-Bau, nichts an der Auslieferung ändert
sich dabei.

Was dabei über diese Stufe hinausgeht:

- **Das entzerrte Bild muss als JPEG in die WebView.** `web/pdf/build.js` nimmt JPEG-Bytes,
  und der Kern fasst `imgcodecs` nicht an. Auf Android kodiert `Bitmap.compress` — die
  Grenze steht schon richtig, sie wird nur noch nicht benutzt.
- **Ein gekacheltes Schablonen-PDF passt nicht durch die Base64-Brücke.** Das Markerblatt
  mit seinen 5,4 KB schon; ein Ausdruck mit eingebettetem Raster wären Dutzende Megabyte
  Text. Dafür gehört das Bild vorher auf die native Seite.

---

## 8 · Nachvollziehen

```powershell
# 1 · Die JNI-Schicht auf einer echten JVM (baut den Kern mit)
.\dev.ps1 check-jni
#   BESTANDEN - die JNI-Schicht liefert die Ecken der Grundwahrheit.
#   BESTANDEN - alle 4 Muster stimmen mit cv2 ueberein.

# 2 · Ecke fuer Ecke, alle drei Wege
.\core\build\aruco_conformance.exe core\build\fixtures\fixtures.txt --ecken `
    | Select-String '^ecke ' | Set-Content cpp.txt
.\core\build\aruco_conformance.exe core\build\fixtures\fixtures.txt --ecken --capi `
    | Select-String '^ecke ' | Set-Content capi.txt
.\venv\Scripts\python.exe core\tools\compare_corners.py cpp.txt capi.txt "C++" "C-API"
#   Ecken verglichen: 64 · davon verschieden: 0

# 3 · Die .so und das APK
.\dev.ps1 build-android-libs arm64-v8a,armeabi-v7a,x86,x86_64
.\dev.ps1 check-android-so  arm64-v8a,armeabi-v7a,x86,x86_64
.\dev.ps1 build-apk         # baut und misst nach; APK in android/out/

# 4 · Die drei Suiten
.\venv\Scripts\python.exe -m pytest -o "addopts=" -q                    # 183 passed
$env:ARUCO_CORE='cpp'; .\venv\Scripts\python.exe -m pytest -o "addopts=" -q  # 183 passed
$env:ARUCO_PDF='js';   .\venv\Scripts\python.exe -m pytest -o "addopts=" -q  # 183 passed
```

Der Gradle-Bau braucht beim ersten Lauf Netz (AGP 8.7.3, Gradle 8.9, `androidx.webkit`) und
ein `npm install` im Wurzelverzeichnis (`pdf-lib` wandert ins APK). Danach baut er offline.

Gelaufen am 2026-09-08: alle vier Blöcke, Ergebnisse wie angegeben.
