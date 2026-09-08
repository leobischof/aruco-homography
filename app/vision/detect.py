"""Foto laden und ArUco-Marker mit Subpixel-Genauigkeit finden.

Zwei Dinge entscheiden hier ueber die spaetere Masshaltigkeit:
  * Die EXIF-Orientierung muss VOR jeder Erkennung angewandt werden - sonst sucht
    der Detektor in einem gedrehten Bild und alle Koordinaten sind falsch.
  * Subpixel-Refinement der Ecken. Ohne das verliert man rund ein Pixel, was auf
    einem 500-mm-Objekt schon mehrere Zehntelmillimeter Fehler bedeutet.

Die Erkennung selbst gibt es zweimal: hier als geprueft masshaltige Referenz und
in C++ unter `core/`. Welche laeuft, entscheidet `app/vision/backend.py` -
Aufrufer merken davon nichts. Das Laden des Fotos bleibt Python: es haengt an
PIL und an EXIF, und beides gibt es im Browser nicht (Stufe 0, Abschnitt 5).
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps

from app import config
from app.vision import backend

try:  # Handyfotos von iPhones kommen als HEIC an.
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:  # pragma: no cover - ohne HEIC laeuft alles andere weiter
    pass

_EXIF_IFD = 0x8769
_TAG_FOCAL_35MM = 41989
_TAG_MODEL = 0x0110


@dataclass(frozen=True)
class Photo:
    """Ein geladenes Foto samt der EXIF-Angaben, die wir brauchen."""

    bgr: np.ndarray
    focal35_mm: float | None
    camera_model: str | None

    @property
    def width(self) -> int:
        return int(self.bgr.shape[1])

    @property
    def height(self) -> int:
        return int(self.bgr.shape[0])


@dataclass(frozen=True)
class DetectedMarker:
    """Ein erkannter Marker: ID und die vier Bildecken in der Reihenfolge TL, TR, BR, BL."""

    marker_id: int
    corners_px: np.ndarray  # (4,2) float64

    @property
    def center_px(self) -> np.ndarray:
        return self.corners_px.mean(axis=0)

    @property
    def image_area_px(self) -> float:
        # Auch das durch den Umschalter: die Flaeche entscheidet, welcher Marker
        # im Frei-Modus der Anker wird und welcher bei doppelter ID gewinnt. Eine
        # andere Reihenfolge waere ein anderer Startwert.
        return float(_quad_area(self.corners_px))


def load_photo(data: bytes) -> Photo:
    """Bytes eines Uploads in ein BGR-Bild verwandeln, EXIF-Rotation angewandt."""
    with Image.open(io.BytesIO(data)) as image:
        focal35, model = _read_exif(image)
        upright = ImageOps.exif_transpose(image)
        rgb = np.asarray(upright.convert("RGB"))

    return Photo(
        bgr=cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
        focal35_mm=focal35,
        camera_model=model,
    )


def _read_exif(image: Image.Image) -> tuple[float | None, str | None]:
    """35-mm-Brennweite und Kameramodell aus den EXIF-Daten ziehen.

    FocalLengthIn35mmFilm steht in der Exif-Sub-IFD, nicht in IFD0 - beide werden
    abgefragt, weil manche Kameras/Apps die Tags anders einsortieren.
    """
    try:
        exif = image.getexif()
    except Exception:  # pragma: no cover - defekte EXIF-Bloecke sind kein Fehlerfall
        return None, None
    if not exif:
        return None, None

    focal_raw = exif.get(_TAG_FOCAL_35MM)
    if focal_raw is None:
        try:
            focal_raw = exif.get_ifd(_EXIF_IFD).get(_TAG_FOCAL_35MM)
        except Exception:  # pragma: no cover
            focal_raw = None

    focal35: float | None = None
    if focal_raw is not None:
        try:
            value = float(focal_raw)
            focal35 = value if value > 0.0 else None
        except (TypeError, ValueError):
            focal35 = None

    model = exif.get(_TAG_MODEL)
    model = str(model).strip() or None if model is not None else None
    return focal35, model


def build_detector() -> cv2.aruco.ArucoDetector:
    """Detektor mit den Parametern, die fuer grosse Handyfotos noetig sind."""
    dictionary = cv2.aruco.getPredefinedDictionary(config.ARUCO_DICT_ID)
    params = cv2.aruco.DetectorParameters()

    # Subpixel-Refinement: der wichtigste Genauigkeitsschalter dieses Projekts.
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    params.cornerRefinementWinSize = 5
    params.cornerRefinementMaxIterations = 50
    params.cornerRefinementMinAccuracy = 0.01

    # Ein 12-MP-Foto braucht deutlich groessere Schwellwertfenster als die Defaults,
    # weil ein 50-mm-Marker darin mehrere hundert Pixel breit ist.
    params.adaptiveThreshWinSizeMin = 3
    params.adaptiveThreshWinSizeMax = 53
    params.adaptiveThreshWinSizeStep = 10
    params.minMarkerPerimeterRate = 0.01

    return cv2.aruco.ArucoDetector(dictionary, params)


def _quad_area_python(quad: np.ndarray) -> float:
    """Bildflaeche eines Markervierecks (contourArea auf float32-Ecken)."""
    return float(cv2.contourArea(np.asarray(quad, dtype=np.float32)))


_quad_area = backend.implementation("quad_area", _quad_area_python)


def _detect_markers_python(
    bgr: np.ndarray, enhance_contrast: bool
) -> list[tuple[int, np.ndarray]]:
    """Die geprueft masshaltige Referenz - dieselbe Rechnung wie seit jeher.

    Rueckgabe sind absichtlich nur (ID, Ecken) und keine DetectedMarker: das ist
    die Grenze, an der der C++-Kern andockt (core/include/aruco/types.hpp), und
    die kennt keine Python-Klassen.

    Bei mehrfach erkannter ID gewinnt der Marker mit der groesseren Bildflaeche -
    Doppelerkennungen sind selten, wuerden die Homographie aber verziehen.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if enhance_contrast:
        gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)

    corners, ids, _ = build_detector().detectMarkers(gray)
    if ids is None or len(ids) == 0:
        return []

    best: dict[int, DetectedMarker] = {}
    for quad, marker_id in zip(corners, ids.flatten()):
        marker = DetectedMarker(int(marker_id), np.asarray(quad, dtype=np.float64).reshape(4, 2))
        previous = best.get(marker.marker_id)
        if previous is None or marker.image_area_px > previous.image_area_px:
            best[marker.marker_id] = marker

    return [(key, best[key].corners_px) for key in sorted(best)]


# Der Umschalter. Welcher Kern rechnet, entscheidet ARUCO_CORE beim Import -
# nachgeschlagen wird es genau hier und nirgends sonst (app/vision/backend.py).
_detect_markers = backend.implementation("detect_markers", _detect_markers_python)


def detect_markers(bgr: np.ndarray, enhance_contrast: bool = True) -> list[DetectedMarker]:
    """Alle Marker im Bild finden, sortiert nach ID.

    Die Erkennung selbst macht der aktive Kern; diese Funktion macht aus seinem
    sprachneutralen Ergebnis wieder DetectedMarker. Fuer alle Aufrufer sieht das
    aus wie vorher - genau das ist der Sinn (docs/cpp-migration/README.md).
    """
    return [
        DetectedMarker(int(marker_id), np.asarray(corners, dtype=np.float64).reshape(4, 2))
        for marker_id, corners in _detect_markers(bgr, enhance_contrast)
    ]


def draw_detection(bgr: np.ndarray, markers: list[DetectedMarker]) -> np.ndarray:
    """Erkennungs-Overlay fuer die Vorschau: Umriss, ID und Eckennummern."""
    canvas = bgr.copy()
    thickness = max(1, round(min(canvas.shape[:2]) / 400))

    for marker in markers:
        quad = marker.corners_px.astype(np.int32)
        cv2.polylines(canvas, [quad], True, (0, 220, 0), thickness, cv2.LINE_AA)
        cv2.circle(canvas, tuple(quad[0]), thickness * 3, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.putText(
            canvas,
            str(marker.marker_id),
            tuple(marker.center_px.astype(int)),
            cv2.FONT_HERSHEY_SIMPLEX,
            thickness * 0.6,
            (0, 220, 0),
            thickness,
            cv2.LINE_AA,
        )
    return canvas
