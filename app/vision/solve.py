"""Homographie Ebene (mm) -> Bild (px) aus erkannten Markern bestimmen.

Drei Modi, alle enden in derselben nichtlinearen Ausgleichsrechnung:

  Blatt-Modus - die Markerpositionen auf dem A4-Blatt sind bekannt. Alle erkannten
    Ecken sind damit Referenzpunkte; das ist der genaueste Weg.

  Frei-Modus  - nur die Markergroesse ist bekannt. Homographie UND Markerpositionen
    werden gemeinsam geschaetzt: 8 + 2*(n-1) Unbekannte gegen 8*n Gleichungen.
    Vorausgesetzt wird, dass alle Marker gleich ausgerichtet gedruckt sind; genau
    das prueft _rotation_deviation und warnt sonst.

  Streu-Modus - dieselbe Rechnung mit einer Unbekannten mehr je Marker: der
    Drehung. 8 + 3*(n-1) gegen 8*n. Damit darf jeder Marker liegen, wie er faellt.
    Zwei Dinge folgen daraus:

      * Es gibt keinen ausgezeichneten Marker mehr, an dem sich die Ebene
        ausrichten liesse - der groesste liegt ja in einem zufaelligen Winkel.
        Also richtet sich die Ebene nach dem FOTO (siehe _oriented_to_photo).
      * Jeder weitere Marker bringt fuenf Bestimmungsstuecke netto ein statt
        sechs. Der Frei-Modus bleibt deshalb der genauere, wenn seine Annahme
        stimmt - er ist kein ueberholter Vorlaeufer, sondern der engere Fall.

**Ein einzelner Marker reicht in jedem Modus.** Vier Punktpaare bestimmen eine
Homographie exakt; der Marker traegt sein Koordinatensystem selbst, in der
festen Eckenreihenfolge. Was er nicht traegt, ist eine Probe - das Residuum ist
dann null, ohne dass der Fehler klein waere. Dafuer gibt es single_marker.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from scipy.optimize import least_squares

from app import config
from app.notices import AppError, NoticeList
from app.vision import backend
from app.vision.detect import DetectedMarker
from app.vision.geometry import convex_hull, local_px_per_mm, polygon_area, project

# Einheitsquadrat in der Reihenfolge, die cv2.aruco fuer die Ecken liefert.
_UNIT_CORNERS = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])

# Dieselben vier Ecken, aber relativ zum MITTELPUNKT. Der Streu-Modus dreht um
# den Mittelpunkt und nicht um die obere linke Ecke; nur so bleibt eine Drehung
# eine Drehung und wird nicht zugleich eine Verschiebung.
_CENTRED_CORNERS = _UNIT_CORNERS - 0.5


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


def marker_plane_corners_at(poses: np.ndarray, side_mm: float) -> np.ndarray:
    """Lagen (M,3) = (x, y, Winkel) -> Ebenenecken (M,4,2), TL, TR, BR, BL.

    Das Gegenstueck zu marker_plane_corners fuer gedrehte Marker. Der Winkel
    steht im Bogenmass und dreht gegen den Uhrzeigersinn in Ebenenkoordinaten;
    `theta == 0` liefert genau dieselben Ecken wie marker_plane_corners.
    """
    values = np.asarray(poses, dtype=np.float64).reshape(-1, 3)
    cos_t = np.cos(values[:, 2])
    sin_t = np.sin(values[:, 2])
    local = _CENTRED_CORNERS * side_mm
    return np.stack(
        [
            np.outer(cos_t, local[:, 0]) - np.outer(sin_t, local[:, 1]) + values[:, 0:1],
            np.outer(sin_t, local[:, 0]) + np.outer(cos_t, local[:, 1]) + values[:, 1:2],
        ],
        axis=-1,
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
        raise AppError("no_markers")
    if marker_mm <= 0.0:
        raise AppError("bad_marker_size", "marker_mm")

    if mode == "sheet":
        homography, plane_by_id = _solve_sheet(markers, marker_mm, spacing_mm)
    elif mode == "free":
        homography, plane_by_id = _solve_free(markers, marker_mm)
    elif mode == "scattered":
        homography, plane_by_id = _solve_scattered(markers, marker_mm)
    else:
        raise AppError("bad_mode", "mode", mode=mode)

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
        raise AppError(
            "no_sheet_ids",
            "mode",
            found=", ".join(str(m.marker_id) for m in markers),
            expected=", ".join(str(i) for i in config.SHEET_MARKER_IDS),
        )

    plane_by_id = {m.marker_id: layout[m.marker_id] for m in usable}
    plane_pts = np.vstack([plane_by_id[m.marker_id] for m in usable])
    image_pts = np.vstack([m.corners_px for m in usable])

    if len(usable) == 1:
        # Vier Punkte: exakt bestimmt, LMEDS braucht mehr. Kein Ausgleich moeglich.
        homography = _homography_from_quad(plane_pts, image_pts)
    else:
        try:
            homography = _homography_lmeds(plane_pts, image_pts)
        except RuntimeError as error:  # der Kern findet keine - siehe unten
            raise AppError("homography_failed") from error

    return _refine_homography(homography, plane_pts, image_pts), plane_by_id


def _fit_free_python(quads: np.ndarray, marker_mm: float) -> tuple[np.ndarray, np.ndarray]:
    """Homographie UND Markerversaetze gemeinsam schaetzen.

    `quads` ist (M,4,2) und ABSTEIGEND nach Bildflaeche sortiert - der erste
    Marker ist der Anker. Sortiert wird beim Aufrufer, weil nur der die
    Marker-IDs kennt, die hinterher wieder zugeordnet werden muessen; die Grenze
    zum Rechenkern kennt keine IDs, sondern nur Ecken.
    """
    quads = np.asarray(quads, dtype=np.float64).reshape(-1, 4, 2)
    image_pts = quads.reshape(-1, 2)

    # Startwert: der groesste Marker definiert Ursprung und Massstab der Ebene.
    anchor_plane = _UNIT_CORNERS * marker_mm
    homography = cv2.getPerspectiveTransform(
        anchor_plane.astype(np.float32), quads[0].astype(np.float32)
    )

    inverse = np.linalg.inv(homography)
    offsets = []
    for quad in quads[1:]:
        plane_quad = project(inverse, quad)
        offsets.append(plane_quad.mean(axis=0) - marker_mm / 2.0)
    offsets_array = np.array(offsets).reshape(-1, 2) if offsets else np.zeros((0, 2))

    def plane_points(offset_values: np.ndarray) -> np.ndarray:
        parts = [anchor_plane]
        for offset in offset_values.reshape(-1, 2):
            parts.append(_UNIT_CORNERS * marker_mm + offset)
        return np.vstack(parts)

    def residual(params: np.ndarray) -> np.ndarray:
        matrix = np.append(params[:8], 1.0).reshape(3, 3)
        return (project(matrix, plane_points(params[8:])) - image_pts).ravel()

    start = np.concatenate([_as_eight(homography), offsets_array.ravel()])
    fitted = least_squares(residual, start, method="trf", xtol=1e-14, ftol=1e-14, gtol=1e-14)

    return np.append(fitted.x[:8], 1.0).reshape(3, 3), fitted.x[8:].reshape(-1, 2)


_fit_free = backend.implementation("fit_free", _fit_free_python)


def _solve_free(
    markers: list[DetectedMarker], marker_mm: float
) -> tuple[np.ndarray, dict[int, np.ndarray]]:
    ordered = sorted(markers, key=lambda m: m.image_area_px, reverse=True)
    anchor, others = ordered[0], ordered[1:]

    solved, final_offsets = _fit_free(np.stack([m.corners_px for m in ordered]), marker_mm)

    anchor_plane = _UNIT_CORNERS * marker_mm
    plane_by_id = {anchor.marker_id: anchor_plane}
    for marker, offset in zip(others, np.asarray(final_offsets).reshape(-1, 2)):
        plane_by_id[marker.marker_id] = _UNIT_CORNERS * marker_mm + offset
    return np.asarray(solved, dtype=np.float64), plane_by_id


def _plane_jacobian(homography: np.ndarray, point_mm: np.ndarray) -> np.ndarray:
    """Die 2x2-Jacobimatrix der Abbildung Ebene -> Bild an einer Stelle.

    Nicht mit geometry.local_px_per_mm geteilt, obwohl dieselben vier Groessen
    dort auch vorkommen: local_px_per_mm ist eine Funktion HINTER dem Umschalter
    und traegt RMS-in-mm, Interpolationswahl und Fusszeile. Sie fuer diesen einen
    Aufrufer zu zerlegen hiesse, an einer tragenden Stelle etwas zu aendern, das
    hier nur gebraucht wird. Der C++-Kern haelt es genauso (solve.cpp).
    """
    matrix = np.asarray(homography, dtype=np.float64)
    x, y = float(point_mm[0]), float(point_mm[1])

    w = matrix[2, 0] * x + matrix[2, 1] * y + matrix[2, 2]
    if abs(w) < 1e-12:
        raise AppError("homography_degenerate")
    u = (matrix[0, 0] * x + matrix[0, 1] * y + matrix[0, 2]) / w
    v = (matrix[1, 0] * x + matrix[1, 1] * y + matrix[1, 2]) / w

    return np.array(
        [
            [(matrix[0, 0] - u * matrix[2, 0]) / w, (matrix[0, 1] - u * matrix[2, 1]) / w],
            [(matrix[1, 0] - v * matrix[2, 0]) / w, (matrix[1, 1] - v * matrix[2, 1]) / w],
        ]
    )


def _oriented_to_photo(
    homography: np.ndarray, poses: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Die Ebene so drehen und schieben, dass sie zum Foto passt.

    Der Zuschnitt ist ein ACHSPARALLELES Rechteck. Haengen die Ebenenachsen am
    Ankermarker - und der liegt im Streu-Modus in einem zufaelligen Winkel -,
    steht die Schablone schief, und um das Objekt herum wird Rand verschenkt.

    Gesucht ist deshalb die Drehung, nach der die Abbildung Ebene -> Bild
    moeglichst wenig dreht. Fuer eine 2x2-Matrix J ist die naechstgelegene
    Drehung atan2(J10 - J01, J00 + J11); dreht man sie heraus, bleibt eine
    SYMMETRISCHE Streckung uebrig - die perspektivische Verkuerzung, die sich
    nicht wegdrehen laesst. Gemessen wird in der Mitte der Markerwolke, weil dort
    die Schablone liegt; dorthin kommt auch der Ursprung.
    """
    centre = poses[:, :2].mean(axis=0)
    jacobian = _plane_jacobian(homography, centre)
    turn = -np.arctan2(
        jacobian[1, 0] - jacobian[0, 1], jacobian[0, 0] + jacobian[1, 1]
    )
    cos_t, sin_t = np.cos(turn), np.sin(turn)

    # Von den NEUEN Ebenenkoordinaten in die alten: erst drehen, dann in die
    # Mitte schieben. Verkettet mit der Homographie ergibt das die neue.
    move = np.array(
        [[cos_t, -sin_t, centre[0]], [sin_t, cos_t, centre[1]], [0.0, 0.0, 1.0]]
    )
    oriented = np.asarray(homography, dtype=np.float64) @ move
    if abs(oriented[2, 2]) < 1e-15:
        raise AppError("homography_degenerate")

    delta = poses[:, :2] - centre
    turned = np.column_stack(
        [
            cos_t * delta[:, 0] + sin_t * delta[:, 1],
            -sin_t * delta[:, 0] + cos_t * delta[:, 1],
            poses[:, 2] - turn,
        ]
    )
    return oriented / oriented[2, 2], turned


def _fit_scattered_python(quads: np.ndarray, marker_mm: float) -> tuple[np.ndarray, np.ndarray]:
    """Homographie UND Markerlagen (x, y, Winkel) gemeinsam schaetzen.

    Wie _fit_free_python, nur mit einer Unbekannten mehr je Marker. `quads` ist
    (M,4,2) und ABSTEIGEND nach Bildflaeche sortiert; zurueck kommt die
    ausgerichtete Homographie und eine Lage je Marker - AUCH fuer den ersten,
    denn nach der Ausrichtung steht auch er nicht mehr im Ursprung.
    """
    quads = np.asarray(quads, dtype=np.float64).reshape(-1, 4, 2)
    image_pts = quads.reshape(-1, 2)

    # Startwert: der groesste Marker liegt achsparallel im Ursprung. Nur der
    # Anfangspunkt der Rechnung - ausgerichtet wird ganz am Ende.
    anchor = np.array([marker_mm / 2.0, marker_mm / 2.0, 0.0])
    anchor_plane = marker_plane_corners_at(anchor, marker_mm)[0]
    homography = cv2.getPerspectiveTransform(
        anchor_plane.astype(np.float32), quads[0].astype(np.float32)
    )

    inverse = np.linalg.inv(homography)
    poses = [anchor]
    for quad in quads[1:]:
        plane_quad = project(inverse, quad)
        # Der Winkel kommt aus der Kante Ecke 0 -> Ecke 1. Sie zeigt im Marker
        # selbst in +x-Richtung, ihr Winkel in der Ebene IST also die Drehung.
        edge = plane_quad[1] - plane_quad[0]
        poses.append(
            np.array(
                [*plane_quad.mean(axis=0), float(np.arctan2(edge[1], edge[0]))]
            )
        )
    start_poses = np.array(poses).reshape(-1, 3)

    def plane_points(pose_values: np.ndarray) -> np.ndarray:
        every = np.vstack([anchor, pose_values.reshape(-1, 3)])
        return marker_plane_corners_at(every, marker_mm).reshape(-1, 2)

    def residual(params: np.ndarray) -> np.ndarray:
        matrix = np.append(params[:8], 1.0).reshape(3, 3)
        return (project(matrix, plane_points(params[8:])) - image_pts).ravel()

    start = np.concatenate([_as_eight(homography), start_poses[1:].ravel()])
    fitted = least_squares(residual, start, method="trf", xtol=1e-14, ftol=1e-14, gtol=1e-14)

    return _oriented_to_photo(
        np.append(fitted.x[:8], 1.0).reshape(3, 3),
        np.vstack([anchor, fitted.x[8:].reshape(-1, 3)]),
    )


_fit_scattered = backend.implementation("fit_scattered", _fit_scattered_python)


def _solve_scattered(
    markers: list[DetectedMarker], marker_mm: float
) -> tuple[np.ndarray, dict[int, np.ndarray]]:
    ordered = sorted(markers, key=lambda m: m.image_area_px, reverse=True)
    solved, poses = _fit_scattered(np.stack([m.corners_px for m in ordered]), marker_mm)

    corners = marker_plane_corners_at(np.asarray(poses), marker_mm)
    plane_by_id = {marker.marker_id: quad for marker, quad in zip(ordered, corners)}
    return np.asarray(solved, dtype=np.float64), plane_by_id


def _homography_from_quad_python(plane: np.ndarray, image: np.ndarray) -> np.ndarray:
    """Homographie aus GENAU vier Punktpaaren - exakt bestimmt, kein Ausgleich."""
    return cv2.getPerspectiveTransform(
        np.asarray(plane, dtype=np.float32), np.asarray(image, dtype=np.float32)
    )


def _homography_lmeds_python(plane: np.ndarray, image: np.ndarray) -> np.ndarray:
    """Homographie aus vielen Punktpaaren, robust (LMEDS).

    Wirft RuntimeError, statt None zurueckzugeben: eine sprachneutrale Grenze
    kennt kein None, und der C++-Kern kann nur werfen. Welcher Fehlercode daraus
    wird, entscheidet der Aufrufer - der Kern kennt keine Fehlertexte
    (Invariante 7).
    """
    homography, _ = cv2.findHomography(plane, image, method=cv2.LMEDS)
    if homography is None:
        raise RuntimeError("homography_failed")
    return homography


def _refine_homography_python(
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


# Hier entstehen die Millimeter. Deshalb stehen genau diese drei hinter dem
# Umschalter: ARUCO_CORE=cpp faehrt dieselbe Testsuite gegen die C++-Fassung,
# und ein Auseinanderlaufen faellt am selben Tag auf, an dem es entsteht.
_homography_from_quad = backend.implementation(
    "homography_from_quad", _homography_from_quad_python
)
_homography_lmeds = backend.implementation("homography_lmeds", _homography_lmeds_python)
_refine_homography = backend.implementation("refine_homography", _refine_homography_python)


def _as_eight(homography: np.ndarray) -> np.ndarray:
    """Homographie auf H[2,2] = 1 normieren und die 8 freien Parameter zurueckgeben."""
    matrix = np.asarray(homography, dtype=np.float64)
    if abs(matrix[2, 2]) < 1e-15:
        raise AppError("homography_degenerate")
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
        notices.warn("single_marker")

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
            notices.warn("collinear_markers")

    if solution.rms_px > config.RMS_WARN_PX or solution.rms_mm > config.RMS_WARN_MM:
        notices.warn(
            "high_residual",
            rms_px=f"{solution.rms_px:.2f}",
            rms_mm=f"{solution.rms_mm:.2f}",
        )

    for fit in solution.markers:
        deviation = abs(fit.side_mm_measured - marker_mm) / marker_mm
        if deviation > config.MARKER_SIZE_DEV_WARN:
            notices.warn(
                "marker_size_deviation",
                marker_id=fit.marker_id,
                measured_mm=f"{fit.side_mm_measured:.1f}",
                expected_mm=f"{marker_mm:.1f}",
                deviation_pct=f"{deviation * 100:.1f}",
            )

    if solution.mode == "free":
        reference = solution.markers[0].rotation_deg
        for fit in solution.markers[1:]:
            if abs(fit.rotation_deg - reference) > config.MARKER_ROT_WARN_DEG:
                notices.warn(
                    "marker_rotation",
                    marker_id=fit.marker_id,
                    rotation_deg=f"{abs(fit.rotation_deg - reference):.1f}",
                )
