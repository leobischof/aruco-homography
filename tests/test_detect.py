"""Der echte Detektor gegen die analytisch exakten Ecken."""

from __future__ import annotations

import numpy as np

from app.vision.detect import detect_markers
from tests.conftest import ideal_markers


def test_findet_alle_marker(scene):
    found = detect_markers(scene.image)
    assert [m.marker_id for m in found] == sorted(scene.centers_mm)


def test_ecken_subpixelgenau(scene):
    """Ohne Subpixel-Refinement liegt der Fehler bei ~1 px; gefordert sind 0,3 px."""
    found = {m.marker_id: m for m in detect_markers(scene.image)}
    truth = {m.marker_id: m for m in ideal_markers(scene)}

    for marker_id, marker in truth.items():
        error = np.linalg.norm(found[marker_id].corners_px - marker.corners_px, axis=1)
        assert error.max() < 0.3, f"Marker {marker_id}: {error.max():.3f} px"


def test_eckenreihenfolge_stimmt(scene):
    """TL, TR, BR, BL - falsche Reihenfolge wuerde die Homographie spiegeln."""
    marker = detect_markers(scene.image)[0]
    top_left, top_right, bottom_right, _ = marker.corners_px
    assert top_right[0] > top_left[0]
    assert bottom_right[1] > top_right[1]
