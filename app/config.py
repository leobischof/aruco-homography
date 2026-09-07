"""Single Source of Truth fuer alle Konstanten des Projekts.

Jede Zahl, die an mehr als einer Stelle eine Rolle spielt, steht hier - und nur hier.
Module importieren aus diesem Modul, sie definieren nichts nach.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2

# --- Pfade zu mitgelieferten Dateien ------------------------------------------
# `Path(__file__).parent` bedeutet in einer eingefrorenen .exe etwas anderes als im
# Quellbaum: PyInstaller legt die Datendateien in ein eigenes Verzeichnis (im
# One-Folder-Modus `_internal/`) und nennt es `sys._MEIPASS`. Der Modulpfad zeigt
# dann daneben - die Anwendung startet, liefert aber eine Seite ohne Schrift, ohne
# Logo und ohne Uebersetzung. Deshalb geht JEDER Pfad auf eine Datendatei durch
# diesen einen Helfer, und er liefert in beiden Faellen dasselbe.
_BUNDLE_DIR = getattr(sys, "_MEIPASS", None)   # nur im PyInstaller-Bundle gesetzt
_PACKAGE_DIR = Path(_BUNDLE_DIR) / "app" if _BUNDLE_DIR else Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    """Pfad zu einer mitgelieferten Datei unterhalb von `app/`.

    Bedingung an die Bauvorschrift: `aruco-homographie.spec` muss den Baum in
    derselben Form ins Bundle legen (`app/static/...` bleibt `app/static/...`),
    sonst zeigt dieser Helfer im Bundle ins Leere.
    """
    return _PACKAGE_DIR.joinpath(*parts)


STATIC_DIR = resource_path("static")

# --- Name ----------------------------------------------------------------------
# Der Produktname: Titel der FastAPI-Anwendung, Beschriftung des eigenen Fensters,
# Name der .exe und des Ordners um sie herum (aruco-homographie.spec liest ihn von
# hier). Eine Marke, kein uebersetzbarer Satz - deshalb steht er hier und nicht im
# Sprachkatalog.
APP_NAME = "ArUco-Homographie"

# --- Fassung -------------------------------------------------------------------
# Die Versionsnummer steht NUR hier. `dev.ps1 build-installer` liest sie von hier
# und reicht sie als /D-Definition an Inno Setup weiter - genauso, wie der Port
# schon von hier gelesen wird. Eine zweite Zahl in `installer/aruco-homographie.iss`
# waere die Sorte Duplikat, die still veraltet: der Installer hiesse dann anders,
# als die Anwendung von sich behauptet, und niemand merkte es.
# Der Wert folgt der obersten veroeffentlichten Ueberschrift in CHANGELOG.md.
APP_VERSION = "0.0.2-alpha"

# Windows will in den BINAEREN Versionsfeldern seiner Dateieigenschaften vier ganze
# Zahlen sehen und vertraegt kein "-alpha". Die Vorabkennung wird deshalb hier
# EINMAL abgeschnitten und auf vier Stellen aufgefuellt; die PyInstaller-Vorschrift
# und der Inno-Installer nehmen beide dieses Ergebnis, statt die Regel jeder fuer
# sich noch einmal zu erfinden. Der lesbare Text bleibt daneben APP_VERSION - in den
# Zeichenkettenfeldern ist er erlaubt, und dort will man ihn auch sehen.
APP_VERSION_TUPLE = tuple(
    int(part) for part in (APP_VERSION.split("-", 1)[0].split(".") + ["0"] * 4)[:4]
)
APP_VERSION_NUMERIC = ".".join(str(part) for part in APP_VERSION_TUPLE)

# --- Marke ---------------------------------------------------------------------
# Die Farben stammen aus snow-service-free/src/main.css und sind dort als oklch
# notiert; hier stehen die umgerechneten sRGB-Werte, weil ReportLab und CSS im
# PDF beide Hex brauchen. Gegenprobe: --foreground oklch(0.3717 0.0392 257.29)
# ergibt #334155, genau die Tinte, die logo-dark.svg im Dateikommentar nennt.
BRAND_NAME = "Bischof Snowboards"
BRAND_CLAIM = "Made with Bischof Snowboards Software"
BRAND_URL = "https://bischof-snowboards.com"
# Die Zeile, die in den Dateieigenschaften beider .exe unter "Copyright" steht.
#
# Bewusst OHNE Jahreszahl: sie veraltete sonst jeden Januar still, und ein
# Urheberrechtsvermerk braucht keine.
#
# Bewusst mit "(C)" statt dem Zeichen (C-im-Kreis), obwohl im Ausdruck spaeter das
# Zeichen steht. Der Wert reist ueber zwei Stellen, an denen ein Sonderzeichen von
# der Codepage abhaengt: Python schreibt ihn auf die Standardausgabe, PowerShell
# liest ihn zurueck (dev.ps1) und gibt ihn an ISCC weiter. Gemessen: auf DIESEM
# Rechner steht die Konsole auf UTF-8 und es geht gut - auf einer Konsole mit
# cp850, der Vorgabe, wuerde aus dem Zeichen lautlos ein anderes. Reines ASCII
# ueberlebt jede dieser Stationen.
#
# Sichtbar wird trotzdem das richtige Zeichen: Inno Setup ersetzt "(C)" in
# VersionInfoCopyright von sich aus (nachgemessen), und aruco-homographie.spec tut
# im eigenen Prozess dasselbe. Beide .exe zeigen deshalb denselben Text.
BRAND_COPYRIGHT = f"Copyright (C) {BRAND_NAME}"

BRAND_INK = "#334155"            # --foreground, die Hausschrift-Tinte
BRAND_PRIMARY = "#379992"        # --primary, das Petrol der Marke
BRAND_ACTION = "#ffbf00"         # --action, das Bernsteingelb fuer Aktionen
BRAND_DARK = "#25242b"           # --action-foreground, der dunkle Grund
BRAND_LIGHT = "#f1f5f9"          # --primary-foreground, helle Schrift
BRAND_SECONDARY = "#e2e8f0"      # --secondary
BRAND_ACCENT = "#f0f3f3"         # --accent
BRAND_DESTRUCTIVE = "#e7000b"    # --destructive

BRAND_DIR = STATIC_DIR / "brand"
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
LOCALE_DIR = STATIC_DIR / "i18n"
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
# BEVORZUGTER Port, keine Zusage. Auf einem Werkstattrechner haelt schnell irgendetwas
# anderes die 8000, und ein Doppelklick, der mit "address already in use" abbricht,
# ist kein Programm. app.main.choose_port() nimmt diesen Port, wenn er frei ist, und
# sonst einen beliebigen freien - die stabile URL bleibt der Normalfall.
PORT = 8000
# Wie lange der Browser-Faden auf den Server wartet, bevor er aufgibt. Eine .exe auf
# kaltem Dateisystem entpackt OpenCV beim ersten Start spuerbar lange.
BROWSER_WAIT_S = 60.0

# --- Eigenes Fenster ----------------------------------------------------------
# Die Anwendung zeigt sich in einem eigenen Fenster (pywebview) statt in einem
# Browser-Reiter; der Server dahinter bleibt derselbe.
#
# Die Breite ist so gewaehlt, dass die Oberflaeche ihre volle Breite bekommt: der
# Inhalt ist auf 68 rem = 1088 px begrenzt (app/static/css/layout.css) und traegt
# links und rechts 24 px Rand - macht 1136 px, ab denen nichts mehr gewonnen ist.
WINDOW_SIZE = (1200, 860)
# Untergrenze, damit das Fenster nicht auf eine Groesse gezogen werden kann, in der
# die Schrittfolge nicht mehr zu bedienen ist. 900 px liegen ueber dem Umbruchpunkt
# der Oberflaeche (768 px), das Fenster bleibt also immer im Rechner-Layout.
WINDOW_MIN_SIZE = (900, 600)
# Wie lange nach dem Schliessen des Fensters auf das Ende des Servers gewartet wird.
# Die Frist ist nur die Gelegenheit, sich sauber zu verabschieden: der Serverfaden
# ist ein Daemon und endet mit dem Prozess, ob er will oder nicht. Sie ist da, damit
# eine laufende Antwort noch hinausgeht, nicht damit irgendetwas haengen bleibt.
SERVER_STOP_WAIT_S = 5.0

# --- Einheiten ----------------------------------------------------------------
PT_PER_MM = 72.0 / 25.4              # ReportLab rechnet in Punkt
MM_PER_INCH = 25.4
