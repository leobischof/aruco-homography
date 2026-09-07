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
from app.vision.geometry import project
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


@pytest.mark.parametrize("name", NAMES)
def test_rueckgerechnete_mittelpunkte_treffen_die_sollposition(name):
    """Die Millimeter selbst, gegen die Grundwahrheit - nicht gegen Python.

    Die drei Tests darueber messen in Pixeln; erst dieser misst in der Einheit,
    die das Produkt ist. Ohne ihn waere `centre_mm` in der goldenen Datei eine
    Zusage, die niemand einloest - und der C++-Kern uebernaehme sie ungeprueft.
    """
    image, truth = load(name)
    limit = truth["tolerances"]["centre_mm"]

    solution = solve(detect_markers(image), truth["marker_mm"], "sheet", NoticeList())
    # Die Homographie bildet Ebene(mm) -> Bild(px) ab. Rueckwaerts wird der Marker
    # wieder zum Quadrat, und dann ist das Mittel seiner vier Ecken sein Mittelpunkt.
    inverse = np.linalg.inv(solution.homography)

    for marker in solution.markers:
        measured = project(inverse, marker.corners_px).mean(axis=0)
        expected = np.asarray(truth["marker_centers_mm"][str(marker.marker_id)])
        error = float(np.linalg.norm(measured - expected))
        assert error <= limit, (
            f"Marker {marker.marker_id}: Mittelpunkt {error:.4f} mm daneben > {limit} mm"
        )
