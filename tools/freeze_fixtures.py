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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config                                  # noqa: E402
from tests.conftest import ideal_markers, make_scene    # noqa: E402

SCENES = {
    "flat": {"thickness_mm": 0.0},
    "thick": {"thickness_mm": 20.0},
}

# Toleranzen fuer die Konformitaetspruefung. Sie stehen HIER und wandern mit in die
# goldene Datei, damit die C++-Seite dieselben benutzt, statt sich eigene auszudenken.
#
# Alle drei sind an DIESEN Szenen gemessen, nicht geschaetzt. Nachgestellt wurde es,
# indem corner_px voruebergehend auf 0.001 gesetzt und der Test zum Scheitern
# gebracht wurde. Achtung beim Nachmessen: der Test bricht beim ersten Marker ab
# (dort 0,186 px) - der schlechteste ist Marker 2. Die Szenen bilden 1,923 px/mm ab,
# ein Pixel ist hier also gut ein halber Millimeter.
TOLERANCES = {
    # Detektierte Ecke gegen analytisch exakte Ecke. Gemessen: 0,2337 px in beiden
    # Szenen. 0,75 px laesst gut das Dreifache Luft und bleibt dabei unter einem
    # halben Millimeter (0,39 mm) - eine andere Implementierung darf abweichen,
    # aber nicht so weit, dass es am Ausdruck sichtbar wird.
    "corner_px": 0.75,
    # Reprojektionsfehler nach dem Ausgleich. Gemessen: 0,095 px.
    "rms_px": 1.0,
    # Rueckgerechneter Markermittelpunkt gegen Sollposition - die Millimeter selbst.
    # Gemessen: 0,023 mm.
    "centre_mm": 0.25,
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
