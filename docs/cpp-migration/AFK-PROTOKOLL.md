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

#### 2026-09-08 · Was noch unbelegt ist

Der Auftrag lautet „durch Blocker hindurcharbeiten". Damit niemand mehr hineinliest,
als drinsteht:

- **Der Messschieber-Beleg hängt weiter an der Python-Kette.** `100 mm = 100 mm` wurde
  an einem Ausdruck gemessen, den Python erzeugt hat. Der C++-Kern erbt das erst, wenn
  er die ganze Kette fährt.
- **Und auch dieser Beleg deckt nur die halbe Kette:** `PDF → Drucker → Papier`. Der Weg
  `Foto → Marker → Millimeter` ist nach wie vor nur gegen synthetische Szenen belegt.
- **Kein echtes Foto.** Alles bisher Gemessene ist gerechnet.
- **Android: nichts ausgeführt.** Siehe oben.

