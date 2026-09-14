---
title: CI/CD und Auslieferung — Design / Spezifikation
description: Prüfschranken auf jedem PR, gebaute Erzeugnisse aus der Werkbank statt vom Entwicklerrechner, und eine Fassung, die nur über master erscheint.
audience: developer
status: proposed
updated: 2026-09-14
---

# CI/CD und Auslieferung — Design / Spezifikation

**Datum:** 2026-09-14
**Status:** entworfen, in Umsetzung

> **Fortgeschrieben am 14.09.2026, noch am Tag der Niederschrift.** Zwischen Entwurf und
> Umsetzung ist `669424c` auf `develop` gelandet (GPL-3.0-or-later, `docs/publishing/`,
> `docs/licensing/`, `fastlane/metadata/`), und die Umsetzung von §5.1 hat eine Lücke im
> eigenen Entwurf gezeigt. Geändert haben sich dadurch **§2.1(c)**, **§5.1**, **§5.2**,
> **§5.3**, **§7**, **§8** und **§9**.
>
> Die überholten Absätze sind **durchgestrichen stehengeblieben, nicht gelöscht**. Ein
> Entwurf, aus dem der Irrtum entfernt wurde, liest sich, als sei er nie einer gewesen —
> und die nächste Person trifft dieselbe Entscheidung noch einmal.
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
Fehlt der Schlüsselspeicher, wird einer **erzeugt**. Auf dem Entwickler-
rechner ist das die richtige Entscheidung (einmal anlegen, nie wieder). In der Werkbank ist
es eine Falle: Wäre das Geheimnis nicht gesetzt oder landete es am falschen Ort, würde jede
Fassung mit einem **anderen** Schlüssel signiert. Android verweigert dann jede
Aktualisierung (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`), und der Bau bliebe grün — im
Protokoll stünde eine Zeile „Angelegt:" und sonst nichts.

→ Das ist der gefährlichste Einzelbefund dieses Entwurfs und wird zuerst behoben (§5.1).

**(c) ~~Es gibt keine `LICENSE`.~~ — überholt am 14.09.2026, noch am selben Tag.**

Dieser Absatz stand hier: es gebe keine Lizenz, `package.json` sage `UNLICENSED`, und das
schließe den offiziellen f-droid.org-Bestand hart aus. **Beides stimmt nicht mehr.** Commit
`669424c` hat das Projekt unter **GPL-3.0-or-later** gestellt, und `docs/licensing/`
weist nach, dass alle fünf Fremdbestandteile damit verträglich sind — die Montserrat unter
der SIL OFL eingeschlossen.

Er bleibt sichtbar statt gelöscht, weil er sonst nur einen halben Tag lang wahr war und
niemand mehr wüsste, warum §7 sich für den *eigenen* Bestand entschieden hat. Der Grund
war damals die Lizenz **und** das vorgebaute OpenCV-SDK; heute ist es nur noch das SDK.
Was der offizielle Weg jetzt wirklich kostet, hat der Eigentümer in
[`docs/publishing/f-droid.md`](../../publishing/f-droid.md) nachgerechnet — die Entscheidung
für den eigenen Bestand bleibt davon unberührt, denn sie hängt nicht mehr an einer Sperre,
sondern daran, dass Android-Benutzer *jetzt* Aktualisierungen bekommen sollen.

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
  index.html        Landeseite mit Bestandsadresse und QR-Code

fastlane/metadata/android/    liegt schon da (669424c) -- NICHT verdoppeln
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
| `build-android` | `windows-latest` | `dev.ps1 build-android-libs`, `build-apk-release`, `check-apk-release` |
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

**Die beiden sind gekoppelt, und zwar nachträglich.** Dieser Abschnitt beschrieb sie zuerst
als unabhängig; die Umsetzung hat gezeigt, dass das die Falle nur verschiebt. Wer
`ARUCO_SIGNING_DIR` setzt und den zweiten Schalter vergisst — eine Zeile in einer Datei, die
beim Schreiben dieses Satzes noch niemand geschrieben hatte —, bekommt genau den stillen
Schlüsselwechsel aus §2.1(b), nur an einem anderen Ort.

Dass ihn niemand bemerkt hätte, ist der eigentliche Punkt: ein erfundener Schlüssel entsteht
mit `CN=Bischof Snowboards, O=Bischof Snowboards, C=DE` — **Zeichen für Zeichen die DN des
echten Zertifikats** —, und die einzige Signaturprüfung, die es damals gab, sucht nach
`CN=Android Debug`. Sie hätte ihn durchgewinkt.

Deshalb greift der Riegel jetzt, sobald **einer von beiden** gesetzt ist: ein Ablageort, der
nicht der vorgegebene ist, ist per Definition nicht der Ort, an dem einmalig ein Schlüssel
entsteht. Der Entwicklerrechner merkt davon nichts — dort ist keiner der beiden gesetzt.

### 5.2 Der Fingerabdruck — nachsehen, WOMIT signiert wurde

**Kein eigener Befehl.** Eine frühere Fassung dieses Abschnitts verlangte ein
`check-release-key`; die Prüfung gehört aber dorthin, wo `apksigner verify --print-certs`
ohnehin schon läuft und wo schon eine Aussage über den Schlüssel getroffen wird — in
`Invoke-CheckApk`. Ein zweiter Befehl wäre eine zweite Art, dasselbe zu tun.

`check-apk-release` vergleicht den Fingerabdruck aus dem **fertigen APK** mit
`ARUCO_EXPECTED_CERT_SHA256`. Ist die Erwartung nicht gesetzt, wird nur gemeldet: auf dem
Entwicklerrechner gibt es genau einen Schlüssel, und eine von Hand gepflegte Zahl wäre dort
eine Fehlerquelle ohne Gegenwert. Die Werkbank setzt sie.

Der Grund: §5.1 verhindert, dass *kein* Schlüssel da ist. Diese Prüfung verhindert, dass der
*falsche* da ist — und sie prüft das Erzeugnis, nicht die Absicht. Genau die Unterscheidung,
auf der `check-apk` schon besteht.

### 5.3 ~~`build-aab-release`~~ — entfällt

Hier stand, die Werkbank solle ein Play-Bündel als Probe bauen, „für den Tag, an dem eine
Play Console existiert". **Dieser Tag ist abgesagt.** `docs/publishing/README.md` §4
begründet, warum Google Play nicht verfolgt wird — die API-Frist vom 31.08.2026 ist
abgelaufen, GPLv3 und die Play-Bedingungen reiben sich, und ein AAB wäre ein zweites
Erzeugnis, das niemand mitmisst. `build-aab` hat es kurz gegeben und ist in `c635af5`
wieder entfernt worden.

Ein Entwurf, der einen Befehl wieder einbaut, den der Eigentümer begründet entfernt hat,
ist kein Entwurf, sondern ein Rückschritt mit Datum. Der Abschnitt bleibt als Grabstein
stehen, damit niemand ihn in einem halben Jahr aus der Historie „wiederherstellt".

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
auseinanderläuft. Versioniert ist nur, was Quelle ist: `fdroid/config.yml`.

**Die Metadaten liegen schon da und werden nicht zweimal geschrieben.** `669424c` hat
`fastlane/metadata/android/{de-DE,en-US}/` angelegt — Titel, Kurz- und Langbeschreibung,
und `changelogs/107.txt` für den `versionCode` 107, den `Get-AndroidVersionCode` aus
`0.1.7` ableitet. `fdroid update` liest dieses Format von sich aus. Ein eigener
`fdroid/metadata/…yml` wäre dieselbe Aussage ein zweites Mal, in einer zweiten Sprache,
an einer zweiten Stelle — und die beiden liefen auseinander, sobald jemand nur eine
davon anfasst.

Als Lizenz steht dort **`GPL-3.0-or-later`**, und `AntiFeatures` bleibt **leer**:
`docs/licensing/third-party.md` weist für alle fünf Fremdbestandteile die Verträglichkeit
nach, die Montserrat unter der SIL OFL eingeschlossen. `NonFreeAssets` wäre eine falsche
Angabe in einem Laden — und die ist schlechter als gar keine.

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

**Play Store.** Nicht „noch nicht" — **gar nicht**. Die Begründung steht nicht hier, sondern
in [`docs/publishing/README.md`](../../publishing/README.md) §4, und sie ist die
verbindliche: abgelaufene API-Frist, Reibung zwischen GPLv3 und den Play-Bedingungen, und
ein AAB als zweites Erzeugnis ohne eigene Messung. Dieser Entwurf hat in einer früheren
Fassung das Gegenteil vorbereitet; dass er es nicht mehr tut, ist keine Auslassung.

**Offizielles F-Droid.** Seit dem 14.09.2026 fehlt dafür nur noch **eine** Sache, nicht
mehr drei: die Lizenz ist da (GPL-3.0-or-later), die Fastlane-Metadaten sind da, jede
Fassung trägt ein Git-Tag. Übrig bleibt das vorgebaute **OpenCV-Android-SDK** — F-Droid
baut selbst und nimmt vorgefertigte Binärdateien nur aus Quellen, denen es traut.

Der Eigentümer hat die zwei Auswege in
[`docs/publishing/f-droid.md`](../../publishing/f-droid.md) nachgerechnet; Weg A
(`org.opencv:opencv:5.0.0.1` von Maven Central über `prefab`) kostet rund 25 MB im Paket.
**Das ist ein Umbau am Bau, keine CI-Frage**, und deshalb nicht Gegenstand dieses Entwurfs.
Der eigene Bestand aus §7 bleibt davon unberührt und liefe danach weiter.

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

1. **`dev.ps1`:** `ARUCO_SIGNING_DIR` und `ARUCO_REQUIRE_EXISTING_KEY` (gekoppelt, §5.1),
   dann der Fingerabdruck in `check-apk-release` (§5.2), dann die Werkzeugketten-Schalter
   `ARUCO_CMAKE` · `ARUCO_NINJA` · `ARUCO_NDK_VERSION` (§5.4). Örtlich geprüft.
   — *Behebt zuerst die Falle aus §2.1(b).*
2. **`tools/release_notes.py`:** Fassung und Changelog-Abschnitt lesen, mit Tests.
3. **`.github/actions/`:** die beiden Werkzeugketten-Aktionen.
4. **`ci.yml`:** die drei Prüfaufgaben. Erst wenn sie grün sind, werden sie als Schranke
   eingetragen (§6).
5. **`build.yml`:** die gemeinsame Baubeschreibung, von Hand auslösbar.
6. **`release.yml`:** Marke, Fassung, Changelog-Beschreibung.
7. **F-Droid:** `fdroid/config.yml`, Bestandsschlüssel, Pages — die Metadaten liegen
   schon unter `fastlane/metadata/` und werden **nicht** zweimal geschrieben (§7).
8. **`nightly.yml`**, **`codeql.yml`**, **`dependabot.yml`**.
9. **Dokumentation:** `docs/publishing/releasing.md` — dort, wo die Auslieferung schon
   beschrieben ist, nicht daneben —, ein Abschnitt in der `README.md`, Verweis aus
   `AGENTS.md`.

Geheimnisse, die dafür am Repository hinterlegt werden müssen:

| Name | Woher |
|---|---|
| `ANDROID_KEYSTORE_P12_BASE64` | `_toolchain/aruco-signing/aruco-release.p12` |
| `ANDROID_KEYSTORE_PASSWORD` | `_toolchain/aruco-signing/aruco-release.pass` |
| `FDROID_REPO_KEYSTORE_BASE64` | einmal zu erzeugen |
| `FDROID_REPO_KEYSTORE_PASSWORD` | einmal zu erzeugen |
| Variable `ANDROID_CERT_SHA256` | Fingerabdruck des bestehenden Schlüssels (§5.2) |
