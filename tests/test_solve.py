"""Der Ausgleich in beiden Modi, rauschfrei und mit Detektionsrauschen."""

from __future__ import annotations

import numpy as np
import pytest

from app.notices import AppError, NoticeList
from app.vision.detect import DetectedMarker
from app.vision.geometry import project
from app.vision.solve import solve
from tests.conftest import ideal_markers, make_scene, noisy_markers


def recovered_distance(scene, homography) -> float:
    """Bekannten 500-mm-Abstand durch die geloeste Homographie zurueckmessen."""
    image_points = project(scene.homography, scene.measure_points_mm)
    plane_points = project(np.linalg.inv(homography), image_points)
    return float(np.linalg.norm(plane_points[1] - plane_points[0]))


def test_blattmodus_rauschfrei_ist_exakt(scene):
    notices = NoticeList()
    solution = solve(ideal_markers(scene), scene.marker_mm, "sheet", notices)

    assert solution.rms_px < 1e-6
    assert abs(recovered_distance(scene, solution.homography) - scene.measure_distance_mm) < 1e-6


def test_blattmodus_misst_markergroesse_zurueck(scene):
    solution = solve(ideal_markers(scene), scene.marker_mm, "sheet", NoticeList())
    for fit in solution.markers:
        assert abs(fit.side_mm_measured - scene.marker_mm) < 1e-6
        assert abs(fit.rotation_deg) < 1e-6


def test_blattmodus_mit_rauschen_bleibt_unter_einem_halben_millimeter(scene):
    solution = solve(noisy_markers(scene, 0.2), scene.marker_mm, "sheet", NoticeList())
    error = abs(recovered_distance(scene, solution.homography) - scene.measure_distance_mm)
    assert error < 0.5, f"{error:.3f} mm ueber 500 mm"


def test_freimodus_rauschfrei_ist_exakt(scene):
    solution = solve(ideal_markers(scene), scene.marker_mm, "free", NoticeList())

    assert solution.rms_px < 1e-6
    assert abs(recovered_distance(scene, solution.homography) - scene.measure_distance_mm) < 1e-6


def test_freimodus_findet_das_unbekannte_layout(scene):
    """Die geschaetzten Markerabstaende muessen den echten entsprechen."""
    solution = solve(ideal_markers(scene), scene.marker_mm, "free", NoticeList())
    centres = {fit.marker_id: fit.plane_mm.mean(axis=0) for fit in solution.markers}

    truth_dx = scene.centers_mm[1][0] - scene.centers_mm[0][0]
    truth_dy = scene.centers_mm[2][1] - scene.centers_mm[0][1]
    assert abs((centres[1] - centres[0])[0] - truth_dx) < 1e-6
    assert abs((centres[2] - centres[0])[1] - truth_dy) < 1e-6


def test_freimodus_mit_rauschen_bleibt_unter_einem_millimeter(scene):
    solution = solve(noisy_markers(scene, 0.2), scene.marker_mm, "free", NoticeList())
    error = abs(recovered_distance(scene, solution.homography) - scene.measure_distance_mm)
    assert error < 1.0, f"{error:.3f} mm ueber 500 mm"


def test_freimodus_funktioniert_mit_beliebigem_layout():
    """Der eigentliche Zweck des Frei-Modus: irgendwie verteilte Marker."""
    scene = make_scene(
        centers_mm={0: (30.0, 40.0), 1: (170.0, 25.0), 2: (45.0, 250.0), 3: (185.0, 265.0)}
    )
    solution = solve(ideal_markers(scene), scene.marker_mm, "free", NoticeList())
    assert abs(recovered_distance(scene, solution.homography) - scene.measure_distance_mm) < 1e-6


def test_blattmodus_lehnt_fremde_ids_ab(scene):
    fremde = [DetectedMarker(m.marker_id + 20, m.corners_px) for m in ideal_markers(scene)]
    with pytest.raises(AppError) as error:
        solve(fremde, scene.marker_mm, "sheet", NoticeList())
    assert error.value.code == "no_sheet_ids"


def test_ohne_marker_bricht_ab(scene):
    with pytest.raises(AppError) as error:
        solve([], scene.marker_mm, "sheet", NoticeList())
    assert error.value.code == "no_markers"


def test_einzelmarker_rechnet_aber_warnt(scene):
    notices = NoticeList()
    solution = solve(ideal_markers(scene)[:1], scene.marker_mm, "sheet", notices)

    assert solution.rms_px < 1e-6
    assert "single_marker" in {n.code for n in notices.items}


def test_kollineare_marker_werden_gewarnt():
    """Drei Marker auf einer Linie: rechnerisch moeglich, praktisch unbrauchbar."""
    scene = make_scene(centers_mm={0: (40.0, 150.0), 1: (110.0, 150.0), 2: (180.0, 150.0)})
    notices = NoticeList()
    solve(ideal_markers(scene), scene.marker_mm, "free", notices)
    assert "collinear_markers" in {n.code for n in notices.items}


def test_falsche_markergroesse_faellt_auf(scene):
    """Wer 45 statt 50 mm eintraegt, bekommt keine stille Fehlskalierung."""
    notices = NoticeList()
    solve(ideal_markers(scene), 45.0, "free", notices)
    assert "marker_size_deviation" not in {n.code for n in notices.items}

    # Im Blattmodus passt das Layout dann nicht mehr zur Markergroesse - das faellt auf.
    notices = NoticeList()
    solve(ideal_markers(scene), 45.0, "sheet", notices)
    assert {"marker_size_deviation", "high_residual"} & {n.code for n in notices.items}
