"""Dickenkorrektur: Hoehenversatz zwischen Markerebene und Objektoberflaeche.

Eine Homographie ist nur fuer GENAU EINE Ebene exakt. Liegt das Markerblatt neben
dem Objekt auf dem Tisch, waehrend die interessante Flaeche h Millimeter hoeher
liegt, erscheint diese Flaeche radial vom Kamera-Lotpunkt weg gestreckt:

    T = N + k * (Q - N)        mit  k = d / (d - h)

T ist die scheinbare Lage in der Markerebene, Q die wahre Lage auf der
Objektoberflaeche, N der Lotpunkt, d die Kamerahoehe. Die Ruecktransformation ist
eine Skalierung um N mit 1/k; sie wird als Vorschaltmatrix in die Homographie
gefaltet, damit das Rasterbild direkt in wahren Objektkoordinaten entsteht.
"""

from __future__ import annotations

import numpy as np

from app.notices import AppError
from app.vision.camera import CameraPose


def correction_matrix(
    nadir_mm: tuple[float, float], camera_height_mm: float, thickness_mm: float
) -> np.ndarray:
    """Affine 3x3-Matrix, die wahre Objektkoordinaten auf ihre scheinbare Lage abbildet."""
    if abs(thickness_mm) < 1e-9:
        return np.eye(3)
    if camera_height_mm <= thickness_mm:
        raise AppError(
            "thickness_too_large",
            "thickness_mm",
            thickness_mm=f"{thickness_mm:.1f}",
            camera_height_mm=f"{camera_height_mm:.0f}",
        )

    factor = camera_height_mm / (camera_height_mm - thickness_mm)
    nadir_x, nadir_y = nadir_mm
    return np.array(
        [
            [factor, 0.0, nadir_x * (1.0 - factor)],
            [0.0, factor, nadir_y * (1.0 - factor)],
            [0.0, 0.0, 1.0],
        ]
    )


def effective_homography(
    homography: np.ndarray, pose: CameraPose, thickness_mm: float
) -> tuple[np.ndarray, float]:
    """Liefert (H_eff, k). Ohne Dicke ist H_eff = H und k = 1."""
    if abs(thickness_mm) < 1e-9:
        return np.asarray(homography, dtype=np.float64), 1.0

    if not pose.usable_for_thickness:
        raise AppError("camera_height_required", "camera_height_mm")

    assert pose.nadir_mm is not None and pose.height_mm is not None  # von usable_for_thickness
    correction = correction_matrix(pose.nadir_mm, pose.height_mm, thickness_mm)
    factor = pose.height_mm / (pose.height_mm - thickness_mm)
    return np.asarray(homography, dtype=np.float64) @ correction, float(factor)
