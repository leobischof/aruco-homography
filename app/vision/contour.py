"""Optionale Umriss-Erkennung im bereits entzerrten Bild.

Das Ergebnis ist eine Schnitthilfe, kein Messwerkzeug: es steht und faellt mit dem
Kontrast zwischen Objekt und Untergrund. Findet sich nichts Plausibles, wird das
gemeldet und das PDF ohne Kontur gebaut - lieber keine Linie als eine falsche.

Koordinaten kommen in Millimetern relativ zur linken oberen Ecke des Zuschnitts
zurueck, y nach unten (wie im Bild). Die PDF-Schicht dreht y einmalig um.
"""

from __future__ import annotations

import cv2
import numpy as np

from app import config


def find_contour_mm(rectified_bgr: np.ndarray, px_per_mm: float) -> np.ndarray | None:
    """Groesste plausible Aussenkontur als (N,2)-Polygon in mm, sonst None."""
    gray = cv2.cvtColor(rectified_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)

    # Canny-Schwellen aus dem Bildmedian: robuster als feste Werte ueber
    # verschiedene Belichtungen hinweg.
    median = float(np.median(blurred))
    edges = cv2.Canny(blurred, int(max(0, 0.66 * median)), int(min(255, 1.33 * median)))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    image_area = float(rectified_bgr.shape[0] * rectified_bgr.shape[1])
    if cv2.contourArea(largest) < config.CONTOUR_MIN_AREA_FRAC * image_area:
        return None

    simplified = cv2.approxPolyDP(largest, config.CONTOUR_EPS_MM * px_per_mm, True)
    return simplified.reshape(-1, 2).astype(np.float64) / px_per_mm


def bounding_box_mm(contour_mm: np.ndarray) -> tuple[float, float]:
    """Breite und Hoehe der Kontur in mm - fuer die Fusszeile."""
    return (
        float(np.ptp(contour_mm[:, 0])),
        float(np.ptp(contour_mm[:, 1])),
    )
