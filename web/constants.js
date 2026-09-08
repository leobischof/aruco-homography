/**
 * constants.js - die Produktkonstanten fuer JavaScript, gelesen aus
 * shared/constants.json.
 *
 * Dieselbe Datei, die auch app/config.py liest. Keine zweite Fassung, kein
 * abgetippter Millimeter (AGENTS.md, Invariante 4): eine Zahl, die hier noch
 * einmal im Klartext staende, wuerde von der Python-Referenz wegdriften - und
 * zwar in Millimetern.
 *
 * Geladen wird per JSON-Import-Attribut statt ueber `fs`. Das ist Absicht: dieses
 * Modul muss im Browser laufen, und dort gibt es kein Dateisystem. Node 22 und
 * die aktuellen Browser koennen beide `import ... with { type: "json" }`.
 *
 * Es liegt in web/ und nicht mehr in web/pdf/, seit es zwei Verbraucher hat:
 * den PDF-Bau und den Rechenweg im Browser (web/vision/). Eine zweite Fassung
 * je Verbraucher waere genau die Stelle, an der Millimeter auseinanderlaufen.
 *
 * Jeder Name wird EINZELN gebunden, genau wie in app/config.py: ein Tippfehler
 * im Schluessel faellt hier beim Laden auf statt spaeter als `undefined` in einer
 * Millimeterrechnung. Ein `undefined` in einer Multiplikation ergibt NaN, und ein
 * NaN in der MediaBox ist ein Blatt ohne Groesse.
 */

import shared from "../shared/constants.json" with { type: "json" };

// --- Einheiten -----------------------------------------------------------------
export const MM_PER_INCH = shared.MM_PER_INCH;

// --- Marker und Markerblatt ----------------------------------------------------
export const ARUCO_DICT_NAME = shared.ARUCO_DICT_NAME;
export const MARKER_MM_NOMINAL = shared.MARKER_MM_NOMINAL;
export const SHEET_MM = Object.freeze([...shared.SHEET_MM]);
export const SHEET_SPACING_MM = Object.freeze([...shared.SHEET_SPACING_MM]);
export const SHEET_MARKER_IDS = Object.freeze([...shared.SHEET_MARKER_IDS]);

// --- Der Rechenweg -------------------------------------------------------------
// Alles, was app/vision/ aus config.py holt. Erst gebraucht, seit derselbe
// Rechenweg auch im Browser laeuft (web/vision/).
export const MAX_OUTPUT_MPX = shared.MAX_OUTPUT_MPX;

/**
 * Wieviele Ausgabepixel HIER moeglich sind - Produktgrenze und Geraetegrenze,
 * die kleinere gewinnt.
 *
 * `MAX_OUTPUT_MPX` steht in shared/constants.json und sagt, was das FORMAT
 * hergibt: 300 Megapixel, auf jedem Ziel dieselbe Zahl. Was die MASCHINE
 * hergibt, ist eine andere Frage und gehoert deshalb nicht dorthin -
 * 300 MPx sind beim Export 900 MB Raster, und ein Telefon hat sie nicht.
 *
 * Die Android-Huelle setzt `globalThis.ARUCO_MAX_OUTPUT_MPX` aus dem wirklich
 * verfuegbaren Speicher (bridge-shim.js <- NativeImages.budgetMegapixels).
 * Fehlt der Wert - Browser, Node, Schreibtisch -, gilt die Produktgrenze.
 *
 * Ohne das brach der Export auf dem Telefon mit einem OutOfMemoryError ab,
 * den die WebView verschluckte: "Java exception was raised during method
 * invocation", ohne ein Wort darueber, was zu tun waere. Mit der Grenze faellt
 * derselbe Fall in `output_too_large` - eine uebersetzte Meldung, die eine
 * kleinere Aufloesung oder einen kleineren Ausschnitt vorschlaegt.
 */
export function outputBudgetMpx() {
    const device = globalThis.ARUCO_MAX_OUTPUT_MPX;
    return Number.isFinite(device) && device > 0
        ? Math.min(MAX_OUTPUT_MPX, device)
        : MAX_OUTPUT_MPX;
}
/**
 * Pixel je Millimeter fuer eine Aufloesung in dpi.
 *
 * Steht HIER und nicht in web/vision/rectify.js, weil beide Schichten sie
 * brauchen und die PDF-Schicht die Sichtschicht nicht kennen darf: web/pdf/
 * laeuft auch unter Node aus der Python-Suite (ARUCO_PDF=js), wo es kein
 * web/vision/ gibt. Zwei Fassungen derselben Division waeren die Sorte
 * Duplikat, die man erst am schiefen Ausdruck bemerkt.
 */
export function pxPerMmForDpi(dpi) {
    return dpi / MM_PER_INCH;
}

export const MAX_UPLOAD_MB = shared.MAX_UPLOAD_MB;
export const PREVIEW_MAX_PX = shared.PREVIEW_MAX_PX;
export const DEFAULT_CROP_MAX_MM = shared.DEFAULT_CROP_MAX_MM;
export const DPI_CHOICES = Object.freeze([...shared.DPI_CHOICES]);
export const RMS_WARN_PX = shared.RMS_WARN_PX;
export const RMS_WARN_MM = shared.RMS_WARN_MM;
export const MARKER_SIZE_DEV_WARN = shared.MARKER_SIZE_DEV_WARN;
export const MARKER_ROT_WARN_DEG = shared.MARKER_ROT_WARN_DEG;
export const EXTRAPOLATION_WARN_FRAC = shared.EXTRAPOLATION_WARN_FRAC;
export const COLLINEARITY_WARN = shared.COLLINEARITY_WARN;
export const CAM_HEIGHT_MIN_MM = shared.CAM_HEIGHT_MIN_MM;
export const CAM_HEIGHT_MAX_MM = shared.CAM_HEIGHT_MAX_MM;
export const HORIZON_EPS = shared.HORIZON_EPS;
export const EXTENT_HULL_FACTOR = shared.EXTENT_HULL_FACTOR;
export const CONTOUR_EPS_MM = shared.CONTOUR_EPS_MM;
export const CONTOUR_MIN_AREA_FRAC = shared.CONTOUR_MIN_AREA_FRAC;
export const LAYOUT_DEFAULT = shared.LAYOUT_DEFAULT;

// Die Farbtoene der Farbbetonung. Nur die SCHLUESSEL werden hier gebraucht - die
// Gradzahlen dahinter rechnet der Kern (core/src/enhance.cpp), und die Liste
// entscheidet allein, welche Auswahl gueltig ist.
export const ADJUST_EMPHASIS_HUES = Object.freeze({ ...shared.ADJUST_EMPHASIS_HUES });

// --- PDF-Geometrie -------------------------------------------------------------
export const DPI_DEFAULT = shared.DPI_DEFAULT;
export const JPEG_QUALITY = shared.JPEG_QUALITY;
export const PAGE_MARGIN_MM_DEFAULT = shared.PAGE_MARGIN_MM_DEFAULT;
export const PRINTER_MARGIN_MM_DEFAULT = shared.PRINTER_MARGIN_MM_DEFAULT;
export const TILE_OVERLAP_MM_DEFAULT = shared.TILE_OVERLAP_MM_DEFAULT;
export const TILE_OVERVIEW_DEFAULT = shared.TILE_OVERVIEW_DEFAULT;
export const STRIP_H_MM = shared.STRIP_H_MM;
export const GRID_STEP_MM = shared.GRID_STEP_MM;
export const GRID_LINE_PT = shared.GRID_LINE_PT;
export const GRID_HALO_PT = shared.GRID_HALO_PT;
export const GRID_LABEL_PT = shared.GRID_LABEL_PT;
export const SCALEBAR_MM = shared.SCALEBAR_MM;
export const CONTOUR_LINE_MM = shared.CONTOUR_LINE_MM;
export const SHEET_FORMATS = Object.freeze(
    Object.fromEntries(
        Object.entries(shared.SHEET_FORMATS).map(([name, size]) => [name, Object.freeze([...size])]),
    ),
);

// --- Marke ---------------------------------------------------------------------
export const BRAND_NAME = shared.BRAND_NAME;
export const BRAND_CLAIM = shared.BRAND_CLAIM;
export const BRAND_URL = shared.BRAND_URL;
export const BRAND_INK = shared.BRAND_INK;
export const BRAND_PRIMARY = shared.BRAND_PRIMARY;
export const LOGO_MM = shared.LOGO_MM;

// Das Raster wird zweimal gezogen - weisser Saum, darueber die Kernlinie in
// Markentinte (AGENTS.md, Invariante 5). Die Tinte ist dieselbe wie die der
// Fusszeile; der eigene Name macht sichtbar, dass das eine Entscheidung war.
export const GRID_INK = BRAND_INK;

// --- Sprachen ------------------------------------------------------------------
export const SUPPORTED_LOCALES = Object.freeze([...shared.SUPPORTED_LOCALES]);
export const DEFAULT_LOCALE = shared.DEFAULT_LOCALE;

/**
 * Markermittelpunkte in mm, mittig auf A4, y von OBEN gezaehlt.
 *
 * Die einzige Stelle, an der aus zwei Abstaenden vier Positionen werden - so wie
 * config.sheet_marker_centers() es auf der Python-Seite ist.
 */
export function sheetMarkerCenters(spacingMm = SHEET_SPACING_MM) {
    const [spacingX, spacingY] = spacingMm;
    const centreX = SHEET_MM[0] / 2.0;
    const centreY = SHEET_MM[1] / 2.0;
    return {
        0: [centreX - spacingX / 2.0, centreY - spacingY / 2.0],
        1: [centreX + spacingX / 2.0, centreY - spacingY / 2.0],
        2: [centreX - spacingX / 2.0, centreY + spacingY / 2.0],
        3: [centreX + spacingX / 2.0, centreY + spacingY / 2.0],
    };
}
