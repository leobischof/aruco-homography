"""Welcher Teil der Ebene ist ueberhaupt abbildbar - und wie weit extrapoliert man?

Bei schraeger Aufnahme laeuft ein Teil des Bildes gegen den Horizont der
Homographie: dort bildet die Ruecktransformation ins Unendliche ab. Ohne Clipping
kaeme ein Extent von mehreren Kilometern heraus. Deshalb wird das Bildrechteck erst
an der Horizontlinie beschnitten und dann zurueckprojiziert.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app import config
from app.vision.geometry import (
    clip_polygon_halfplane,
    convex_intersection_area,
    project,
    rect_polygon,
)


@dataclass(frozen=True)
class Extent:
    """Achsparalleler Bereich in Ebenen-Millimetern."""

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def as_dict(self) -> dict[str, float]:
        return {"x0": self.x0, "y0": self.y0, "x1": self.x1, "y1": self.y1}

    def clamped_to(self, other: "Extent") -> "Extent":
        return Extent(
            max(self.x0, other.x0),
            max(self.y0, other.y0),
            min(self.x1, other.x1),
            min(self.y1, other.y1),
        )


def plane_extent(
    homography: np.ndarray, width: int, height: int, hull_mm: np.ndarray
) -> Extent:
    """Bounding-Box des abbildbaren Ebenenbereichs, horizontsicher und geklammert."""
    inverse = np.linalg.inv(np.asarray(homography, dtype=np.float64))
    a, b, c = inverse[2, 0], inverse[2, 1], inverse[2, 2]

    # Referenzvorzeichen dort bestimmen, wo die Marker liegen - dieser Teil des
    # Bildes ist garantiert die "richtige" Seite des Horizonts.
    hull_centroid = hull_mm.mean(axis=0)
    reference_px = project(homography, hull_centroid.reshape(1, 2))[0]
    reference_w = a * reference_px[0] + b * reference_px[1] + c
    sign = 1.0 if reference_w >= 0.0 else -1.0
    epsilon = config.HORIZON_EPS * abs(reference_w)

    visible = clip_polygon_halfplane(
        rect_polygon(0.0, 0.0, float(width), float(height)),
        (sign * a, sign * b, sign * c),
        eps=epsilon,
    )
    if len(visible) < 3:  # Kein brauchbarer Bereich: auf die Marker zurueckfallen.
        return _hull_clamp(hull_mm)

    mapped = project(inverse, visible)
    finite = mapped[np.isfinite(mapped).all(axis=1)]
    if len(finite) < 3:
        return _hull_clamp(hull_mm)

    candidate = Extent(
        float(finite[:, 0].min()),
        float(finite[:, 1].min()),
        float(finite[:, 0].max()),
        float(finite[:, 1].max()),
    )
    return candidate.clamped_to(_hull_clamp(hull_mm))


def _hull_clamp(hull_mm: np.ndarray) -> Extent:
    """Die Marker-Huelle, aufgeweitet um EXTENT_HULL_FACTOR mal ihre Diagonale."""
    x_min, y_min = hull_mm.min(axis=0)
    x_max, y_max = hull_mm.max(axis=0)
    diagonal = float(np.hypot(x_max - x_min, y_max - y_min))
    pad = config.EXTENT_HULL_FACTOR * max(diagonal, 1.0)
    return Extent(
        float(x_min) - pad, float(y_min) - pad, float(x_max) + pad, float(y_max) + pad
    )


def default_crop(extent: Extent, hull_mm: np.ndarray) -> Extent:
    """Startvorschlag fuer den Zuschnitt: der Extent, um den Huellschwerpunkt begrenzt."""
    limit = config.DEFAULT_CROP_MAX_MM
    center_x, center_y = hull_mm.mean(axis=0)
    around_hull = Extent(
        float(center_x) - limit / 2.0,
        float(center_y) - limit / 2.0,
        float(center_x) + limit / 2.0,
        float(center_y) + limit / 2.0,
    )
    return extent.clamped_to(around_hull)


def extrapolation_fraction(crop: Extent, hull_mm: np.ndarray) -> float:
    """Flaechenanteil des Zuschnitts ausserhalb der konvexen Marker-Huelle (0..1).

    Genau dort ist die Homographie am unzuverlaessigsten: sie wird ueber den
    gemessenen Bereich hinaus fortgeschrieben, und Objektivverzeichnung schlaegt
    ungebremst durch.
    """
    crop_polygon = rect_polygon(crop.x0, crop.y0, crop.x1, crop.y1)
    crop_area = crop.width * crop.height
    if crop_area <= 0.0:
        return 0.0
    inside = convex_intersection_area(crop_polygon, hull_mm)
    return float(min(1.0, max(0.0, 1.0 - inside / crop_area)))
