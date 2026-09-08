"""Das Startsymbol der Android-App - aus dem echten Marker, nicht aus einer Zeichnung.

    ./venv/Scripts/python.exe android/tools/make_launcher_icons.py

Erzeugt android/app/src/main/res/mipmap-*/ic_launcher.png und
ic_launcher_foreground.png. Die Dateien sind eingecheckt: aapt2 backt Ressourcen
lange vor jedem Python-Lauf ein, ein Erzeugungsschritt im Gradle-Bau brauchte
also ein Python im Android-Bau - und das hat er nicht.

**Warum ein echter Marker.** Das Zeichen der App ist das Ding, das sie misst.
Gezeichnet wird Marker 0 aus dem Woerterbuch, das shared/constants.json nennt,
und zwar mit demselben cv2, das auch die Erkennung fuehrt. Ein von Hand
nachgemaltes Quadratmuster saehe genauso aus und waere eine Erfindung; dieses
hier ist im Wortsinn dasselbe Muster, das auf dem Markerblatt steht.

Zwei Erzeugnisse, weil Android zwei Sorten Symbol kennt:

* ``ic_launcher.png`` - das ganze Symbol fuer Android vor 8.0 (API < 26). Der
  Marker sitzt auf einem Feld in der Markenfarbe.
* ``ic_launcher_foreground.png`` - nur der Vordergrund fuer das adaptive Symbol ab
  API 26; den Hintergrund legt mipmap-anydpi-v26/ic_launcher.xml als Farbflaeche
  darunter. Der Vordergrund muss in der mittleren Ellipse von 66 % Kantenlaenge
  bleiben, weil das System ihn je nach Startbildschirm beschneidet - deshalb
  steht der Marker dort deutlich kleiner.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
RES = REPO / "android" / "app" / "src" / "main" / "res"

# Androids Dichtestufen. Die Zahl ist die Kantenlaenge des Symbols in Pixeln.
DENSITIES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}

# Der adaptive Vordergrund ist immer 108 dp gross, sichtbar sind davon 72 dp.
ADAPTIVE_SCALE = 108 / 48


def brand_colour() -> tuple[int, int, int]:
    """BRAND_PRIMARY aus shared/constants.json als (R, G, B)."""
    constants = json.loads((REPO / "shared" / "constants.json").read_text(encoding="utf-8"))
    value = constants["BRAND_PRIMARY"].lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def marker_bits(modules: int = 6) -> np.ndarray:
    """Marker 0 als (modules, modules)-Feld, 0 = schwarz - genau wie auf dem Blatt."""
    constants = json.loads((REPO / "shared" / "constants.json").read_text(encoding="utf-8"))
    dictionary = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, constants["ARUCO_DICT_NAME"])
    )
    image = dictionary.generateImageMarker(constants["SHEET_MARKER_IDS"][0], modules, 1)
    return np.asarray(image)


def render(size: int, marker_fraction: float, background: tuple[int, int, int] | None) -> np.ndarray:
    """Ein Symbol der Kantenlaenge `size`, RGBA."""
    canvas = np.zeros((size, size, 4), dtype=np.uint8)
    if background is not None:
        canvas[:, :, 0:3] = background
        canvas[:, :, 3] = 255

    bits = marker_bits()
    modules = bits.shape[0]
    # Auf ein Vielfaches der Modulzahl runden: sonst sind die Module verschieden
    # breit, und ein ungleichmaessiges Raster ist genau das, was der Detektor
    # spaeter nicht sehen soll.
    marker_px = max(modules, int(round(size * marker_fraction / modules)) * modules)
    scaled = cv2.resize(bits, (marker_px, marker_px), interpolation=cv2.INTER_NEAREST)

    offset = (size - marker_px) // 2
    patch = np.zeros((marker_px, marker_px, 4), dtype=np.uint8)
    patch[:, :, 0] = scaled
    patch[:, :, 1] = scaled
    patch[:, :, 2] = scaled
    patch[:, :, 3] = 255
    canvas[offset : offset + marker_px, offset : offset + marker_px] = patch
    return canvas


def main() -> int:
    background = brand_colour()
    for density, size in DENSITIES.items():
        directory = RES / f"mipmap-{density}"
        directory.mkdir(parents=True, exist_ok=True)

        # Das klassische Symbol: Marker auf Markenfarbe, mit Rand.
        classic = render(size, marker_fraction=0.68, background=background)
        cv2.imwrite(str(directory / "ic_launcher.png"), cv2.cvtColor(classic, cv2.COLOR_RGBA2BGRA))

        # Der adaptive Vordergrund: durchsichtig, Marker klein genug fuer jeden
        # Zuschnitt (0.68 * 72/108 der Gesamtkante).
        adaptive_size = int(round(size * ADAPTIVE_SCALE))
        foreground = render(adaptive_size, marker_fraction=0.68 * 72 / 108, background=None)
        cv2.imwrite(
            str(directory / "ic_launcher_foreground.png"),
            cv2.cvtColor(foreground, cv2.COLOR_RGBA2BGRA),
        )
        print(f"  {density:8s} {size:3d} px + {adaptive_size:3d} px adaptiv")

    print(f"Fertig: {RES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
