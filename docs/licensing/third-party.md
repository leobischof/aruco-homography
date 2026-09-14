---
title: Fremder Code
description: Jede fremde Bibliothek mit ihrer Lizenz, getrennt nach dem, was wirklich ausgeliefert wird, und dem, was nur beim Bauen mitläuft.
audience: developer
status: current
updated: 2026-09-14
---

# Fremder Code

**Die Trennlinie dieses Dokuments ist „wird ausgeliefert" gegen „läuft nur hier".** Sie
ist der einzige Teil, der lizenzrechtlich zählt: Pflichten entstehen beim *Weitergeben*,
nicht beim Benutzen. Eine Bibliothek, die nur der Prüfstand anfasst, erzeugt keine.

Alle Angaben unten sind am **08.2026 installierten Stand** aus den Paketmetadaten
ausgelesen, nicht aus dem Gedächtnis zitiert. Nachzusehen mit:

```powershell
.\venv\Scripts\python.exe -c "import importlib.metadata as m; print(m.metadata('svglib')['License'])"
```

---

## 1 · Im Android-APK

Das ist die Liste, die für [F-Droid und Google Play](../publishing/README.md) gilt.

| Bibliothek | Fassung | Lizenz | Wo im Paket |
|---|---|---|---|
| **OpenCV** (Module `core`, `geometry`, `imgproc`, `objdetect`) | 5.x | Apache-2.0 | statisch in `libaruco_core.so` |
| **pdf-lib** | 1.17.1 | MIT | `assets/www/vendor/pdf-lib.esm.min.js` |
| **androidx.webkit** | 1.12.1 | Apache-2.0 | Java |
| **androidx.core** | 1.13.1 | Apache-2.0 | Java |
| **Montserrat** | variable | SIL OFL 1.1 | `assets/www/brand/fonts/` — Lizenztext liegt [daneben](../../app/static/brand/fonts/OFL.txt) |

Alle fünf sind mit der GPL-3.0 verträglich. Bei der Schrift ist das kein Zusammenbinden,
sondern ein Mitliefern: die OFL bleibt für die Schriftdatei bestehen, und die OFL
verlangt genau eine Sache — **dass ihr Text mitgeht**. Deshalb liegt
[`app/static/brand/fonts/OFL.txt`](../../app/static/brand/fonts/OFL.txt) neben der
`.woff2` und nicht in einem Ordner weiter oben. Wer die Schrift verschiebt, verschiebt
die Datei mit.

> Was **nicht** im APK liegt und deshalb hier fehlt: `@techstark/opencv-js` und der
> WASM-Kern unter `web/vendor/core/`. `./dev.ps1 check-apk` prüft das nach — die beiden
> stehen dort in der Liste `$AndroidPayloadForbidden`, und zwar aus einem Rechen- und nicht aus einem
> Lizenzgrund (ein zweiter Kern, den niemand mitmisst).

## 2 · In der Windows-`.exe`

| Bibliothek | Fassung | Lizenz |
|---|---|---|
| OpenCV (über `opencv-python-headless`) | 5.0.0.93 | Apache-2.0 |
| NumPy | 2.5.3 | BSD-3-Clause u. a. |
| SciPy | 1.18.1 | BSD-3-Clause |
| Pillow | 12.3.0 | MIT-CMU |
| pillow-heif | 1.7.0 | BSD-3-Clause |
| ReportLab | 5.0.1 | BSD-3-Clause |
| **svglib** | 2.2.0 | **LGPL-3.0-or-later** |
| qrcode | 8.2 | BSD-3-Clause |
| FastAPI | 0.141.1 | MIT |
| Uvicorn | 0.52.4 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| pydantic | 2.13.5 | MIT |
| pywebview | 6.2.1 | BSD-3-Clause |
| **PyInstaller** | 6.22.2 | **GPL-2.0-or-later mit Bootloader-Ausnahme** |

Zwei Zeilen sind fett, weil sie die einzigen sind, bei denen man kurz nachdenken muss:

- **svglib ist LGPL.** Mit der GPL-3.0 verträglich — die LGPL erlaubt ausdrücklich, unter
  der GPL weiterzugeben. Wäre dieses Projekt proprietär, müsste svglib dynamisch
  gebunden und austauschbar bleiben; unter der GPL entfällt die Auflage.
- **PyInstaller ist GPL-2.0-or-later.** Die Ausnahme in seiner Lizenz erlaubt, damit auch
  *unfreie* Programme zu packen — hier wird sie gar nicht gebraucht. „or later" heißt
  außerdem, dass der Bootloader unter GPL-3 weitergegeben werden darf, und genau das
  passiert.

**Die Kette geht also auf:** Apache-2.0, BSD, MIT und LGPL-3.0 dürfen alle in ein
GPL-3.0-Werk eingehen. Die umgekehrte Richtung gäbe es nicht — wäre dieses Projekt MIT,
wäre svglib das Problem.

## 3 · Nur beim Bauen und Prüfen — wird nicht ausgeliefert

| Werkzeug | Fassung | Lizenz | Wofür |
|---|---|---|---|
| pytest | 9.1.1 | MIT | `./dev.ps1 run-tests` |
| pypdf | 6.17.0 | BSD-3-Clause | PDFs in Tests nachmessen |
| httpx | 0.28.1 | BSD-3-Clause | der Testclient |
| pybind11 | 3.1.0 | BSD-3-Clause | die Python-Bindung an `core/` |
| `@techstark/opencv-js` | 5.0.0-release.1 | Apache-2.0 | Markermodule im Prüfstand erzeugen |
| **PyMuPDF** | 1.28.2 | **AGPL-3.0-or-later** oder Artifex-Kauflizenz | PDFs ansehen, beim Entwickeln |

**Die letzte Zeile ist der Grund, warum es diesen Abschnitt gibt.** PyMuPDF steht unter
der AGPL, und die AGPL ist die einzige Lizenz in diesem ganzen Dokument, die neue
Pflichten erzeugen könnte, wenn das Paket je mit ausgeliefert würde.

Es wird nicht ausgeliefert, und das ist kein Vorsatz, sondern eine Zeile im Bauplan:

```python
# aruco-homographie.spec
excludes = [
    ...
    "pymupdf",
    "fitz",
```

**Am Erzeugnis nachgesehen, nicht nur am Bauplan** — im gebauten Bündel unter `dist/`
(Stand 0.1.7-alpha) liegt weder das eine noch das andere:

```powershell
Get-ChildItem dist -Recurse -Include "fitz*","pymupdf*" | Measure-Object
# Count : 0    <- am 14.09.2026 so gemessen
```

Diese Zeile gehört in jede Prüfung vor einer Auslieferung. Ein `excludes`-Eintrag ist
eine Absicht; die Zahl darunter ist der Beleg.

Wer PyMuPDF je in `app/` importiert, verschiebt es damit in Abschnitt 2 und ändert die
Lizenzlage des ausgelieferten Programms. Das ist keine Kleinigkeit, die man nebenbei
macht.
