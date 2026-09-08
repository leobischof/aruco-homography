/**
 * request.js - was am Server das Schema ergaenzt.
 *
 * `app/schemas.py` ist mehr als eine Typpruefung: seine Vorgabewerte sind Teil
 * der Schnittstelle. `app/static/js/main.js` schickt bewusst NICHT alle Felder -
 * Ausrichtung, Druckerrand und Seitenrand stehen in keinem Bedienfeld, sie
 * kommen vom Server. Im Ortsbetrieb gibt es keinen Server, also muessen sie
 * hier entstehen, bevor `pipeline.js` sie liest.
 *
 * Was passiert, wenn man das vergisst, ist keine Fehlermeldung: `exportOptions`
 * in web/pdf/build.js verteilt die Ueberschreibungen mit `...overrides`, und ein
 * ausdrueckliches `undefined` **ueberschreibt die Vorgabe**. Aus dem fehlenden
 * Druckerrand wurde so ein NaN, das erst zehn Aufrufe spaeter beim Zeichnen des
 * Klebeplans auffiel ("options.x must be of type number").
 *
 * SSOT bleibt `app/schemas.py`. Diese Datei spiegelt es und erfindet nichts
 * dazu; wer dort eine Vorgabe aendert, aendert sie hier mit.
 *
 * **Nicht gespiegelt sind die Wertebereiche** (`ge=0.0`, `gt=0.0`). Der Server
 * weist eine negative Ueberlappung mit 422 ab, der Ortsbetrieb nimmt sie an.
 * Die Bedienung laesst solche Werte nicht zu - die Eingabefelder tragen `min` -,
 * und ein Unterschied, den man nur mit einem eigenen Werkzeug herbeifuehren
 * kann, ist eine Luecke und kein Fehler. Sie steht in
 * docs/cpp-migration/stage-4-web.md.
 */

import * as constants from "../constants.js";
import { normalise } from "../pdf/i18n.js";

/** Wert uebernehmen, wenn er da ist - sonst die Vorgabe. */
function fallback(value, standard) {
    return value === undefined || value === null ? standard : value;
}

/** SolveRequest aus app/schemas.py. */
export function solveRequest(wire) {
    return {
        session_id: wire.session_id,
        marker_mm: fallback(wire.marker_mm, constants.MARKER_MM_NOMINAL),
        mode: fallback(wire.mode, "sheet"),
        thickness_mm: fallback(wire.thickness_mm, 0.0),
        // Das einzige Feld, dessen Vorgabe null IST - "unbekannt" ist hier eine
        // Aussage und kein fehlender Wert (camera.py, Weg B).
        camera_height_mm: wire.camera_height_mm === undefined ? null : wire.camera_height_mm,
        spacing_x_mm: fallback(wire.spacing_x_mm, constants.SHEET_SPACING_MM[0]),
        spacing_y_mm: fallback(wire.spacing_y_mm, constants.SHEET_SPACING_MM[1]),
    };
}

/**
 * ExportImageRequest aus app/schemas.py.
 *
 * Kurz, weil ein Bild fast nichts von dem hat, was ein Ausdruck braucht: kein
 * Seitenformat, keine Ueberlappung, keine Aufdrucke, keine Sprache.
 */
export function imageRequest(wire) {
    return {
        session_id: wire.session_id,
        crop_mm: wire.crop_mm,
        dpi: fallback(wire.dpi, constants.DPI_DEFAULT),
        image_format: fallback(wire.image_format, "jpeg"),
        adjust: wire.adjust || {},
        filename: fallback(wire.filename, "schablone"),
    };
}

/** ExportRequest aus app/schemas.py, samt OverlayFlags. */
export function exportRequest(wire) {
    const overlays = wire.overlays || {};
    return {
        session_id: wire.session_id,
        crop_mm: wire.crop_mm,
        dpi: fallback(wire.dpi, constants.DPI_DEFAULT),
        layout: fallback(wire.layout, constants.LAYOUT_DEFAULT),
        page_format: fallback(wire.page_format, "A4"),
        orientation: fallback(wire.orientation, "auto"),
        overlap_mm: fallback(wire.overlap_mm, constants.TILE_OVERLAP_MM_DEFAULT),
        printer_margin_mm: fallback(wire.printer_margin_mm, constants.PRINTER_MARGIN_MM_DEFAULT),
        page_margin_mm: fallback(wire.page_margin_mm, constants.PAGE_MARGIN_MM_DEFAULT),
        overlays: {
            scalebar: fallback(overlays.scalebar, true),
            grid: fallback(overlays.grid, true),
            footer: fallback(overlays.footer, true),
            marks: fallback(overlays.marks, true),
        },
        tile_overview: fallback(wire.tile_overview, constants.TILE_OVERVIEW_DEFAULT),
        contour: fallback(wire.contour, false),
        // Die Regler bekommen ihre Vorgaben in enhance.js::adjustOptions, Feld
        // fuer Feld - hier waere es eine zweite Liste derselben Namen.
        adjust: wire.adjust || {},
        // Abbilden statt ablehnen, wie der Feldpruefer am Server: "de-CH" ist
        // kein Bedienfehler, und ein Export scheitert nie an einer Sprachangabe.
        locale: normalise(fallback(wire.locale, constants.DEFAULT_LOCALE)),
        filename: fallback(wire.filename, "schablone.pdf"),
    };
}
