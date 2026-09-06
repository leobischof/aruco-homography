"""Das Markenzeichen muss auf JEDEM Blatt stehen - und zwar nachweisbar.

Geprueft wird der Text ueber die PDF-Textextraktion (er ist echter Text, kein Bild)
und das Logo ueber seine Vektorzeichnung. Ein Blatt ohne Marke faellt hier auf,
egal ob es die Einzelseite, eine Kachel, der Klebeplan oder das Markerblatt ist.
"""

from __future__ import annotations

import io

import numpy as np
import pytest
from pypdf import PdfReader

from app import config
from app.pdf import branding
from app.pdf.build import ExportOptions, build_footer_lines, build_pdf
from app.pdf.markersheet import build_markersheet

FOOTER = build_footer_lines({"object_mm": "Test"})


def dummy_image(width_mm: float, height_mm: float, dpi: int = 150) -> np.ndarray:
    px_per_mm = dpi / config.MM_PER_INCH
    return np.full(
        (int(height_mm * px_per_mm), int(width_mm * px_per_mm), 3), 210, np.uint8
    )


def page_texts(data: bytes) -> list[str]:
    return [page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages]


def test_logo_laedt_als_vektorzeichnung():
    drawing = branding.logo_drawing(str(config.LOGO_INK_SVG), config.LOGO_MM)

    assert drawing.height == pytest.approx(config.LOGO_MM * config.PT_PER_MM, rel=1e-6)
    assert drawing.width > 0
    # Das Logo ist quadratisch; alles andere waere eine kaputte Skalierung.
    assert drawing.width == pytest.approx(drawing.height, rel=0.02)


def test_markenblock_passt_in_den_streifen():
    assert branding.block_width_mm() > config.LOGO_MM
    assert config.LOGO_MM < config.STRIP_H_MM


def test_einzelseite_traegt_die_herkunftszeile():
    result = build_pdf(dummy_image(200, 150), 200.0, 150.0, ExportOptions(), FOOTER)
    assert config.BRAND_CLAIM in page_texts(result.data)[0]
    assert config.BRAND_NAME in page_texts(result.data)[0]


def test_jede_kachel_und_der_klebeplan_tragen_die_marke():
    options = ExportOptions(layout="tiles", page_format="A4", tile_overview=True)
    result = build_pdf(dummy_image(700, 500), 700.0, 500.0, options, FOOTER)

    texts = page_texts(result.data)
    assert len(texts) == result.page_count > 2
    for index, text in enumerate(texts):
        assert config.BRAND_CLAIM in text, f"Seite {index + 1} ohne Herkunftszeile"


def test_markerblatt_traegt_die_marke():
    assert config.BRAND_CLAIM in page_texts(build_markersheet())[0]


def test_marke_bleibt_auch_ohne_aufdrucke():
    """Massstab und Fusszeile sind abschaltbar - die Marke nicht."""
    options = ExportOptions(show_scalebar=False, show_footer=False, show_grid=False)
    result = build_pdf(dummy_image(200, 150), 200.0, 150.0, options, FOOTER)

    text = page_texts(result.data)[0]
    assert config.BRAND_CLAIM in text
    assert "Kontrollmassstab" not in text


def page_link_targets(data: bytes, page_index: int = 0) -> list[str]:
    """URLs aller Link-Annotationen einer PDF-Seite."""
    page = PdfReader(io.BytesIO(data)).pages[page_index]
    targets = []
    for annotation in page.get("/Annots") or []:
        action = annotation.get_object().get("/A")
        if action is not None and "/URI" in action:
            targets.append(str(action["/URI"]))
    return targets


def test_markenblock_fuehrt_auf_die_website():
    result = build_pdf(dummy_image(200, 150), 200.0, 150.0, ExportOptions(), FOOTER)
    assert config.BRAND_URL in page_link_targets(result.data)


def test_auch_das_markerblatt_ist_verlinkt():
    assert config.BRAND_URL in page_link_targets(build_markersheet())


def test_schmale_seite_behaelt_wenigstens_das_logo():
    """Auf einer schmalen Seite entfaellt der Text, das Logo bleibt."""
    result = build_pdf(dummy_image(60, 60), 60.0, 60.0, ExportOptions(), FOOTER)

    assert config.BRAND_CLAIM not in page_texts(result.data)[0]
    assert len(result.data) > 2000  # Das Logo ist als Vektor trotzdem drin.
