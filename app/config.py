"""Single Source of Truth fuer alle Konstanten des Projekts.

Jede Zahl, die an mehr als einer Stelle eine Rolle spielt, steht hier - und nur hier.
Module importieren aus diesem Modul, sie definieren nichts nach.
"""

from __future__ import annotations

from pathlib import Path

import cv2

# --- Marke ---------------------------------------------------------------------
# Die Farben stammen aus snow-service-free/src/main.css und sind dort als oklch
# notiert; hier stehen die umgerechneten sRGB-Werte, weil ReportLab und CSS im
# PDF beide Hex brauchen. Gegenprobe: --foreground oklch(0.3717 0.0392 257.29)
# ergibt #334155, genau die Tinte, die logo-dark.svg im Dateikommentar nennt.
BRAND_NAME = "Bischof Snowboards"
BRAND_CLAIM = "Made with Bischof Snowboards Software"
BRAND_URL = "https://bischof-snowboards.com"

BRAND_INK = "#334155"            # --foreground, die Hausschrift-Tinte
BRAND_PRIMARY = "#379992"        # --primary, das Petrol der Marke
BRAND_ACTION = "#ffbf00"         # --action, das Bernsteingelb fuer Aktionen
BRAND_DARK = "#25242b"           # --action-foreground, der dunkle Grund
BRAND_LIGHT = "#f1f5f9"          # --primary-foreground, helle Schrift
BRAND_SECONDARY = "#e2e8f0"      # --secondary
BRAND_ACCENT = "#f0f3f3"         # --accent
BRAND_DESTRUCTIVE = "#e7000b"    # --destructive

BRAND_DIR = Path(__file__).parent / "static" / "brand"
LOGO_INK_SVG = BRAND_DIR / "logo-dark.svg"      # #334155, fuers PDF
LOGO_BLACK_SVG = BRAND_DIR / "logo-black.svg"
LOGO_LIGHT_SVG = BRAND_DIR / "logo-light.svg"
LOGO_MM = 11.0                   # Kantenlaenge des Logos auf dem Papier

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
# Was der Bediener bekommt, wenn er nichts waehlt: verteilen und zusammenkleben.
# Eine Schablone in Originalgroesse passt auf kein Blatt, das hier jemand im
# Drucker hat - die Einzelseite ist der Sonderfall, nicht der Regelfall.
# ACHTUNG: das ist die Vorgabe fuer die BEDIENUNG (app/schemas.py). Die
# PDF-Schicht selbst (ExportOptions in app/pdf/build.py) hat bewusst eine andere:
# dort ist "eine Seite" der schlichte Fall, und Kachelung eine Betriebsart.
LAYOUT_DEFAULT = "tiles"
PAGE_MARGIN_MM_DEFAULT = 5.0
PRINTER_MARGIN_MM_DEFAULT = 5.0
TILE_OVERLAP_MM_DEFAULT = 10.0
TILE_OVERVIEW_DEFAULT = True
STRIP_H_MM = 18.0                    # Massstab links, Metadaten rechts (Spec 4.2)
GRID_STEP_MM = 50.0
# Das Raster muss auf hellem UND dunklem Untergrund lesbar sein. Deshalb wird jede
# Linie zweimal gezogen: erst ein breiter weisser Saum, dann die Kernlinie in
# Markentinte. Auf Weiss verschwindet der Saum, auf Schwarz traegt er die Linie.
GRID_INK = BRAND_INK
GRID_LINE_PT = 0.5
GRID_HALO_PT = 1.5
GRID_LABEL_PT = 6.5
SCALEBAR_MM = 100.0
CONTOUR_LINE_MM = 0.25
CONTOUR_EPS_MM = 0.5
CONTOUR_MIN_AREA_FRAC = 0.05

# Papierformate fuer die Kachelung, immer (Breite, Hoehe) im Hochformat.
SHEET_FORMATS = {"A4": (210.0, 297.0), "A3": (297.0, 420.0)}

# --- Sprachen -----------------------------------------------------------------
# Oberflaeche und PDF sprechen dieselben Kataloge. Sie liegen unter app/static/i18n/,
# damit der Browser sie direkt laden kann UND Python sie lesen kann - eine Datei je
# Sprache, keine zweite Fassung fuer den Server.
LOCALE_DIR = Path(__file__).parent / "static" / "i18n"
SUPPORTED_LOCALES = ("de", "en")
DEFAULT_LOCALE = "de"
# Schluessel, unter dem der Browser die zuletzt gewaehlte Sprache merkt. Der Name
# folgt snow-service-free ("free-language"), damit die Werkzeuge des Hauses sich
# gleich verhalten.
LOCALE_STORAGE_KEY = "aruco-language"
THEME_STORAGE_KEY = "aruco-theme"

# --- Bildaufbereitung ---------------------------------------------------------
# Die Aufbereitung greift AUSSCHLIESSLICH am entzerrten Bild an, niemals vor der
# Markererkennung: die Homographie wird am unveraenderten Foto gemessen. Sonst
# wuerde ein Schaerferegler die Millimeter verschieben - und Millimeter sind hier
# das Produkt (siehe AGENTS.md, Invarianten).
ADJUST_CLAHE_TILES = 8               # Kachelraster fuer den lokalen Kontrast
ADJUST_CLAHE_CLIP_MAX = 4.0          # Obergrenze des CLAHE-Clip-Limits bei Staerke 1.0
ADJUST_UNSHARP_SIGMA_PX = 2.0        # Radius der Unschaerfemaske fuer die Kantenanhebung
ADJUST_UNSHARP_MAX = 2.0             # Maximaler Anteil der Maske bei Staerke 1.0
ADJUST_EDGE_CANNY = (60, 160)        # Schwellen fuer die aufgelegte Kantenzeichnung
ADJUST_EMPHASIS_SIGMA_DEG = 25.0     # Halbe Breite des betonten Farbtonfensters (HSV-Grad)
# Farbtonmitten in OpenCV-HSV (0..179) fuer die waehlbaren Farbbetonungen.
ADJUST_EMPHASIS_HUES = {
    "red": 0,
    "yellow": 22,
    "green": 60,
    "cyan": 90,
    "blue": 120,
    "magenta": 150,
}

# --- Server -------------------------------------------------------------------
SESSION_TTL_S = 3600
HOST = "0.0.0.0"
PORT = 8000

# --- Einheiten ----------------------------------------------------------------
PT_PER_MM = 72.0 / 25.4              # ReportLab rechnet in Punkt
MM_PER_INCH = 25.4
