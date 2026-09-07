"""Entzerrung: exakte Rastergroesse und ein durchgemessenes Testobjekt."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.notices import AppError, NoticeList
from app.vision.extent import Extent
from app.vision.rectify import check_output_budget, output_size, px_per_mm_for_dpi, rectify
from app.vision.solve import solve
from tests.conftest import ideal_markers


def test_hundert_millimeter_bei_300_dpi_sind_1181_pixel():
    width, height = output_size(Extent(0.0, 0.0, 100.0, 100.0), px_per_mm_for_dpi(300))
    assert (width, height) == (1181, 1181)  # 100 mm * 300 / 25.4 = 1181,1


def test_rastergroesse_folgt_der_aufloesung():
    crop = Extent(10.0, 20.0, 210.0, 120.0)  # 200 x 100 mm
    assert output_size(crop, px_per_mm_for_dpi(150)) == (1181, 591)
    assert output_size(crop, px_per_mm_for_dpi(600)) == (4724, 2362)


def edge_distance_px(profile: np.ndarray) -> float:
    """Breite eines dunklen Blocks im Intensitaetsprofil, subpixelgenau.

    Eine Bounding-Box auf einem Schwellwertbild misst systematisch zu gross, weil
    die weichgezeichneten Randpixel mitzaehlen. Stattdessen wird die 50-%-Flanke
    beidseitig linear interpoliert - das ist unabhaengig von der Kantenschaerfe.
    """
    level = (float(profile.min()) + float(profile.max())) / 2.0
    below = profile < level
    first = int(np.argmax(below))
    last = len(below) - 1 - int(np.argmax(below[::-1]))

    left = first - 1 + (profile[first - 1] - level) / (profile[first - 1] - profile[first])
    right = last + (profile[last] - level) / (profile[last] - profile[last + 1])
    return float(right - left)


def test_testobjekt_misst_sich_im_entzerrten_bild_richtig(scene):
    """Ende-zu-Ende durch das Rasterbild: Kante rein, Millimeter raus."""
    solution = solve(ideal_markers(scene), scene.marker_mm, "sheet", NoticeList())
    x0, y0, x1, y1 = scene.object_rect_mm
    crop = Extent(x0 - 20.0, y0 - 20.0, x1 + 20.0, y1 + 20.0)

    px_per_mm = px_per_mm_for_dpi(300)
    image = rectify(scene.image, solution.homography, crop, px_per_mm, solution.px_per_mm)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)

    # Mittlere Profile durch die Mitte des Objekts, quer und laengs.
    height, width = gray.shape
    horizontal = gray[height // 2 - 50 : height // 2 + 50, :].mean(axis=0)
    vertical = gray[:, width // 2 - 50 : width // 2 + 50].mean(axis=1)

    assert abs(edge_distance_px(horizontal) / px_per_mm - (x1 - x0)) < 0.3
    assert abs(edge_distance_px(vertical) / px_per_mm - (y1 - y0)) < 0.3


def test_zu_grosse_ausgabe_wird_abgelehnt_mit_vorschlag():
    riesig = Extent(0.0, 0.0, 3000.0, 3000.0)  # 3 x 3 m bei 600 dpi
    with pytest.raises(AppError) as error:
        check_output_budget(riesig, 600)

    assert error.value.code == "output_too_large"
    assert error.value.field_name == "dpi"
    # Der Vorschlag steckt als Baustein in den Parametern, nicht als fertiger Satz -
    # welche Sprache daraus wird, entscheidet erst die HTTP-Schicht.
    assert error.value.params["hint"].key == "errors.output_too_large_hint_crop"
    assert "dpi" in error.value.message("de").lower()


def test_erlaubte_ausgabe_geht_durch():
    check_output_budget(Extent(0.0, 0.0, 700.0, 500.0), 300)  # wirft nicht
