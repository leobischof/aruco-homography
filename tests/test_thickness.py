"""Die Dickenkorrektur - in beide Richtungen geprueft.

Der zweite Test allein waere wertlos: er koennte auch dann gruen sein, wenn die
Szene gar keinen Hoehenversatz enthaelt. Deshalb belegt der erste Test zuerst, dass
das Problem ohne Korrektur wirklich auftritt, und zwar genau in der erwarteten
Groessenordnung.
"""

from __future__ import annotations

import numpy as np

from app.notices import NoticeList
from app.vision.camera import resolve_pose
from app.vision.geometry import project
from app.vision.solve import solve
from app.vision.thickness import effective_homography
from tests.conftest import ideal_markers


def object_corners(scene) -> np.ndarray:
    x0, y0, x1, y1 = scene.object_rect_mm
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])


def measured_size(scene, homography) -> tuple[float, float]:
    """Testobjekt durch eine gegebene Homographie zurueckmessen."""
    image_points = project(scene.homography, scene.apparent(object_corners(scene)))
    plane = project(np.linalg.inv(homography), image_points)
    return (
        float(np.linalg.norm(plane[1] - plane[0])),
        float(np.linalg.norm(plane[3] - plane[0])),
    )


def true_size(scene) -> tuple[float, float]:
    x0, y0, x1, y1 = scene.object_rect_mm
    return (x1 - x0, y1 - y0)


def test_ohne_korrektur_ist_der_fehler_genau_der_hoehenfaktor(thick_scene):
    """20 mm bei 900 mm Abstand: 2,27 % zu gross - das ist die Falle, um die es geht."""
    solution = solve(ideal_markers(thick_scene), thick_scene.marker_mm, "sheet", NoticeList())
    width, height = measured_size(thick_scene, solution.homography)
    truth_w, truth_h = true_size(thick_scene)

    assert width / truth_w == expect_k(thick_scene)
    assert height / truth_h == expect_k(thick_scene)
    # In Millimetern: auf 160 mm Breite sind das rund 3,6 mm daneben.
    assert width - truth_w > 3.0


def expect_k(scene):
    import pytest

    return pytest.approx(scene.correction_k, rel=1e-6)


def test_mit_korrektur_stimmt_das_mass(thick_scene):
    solution = solve(ideal_markers(thick_scene), thick_scene.marker_mm, "sheet", NoticeList())
    pose = resolve_pose(
        solution.homography,
        thick_scene.focal35_mm,
        *thick_scene.image_size,
        thick_scene.thickness_mm,
        None,
        NoticeList(),
    )
    corrected, factor = effective_homography(
        solution.homography, pose, thick_scene.thickness_mm
    )

    width, height = measured_size(thick_scene, corrected)
    truth_w, truth_h = true_size(thick_scene)

    assert abs(factor - thick_scene.correction_k) < 1e-4
    assert abs(width - truth_w) < 0.05, f"{width:.4f} statt {truth_w:.4f} mm"
    assert abs(height - truth_h) < 0.05, f"{height:.4f} statt {truth_h:.4f} mm"


def test_ohne_dicke_bleibt_die_homographie_unveraendert(scene):
    solution = solve(ideal_markers(scene), scene.marker_mm, "sheet", NoticeList())
    pose = resolve_pose(
        solution.homography, scene.focal35_mm, *scene.image_size, 0.0, None, NoticeList()
    )
    corrected, factor = effective_homography(solution.homography, pose, 0.0)

    assert factor == 1.0
    assert np.allclose(corrected, solution.homography)
