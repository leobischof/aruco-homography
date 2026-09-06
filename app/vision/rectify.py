"""Entzerren in ein exaktes Millimeter-Raster.

Der Kniff steckt im halben Pixel: die Abbildung Ausgabepixel -> mm setzt die
Pixelmitten auf x0 + (u + 0.5)/spp. Dadurch fallen die AUSSENKANTEN des Rasters
exakt auf die Zuschnittgrenzen, und das Bild belegt im PDF hinterher genau
crop_w x crop_h Millimeter. Ohne diesen Versatz waere alles um ein halbes Pixel
verschoben - bei 300 dpi 0,042 mm, aber es ist umsonst zu haben.
"""

from __future__ import annotations

import cv2
import numpy as np

from app import config
from app.notices import AppError
from app.vision.extent import Extent


def output_size(crop: Extent, px_per_mm: float) -> tuple[int, int]:
    """Rastergroesse in Pixeln fuer einen Zuschnitt bei gegebener Aufloesung."""
    return (
        max(1, int(round(crop.width * px_per_mm))),
        max(1, int(round(crop.height * px_per_mm))),
    )


def px_per_mm_for_dpi(dpi: float) -> float:
    return float(dpi) / config.MM_PER_INCH


def check_output_budget(crop: Extent, dpi: int) -> None:
    """Bricht ab, wenn das Rasterbild die Speichergrenze sprengt - mit brauchbarem Vorschlag."""
    width, height = output_size(crop, px_per_mm_for_dpi(dpi))
    megapixels = width * height / 1e6
    if megapixels <= config.MAX_OUTPUT_MPX:
        return

    affordable = [
        choice
        for choice in config.DPI_CHOICES
        if _megapixels(crop, choice) <= config.MAX_OUTPUT_MPX
    ]
    hint = (
        f"Mit {max(affordable)} dpi passt es."
        if affordable
        else f"Auch {min(config.DPI_CHOICES)} dpi reicht nicht - verkleinere den Zuschnitt."
    )
    raise AppError(
        "output_too_large",
        f"Das Ergebnis waere {width} x {height} Pixel ({megapixels:.0f} MPixel) gross, "
        f"erlaubt sind {config.MAX_OUTPUT_MPX:.0f} MPixel. {hint}",
        "dpi",
    )


def _megapixels(crop: Extent, dpi: int) -> float:
    width, height = output_size(crop, px_per_mm_for_dpi(dpi))
    return width * height / 1e6


def rectify(
    image_bgr: np.ndarray,
    homography: np.ndarray,
    crop: Extent,
    px_per_mm: float,
    source_px_per_mm: float | None = None,
) -> np.ndarray:
    """Entzerrt den Zuschnitt in ein Raster mit exakt px_per_mm Pixeln je Millimeter."""
    width, height = output_size(crop, px_per_mm)
    scale_matrix = _output_to_plane(crop, px_per_mm)
    total = np.asarray(homography, dtype=np.float64) @ scale_matrix

    interpolation = _interpolation_for(px_per_mm, source_px_per_mm)
    return cv2.warpPerspective(
        image_bgr,
        total,
        (width, height),
        flags=interpolation | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )


def _output_to_plane(crop: Extent, px_per_mm: float) -> np.ndarray:
    """Ausgabepixel -> Ebenen-mm, mit Pixelmitten-Versatz (siehe Modulkommentar)."""
    step = 1.0 / px_per_mm
    return np.array(
        [
            [step, 0.0, crop.x0 + step / 2.0],
            [0.0, step, crop.y0 + step / 2.0],
            [0.0, 0.0, 1.0],
        ]
    )


def _interpolation_for(px_per_mm: float, source_px_per_mm: float | None) -> int:
    """INTER_AREA beim Verkleinern (vermeidet Aliasing), sonst Lanczos."""
    if source_px_per_mm and px_per_mm < 0.9 * source_px_per_mm:
        return cv2.INTER_AREA
    return cv2.INTER_LANCZOS4


def preview_px_per_mm(extent: Extent) -> float:
    """Aufloesung, bei der die Vorschau gerade noch unter PREVIEW_MAX_PX bleibt."""
    longest_mm = max(extent.width, extent.height, 1e-6)
    return float(config.PREVIEW_MAX_PX) / longest_mm
