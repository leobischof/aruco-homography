"""Belegt, dass der Umzug der Konstanten nach shared/ keine Zahl veraendert hat.

Die Werte hier sind mit der Hand aus app/config.py von vor dem Umzug uebernommen.
Wer eine Konstante absichtlich aendert, aendert sie HIER mit - und sieht dabei,
dass er sie aendert. Genau das ist der Zweck.
"""

from __future__ import annotations

from app import config

# Vor dem Umzug aus app/config.py abgelesen. Nicht generiert - abgeschrieben.
FROZEN = {
    "ARUCO_DICT_NAME": "DICT_4X4_50",
    "MARKER_MM_NOMINAL": 67.0,
    "SHEET_MM": (210.0, 297.0),
    "SHEET_SPACING_MM": (121.0, 171.0),
    "SHEET_MARKER_IDS": (0, 1, 2, 3),
    "DPI_DEFAULT": 300,
    "DPI_CHOICES": (150, 200, 300, 400, 600),
    "MAX_OUTPUT_MPX": 300.0,
    "MAX_UPLOAD_MB": 60,
    "PREVIEW_MAX_PX": 1600,
    "DEFAULT_CROP_MAX_MM": 1500.0,
    "JPEG_QUALITY": 92,
    "RMS_WARN_PX": 2.0,
    "RMS_WARN_MM": 1.0,
    "MARKER_SIZE_DEV_WARN": 0.02,
    "MARKER_ROT_WARN_DEG": 2.0,
    "EXTRAPOLATION_WARN_FRAC": 0.25,
    "COLLINEARITY_WARN": 0.05,
    "CAM_HEIGHT_MIN_MM": 100.0,
    "CAM_HEIGHT_MAX_MM": 10000.0,
    "HORIZON_EPS": 0.02,
    "EXTENT_HULL_FACTOR": 3.0,
    "LAYOUT_DEFAULT": "tiles",
    "PAGE_MARGIN_MM_DEFAULT": 5.0,
    "PRINTER_MARGIN_MM_DEFAULT": 5.0,
    "TILE_OVERLAP_MM_DEFAULT": 10.0,
    "TILE_OVERVIEW_DEFAULT": True,
    "OVERVIEW_MAX_PX": 1600,
    "STRIP_H_MM": 18.0,
    "GRID_STEP_MM": 50.0,
    "GRID_LINE_PT": 0.5,
    "GRID_HALO_PT": 1.5,
    "GRID_LABEL_PT": 6.5,
    "SCALEBAR_MM": 100.0,
    "CONTOUR_LINE_MM": 0.25,
    "CONTOUR_EPS_MM": 0.5,
    "CONTOUR_MIN_AREA_FRAC": 0.05,
    "SHEET_FORMATS": {"A4": (210.0, 297.0), "A3": (297.0, 420.0)},
    "BRAND_NAME": "Bischof Snowboards",
    "BRAND_CLAIM": "Made with Bischof Snowboards Software",
    "BRAND_URL": "https://bischof-snowboards.com",
    "BRAND_INK": "#334155",
    "BRAND_PRIMARY": "#379992",
    "BRAND_ACTION": "#ffbf00",
    "BRAND_DARK": "#25242b",
    "BRAND_LIGHT": "#f1f5f9",
    "BRAND_SECONDARY": "#e2e8f0",
    "BRAND_ACCENT": "#f0f3f3",
    "BRAND_DESTRUCTIVE": "#e7000b",
    "LOGO_MM": 11.0,
    "ADJUST_CLAHE_TILES": 8,
    "ADJUST_CLAHE_CLIP_MAX": 4.0,
    "ADJUST_UNSHARP_SIGMA_PX": 2.0,
    "ADJUST_UNSHARP_MAX": 2.0,
    "ADJUST_EDGE_CANNY": (60, 160),
    "ADJUST_EMPHASIS_SIGMA_DEG": 25.0,
    "ADJUST_EMPHASIS_HUES": {
        "red": 0, "yellow": 22, "green": 60, "cyan": 90, "blue": 120, "magenta": 150,
    },
    "SUPPORTED_LOCALES": ("de", "en"),
    "DEFAULT_LOCALE": "de",
    "MM_PER_INCH": 25.4,
}


def test_konstanten_haben_sich_nicht_veraendert():
    """Jeder Wert ist noch der, der er vor dem Umzug war."""
    for name, expected in FROZEN.items():
        actual = getattr(config, name)
        assert actual == expected, f"{name}: {actual!r} statt {expected!r}"


def test_abgeleitete_werte_stimmen_weiter():
    """Was aus den Konstanten berechnet wird, rechnet danach noch dasselbe."""
    assert config.BRAND_COPYRIGHT == "Copyright (C) Bischof Snowboards"
    assert config.PT_PER_MM == 72.0 / 25.4
    assert config.GRID_INK == config.BRAND_INK
    assert config.SHEET_MARKER_CENTERS_MM == {
        0: (44.5, 63.0), 1: (165.5, 63.0), 2: (44.5, 234.0), 3: (165.5, 234.0),
    }
