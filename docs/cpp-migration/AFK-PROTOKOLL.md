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
