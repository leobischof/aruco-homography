"""Die Produktzusage: das Bild belegt im PDF exakt die Millimeter des Zuschnitts.

Geprueft wird die MediaBox mit pypdf (1 mm = 2,834645669 pt) sowie das
Platzierungsrechteck, das build_pdf zurueckmeldet.
"""

from __future__ import annotations

import io

import numpy as np
import pytest
from pypdf import PdfReader

from app import config
from app.pdf.build import ExportOptions, build_footer_lines, build_pdf


def dummy_image(width_mm: float, height_mm: float, dpi: int = 300) -> np.ndarray:
    """Graustufenmuster in der Groesse, die die Entzerrung liefern wuerde."""
    px_per_mm = dpi / config.MM_PER_INCH
    width = int(round(width_mm * px_per_mm))
    height = int(round(height_mm * px_per_mm))
    image = np.full((height, width, 3), 220, np.uint8)
    image[height // 4 : 3 * height // 4, width // 4 : 3 * width // 4] = 60
    return image


def page_size_mm(data: bytes, page: int = 0) -> tuple[float, float]:
    box = PdfReader(io.BytesIO(data)).pages[page].mediabox
    return (float(box.width) / config.PT_PER_MM, float(box.height) / config.PT_PER_MM)


FOOTER = build_footer_lines({"object_mm": "Test"})


def test_einzelseite_hat_exakt_die_erwartete_groesse():
    crop_w, crop_h = 400.0, 250.0
    options = ExportOptions(layout="single", page_margin_mm=5.0)
    result = build_pdf(dummy_image(crop_w, crop_h), crop_w, crop_h, options, FOOTER)

    expected = (crop_w + 10.0, crop_h + 10.0 + config.STRIP_H_MM)
    assert result.page_size_mm == pytest.approx(expected)
    assert page_size_mm(result.data) == pytest.approx(expected, abs=0.01)


def test_bildrechteck_belegt_genau_den_zuschnitt():
    crop_w, crop_h = 400.0, 250.0
    result = build_pdf(
        dummy_image(crop_w, crop_h),
        crop_w,
        crop_h,
        ExportOptions(layout="single", page_margin_mm=5.0),
        FOOTER,
    )

    x, y, width, height = result.image_rect_mm
    assert (width, height) == pytest.approx((crop_w, crop_h))
    assert (x, y) == pytest.approx((5.0, 5.0 + config.STRIP_H_MM))


def test_randlos_ohne_aufdrucke_ist_die_seite_das_objekt():
    crop_w, crop_h = 700.0, 500.0
    options = ExportOptions(
        layout="single",
        page_margin_mm=0.0,
        show_scalebar=False,
        show_footer=False,
        show_grid=False,
    )
    result = build_pdf(dummy_image(crop_w, crop_h, dpi=150), crop_w, crop_h, options, FOOTER)

    assert page_size_mm(result.data) == pytest.approx((crop_w, crop_h), abs=0.01)
    assert result.image_rect_mm == pytest.approx((0.0, 0.0, crop_w, crop_h))


def test_kachelung_hat_die_erwartete_seitenzahl_und_a4_seiten():
    crop_w, crop_h = 700.0, 500.0
    options = ExportOptions(
        layout="tiles", page_format="A4", orientation="portrait", tile_overview=True
    )
    result = build_pdf(dummy_image(crop_w, crop_h, dpi=150), crop_w, crop_h, options, FOOTER)

    reader = PdfReader(io.BytesIO(result.data))
    assert len(reader.pages) == result.page_count
    assert result.page_count == int(result.meta["tiles"]) + 1  # plus Klebeplan
    assert page_size_mm(result.data) == pytest.approx(config.SHEET_MM, abs=0.01)


def test_kachelung_ohne_klebeplan_ist_genau_die_kachelzahl():
    crop_w, crop_h = 700.0, 500.0
    options = ExportOptions(layout="tiles", page_format="A4", tile_overview=False)
    result = build_pdf(dummy_image(crop_w, crop_h, dpi=150), crop_w, crop_h, options, FOOTER)

    assert result.page_count == int(result.meta["tiles"])


def test_kontur_wird_gezeichnet_ohne_die_geometrie_zu_veraendern():
    crop_w, crop_h = 300.0, 200.0
    contour = np.array([[20.0, 20.0], [280.0, 20.0], [280.0, 180.0], [20.0, 180.0]])
    options = ExportOptions(layout="single", contour=True, page_margin_mm=5.0)
    result = build_pdf(
        dummy_image(crop_w, crop_h), crop_w, crop_h, options, FOOTER, contour_mm=contour
    )

    assert result.image_rect_mm == pytest.approx((5.0, 5.0 + config.STRIP_H_MM, crop_w, crop_h))
    assert len(result.data) > 1000
