---
title: Lizenzlage
description: Unter welcher Lizenz dieses Projekt steht, was das für Abhängigkeiten heißt und was die Marke davon ausnimmt.
audience: developer
status: current
updated: 2026-09-14
---

# Lizenzlage

Drei Fragen, drei Dateien. Wer eine davon beantwortet haben will, muss nicht die
anderen beiden lesen.

| Frage | Datei |
|---|---|
| Unter welcher Lizenz steht **dieses** Projekt? | [`../../LICENSE`](../../LICENSE) — GNU GPL, Version 3 oder später, im Wortlaut |
| Was ist von der Lizenz **nicht** erfasst? | [`../../TRADEMARKS.md`](../../TRADEMARKS.md) — Name und Zeichen, als Zusatzbedingung nach GPLv3 §7(e) |
| Wessen Code liegt sonst noch drin? | [`third-party.md`](third-party.md) — jede fremde Bibliothek mit ihrer Lizenz, getrennt nach dem, was **ausgeliefert** wird |

---

## 1 · Die kurze Antwort

**GNU General Public License, Version 3 oder später.** Copyright © 2026 Leo Bischof.

```
SPDX-License-Identifier: GPL-3.0-or-later
```

Das heißt, in der Reihenfolge, in der es jemanden interessiert:

- **Benutzen, weitergeben, verändern: ja.** Für jeden Zweck, auch gewerblich.
- **Wer eine veränderte Fassung weitergibt, gibt den Quelltext mit weiter** — unter
  derselben Lizenz. Das gilt für das APK genauso wie für die `.exe`.
- **Keine Gewährleistung.** Steht in §15 und §16 der Lizenz und ist bei einem Werkzeug,
  dessen Erzeugnis gesägt wird, keine Formalie: die Verantwortung für das Maß liegt bei
  dem, der sägt. Das sagt auch die [`../../README.md`](../../README.md) — *am fertigen
  Teil nachmessen.*

## 2 · Warum GPL und nicht MIT

Weil die Kette, die hier zählt, nachprüfbar bleiben soll.

Dieses Projekt behauptet Millimeter. Der einzige Beleg dafür sind die Tests in `tests/`
und die eingefrorenen Szenen in `shared/fixtures/` — und die nützen niemandem, der eine
Binärdatei in der Hand hält, deren Quelltext er nicht sehen kann. Eine geschlossene
Abzweigung dieses Werkzeugs könnte an der Geometrie etwas ändern, weiter „maßhaltig"
sagen, und niemand könnte nachsehen. **Unter der GPL kann er das nicht, ohne den
Quelltext mitzugeben.**

Der Preis ist bekannt und wird hier bewusst bezahlt: Wer dieses Werkzeug in ein
geschlossenes Produkt einbauen will, darf das nicht. Für eine Bibliothek wäre das der
falsche Handel. Für ein Werkzeug, dessen ganzer Wert an einer überprüfbaren Zusage
hängt, ist es der richtige.

## 3 · Der Kopf in neuen Dateien

Neue Quelldateien bekommen **eine** Zeile, nicht den ganzen Lizenzkopf:

```python
# SPDX-License-Identifier: GPL-3.0-or-later
```

Das ist kein Sparen an der richtigen Stelle, sondern die Form, auf die sich
Lizenzwerkzeuge geeinigt haben ([SPDX](https://spdx.dev/)) — sie ist maschinenlesbar,
und sie läuft nicht auseinander, weil sie zu kurz zum Auseinanderlaufen ist. Der
vollständige Wortlaut steht genau einmal, in [`../../LICENSE`](../../LICENSE).

Bestehende Dateien werden dafür **nicht** angefasst. Ein Commit, der 200 Dateien um eine
Kommentarzeile ergänzt, macht die Historie unlesbar und beweist nichts, was die
`LICENSE` an der Wurzel nicht schon beweist.

## 4 · Was das für Beiträge heißt

Wer hier etwas beiträgt, stellt es unter dieselbe Lizenz. Es gibt **kein** CLA und keine
Abtretung von Rechten — der Beitragende behält sein Copyright. Das steht ausführlich in
[`../../CONTRIBUTING.md`](../../CONTRIBUTING.md), Abschnitt *Licence of your contribution*.
