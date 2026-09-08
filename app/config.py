"""Single Source of Truth fuer alle Konstanten des Projekts.

Jede Zahl, die an mehr als einer Stelle eine Rolle spielt, steht hier - und nur hier.
Module importieren aus diesem Modul, sie definieren nichts nach.

Die Werte selbst kommen zweigeteilt: was eine Aussage ueber das PRODUKT macht
(Millimeter, Schwellen, Farben, Papier) steht in `shared/constants.json`, was eine
Aussage ueber dieses PYTHON-PROGRAMM macht (Pfade, Port, Fassung, Speicherschluessel)
steht hier im Klartext. Nach aussen ist der Unterschied unsichtbar: `config.SHEET_MM`
liefert dasselbe wie zuvor.
"""

from __future__ import annotations

import json
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

# Ob dieser Prozess aus der gebauten .exe laeuft. Genau diese eine Stelle liest
# `sys._MEIPASS`; wer sonst noch wissen muss, ob eingefroren wurde, fragt hier.
# Gebraucht wird es ausserhalb der Pfade oben vom Rechenkern: im Quellbaum liegt
# er in core/build/, im Bundle als .pyd neben der Anwendung, und die Vorgabe fuer
# ARUCO_CORE haengt daran (app/vision/backend.py).
FROZEN = _BUNDLE_DIR is not None
BUNDLE_DIR = Path(_BUNDLE_DIR) if _BUNDLE_DIR else None


def resource_path(*parts: str) -> Path:
    """Pfad zu einer mitgelieferten Datei unterhalb von `app/`.

    Bedingung an die Bauvorschrift: `aruco-homographie.spec` muss den Baum in
    derselben Form ins Bundle legen (`app/static/...` bleibt `app/static/...`),
    sonst zeigt dieser Helfer im Bundle ins Leere.
    """
    return _PACKAGE_DIR.joinpath(*parts)


STATIC_DIR = resource_path("static")

# --- Geteilte Konstanten -------------------------------------------------------
# Alles, was eine Aussage ueber das PRODUKT macht - Millimeter, Schwellen, Farben,
# Papier - steht in shared/constants.json und NICHT hier. Der Grund ist der Umzug
# auf einen C++-Kern und eine JavaScript-PDF-Schicht (docs/cpp-migration/): drei
# Sprachen, die dieselben Zahlen brauchen. Eine Zahl, die in Python steht, muessten
# die anderen beiden abschreiben - und abgeschriebene Zahlen driften.
#
# Was ueber das PYTHON-PROGRAMM etwas aussagt - Pfade, Port, Fassung - bleibt hier.
_SHARED_DIR = (
    Path(_BUNDLE_DIR) / "shared"
    if _BUNDLE_DIR
    else Path(__file__).resolve().parent.parent / "shared"
)


def shared_path(*parts: str) -> Path:
    """Pfad zu einer Datei unter `shared/`, im Quellbaum wie im Bundle.

    Bedingung an die Bauvorschrift: `aruco-homographie.spec` muss `shared/` ins
    Bundle legen. Fehlt es dort, startet die .exe nicht - und das ist Absicht.
    Eine Anwendung, die mit halben Konstanten weiterlaeuft, misst falsch.
    """
    return _SHARED_DIR.joinpath(*parts)


# JSON kennt keine Tupel. Diese Schluessel sind in Python Tupel und werden beim
# Laden zurueckverwandelt - damit `config.SHEET_MM[0]` sich nicht ploetzlich anders
# verhaelt als vorher und `in`-Pruefungen auf DPI_CHOICES weiter stimmen.
_TUPLE_KEYS = frozenset({
    "SHEET_MM", "SHEET_SPACING_MM", "SHEET_MARKER_IDS", "DPI_CHOICES",
    "ADJUST_EDGE_CANNY", "SUPPORTED_LOCALES",
})


def _load_shared_constants() -> dict:
    """Liest shared/constants.json und macht aus Listen wieder Tupel.

    Kein Vorgabewert, kein try/except: fehlt die Datei, ist das Bundle kaputt und
    der Abbruch mit Dateinamen ist die freundlichste Meldung, die es dann gibt.
    """
    raw = json.loads(shared_path("constants.json").read_text(encoding="utf-8"))
    raw.pop("_comment", None)
    values = {}
    for key, value in raw.items():
        if key in _TUPLE_KEYS:
            values[key] = tuple(value)
        elif key == "SHEET_FORMATS":
            values[key] = {name: tuple(size) for name, size in value.items()}
        else:
            values[key] = value
    return values


# Jeder Name wird unten EINZELN gebunden, nicht per `globals().update()`. Das ist
# laenger, aber greifbar: `grep STRIP_H_MM app/config.py` findet die Stelle weiter,
# statische Pruefer sehen die Namen ohne `noqa`, ein Tippfehler im Schluessel faellt
# als KeyError beim Import auf statt als AttributeError irgendwo spaeter - und vor
# allem bleibt jeder Begruendungskommentar neben seiner Konstanten stehen. JSON
# kennt keine Kommentare; das Warum haette den Umzug sonst nicht ueberlebt.
SHARED_CONSTANTS = _load_shared_constants()

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
#
# Bleibt bewusst in Python: eine Fassung ist eine Aussage ueber DIESES Programm,
# nicht ueber das Produkt - der C++-Kern und der WASM-Bau bekommen eigene.
APP_VERSION = "0.1.5-alpha"

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
# notiert; in shared/constants.json stehen die umgerechneten sRGB-Werte, weil
# ReportLab und CSS im PDF beide Hex brauchen. Gegenprobe: --foreground
# oklch(0.3717 0.0392 257.29) ergibt #334155, genau die Tinte, die logo-dark.svg
# im Dateikommentar nennt.
BRAND_NAME = SHARED_CONSTANTS["BRAND_NAME"]
BRAND_CLAIM = SHARED_CONSTANTS["BRAND_CLAIM"]
BRAND_URL = SHARED_CONSTANTS["BRAND_URL"]
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

BRAND_INK = SHARED_CONSTANTS["BRAND_INK"]                  # --foreground, die Hausschrift-Tinte
BRAND_PRIMARY = SHARED_CONSTANTS["BRAND_PRIMARY"]          # --primary, das Petrol der Marke
BRAND_ACTION = SHARED_CONSTANTS["BRAND_ACTION"]            # --action, das Bernsteingelb fuer Aktionen
BRAND_DARK = SHARED_CONSTANTS["BRAND_DARK"]                # --action-foreground, der dunkle Grund
BRAND_LIGHT = SHARED_CONSTANTS["BRAND_LIGHT"]              # --primary-foreground, helle Schrift
BRAND_SECONDARY = SHARED_CONSTANTS["BRAND_SECONDARY"]      # --secondary
BRAND_ACCENT = SHARED_CONSTANTS["BRAND_ACCENT"]            # --accent
BRAND_DESTRUCTIVE = SHARED_CONSTANTS["BRAND_DESTRUCTIVE"]  # --destructive

BRAND_DIR = STATIC_DIR / "brand"
LOGO_INK_SVG = BRAND_DIR / "logo-dark.svg"      # #334155, fuers PDF
LOGO_BLACK_SVG = BRAND_DIR / "logo-black.svg"
LOGO_LIGHT_SVG = BRAND_DIR / "logo-light.svg"
LOGO_MM = SHARED_CONSTANTS["LOGO_MM"]            # Kantenlaenge des Logos auf dem Papier

# --- Marker ------------------------------------------------------------------
ARUCO_DICT_NAME = SHARED_CONSTANTS["ARUCO_DICT_NAME"]
# Die OpenCV-Kennung wird aus dem NAMEN abgeleitet und steht deshalb nicht in der
# sprachneutralen Datei: eine OpenCV-Zahl waere dort keine sprachneutrale Angabe,
# sondern eine Wette darauf, dass jede Bindung dieselbe Nummerierung benutzt.
ARUCO_DICT_ID = getattr(cv2.aruco, ARUCO_DICT_NAME)

# Nominale Kantenlaenge eines Markers INKLUSIVE schwarzem Rand. Das ist genau die
# Groesse, die cv2.aruco als Eckpunkte liefert, und die man am Ausdruck misst.
MARKER_MM_NOMINAL = SHARED_CONSTANTS["MARKER_MM_NOMINAL"]

# Markerblatt: A4 hoch, vier Marker auf einem Rechteck. Die Abstaende sind die am
# realen Blatt gemessenen Mittelpunktabstaende (x, y).
SHEET_MM = SHARED_CONSTANTS["SHEET_MM"]
SHEET_SPACING_MM = SHARED_CONSTANTS["SHEET_SPACING_MM"]

# Zuordnung der IDs auf dem mitgelieferten Blatt: 0 = oben links, 1 = oben rechts,
# 2 = unten links, 3 = unten rechts.
SHEET_MARKER_IDS = SHARED_CONSTANTS["SHEET_MARKER_IDS"]


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
DPI_DEFAULT = SHARED_CONSTANTS["DPI_DEFAULT"]
DPI_CHOICES = SHARED_CONSTANTS["DPI_CHOICES"]
MAX_OUTPUT_MPX = SHARED_CONSTANTS["MAX_OUTPUT_MPX"]
MAX_UPLOAD_MB = SHARED_CONSTANTS["MAX_UPLOAD_MB"]
PREVIEW_MAX_PX = SHARED_CONSTANTS["PREVIEW_MAX_PX"]
DEFAULT_CROP_MAX_MM = SHARED_CONSTANTS["DEFAULT_CROP_MAX_MM"]
JPEG_QUALITY = SHARED_CONSTANTS["JPEG_QUALITY"]

# --- Qualitaetsschwellen ------------------------------------------------------
RMS_WARN_PX = SHARED_CONSTANTS["RMS_WARN_PX"]
RMS_WARN_MM = SHARED_CONSTANTS["RMS_WARN_MM"]
# 2 % Abweichung der gemessenen Markergroesse
MARKER_SIZE_DEV_WARN = SHARED_CONSTANTS["MARKER_SIZE_DEV_WARN"]
# Frei-Modus setzt gleiche Ausrichtung voraus
MARKER_ROT_WARN_DEG = SHARED_CONSTANTS["MARKER_ROT_WARN_DEG"]
# Crop-Flaechenanteil ausserhalb der Marker-Huelle
EXTRAPOLATION_WARN_FRAC = SHARED_CONSTANTS["EXTRAPOLATION_WARN_FRAC"]
# Huellflaeche der Mittelpunkte / groesster Abstand^2
COLLINEARITY_WARN = SHARED_CONSTANTS["COLLINEARITY_WARN"]
CAM_HEIGHT_MIN_MM = SHARED_CONSTANTS["CAM_HEIGHT_MIN_MM"]
CAM_HEIGHT_MAX_MM = SHARED_CONSTANTS["CAM_HEIGHT_MAX_MM"]
# Sicherheitsabstand zum Fluchtpunkt-Horizont
HORIZON_EPS = SHARED_CONSTANTS["HORIZON_EPS"]
# Klammer fuer den abbildbaren Bereich
EXTENT_HULL_FACTOR = SHARED_CONSTANTS["EXTENT_HULL_FACTOR"]

# --- PDF-Geometrie ------------------------------------------------------------
# Was der Bediener bekommt, wenn er nichts waehlt: verteilen und zusammenkleben.
# Eine Schablone in Originalgroesse passt auf kein Blatt, das hier jemand im
# Drucker hat - die Einzelseite ist der Sonderfall, nicht der Regelfall.
# ACHTUNG: das ist die Vorgabe fuer die BEDIENUNG (app/schemas.py). Die
# PDF-Schicht selbst (ExportOptions in app/pdf/build.py) hat bewusst eine andere:
# dort ist "eine Seite" der schlichte Fall, und Kachelung eine Betriebsart.
LAYOUT_DEFAULT = SHARED_CONSTANTS["LAYOUT_DEFAULT"]
PAGE_MARGIN_MM_DEFAULT = SHARED_CONSTANTS["PAGE_MARGIN_MM_DEFAULT"]
PRINTER_MARGIN_MM_DEFAULT = SHARED_CONSTANTS["PRINTER_MARGIN_MM_DEFAULT"]
TILE_OVERLAP_MM_DEFAULT = SHARED_CONSTANTS["TILE_OVERLAP_MM_DEFAULT"]
TILE_OVERVIEW_DEFAULT = SHARED_CONSTANTS["TILE_OVERVIEW_DEFAULT"]
# Der Klebeplan zeigt den Zuschnitt als Bild unter der Kachelung - aber als
# Daumennagel. Er wird ANGESEHEN und nicht nachgemessen: mehr als 1600 Pixel auf
# der langen Kante sind auf einem A4-Blatt (hoechstens 250 mm hoch, also rund
# 160 dpi) nicht mehr zu sehen, kosten aber Dateigroesse - und auf dem Telefon
# Arbeitsspeicher, den der blattweise Export gerade erst eingespart hat.
OVERVIEW_MAX_PX = SHARED_CONSTANTS["OVERVIEW_MAX_PX"]
# Massstab links, Metadaten rechts (Spec 4.2)
STRIP_H_MM = SHARED_CONSTANTS["STRIP_H_MM"]
GRID_STEP_MM = SHARED_CONSTANTS["GRID_STEP_MM"]
# Das Raster muss auf hellem UND dunklem Untergrund lesbar sein. Deshalb wird jede
# Linie zweimal gezogen: erst ein breiter weisser Saum, dann die Kernlinie in
# Markentinte. Auf Weiss verschwindet der Saum, auf Schwarz traegt er die Linie.
GRID_INK = BRAND_INK
GRID_LINE_PT = SHARED_CONSTANTS["GRID_LINE_PT"]
GRID_HALO_PT = SHARED_CONSTANTS["GRID_HALO_PT"]
GRID_LABEL_PT = SHARED_CONSTANTS["GRID_LABEL_PT"]
SCALEBAR_MM = SHARED_CONSTANTS["SCALEBAR_MM"]
CONTOUR_LINE_MM = SHARED_CONSTANTS["CONTOUR_LINE_MM"]
CONTOUR_EPS_MM = SHARED_CONSTANTS["CONTOUR_EPS_MM"]
CONTOUR_MIN_AREA_FRAC = SHARED_CONSTANTS["CONTOUR_MIN_AREA_FRAC"]

# Papierformate fuer die Kachelung, immer (Breite, Hoehe) im Hochformat.
SHEET_FORMATS = SHARED_CONSTANTS["SHEET_FORMATS"]

# --- Sprachen -----------------------------------------------------------------
# Oberflaeche und PDF sprechen dieselben Kataloge. Sie liegen unter app/static/i18n/,
# damit der Browser sie direkt laden kann UND Python sie lesen kann - eine Datei je
# Sprache, keine zweite Fassung fuer den Server.
LOCALE_DIR = STATIC_DIR / "i18n"
SUPPORTED_LOCALES = SHARED_CONSTANTS["SUPPORTED_LOCALES"]
DEFAULT_LOCALE = SHARED_CONSTANTS["DEFAULT_LOCALE"]
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
# Kachelraster fuer den lokalen Kontrast
ADJUST_CLAHE_TILES = SHARED_CONSTANTS["ADJUST_CLAHE_TILES"]
# Obergrenze des CLAHE-Clip-Limits bei Staerke 1.0
ADJUST_CLAHE_CLIP_MAX = SHARED_CONSTANTS["ADJUST_CLAHE_CLIP_MAX"]
# Radius der Unschaerfemaske fuer die Kantenanhebung
ADJUST_UNSHARP_SIGMA_PX = SHARED_CONSTANTS["ADJUST_UNSHARP_SIGMA_PX"]
# Maximaler Anteil der Maske bei Staerke 1.0
ADJUST_UNSHARP_MAX = SHARED_CONSTANTS["ADJUST_UNSHARP_MAX"]
# Schwellen fuer die aufgelegte Kantenzeichnung
ADJUST_EDGE_CANNY = SHARED_CONSTANTS["ADJUST_EDGE_CANNY"]
# Halbe Breite des betonten Farbtonfensters (HSV-Grad)
ADJUST_EMPHASIS_SIGMA_DEG = SHARED_CONSTANTS["ADJUST_EMPHASIS_SIGMA_DEG"]
# Farbtonmitten in OpenCV-HSV (0..179) fuer die waehlbaren Farbbetonungen.
ADJUST_EMPHASIS_HUES = SHARED_CONSTANTS["ADJUST_EMPHASIS_HUES"]

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
MM_PER_INCH = SHARED_CONSTANTS["MM_PER_INCH"]
PT_PER_MM = 72.0 / MM_PER_INCH       # ReportLab rechnet in Punkt
