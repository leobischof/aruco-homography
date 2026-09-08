---
title: Stufe 1: `shared/` — eine Wahrheit, sprachneutral
description: Der Plan, mit dem Konstanten und Prüfszenen aus Python herausgelöst wurden, damit drei Sprachen dieselben Zahlen lesen.
audience: developer
status: current
updated: 2026-09-07
---

# Stufe 1: `shared/` — eine Wahrheit, sprachneutral

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Ziel:** Die Konstanten und die Grundwahrheiten aus Python herauslösen, damit ein
C++-Kern und eine JavaScript-PDF-Schicht später **dieselben** Zahlen und **dieselben**
Prüfszenen benutzen können — ohne dass irgendetwas kopiert wird.

**Architektur:** `shared/constants.json` wird die einzige Quelle für alle Konstanten,
die Aussagen über das *Produkt* machen (Marker, Blatt, Schwellen, PDF-Geometrie,
Marke). `app/config.py` liest daraus und bleibt nach außen unverändert — kein anderes
Modul merkt etwas. `shared/fixtures/` friert die synthetischen Szenen als Dateien ein,
zusammen mit der **Grundwahrheit**, aus der sie gebaut wurden.

**Tech Stack:** Python 3.13, pytest, NumPy, OpenCV, PyInstaller (das Bundle muss
`shared/` mitnehmen).

**Vorbedingung:** Zweig von `master`. Der ausgelieferte Stand darf zu keinem Zeitpunkt
kaputt sein — nach jeder Aufgabe läuft die Anwendung.

## Global Constraints

- **AGENTS.md Invariante 4:** Konstanten haben genau eine Stelle. Nach dieser Stufe ist
  das für Produktkonstanten `shared/constants.json`, gelesen von `app/config.py`. Es
  darf **keine** zweite Definition entstehen — auch keine „Vorgabe, falls die Datei
  fehlt". Fehlt die Datei, bricht der Start ab.
- **AGENTS.md Invariante 7:** Jede sichtbare Zeichenkette kommt aus dem i18n-Katalog.
  Diese Stufe fasst Kataloge nicht an.
- **Ausgangslage: 153 Tests grün.** Nach jeder Aufgabe wieder grün, Zahl nennen.
- **Nichts an Zahlenwerten ändern.** Das ist ein wertbewahrender Umbau. Ein
  Charakterisierungstest belegt das.
- **Die `.exe` muss weiter laufen.** `shared/` liegt außerhalb von `app/`, also muss
  `aruco-homographie.spec` es ausdrücklich ins Bundle legen — sonst startet die
  gebaute Anwendung nicht mehr.
- **Git:** Committen ohne Rückfrage, **niemals pushen**. Ein Feature, ein Commit.
  Betreff englisch mit konventionellem Präfix, Leerzeile, Rumpf erklärt das *Warum*.
  Autor: `Leo Bischof <leo@bischof-snowboards.com>` via
  `git -c user.name="Leo Bischof" -c user.email="leo@bischof-snowboards.com" commit -F <datei>`
- Commit-Rumpf endet auf:
  ```
  Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01EwNDZCfoWx3Nyh6Z1kLi3V
  ```

---

## Aufgabe 1: Produktkonstanten nach `shared/constants.json`

**Files:**
- Create: `shared/constants.json`
- Create: `shared/README.md`
- Modify: `app/config.py` (Zeilen 98–234: die Konstantenblöcke)
- Modify: `aruco-homographie.spec:120-124` (datas)
- Test: `tests/test_shared_constants.py` (neu)

**Interfaces:**
- Consumes: nichts aus früheren Aufgaben.
- Produces:
  - `shared/constants.json` — flaches JSON-Objekt, Schlüssel in `SCREAMING_SNAKE_CASE`,
    identisch mit den heutigen Python-Namen.
  - `app.config.shared_path(*parts) -> pathlib.Path` — Pfad zu einer Datei unter
    `shared/`, funktioniert im Quellbaum **und** im PyInstaller-Bundle.
  - `app.config.SHARED_CONSTANTS: dict` — der geladene Inhalt.
  - Alle heutigen `config.*`-Namen bleiben erhalten und liefern dieselben Werte.

### Welche Konstanten umziehen

**Grenze:** Ist es eine Aussage über das **Produkt** (Millimeter, Schwellen, Farben,
Papier), zieht es um. Ist es eine Aussage über das **Python-Programm** (Pfade, Port,
Fassung, Speicherschlüssel), bleibt es.

| Umziehen | Bleiben in `config.py` |
|---|---|
| `ARUCO_DICT_NAME`, `MARKER_MM_NOMINAL` | `resource_path`, `STATIC_DIR`, `BRAND_DIR`, `LOGO_*_SVG` |
| `SHEET_MM`, `SHEET_SPACING_MM`, `SHEET_MARKER_IDS` | `APP_VERSION*` |
| `DPI_DEFAULT`, `DPI_CHOICES`, `MAX_OUTPUT_MPX`, `MAX_UPLOAD_MB`, `PREVIEW_MAX_PX`, `DEFAULT_CROP_MAX_MM`, `JPEG_QUALITY` | `LOCALE_DIR`, `LOCALE_STORAGE_KEY`, `THEME_STORAGE_KEY` |
| alle `*_WARN*`, `CAM_HEIGHT_*`, `HORIZON_EPS`, `EXTENT_HULL_FACTOR`, `COLLINEARITY_WARN` | `SESSION_TTL_S`, `HOST`, `PORT`, `BROWSER_WAIT_S` |
| `LAYOUT_DEFAULT`, `PAGE_MARGIN_MM_DEFAULT`, `PRINTER_MARGIN_MM_DEFAULT`, `TILE_*`, `STRIP_H_MM`, `GRID_*`, `SCALEBAR_MM`, `CONTOUR_*`, `SHEET_FORMATS` | `ARUCO_DICT_ID` (aus dem Namen **abgeleitet**) |
| `BRAND_NAME`, `BRAND_CLAIM`, `BRAND_URL`, `BRAND_INK`, `BRAND_PRIMARY`, `BRAND_ACTION`, `BRAND_DARK`, `BRAND_LIGHT`, `BRAND_SECONDARY`, `BRAND_ACCENT`, `BRAND_DESTRUCTIVE`, `LOGO_MM` | `BRAND_COPYRIGHT` (abgeleitet), `SHEET_MARKER_CENTERS_MM` (berechnet) |
| alle `ADJUST_*` | `PT_PER_MM` (abgeleitet aus `MM_PER_INCH`) |
| `SUPPORTED_LOCALES`, `DEFAULT_LOCALE`, `MM_PER_INCH` | `GRID_INK` (= `BRAND_INK`) |

**Wichtig:** `ARUCO_DICT_ID = cv2.aruco.DICT_4X4_50` zieht **nicht** um. In der JSON
steht nur der **Name**; jede Sprache leitet ihre eigene Kennung daraus ab. Das ist der
Punkt: eine OpenCV-Zahl in einer sprachneutralen Datei wäre keine.

- [ ] **Schritt 1: Charakterisierungstest schreiben — er muss SOFORT grün sein**

Das ist kein Rot-Grün-Zyklus, sondern die Absicherung eines wertbewahrenden Umbaus:
der Test hält die heutigen Werte fest, **bevor** etwas bewegt wird. Bleibt er nach dem
Umbau grün, hat sich nachweislich keine Zahl geändert.

Datei `tests/test_shared_constants.py`:

```python
"""Belegt, dass der Umzug der Konstanten nach shared/ keine Zahl veraendert hat.

Die Werte hier sind mit der Hand aus app/config.py von vor dem Umzug uebernommen.
Wer eine Konstante absichtlich aendert, aendert sie HIER mit - und sieht dabei,
dass er sie aendert. Genau das ist der Zweck.
"""

from __future__ import annotations

import json

from app import config

# Vor dem Umzug aus app/config.py abgelesen. Nicht generiert - abgeschrieben.
FROZEN = {
    "ARUCO_DICT_NAME": "DICT_4X4_50",
    "MARKER_MM_NOMINAL": 67.0,
    "SHEET_MM": (210.0, 297.0),
    "SHEET_SPACING_MM": (121.0, 171.0),
    "SHEET_MARKER_IDS": (0, 1, 2, 3),
    "DPI_DEFAULT": 300,
    "DPI_CHOICES": (150, 200, 300, 400, 600),
    "MAX_OUTPUT_MPX": 300.0,
    "MAX_UPLOAD_MB": 60,
    "PREVIEW_MAX_PX": 1600,
    "DEFAULT_CROP_MAX_MM": 1500.0,
    "JPEG_QUALITY": 92,
    "RMS_WARN_PX": 2.0,
    "RMS_WARN_MM": 1.0,
    "MARKER_SIZE_DEV_WARN": 0.02,
    "MARKER_ROT_WARN_DEG": 2.0,
    "EXTRAPOLATION_WARN_FRAC": 0.25,
    "COLLINEARITY_WARN": 0.05,
    "CAM_HEIGHT_MIN_MM": 100.0,
    "CAM_HEIGHT_MAX_MM": 10000.0,
    "HORIZON_EPS": 0.02,
    "EXTENT_HULL_FACTOR": 3.0,
    "LAYOUT_DEFAULT": "tiles",
    "PAGE_MARGIN_MM_DEFAULT": 5.0,
    "PRINTER_MARGIN_MM_DEFAULT": 5.0,
    "TILE_OVERLAP_MM_DEFAULT": 10.0,
    "TILE_OVERVIEW_DEFAULT": True,
    "STRIP_H_MM": 18.0,
    "GRID_STEP_MM": 50.0,
    "GRID_LINE_PT": 0.5,
    "GRID_HALO_PT": 1.5,
    "GRID_LABEL_PT": 6.5,
    "SCALEBAR_MM": 100.0,
    "CONTOUR_LINE_MM": 0.25,
    "CONTOUR_EPS_MM": 0.5,
    "CONTOUR_MIN_AREA_FRAC": 0.05,
    "SHEET_FORMATS": {"A4": (210.0, 297.0), "A3": (297.0, 420.0)},
    "BRAND_NAME": "Bischof Snowboards",
    "BRAND_CLAIM": "Made with Bischof Snowboards Software",
    "BRAND_URL": "https://bischof-snowboards.com",
    "BRAND_INK": "#334155",
    "BRAND_PRIMARY": "#379992",
    "BRAND_ACTION": "#ffbf00",
    "BRAND_DARK": "#25242b",
    "BRAND_LIGHT": "#f1f5f9",
    "BRAND_SECONDARY": "#e2e8f0",
    "BRAND_ACCENT": "#f0f3f3",
    "BRAND_DESTRUCTIVE": "#e7000b",
    "LOGO_MM": 11.0,
    "ADJUST_CLAHE_TILES": 8,
    "ADJUST_CLAHE_CLIP_MAX": 4.0,
    "ADJUST_UNSHARP_SIGMA_PX": 2.0,
    "ADJUST_UNSHARP_MAX": 2.0,
    "ADJUST_EDGE_CANNY": (60, 160),
    "ADJUST_EMPHASIS_SIGMA_DEG": 25.0,
    "ADJUST_EMPHASIS_HUES": {
        "red": 0, "yellow": 22, "green": 60, "cyan": 90, "blue": 120, "magenta": 150,
    },
    "SUPPORTED_LOCALES": ("de", "en"),
    "DEFAULT_LOCALE": "de",
    "MM_PER_INCH": 25.4,
}


def test_konstanten_haben_sich_nicht_veraendert():
    """Jeder Wert ist noch der, der er vor dem Umzug war."""
    for name, expected in FROZEN.items():
        actual = getattr(config, name)
        assert actual == expected, f"{name}: {actual!r} statt {expected!r}"


def test_abgeleitete_werte_stimmen_weiter():
    """Was aus den Konstanten berechnet wird, rechnet danach noch dasselbe."""
    assert config.BRAND_COPYRIGHT == "Copyright (C) Bischof Snowboards"
    assert config.PT_PER_MM == 72.0 / 25.4
    assert config.GRID_INK == config.BRAND_INK
    assert config.SHEET_MARKER_CENTERS_MM == {
        0: (44.5, 63.0), 1: (165.5, 63.0), 2: (44.5, 234.0), 3: (165.5, 234.0),
    }
```

- [ ] **Schritt 2: Test laufen lassen — er MUSS grün sein**

```
.\dev.ps1 run-tests
```

Erwartet: **155 passed** (153 + 2 neue). Ist er rot, ist ein Wert oben falsch
abgeschrieben — korrigieren, **bevor** irgendetwas umzieht. Ein
Charakterisierungstest, der schon vor dem Umbau rot ist, sichert nichts.

- [ ] **Schritt 3: `shared/constants.json` anlegen**

JSON kennt keine Tupel. Was in Python ein Tupel ist, steht als Liste in der Datei und
wird beim Laden zurückverwandelt — die Liste `TUPLE_KEYS` in `config.py` sagt, welche.

```json
{
  "_comment": "Produktkonstanten. Sprachneutral, weil Python, C++ und JavaScript sie teilen. Aenderungen hier aendern das Produkt - siehe docs/cpp-migration/README.md.",

  "ARUCO_DICT_NAME": "DICT_4X4_50",
  "MARKER_MM_NOMINAL": 67.0,
  "SHEET_MM": [210.0, 297.0],
  "SHEET_SPACING_MM": [121.0, 171.0],
  "SHEET_MARKER_IDS": [0, 1, 2, 3],

  "DPI_DEFAULT": 300,
  "DPI_CHOICES": [150, 200, 300, 400, 600],
  "MAX_OUTPUT_MPX": 300.0,
  "MAX_UPLOAD_MB": 60,
  "PREVIEW_MAX_PX": 1600,
  "DEFAULT_CROP_MAX_MM": 1500.0,
  "JPEG_QUALITY": 92,

  "RMS_WARN_PX": 2.0,
  "RMS_WARN_MM": 1.0,
  "MARKER_SIZE_DEV_WARN": 0.02,
  "MARKER_ROT_WARN_DEG": 2.0,
  "EXTRAPOLATION_WARN_FRAC": 0.25,
  "COLLINEARITY_WARN": 0.05,
  "CAM_HEIGHT_MIN_MM": 100.0,
  "CAM_HEIGHT_MAX_MM": 10000.0,
  "HORIZON_EPS": 0.02,
  "EXTENT_HULL_FACTOR": 3.0,

  "LAYOUT_DEFAULT": "tiles",
  "PAGE_MARGIN_MM_DEFAULT": 5.0,
  "PRINTER_MARGIN_MM_DEFAULT": 5.0,
  "TILE_OVERLAP_MM_DEFAULT": 10.0,
  "TILE_OVERVIEW_DEFAULT": true,
  "STRIP_H_MM": 18.0,
  "GRID_STEP_MM": 50.0,
  "GRID_LINE_PT": 0.5,
  "GRID_HALO_PT": 1.5,
  "GRID_LABEL_PT": 6.5,
  "SCALEBAR_MM": 100.0,
  "CONTOUR_LINE_MM": 0.25,
  "CONTOUR_EPS_MM": 0.5,
  "CONTOUR_MIN_AREA_FRAC": 0.05,
  "SHEET_FORMATS": {"A4": [210.0, 297.0], "A3": [297.0, 420.0]},

  "BRAND_NAME": "Bischof Snowboards",
  "BRAND_CLAIM": "Made with Bischof Snowboards Software",
  "BRAND_URL": "https://bischof-snowboards.com",
  "BRAND_INK": "#334155",
  "BRAND_PRIMARY": "#379992",
  "BRAND_ACTION": "#ffbf00",
  "BRAND_DARK": "#25242b",
  "BRAND_LIGHT": "#f1f5f9",
  "BRAND_SECONDARY": "#e2e8f0",
  "BRAND_ACCENT": "#f0f3f3",
  "BRAND_DESTRUCTIVE": "#e7000b",
  "LOGO_MM": 11.0,

  "ADJUST_CLAHE_TILES": 8,
  "ADJUST_CLAHE_CLIP_MAX": 4.0,
  "ADJUST_UNSHARP_SIGMA_PX": 2.0,
  "ADJUST_UNSHARP_MAX": 2.0,
  "ADJUST_EDGE_CANNY": [60, 160],
  "ADJUST_EMPHASIS_SIGMA_DEG": 25.0,
  "ADJUST_EMPHASIS_HUES": {
    "red": 0, "yellow": 22, "green": 60, "cyan": 90, "blue": 120, "magenta": 150
  },

  "SUPPORTED_LOCALES": ["de", "en"],
  "DEFAULT_LOCALE": "de",
  "MM_PER_INCH": 25.4
}
```

- [ ] **Schritt 4: `app/config.py` auf die Datei umstellen**

Oben, direkt nach `resource_path`, einfügen:

```python
# --- Geteilte Konstanten -------------------------------------------------------
# Alles, was eine Aussage ueber das PRODUKT macht - Millimeter, Schwellen, Farben,
# Papier - steht in shared/constants.json und NICHT hier. Der Grund ist der Umzug
# auf einen C++-Kern und eine JavaScript-PDF-Schicht (docs/cpp-migration/): drei
# Sprachen, die dieselben Zahlen brauchen. Eine Zahl, die in Python steht, muessten
# die anderen beiden abschreiben - und abgeschriebene Zahlen driften.
#
# Was ueber das PYTHON-PROGRAMM etwas aussagt - Pfade, Port, Fassung - bleibt hier.
_SHARED_DIR = (
    Path(_BUNDLE_DIR) / "shared"
    if _BUNDLE_DIR
    else Path(__file__).resolve().parent.parent / "shared"
)


def shared_path(*parts: str) -> Path:
    """Pfad zu einer Datei unter `shared/`, im Quellbaum wie im Bundle.

    Bedingung an die Bauvorschrift: `aruco-homographie.spec` muss `shared/` ins
    Bundle legen. Fehlt es dort, startet die .exe nicht - und das ist Absicht.
    Eine Anwendung, die mit halben Konstanten weiterlaeuft, misst falsch.
    """
    return _SHARED_DIR.joinpath(*parts)


# JSON kennt keine Tupel. Diese Schluessel sind in Python Tupel und werden beim
# Laden zurueckverwandelt - damit `config.SHEET_MM[0]` sich nicht ploetzlich anders
# verhaelt als vorher und `in`-Pruefungen auf DPI_CHOICES weiter stimmen.
_TUPLE_KEYS = frozenset({
    "SHEET_MM", "SHEET_SPACING_MM", "SHEET_MARKER_IDS", "DPI_CHOICES",
    "ADJUST_EDGE_CANNY", "SUPPORTED_LOCALES",
})


def _load_shared_constants() -> dict:
    """Liest shared/constants.json und macht aus Listen wieder Tupel.

    Kein Vorgabewert, kein try/except: fehlt die Datei, ist das Bundle kaputt und
    der Abbruch mit Dateinamen ist die freundlichste Meldung, die es dann gibt.
    """
    raw = json.loads(shared_path("constants.json").read_text(encoding="utf-8"))
    raw.pop("_comment", None)
    values = {}
    for key, value in raw.items():
        if key in _TUPLE_KEYS:
            values[key] = tuple(value)
        elif key == "SHEET_FORMATS":
            values[key] = {name: tuple(size) for name, size in value.items()}
        else:
            values[key] = value
    return values


SHARED_CONSTANTS = _load_shared_constants()
globals().update(SHARED_CONSTANTS)
```

Dazu oben `import json` ergänzen.

Danach die umgezogenen Zuweisungen aus `app/config.py` **löschen** (die Blöcke
„Marker", „Aufloesung und Groessengrenzen", „Qualitaetsschwellen", „PDF-Geometrie",
„Bildaufbereitung" sowie die Marken- und Sprachwerte aus der Tabelle oben). Es bleiben
nur die **abgeleiteten** Werte, jetzt aus `SHARED_CONSTANTS` gespeist:

```python
ARUCO_DICT_ID = getattr(cv2.aruco, ARUCO_DICT_NAME)   # noqa: F821 - via globals()
BRAND_COPYRIGHT = f"Copyright (C) {BRAND_NAME}"       # noqa: F821
GRID_INK = BRAND_INK                                  # noqa: F821
PT_PER_MM = 72.0 / MM_PER_INCH                        # noqa: F821
```

> **Hinweis für den Umsetzenden:** `globals().update(...)` macht die Namen für
> statische Prüfer unsichtbar — daher die `noqa`. Wenn das im Review stört, ist die
> Alternative, jeden Namen einmal ausdrücklich zuzuweisen
> (`MARKER_MM_NOMINAL = SHARED_CONSTANTS["MARKER_MM_NOMINAL"]`). Das ist länger, aber
> greifbarer. **Entscheide dich für eine Variante und begründe sie im Commit.**

- [ ] **Schritt 5: `shared/README.md` schreiben**

```markdown
# `shared/` — was sich drei Sprachen teilen

Hier liegt, was Python, C++ und JavaScript **gemeinsam** brauchen. Nichts hier ist
Python-spezifisch, und nichts hier darf in einer der drei Sprachen noch einmal
definiert werden.

- `constants.json` — alle Konstanten, die eine Aussage über das *Produkt* machen.
  Konstanten über das *Programm* (Pfade, Port, Fassung) stehen weiter in
  `app/config.py`.
- `fixtures/` — eingefrorene synthetische Szenen samt Grundwahrheit. Jede
  Implementierung des Rechenkerns wird gegen **diese** Dateien geprüft, nicht
  gegeneinander.

Warum das so ist: `docs/cpp-migration/README.md`.
```

- [ ] **Schritt 6: `aruco-homographie.spec` das Bundle beibringen**

`aruco-homographie.spec:120-124` ersetzen durch:

```python
datas = [
    # Oberflaeche, Marke und i18n-Kataloge. KEIN Python - die statische Analyse
    # von PyInstaller sieht davon nichts.
    (os.path.join(ROOT, "app", "static"), os.path.join("app", "static")),
    # Die geteilten Konstanten. Liegen ausserhalb von app/, muessen also einzeln
    # genannt werden - ohne sie bricht config.py beim Start ab.
    (os.path.join(ROOT, "shared"), "shared"),
]
```

- [ ] **Schritt 7: Tests laufen lassen**

```
.\dev.ps1 run-tests
```

Erwartet: **155 passed**. Der Charakterisierungstest aus Schritt 1 ist der Beweis,
dass keine Zahl gewandert ist.

- [ ] **Schritt 8: Die `.exe` bauen und wirklich starten**

Der Schritt, der hier am ehesten schiefgeht: im Quellbaum findet `shared_path()` die
Datei über `__file__`, im Bundle über `sys._MEIPASS`. Nur der Bau zeigt, ob Schritt 6
gestimmt hat.

```
.\dev.ps1 build-exe
.\dist\ArUco-Homographie\ArUco-Homographie.exe --no-browser --port 8021
```

Dann in einer zweiten Konsole prüfen und **danach den Server beenden**:

```
curl http://127.0.0.1:8021/api/locales
```

Erwartet: `{"default":"de","locales":[...]}`. Bricht die `.exe` mit
`FileNotFoundError … constants.json` ab, fehlt der Eintrag aus Schritt 6.

- [ ] **Schritt 9: Commit**

```bash
git add shared/ app/config.py aruco-homographie.spec tests/test_shared_constants.py
git -c user.name="Leo Bischof" -c user.email="leo@bischof-snowboards.com" \
    commit -F <nachrichtendatei>
```

Betreff: `refactor: move product constants into a language-neutral file`

---

## Aufgabe 2: Prüfszenen einfrieren

**Files:**
- Create: `shared/fixtures/scenes/flat.png`, `shared/fixtures/scenes/thick.png`
- Create: `shared/fixtures/expected/flat.json`, `shared/fixtures/expected/thick.json`
- Create: `tools/freeze_fixtures.py`
- Test: `tests/test_conformance.py` (neu)

**Interfaces:**
- Consumes: `app.config.shared_path` aus Aufgabe 1.
- Produces:
  - `shared/fixtures/<name>.png` + `expected/<name>.json` als **Vertrag**, gegen den
    später auch der C++-Kern und der WASM-Bau geprüft werden.
  - `tests/test_conformance.py` als Vorlage: was diese Datei in Python tut, tut die
    C++-Seite später mit denselben Dateien.

### Warum Grundwahrheit und nicht Python-Ausgabe

Die goldenen Dateien enthalten die Werte, aus denen die Szene **gebaut** wurde — nicht
das, was Python daraus errechnet. Stünde Pythons Ergebnis drin, erbte jede spätere
Implementierung Pythons Schiefe, und niemand sähe es je. So wird **jede**
Implementierung gegen die Wirklichkeit gemessen, auch die heutige.

Die exakten Ecken liefert `tests/conftest.py:225 ideal_markers()`: es projiziert die
bekannten Markerecken durch die bekannte Homographie. Analytisch, nicht detektiert.

- [ ] **Schritt 1: Den Einfrierer schreiben**

Datei `tools/freeze_fixtures.py`:

```python
"""Schreibt die synthetischen Szenen als Dateien nach shared/fixtures/.

Einmal ausgefuehrt, danach nur wieder, wenn sich die Szenen absichtlich aendern
sollen. Die Dateien sind ein VERTRAG: gegen sie wird der C++-Kern geprueft, und
spaeter der WASM-Bau. Wer sie neu erzeugt, muss sagen warum.

    python tools/freeze_fixtures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config                                  # noqa: E402
from tests.conftest import ideal_markers, make_scene    # noqa: E402

SCENES = {
    "flat": {"thickness_mm": 0.0},
    "thick": {"thickness_mm": 20.0},
}

# Toleranzen fuer die Konformitaetspruefung. Sie stehen HIER und wandern mit in die
# goldene Datei, damit die C++-Seite dieselben benutzt, statt sich eigene auszudenken.
TOLERANCES = {
    "corner_px": 0.75,   # Detektierte Ecke gegen analytisch exakte Ecke
    "rms_px": 1.0,       # Reprojektionsfehler nach dem Ausgleich
    "centre_mm": 0.25,   # Rueckgerechneter Markermittelpunkt gegen Sollposition
}


def freeze(name: str, kwargs: dict) -> None:
    scene = make_scene(**kwargs)
    root = config.shared_path("fixtures")
    (root / "scenes").mkdir(parents=True, exist_ok=True)
    (root / "expected").mkdir(parents=True, exist_ok=True)

    # PNG, nicht JPEG: eine verlustbehaftete Szene waere in jeder Sprache eine
    # ANDERE Szene, sobald die Decoder sich um ein Bit unterscheiden.
    image_path = root / "scenes" / f"{name}.png"
    if not cv2.imwrite(str(image_path), scene.image):
        raise RuntimeError(f"konnte {image_path} nicht schreiben")

    truth = {
        "scene": name,
        "image": f"scenes/{name}.png",
        "image_size_px": list(scene.image_size),
        "marker_mm": scene.marker_mm,
        "thickness_mm": scene.thickness_mm,
        "correction_k": scene.correction_k,
        "camera": {
            "height_mm": scene.camera_height_mm,
            "focal_px": scene.focal_px,
            "focal35_mm": scene.focal35_mm,
            "nadir_mm": list(scene.nadir_mm),
            "tilt_deg": scene.tilt_deg,
        },
        "homography_plane_to_image": scene.homography.tolist(),
        "marker_centers_mm": {
            str(marker_id): list(centre)
            for marker_id, centre in sorted(scene.centers_mm.items())
        },
        # Der eigentliche Vertrag: wo die Ecken im Bild WIRKLICH liegen.
        "marker_corners_px": {
            str(marker.marker_id): marker.corners_px.tolist()
            for marker in ideal_markers(scene)
        },
        "tolerances": TOLERANCES,
    }

    out = root / "expected" / f"{name}.json"
    out.write_text(json.dumps(truth, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"  {name}: {image_path.name} ({image_path.stat().st_size} B) + {out.name}")


if __name__ == "__main__":
    print("friere Pruefszenen ein:")
    for scene_name, scene_kwargs in SCENES.items():
        freeze(scene_name, scene_kwargs)
```

- [ ] **Schritt 2: Einfrierer laufen lassen**

```
.\venv\Scripts\python.exe tools\freeze_fixtures.py
```

Erwartet: zwei PNG und zwei JSON, jede PNG mehrere Megabyte (2400×1800, verlustfrei).

- [ ] **Schritt 3: Den Konformitätstest schreiben — er MUSS scheitern**

Zuerst gegen einen absichtlich zu strengen Wert, um zu sehen, dass der Test wirklich
prüft. Datei `tests/test_conformance.py`:

```python
"""Prueft die Pipeline gegen die eingefrorenen Szenen in shared/fixtures/.

Das ist die Datei, die spaeter zweimal existiert: einmal hier fuer Python, einmal
in core/tests/ fuer C++ - gegen DIESELBEN Dateien und DIESELBEN Toleranzen. Zwei
Implementierungen ohne gemeinsamen Pruefstand driften, und sie driften in
Millimetern (docs/cpp-migration/README.md).
"""

from __future__ import annotations

import json

import cv2
import numpy as np
import pytest

from app import config
from app.notices import NoticeList
from app.vision.detect import detect_markers
from app.vision.solve import solve

FIXTURES = config.shared_path("fixtures")
NAMES = ("flat", "thick")


def load(name: str):
    truth = json.loads((FIXTURES / "expected" / f"{name}.json").read_text("utf-8"))
    image = cv2.imread(str(FIXTURES / truth["image"]), cv2.IMREAD_COLOR)
    assert image is not None, f"Szene {name} nicht lesbar"
    return image, truth


@pytest.mark.parametrize("name", NAMES)
def test_szene_ist_lesbar_und_hat_die_erwartete_groesse(name):
    image, truth = load(name)
    assert [image.shape[1], image.shape[0]] == truth["image_size_px"]


@pytest.mark.parametrize("name", NAMES)
def test_alle_vier_marker_werden_gefunden(name):
    image, truth = load(name)
    markers = detect_markers(image)
    assert sorted(m.marker_id for m in markers) == sorted(
        int(k) for k in truth["marker_corners_px"]
    )


@pytest.mark.parametrize("name", NAMES)
def test_ecken_liegen_innerhalb_der_toleranz_an_der_grundwahrheit(name):
    """Der eigentliche Vertrag - hieran wird spaeter auch C++ gemessen."""
    image, truth = load(name)
    limit = truth["tolerances"]["corner_px"]

    found = {m.marker_id: np.asarray(m.corners_px) for m in detect_markers(image)}
    for marker_id, expected in truth["marker_corners_px"].items():
        actual = found[int(marker_id)]
        error = np.linalg.norm(actual - np.asarray(expected), axis=1)
        assert error.max() <= limit, (
            f"Marker {marker_id}: groesster Eckfehler {error.max():.3f} px > {limit} px"
        )


@pytest.mark.parametrize("name", NAMES)
def test_reprojektionsfehler_bleibt_unter_der_toleranz(name):
    image, truth = load(name)
    markers = detect_markers(image)
    # solve() nimmt die NoticeList als VIERTES, nicht optionales Argument - sie
    # sammelt Warnungen ein, die die Rechenschritte nicht selbst kennen muessen.
    solution = solve(markers, truth["marker_mm"], "sheet", NoticeList())
    assert solution.rms_px <= truth["tolerances"]["rms_px"]
```

- [ ] **Schritt 4: Sehen, dass der Test wirklich prüft**

`corner_px` in `tools/freeze_fixtures.py` **vorübergehend** auf `0.001` setzen,
Einfrierer neu laufen lassen, Tests laufen lassen:

```
.\dev.ps1 run-tests
```

Erwartet: `test_ecken_liegen_innerhalb_der_toleranz...` schlägt **fehl**, mit einer
Meldung wie `groesster Eckfehler 0.184 px > 0.001 px`.

**Die Zahl in dieser Fehlermeldung notieren** — sie ist der tatsächliche Eckfehler des
Detektors und begründet die endgültige Toleranz.

- [ ] **Schritt 5: Toleranz zurücksetzen und begründen**

`corner_px` zurück auf `0.75` (oder auf das ~4-fache des in Schritt 4 gemessenen
Fehlers, je nachdem was größer ist — als Kommentar mit der gemessenen Zahl
begründen). Einfrierer neu laufen lassen.

- [ ] **Schritt 6: Tests laufen lassen**

```
.\dev.ps1 run-tests
```

Erwartet: **163 passed** (155 + 8 neue: 4 Testfunktionen × 2 Szenen).

- [ ] **Schritt 7: Prüfen, dass die Fixtures wirklich in Git landen**

PNG-Dateien fallen leicht einer `.gitignore`-Regel zum Opfer — und ohne sie ist der
ganze Vertrag weg.

```
git status --short shared/fixtures/
git check-ignore -v shared/fixtures/scenes/flat.png
```

Erwartet: die Dateien erscheinen als neu; `check-ignore` findet **keine** Regel
(Rückgabewert 1, keine Ausgabe). Trifft doch eine Regel, in `.gitignore` eine
Ausnahme (`!shared/fixtures/**`) ergänzen.

- [ ] **Schritt 8: Commit**

```bash
git add shared/fixtures/ tools/freeze_fixtures.py tests/test_conformance.py
git -c user.name="Leo Bischof" -c user.email="leo@bischof-snowboards.com" \
    commit -F <nachrichtendatei>
```

Betreff: `test: freeze the synthetic scenes as a cross-language contract`

Der Rumpf muss sagen: **warum Grundwahrheit statt Python-Ausgabe**, und **welchen
Eckfehler** der Detektor in Schritt 4 tatsächlich hatte.

---

## Fertig, wenn

- `shared/constants.json` ist die einzige Stelle für Produktkonstanten, `config.py`
  liest daraus, und der Charakterisierungstest belegt, dass keine Zahl gewandert ist.
- Die eingefrorenen Szenen liegen als Dateien in Git, mit Grundwahrheit und Toleranzen.
- `.\dev.ps1 run-tests` → **163 passed**.
- Die gebaute `.exe` startet und antwortet — nicht nur der Quellbaum.
- Zwei Commits, beide von `leo@bischof-snowboards.com`, **nichts gepusht**.

## Was diese Stufe ausdrücklich NICHT tut

- **Kein Umzug von `app/` nach `py/`.** Das bricht `dev.ps1`, die Bauvorschrift, den
  Installer und jeden Pfad in der Dokumentation — und bringt vor Stufe 4 nichts.
- **Kein Umzug der i18n-Kataloge nach `shared/i18n/`.** Erst nötig, wenn die Hüllen
  sie brauchen; heute wäre es Bruch ohne Gegenwert.
- **Keine Zeile C++.** Das ist Stufe 2, und sie steht erst an, wenn Stufe 0 gezeigt
  hat, dass das Web-Ziel überhaupt tragfähig ist.
