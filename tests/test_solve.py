"""Der Ausgleich in beiden Modi, rauschfrei und mit Detektionsrauschen."""

from __future__ import annotations

import numpy as np
import pytest

from app.notices import AppError, NoticeList
from app.vision.detect import DetectedMarker
from app.vision.geometry import project
from app.vision.solve import solve
from tests.conftest import ideal_markers, make_scene, noisy_markers, rotated_markers

# Vier Winkel ohne Muster - der Streu-Modus soll nichts voraussetzen. Keiner ist
# ein Vielfaches von 90 Grad: ein um 90 Grad gedrehter Marker sieht wie ein
# ungedrehter aus, wenn man die Eckenreihenfolge verwechselt, und genau dieser
# Fehler soll auffallen.
SCATTERED_ANGLES = {0: 37.0, 1: -62.0, 2: 128.0, 3: 15.0}


def recovered_distance(scene, homography) -> float:
    """Bekannten 500-mm-Abstand durch die geloeste Homographie zurueckmessen."""
    image_points = project(scene.homography, scene.measure_points_mm)
    plane_points = project(np.linalg.inv(homography), image_points)
    return float(np.linalg.norm(plane_points[1] - plane_points[0]))


def marker_angle_deg(quad: np.ndarray) -> float:
    """Der Winkel eines Markers in der Ebene, aus der Kante Ecke 0 -> Ecke 1."""
    edge = quad[1] - quad[0]
    return float(np.degrees(np.arctan2(edge[1], edge[0])))


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


def test_streumodus_rauschfrei_ist_exakt(scene):
    markers = rotated_markers(scene, SCATTERED_ANGLES)
    solution = solve(markers, scene.marker_mm, "scattered", NoticeList())

    assert solution.rms_px < 1e-6
    assert abs(recovered_distance(scene, solution.homography) - scene.measure_distance_mm) < 1e-6


def test_streumodus_gibt_jedem_marker_seinen_winkel_zurueck(scene):
    """Die Winkel sind das Neue an diesem Modus - also werden sie nachgemessen."""
    solution = solve(
        rotated_markers(scene, SCATTERED_ANGLES), scene.marker_mm, "scattered", NoticeList()
    )
    found = {fit.marker_id: marker_angle_deg(fit.plane_mm) for fit in solution.markers}

    # Die UNTERSCHIEDE der Winkel stecken allein in den Markerecken und muessen
    # deshalb exakt herauskommen.
    reference = min(found)
    for marker_id, angle in found.items():
        expected = SCATTERED_ANGLES[marker_id] - SCATTERED_ANGLES[reference]
        measured = angle - found[reference]
        assert abs(((measured - expected + 180.0) % 360.0) - 180.0) < 1e-6

    # Und die Markergroesse bleibt, was sie war: sie wird nicht mitgeschaetzt.
    for fit in solution.markers:
        assert abs(fit.side_mm_measured - scene.marker_mm) < 1e-6


def test_streumodus_richtet_die_ebene_nach_dem_foto_aus(scene):
    """Oben in der Schablone ist oben im Foto - nicht oben im groessten Marker.

    Der Zuschnitt ist ein achsparalleles Rechteck. Haengen die Ebenenachsen am
    Ankermarker, steht die Schablone in dessen Zufallswinkel schief. Zwei
    Aussagen belegen, dass sie das nicht tut.
    """
    solution = solve(
        rotated_markers(scene, SCATTERED_ANGLES), scene.marker_mm, "scattered", NoticeList()
    )

    # 1 - Jeder Marker steht in dem Winkel da, in dem er zum FOTO liegt. Haette
    #     der Anker die Achsen gesetzt, stuende er bei 0 und alle anderen relativ
    #     zu ihm. Die verbleibende Zehntelgrad ist die Scherung der Perspektive:
    #     die laesst sich nicht wegdrehen, und mehr will diese Zusage nicht.
    for fit in solution.markers:
        assert abs(marker_angle_deg(fit.plane_mm) - SCATTERED_ANGLES[fit.marker_id]) < 0.1

    # 2 - Und dasselbe ohne Marker gemessen: was im Bild waagrecht liegt, liegt
    #     auch in der Ebene waagrecht.
    inverse = np.linalg.inv(solution.homography)
    centre_px = project(solution.homography, solution.hull_mm.mean(axis=0).reshape(1, 2))[0]
    across = project(inverse, np.array([centre_px - [20.0, 0.0], centre_px + [20.0, 0.0]]))
    edge = across[1] - across[0]
    assert abs(np.degrees(np.arctan2(edge[1], edge[0]))) < 0.1


def test_streumodus_setzt_den_ursprung_in_die_markermitte(scene):
    """Ohne ausgezeichneten Marker gibt es auch keinen ausgezeichneten Ursprung."""
    solution = solve(
        rotated_markers(scene, SCATTERED_ANGLES), scene.marker_mm, "scattered", NoticeList()
    )
    centres = np.array([fit.plane_mm.mean(axis=0) for fit in solution.markers])
    assert np.allclose(centres.mean(axis=0), [0.0, 0.0], atol=1e-9)


def test_freimodus_scheitert_an_gedrehten_markern(scene):
    """Der Grund, warum es den Streu-Modus gibt - hier steht er als Zahl.

    Der Frei-Modus schaetzt je Marker nur eine Verschiebung und setzt damit
    voraus, dass alle gleich ausgerichtet liegen. Gilt das nicht, ist das
    Ergebnis nicht etwa ungenau, sondern falsch.
    """
    markers = rotated_markers(scene, SCATTERED_ANGLES)
    notices = NoticeList()
    solution = solve(markers, scene.marker_mm, "free", notices)

    assert solution.rms_px > 10.0
    assert abs(recovered_distance(scene, solution.homography) - scene.measure_distance_mm) > 100.0
    assert {"high_residual", "marker_rotation"} <= {n.code for n in notices.items}


def test_streumodus_warnt_nicht_ueber_gedrehte_marker(scene):
    """marker_rotation waere hier keine Warnung, sondern der Normalfall."""
    notices = NoticeList()
    solve(rotated_markers(scene, SCATTERED_ANGLES), scene.marker_mm, "scattered", notices)
    assert "marker_rotation" not in {n.code for n in notices.items}


def test_streumodus_mit_rauschen_bleibt_unter_zwei_millimetern(scene):
    """Mehr Unbekannte je Marker heisst weniger Sicherheit gegen Rauschen."""
    markers = rotated_markers(scene, SCATTERED_ANGLES)
    generator = np.random.default_rng(7)
    noisy = [
        DetectedMarker(m.marker_id, m.corners_px + generator.normal(0.0, 0.2, m.corners_px.shape))
        for m in markers
    ]
    solution = solve(noisy, scene.marker_mm, "scattered", NoticeList())
    error = abs(recovered_distance(scene, solution.homography) - scene.measure_distance_mm)
    assert error < 2.0, f"{error:.3f} mm ueber 500 mm"


def test_streumodus_kommt_mit_einem_einzigen_marker_aus(scene):
    """Ein Marker traegt sein Koordinatensystem selbst - vier Punktpaare reichen.

    Was er nicht traegt, ist eine Probe: das Residuum ist null, ohne dass der
    Fehler klein waere. Deshalb muss die Warnung kommen.
    """
    notices = NoticeList()
    einer = rotated_markers(scene, SCATTERED_ANGLES)[:1]
    solution = solve(einer, scene.marker_mm, "scattered", notices)

    assert solution.rms_px < 1e-6
    assert "single_marker" in {n.code for n in notices.items}
    # Auch allein wird die Ebene nach dem Foto ausgerichtet und nicht nach ihm.
    assert abs(marker_angle_deg(solution.markers[0].plane_mm) - SCATTERED_ANGLES[0]) < 0.1


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
