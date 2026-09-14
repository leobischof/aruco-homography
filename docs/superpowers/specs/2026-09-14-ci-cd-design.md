---
title: CI/CD und Auslieferung — Design / Spezifikation
description: Prüfschranken auf jedem PR, gebaute Erzeugnisse aus der Werkbank statt vom Entwicklerrechner, und eine Fassung, die nur über master erscheint.
audience: developer
status: proposed
updated: 2026-09-14
---

# CI/CD und Auslieferung — Design / Spezifikation

**Datum:** 2026-09-14
**Status:** entworfen, noch nicht umgesetzt
**Betrifft:** `.github/`, `dev.ps1`, `docs/contributing/`, `README.md`

---

## 1 · Zweck

Heute entsteht jede Fassung von Hand auf **einem** Rechner: `build-exe`, `build-installer`,
`build-apk-release`, `build-web`, dann `gh release create` mit vier Anhängen. Das hat drei
Eigenschaften, die keine Absicht sind:

1. **Die Auslieferung hängt an einem Rechner.** Was ausgeliefert wird, hat niemand außer
   diesem einen Arbeitsplatz je gebaut. Ein Bau, den nur eine Maschine kann, ist ein Bau,
   dessen Voraussetzungen niemand aufgeschrieben hat.
2. **Es gibt keine Schranke.** `master` und `develop` sind geschützt (kein direkter Push,
   nur Squash, lineare Historie) — aber **kein** Pull Request muss grün sein, um gemergt zu
   werden. Die Regel „`.\dev.ps1 run-tests` ist grün, bevor committet wird" ist heute eine
   Selbstverpflichtung und keine Schranke.
3. **Android bekommt nur, wer eine Datei herunterlädt.** Es gibt keinen Weg, auf dem ein
   Telefon eine Aktualisierung von selbst bemerkt.

Dieses Dokument beschreibt, was das ersetzt.

**Erfolgskriterium.** Ein Push nach `master` erzeugt ohne weiteres Zutun: eine Marke, eine
GitHub-Fassung mit Installer · APK · Browser-Bau, und einen aktualisierten F-Droid-Bestand,
den ein Telefon von selbst findet. Ein Pull Request, dessen Tests rot sind, lässt sich nicht
mergen.

---

## 2 · Was der Bestand schon hergibt

Die Erhebung, auf der dieser Entwurf steht — nachgesehen am 2026-09-14:

| Befund | Folge für diesen Entwurf |
|---|---|
| Das Repository ist **öffentlich**. | GitHub-Läufer sind kostenlos und unbegrenzt. Windows-Läufer kosten nichts extra — das übliche Argument gegen sie entfällt. |
| `master` und `develop` sind geschützt: kein direkter Push, `enforce_admins`, nur Squash, lineare Historie, 0 Freigaben. | „Eine Fassung nur über `master`" ist **bereits** baulich wahr. Neu ist allein die **Prüfschranke** (`required_status_checks`), die heute `null` ist. |
| OpenCV 5.0.0 liefert fertige **Windows-** und **Android-SDKs** als Anhänge seiner GitHub-Fassung. | Kein Übersetzen von OpenCV in der Werkbank. Herunterladen und zwischenlagern. |
| `web/vendor/core/aruco_core.wasm` ist **eingecheckt** (`.gitignore` sagt ausdrücklich warum). | Emscripten wird in der Werkbank **nicht** gebraucht. Das spart je Lauf rund eine Stunde. |
| Die Fassung steht genau einmal: `app/config.py: APP_VERSION`. `versionCode` wird abgeleitet (`Get-AndroidVersionCode`), `CHANGELOG.md` trägt den passenden Abschnitt. | Die Werkbank **liest** die Fassung, sie bekommt sie nicht gesagt. Kein zweiter Ort, an dem eine Zahl steht. |

### 2.1 Drei Dinge, die im Weg stehen

**(a) `dev.ps1` ist an Windows gebunden — auch für Android.**
`Invoke-BuildCoreAndroid` ruft `Invoke-CrossCmake`, und das holt sich `cmake` und `ninja`
über `Get-CMakeAndNinja` **aus der Visual-Studio-Installation**. Der Kreuzbau fürs Telefon
braucht also Visual Studio. `AGENTS.md` sagt, `dev.ps1` sei die einzige Quelle für
Projektbefehle; die Werkbank muss also hineinrufen und nicht danebenher eine zweite Fassung
derselben Befehle führen.

→ **Alle Bau-Aufgaben laufen auf `windows-latest`.** Nur die F-Droid-Veröffentlichung läuft
auf Ubuntu, weil `fdroidserver` dort zu Hause ist und dort nichts aus `dev.ps1` gebraucht
wird.

Der Gegenentwurf — `Get-CMakeAndNinja` auf Nicht-Windows auf `cmake`/`ninja` aus dem Pfad
zurückfallen lassen und Android auf Ubuntu bauen — wäre etwa doppelt so schnell und ist
**bewusst verworfen**: er führt einen zweiten Bauweg ein, den auf diesem Rechner niemand je
läuft. Ein Unterschied zwischen dem, was die Werkbank baut, und dem, was der Entwickler
baut, fällt genau dann auf, wenn es teuer ist.

**(b) `Enable-ReleaseSigning` legt stillschweigend einen neuen Schlüssel an.**
`dev.ps1:972` — fehlt der Schlüsselspeicher, wird einer **erzeugt**. Auf dem Entwickler-
rechner ist das die richtige Entscheidung (einmal anlegen, nie wieder). In der Werkbank ist
es eine Falle: Wäre das Geheimnis nicht gesetzt oder landete es am falschen Ort, würde jede
Fassung mit einem **anderen** Schlüssel signiert. Android verweigert dann jede
Aktualisierung (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`), und der Bau bliebe grün — im
Protokoll stünde eine Zeile „Angelegt:" und sonst nichts.

→ Das ist der gefährlichste Einzelbefund dieses Entwurfs und wird zuerst behoben (§5.1).

**(c) Es gibt keine `LICENSE`.** `package.json` sagt `UNLICENSED`. Für einen **eigenen**
F-Droid-Bestand ist das gleichgültig — genau deshalb ist er der richtige Weg. Für den
offiziellen f-droid.org-Bestand ist es ein harter Ausschluss, neben dem vorgebauten
OpenCV-SDK. Beides ist **nicht** Gegenstand dieses Entwurfs, aber §8 hält fest, was dafür
nachzuholen wäre.

---

## 3 · Aufbau

```
.github/
  workflows/
    ci.yml          PR -> develop|master, Push -> develop   Prüfschranke
    build.yml       workflow_call                            die EINE Baubeschreibung
    release.yml     Push -> master                           Marke, Fassung, F-Droid
    nightly.yml     Zeitplan + von Hand                      rollender Vorabstand
    codeql.yml      PR + Zeitplan                            Python und JavaScript
  actions/
    setup-windows-toolchain/     venv · npm ci · OpenCV-Windows-SDK · Inno Setup
    setup-android-toolchain/     JDK · Android-SDK+NDK · OpenCV-Android-SDK · Schlüssel
  dependabot.yml    pip · npm · gradle · github-actions
fdroid/
  config.yml        Vorlage; der Schlüssel kommt aus dem Geheimnis
  metadata/com.bischofsnowboards.aruco.yml
```

**`build.yml` ist der Grund für den Zuschnitt.** Drei Anlässe wollen dasselbe bauen
(Fassung, Nachtbau, Handstart). Die Bauschritte stehen deshalb **einmal** in einem
`workflow_call`-Ablauf, und die anderen rufen ihn. Dieselbe Regel, die im Repo für
`dev.ps1` gilt: eine Sache, ein Ort.

Die zwei zusammengesetzten Aktionen unter `.github/actions/` gibt es aus demselben Grund
eine Ebene tiefer: das Herrichten der Werkzeugkette ist in `ci.yml`, `build.yml` und
`nightly.yml` dasselbe und wird nicht dreimal getippt.

### 3.1 Die Aufgaben und was sie rufen

| Aufgabe | Läufer | Ruft |
|---|---|---|
| `test-python` | `windows-latest` | `dev.ps1 run-tests` |
| `test-cpp` | `windows-latest` | `dev.ps1 build-core`, `dev.ps1 run-tests-cpp`, `dev.ps1 check-jni` |
| `test-js` | `windows-latest` | `dev.ps1 run-tests-js`, `dev.ps1 run-tests-pdf-js` |
| `build-windows` | `windows-latest` | `dev.ps1 build-exe`, `build-installer`, `build-web` |
| `build-android` | `windows-latest` | `dev.ps1 build-android-libs`, `build-apk-release`, `check-apk-release`, `build-aab-release` |
| `release` | `ubuntu-latest` | `gh release create` |
| `fdroid` | `ubuntu-latest` | `fdroid update`, `actions/deploy-pages` |

`test-python`, `test-cpp` und `test-js` sind die **Prüfschranken** (§6). Sie laufen
nebeneinander; `build-windows` und `build-android` ebenfalls.

---

## 4 · Der Weg einer Fassung

Auslöser: **ein Push nach `master`**. Weil `master` nur Release-PRs bekommt
(`docs/contributing/git.md` §7), ist ein Push nach `master` gleichbedeutend mit „eine
Fassung soll erscheinen". Die Werkbank verlässt sich darauf aber **nicht** — sie prüft:

1. **Fassung lesen.** `APP_VERSION` aus `app/config.py`. Nicht aus der Marke, nicht aus dem
   PR-Titel, nicht aus einer Eingabe.
2. **Abbrechen, wenn `v<Fassung>` schon als Marke existiert.** Das macht den Ablauf
   *idempotent*: ein Push nach `master`, der die Fassung nicht erhöht hat (eine Korrektur an
   der README etwa), tut nichts und meldet das, statt eine zweite Fassung unter derselben
   Nummer zu erzeugen.
3. **Abbrechen, wenn `CHANGELOG.md` keinen Abschnitt für diese Fassung hat.** Der Abschnitt
   IST die Beschreibung der Fassung (Schritt 6). Fehlt er, fehlt sie — und eine Fassung ohne
   Beschreibung wird hier nicht ausgeliefert.
4. **Bauen**, `build-windows` und `build-android` nebeneinander.
5. **Marke setzen und Fassung anlegen.** `v<Fassung>`, Anhänge:
   `ArUco-Homographie-Setup-<Fassung>.exe` · `aruco-homographie-<Fassung>.apk` ·
   `aruco-homographie-web-<Fassung>.zip`.

   **Das Debug-APK entfällt.** Bis 0.1.7-alpha lag es daneben, und es hat genau den
   Schaden angerichtet, für den es gedacht war, ihn zu vermeiden: Wer die Fassungsseite
   sieht, lädt eine der beiden Dateien, und welche das war, weiß danach niemand mehr.
   Der Bau erzeugt es weiterhin (`dev.ps1 build-apk`), aber eine Fassungsseite bietet
   **eine** Datei je Ziel an.
6. **Beschreibung** = der Abschnitt aus `CHANGELOG.md`, Zeichen für Zeichen. Nicht aus der
   Commit-Liste erzeugt: was eine Fassung enthält, sagt der Changelog — so steht es schon in
   `docs/contributing/git.md` §7.
7. **F-Droid-Bestand neu bauen** und nach GitHub Pages ausliefern (§7).

Die Schritte 2 und 3 sind Abbrüche, keine Warnungen. Eine halbe Fassung ist schlimmer als
keine — dieselbe Regel wie beim Raster in 0.1.7-alpha.

### 4.1 Der Nachtbau

`nightly.yml` läuft nach Zeitplan, baut aber **nur, wenn `develop` seit dem letzten
Nachtbau einen neuen Commit hat**. Sonst endet er sofort. Ergebnis ist eine rollende
Vorabfassung (`nightly`), deren Anhänge jedes Mal ersetzt werden — keine wachsende Liste
von Nachtständen.

Der Nachtbau ist ausdrücklich **keine** Pflichtschranke: `develop` darf auch dann weiter
gefüllt werden, wenn er einmal fehlschlägt.

---

## 5 · Änderungen an `dev.ps1`

Die Werkbank definiert **keinen** Projektbefehl selbst. Was sie zusätzlich braucht, kommt
nach `dev.ps1` — und steht damit auch dem Entwicklerrechner zur Verfügung.

### 5.1 Der Schlüssel wird nicht mehr aus Versehen neu erfunden

`Enable-ReleaseSigning` bekommt zwei Umgebungsschalter:

| Schalter | Wirkung |
|---|---|
| `ARUCO_SIGNING_DIR` | Wo der Schlüssel liegt. Vorgabe bleibt `../_toolchain/aruco-signing/`. Die Werkbank legt ihn in den Arbeitsbereich und zeigt hierhin. |
| `ARUCO_REQUIRE_EXISTING_KEY=1` | **Anlegen verboten.** Fehlt der Schlüssel, wird abgebrochen statt erzeugt. |

Die Werkbank setzt beide. Damit ist der stille Schlüsselwechsel aus §2.1(b) unmöglich: ohne
Geheimnis bricht der Bau ab, mit falschem Geheimnis fällt es in Schritt 5.2 auf.

### 5.2 `check-release-key` — nachsehen, womit signiert wurde

Neuer Befehl. Liest den Fingerabdruck des Zertifikats aus dem **fertigen APK** (`apksigner
verify --print-certs`) und vergleicht ihn mit einem erwarteten SHA-256, der als
Repository-Variable steht. Stimmt er nicht, Abbruch.

Der Grund: §5.1 verhindert, dass *kein* Schlüssel da ist. Diese Prüfung verhindert, dass der
*falsche* da ist — und sie prüft das Erzeugnis, nicht die Absicht. Genau die Unterscheidung,
auf der `check-apk` schon besteht.

### 5.3 `build-aab-release`

`bundleRelease` mit demselben Schlüssel und derselben abgeleiteten Fassung wie
`build-apk-release`. Die Werkbank baut das Bündel als **Prüfung** — es wird der Fassung
**nicht** angehängt, weil eine `.aab` sich nicht installieren lässt und auf einer
Fassungsseite nur danebenläge. Am Tag, an dem eine Play Console existiert, ist es eine Zeile
(§8).

### 5.4 `aruco.buildRoot`

`android/gradle.properties` schreibt `aruco.buildRoot=C:/aruco-android-build` fest (gegen
MAX_PATH). Auf einem Windows-Läufer ist das schreibbar, also bleibt es unverändert. Wer den
Android-Bau je nach Ubuntu verschiebt, muss hier vorbeikommen — deshalb steht es hier.

---

## 6 · Die Prüfschranke

Nach dem ersten grünen Lauf werden am Repository für **`develop` und `master`** eingetragen:

```
required_status_checks:
  strict: true
  contexts: [ test-python, test-cpp, test-js ]
```

`strict: true` heißt: der Zweig muss auf dem aktuellen Stand des Ziels sein. Bei einem
Bearbeiter kostet das selten etwas und schließt den Fall aus, dass zwei für sich grüne PRs
zusammen rot ergeben.

Die bestehenden Einstellungen aus `docs/contributing/git.md` §7 bleiben **unangetastet**.
Diese Zeilen kommen dazu, es wird nichts gelockert.

**Was sich für den Ablauf ändert:** nichts an den Befehlen, aber der Merge-Knopf ist
gesperrt, bis die drei Prüfungen durch sind. Das ist der eigentliche Zugewinn — die Regel
„Tests grün vor dem Commit" hört auf, eine Selbstverpflichtung zu sein.

---

## 7 · F-Droid: ein eigener Bestand, ohne zweite Ablage

**Gewählt:** ein eigener F-Droid-Bestand auf GitHub Pages.
**Nicht gewählt:** der offizielle f-droid.org-Bestand — §8.

Der übliche Weg legt jedes APK dauerhaft in einen `gh-pages`-Zweig. Das lässt dieses
Repository um rund 10 MB je Fassung wachsen, für immer, und die Git-Historie gibt den Platz
nie wieder her.

**Stattdessen wird der Bestand bei jedem Lauf neu erzeugt:** die Aufgabe lädt die APKs der
**letzten fünf** GitHub-Fassungen herunter, ruft `fdroid update` und liefert das Ergebnis als
Pages-Artefakt aus. Die GitHub-Fassungen **sind** schon die Antwort auf „welche Fassungen
gibt es" — eine zweite Ablage derselben Aussage wäre genau die zweite Fassung, die
auseinanderläuft. Versioniert ist nur, was Quelle ist: `fdroid/config.yml` und die
Metadaten.

Fünf und nicht alle: F-Droid braucht ältere Stände nur, damit ein Telefon, das lange nicht
nachgesehen hat, überhaupt etwas findet — und dafür genügt die jeweils neueste. Die vier
darunter sind Rückfallmöglichkeit, nicht Archiv. Wer einen älteren Stand sucht, findet ihn
unverändert auf der GitHub-Fassungsseite; die wird von dieser Zahl nicht berührt.

Der Bestandsschlüssel (mit dem der **Index** signiert wird, nicht das APK) wird einmal
erzeugt und liegt als Geheimnis. Er ist so unersetzlich wie der App-Schlüssel: geht er
verloren, muss jeder Benutzer den Bestand neu hinzufügen.

Adresse: `https://leobischof.github.io/aruco-homography/fdroid/repo`
Dazu ein QR-Code und eine kurze Anleitung in der `README.md`.

---

## 8 · Was bewusst nicht gelöst ist

**Play Store.** Nicht verdrahtet. Die erste Einreichung einer App muss von Hand in der Play
Console geschehen; eine Werkbank kann erst ab der zweiten übernehmen. Vorbereitet ist alles:
`build-aab-release` erzeugt das Bündel, und es fehlt nur eine Aufgabe mit
`r0adkll/upload-google-play` und einem Dienstkonto-Geheimnis. Zu bedenken, bevor das ansteht:
Google verlangt ab September 2026 verifizierte Entwickler.

**Offizielles F-Droid.** Braucht drei Dinge, die es heute nicht gibt: eine OSI-Lizenz (es
gibt keine `LICENSE`), einen Bau ohne vorgebaute Binärdateien (das OpenCV-Android-SDK müsste
in ihrer Bauvorschrift aus dem Quelltext entstehen), und eine Prüfung durch F-Droid, die
Wochen dauert. Der eigene Bestand aus §7 bleibt davon unberührt und liefe weiter.

**Signatur der Windows-`.exe`.** Unverändert ungelöst. `AGENTS.md` hält schon fest, dass
ausgefüllte Dateieigenschaften keine Signatur sind und SmartScreen weiterhin keinen
Herausgeber nennt. Ein Zertifikat kostet Geld und ist keine CI-Frage.

**Reproduzierbare Bauten.** Zwei Läufe desselben Commits ergeben heute nicht Byte für Byte
dasselbe APK. Für den eigenen Bestand ist das ohne Belang.

**Der Bau misst weiterhin nicht auf einem Telefon.** `check-apk` zählt Dateien im Paket, und
`run-tests-cpp` fährt den Prüfstand — aber die Kette Foto → Marker → Millimeter bleibt auf
Android unbelegt, genau wie `CLAUDE.md` es beschreibt. **Eine grüne Werkbank ändert daran
nichts** und darf nicht so gelesen werden.

---

## 9 · Reihenfolge der Umsetzung

Jeder Schritt ist für sich lauffähig und wird für sich committet
(`docs/contributing/git.md` §3).

1. **`dev.ps1`:** `ARUCO_SIGNING_DIR`, `ARUCO_REQUIRE_EXISTING_KEY`, `check-release-key`,
   `build-aab-release`. Örtlich geprüft. — *Behebt zuerst die Falle aus §2.1(b).*
2. **`.github/actions/`:** die beiden Werkzeugketten-Aktionen.
3. **`ci.yml`:** die drei Prüfaufgaben. Erst wenn sie grün sind, werden sie als Schranke
   eingetragen (§6).
4. **`build.yml`:** die gemeinsame Baubeschreibung, von Hand auslösbar.
5. **`release.yml`:** Marke, Fassung, Changelog-Beschreibung.
6. **F-Droid:** `fdroid/`-Metadaten, Bestandsschlüssel, Pages.
7. **`nightly.yml`**, **`codeql.yml`**, **`dependabot.yml`**.
8. **Dokumentation:** `docs/contributing/releasing.md`, Abschnitt in der `README.md`,
   Verweis aus `AGENTS.md`.

Geheimnisse, die dafür am Repository hinterlegt werden müssen:

| Name | Woher |
|---|---|
| `ANDROID_KEYSTORE_P12_BASE64` | `_toolchain/aruco-signing/aruco-release.p12` |
| `ANDROID_KEYSTORE_PASSWORD` | `_toolchain/aruco-signing/aruco-release.pass` |
| `FDROID_REPO_KEYSTORE_BASE64` | einmal zu erzeugen |
| `FDROID_REPO_KEYSTORE_PASSWORD` | einmal zu erzeugen |
| Variable `ANDROID_CERT_SHA256` | Fingerabdruck des bestehenden Schlüssels (§5.2) |
