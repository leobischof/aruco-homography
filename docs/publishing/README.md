---
title: Auslieferung an F-Droid
description: Was zwischen dem heutigen APK und einem Eintrag bei F-Droid noch liegt — und warum Google Play bewusst nicht verfolgt wird.
audience: developer
status: draft
updated: 2026-09-14
---

# Auslieferung an F-Droid

> **Stand 14.09.2026: das APK ist fertig, der Weg ist durch genau eine Sache versperrt.**
> OpenCV kommt aus einem heruntergeladenen SDK, und F-Droid baut nur aus Quellen oder aus
> Paketquellen, denen es traut. Lösbar, nicht gelöst.

| | Datei |
|---|---|
| Die Sperre, die zwei Auswege mit ihren gemessenen Kosten, die Metadatendatei | [`f-droid.md`](f-droid.md) |
| Die Datenschutzerklärung, zweisprachig | [`privacy-policy.md`](privacy-policy.md) |

**Google Play wird nicht verfolgt** — die Begründung steht in [§4](#4--google-play-liegt-bewusst-daneben),
damit die Entscheidung nicht in einem Jahr als Versäumnis gelesen wird.

---

## 1 · Was heute schon steht

Nichts davon muss für F-Droid neu gemacht werden.

| | Stand |
|---|---|
| Release-APK mit eigenem Schlüssel | **fertig** — `./dev.ps1 build-apk-release`, `CN=Bischof Snowboards`, 9,87 MB, arm64-v8a |
| Schlüssel liegt außerhalb des Repos | **ja** — `../_toolchain/aruco-signing/`, Kennwort über die Umgebung |
| Anwendungskennung | `com.bischofsnowboards.aruco` — frei und eindeutig |
| Fassung kommt aus einer Quelle | **ja** — `app/config.py` → `dev.ps1` → Gradle. Nichts abgetippt |
| Freie Lizenz | **ja**, seit dem 14.09.2026 — GPL-3.0-or-later, siehe [`../licensing/README.md`](../licensing/README.md) |
| Keine Netzberechtigung, keine Tracker, keine Werbung | **ja** — steht im `AndroidManifest.xml` und ist dort auch begründet |
| Git-Tag je Veröffentlichung | **ja** — elf, von `v0.0.1-alpha` bis `v0.1.7-alpha`. F-Droid baut aus einem Tag, nicht aus `master` |
| Prüfstand läuft auf dem Gerät | **ja** — auf einem Xiaomi 2312DRA50G am 08.09.2026 bestanden |

Der letzte Punkt ist der, der bei F-Droid ungewöhnlich gut aussieht: die App bringt ihren
eigenen Nachweis mit, und ein Prüfer kann ihn drücken.

## 2 · Was noch fehlt

- **Der Bau ohne heruntergeladenes OpenCV-SDK.** Die eigentliche Arbeit; zwei Wege stehen
  in [`f-droid.md`](f-droid.md) §2, beide durchgerechnet.
- **Bilder.** Symbol 512 × 512 und vier Bildschirmfotos vom Telefon. Nur von Hand zu
  machen, und das Telefon hat die App ohnehin schon gefahren.
- **Eine Entscheidung über die Fassungsnummer.** `0.1.7-alpha` ist ehrlich und in einem
  Laden trotzdem heikel: „alpha" neben einem Werkzeug, mit dem Leute sägen, liest sich als
  Warnung. Das ist sie auch — die Frage ist nur, ob sie in der Fassungsnummer stehen soll
  oder im Beschreibungstext, wo Platz für den ganzen Satz ist.

Die Store-Texte sind da: `fastlane/metadata/android/` auf Deutsch und Englisch, dort, wo
F-Droid sie aus diesem Repo selbst liest.

## 3 · Reihenfolge

1. OpenCV-Frage entscheiden (Maven-AAR oder Quellbau) und den Bau umstellen.
2. **Auf dem Gerät nachmessen.** Jeder Umbau an `libaruco_core.so` macht den
   Prüfstandslauf vom 08.09.2026 neu fällig — der Knopf dafür ist in der App.
3. Bilder machen.
4. `fdroid build` in F-Droids eigener Bauumgebung, **bevor** der Antrag rausgeht.
5. Merge Request bei fdroiddata.

## 4 · Google Play liegt bewusst daneben

**Nicht vergessen, sondern entschieden** — am 14.09.2026, mit diesen Gründen:

- **Die API-Frist ist bereits abgelaufen.** Seit dem 31.08.2026 nimmt Play neue Apps nur
  noch mit `targetSdk = 36`; diese App steht auf 35. Das Anheben ist nicht die Arbeit —
  das Nachmessen auf einem Gerät ist es, weil `targetSdk` Verhaltensänderungen scharf
  schaltet und dieses Projekt genau daran schon einmal gelitten hat (Rand-zu-Rand,
  08.09.2026).
- **Der Vorlauf ist lang.** 25 USD, Identitätsprüfung, und für ein privates Konto ein
  geschlossener Test mit 12 Testern über 14 ununterbrochene Tage. Für ein
  Werkstattwerkzeug ist das die unangenehmste Auflage von allen.
- **GPLv3 und die Play-Bedingungen reiben sich.** Play untersagt Nutzern das
  Weiterverteilen, die GPL gibt jedem Empfänger genau dieses Recht. In der Praxis stehen
  GPLv3-Apps zu Tausenden bei Play und Google entfernt sie nicht deswegen — aber es ist
  eine Reibung, die es bei F-Droid schlicht nicht gibt.
- **Play will ein AAB, kein APK.** Also ein zweites Erzeugnis, das niemand mitmisst.
  `build-aab` gab es kurz und ist wieder draußen (Commit `c635af5`).

Wenn Play später doch kommt, ist der Weg nicht verloren: er steht in der Historie, und
die Punkte oben sind die Liste, die dann abzuarbeiten wäre.
