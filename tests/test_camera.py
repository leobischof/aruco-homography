"""Brennweite, Zerlegung der Homographie und die Fallback-Kette."""

from __future__ import annotations

import numpy as np
import pytest

from app.notices import AppError, NoticeList
from app.vision.camera import focal_px_from_focal35, pose_from_homography, resolve_pose


def test_brennweite_aus_35mm_aequivalent():
    # 26 mm KB-Aequivalent auf 2400 px Laengsseite: 26/36 * 2400
    assert focal_px_from_focal35(26.0, 2400, 1800) == pytest.approx(1733.333, abs=1e-3)
    assert focal_px_from_focal35(26.0, 1800, 2400) == pytest.approx(1733.333, abs=1e-3)


def test_zerlegung_findet_hoehe_lotpunkt_und_neigung(scene):
    height, nadir, tilt = pose_from_homography(
        scene.homography, scene.focal_px, *scene.image_size
    )

    assert abs(height - scene.camera_height_mm) / scene.camera_height_mm < 0.005
    assert np.linalg.norm(np.array(nadir) - np.array(scene.nadir_mm)) < 1.0
    assert abs(tilt - scene.tilt_deg) < 0.1


def test_exif_weg_wird_benutzt(scene):
    pose = resolve_pose(
        scene.homography, scene.focal35_mm, *scene.image_size, 20.0, None, NoticeList()
    )
    assert pose.source == "exif"
    assert pose.height_mm == pytest.approx(scene.camera_height_mm, rel=0.005)


def test_ohne_exif_und_ohne_dicke_ist_das_kein_fehler(scene):
    pose = resolve_pose(scene.homography, None, *scene.image_size, 0.0, None, NoticeList())
    assert pose.source == "none"
    assert pose.height_mm is None


def test_ohne_exif_mit_dicke_wird_der_abstand_zur_pflicht(scene):
    with pytest.raises(AppError) as error:
        resolve_pose(scene.homography, None, *scene.image_size, 20.0, None, NoticeList())
    assert error.value.code == "camera_height_required"
    assert error.value.field_name == "camera_height_mm"


def test_manueller_abstand_ersetzt_das_fehlende_exif(scene):
    pose = resolve_pose(scene.homography, None, *scene.image_size, 20.0, 850.0, NoticeList())
    assert pose.source == "manual"
    assert pose.height_mm == 850.0
    assert pose.nadir_mm is not None  # Bildmitte in die Ebene zurueckprojiziert


def test_unplausible_hoehe_wird_verworfen(scene):
    """Eine absurde Brennweite darf keine absurde Korrektur nach sich ziehen."""
    notices = NoticeList()
    with pytest.raises(AppError):
        resolve_pose(scene.homography, 0.05, *scene.image_size, 20.0, None, notices)
    assert "camera_height_implausible" in {n.code for n in notices.items}
