"""Das Markerblatt - Ursprung des Massstabs, also selbst geprueft."""

from __future__ import annotations

import io

import pytest
from pypdf import PdfReader

from app import config
from app.pdf.markersheet import build_markersheet, sheet_layout

QUIET_ZONE_MIN_MM = 8.0


def test_layout_entspricht_den_konfigurierten_mittelpunkten():
    sheet_h = config.SHEET_MM[1]
    layout = sheet_layout(config.MARKER_MM_NOMINAL)

    for marker_id, (cx, cy) in config.SHEET_MARKER_CENTERS_MM.items():
        rect = layout[marker_id]
        assert rect.x + rect.width / 2.0 == pytest.approx(cx, abs=1e-9)
        # y kommt von unten, die Konfiguration zaehlt von oben.
        assert rect.y + rect.height / 2.0 == pytest.approx(sheet_h - cy, abs=1e-9)
        assert rect.width == rect.height == config.MARKER_MM_NOMINAL


def test_alle_marker_liegen_mit_ruhezone_auf_dem_blatt():
    sheet_w, sheet_h = config.SHEET_MM
    for rect in sheet_layout().values():
        assert rect.x >= QUIET_ZONE_MIN_MM
        assert rect.y >= QUIET_ZONE_MIN_MM
        assert rect.x + rect.width <= sheet_w - QUIET_ZONE_MIN_MM
        assert rect.y + rect.height <= sheet_h - QUIET_ZONE_MIN_MM


def test_marker_ueberlappen_einander_nicht():
    rects = list(sheet_layout().values())
    for index, first in enumerate(rects):
        for second in rects[index + 1 :]:
            disjoint = (
                first.x + first.width <= second.x
                or second.x + second.width <= first.x
                or first.y + first.height <= second.y
                or second.y + second.height <= first.y
            )
            assert disjoint


def test_abstaende_steuern_das_layout():
    """Markergroesse und Abstaende sind unabhaengig einstellbar - beide gemessen."""
    layout = sheet_layout(60.0, (100.0, 150.0))

    assert layout[0].width == layout[0].height == pytest.approx(60.0)
    centre = lambda rect: (rect.x + rect.width / 2.0, rect.y + rect.height / 2.0)  # noqa: E731
    assert centre(layout[1])[0] - centre(layout[0])[0] == pytest.approx(100.0)
    assert centre(layout[0])[1] - centre(layout[2])[1] == pytest.approx(150.0)


def test_standardlayout_hat_die_gemessenen_masse():
    """Die Vorgabe entspricht dem real vermessenen Blatt: 67 mm, 121 x 171 mm."""
    assert config.MARKER_MM_NOMINAL == pytest.approx(67.0)
    assert config.SHEET_SPACING_MM == pytest.approx((121.0, 171.0))

    sheet_w, sheet_h = config.SHEET_MM
    assert config.MARKER_MM_NOMINAL + config.SHEET_SPACING_MM[0] <= sheet_w
    assert config.MARKER_MM_NOMINAL + config.SHEET_SPACING_MM[1] <= sheet_h


def test_pdf_ist_a4_und_enthaelt_eine_seite():
    reader = PdfReader(io.BytesIO(build_markersheet()))
    assert len(reader.pages) == 1

    box = reader.pages[0].mediabox
    assert float(box.width) / config.PT_PER_MM == pytest.approx(config.SHEET_MM[0], abs=0.01)
    assert float(box.height) / config.PT_PER_MM == pytest.approx(config.SHEET_MM[1], abs=0.01)
