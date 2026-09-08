"""Synthetische Szenen mit bekannter Grundwahrheit.

Kein Test dieses Projekts verlaesst sich auf ein echtes Foto oder auf Augenschein.
Stattdessen wird eine virtuelle Kamera mit gewaehlter Brennweite, Hoehe und Neigung
aufgebaut, die Ebene mit Markern und Testobjekt gerendert und anschliessend geprueft,
ob die Pipeline die eingesetzten Zahlen zurueckgewinnt.

Der Trick fuer die Dickenkorrektur: ein Objekt in Hoehe h wird an seiner SCHEINBAREN
Stelle auf der Ebene z = 0 gezeichnet (T = N + k*(Q-N)). Optisch ist das dasselbe
Bild - und die Pipeline muss daraus wieder Q machen.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import pytest

from app import config
from app.vision.detect import DetectedMarker
from app.vision.geometry import project
from app.vision.solve import marker_plane_corners, marker_plane_corners_at

# Aufloesung der virtuellen Ebene. Sie ist die Genauigkeitsgrenze des Renderers:
# eine Kante kann nur auf 1/CANVAS_PPM mm genau gezeichnet werden, und im Foto
# entspricht das bei ~1,9 px/mm rund 0,16 px. Mit 6 px/mm lag dieser Rasterfehler
# in derselben Groessenordnung wie die zu pruefende Subpixel-Genauigkeit - deshalb
# 12 px/mm. Der Wert muss so gewaehlt sein, dass marker_mm * CANVAS_PPM durch 6
# teilbar ist (4x4-Marker + Rand = 6 Module), sonst werden die Module ungleich.
CANVAS_PPM = 12.0
CANVAS_X0, CANVAS_Y0 = -160.0, -20.0
CANVAS_X1, CANVAS_Y1 = 260.0, 330.0
QUIET_ZONE_MM = 10.0


@dataclass(frozen=True)
class Scene:
    """Ein gerendertes Testfoto samt allem, was die Pipeline daraus finden soll."""

    image: np.ndarray
    homography: np.ndarray            # wahre Abbildung Ebene(mm) -> Bild(px), z = 0
    focal_px: float
    focal35_mm: float
    camera_height_mm: float
    nadir_mm: tuple[float, float]
    tilt_deg: float
    marker_mm: float
    centers_mm: dict[int, tuple[float, float]]
    thickness_mm: float
    correction_k: float
    object_rect_mm: tuple[float, float, float, float]
    measure_points_mm: np.ndarray     # zwei Punkte in WAHREN Objektkoordinaten

    @property
    def image_size(self) -> tuple[int, int]:
        return (int(self.image.shape[1]), int(self.image.shape[0]))

    def apparent(self, points_mm: np.ndarray) -> np.ndarray:
        """Wahre Objektkoordinaten -> scheinbare Lage in der Markerebene."""
        points = np.asarray(points_mm, dtype=np.float64).reshape(-1, 2)
        nadir = np.array(self.nadir_mm)
        return nadir + self.correction_k * (points - nadir)

    @property
    def measure_distance_mm(self) -> float:
        return float(np.linalg.norm(self.measure_points_mm[1] - self.measure_points_mm[0]))


def make_scene(
    thickness_mm: float = 0.0,
    marker_mm: float = config.MARKER_MM_NOMINAL,
    centers_mm: dict[int, tuple[float, float]] | None = None,
    image_size: tuple[int, int] = (2400, 1800),
    camera_xy: tuple[float, float] = (140.0, 160.0),
    camera_height_mm: float = 900.0,
    target_mm: tuple[float, float] = (105.0, 148.5),
    focal35_mm: float = 26.0,
) -> Scene:
    """Baut eine Szene. thickness_mm > 0 legt das Testobjekt ueber die Markerebene."""
    centers = dict(centers_mm or config.SHEET_MARKER_CENTERS_MM)
    width, height = image_size
    focal_px = focal35_mm / 36.0 * max(width, height)

    rotation, translation = _look_at(camera_xy, camera_height_mm, target_mm)
    intrinsics = np.array(
        [[focal_px, 0.0, width / 2.0], [0.0, focal_px, height / 2.0], [0.0, 0.0, 1.0]]
    )
    homography = intrinsics @ np.column_stack([rotation[:, 0], rotation[:, 1], translation])
    homography = homography / homography[2, 2]

    factor = camera_height_mm / (camera_height_mm - thickness_mm)
    object_rect = (-130.0, 30.0, 30.0, 270.0)
    measure_points = np.array([[-200.0, 150.0], [300.0, 150.0]])

    scene = Scene(
        image=np.zeros((1, 1, 3), np.uint8),  # gleich ersetzt
        homography=homography,
        focal_px=focal_px,
        focal35_mm=focal35_mm,
        camera_height_mm=camera_height_mm,
        nadir_mm=(camera_xy[0], camera_xy[1]),
        tilt_deg=float(np.degrees(np.arccos(min(1.0, abs(rotation[2, 2]))))),
        marker_mm=marker_mm,
        centers_mm=centers,
        thickness_mm=thickness_mm,
        correction_k=factor,
        object_rect_mm=object_rect,
        measure_points_mm=measure_points,
    )

    canvas = _render_plane(scene)
    image = _photograph(canvas, homography, image_size)
    return Scene(**{**scene.__dict__, "image": image})


def _look_at(
    camera_xy: tuple[float, float], height_mm: float, target_mm: tuple[float, float]
) -> tuple[np.ndarray, np.ndarray]:
    """Kamerapose als (R, t). Weltframe: x rechts, y unten, Kamera bei negativem z."""
    centre = np.array([camera_xy[0], camera_xy[1], -float(height_mm)])
    target = np.array([target_mm[0], target_mm[1], 0.0])

    forward = target - centre
    forward = forward / np.linalg.norm(forward)
    right = np.cross(np.array([0.0, 1.0, 0.0]), forward)
    right = right / np.linalg.norm(right)
    down = np.cross(forward, right)

    rotation = np.vstack([right, down, forward])
    return rotation, -rotation @ centre


def _render_plane(scene: Scene) -> np.ndarray:
    """Die Ebene als Bild: helles Blatt, dunkles Testobjekt, Marker mit Ruhezone."""
    width = int(round((CANVAS_X1 - CANVAS_X0) * CANVAS_PPM))
    height = int(round((CANVAS_Y1 - CANVAS_Y0) * CANVAS_PPM))
    canvas = np.full((height, width, 3), 235, np.uint8)

    # Testobjekt an seiner SCHEINBAREN Lage - so, wie die Kamera es sehen wuerde.
    x0, y0, x1, y1 = scene.object_rect_mm
    corners = scene.apparent(np.array([[x0, y0], [x1, y1]]))
    cv2.rectangle(
        canvas,
        _to_canvas(corners[0]),
        _to_canvas(corners[1]),
        (70, 70, 70),
        thickness=-1,
    )

    dictionary = cv2.aruco.getPredefinedDictionary(config.ARUCO_DICT_ID)
    side_px = int(round(scene.marker_mm * CANVAS_PPM))
    quiet_px = int(round(QUIET_ZONE_MM * CANVAS_PPM))

    for marker_id, (cx, cy) in scene.centers_mm.items():
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, side_px)
        left, top = _to_canvas((cx - scene.marker_mm / 2.0, cy - scene.marker_mm / 2.0))

        # Lieber laut scheitern als einen angeschnittenen Marker rendern - ein
        # halber Marker wuerde als raetselhafter Detektionsfehler auftauchen.
        assert 0 <= left and left + side_px <= width, f"Marker {marker_id} passt nicht in x"
        assert 0 <= top and top + side_px <= height, f"Marker {marker_id} passt nicht in y"

        canvas[
            max(0, top - quiet_px) : min(height, top + side_px + quiet_px),
            max(0, left - quiet_px) : min(width, left + side_px + quiet_px),
        ] = 255
        canvas[top : top + side_px, left : left + side_px] = marker[:, :, None]

    return canvas


def _to_canvas(point_mm) -> tuple[int, int]:
    return (
        int(round((float(point_mm[0]) - CANVAS_X0) * CANVAS_PPM)),
        int(round((float(point_mm[1]) - CANVAS_Y0) * CANVAS_PPM)),
    )


def _photograph(
    canvas: np.ndarray, homography: np.ndarray, image_size: tuple[int, int]
) -> np.ndarray:
    """Die Ebene durch die virtuelle Kamera abbilden.

    Vor dem Warp wird tiefpassgefiltert. warpPerspective kann nicht flaechenmitteln;
    die Ebene wird hier aber um ein Vielfaches verkleinert (12 px/mm auf rund
    2 px/mm im Foto). Ohne Vorfilterung entsteht massives Aliasing, das die
    Markerecken um mehrere Zehntelpixel verschiebt - der Test wuerde dann den
    Renderer messen statt den Detektor. Der Gauss ist symmetrisch und verschiebt
    Kanten daher nicht; er macht genau das, was eine echte Optik auch tut.
    """
    canvas_to_plane = np.array(
        [
            [1.0 / CANVAS_PPM, 0.0, CANVAS_X0],
            [0.0, 1.0 / CANVAS_PPM, CANVAS_Y0],
            [0.0, 0.0, 1.0],
        ]
    )
    total = homography @ canvas_to_plane

    downscale = CANVAS_PPM / _image_px_per_mm(homography)
    if downscale > 1.0:
        sigma = 0.5 * downscale
        canvas = cv2.GaussianBlur(canvas, (0, 0), sigma)

    return cv2.warpPerspective(
        canvas,
        total,
        image_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )


def _image_px_per_mm(homography: np.ndarray) -> float:
    """Wie viele Bildpixel ein Millimeter der Ebene ungefaehr belegt."""
    probe = project(homography, np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]))
    return float(
        (np.linalg.norm(probe[1] - probe[0]) + np.linalg.norm(probe[2] - probe[0])) / 2.0
    )


def ideal_markers(scene: Scene) -> list[DetectedMarker]:
    """Analytisch exakte Markerecken - trennt die Solver-Tests vom Detektor."""
    markers = []
    for marker_id, (cx, cy) in sorted(scene.centers_mm.items()):
        plane = marker_plane_corners(cx, cy, scene.marker_mm)
        markers.append(DetectedMarker(marker_id, project(scene.homography, plane)))
    return markers


def rotated_markers(scene: Scene, angles_deg: dict[int, float]) -> list[DetectedMarker]:
    """Ideale Ecken, aber jeder Marker um seinen eigenen Mittelpunkt gedreht.

    Das ist die Lage, fuer die es den Streu-Modus gibt: Marker, die verstreut
    auf einer Flaeche liegen, jeder in seinem Winkel.

    Das gerenderte Foto der Szene zeigt sie weiterhin achsparallel - hier wird
    nichts neu gezeichnet. Das ist kein Mangel, sondern dieselbe Trennung, die
    ideal_markers schon macht: der Detektor ist anderswo geprueft, hier steht
    der Ausgleich auf dem Pruefstand, und der sieht nichts als Ecken.
    """
    markers = []
    for marker_id, (cx, cy) in sorted(scene.centers_mm.items()):
        pose = np.array([cx, cy, np.radians(angles_deg.get(marker_id, 0.0))])
        plane = marker_plane_corners_at(pose, scene.marker_mm)[0]
        markers.append(DetectedMarker(marker_id, project(scene.homography, plane)))
    return markers


def noisy_markers(scene: Scene, sigma_px: float, seed: int = 7) -> list[DetectedMarker]:
    """Ideale Ecken plus Gauss-Rauschen - simuliert Detektionsunsicherheit."""
    generator = np.random.default_rng(seed)
    return [
        DetectedMarker(
            marker.marker_id,
            marker.corners_px + generator.normal(0.0, sigma_px, marker.corners_px.shape),
        )
        for marker in ideal_markers(scene)
    ]


@pytest.fixture(scope="session")
def scene() -> Scene:
    """Standardszene ohne Hoehenversatz."""
    return make_scene()


@pytest.fixture(scope="session")
def thick_scene() -> Scene:
    """Objekt 20 mm ueber der Markerebene, Kamera 900 mm hoch -> k = 1,0227."""
    return make_scene(thickness_mm=20.0)
