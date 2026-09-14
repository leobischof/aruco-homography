---
title: Der Weg zu F-Droid
description: Die eine echte Sperre (OpenCV als heruntergeladenes SDK), die zwei Auswege mit ihren gemessenen Kosten, und die Metadatendatei im Entwurf.
audience: developer
status: draft
updated: 2026-09-14
---

# Der Weg zu F-Droid

> **Nichts hiervon ist ausprobiert.** Es ist eine Recherche, keine Messung. Wo unten eine
> Zahl steht, ist sie aus dem echten Paket gelesen — wo ein Bau beschrieben ist, ist er
> **nicht gelaufen**. Diese Unterscheidung ist in diesem Repo die wichtigste, und sie gilt
> hier genauso wie bei Millimetern.

---

## 1 · Die Sperre

F-Droid baut **selbst**, aus dem Quelltext, auf einem eigenen Bauserver — und nimmt
vorgefertigte Binärdateien nur aus wenigen Quellen, denen es traut:
Debians Paketarchiv, **Maven-Repositorien** (Maven Central, Google Maven, Sonatype,
JitPack), das Android-SDK und -NDK, PyPI-Wheels, die Compiler von Rust, Go und Node.js.

Dieses Projekt baut `libaruco_core.so` gegen ein **heruntergeladenes OpenCV-Android-SDK**
in `../_toolchain/opencv-android/`. Das ist keine dieser Quellen. So wie der Bau heute
steht, kann F-Droid ihn nicht nachvollziehen.

Alles andere ist in Ordnung: freie Lizenz seit dem 14.09.2026, keine Netzberechtigung,
keine Google-Play-Dienste, kein Firebase, kein Crashlytics, keine Werbe- oder
Zählbibliothek, eindeutige Anwendungskennung, und für jede Veröffentlichung ein Git-Tag.

## 2 · Zwei Auswege — und was sie kosten

### Weg A · OpenCV aus Maven Central, über `prefab`

Seit 4.9.0 liegt OpenCV auf Maven Central, und **die Fassung, die dieses Projekt braucht,
ist dort**: `org.opencv:opencv:5.0.0.1`. Maven Central steht auf F-Droids Liste. Damit
wäre die Sperre weg, ohne dass jemand OpenCV baut.

**Nachgesehen, nicht vermutet** — der Inhalt des AAR, aus der Zentralverzeichnis­tabelle
des Pakets gelesen (14.09.2026):

| | |
|---|---|
| prefab-Module | **genau eines**: `opencv_java5` |
| Kopfdateien | vollständig, `opencv2/geometry/` und `geometry.hpp` **sind dabei** |
| Bibliothek je ABI | `libopencv_java5.so` — **33,38 MB** |
| dazu | `libc++_shared.so` — 1,29 MB |

Die zweite Zeile ist die gute Nachricht: `core/CMakeLists.txt` verlangt
`core geometry imgproc objdetect`, und `geometry` ist in OpenCV 5 ein eigenes Modul. Es
ist im AAR vorhanden. Der Umbau scheitert nicht an einem fehlenden Kopf.

Die dritte Zeile ist der Preis. **Das AAR liefert eine einzige, vollständige gemeinsame
Bibliothek, keine vier statischen Modulbibliotheken.** Heute bindet `libaruco_core.so`
genau die vier Module statisch ein und wiegt damit rund 6 MB; das Release-APK wiegt
**9,87 MB**. Über das AAR schrumpft `libaruco_core.so` auf ein paar hundert Kilobyte,
aber daneben müssen 33,38 + 1,29 MB ins Paket — **und zwar unkomprimiert**, weil
`android/app/build.gradle.kts` `useLegacyPackaging = false` setzt, damit der Linker die
`.so` direkt aus dem APK abbilden kann.

> **Aus 9,9 MB werden geschätzt rund 38 MB je ABI.** Mitgeschleppt werden dann `dnn`,
> `videoio`, `stitching`, `photo`, `ptcloud`, `flann`, `features` und `highgui` — alles,
> was dieses Projekt nie anfasst.

### Weg B · OpenCV im Bauserver aus Quellen bauen

F-Droids Metadatenformat kennt `srclibs`: eine zweite Quelle, die vor dem eigentlichen Bau
ausgecheckt und gebaut wird. Damit bliebe alles, wie es ist — statisch gebunden, vier
Module, 9,87 MB — und das ausgelieferte APK wäre **dasselbe Erzeugnis, das hier gemessen
wurde**.

Der Preis ist Bauzeit und Geduld des Prüfers. Mildern lässt er sich erheblich, weil dieses
Projekt so wenig braucht:

```
-DBUILD_LIST=core,geometry,imgproc,objdetect
-DBUILD_SHARED_LIBS=OFF -DBUILD_TESTS=OFF -DBUILD_PERF_TESTS=OFF
-DBUILD_EXAMPLES=OFF -DBUILD_ANDROID_PROJECTS=OFF -DWITH_PROTOBUF=OFF
```

Vier Module statt dreißig ist der Unterschied zwischen einer knappen Stunde und einem
halben Tag.

### Welcher Weg

**Für die Aufnahme: A. Für das Erzeugnis: B.**

Weg A ist bei der Prüfung fast sicher unstrittig — eine Maven-Abhängigkeit, mehr nicht —
und er räumt nebenbei 15 GB Werkzeugkette neben dem Repo weg. Weg B liefert das kleinere
und ehrlichere Paket und lässt die bereits gemessene Bitgleichheit auf dem Telefon
bestehen; ein Umbau auf A macht jede Messung von `libaruco_core.so` neu fällig, also auch
den Prüfstandslauf vom 08.09.2026.

Wer es sich leicht machen will, nimmt A und **misst danach auf dem Gerät nach** — der
Knopf dafür ist schon da.

## 3 · Die zwei kleineren Prüfrisiken

**`web/vendor/core/aruco_core.wasm`, 3,64 MB, ist eingecheckt.** Ein Prüfer, der nach
Binärdateien sucht, findet genau diese eine (die andere ist `gradle-wrapper.jar`, und die
ersetzt F-Droid ohnehin durch seine eigene). Zwei Dinge entschärfen sie, und beide
stimmen: sie liegt **nicht im APK** — `./dev.ps1 check-apk` verbietet sie dort
ausdrücklich über die Liste `$AndroidPayloadForbidden` — und sie entsteht aus `core/` in diesem Repo, ist
also kein fremdes Blob. Sauberer wäre trotzdem, sie zu bauen statt einzuchecken. Das ist
eine eigene Aufgabe, keine für den Aufnahmeantrag.

**`pdf-lib` wird als fertiges Bündel mitgeliefert.** `android/app/build.gradle.kts` kopiert
`node_modules/pdf-lib/dist/pdf-lib.esm.min.js` ins APK. Das ist vorgefertigtes,
minifiziertes JavaScript aus der npm-Registry. F-Droids Regel dazu lautet, dass
Vorgefertigtes „über die Metadaten oder von einer seriösen dritten Stelle" gebaut sein
muss — npm ist so eine Stelle, aber minifiziertes JavaScript ist der Fall, bei dem
Prüfer nachfragen. Der Ausweg, falls gefragt wird: `pdf-lib` als `srclib` eintragen und
im `prebuild` aus seinem Quelltext bauen.

## 4 · Die Metadatendatei — Entwurf

Kommt **nicht** in dieses Repo, sondern als
`metadata/com.bischofsnowboards.aruco.yml` in eine Abzweigung von
[fdroiddata](https://gitlab.com/fdroid/fdroiddata/). Hier steht sie, damit sie nicht
zweimal erfunden wird. **Der `Builds`-Block zeigt Weg B** und ist der ungeprüfte Teil.

```yaml
Categories:
  - Science & Education
License: GPL-3.0-or-later
AuthorName: Leo Bischof
SourceCode: https://github.com/leobischof/aruco-homography
IssueTracker: https://github.com/leobischof/aruco-homography/issues
Changelog: https://github.com/leobischof/aruco-homography/blob/master/CHANGELOG.md

RepoType: git
Repo: https://github.com/leobischof/aruco-homography.git

Builds:
  - versionName: 0.1.7-alpha
    versionCode: 107
    commit: v0.1.7-alpha
    subdir: android/app
    sudo:
      - apt-get update
      - apt-get install -y cmake ninja-build nodejs npm
    init:
      - npm ci
    gradle:
      - yes
    srclibs:
      - opencv@5.0.0
    ndk: r27c
    prebuild:
      - pushd $$opencv$$ && mkdir -p build-android && cd build-android &&
        cmake -G Ninja ..
        -DCMAKE_TOOLCHAIN_FILE=$$NDK$$/build/cmake/android.toolchain.cmake
        -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-24
        -DBUILD_LIST=core,geometry,imgproc,objdetect
        -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTS=OFF -DBUILD_PERF_TESTS=OFF
        -DBUILD_EXAMPLES=OFF -DBUILD_ANDROID_PROJECTS=OFF
        -DCMAKE_INSTALL_PREFIX=../install && ninja install && popd
      # dann libaruco_core.so aus core/ gegen ../install bauen
    ndkstatic: true

AutoUpdateMode: None
UpdateCheckMode: Tags ^v[0-9.]+-alpha$
CurrentVersion: 0.1.7-alpha
CurrentVersionCode: 107
```

Offene Punkte in genau diesem Entwurf, damit sie niemand übersieht:

- **`versionCode: 107` stimmt** — nachgerechnet, nicht geraten: `Get-AndroidVersionCode`
  in `dev.ps1` bildet `major * 10000 + minor * 100 + patch`, also `0.1.7-alpha` → `107`.
  Bei jeder neuen Fassung wird sie dort abgelesen und nicht hier fortgeschrieben.
- **`prebuild` ist eine Skizze.** Der zweite Teil — `core/` gegen das gebaute OpenCV
  übersetzen und die `.so` nach `android/app/src/main/jniLibs/<abi>/` legen — ist der
  Teil, den heute `./dev.ps1 build-core-android` tut. Er muss in Shell übersetzt werden,
  ohne PowerShell.
- **`Categories`** ist zu prüfen; F-Droids Liste ist fest, und „Science & Education" ist
  eine Vermutung.

## 5 · Store-Texte im Repo

F-Droid liest sie aus **diesem** Repo. Sie liegen deshalb schon hier:

```
fastlane/metadata/android/en-US/     short_description.txt · full_description.txt · changelogs/
fastlane/metadata/android/de-DE/     dasselbe auf Deutsch
```

Was dort noch **fehlt** und nur von Hand entstehen kann:

```
fastlane/metadata/android/en-US/images/icon.png                 512 × 512
fastlane/metadata/android/en-US/images/phoneScreenshots/1.png   …und 2, 3, 4
```

Vier Bildschirmfotos vom Telefon, das die App ohnehin schon gefahren hat. Das Symbol liegt
in `android/app/src/main/res/mipmap-xxxhdpi/` und muss nur auf 512 × 512 gebracht werden.

## 6 · Der Ablauf, wenn der Bau steht

1. [fdroiddata](https://gitlab.com/fdroid/fdroiddata/) abzweigen, Zweig
   `com.bischofsnowboards.aruco`.
2. Die Datei aus §4 einlegen, Commit-Nachricht `New App: com.bischofsnowboards.aruco`.
3. **Vor dem Antrag selbst bauen:** `fdroid build com.bischofsnowboards.aruco` in
   F-Droids Docker-Bauumgebung. Ein Antrag, dessen Bau beim Prüfer scheitert, kostet eine
   Runde von mehreren Wochen.
4. Merge Request aufmachen, auf Rückfragen zügig antworten.
5. Nach dem Zusammenführen dauert es 24 bis 48 Stunden bis zum Erscheinen.

**Signatur:** F-Droid baut selbst und signiert mit **seinem** Schlüssel. Das APK aus
F-Droid und das von `./dev.ps1 build-apk-release` lassen sich dann nicht gegenseitig
aktualisieren — verschiedene Signaturen, `INSTALL_FAILED_UPDATE_INCOMPATIBLE`, derselbe
Stolperstein wie zwischen Debug- und Release-Bau. Wer das vermeiden will, beantragt
[Reproducible Builds](https://f-droid.org/docs/Reproducible_Builds/): F-Droid baut,
vergleicht mit dem hier signierten APK und liefert bei Bitgleichheit **das eigene**
Erzeugnis aus. Das ist die schönere Lösung und die schwerere — sie kommt später, nicht
zur Aufnahme.
