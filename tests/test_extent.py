"""Abbildbarer Bereich, Horizont-Clipping und der Extrapolationsanteil."""

from __future__ import annotations

import numpy as np

from app import config
from app.notices import NoticeList
from app.vision.extent import Extent, default_crop, extrapolation_fraction, plane_extent
from app.vision.solve import solve
from tests.conftest import ideal_markers, make_scene


def solved_extent(scene):
    solution = solve(ideal_markers(scene), scene.marker_mm, "sheet", NoticeList())
    return plane_extent(solution.homography, *scene.image_size, solution.hull_mm), solution


def test_extent_ist_endlich_und_enthaelt_die_marker(scene):
    extent, solution = solved_extent(scene)

    assert np.isfinite([extent.x0, extent.y0, extent.x1, extent.y1]).all()
    assert extent.width > 0 and extent.height > 0
    assert extent.x0 <= solution.hull_mm[:, 0].min()
    assert extent.x1 >= solution.hull_mm[:, 0].max()


def test_flacher_blickwinkel_sprengt_den_extent_nicht():
    """Ohne Horizont-Clipping kaemen hier Kilometer heraus."""
    scene = make_scene(camera_height_mm=350.0, target_mm=(700.0, 148.5))
    extent, _ = solved_extent(scene)

    assert np.isfinite([extent.x0, extent.y0, extent.x1, extent.y1]).all()
    assert extent.width < 5000.0 and extent.height < 5000.0


def test_startzuschnitt_bleibt_im_extent(scene):
    extent, solution = solved_extent(scene)
    crop = default_crop(extent, solution.hull_mm)

    assert crop.x0 >= extent.x0 and crop.y0 >= extent.y0
    assert crop.x1 <= extent.x1 and crop.y1 <= extent.y1
    assert crop.width <= config.DEFAULT_CROP_MAX_MM + 1e-9


def test_extrapolationsanteil_stimmt_an_den_raendern(scene):
    _, solution = solved_extent(scene)
    hull = solution.hull_mm

    inner = Extent(
        float(hull[:, 0].min()) + 5.0,
        float(hull[:, 1].min()) + 5.0,
        float(hull[:, 0].max()) - 5.0,
        float(hull[:, 1].max()) - 5.0,
    )
    assert extrapolation_fraction(inner, hull) < 0.02

    weit_draussen = Extent(2000.0, 2000.0, 2400.0, 2400.0)
    assert extrapolation_fraction(weit_draussen, hull) > 0.99
