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
from app.pdf.build import (
    ExportOptions,
    _overview_thumbnail,
    build_footer_lines,
    build_pdf,
)


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


def test_randlos_belegt_das_bild_exakt_den_zuschnitt():
    """Randlos heisst: kein Seitenrand. Der Markenstreifen bleibt trotzdem.

    Die Seite ist damit um STRIP_H_MM hoeher als das Objekt - das BILD aber belegt
    weiterhin exakt crop_w x crop_h Millimeter, und nur das ist die Zusage.
    """
    crop_w, crop_h = 700.0, 500.0
    options = ExportOptions(
        layout="single",
        page_margin_mm=0.0,
        show_scalebar=False,
        show_footer=False,
        show_grid=False,
    )
    result = build_pdf(dummy_image(crop_w, crop_h, dpi=150), crop_w, crop_h, options, FOOTER)

    assert result.image_rect_mm == pytest.approx((0.0, config.STRIP_H_MM, crop_w, crop_h))
    assert page_size_mm(result.data) == pytest.approx(
        (crop_w, crop_h + config.STRIP_H_MM), abs=0.01
    )


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


def test_klebeplan_zeigt_den_zuschnitt_als_bild():
    """Unter der Kachelung liegt das Bild, das gekachelt wird.

    Ohne das ist der Klebeplan ein leeres Gitter mit Nummern: er sagt, WIE VIELE
    Blaetter es gibt, aber nicht, welches man gerade in der Hand haelt.

    Geprueft wird am fertigen PDF und damit fuer BEIDE Erzeuger - ARUCO_PDF=js
    faehrt dieselbe Zeile durch web/pdf/build.js.
    """
    import pymupdf

    crop_w, crop_h = 700.0, 500.0
    options = ExportOptions(
        layout="tiles", page_format="A4", orientation="portrait", tile_overview=True
    )
    result = build_pdf(dummy_image(crop_w, crop_h, dpi=150), crop_w, crop_h, options, FOOTER)

    document = pymupdf.open(stream=result.data, filetype="pdf")
    images = document[0].get_images(full=True)
    assert len(images) == 1, f"Der Klebeplan traegt {len(images)} Bilder statt einem"

    # Der ganze Zuschnitt und nicht eine Kachel - das Seitenverhaeltnis verraet es.
    width_px, height_px = images[0][2], images[0][3]
    assert width_px / height_px == pytest.approx(crop_w / crop_h, rel=0.01)


def test_uebersichtsbild_ist_ein_daumennagel():
    """Das Bild im Klebeplan wird verkleinert - es wird angesehen, nicht gemessen.

    ReportLab kodiert bei jedem drawImage neu und teilt nichts mit den
    Kachelseiten. In voller Aufloesung steckte der Zuschnitt also ein zweites Mal
    in der Datei, fuer eine Handflaeche Papier.
    """
    big = dummy_image(700.0, 500.0, dpi=150)
    small = _overview_thumbnail(big)

    assert max(small.shape[:2]) == config.OVERVIEW_MAX_PX
    assert small.shape[1] / small.shape[0] == pytest.approx(
        big.shape[1] / big.shape[0], rel=0.01
    )
    # Was ohnehin klein genug ist, wird nicht angefasst - und schon gar nicht
    # hochgerechnet.
    assert _overview_thumbnail(small) is small


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
