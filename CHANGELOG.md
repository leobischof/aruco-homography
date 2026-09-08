# Changelog

Bemerkenswerte Änderungen an diesem Projekt. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach
[SemVer](https://semver.org/lang/de/).

## [0.1.3-alpha] – 2026-09-08

**Das Foto entsteht jetzt in der App, und die Marker dürfen liegen, wie sie fallen.** Fünf
Dinge, die im Weg standen: die App kam nicht an die Kamera, das Markerblatt war die einzige
verlässliche Vorlage, der Zuschnitt ließ sich nur als PDF speichern, der Klebeplan zeigte ein
leeres Gitter, und der Kopf brauchte auf dem Telefon drei Zeilen für drei Knöpfe.

### Hinzugefügt

- **Fotografieren in der App.** Neben *Datei wählen* steht auf Geräten mit grobem Zeigegerät
  ein zweites Feld *Foto aufnehmen*, das die Kamera-App des Systems öffnet. Bisher ging das
  nicht: der Kommentar im Markup behauptete, das Handy biete von sich aus Kamera und Galerie
  an — im Browser stimmt das, hinter dieser WebView nicht. `MainActivity.onShowFileChooser`
  überging die `FileChooserParams` und startete immer den Dokumentwähler. Der einzige Weg
  hinein war also ein Foto, das es schon gab.

  Es ist die **Kamera-App des Systems** und keine eingebaute: das Bild kommt in voller
  Auflösung und mit EXIF, und damit funktioniert die automatische Kamerahöhe aus der
  Brennweite weiter. Die App braucht dafür **kein CAMERA-Recht** — sie startet eine fremde
  App und bekommt eine Datei zurück.

- **Ein dritter Modus: „Verstreute Marker (beliebige Winkel)".** Bisher gab es das
  Markerblatt (Abstände bekannt) und *frei* — letzteres setzt voraus, dass alle Marker
  **gleich ausgerichtet** liegen. Liegen sie das nicht, ist frei nicht bloß ungenauer,
  sondern falsch: auf der Prüfszene 71 px Restfehler und 500 mm als 148 mm gelesen. Das ist
  jetzt ein Test.

  Der neue Modus schätzt je Marker **einen Winkel mit**, also 8 + 3·(n−1) Unbekannte statt
  8 + 2·(n−1). Weil ein Marker sein eigenes Koordinatensystem mitbringt, **genügt ein
  einziger** — vier Ecken bekannter Kantenlänge bestimmen die Ebene. Der Preis: jeder
  weitere Marker steuert fünf statt sechs Bedingungen bei, deshalb bleibt *frei* die
  genauere Wahl, solange seine Annahme stimmt. Alle Marker müssen **gleich groß** sein; ihre
  Kantenlänge wird gemessen und nicht geschätzt.

  Ausgerichtet wird die Ebene **nach dem Foto**: verstreute Marker geben keine Vorzugsrichtung
  her, also bleibt das Zuschnitt-Rechteck achsparallel zum Bild. Der Ursprung liegt in der
  Mitte der Markerwolke.

- **Der Zuschnitt als Bilddatei, JPEG oder PNG.** Mit der **Auflösung in der Datei** —
  JFIF-Dichte beim JPEG, `pHYs` beim PNG. Ein nachgelagertes Programm liest damit den
  Maßstab, statt ihn zu raten; ein Pixel ist 25,4/dpi Millimeter. Das musste eigens
  geschrieben werden: die Leinwand des Browsers schreibt `units = 0`, `Bitmap.compress`
  schreibt gar kein `pHYs`, und `cv2.imwrite` kann beides nicht.

  Was auf dem Bild **fehlt und fehlen muss**: Maßstab, Raster, Fußzeile, Schnittmarken,
  Klebeplan. Auf einem Ausdruck ist das ein Aufdruck, auf einem Bild wäre es Bildinhalt, den
  niemand mehr von der Schablone unterscheiden kann.

### Geändert

- **Der Klebeplan zeigt den Zuschnitt, den er kachelt.** Vorher sagte er, *wie viele* Blätter
  es gibt und welche Nummer wohin gehört — aber nicht, was darauf zu sehen ist. Vor acht
  gleich aussehenden A4-Seiten hilft die Nummer im leeren Rechteck nicht; das Bild hilft.
  Es ist ein Daumennagel (längere Kante höchstens 1600 px, auf A4 rund 160 dpi) und keine
  Schablone — nachgemessen wird auf dieser Seite nichts.

  Weil darunter jetzt ein Foto liegt, bekommen Kachelränder und Außenkante denselben weißen
  Saum wie das Millimeterraster, und die Blattnummern stehen auf weißem Träger. Eine dünne
  Linie ist auf einem Foto sonst mal sichtbar und mal nicht.

  **Der blattweise Export bleibt blattweise.** Der Plan fragt sein Bild mit einer Obergrenze
  an Pixeln; das Riesenraster, dessen Vermeidung `0.1.2-alpha` ausmachte, entsteht nicht
  wieder.

- **Markerblatt, Sprache und Thema stehen in einer Zeile.** Auf dem Telefon brauchten die
  drei bisher drei Zeilen — der Verweis bekam eine eigene, weil er mit dem ausgeschriebenen
  Sprachnamen nicht danebenpasste (bei 390 px: 361 px in 358 px Innenbreite). Der
  Sprachwähler zeigt jetzt **geschlossen das Kürzel** `DE` / `EN` und **aufgeklappt** den
  Eigennamen `Deutsch` / `English`; damit passen alle drei nebeneinander. Unter etwa 380 px
  passen sie weiterhin nicht — dort fällt das Paar aus Sprache und Thema **gemeinsam** in die
  zweite Zeile, statt den Themenknopf allein darunter zu stellen.

### Was NICHT belegt ist

- **Auf einem Telefon ist von dieser Fassung nichts gelaufen.** Wie bei `0.1.2-alpha` ist sie
  in einem Chromium aus dem gebauten APK geprüft: beide Rasterwege bis zum nachgemessenen PDF
  (je 3 Seiten, 13 Rasterabstände zu 50 mm, größte Abweichung 6 nm), der Bildexport in beiden
  Formaten mit der Auflösung aus der Datei zurückgelesen, der Klebeplan mit eigenem Bild auf
  Seite 1. Der Kopf ist bei 360, 390, 768 und 1280 px in beiden Themen und beiden Sprachen
  vermessen und angesehen.
- **Der neue Modus ist an synthetischen Szenen belegt, nicht an einem echten Foto.** Acht
  Prüfungen in Python, sechs durch das WebAssembly, dieselben Zahlen im C++-Kern.
- **Die Kette `Foto → Marker → Millimeter` ist weiterhin auf keinem Ziel unabhängig belegt.**
  Belegt ist `PDF → Drucker → Papier` (07.09.2026, Messschieber). Was fehlt, ist ein
  Gegenstand *bekannter* Länge mit aufs Foto und derselbe Gegenstand auf dem Ausdruck
  nachgemessen.

## [0.1.2-alpha] – 2026-09-08

**Der Export auf dem Telefon rastert jetzt blattweise — und damit läuft er.** `0.1.1-alpha`
hatte den Speicherfehler gemeldet statt ihn zu verschlucken; gedruckt hat sie deswegen noch
nichts. Diese Fassung baut das Riesenraster gar nicht erst.

### Behoben

- **`PDF erzeugen` scheiterte auf dem Telefon bei jeder Auflösung.** Der Rohtext
  *Raster 9575x13623 braucht 373 MB und der Speicher gibt sie nicht her* blieb stehen, auch
  bei 150 dpi. Zwei Gründe, beide nachgerechnet:

  1. **Die Sicherung aus `0.1.1-alpha` griff nicht.** Ihre Obergrenze stand auf 768 MiB und
     galt als *Summe* für beide Raster — 805 306 368 / 6 = **134 Megapixel**. Der Export
     wollte 130,44: er kam durch die Prüfung und scheiterte danach an **einer** Belegung von
     373 MiB. Ein Direktpuffer braucht einen zusammenhängenden Block; wieviel insgesamt frei
     ist, sagt darüber wenig. Die Grenze bezieht sich jetzt auf eine einzelne Belegung.
  2. **Eine greifende Grenze hätte nur besser abgewiesen.** 150 dpi sind auf demselben
     Zuschnitt immer noch 32,6 Megapixel und 98 MB am Stück. Eine Meldung ist kein PDF.

  **Also der andere Schnitt:** gedruckt wird der Zuschnitt ohnehin in A4-Blättern, und jedes
  Blatt holt sich jetzt sein eigenes Bild, statt aus einem Riesenbild geschnitten zu werden.
  Der Spitzenbedarf hängt damit am **Blatt** — A4 bei 300 dpi sind rund 26 MB — und wächst
  nicht mehr, wenn die Schablone größer wird.

### Was das am Ausdruck ändert: nichts

`core/src/rectify.cpp` bildet Ausgabepixel `u` auf `crop.x0 + (u + 0,5) / px_per_mm` ab. Ein
Blatt, das an einer **ganzzahligen** Pixelgrenze beginnt, tastet deshalb genau dieselben
Stellen der Ebene ab wie der entsprechende Ausschnitt des großen Rasters — und die
Interpolation liest dabei aus dem **Quellfoto**, das für jedes Blatt vollständig vorliegt.
Kein abgeschnittener Filterkern, kein Randeffekt. `web/vision/tiles.test.mjs` misst das nach:
Blatt für Blatt **Bit für Bit** gleich, und die Blätter setzen das Ganze lückenlos wieder
zusammen.

Drei Regler können das nicht — **lokaler Kontrast** (CLAHE legt sein Histogrammgitter über
das ganze Bild), **Kantenschärfe** und **Kantenzeichnung** (beide greifen in die
Nachbarschaft) — und der **Umriss** wird auf dem fertigen Bild gesucht. In diesen vier Fällen
wird weiter am Stück gerastert. Alle vier stehen per Vorgabe aus.

**Was es kostet:** das PDF wird gut ein Fünftel größer, weil die Überlappung zweier Blätter
jetzt zweimal kodiert wird statt einmal geteilt. Auf die Millimeter hat das keinen Einfluss.

### Hinzugefügt

- **Die Speichergrenze steht auf der Geräteseite.** Sie wurde in Java ausgerechnet, durch die
  Brücke gereicht und angewandt — und nirgends angezeigt. Als der Export scheiterte, ließ sich
  deshalb nicht ablesen, ob die Sicherung überhaupt scharf war. Steht die Zahl nicht, sagt die
  Zeile das jetzt.
- **Der Prüfstand fährt beide Wege.** `ui-probe.html` setzte `local_contrast` und fuhr damit
  immer den Weg am Stück; der Regelfall — Regler unangetastet — war end-to-end ungeprüft, und
  genau so ist der Fehler ausgeliefert worden. `./dev.ps1 check-android-ui` misst jetzt beide
  PDFs nach und weist mit `--eigenes-bild-je-seite` nach, dass wirklich blattweise gerastert
  wurde.

### Was NICHT belegt ist

- **Auf einem Telefon ist von dieser Fassung nichts gelaufen.** Geprüft ist sie in einem
  Chromium aus dem gebauten APK — beide Wege, jeder bis zum nachgemessenen PDF (je 3 Seiten,
  13 Rasterabstände zu 50 mm, größte Abweichung 6 nm).
- **Die Kette `Foto → Marker → Millimeter` ist weiterhin auf keinem Ziel unabhängig belegt.**
  Belegt ist `PDF → Drucker → Papier` (07.09.2026, Messschieber). Was fehlt, ist ein Gegenstand
  *bekannter* Länge mit aufs Foto und derselbe Gegenstand auf dem Ausdruck nachgemessen.

Deshalb bleibt `alpha` im Namen.

## [0.1.1-alpha] – 2026-09-08

**Die erste Fassung, die ein echtes Telefon hinter sich hat.** `0.1.0-alpha` lief auf
einem Xiaomi 2312DRA50G mit Android 15 — und der Lauf hat beides getan, was ein erster
Lauf tun kann: er hat den Prüfstand bestanden und zwei Fehler gefunden, die auf einem
Rechner ohne Android gar nicht auftreten konnten.

### Was das Gerät gemessen hat

| | |
|---|---|
| **Prüfstand** | **BESTANDEN.** `flat` 0,2337 px in 83 ms, `thick` 0,2337 px in 84 ms, je 4/4 Marker, Toleranz 0,7500 px |
| Die beiden SHA-256 der Prüfszenen | **genau die vorhergesagten** — `da8c60f0…` und `c3695fe4…` |
| Umgebung | Android 15 (API 35), System-WebView 152.0.7977.64, `arm64-v8a`, Seitengröße 4096 B |

**Die beiden Prüfsummen sind der eigentliche Fund.** Sie sagen, dass Androids PNG-Dekoder
**dieselben Pixel** geliefert hat wie `cv2` auf dem Bau-Rechner — und erst dadurch ist der
gleiche Eckfehler eine Aussage über den *Detektor* und nicht über das *Laden*. Damit ist
der Satz „Android ist ungemessen", der in `0.1.0-alpha` noch unter *Was NICHT belegt ist*
stand, eingelöst.

### Behoben

- **Der Export brach auf dem Telefon ab** — `Error invoking core: Java exception was raised
  during method invocation`, ein Satz von Chromium, der keinen Grund nennt. Dahinter lag
  ein `OutOfMemoryError` beim Anlegen des Ausgaberasters: der Vorgabeausschnitt ergab bei
  300 dpi rund **169 Megapixel**, also 506 MB, und der Export hält zwei davon gleichzeitig.
  Zwei Fehler machten sich dabei gegenseitig unsichtbar — `WebBridge` fing `Exception`,
  aber ein `OutOfMemoryError` ist ein `Error`; und die Obergrenze war eine Aussage über das
  **Format** (300 MPx, überall gleich) statt über die **Maschine**. Jetzt meldet Android
  seinen wirklich verfügbaren Speicher an die Seite, die kleinere der beiden Zahlen gilt,
  und der Abbruch kommt als übersetzte Meldung mit einem Vorschlag, der auch wirklich passt.
- **Die Oberfläche lag unter Statusleiste und Navigationsleiste.** Android 15 erzwingt für
  jede App mit `targetSdk 35`, dass sie bis an die Bildschirmkanten zeichnet; wer seinen
  Inhalt dann nicht selbst einrückt, legt die Kopfzeile unter die Uhr und den Fuß hinter die
  Navigationsleiste. Vier CSS-Variablen tragen den sicheren Bereich, gefüllt aus `env()` im
  Browser und aus `WindowInsetsCompat` auf Android — `env()` allein reicht dort nicht, es
  kennt nur die Kamera-Aussparung, nicht die Leisten.

### Hinzugefügt

- **Ein Release-APK.** Bis hierher trug das einzige APK den Schlüssel, den jedes
  Android-SDK jedem Rechner mitgibt (`CN=Android Debug`) — installierbar, startbar, und
  eben deshalb fiel nicht auf, dass es kein Auslieferungsstand ist. `./dev.ps1
  build-apk-release` signiert mit einem eigenen Schlüssel, der **außerhalb des Repos** liegt
  und beim ersten Bau angelegt wird; `check-apk-release` weist ein versehentlich
  debug-signiertes APK ab, statt der Bauart zu glauben. Diese Fassung liegt in beiden
  Ausführungen bei.
- **`versionCode` steht jetzt in der Datei.** Er wird aus `APP_VERSION` abgeleitet
  (`0.1.1` → `101`). Bis hierher stand dort Gradles Vorgabe `1`, für jede Fassung dieselbe:
  `versionName` ist Text und interessiert Android nicht, `versionCode` ist die Zahl, an der
  es entscheidet, ob etwas eine Aktualisierung ist.
- **Sechs Prüfungen für die Speichergrenze** (`web/vision/budget.test.mjs`). Bei einem
  Budget von 40 MPx wird derselbe Export mit `limit_mpx: 40` und `megapixels: 169`
  abgewiesen, bei 300 MPx geht er durch — Windows und Browser bleiben unberührt.

### Was NICHT belegt ist

- **Keine der beiden Behebungen ist auf einem Gerät nachgesehen.** Der Speicherabbruch ist
  in seiner JavaScript-Hälfte geprüft, der sichere Bereich in seiner Wirkung auf CSS — beide
  in einem Chromium auf Windows, mit von Hand gesetzten Zahlen statt gemessenen.
- **Ob das Release-APK auf einem Gerät startet.** Gelaufen ist bisher nur das Debug-APK.
  Der Inhalt ist derselbe, aber das ist ein Vergleich am Zip, kein Startversuch.
- **Die Kette `Foto → Marker → Millimeter` ist weiterhin auf keinem Ziel unabhängig
  belegt.** Belegt ist `PDF → Drucker → Papier` (07.09.2026, Messschieber). Was fehlt, ist
  ein Gegenstand *bekannter* Länge mit aufs Foto und derselbe Gegenstand auf dem Ausdruck
  nachgemessen. Der Prüfstand sagt: *Android rechnet dasselbe wie Python.* Ob **Python** die
  Wahrheit rechnet, sagt er nicht.

Deshalb bleibt `alpha` im Namen.

### Ein Hinweis zum Installieren

Über ein installiertes Debug-APK lässt sich das Release-APK **nicht** installieren: Android
vergleicht die Signaturen und weist die Aktualisierung ab. Erst deinstallieren, dann
installieren. Wer bei der Debug-Ausführung bleibt, aktualisiert wie gewohnt.

## [0.1.0-alpha] – 2026-09-08

**Dieselbe Messtechnik rechnet jetzt auf drei Zielen: Windows, Android und im Browser.**
Aus einem Quelltext, mit einer Testsuite, gegen dieselben eingefrorenen Szenen. Der
Sprung von `0.0.x` auf `0.1.0` sagt nicht „ein bisschen mehr“, sondern: ein anderes
Produkt.

Bis hierher war dies ein Python-Programm mit einer Weboberfläche, das auf einem
Windows-Rechner lief. Ab hier ist es ein C++-Rechenkern, um den drei Hüllen stehen.

### Was in dieser Fassung liegt

| | |
|---|---|
| **Windows** | Installer, rund 103 MB, ohne Adminrechte |
| **Android** | APK, 10,30 MB, `arm64-v8a`, **ohne jede Berechtigung** |
| **Browser** | `dist/web`, 4,5 MB, läuft von einem Dateiserver, danach **ohne Netz** |

Alle drei rechnen mit `core/` — 4 951 Zeilen C++ (2 320 Rechnung, 781 Kopfdateien,
1 567 Anbindungen, 283 Prüfstand), übersetzt mit MSVC, dem Android-NDK
und Emscripten. **Kein einziges `#ifdef` unterscheidet die Ziele.**

### Warum überhaupt

Ein Foto entsteht am Handy und eine Schablone wird am Rechner gedruckt. Solange die
Messung nur in Python existierte, brauchte jedes weitere Ziel eine **zweite Fassung
derselben Millimeter** — und zwei Fassungen driften. Nicht laut, sondern in der
vierten Stelle, und das merkt man am fertigen Teil.

### Wie belegt ist, dass sie gleich rechnen

**Es gibt keine zweite Testsuite.** `ARUCO_CORE=python|cpp` und `ARUCO_PDF=python|js`
tauschen die Umsetzung hinter der Schnittstelle, und die **vorhandenen** Prüfungen
laufen unverändert:

```
ARUCO_CORE=python  ARUCO_PDF=python   183 passed
ARUCO_CORE=python  ARUCO_PDF=js       183 passed
ARUCO_CORE=cpp     ARUCO_PDF=python   183 passed
ARUCO_CORE=cpp     ARUCO_PDF=js       183 passed
node --test                            18 passed
```

Dazu, gegen die **Grundwahrheit** aus `shared/fixtures/` — die Zahlen, aus denen die
Szenen *gebaut* wurden, nicht die, die Python daraus errechnet:

| Vergleich | Ergebnis |
|---|---|
| C++ gegen Python, ganze Kette | Ausdehnung **2,0·10⁻⁶ mm**, Kamerahöhe 8,0·10⁻⁹ mm, Maßstab 5,4·10⁻¹² px/mm |
| C++ gegen die C-Schnittstelle | 64 Ecken, **0 verschieden** |
| C++ gegen die JNI-Schicht (echte JVM) | 18 Größen je Szene, **bitgleich**, einschließlich SHA-256 der 5,9-MB-Raster |
| Windows gegen WASM | 5 von 64 Ecken um **je ein `float32`-ULP** = 0,000122 px |
| Server gegen Browser, dieselbe Szene | `rms` 0,095 px beidseits; eine von 32 Koordinaten um ein ULP |
| Beide PDFs gerastert und durch den **echten** Detektor | Markerkanten **bis zur letzten Stelle gleich**, beide 62,6 µm von der Wahrheit |
| Die Schablone aus der Android-Kette, an den Vektoren vermessen | 13 Rasterabstände, alle 50 mm, größte Abweichung **6,0 nm** |

**Die 2 Nanometer zwischen Python und C++ sind kein Mangel.** `refine_homography` ist
in Python eine `scipy`-Ausgleichsrechnung und in C++ `cv::LevMarq`. Zwei Verfahren auf
demselben Problem enden nicht auf demselben Bit — die Toleranz einer Markerecke ist
**155 000-mal größer**.

### Was NICHT belegt ist

Das gehört genauso in eine Fassungsnotiz wie das Übrige.

- **Auf einem Android-Gerät ist nichts gelaufen.** Kein Telefon, kein Emulator. Das APK
  ist gebaut, vermessen und signiert; dass es startet, ist **nicht** geprüft. Die genauen
  Befehle für den ersten Versuch stehen in `docs/cpp-migration/stage-4-android.md`.
- **Die Java-Schicht der App ist nirgends ausgeführt.** Sie ist übersetzt und dexed. Der
  Browser-Prüfstand fährt einen Nachbau davon, der JNI-Prüfstand fährt an ihr vorbei —
  die Naht dazwischen ist die eine Stelle, an der beide Prüfungen grün wären und die App
  trotzdem kaputt.
- **Nur Chromium.** Kein Safari, kein Firefox, keine System-WebView.
- **`Foto → Marker → Millimeter` ist weiter nicht unabhängig belegt** — auf keinem Ziel.
  Belegt ist `PDF → Drucker → Papier` (07.09.2026, Messschieber). Alles in dieser Fassung
  sagt nur: *die drei Ziele rechnen dasselbe wie Python.* Ob **Python** die Wahrheit
  rechnet, ist eine andere Messung — ein Gegenstand bekannter Länge mit aufs Foto,
  Schablone drucken, **diesen Gegenstand** auf dem Papier nachmessen — und die steht aus.

Deshalb bleibt `alpha` im Namen.

### Hinzugefügt

- **`core/` — der Rechenkern in C++.** Erkennung, Homographie, Ausgleich, Kamerapose,
  Ausdehnung, Entzerrung, Aufbereitung, Kontur. Angebunden über pybind11 (Python), eine
  C-Schnittstelle und JNI (Android) sowie Embind (Browser).
- **`web/pdf/` — der PDF-Bau in JavaScript**, Modul für Modul das Spiegelbild von
  `app/pdf/`. Ein Bau bedient alle drei Ziele; ReportLab gibt es auf Android nicht.
- **`web/vision/` — die Messkette in JavaScript.** Browser und Android teilen sie sich
  **byteweise**; verschieden sind genau zwei Dateien, die den Kern anbinden
  (`core.js` für WASM, `core-android.js` für JNI).
- **Die Android-App.** WebView über die unveränderte Oberfläche, darunter
  `libaruco_core.so`. Kein WebAssembly im APK — nachgeprüft am fertigen Erzeugnis.
  Ohne Netzberechtigung: offline ist keine Zusage, sondern eine Systemeigenschaft.
- **Der Browser-Bau.** Die ganze Kette ohne Server. Nach dem Laden **null** weitere
  Anfragen bis zum fertigen PDF, in Chromium mit abgeklemmtem Netz gemessen.
- **`shared/`** — Konstanten und eingefrorene Prüfszenen, sprachneutral. Kein Zahlenwert
  wird mehr abgeschrieben.
- **Prüfstände, die auch ohne Gerät etwas belegen:** `check-jni` fährt dieselbe
  `jni.cpp` als Windows-DLL auf einer echten JVM, `check-android-ui` fährt die
  Oberfläche **aus dem gebauten APK** durch Chromium bis zum vermessenen PDF,
  `check-apk` zählt nach, was wirklich im Erzeugnis liegt.

### Geändert

- **Die ausgelieferte `.exe` misst mit C++.** Im Quellbaum bleibt Python die Vorgabe —
  es ist die geprüfte Referenz. Fehlt der Kern im Bundle, **startet die Anwendung
  nicht**; ein stiller Rückfall auf Python wäre der teuerste Ausgang, weil alles grün
  aussähe. Das Startbanner nennt den aktiven Kern.
- **Der Ordner wächst von rund 308 MB auf 388 MB**, der Installer von 78 MB auf 103 MB.
  `opencv_world500.dll` muss mit, solange `cv2` für Bild-Ein- und -Ausgabe gebraucht
  wird.
- **Zwei geschützte Zweige.** `develop` sammelt, `master` veröffentlicht.

### Behoben

- **`./dev.ps1 run-tests-js` war auf einem frischen Klon kaputt.** `npm` löst unter
  Windows auf `npm.ps1` auf und stirbt am `Set-StrictMode`; und `--prefix` trug das
  Projekt als Abhängigkeit von **sich selbst** in `package.json` ein. Beides traf
  ausschließlich den ersten Bau — also genau den Fall, für den die Selbstheilung da ist.
- **Gradle trug keine Aufgabenabhängigkeit aus `assets.srcDir()`.** Der Bau war grün und
  das APK enthielt **nichts** von der Oberfläche. Nur eine Größenprüfung hätte es
  gesehen; `check-apk` zählt jetzt die Dateien im fertigen Erzeugnis.
- **Ein `undefined` überschrieb im Browser-Bau den Vorgabewert** für den Druckerrand und
  wurde zehn Bilder später zu einem `NaN` beim Zeichnen des Klebeplans.

---

## [0.0.3-alpha] – 2026-09-08

**Die erste Fassung, die keine Vorabversion mehr ist** — und die erste, an der ein Messschieber
war. Dazu bekommt das Programm ein eigenes Fenster.

### Am Papier nachgemessen

**Der gedruckte 100-mm-Kontrollmaßstab misst 100 mm. Das 50-mm-Raster misst 50 mm.** Nachgemessen
am 07.09.2026 mit dem Messschieber an einem echten Ausdruck. Seit dem ersten Tag stand in jeder
Fassung dieses Protokolls derselbe Vorbehalt — „belegt nur gegen synthetische Szenen, der Beweis
am Papier steht aus". Er steht nicht mehr aus.

**Was damit belegt ist: `PDF → Drucker → Papier`.** Die Seitengeometrie stimmt, und der Drucker
skaliert nicht. Das war eine der beiden Hälften, an denen dieses Werkzeug scheitern konnte, und
sie ist zu.

**Was damit nicht belegt ist: `Foto → Marker → Millimeter`.** Und das gehört genauso deutlich
hierher, denn der Unterschied ist nicht offensichtlich: Maßstab und Raster zeichnet die
PDF-Schicht aus **denselben** Millimeterzahlen, in denen der Zuschnitt angegeben ist. Läge die
Homographie daneben, käme die Schablone falsch groß heraus — und Maßstab und Raster mäßen darauf
trotzdem tadellos. Sie können diesen Fehler nicht sehen.

Was ihn sähe: einen Gegenstand **bekannter** Länge mit aufs Foto legen, die Schablone drucken und
**diesen Gegenstand** auf dem Ausdruck nachmessen. Das steht weiter aus.

Deshalb bleibt `alpha` im Namen, obwohl diese Fassung **nicht mehr als Vorabversion**
veröffentlicht wird: geprüft genug, um sie zu benutzen, nicht geprüft genug, um sich das Messen
am fertigen Teil zu sparen.

### Das Programm bekommt ein eigenes Fenster Bis hierher öffnete ein Doppelklick den
Standardbrowser: die Anwendung war ein Reiter zwischen zwanzig anderen, wurde beim Aufräumen des
Browsers mitgeschlossen und sah dann verschwunden aus, obwohl ihr Server weiterlief. Ein Fenster
mit eigenem Namen in der Taskleiste ist ein Programm. Am Rechenweg ändert sich **nichts** — es
ist dieselbe Oberfläche auf demselben Server, nur in einem anderen Rahmen.

### Hinzugefügt

- **Ein eigenes Fenster (pywebview) als Vorgabe.** Ein Doppelklick auf die `.exe` öffnet die
  Anwendung in einem Fenster von 1200 × 860 Punkt, das nicht kleiner als 900 × 600 gezogen
  werden kann. Die Breite ist nicht geraten: der Inhalt der Oberfläche ist auf 68 rem begrenzt
  und braucht mit seinen Rändern rund 1136 Punkt — darüber gewönne man nichts mehr. Beide Maße
  stehen in `app/config.py` (Invariante 4), der Fenstertitel ist der Produktname, der jetzt
  ebenfalls dort steht und nicht mehr an drei Stellen getippt wird.

  **Der Server bleibt, was er war.** Er läuft weiter, gibt weiter LAN-Adresse und QR-Code aus,
  und das Handy erreicht ihn weiter, während das Fenster offen steht. Das Fenster ist eine
  *zweite Ansicht* auf denselben Server, keine zweite Anwendung — und das ist der Punkt, denn
  das Foto kommt vom Handy.

  Zwei Kleinigkeiten, die pywebview anders vorgibt, sind ausdrücklich zurückgestellt: Textauswahl
  bleibt erlaubt und Strg+Mausrad zoomt weiter. Das Fenster soll sich verhalten wie der
  Browser-Reiter, den es ersetzt, und in einer Oberfläche voller Zahlenfelder und kleiner
  Messwerte will man beides haben. Aus demselben Grund läuft es **nicht** im Privatmodus: die
  gewählte Sprache und das gewählte Thema stehen im `localStorage`, und die sollen den nächsten
  Start überleben.
- **`--browser` als Notausgang.** Nimmt statt des Fensters den Browser des Systems — das
  bisherige Verhalten, für den Rechner, auf dem das Fenster nicht taugt.

### Geändert

- **`--no-browser` heißt weiterhin „gar nichts aufmachen"** — weder Fenster noch Browser, nur
  der Server. Die Bedeutung ist absichtlich unverändert geblieben: die Freigabeprüfung fährt die
  Anwendung damit ohne Anzeige hoch, und ein Schalter, der plötzlich ein Fenster öffnete, ließe
  sie auf ein Fenster warten, das niemand schließt. Stehen `--browser` und `--no-browser`
  zusammen da, gewinnt `--no-browser`.
- **`.\dev.ps1 start-server` sagt jetzt das Richtige** und reicht beide Schalter durch.

### Sicherheitsnetz

- **Kein Fenster ist kein Abbruch.** Fehlt pywebview, fehlt die WebView2-Laufzeit (Windows 10
  ohne Nachinstallation) oder wirft die Anzeige-Maschine beim Aufbauen, dann sagt das Programm
  in **einer** Zeile, was fehlt, und öffnet den Browser. Der Server startet in jedem dieser Fälle
  trotzdem — ein Werkstattrechner ohne WebView2 bleibt vom Handy aus voll benutzbar.

  Der heikelste dieser Fälle ist der stille: **ohne WebView2-Laufzeit fällt pywebview unter
  Windows wortlos auf die alte IE-Maschine zurück.** Die kennt keine ES-Module, und die
  Oberfläche besteht aus welchen — das Fenster ginge auf und bliebe leer. Ein leeres Fenster
  sieht aus wie ein Absturz ohne Meldung. Deshalb wird vor dem Öffnen gefragt, *womit* gezeichnet
  würde, und MSHTML ausdrücklich abgelehnt; die Meldung nennt den winget-Befehl, der die
  Laufzeit nachrüstet. `tests/test_window.py` hält beides fest.

### Geprüft

`.\dev.ps1 run-tests`: **161 grün** (153 vorher, acht neue in `tests/test_window.py`).

Das Fenster wurde nicht behauptet, sondern **gesehen** — aus dem Quellbaum und, was allein zählt,
aus der gebauten `.exe`: Fenstertitel `ArUco-Homographie`, Rahmen 1200 × 860, darin die
vollständige Oberfläche mit Kopfzeile, Schritt 1 und Markenstreifen. Der Bau brauchte dafür zwei
Zeilen in `aruco-homographie.spec`: die Anzeige-Module von pywebview als `hiddenimports` (sie
werden erst zur Laufzeit über einen Namen gezogen) und `webview/js` als Datendateien — der
mitgelieferte PyInstaller-Hook sammelt nur `webview/lib`, und ohne die JavaScript-Dateien stirbt
der Fensterstart mit „Cannot find JS directory". Im Quellbaum fällt das nicht auf; es fällt erst
an der ausgelieferten `.exe` auf.

Ebenfalls an der gebauten `.exe` gemessen: `--no-browser` startet **ohne Fenster und ohne
Browser** und beantwortet HTTP; bei offenem Fenster antwortet die **LAN-Adresse** und liefert ein
Markerblatt-PDF; `--browser` ruft den Browser und öffnet kein Fenster.

**Was damit nicht bewiesen ist:** der Rückfall auf den Browser auf einem Rechner, dem die
WebView2-Laufzeit wirklich fehlt. Dieser Rechner hat sie (v152), also ist dieser Weg nur im Test
belegt, nicht am echten Windows 10.

## [0.0.2-alpha] – 2026-09-07

**Die Fassung, die einen richtigen Installer mitbringt.** 0.0.1-alpha kam als ZIP, das man selbst
auspacken musste — und zwar an eine Stelle, die nicht zu tief liegen durfte, sonst starb das
Programm beim Start an Windows' 260-Zeichen-Grenze. Hier gibt es stattdessen **eine Datei**:
doppelklicken, durchklicken, fertig. Am Rechenweg hat sich **nichts** geändert; die Millimeter
kommen aus demselben Code wie vorher.

### Hinzugefügt

- **Ein Windows-Installer — eine Datei, nichts zu entpacken.** `.\dev.ps1 build-installer` baut
  mit Inno Setup `dist\ArUco-Homographie-Setup-<Fassung>.exe`: **rund 78 MB** statt eines
  114-MB-ZIPs, das man erst auspacken muss und dabei auch noch an der richtigen Stelle.
  (Auf die Byte genau steht die Zahl hier bewusst nicht: zwei Bauläufe aus demselben Quellstand
  ergaben 81 780 869 und 81 786 796 Byte. PyInstaller schreibt Zeitstempel ins Bundle, und was
  sich nicht wiederholen lässt, gehört nicht als genaue Zahl in ein Änderungsprotokoll.)
  Doppelklicken, durchklicken, fertig — Startmenü-Eintrag, wahlweise ein Schreibtischsymbol
  (unangehakt, wie es Windows macht) und ein Deinstallierer in *Apps & Features*.

  Installiert wird **ohne Administratorrechte** für den angemeldeten Benutzer nach
  `%LOCALAPPDATA%\Programs\ArUco-Homographie`. Zwei Gründe, und beide zählen an einem
  Werkstattrechner: wer dort sitzt, ist oft kein Administrator — und weil jetzt der *Installer*
  den Zielpfad wählt und nicht der Benutzer beim Entpacken, **ist die MAX_PATH-Falle für diesen
  Weg weg**. Das war der Fehler, der wie ein Codefehler aussah und keiner war: ein zu tiefer
  OneDrive-Ordner riss Windows' 260-Zeichen-Grenze, und die `.exe` starb beim Start mit
  „DLL load failed … Dateiname oder Erweiterung ist zu lang".

  **Das Bundle bleibt One-Folder.** Der Installer ersetzt es nicht, er umhüllt es. One-File
  entpackte weiterhin bei jedem Start über 100 MB OpenCV, NumPy und SciPy in ein
  Temp-Verzeichnis und kostete dafür Sekunden Startzeit — der Installer kopiert einmal.

  Die Bauvorschrift `installer/aruco-homographie.iss` ist versioniert, denn sie ist Quelltext.
  Sie enthält **keine** Fassungsnummer und keine Markenzeichenkette: `dev.ps1` liest beides aus
  `app/config.py` und reicht es als `/D`-Definition hinein. Die `AppId` ist eine feste GUID und
  darf nie geändert werden — sonst stellte die nächste Fassung sich daneben, statt zu ersetzen,
  und es lägen zwei Bundles à 290 MB auf der Platte. `ISCC.exe` wird gesucht statt
  festgeschrieben (`PATH`, Installation pro Benutzer, beide `Program Files`); fehlt sie, nennt
  die Meldung `winget install --id JRSoftware.InnoSetup`.

  Der ZIP-Weg (`.\dev.ps1 build-exe`, ganzer Ordner) bleibt dokumentiert — für Rechner, auf
  denen nichts installiert werden darf.
- **Die `.exe` sagt jetzt, von wem sie ist.** Rechtsklick → Eigenschaften → Details war bei der
  Anwendung **vollständig leer** — PyInstaller legt von sich aus keine Versionsressource an, und
  ohne die steht dort kein Herausgeber, keine Fassung, gar nichts. `aruco-homographie.spec` legt
  sie nun an: `CompanyName` (Bischof Snowboards), `ProductName`, `FileDescription`,
  `FileVersion`, `ProductVersion`, `LegalCopyright`, dazu `InternalName`, `OriginalFilename` und
  die Adresse als `Comments`. Die Setup-`.exe` trug Herausgeber und Produkt schon, aber **keinen
  Urheberrechtsvermerk**; die `VersionInfo*`-Anweisungen in der `.iss` setzen jetzt alle vier
  ausdrücklich, statt sich auf Inno-Vorgaben zu verlassen.

  Nichts davon ist abgetippt: die Vorschrift importiert `app/config.py` (sie ist selbst Python),
  die `.iss` bekommt die Werte wie gehabt als `/D`-Definitionen. Die **Beschreibung** kommt aus
  dem i18n-Katalog — es ist derselbe Satz, den die Kopfzeile der Oberfläche zeigt, denn eine
  sichtbare Zeichenkette gehört in den Katalog (Invariante 7). Fehlt der Schlüssel, **bricht der
  Bau ab**, statt „ui.header.subtitle" in die Eigenschaften der ausgelieferten `.exe` zu schreiben.

  Der Urheberrechtsvermerk steht in `config.py` als reines ASCII (`Copyright (C) …`), weil er
  auf dem Weg zu Inno Setup durch zwei Konsolen-Stationen muss und ein Sonderzeichen dort von
  der Codepage abhinge. Gemessen: auf diesem Rechner steht die Konsole zufällig auf UTF-8 und
  es ginge gut — auf cp850, der Vorgabe, würde aus dem Zeichen lautlos ein anderes. Sichtbar
  wird trotzdem das richtige Zeichen: Inno ersetzt `(C)` von sich aus (nachgemessen), und die
  Bauvorschrift tut im eigenen Prozess dasselbe. Auf beiden `.exe` steht derselbe Text.

  **Das ersetzt keine Signatur.** SmartScreen zeigt weiterhin *Unbekannter Herausgeber*:
  Dateieigenschaften kann jeder hineinschreiben, und Windows weiß das. Dagegen hilft nur ein
  Code-Signing-Zertifikat.
- **`APP_VERSION` in `app/config.py`.** Die Fassungsnummer stand bisher nirgends im Code, nur in
  dieser Datei und im Git-Tag. Jetzt hat sie eine Stelle, und zwar die für Konstanten vorgesehene
  (AGENTS.md, Invariante 4). `dev.ps1` liest sie von dort, wie es den Port schon las. Daneben
  `APP_VERSION_TUPLE`/`APP_VERSION_NUMERIC` (`0.0.2.0`) und `BRAND_COPYRIGHT`. Die binären
  Versionsfelder von Windows nehmen nur vier ganze Zahlen und weisen `0.0.2-alpha` ab —
  abgeschnitten wird deshalb **einmal**, in `config.py`; Bauvorschrift und Installer nehmen beide
  dieses Ergebnis, statt die Regel jeder für sich zu erfinden.
- **`--port N` beim Start.** Verschiebt den *Wunsch*-Port; ausgewichen wird danach wie immer.
  Gebraucht, sobald eine zweite Kopie danebenlaufen soll — etwa, wenn eine frisch installierte
  Fassung neben dem Entwicklungsserver geprüft wird. Ein unbrauchbarer Wert bricht nicht ab,
  sondern fällt auf `config.PORT` zurück: ein Doppelklick, der an einem Komfortargument
  scheitert, wäre schlechter als einer auf dem Vorgabeport.

### Geprüft

Der Installer wurde nicht nur gebaut, sondern **still installiert, gestartet, benutzt und wieder
entfernt**: 287 Dateien / 292 MB landeten unter `%LOCALAPPDATA%\Programs\ArUco-Homographie`, die
installierte Fassung lieferte Oberfläche, Themen-Tokens, `main.js` und beide Sprachkataloge aus,
gab ein echtes Markerblatt-PDF heraus und fuhr eine vollständige synthetische Szene durch Upload,
Entzerrung (RMS 0,093 px) und Export (210,000 × 178,000 mm, eine Seite). Danach war nach der
stillen Deinstallation weder das Verzeichnis noch die Verknüpfung noch der Eintrag in
*Apps & Features* übrig.

Die Dateieigenschaften wurden an **beiden** gebauten `.exe` zurückgelesen. Sie stimmen überein:
Herausgeber `Bischof Snowboards`, Produkt `ArUco-Homographie`, Fassung `0.0.2-alpha`, binär
`0.0.2.0`, `Copyright © Bischof Snowboards`.

**Was damit nicht bewiesen ist:** die Maßhaltigkeit am Papier. Sie ist weiterhin ausschließlich
gegen synthetische Szenen belegt, und geprüft wurde auf **diesem** Rechner, nicht auf einem
fremden ohne Python.

## [0.0.1-alpha] – 2026-09-07

**Die erste veröffentlichte Fassung.** Inhaltlich ist das der Stand von 0.3.0 — neue
Funktionen kommen hier keine dazu. Die Nummern 0.1.0 bis 0.3.0 darunter sind
Entwicklungsschritte, zu denen es nie ein veröffentlichtes Erzeugnis und keinen Tag gab;
die Zählung der *Veröffentlichungen* fängt deshalb bei 0.0.1 neu an, statt eine Herkunft
vorzutäuschen, die es nicht gibt.

**Warum `alpha`:** weil die zentrale Zusage dieses Projekts noch offen ist. Die
Maßhaltigkeit ist bis heute **ausschließlich gegen synthetische Szenen** belegt — eine
virtuelle Kamera, gerenderte Marker, bekannte Grundwahrheit. Der Beweis am echten
Ausdruck steht aus: drucken, mit dem Messschieber nachmessen, das Ergebnis festhalten.
Bis das passiert ist, gilt: **jede Schablone vor dem Sägen am aufgedruckten
100-mm-Maßstab nachmessen.**

### Beigelegt

`ArUco-Homographie-v0.0.1-alpha-win64.zip` — das One-Folder-Bundle für Windows x64.
Entpacken, `ArUco-Homographie.exe` doppelklicken; auf dem Zielrechner muss **kein Python**
installiert sein. Es wird der **ganze Ordner** gebraucht, nicht nur die `.exe` darin.

Zwei bekannte Grenzen, beide keine Codefehler, beide sehen aber wie welche aus: der
Zielordner darf nicht zu tief liegen (Windows' 260-Zeichen-Grenze, siehe README), und die
`.exe` ist nicht signiert, weshalb SmartScreen beim ersten Start warnt.

## [0.3.0] – 2026-09-07

Der Tag, an dem die Oberfläche zweisprachig, umschaltbar hell/dunkel, auf dem Handy
bedienbar und um eine Bildaufbereitung reicher wurde. Am Rechenweg hat sich **nichts**
geändert: die Homographie wird nach wie vor am unberührten Foto gemessen.

### Hinzugefügt

- **Deutsch und Englisch aus einem Katalog.** Jede sichtbare Zeichenkette kommt aus
  `app/static/i18n/`, einer Datei je Sprache — dieselben Dateien für den Browser, für die
  Warnungen und Fehler des Servers und für den PDF-Aufdruck. Keine zweite Fassung, kein
  Nachpflegen an drei Stellen. Warnungen und Fehler tragen jetzt einen Code plus Parameter
  statt eines fertigen Satzes; der Satz entsteht erst am Rand. 184 Schlüssel je Sprache, und
  `tests/test_i18n.py` besteht darauf, dass die Schlüsselmengen gleich bleiben, dass jeder
  Platzhalter auf beiden Seiten existiert und dass jeder in `app/` erhobene Code auch einen
  Text hat.
- **Sprachumschalter in der Kopfzeile.** Der Wechsel rendert die Seite ohne Neuladen, schreibt
  `<html lang>` und `document.title` um und schickt `Accept-Language` an jede Anfrage, damit
  Servermeldungen der App folgen und nicht dem Browser.
- **Der Ausdruck folgt der gewählten Sprache.** `ExportRequest` hat ein `locale`-Feld, über
  `i18n.normalise` normalisiert — ein Export scheitert niemals an einer Sprachangabe, er
  kommt dann eben in der Vorgabesprache. Das Markerblatt nimmt die Sprache als `?locale=`
  entgegen, weil ein einfacher Anker keine Kopfzeile mitschicken kann.
- **Helles und dunkles Thema**, mit einer Schaltfläche in der Kopfzeile. Es gibt **drei**
  Zustände: ausdrücklich hell, ausdrücklich dunkel, und gar keine gespeicherte Wahl — dann
  gilt die Systemvorgabe, auch wenn sie mitten in der Sitzung umschaltet. Die Tokennamen
  stammen aus `snow-service-free`, damit die Werkzeuge des Hauses dieselbe Sprache sprechen.
- **Bildaufbereitung vor dem Druck** (`app/vision/enhance.py`): Schwarzweiß, Negativ,
  Helligkeit, Kontrast, Sättigung, lokaler Kontrast (CLAHE), Kantenanhebung, aufgelegte
  Kantenzeichnung, Farbbetonung und Schwelle. Live-Vorschau über `POST /api/adjust`, dieselben
  Regler im Export.
  **Sie greift ausschließlich am bereits entzerrten Bild an, nie vor der Markererkennung** —
  ein Schärferegler vor dem Detektor würde die Markerecken und damit die Millimeter
  verschieben. `tests/test_enhance.py` misst die Subpixel-Lage einer Kante vor und nach jedem
  einzelnen Eingriff: Schwarzweiß, Schwelle und Kantenanhebung verschieben sie um exakt
  0,000000 px; der lokale Kontrast um 0,11 px, weil CLAHE die Flanke kachelweise kippt — bei
  300 dpi sind das 0,009 mm.
- **Das Zuschnitt-Rechteck lässt sich endlich ändern.** Acht Griffe (vier Ecken, vier
  Kantenmitten), Ziehen im Inneren verschiebt, Ziehen auf freier Fläche zieht wie bisher ein
  neues auf, Pfeiltasten schieben um 1 mm und mit Shift um 10 mm. Vorher gab es genau eine
  Geste: neu aufziehen.
- **Bedienbar auf dem Handy.** Eine Spalte, Berührungsziele von mindestens 44 px, kein
  waagerechter Überlauf bei 360 und 390 px Breite, und die Zuschnittfläche bleibt benutzbar.
  Das Handy, das das Foto gemacht hat, kann damit den ganzen Ablauf über die LAN-Adresse
  fahren.
- **[`docs/plans.md`](docs/plans.md)**: die Vorhaben, an denen niemand arbeitet, die aber
  gebaut werden sollen — Windows-`.exe`, Android-`.apk`, ein geteilter Rechenkern, DXF-Export
  für die Fräse. Mit Weg, bekannten Stolpersteinen und offenen Fragen, damit sie nicht bei
  jedem Gespräch neu hergeleitet werden.
- **[`docs/design/design-system.md`](docs/design/design-system.md)** und
  [`docs/design/README.md`](docs/design/README.md): das Designsystem des Hauses und seine
  Herkunft, samt der drei Tokens, die gegenüber `free` bewusst korrigiert sind, weil sie dort
  auf ihrem eigenen Untergrund unsichtbar wären.
- **[`docs/contributing/git.md`](docs/contributing/git.md)**: die verbindlichen Git-Regeln,
  einmal aufgeschrieben statt in drei Fassungen verstreut.
- **[`docs/README.md`](docs/README.md)**: das Inhaltsverzeichnis der Dokumentation. Jede Datei
  unter `docs/` mit Zweck, Zielgruppe und Stand — und ein YAML-Frontmatter-Schema, an dem ein
  Skript den Baum aufzählen und prüfen kann.

- **Auslieferung als Windows-`.exe`.** `.\dev.ps1 build-exe` baut mit PyInstaller ein
  One-Folder-Bundle nach `dist/ArUco-Homographie/`. Doppelklick startet den Server und
  öffnet den Browser; Python muss auf dem Rechner nicht installiert sein. Weitergegeben
  wird der ganze Ordner, nicht nur die `.exe` darin. Bewusst **nicht** One-File: das
  entpackt bei jedem Start OpenCV, NumPy und SciPy in ein Temp-Verzeichnis und kostet
  Sekunden Startzeit für nichts.
- **`aruco-homographie.spec`** — die Bauvorschrift ist versioniert, nicht eine
  Kommandozeile, die mit dem Terminalfenster verlorengeht. Sie trägt, was die statische
  Analyse von PyInstaller nicht findet: den ganzen Baum `app/static/**` und die
  Datendateien von ReportLab.
- **`config.resource_path()`** löst jeden Pfad auf eine mitgelieferte Datei auf —
  `sys._MEIPASS` im Bundle, `app/` im Quellbaum. Ohne den Helfer startet die `.exe` und
  liefert eine nackte Seite ohne Schrift, ohne Logo und ohne Übersetzung: der gefährliche
  Fehler, weil er wie ein Erfolg aussieht.
- `tests/test_startup.py` prüft die drei Dinge, die sonst erst am Werkstattrechner
  auffallen: Ausweichen auf einen freien Port, ein Banner, das eine Konsole ohne
  Blockzeichen überlebt, und Datenpfade, die dem Bundle folgen.
- VS-Code-Task **„Build Windows .exe"** — ruft wie alle Tasks nur `dev.ps1` auf.

### Geändert

- **Die Vorgabe des Exports ist die Kachelung auf A4 mit Klebeplan**, nicht mehr die
  Einzelseite. Eine Schablone in Originalgröße passt auf keinen Drucker, den hier jemand hat;
  die alte Vorgabe erzeugte also verlässlich etwas Undruckbares und musste vor jedem Gebrauch
  von Hand korrigiert werden. Der Wert steht in `config.LAYOUT_DEFAULT`. Bewusst **nicht**
  mitgezogen wurde `ExportOptions` in der PDF-Schicht: dort ist „eine Seite" der schlichte
  Fall und Kachelung eine Betriebsart, die ein Aufrufer verlangt.
- **Die Oberfläche ist auf Design-Token und i18n-Schlüssel neu gebaut.** Aus einer
  388-Zeilen-`app.js` und einem nur dunklen Stylesheet mit handgeschriebenen Farben wurden
  ES-Module über HTTP, ohne Build-Schritt: `i18n`, `theme`, `api`, `header`, `crop-geometry`,
  `crop-rect`, `crop-info`, `adjust`, `report`, `main` — das Stylesheet entlang derselben
  Linien geteilt. Jede Farbe, jeder Radius und jeder Abstand kommt aus `tokens.css`; im neuen
  CSS steht kein einziges Farbliteral.
- **Committen braucht keine Rückfrage mehr, Pushen immer.** Die Erlaubnisse sind bewusst
  asymmetrisch: ein Commit ist örtlich und umkehrbar, ein Push ist sofort öffentlich. Fertig
  **und geprüft** ist nicht die Erlaubnis zu committen, sondern der Auslöser. Diese Regel
  weicht bewusst von der globalen Fassung in `~/.claude/CLAUDE.md` ab.
- **Testartefakte und Screenshots bleiben aus dem Verzeichnisbaum.** Die Regeln sind an die
  Projektwurzel geheftet, damit ein pauschales `*.png` nicht die Favicons und Logos unter
  `app/static/` verschluckt; `.vscode/` ist ausgeschlossen, `.vscode/tasks.json` ausdrücklich
  wieder hereingeholt, weil die Tasks zum Projekt gehören.

- **`config.PORT` ist jetzt der *bevorzugte* Port, keine Zusage.** Ist 8000 belegt — auf
  einem Werkstattrechner eine Frage der Zeit —, weicht der Server auf einen freien aus,
  statt mit „address already in use" abzubrechen. Die stabile URL bleibt der Normalfall.
- **Den Browser öffnet `app.main` selbst**, nicht mehr `dev.ps1`. Erst dort steht fest,
  welcher Port es geworden ist; eine vorher gebaute URL wäre nach dem Ausweichen falsch.
  `--no-browser` wird jetzt an den Server durchgereicht statt vom Skript abgefangen.
- **`opencv-python` → `opencv-python-headless`.** Die Anwendung öffnet nie ein
  `cv2`-Fenster. `cv2.aruco` ist im Headless-Rad vollständig enthalten (geprüft:
  `ArucoDetector`, `getPredefinedDictionary`, `generateImageMarker`,
  `CORNER_REFINE_SUBPIX`, Erzeugen-und-Wiedererkennen, gesamte Testsuite). Anders als in
  `docs/plans.md` vermutet spart das unter Windows **nicht** 60–80 MB: die
  OpenCV-5-Räder für Windows bringen gar kein Qt mit, gemessener Unterschied 0,42 MB.
- `kill-servers` beendet auch die gebaute `.exe` aus diesem Verzeichnis, nicht nur
  `python -m app.main`. `clean-all` räumt zusätzlich `build/` und `dist/`.

### Behoben

- **Der Hinweis am Zuschnitt nannte eine Farbe, die es nicht mehr gibt** („grüne Fläche"). Die
  Marker-Hülle leitet ihre Füllung seit dem Umzug auf die Token aus `--primary` ab und ist
  petrol. Ein Satz, der in einer Oberfläche mit zwei Themen auf eine Farbe zeigt, veraltet mit
  der nächsten Nachjustierung — der neue Text benennt die Fläche statt ihrer Farbe. Er ist
  zugleich das `aria-label` der Zeichenfläche.
- **Das Overlay der Zuschnittfläche ignorierte `devicePixelRatio`** und war auf jedem Handy
  und jedem HiDPI-Schirm weichgezeichnet — ausgerechnet über einer Schnittkante.
- **Die Farben des Overlays waren fest verdrahtet** und konnten dem Thema nicht folgen. Ein
  Canvas löst `var()` nicht auf; die Tokens werden jetzt mit `getComputedStyle` gelesen und
  bei jedem Themenwechsel neu.
- **Der Cache-Buster der Vorschau hatte Sekundenauflösung.** Ein Regler überschreibt dieselbe
  Datei mehrmals je Sekunde, der Browser bekam also dieselbe URL und hätte ein veraltetes Bild
  gezeigt. Jetzt in Millisekunden.

- **Der ASCII-QR-Code riss den Start mit, wenn die Ausgabe kein Unicode konnte.** Der Code
  besteht aus Blockzeichen; schreibt Python nicht in eine Windows-Konsole, sondern in eine
  Pipe oder Datei, nimmt es die Codepage des Systems (cp1252) und `print()` bricht mit
  `UnicodeEncodeError` ab. In der `.exe` hieß das: der Server startete wegen einer
  Verzierung gar nicht erst. Jetzt kommt an dieser Stelle ein Hinweis, und der Server läuft.

### Bekannte Grenze

- Der Bundle-Ordner darf nicht zu tief liegen: die längste enthaltene Datei hat 101
  Zeichen relativen Pfad, ab etwa 157 Zeichen Zielordner reißt Windows'
  260-Zeichen-Grenze und die `.exe` bricht beim Start mit „DLL load failed … Der
  Dateiname oder die Erweiterung ist zu lang" ab. Kein Codefehler — sieht aber wie einer aus.

### Weiterhin offen

- **Die Maßhaltigkeit ist nach wie vor nur gegen synthetische Szenen belegt.** Der Beweis am
  echten Ausdruck — drucken, den 100-mm-Maßstab mit dem Messschieber nachmessen, das Ergebnis
  aufschreiben — steht weiter aus. Von allem, was dieses Projekt noch vorhat, ist das das
  Wichtigste; es steht als erster Punkt in [`docs/plans.md`](docs/plans.md), Abschnitt 5.
- Objektivverzeichnung unkorrigiert, gewölbte Objekte prinzipiell nicht möglich, Sitzungen nur
  im Arbeitsspeicher — unverändert gegenüber 0.1.0.

## [0.2.0] – 2026-09-06

### Hinzugefügt

- **Markenzeichen auf jedem Blatt.** Logo und „Made with Bischof Snowboards Software"
  stehen im Streifen unter dem Bild — auf der Einzelseite, auf *jeder* Kachel, auf dem
  Klebeplan und auf dem Markerblatt. Das Logo wird als Vektor aus der Original-SVG des
  Webprojekts eingebettet, nicht als Rasterbild, und ist damit bei jeder Druckgröße
  scharf.
- **Markenblock im PDF verlinkt** auf bischof-snowboards.com; in der Oberfläche führen
  Logo, Markenzeile und Fußzeile auf dieselbe Adresse.
- **Markenfarben und Montserrat** in der Oberfläche. Die Farbtokens stammen aus
  `snow-service-free/src/main.css`, dort in oklch notiert, hier als sRGB in
  `app/config.py`. Gegenprobe: `--foreground oklch(0.3717 0.0392 257.29)` ergibt
  `#334155`, exakt die Tinte, die `logo-dark.svg` im Dateikommentar nennt.
- **Originales Favicon** aus dem Webprojekt statt einer Nachbildung.
- `tests/test_branding.py`: prüft über die PDF-Textextraktion, dass **keine** Seite ohne
  Herkunftszeile herauskommt, und über die Link-Annotationen, dass der Markenblock
  verlinkt ist.
- `test_markersheet.py` rastert das erzeugte Markerblatt und schickt es durch den echten
  Detektor. Ein vertauschtes oder gespiegeltes Modulraster sähe auf dem Bildschirm normal
  aus und fiele sonst erst am realen Foto auf. Gemessen: Kante 66,98 mm, Abstände
  121,00 × 170,99 mm.

### Geändert

- **Das Raster ist kräftiger und auf hellem wie dunklem Untergrund lesbar.** Jede Linie
  wird zweimal gezogen: erst ein breiter weißer Saum, dann die Kernlinie in Markentinte.
  Auf Weiß verschwindet der Saum, auf Schwarz trägt er die Linie. Die Beschriftungen
  sitzen auf weißem Träger und werden in den Bildbereich hineingeklemmt.
- **Der Streifen unter dem Bild ist jetzt immer da**, auch wenn Maßstab und Fußzeile
  abgeschaltet sind — er trägt das Markenzeichen. Damit ist eine Seite nie mehr exakt so
  groß wie das Objekt; das **Bild** belegt aber unverändert exakt `crop_w × crop_h`
  Millimeter, und nur das war je die Zusage.

## [0.1.0] – 2026-09-06

Erste Fassung: Handyfoto rein, maßhaltiges PDF in Originalgröße raus.

### Hinzugefügt

- **Homographie in zwei Modi.** Blatt-Modus mit bekanntem Layout; Frei-Modus, der
  Homographie und Markerpositionen gemeinsam schätzt (8 + 2(n−1) Unbekannte gegen 8n
  Gleichungen). Vorgabe ist das real vermessene Blatt: 67 mm Marker, Mittelpunktabstände
  121 × 171 mm.
- **Dickenkorrektur.** Eine Fläche `h` über der Markerebene erscheint radial vom
  Kamera-Lotpunkt weg gestreckt um `d/(d−h)`; Höhe und Lotpunkt fallen aus der Zerlegung
  der Homographie, sobald die EXIF-Brennweite bekannt ist. Ohne EXIF wird der
  Kameraabstand zur Pflichteingabe.
- **Qualitätsbericht** statt blindem Vertrauen: Restfehler in px und mm, jeder Marker
  gegen seine Sollgröße zurückgemessen, Kamerahöhe und -neigung, und der Anteil des
  Zuschnitts außerhalb der Marker-Hülle.
- **PDF-Export** als Einzelseite in Objektgröße oder gekachelt auf A4/A3 mit Überlappung,
  Schnitt- und Klebemarken und vorangestelltem Klebeplan. Aufdrucke: 100-mm-Kontroll­maßstab,
  Metadaten-Fußzeile, 50-mm-Raster, optional der erkannte Umriss als Vektor-Schnittlinie.
- **Markerblatt-Generator**, Marker Modul für Modul als Vektorrechtecke gezeichnet, mit
  eigenem Kontrollmaßstab und dem Hinweis, nach dem Druck nachzumessen.
- **Weboberfläche** mit Foto-Upload (auch HEIC), Crop-Rechteck mit Live-Millimeteranzeige
  und Druckoptionen; der Server nennt beim Start die LAN-Adresse samt QR-Code fürs Handy.
- **Testsuite gegen synthetische Grundwahrheit.** Virtuelle Kamera, bekannte Pose,
  bekanntes Objekt; die Dickenkorrektur wird beidseitig geprüft. Der Renderer filtert vor
  dem Warp tief — ohne das verschiebt Aliasing die Markerecken um bis zu 0,58 px und der
  Test misst den Testaufbau statt den Detektor.
- **Selbstheilendes `dev.ps1`** mit Stempel über den SHA-256 von `requirements.txt`, plus
  passende VS-Code-Tasks.

### Bekannte Grenzen

- Objektivverzeichnung bleibt unkorrigiert; mit vier koplanaren Markern nicht abtrennbar.
  Gegenmittel beim Fotografieren: Tele, großer Abstand, Objekt mittig.
- Gewölbte Objekte gehen nicht — eine Homographie beschreibt genau eine Ebene.
- Die Maßhaltigkeit ist bisher **nur gegen synthetische Szenen** belegt. Der Beweis am
  echten Ausdruck (drucken, 100-mm-Maßstab mit dem Messschieber nachmessen) steht aus.
