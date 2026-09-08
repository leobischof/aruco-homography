/**
 * constants.js - die Produktkonstanten, gelesen aus shared/constants.json.
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
 * Jeder Name wird EINZELN gebunden, genau wie in app/config.py: ein Tippfehler
 * im Schluessel faellt hier beim Laden auf statt spaeter als `undefined` in einer
 * Millimeterrechnung. Ein `undefined` in einer Multiplikation ergibt NaN, und ein
 * NaN in der MediaBox ist ein Blatt ohne Groesse.
 */

import shared from "../../shared/constants.json" with { type: "json" };

// --- Einheiten -----------------------------------------------------------------
export const MM_PER_INCH = shared.MM_PER_INCH;

// --- Marker und Markerblatt ----------------------------------------------------
export const ARUCO_DICT_NAME = shared.ARUCO_DICT_NAME;
export const MARKER_MM_NOMINAL = shared.MARKER_MM_NOMINAL;
export const SHEET_MM = Object.freeze([...shared.SHEET_MM]);
export const SHEET_SPACING_MM = Object.freeze([...shared.SHEET_SPACING_MM]);
export const SHEET_MARKER_IDS = Object.freeze([...shared.SHEET_MARKER_IDS]);

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
