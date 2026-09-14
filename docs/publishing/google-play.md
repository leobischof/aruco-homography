---
title: Der Weg zu Google Play
description: Die abgelaufene API-Frist, die Kontoentscheidung, das AAB statt des APK und was Play sonst noch verlangt.
audience: developer
status: draft
updated: 2026-09-14
---

# Der Weg zu Google Play

> **Nichts hiervon ist ausprobiert.** Es gibt kein Play-Konto und keinen hochgeladenen
> Bau. Die Fristen und Regeln unten sind am 14.09.2026 bei Google nachgelesen; alles
> Übrige ist Planung.

---

## 1 · Die Sperre: `targetSdk = 35`

**Seit dem 31.08.2026 nimmt Play neue Apps und Aktualisierungen nur noch mit
`targetSdk = 36`** (Android 16). Diese App steht auf 35. Die Frist ist zwei Wochen her.

Eine Verlängerung bis zum **01.11.2026** lässt sich in der Play Console beantragen, aber
das ist hier unnötiger Aufwand: die Umstellung ist zwei Zeilen.

```kotlin
// android/app/build.gradle.kts
compileSdk = 36
targetSdk  = 36
```

**Zwei Zeilen, aber kein Selbstläufer.** `targetSdk` ist die Zusage an Android, das
Verhalten der neuen Fassung zu vertragen; das Anheben schaltet Verhaltensänderungen
scharf. Für diese App sind die beiden wahrscheinlichen Stolpersteine:

- **Rand-zu-Rand erzwungen.** Ab API 35 zeichnen Apps voll unter Status- und
  Navigationsleiste, ohne Wahl. Dieses Projekt hat genau daran schon einmal gelitten
  (08.09.2026, siehe `docs/cpp-migration/stage-4-android.md`) und es über
  `window.__arucoInsets` behoben. Die vier Zahlen dort sind allerdings **auf einem Gerät
  nie nachgemessen** worden — mit API 36 gehört genau das nachgeholt.
- **Die Kamera-Berechtigung.** Der Weg über `ACTION_IMAGE_CAPTURE` und der über
  `getUserMedia` verhalten sich in neuen Fassungen nicht immer gleich. Beide auf einem
  Gerät durchgehen, nicht nur bauen.

Also: umstellen, dann **auf dem Telefon nachsehen**. Ein `targetSdk`, das nur gebaut
wurde, ist der klassische Fall von „läuft" gegen „gemessen".

## 2 · Die erste Entscheidung: Konto

Sie fällt vor allem anderen, weil sie Wochen kostet oder spart.

| | Privates Konto | Organisationskonto |
|---|---|---|
| Kosten | 25 USD einmalig | 25 USD einmalig |
| Nachweis | Ausweis | **D-U-N-S-Nummer** für Bischof Snowboards |
| Vor der ersten Veröffentlichung | **geschlossener Test: 12 Tester, 14 Tage ununterbrochen** | entfällt |
| Im Laden sichtbar als | „Leo Bischof" | „Bischof Snowboards" |

Die Testauflage gilt für private Konten, die nach dem 13.11.2023 angelegt wurden — also
für jedes neue. Zwölf Leute zu finden, die zwei Wochen lang angemeldet bleiben, ist bei
einem Werkstattwerkzeug die unangenehmere Aufgabe von beiden; steigt einer zwischendurch
aus, fängt die Frist von vorn an.

**Empfehlung: Organisationskonto.** Die D-U-N-S-Nummer ist kostenlos und dauert wenige
Tage, der Name passt zum Markenstreifen auf jedem Blatt, und die Testauflage entfällt.

## 3 · AAB statt APK

Play nimmt für neue Apps kein APK mehr, sondern ein **Android App Bundle**. Der Befehl
dafür gibt es seit heute:

```powershell
.\dev.ps1 build-aab
```

Er baut mit demselben Schlüssel aus `../_toolchain/aruco-signing/` wie
`build-apk-release`, und er prüft das Erzeugnis genauso nach.

**Der Schlüssel ist der Punkt, an dem man sich nicht vertun darf.** Play bietet „Play App
Signing" an: Google verwahrt den Auslieferungsschlüssel und signiert selbst. Das ist
bequem und für dieses Projekt trotzdem die falsche Wahl — dasselbe APK soll auch außerhalb
von Play weitergegeben werden können (GitHub-Releases, F-Droid-Reproducible-Builds), und
ein Schlüssel, der bei Google liegt, macht diese Kette bruchstückhaft. Wer Play App
Signing einmal aktiviert hat, kommt nicht wieder heraus.

## 4 · Was Play sonst verlangt

| Sache | Stand hier |
|---|---|
| Datenschutzerklärung unter öffentlicher Adresse | Entwurf: [`privacy-policy.md`](privacy-policy.md) — nur noch veröffentlichen |
| Data-Safety-Formular | leicht: **nichts wird erhoben**, siehe unten |
| Inhaltsbewertung (Fragebogen) | trivial, keine kritischen Inhalte |
| Symbol 512 × 512, Feature-Grafik 1024 × 500 | **fehlt** |
| Mindestens 2 Bildschirmfotos je Formfaktor | **fehlt** |
| Kurz- und Langbeschreibung | liegt in `fastlane/metadata/` und lässt sich übernehmen |
| Zielgruppe und Inhalte | „Nicht für Kinder bestimmt" |

Das **Data-Safety-Formular** ist bei dieser App das kürzeste, das man ausfüllen kann, und
zwar belegbar: das `AndroidManifest.xml` hat **keine `android.permission.INTERNET`**. Ohne
sie kann die App nichts senden — das ist eine Zusicherung des Systems, nicht eine
Beteuerung des Programmierers. Also überall „nein": keine Datenerhebung, keine Weitergabe,
keine Verschlüsselung nötig, nichts zu löschen.

**Die Kamera-Berechtigung muss man trotzdem erklären.** Play fragt gesondert danach; die
Antwort ist, dass der Sucher die Marker im laufenden Bild findet und das Bild das Gerät
nicht verlässt.

## 5 · GPLv3 auf Play — die bekannte Reibung

Das ist der Punkt, den ich beim Lizenzgespräch genannt habe und der bestehen bleibt.

Die Play-Nutzungsbedingungen untersagen Nutzern, aus Play bezogene Apps weiterzuverteilen.
Die GPLv3 gibt jedem Empfänger genau dieses Recht. Ob das ein echter Widerspruch ist,
wird seit Jahren gestritten; die Praxis ist eindeutig: **GPLv3-Apps stehen in großer Zahl
bei Play**, und Google entfernt sie nicht deswegen. Beschwerden kamen historisch von
Dritten, nicht von Google.

Was das Risiko praktisch auf null bringt, gilt hier ohnehin:

- **Der Urheber ist der Einreichende.** Wer selbst das Copyright hält, kann sich nicht
  selbst wegen Lizenzverstoßes belangen — Beschwerden Dritter laufen ins Leere.
- **Der Quelltext ist öffentlich**, in derselben Fassung, aus demselben Tag.
- **F-Droid steht daneben** und ist der Weg ohne jede Reibung. Play ist die Bequemlichkeit
  für Leute, die nur den Play Store kennen, nicht der Hauptweg.

## 6 · Reihenfolge

1. Konto entscheiden (§2) und anlegen — das läuft im Hintergrund weiter.
2. `targetSdk` auf 36, **auf einem Telefon nachsehen** (§1).
3. `.\dev.ps1 build-aab`.
4. Symbol, Feature-Grafik, Bildschirmfotos — dieselben wie für F-Droid.
5. Datenschutzerklärung veröffentlichen, Adresse eintragen.
6. Interner Test → geschlossener Test → Produktion.
