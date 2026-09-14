---
title: Auslieferung an die App-Läden
description: Was zwischen dem heutigen APK und einem Eintrag bei F-Droid oder Google Play noch liegt, mit den beiden Sperren zuerst.
audience: developer
status: draft
updated: 2026-09-14
---

# Auslieferung an die App-Läden

> **Stand 14.09.2026: das APK ist fertig und beide Wege sind versperrt** — jeder durch
> genau eine Sache, und es ist nicht dieselbe. Beide sind lösbar. Keine ist gelöst.

| Weg | Sperre | Datei |
|---|---|---|
| **F-Droid** | OpenCV kommt aus einem **heruntergeladenen SDK**. F-Droid baut nur aus Quellen oder aus Paketquellen, denen es traut. | [`f-droid.md`](f-droid.md) |
| **Google Play** | `targetSdk = 35`. Play verlangt seit dem **31.08.2026** für neue Apps **API 36**. Die Frist ist vorbei. | [`google-play.md`](google-play.md) |

Dazu, für beide: [`privacy-policy.md`](privacy-policy.md) — Play verlangt eine
Datenschutzerklärung unter einer öffentlichen Adresse, F-Droid zeigt gerne eine an. Sie
ist in diesem Fall angenehm kurz, und zwar nicht aus Nachlässigkeit: die App hat **keine
Netzberechtigung**.

---

## 1 · Was heute schon steht

Nichts davon muss für die Läden neu gemacht werden.

| | Stand |
|---|---|
| Release-APK mit eigenem Schlüssel | **fertig** — `./dev.ps1 build-apk-release`, `CN=Bischof Snowboards`, 9,87 MB, arm64-v8a |
| Schlüssel liegt außerhalb des Repos | **ja** — `../_toolchain/aruco-signing/`, Kennwort über die Umgebung |
| Anwendungskennung | `com.bischofsnowboards.aruco` — frei, eindeutig, für beide Läden brauchbar |
| Fassung kommt aus einer Quelle | **ja** — `app/config.py` → `dev.ps1` → Gradle. Nichts abgetippt |
| Freie Lizenz | **ja**, seit heute — GPL-3.0-or-later, siehe [`../licensing/README.md`](../licensing/README.md) |
| Keine Netzberechtigung, keine Tracker, keine Werbung | **ja** — steht im `AndroidManifest.xml` und ist dort auch begründet |
| Prüfstand läuft auf dem Gerät | **ja** — auf einem Xiaomi 2312DRA50G am 08.09.2026 bestanden |

Der letzte Punkt ist der, der bei F-Droid ungewöhnlich gut aussieht: die App bringt ihren
eigenen Nachweis mit und ein Prüfer kann ihn drücken.

## 2 · Was beide Läden zusätzlich wollen

Für keinen der beiden Wege vorhanden, für beide gebraucht:

- **Store-Texte und Bilder.** Kurzbeschreibung, Langbeschreibung, Symbol, Bildschirmfotos.
  F-Droid liest sie **aus diesem Repo** (`fastlane/metadata/android/…`), Play will sie in
  der Konsole. Einmal schreiben, zweimal benutzen — deshalb liegen sie im Repo.
- **Eine Entscheidung über die Fassungsnummer.** `0.1.7-alpha` ist ehrlich und für einen
  Laden ein Problem: Play zeigt den `versionName` an, und „alpha" neben einem Werkzeug,
  mit dem Leute sägen, liest sich als Warnung. Das ist sie auch — die Frage ist, ob sie
  im Ladennamen stehen soll oder im Beschreibungstext, wo Platz für den ganzen Satz ist.

**Git-Tags gibt es schon** — elf, von `v0.0.1-alpha` bis `v0.1.7-alpha`. F-Droid baut aus
einem Tag und nicht aus `master`; der Weg ist also offen, und die Zeile in der
Metadatendatei kann `v0.1.7-alpha` heißen, ohne dass vorher etwas nachgeholt werden muss.

## 3 · Die Reihenfolge, die ich empfehlen würde

**F-Droid zuerst, Play danach**, und nicht aus Ideologie:

1. F-Droid passt zu diesem Projekt (frei, kein Netz, keine Tracker, nachprüfbarer Bau).
   Die Aufnahme ist kostenlos und dauert Wochen, nicht Tage — je früher angefangen, desto
   besser.
2. Der OpenCV-Umbau, den F-Droid erzwingt, ist **ohnehin die bessere Bauweise**: eine
   Abhängigkeit aus Maven statt eines 15-GB-SDK neben dem Repo. Wer ihn für F-Droid macht,
   macht ihn für alle Ziele.
3. Play kostet 25 USD einmalig, verlangt eine Identitätsprüfung und für ein **privates**
   Konto zusätzlich einen geschlossenen Test mit 12 Testern über 14 zusammenhängende
   Tage, bevor überhaupt veröffentlicht werden darf. Ein **Organisationskonto** auf
   Bischof Snowboards umgeht das — dafür braucht es eine D-U-N-S-Nummer. Die Entscheidung
   steht in [`google-play.md`](google-play.md) und sie ist die erste, die fällt, weil sie
   Wochen kostet oder spart.

**Nicht warten** muss man mit: Store-Texte schreiben und `targetSdk` auf 36 heben. Beides
blockiert nichts und beides ist schnell.
