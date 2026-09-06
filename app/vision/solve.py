"""Homographie Ebene (mm) -> Bild (px) aus erkannten Markern bestimmen.

Zwei Modi, beide enden in derselben nichtlinearen Ausgleichsrechnung:

  Blatt-Modus - die Markerpositionen auf dem A4-Blatt sind bekannt. Alle erkannten
    Ecken sind damit Referenzpunkte; das ist der genaueste Weg.

  Frei-Modus  - nur die Markergroesse ist bekannt. Homographie UND Markerpositionen
    werden gemeinsam geschaetzt: 8 + 2*(n-1) Unbekannte gegen 8*n Gleichungen.
    Vorausgesetzt wird, dass alle Marker gleich ausgerichtet gedruckt sind; genau
    das prueft _rotation_deviation und warnt sonst.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from scipy.optimize import least_squares

from app import config
from app.notices import AppError, NoticeList
from app.vision.detect import DetectedMarker
from app.vision.geometry import convex_hull, local_px_per_mm, polygon_area, project

# Einheitsquadrat in der Reihenfolge, die cv2.aruco fuer die Ecken liefert.
_UNIT_CORNERS = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])


@dataclass(frozen=True)
class MarkerFit:
    """Ein Marker nach dem Ausgleich: wohin er in der Ebene gehoert und wie gut er passt."""

    marker_id: int
    corners_px: np.ndarray
    plane_mm: np.ndarray
    residual_px: float
    side_mm_measured: float
    rotation_deg: float


@dataclass(frozen=True)
class Solution:
    """Ergebnis des Ausgleichs samt allem, was der Qualitaetsbericht braucht."""

    homography: np.ndarray
    mode: str
    markers: list[MarkerFit]
    rms_px: float
    hull_mm: np.ndarray
    px_per_mm: float

    @property
    def mm_per_px(self) -> float:
        return 1.0 / self.px_per_mm if self.px_per_mm else float("inf")

    @property
    def rms_mm(self) -> float:
        return self.rms_px * self.mm_per_px


def marker_plane_corners(center_x: float, center_y: float, side_mm: float) -> np.ndarray:
    """Die vier Ebenenecken eines achsparallelen Markers (TL, TR, BR, BL)."""
    half = side_mm / 2.0
    return np.array(
        [
            [center_x - half, center_y - half],
            [center_x + half, center_y - half],
            [center_x + half, center_y + half],
            [center_x - half, center_y + half],
        ]
    )


def sheet_plane_corners(
    marker_mm: float, spacing_mm: tuple[float, float] | None = None
) -> dict[int, np.ndarray]:
    """Sollpositionen der Blatt-Marker aus den GEMESSENEN Blattmassen.

    Es wird nichts hochgerechnet: Markergroesse und die beiden Mittelpunktabstaende
    kommen so, wie sie am Ausdruck gemessen wurden. Damit faellt eine etwaige
    Druckerskalierung heraus, ohne dass irgendwo ein versteckter Faktor sitzt.
    """
    centers = config.sheet_marker_centers(spacing_mm or config.SHEET_SPACING_MM)
    return {
        marker_id: marker_plane_corners(cx, cy, marker_mm)
        for marker_id, (cx, cy) in centers.items()
    }


def solve(
    markers: list[DetectedMarker],
    marker_mm: float,
    mode: str,
    notices: NoticeList,
    spacing_mm: tuple[float, float] | None = None,
) -> Solution:
    """Einstiegspunkt: Modus waehlen, loesen, Qualitaet bewerten."""
    if not markers:
        raise AppError(
            "no_markers",
            "Es wurde kein ArUco-Marker gefunden. Pruefe Schaerfe, Beleuchtung und ob das "
            "Markerblatt vollstaendig im Bild ist.",
        )
    if marker_mm <= 0.0:
        raise AppError("bad_marker_size", "Die Markergroesse muss groesser als 0 sein.", "marker_mm")

    if mode == "sheet":
        homography, plane_by_id = _solve_sheet(markers, marker_mm, spacing_mm)
    elif mode == "free":
        homography, plane_by_id = _solve_free(markers, marker_mm)
    else:
        raise AppError("bad_mode", f"Unbekannter Modus: {mode}", "mode")

    used = [m for m in markers if m.marker_id in plane_by_id]
    return _finalize(homography, plane_by_id, used, marker_mm, mode, notices)


def _solve_sheet(
    markers: list[DetectedMarker],
    marker_mm: float,
    spacing_mm: tuple[float, float] | None = None,
) -> tuple[np.ndarray, dict[int, np.ndarray]]:
    layout = sheet_plane_corners(marker_mm, spacing_mm)
    usable = [m for m in markers if m.marker_id in layout]
    if not usable:
        found = ", ".join(str(m.marker_id) for m in markers)
        raise AppError(
            "no_sheet_ids",
            f"Erkannt wurden nur die Marker-IDs {found}. Das mitgelieferte Blatt benutzt "
            f"{', '.join(str(i) for i in config.SHEET_MARKER_IDS)}. Wechsle in den Frei-Modus "
            "oder drucke das Markerblatt der App.",
            "mode",
        )

    plane_by_id = {m.marker_id: layout[m.marker_id] for m in usable}
    plane_pts = np.vstack([plane_by_id[m.marker_id] for m in usable])
    image_pts = np.vstack([m.corners_px for m in usable])

    if len(usable) == 1:
        # Vier Punkte: exakt bestimmt, LMEDS braucht mehr. Kein Ausgleich moeglich.
        homography = cv2.getPerspectiveTransform(
            plane_pts.astype(np.float32), image_pts.astype(np.float32)
        )
    else:
        homography, _ = cv2.findHomography(plane_pts, image_pts, method=cv2.LMEDS)
        if homography is None:
            raise AppError(
                "homography_failed",
                "Aus den erkannten Markern liess sich keine Homographie berechnen. "
                "Liegen sie fast auf einer Linie?",
            )

    return _refine_homography(homography, plane_pts, image_pts), plane_by_id


def _solve_free(
    markers: list[DetectedMarker], marker_mm: float
) -> tuple[np.ndarray, dict[int, np.ndarray]]:
    ordered = sorted(markers, key=lambda m: m.image_area_px, reverse=True)
    anchor, others = ordered[0], ordered[1:]
    image_pts = np.vstack([m.corners_px for m in ordered])

    # Startwert: der groesste Marker definiert Ursprung und Massstab der Ebene.
    anchor_plane = _UNIT_CORNERS * marker_mm
    homography = cv2.getPerspectiveTransform(
        anchor_plane.astype(np.float32), anchor.corners_px.astype(np.float32)
    )

    inverse = np.linalg.inv(homography)
    offsets = []
    for marker in others:
        plane_quad = project(inverse, marker.corners_px)
        offsets.append(plane_quad.mean(axis=0) - marker_mm / 2.0)
    offsets_array = np.array(offsets).reshape(-1, 2) if offsets else np.zeros((0, 2))

    def plane_points(offset_values: np.ndarray) -> np.ndarray:
        quads = [anchor_plane]
        for offset in offset_values.reshape(-1, 2):
            quads.append(_UNIT_CORNERS * marker_mm + offset)
        return np.vstack(quads)

    def residual(params: np.ndarray) -> np.ndarray:
        matrix = np.append(params[:8], 1.0).reshape(3, 3)
        return (project(matrix, plane_points(params[8:])) - image_pts).ravel()

    start = np.concatenate([_as_eight(homography), offsets_array.ravel()])
    fitted = least_squares(residual, start, method="trf", xtol=1e-14, ftol=1e-14, gtol=1e-14)

    solved = np.append(fitted.x[:8], 1.0).reshape(3, 3)
    final_offsets = fitted.x[8:].reshape(-1, 2)

    plane_by_id = {anchor.marker_id: anchor_plane}
    for marker, offset in zip(others, final_offsets):
        plane_by_id[marker.marker_id] = _UNIT_CORNERS * marker_mm + offset
    return solved, plane_by_id


def _refine_homography(
    homography: np.ndarray, plane_pts: np.ndarray, image_pts: np.ndarray
) -> np.ndarray:
    """Nichtlinearer Ausgleich des Reprojektionsfehlers ueber die 8 freien Parameter."""

    def residual(params: np.ndarray) -> np.ndarray:
        matrix = np.append(params, 1.0).reshape(3, 3)
        return (project(matrix, plane_pts) - image_pts).ravel()

    fitted = least_squares(
        residual, _as_eight(homography), method="trf", xtol=1e-14, ftol=1e-14, gtol=1e-14
    )
    return np.append(fitted.x, 1.0).reshape(3, 3)


def _as_eight(homography: np.ndarray) -> np.ndarray:
    """Homographie auf H[2,2] = 1 normieren und die 8 freien Parameter zurueckgeben."""
    matrix = np.asarray(homography, dtype=np.float64)
    if abs(matrix[2, 2]) < 1e-15:
        raise AppError("homography_degenerate", "Die Homographie ist entartet (H[2,2] = 0).")
    return (matrix / matrix[2, 2]).ravel()[:8]


def _finalize(
    homography: np.ndarray,
    plane_by_id: dict[int, np.ndarray],
    markers: list[DetectedMarker],
    marker_mm: float,
    mode: str,
    notices: NoticeList,
) -> Solution:
    inverse = np.linalg.inv(homography)
    fits: list[MarkerFit] = []
    squared_errors: list[float] = []

    for marker in markers:
        plane = plane_by_id[marker.marker_id]
        reprojected = project(homography, plane)
        errors = np.linalg.norm(reprojected - marker.corners_px, axis=1)
        squared_errors.extend((errors**2).tolist())

        measured_quad = project(inverse, marker.corners_px)
        fits.append(
            MarkerFit(
                marker_id=marker.marker_id,
                corners_px=marker.corners_px,
                plane_mm=plane,
                residual_px=float(np.sqrt(np.mean(errors**2))),
                side_mm_measured=_mean_side_length(measured_quad),
                rotation_deg=_rotation_deviation(measured_quad),
            )
        )

    rms_px = float(np.sqrt(np.mean(squared_errors))) if squared_errors else 0.0
    hull = convex_hull(np.vstack([f.plane_mm for f in fits]))
    px_per_mm = local_px_per_mm(homography, hull.mean(axis=0))

    solution = Solution(
        homography=homography,
        mode=mode,
        markers=fits,
        rms_px=rms_px,
        hull_mm=hull,
        px_per_mm=px_per_mm,
    )
    _add_quality_notices(solution, marker_mm, notices)
    return solution


def _mean_side_length(quad: np.ndarray) -> float:
    """Mittlere Kantenlaenge eines zurueckprojizierten Markers, in mm."""
    edges = np.linalg.norm(np.roll(quad, -1, axis=0) - quad, axis=1)
    return float(edges.mean())


def _rotation_deviation(quad: np.ndarray) -> float:
    """Abweichung der Markerausrichtung von der Achsparallelitaet, in Grad (-45..45)."""
    edge = quad[1] - quad[0]
    angle = np.degrees(np.arctan2(edge[1], edge[0]))
    return float(((angle + 45.0) % 90.0) - 45.0)


def _add_quality_notices(solution: Solution, marker_mm: float, notices: NoticeList) -> None:
    """Alle Warnungen aus Spec 3.7 erzeugen - keine bricht ab, jede wird sichtbar."""
    if len(solution.markers) == 1:
        notices.warn(
            "single_marker",
            "Nur ein Marker erkannt: die Homographie ist damit exakt bestimmt, aber ohne "
            "jede Redundanz - ein Fehlermass laesst sich nicht angeben.",
        )

    # Kollinearitaet an den MITTELPUNKTEN messen, nicht an der Eckenhuelle: jeder
    # Marker bringt selbst 67 mm Ausdehnung mit, sodass drei Marker in einer Reihe
    # eine voellig unauffaellige Eckenhuelle ergeben - und die Warnung nie kaeme.
    centres = np.array([fit.plane_mm.mean(axis=0) for fit in solution.markers])
    if len(centres) >= 2:
        spread = polygon_area(convex_hull(centres)) if len(centres) >= 3 else 0.0
        span = max(
            float(np.linalg.norm(a - b)) for a in centres for b in centres
        )
        if span > 0.0 and spread / (span * span) < config.COLLINEARITY_WARN:
            notices.warn(
                "collinear_markers",
                "Die Marker liegen fast auf einer Linie. Quer dazu stuetzt sich die "
                "Homographie kaum ab und wird dort unzuverlaessig; verteile die Marker "
                "flaechig.",
            )

    if solution.rms_px > config.RMS_WARN_PX or solution.rms_mm > config.RMS_WARN_MM:
        notices.warn(
            "high_residual",
            f"Restfehler {solution.rms_px:.2f} px ({solution.rms_mm:.2f} mm) ueber der Schwelle. "
            "Ursachen: Objektivverzeichnung, unscharfes Foto oder ein nicht ebenes Markerblatt.",
        )

    for fit in solution.markers:
        deviation = abs(fit.side_mm_measured - marker_mm) / marker_mm
        if deviation > config.MARKER_SIZE_DEV_WARN:
            notices.warn(
                "marker_size_deviation",
                f"Marker {fit.marker_id} misst zurueckgerechnet {fit.side_mm_measured:.1f} mm "
                f"statt {marker_mm:.1f} mm ({deviation * 100:.1f} % Abweichung).",
            )

    if solution.mode == "free":
        reference = solution.markers[0].rotation_deg
        for fit in solution.markers[1:]:
            if abs(fit.rotation_deg - reference) > config.MARKER_ROT_WARN_DEG:
                notices.warn(
                    "marker_rotation",
                    f"Marker {fit.marker_id} ist gegenueber dem Ankermarker um "
                    f"{abs(fit.rotation_deg - reference):.1f} Grad verdreht. Der Frei-Modus "
                    "setzt gleich ausgerichtete Marker voraus.",
                )
