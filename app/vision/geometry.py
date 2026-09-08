"""Projektive Grundrechenarten.

Diese Helfer werden von solve, extent, thickness und rectify gemeinsam benutzt.
Sie stehen hier einmal, damit keine zweite Variante derselben Formel entsteht.

Drei davon rufen OpenCV und koennen deshalb im C++-Kern liegen (Huelle,
Schnittflaeche, lokaler Massstab); welcher Kern rechnet, entscheidet
`app/vision/backend.py`. Der Rest ist reine Formel und bleibt hier: eine
Matrixmultiplikation ueber die Bindungsgrenze zu schicken kostet mehr, als sie
wert ist, und driften kann sie nicht.
"""

from __future__ import annotations

import cv2
import numpy as np

from app.vision import backend


def project(homography: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Wendet eine Homographie auf (N,2)-Punkte an und teilt durch w.

    Punkte, deren w-Komponente verschwindet, liegen im Unendlichen; sie kommen als
    inf zurueck, statt eine Division-durch-Null-Ausnahme zu werfen. Aufrufer, die
    das nicht vertragen, muessen vorher clippen (siehe extent.py).
    """
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    homogeneous = np.hstack([pts, np.ones((len(pts), 1))])
    mapped = homogeneous @ np.asarray(homography, dtype=np.float64).T
    with np.errstate(divide="ignore", invalid="ignore"):
        return mapped[:, :2] / mapped[:, 2:3]


def _local_px_per_mm_python(homography: np.ndarray, point_mm: np.ndarray) -> float:
    """Lokaler Abbildungsmassstab der Homographie Ebene -> Bild an einer Stelle.

    Definition laut Spec 3.7: Wurzel aus dem Betrag der Jacobi-Determinante. Dieses
    eine Mass wird fuer RMS-in-mm, die Interpolationswahl und die PDF-Fusszeile
    benutzt - ueberall dasselbe, damit die Zahlen zusammenpassen.
    """
    matrix = np.asarray(homography, dtype=np.float64)
    x, y = float(point_mm[0]), float(point_mm[1])

    w = matrix[2, 0] * x + matrix[2, 1] * y + matrix[2, 2]
    if abs(w) < 1e-12:
        return float("inf")
    u = (matrix[0, 0] * x + matrix[0, 1] * y + matrix[0, 2]) / w
    v = (matrix[1, 0] * x + matrix[1, 1] * y + matrix[1, 2]) / w

    du_dx = (matrix[0, 0] - u * matrix[2, 0]) / w
    du_dy = (matrix[0, 1] - u * matrix[2, 1]) / w
    dv_dx = (matrix[1, 0] - v * matrix[2, 0]) / w
    dv_dy = (matrix[1, 1] - v * matrix[2, 1]) / w

    return float(np.sqrt(abs(du_dx * dv_dy - du_dy * dv_dx)))


local_px_per_mm = backend.implementation("local_px_per_mm", _local_px_per_mm_python)


def rect_polygon(x0: float, y0: float, x1: float, y1: float) -> np.ndarray:
    """Rechteck als (4,2)-Polygon, im Uhrzeigersinn bei y-nach-unten."""
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float64)


def polygon_area(polygon: np.ndarray) -> float:
    """Flaeche eines einfachen Polygons (Gausssche Trapezformel), immer positiv."""
    pts = np.asarray(polygon, dtype=np.float64).reshape(-1, 2)
    if len(pts) < 3:
        return 0.0
    x, y = pts[:, 0], pts[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2.0)


def _convex_hull_python(points: np.ndarray) -> np.ndarray:
    """Konvexe Huelle als (N,2)-Polygon."""
    pts = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
    return cv2.convexHull(pts).reshape(-1, 2).astype(np.float64)


def _convex_intersection_area_python(first: np.ndarray, second: np.ndarray) -> float:
    """Flaeche des Schnitts zweier KONVEXER Polygone."""
    a = np.asarray(first, dtype=np.float32).reshape(-1, 1, 2)
    b = np.asarray(second, dtype=np.float32).reshape(-1, 1, 2)
    area, _ = cv2.intersectConvexConvex(a, b)
    return float(area)


# Die float32-Zwischenstufe oben ist kein Schoenheitsfehler, sondern Teil des
# Ergebnisses - der C++-Kern legt sie an derselben Stelle ein.
convex_hull = backend.implementation("convex_hull", _convex_hull_python)
convex_intersection_area = backend.implementation(
    "convex_intersection_area", _convex_intersection_area_python
)


def clip_polygon_halfplane(
    polygon: np.ndarray, line: tuple[float, float, float], eps: float = 0.0
) -> np.ndarray:
    """Schneidet ein Polygon an der Halbebene a*x + b*y + c >= eps (Sutherland-Hodgman).

    Wird gebraucht, um das Bildrechteck vom Horizont der Homographie wegzuschneiden -
    jenseits davon bildet die Ruecktransformation ins Unendliche ab.
    """
    a, b, c = line
    pts = np.asarray(polygon, dtype=np.float64).reshape(-1, 2)
    if len(pts) == 0:
        return pts

    def side(point: np.ndarray) -> float:
        return a * point[0] + b * point[1] + c - eps

    output: list[np.ndarray] = []
    for index, current in enumerate(pts):
        previous = pts[index - 1]
        side_current, side_previous = side(current), side(previous)
        if side_current >= 0.0:
            if side_previous < 0.0:
                output.append(_intersect(previous, current, side_previous, side_current))
            output.append(current)
        elif side_previous >= 0.0:
            output.append(_intersect(previous, current, side_previous, side_current))

    return np.array(output, dtype=np.float64).reshape(-1, 2)


def _intersect(
    start: np.ndarray, end: np.ndarray, side_start: float, side_end: float
) -> np.ndarray:
    """Schnittpunkt der Kante start->end mit der Clipping-Linie."""
    denominator = side_start - side_end
    if abs(denominator) < 1e-15:
        return start
    t = side_start / denominator
    return start + t * (end - start)
