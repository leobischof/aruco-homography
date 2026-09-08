---
title: AFK-Protokoll — C++-Umzug
description: Laufendes Protokoll der unbeaufsichtigten Arbeit am C++-Umzug: Entscheidungen, Irrtümer und Prüflücken.
audience: developer
status: current
updated: 2026-09-08
---

# AFK-Protokoll — C++-Umzug

Unbeaufsichtigte Arbeit ab **2026-09-08**. Hier steht, was entschieden wurde, **während
niemand da war, um gefragt zu werden** — und vor allem, was **nicht belegt** ist.

> **Die wichtigste Zeile dieses Dokuments:** Der Auftrag lautet „durcharbeiten, auch
> durch Blocker hindurch". Deshalb steht hier Arbeit, die **übersetzt, aber nicht
> gemessen** ist. In einem Projekt, dessen Produkt Millimeter sind, ist das ein
> Unterschied ums Ganze. Jede solche Stelle ist unten mit **⚠ UNBELEGT** markiert.

---

## Vorgaben vom Auftraggeber (vor dem Weggehen)

| Frage | Antwort |
|---|---|
| GitHub | **Volle Autonomie:** pushen, PRs öffnen, squash-mergen, am Ende `v0.1.0-alpha` veröffentlichen |
| Android | Werkzeugkette **installieren**, APK bauen, prüfen was ohne Gerät prüfbar ist |
| Bei Blockern | **Weiterarbeiten**, Unbelegtes deutlich kennzeichnen |
| `opencv.js` | **Ins Repo legen** (13,3 MB), nicht bei jedem Bau aus npm ziehen |
| Architektur | **Nativer C++-Kern je Plattform** (MSVC / NDK / Emscripten) — *nicht* der billigere Weg, einen WASM-Bau in drei Hüllen zu stecken |

Zur letzten Zeile: der Spike hat belegt, dass OpenCV-in-WASM **identisch** misst
(1 `float32`-ULP). Damit wäre „ein Bau, drei Hüllen" in 2–3 statt 6–10 Wochen zu haben
gewesen, und Drift wäre bauartbedingt unmöglich. Der Auftraggeber hat sich **bewusst
für den nativen Weg** entschieden: schneller zur Laufzeit, sauberer getrennt. Die
Entscheidung ist notiert, nicht kommentiert — aber sie ist der Grund, warum unten drei
Werkzeugketten stehen und nicht eine.

---

## Was diese Maschine hat und was nicht

Gemessen, nicht vermutet:

| | Stand |
|---|---|
| MSVC | ✅ 14.50.35717 (VS BuildTools 18), `vcvars64` vorhanden |
| CMake | ✅ in den BuildTools (`Common7/IDE/CommonExtensions/Microsoft/CMake`) |
| node / npm | ✅ |
| winget | ✅ (unbeaufsichtigte Installation möglich) |
| Platz auf C: | ✅ 537 GB |
| JDK, Android-SDK, NDK, Android Studio | ❌ **nichts davon** |
| Emscripten | ❌ |
| Docker, WSL | ❌ |
| **Android-Gerät oder Emulator** | ❌ **keins** |

Die letzte Zeile ist die folgenreichste: **ob ein APK auf einem echten Telefon
läuft, kann in dieser Sitzung niemand feststellen.** Gebaut werden kann es, geprüft
werden kann der Kern — gestartet nicht.

---

## Verlauf

### Ausgangslage

- `master` = `03c5909`, `v0.0.3-alpha` veröffentlicht (kein Vorabstand mehr)
- `feat/shared-truth` — Stufe 1 fertig, 174 Tests grün, **lokal**
- `spike/opencv-js` — Stufe 0 fertig, **lokal**

### Einträge

<!-- Neue Einträge kommen ANS ENDE. Jeder Eintrag: was, warum, und was daran unbelegt ist. -->

#### 2026-09-08 · AFK bewaffnet

Fragen vorab gestellt und beantwortet (Tabelle oben). Werkzeugkette inventarisiert.
Reihenfolge festgelegt: Stufe 1 und Stufe 0 landen zuerst auf `master`, weil beide
fertig und geprüft sind und alles Weitere darauf aufbaut.

#### 2026-09-08 · Zweistufiger Zweigfluss eingeführt

Auftrag mitten in der Arbeit: einen `develop`-Zweig anlegen, der behandelt wird wie
`master` bisher. Fertiges und Geprüftes geht nach `develop`, und **nur** `develop` geht
nach `master` — damit auf `master` je Fassung ein Eintrag steht statt eines Dutzends
Zwischenschritte.

Umgesetzt: `develop` von `master` abgezweigt (`ff5af30`), **gleich hart geschützt** wie
`master` (kein Direkt-Push, `enforce_admins`, nur Squash, lineare Historie) und zum
**Vorgabezweig** des Repositories gemacht.

Das Letzte war eine eigene Entscheidung und ist erwähnenswert: dadurch zielt ein
`gh pr create` **ohne `--base`** von selbst auf `develop`. Die Regel wird damit von der
Mechanik durchgesetzt statt von der Disziplin — in einer unbeaufsichtigten Sitzung, in
der niemand einen falsch gezielten PR bemerken würde, ist das der Unterschied zwischen
einer Regel und einer Hoffnung.

Der bereits offene PR #12 (Stufe 0) wurde von `master` auf `develop` umgehängt.

**⚠ Zu beachten beim Fassungs-PR:** `develop → master` wird **ohne** `--delete-branch`
gemergt. `develop` ist kein Feature-Branch. In `docs/contributing/git.md` §7 steht der
Ablauf ausgeschrieben, samt dem Nachziehen von `develop` auf `master` danach.

#### 2026-09-08 · Werkzeugkette steht — bis auf ein Gerät

Alles installiert, nichts davon im Repo (alles unter `_toolchain/`):

| | |
|---|---|
| MSVC 14.50 + CMake | VS BuildTools 18, über `vswhere` gefunden statt festgeschrieben |
| OpenCV 5.0.0 Windows-SDK | 195 MB, nur `vc16`-Bibliotheken — 14.50 bindet trotzdem sauber |
| Emscripten | **6.0.9** |
| JDK | **21.0.12.1 LTS** |
| Android-SDK | NDK **27.2.12479018**, build-tools 35.0.0, platform-tools |
| OpenCV Android-SDK | **16-KB-Seiten-Fassung**, ABIs `arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64` |

**Die 16-KB-Falle ist keine mehr.** In `docs/plans.md` stand sie als Sperre für Android
15+ — sie galt für den Python/Chaquopy-Weg, den es nicht mehr gibt. OpenCV liefert für
den nativen Weg eine eigens ausgerichtete Fassung.

**⚠ Was fehlt: ein Android-Gerät oder ein Emulator.** Ein APK lässt sich hier bauen,
aber **nicht starten**. Alles, was über „übersetzt und gelinkt" hinausgeht, bleibt für
Android unbelegt, bis jemand es auf ein Telefon schiebt.

**`winget` hing 36 Minuten bei 4,8 s Rechenzeit** und legte nichts ab; dahinter wartete
ein untätiges `msiexec` auf etwas, das unbeaufsichtigt nie kommt. Ersetzt durch das
ZIP von Microsoft — kein Installationsprogramm, keine Administratorrechte. Die
Begründung steht als Kommentar im Einrichtungsskript, damit es niemand „zurückrepariert".

#### 2026-09-08 · Stufe 2 fertig — die Kerne messen bit für bit gleich

| | Python | C++ |
|---|---|---|
| Testsuite | **183 grün** | **183 grün** |
| schlechtester Eckfehler | 0,2337 px | **0,2337 px** |
| Mittel über 16 Ecken | 0,1402 px | **0,1402 px** |

**Unterschied: 0,0 px.** Auf beiden Szenen, mit und ohne CLAHE. Und es sind dieselben
Zahlen, die Stufe 0 im **Browser** gemessen hat — drei Implementierungen, ein Ergebnis.

Selbst nachgeprüft, nicht bloß berichtet, einschließlich der Probe, auf die es ankommt:
ein Backend, das still auf Python zurückfällt, zeigte **ebenfalls** 183 grün und bewiese
nichts. `backend.ACTIVE = cpp`, und die geladene Datei ist die übersetzte `.pyd`.

**⚠ Ein Fehler von mir, den der Agent gefunden hat.** Ich hatte ihm mitgeteilt,
`cv::LMSolver` stehe für den Ersatz von `least_squares` bereit. Den Namen gibt es in
OpenCV 5.0.0 **nicht**; die Klasse heißt `cv::LevMarq`. Ich hatte ihn aus einer Liste
von Symbolen abgeleitet, die der **JavaScript**-Oberfläche des WASM-Baus fehlen — die
sagt nichts darüber, wie die C++-Kopfdateien etwas nennen. Eine Symbolliste ist kein
API-Verzeichnis, und ich habe sie als eines benutzt. Berichtigt in PR #18.

**Nebenbefund, der Stufe 4 bindet:** `cv::contourArea` ist nach `geometry` gewandert,
wo auch `LevMarq` liegt. **`geometry` muss auf jede WASM-Whitelist**, sonst fehlen
beide Hälften der Messung auf einmal.

#### 2026-09-08 · Die Windows-Hülle misst mit C++ (PR #22)

Bis hierher lag der C++-Kern nur in `core/build/` und wurde ausschließlich von der
Testsuite benutzt. **Die ausgelieferte `.exe` rechnete weiter in Python** — der Umzug
war an genau der Stelle unsichtbar, an der er ankommen soll. Das ist jetzt zu:
`aruco-homographie.spec` legt `.pyd` und `opencv_world500.dll` ins Bundle, und
`app/vision/backend.py` nimmt im eingefrorenen Zustand `cpp` als Vorgabe.

Ganzer Beleg mit Zahlen: [`stage-4-windows-exe.md`](stage-4-windows-exe.md).

**Wieder die Probe, auf die es ankommt.** Banner und Zahlen bestünde auch eine `.exe`,
die den Kern mitschleppt und still in Python weiterrechnet — sie rechnet ja richtig.
Also die `.pyd` weggenommen: **der Server kommt nicht hoch**, mit der Meldung, die den
fehlenden Kern nennt. Ohne diesen Schritt wären die beiden anderen wertlos.

**Der Preis, ungeschönt:** das Bundle wächst von rund 308 MB auf 388 MB, der Installer
von rund 78 MB auf 103 MB. `opencv_world500.dll` (80 MB) muss mit, solange `cv2` für
alles außer dem Detektor gebraucht wird — `core/` umfasst heute genau **eine** Rechnung,
`detect_markers`. Das ist der ehrliche Stand: der Umzug hat den Detektor bewegt, nicht
die Kette.

#### 2026-09-08 · Drei Dinge, die beim Hinsehen aufgefallen sind

**1 · `./dev.ps1 run-tests-js` war auf einem frischen Klon kaputt** (PR #24). Zwei
Fehler in einer Zeile, beide nur dort sichtbar, wo `node_modules` fehlt — also genau da,
wo die Selbstheilung greifen soll. `npm` löst unter Windows auf `npm.ps1` auf, und dieser
Aufsatz stirbt am `Set-StrictMode` von `dev.ps1`; und `--prefix` trug das Projekt als
Abhängigkeit von sich selbst in `package.json` ein. Beides an einem wirklich leeren Baum
nachgemessen, nicht angenommen.

**2 · Acht Dokumente standen nicht im Verzeichnis** (PR #23). `docs/README.md` verlangt
Frontmatter ausnahmslos und einen Eintrag in §1 — der ganze C++-Umzug hat sich an beides
nicht gehalten, mein eigenes `stage-4-windows-exe.md` eingeschlossen. Nachgetragen. Das
Skript, das die Regel künftig durchsetzt, steht als Kandidat in `docs/plans.md`; ein
lauffähiger Entwurf hat alle acht Fälle gefunden.

**3 · `v0.0.2-alpha` trägt `prerelease=false`** und ist damit als Vollversion markiert,
obwohl `CHANGELOG.md` unter 0.0.3-alpha ausdrücklich sagt, das sei „die erste Fassung,
die keine Vorabversion mehr ist". Die Kennzeichnung ist also falsch. **Nicht geändert:**
eine veröffentlichte Fassung nachträglich umzuetikettieren ist nach außen sichtbar und
steht nicht im Auftrag. Ein Befehl, wenn gewünscht:

```powershell
gh release edit v0.0.2-alpha --prerelease
```


#### 2026-09-08 · `v0.1.0-alpha` ist veröffentlicht — der Auftrag ist abgearbeitet

Alle drei Ziele liegen in einer Fassung, wie es Abschnitt 5a verlangt. Die
veröffentlichten Dateien sind **wieder heruntergeladen und über SHA-256 gegen die
gebauten gehalten** — alle drei byteweise gleich:

| Datei | Byte | SHA-256 |
|---|---|---|
| `ArUco-Homographie-Setup-0.1.0-alpha.exe` | 102 907 175 | `719a5fa5c46d60af…` |
| `aruco-homographie-0.1.0-alpha-debug.apk` | 10 790 324 | `c1de0659743b7387…` |
| `aruco-homographie-web-0.1.0-alpha.zip` | 1 587 968 | `a6fa852aca31a19f…` |

Der Weg über die zwei Zweige ist genau so gegangen worden, wie ihn der berichtigte
Abschnitt 7 in `docs/contributing/git.md` beschreibt: Squash von `develop` nach
`master`, **ohne** `--delete-branch` und **ohne** Merge zurück. Nachgesehen: `develop`
steht unverändert auf `0f5e84a`, und der Baum von `master` ist mit ihm deckungsgleich.

**Was ich an den Berichten der Agenten selbst nachgemessen habe** — nicht weitergereicht:

- Die vier Testkombinationen, die JS-Prüfungen, den Prüfstand mit und ohne
  C-Schnittstelle, `check-jni` auf der JVM, `check-android-ui` bis zum PDF.
- **Ob das APK den verbotenen Abkürzungsweg nimmt.** Selbst mit `zipfile` hineingesehen:
  kein `.wasm`, kein `aruco_core.mjs`, kein `core.js`. Gemessen wird durch
  `lib/arm64-v8a/libaruco_core.so`.
- **Ob Browser und Android wirklich dieselbe Kette fahren.** SHA-256 je Datei:
  **16 von 16** im APK sind byteweise die aus `web/vision/`. Ausgetauscht ist nur der
  Kern-Adapter — `core.js` gegen `core-android.js`.
- Die gebaute `.exe`, einschließlich des Gegenbeweises: ohne die `.pyd` startet sie nicht.
- Das erzeugte PDF **angesehen**, nicht nur vermessen (`CLAUDE.md`).

**Zwei Berichtigungen an Agentenberichten**, beide belegt statt behauptet:

1. Ein Agent meldete, mein `rms 0,093 px` sei falsch, richtig seien 0,095. **Beides
   stimmt.** Ich hatte die Szene als JPEG kodiert, er nahm `flat.png` — dasselbe Bild
   (SHA-256 gleich), dieselbe Kette, 0,093 gegen 0,095. Eine rms-Angabe ohne die
   Kodierung dazu ist eine Falle.
2. Derselbe Bericht nannte `ARUCO_PDF=reportlab` als geprüfte Kombination. Den Wert
   gibt es nicht — `app/pdf/__init__.py` **weist ihn ab**, statt still auf ReportLab zu
   fallen. Genau das soll er tun.

#### 2026-09-08 · Was nach der Veröffentlichung offen bleibt

- **`v0.0.2-alpha` trägt weiter `prerelease=false`.** Unverändert nicht angefasst, aus
  demselben Grund wie oben: nach außen sichtbar, nicht im Auftrag.
- **Der Markerblatt-Knopf im Browser-Bau** trägt `/api/markersheet` als statischen
  `href`, bis `header.js` ihn durch ein örtlich gebautes PDF ersetzt. Wer in dem
  Sekundenbruchteil davor klickt, bekommt einen 404. Beim Nachmessen des ZIP gefunden,
  in den Fassungsnotizen benannt, **nicht behoben** — die Berichtigung hätte den
  Erzeugungslauf verändert, den ich gerade geprüft hatte.
- **`./dev.ps1 check-jni` ist mir einmal fehlgeschlagen** und danach zweimal gelungen,
  auch aus einem vollständig gelöschten `core/build`. Der fehlschlagende Zustand war ein
  Bauverzeichnis aus der Zeit vor einem Rebase. Nicht wieder herstellbar, also nicht als
  behoben verbucht; das Mittel ist `Remove-Item core\build -Recurse`.
- **Ein Agent hat in den Live-Checkout geschrieben** (`markersheet-base64.txt`, ein
  gültiges A4-Markerblatt), obwohl der Auftrag das ausschloss. Unversioniert, entfernt.


#### 2026-09-08 · Was noch unbelegt ist

Der Auftrag lautet „durch Blocker hindurcharbeiten". Damit niemand mehr hineinliest,
als drinsteht:

- **Der Messschieber-Beleg hängt weiter an der Python-Kette.** `100 mm = 100 mm` wurde
  an einem Ausdruck gemessen, den Python erzeugt hat. Der C++-Kern erbt das erst, wenn
  er die ganze Kette fährt.
- **Und auch dieser Beleg deckt nur die halbe Kette:** `PDF → Drucker → Papier`. Der Weg
  `Foto → Marker → Millimeter` ist nach wie vor nur gegen synthetische Szenen belegt.
- **Kein echtes Foto.** Alles bisher Gemessene ist gerechnet.
- **Android: nichts ausgeführt.** Siehe oben. — **Eingelöst am 08.09.2026**, siehe den
  Eintrag darunter: ein echtes Telefon hat den Prüfstand selbst gefahren.

---

#### 2026-09-08 · Ein Gerät hat geantwortet — und zwei Fehler mitgebracht

Der Satz, der oben viermal steht — *auf einem Android-Gerät ist nichts gelaufen* — ist
seit diesem Tag falsch. Der Bediener hat `v0.1.0-alpha` auf einem **Xiaomi 2312DRA50G,
Android 15 (API 35)** installiert und den Knopf „Prüfstand laufen lassen" gedrückt:

> **BESTANDEN.** `flat` 0,2337 px in 83 ms, `thick` 0,2337 px in 84 ms, je 4/4 Marker,
> Toleranz 0,7500 px. Beide SHA-256 der Prüfszenen **genau die vorhergesagten**.

**Was daran zählt, ist nicht das Wort BESTANDEN, sondern die Prüfsummen.** Sie sagen,
dass Androids PNG-Dekoder dieselben Pixel geliefert hat wie `cv2` — und erst dadurch ist
der gleiche Eckfehler eine Aussage über den *Detektor* statt über das *Laden*. Ein
Prüfstand, der nur ein Urteil ausgibt, hätte diesen Unterschied verschluckt. Das ist der
Ertrag der Entscheidung, ihn Zahlen ausgeben zu lassen.

**Und derselbe Lauf hat zwei Fehler gefunden, die hier keine Prüfung finden konnte:**

1. Die Oberfläche lag unter Statusleiste und Navigationsleiste (Android 15 erzwingt
   Edge-to-Edge ab `targetSdk 35`). Kein Prüfstand auf diesem Rechner hat je ein Fenster
   mit Systemleisten gesehen.
2. Der Export brach mit `Error invoking core: Java exception was raised during method
   invocation` ab — einem `OutOfMemoryError`, den `catch (Exception)` nicht fing, bei
   einem Ausgaberaster von 169 Megapixeln. Auf einem Rechner mit 32 GB fällt eine
   Speichergrenze, die es nur auf einem Telefon gibt, nicht auf.

**Die Lehre, und sie ist unbequem:** die Belegkette dieses Projekts war so dicht, wie sie
ohne Gerät sein kann — JNI auf einer echten JVM, die Kette aus dem APK in einem echten
Chromium, jedes Erzeugnis nachgemessen. Sie hat den Detektor richtig vorhergesagt, auf die
vierte Stelle. Beide Fehler, die trotzdem übrig blieben, lagen dort, wo das Ersatzstück
saß: im Fenster und im Speicher. **Was ein Ersatzstück ersetzt, misst es nicht.**

