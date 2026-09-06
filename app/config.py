"""Single Source of Truth fuer alle Konstanten des Projekts.

Jede Zahl, die an mehr als einer Stelle eine Rolle spielt, steht hier - und nur hier.
Module importieren aus diesem Modul, sie definieren nichts nach.
"""

from __future__ import annotations

import cv2

# --- Marker ------------------------------------------------------------------
ARUCO_DICT_NAME = "DICT_4X4_50"
ARUCO_DICT_ID = cv2.aruco.DICT_4X4_50

# Nominale Kantenlaenge eines Markers INKLUSIVE schwarzem Rand. Das ist genau die
# Groesse, die cv2.aruco als Eckpunkte liefert, und die man am Ausdruck misst.
MARKER_MM_NOMINAL = 67.0

# Markerblatt: A4 hoch, vier Marker auf einem Rechteck. Die Abstaende sind die am
# realen Blatt gemessenen Mittelpunktabstaende (x, y).
SHEET_MM = (210.0, 297.0)
SHEET_SPACING_MM = (121.0, 171.0)

# Zuordnung der IDs auf dem mitgelieferten Blatt: 0 = oben links, 1 = oben rechts,
# 2 = unten links, 3 = unten rechts.
SHEET_MARKER_IDS = (0, 1, 2, 3)


def sheet_marker_centers(
    spacing_mm: tuple[float, float] = SHEET_SPACING_MM,
) -> dict[int, tuple[float, float]]:
    """Markermittelpunkte in mm, mittig auf A4, y von oben gezaehlt.

    Die einzige Stelle, an der aus zwei Abstaenden vier Positionen werden -
    Markerblatt-Erzeugung und Homographie benutzen beide diese Funktion.
    """
    spacing_x, spacing_y = spacing_mm
    centre_x, centre_y = SHEET_MM[0] / 2.0, SHEET_MM[1] / 2.0
    return {
        0: (centre_x - spacing_x / 2.0, centre_y - spacing_y / 2.0),
        1: (centre_x + spacing_x / 2.0, centre_y - spacing_y / 2.0),
        2: (centre_x - spacing_x / 2.0, centre_y + spacing_y / 2.0),
        3: (centre_x + spacing_x / 2.0, centre_y + spacing_y / 2.0),
    }


SHEET_MARKER_CENTERS_MM = sheet_marker_centers()

# --- Aufloesung und Groessengrenzen -------------------------------------------
DPI_DEFAULT = 300
DPI_CHOICES = (150, 200, 300, 400, 600)
MAX_OUTPUT_MPX = 300.0
MAX_UPLOAD_MB = 60
PREVIEW_MAX_PX = 1600
DEFAULT_CROP_MAX_MM = 1500.0
JPEG_QUALITY = 92

# --- Qualitaetsschwellen ------------------------------------------------------
RMS_WARN_PX = 2.0
RMS_WARN_MM = 1.0
MARKER_SIZE_DEV_WARN = 0.02          # 2 % Abweichung der gemessenen Markergroesse
MARKER_ROT_WARN_DEG = 2.0            # Frei-Modus setzt gleiche Ausrichtung voraus
EXTRAPOLATION_WARN_FRAC = 0.25       # Crop-Flaechenanteil ausserhalb der Marker-Huelle
COLLINEARITY_WARN = 0.05             # Huellflaeche der Mittelpunkte / groesster Abstand^2
CAM_HEIGHT_MIN_MM = 100.0
CAM_HEIGHT_MAX_MM = 10000.0
HORIZON_EPS = 0.02                   # Sicherheitsabstand zum Fluchtpunkt-Horizont
EXTENT_HULL_FACTOR = 3.0             # Klammer fuer den abbildbaren Bereich

# --- PDF-Geometrie ------------------------------------------------------------
PAGE_MARGIN_MM_DEFAULT = 5.0
PRINTER_MARGIN_MM_DEFAULT = 5.0
TILE_OVERLAP_MM_DEFAULT = 10.0
TILE_OVERVIEW_DEFAULT = True
STRIP_H_MM = 18.0                    # Massstab links, Metadaten rechts (Spec 4.2)
GRID_STEP_MM = 50.0
GRID_GRAY = 0.75
SCALEBAR_MM = 100.0
CONTOUR_LINE_MM = 0.25
CONTOUR_EPS_MM = 0.5
CONTOUR_MIN_AREA_FRAC = 0.05

# Papierformate fuer die Kachelung, immer (Breite, Hoehe) im Hochformat.
SHEET_FORMATS = {"A4": (210.0, 297.0), "A3": (297.0, 420.0)}

# --- Server -------------------------------------------------------------------
SESSION_TTL_S = 3600
HOST = "0.0.0.0"
PORT = 8000

# --- Einheiten ----------------------------------------------------------------
PT_PER_MM = 72.0 / 25.4              # ReportLab rechnet in Punkt
MM_PER_INCH = 25.4
