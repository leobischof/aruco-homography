"""Kamerapose aus der Homographie: Hoehe, Lotpunkt, Neigung.

Gebraucht wird das fuer die Dickenkorrektur. Sie streckt radial vom LOTPUNKT der
Kamera aus - also muss man wissen, wo dieser Lotpunkt in der Ebene liegt und wie
hoch die Kamera darueber steht. Beides fallt aus der Zerlegung H = K [r1 r2 t]
heraus, sobald die Brennweite bekannt ist; die liefert normalerweise das EXIF.

Weg A (automatisch): Brennweite aus EXIF -> Zerlegung -> Hoehe und Lotpunkt.
Weg B (Fallback):    Kameraabstand wird eingetippt, Lotpunkt = Bildmitte.

Die Korrektur ist gegenueber der Hoehe unkritisch: bei h/d = 20/900 hinterlaesst
selbst ein 10-%-Fehler in d nur rund 0,2 % Restfehler.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app import config
from app.notices import AppError, NoticeList
from app.vision.geometry import project

# 35-mm-Aequivalent bezieht sich auf ein 36 x 24 mm grosses Bildfeld.
_FILM_WIDTH_MM = 36.0


@dataclass(frozen=True)
class CameraPose:
    """Woher die Brennweite kam und was sich daraus ergab."""

    source: str  # "exif" | "manual" | "none"
    focal_px: float | None
    height_mm: float | None
    nadir_mm: tuple[float, float] | None
    tilt_deg: float | None

    @property
    def usable_for_thickness(self) -> bool:
        return self.height_mm is not None and self.nadir_mm is not None


def focal_px_from_focal35(focal35_mm: float, width: int, height: int) -> float:
    """35-mm-Brennweite in Pixel-Brennweite umrechnen (orientierungsunabhaengig)."""
    return float(focal35_mm) / _FILM_WIDTH_MM * float(max(width, height))


def pose_from_homography(
    homography: np.ndarray, focal_px: float, width: int, height: int
) -> tuple[float, tuple[float, float], float]:
    """Zerlegt H in Rotation und Translation und liefert (Hoehe, Lotpunkt, Neigung).

    Rueckgabe in Ebenenkoordinaten (mm) bzw. Grad.
    """
    intrinsics = np.array(
        [[focal_px, 0.0, width / 2.0], [0.0, focal_px, height / 2.0], [0.0, 0.0, 1.0]]
    )
    normalized = np.linalg.inv(intrinsics) @ np.asarray(homography, dtype=np.float64)
    first, second, translation = normalized[:, 0], normalized[:, 1], normalized[:, 2]

    scale = 2.0 / (np.linalg.norm(first) + np.linalg.norm(second))
    first, second, translation = scale * first, scale * second, scale * translation
    if translation[2] < 0.0:  # Die Ebene muss vor der Kamera liegen.
        first, second, translation = -first, -second, -translation

    rotation = _orthonormalize(np.column_stack([first, second, np.cross(first, second)]))

    center = -rotation.T @ translation
    camera_height_mm = float(abs(center[2]))
    nadir_mm = (float(center[0]), float(center[1]))
    tilt_deg = float(np.degrees(np.arccos(min(1.0, abs(rotation[2, 2])))))
    return camera_height_mm, nadir_mm, tilt_deg


def _orthonormalize(matrix: np.ndarray) -> np.ndarray:
    """Naechstgelegene echte Rotationsmatrix (SVD, Determinante auf +1 gezwungen)."""
    u, _, vt = np.linalg.svd(matrix)
    rotation = u @ vt
    if np.linalg.det(rotation) < 0.0:
        u[:, -1] *= -1.0
        rotation = u @ vt
    return rotation


def resolve_pose(
    homography: np.ndarray,
    focal35_mm: float | None,
    width: int,
    height: int,
    thickness_mm: float,
    camera_height_override_mm: float | None,
    notices: NoticeList,
) -> CameraPose:
    """Pose bestimmen, mit Fallback-Kette und Klartext-Warnungen.

    Ist die Dicke 0, wird die Pose nur informativ berechnet: ein Fehlschlag darf
    dann nichts blockieren, weil ohne Hoehenversatz auch nichts zu korrigieren ist.
    """
    needs_correction = abs(thickness_mm) > 1e-9
    automatic = _try_automatic(homography, focal35_mm, width, height, notices)

    if automatic is not None:
        if camera_height_override_mm is None:
            return automatic
        # Ein ausdruecklich eingetippter Abstand schlaegt die Schaetzung.
        notices.info(
            "camera_height_override",
            f"Eingetippter Kameraabstand {camera_height_override_mm:.0f} mm benutzt "
            f"(EXIF-Schaetzung waere {automatic.height_mm:.0f} mm gewesen).",
        )
        return CameraPose(
            source="manual",
            focal_px=automatic.focal_px,
            height_mm=float(camera_height_override_mm),
            nadir_mm=automatic.nadir_mm,
            tilt_deg=automatic.tilt_deg,
        )

    if camera_height_override_mm is not None:
        return CameraPose(
            source="manual",
            focal_px=None,
            height_mm=float(camera_height_override_mm),
            nadir_mm=_image_center_in_plane(homography, width, height),
            tilt_deg=None,
        )

    if needs_correction:
        raise AppError(
            "camera_height_required",
            "Fuer die Dickenkorrektur fehlt der Kameraabstand: das Foto enthaelt keine "
            "brauchbare EXIF-Brennweite (typisch fuer weitergeleitete Bilder). Trage den "
            "Abstand Kamera-Blatt in mm ein oder setze die Objektdicke auf 0.",
            "camera_height_mm",
        )

    notices.info(
        "camera_pose_unknown",
        "Kamerahoehe unbekannt (keine EXIF-Brennweite). Ohne Objektdicke ist das ohne Folgen.",
    )
    return CameraPose(source="none", focal_px=None, height_mm=None, nadir_mm=None, tilt_deg=None)


def _try_automatic(
    homography: np.ndarray,
    focal35_mm: float | None,
    width: int,
    height: int,
    notices: NoticeList,
) -> CameraPose | None:
    """Weg A. Gibt None zurueck, wenn EXIF fehlt oder das Ergebnis unplausibel ist."""
    if focal35_mm is None:
        return None

    focal_px = focal_px_from_focal35(focal35_mm, width, height)
    camera_height_mm, nadir_mm, tilt_deg = pose_from_homography(
        homography, focal_px, width, height
    )

    if not (config.CAM_HEIGHT_MIN_MM <= camera_height_mm <= config.CAM_HEIGHT_MAX_MM):
        notices.warn(
            "camera_height_implausible",
            f"Aus EXIF und Homographie ergibt sich eine Kamerahoehe von "
            f"{camera_height_mm:.0f} mm - das ist unplausibel und wird verworfen.",
        )
        return None

    return CameraPose(
        source="exif",
        focal_px=focal_px,
        height_mm=camera_height_mm,
        nadir_mm=nadir_mm,
        tilt_deg=tilt_deg,
    )


def _image_center_in_plane(
    homography: np.ndarray, width: int, height: int
) -> tuple[float, float]:
    """Bildmitte in die Ebene zurueckprojizieren - der Lotpunkt-Ersatz fuer Weg B."""
    center = project(np.linalg.inv(homography), np.array([[width / 2.0, height / 2.0]]))[0]
    return (float(center[0]), float(center[1]))
