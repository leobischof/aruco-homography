/**
 * build.js - PDF bauen: Einzelseite in Originalgroesse.
 *
 * Die eine Zusage, die dieses Modul einhalten muss (AGENTS.md, Invariante 1): das
 * entzerrte Bild belegt auf der Seite exakt so viele Millimeter, wie der Zuschnitt
 * gross ist. Deshalb wird jedes Bild mit gesetzter Breite UND Hoehe platziert -
 * nichts darf hier automatisch skaliert werden, und das Seitenverhaeltnis des
 * Pixelbildes hat keine Stimme.
 *
 * Eingabe ist das entzerrte Bild als **JPEG-Bytes**, nicht als Pixelfeld. Das ist
 * die Grenze, die docs/cpp-migration/README.md zieht: Kodieren und Dekodieren
 * gehoert auf jedes Ziel einzeln (der WASM-Bau von OpenCV hat kein `imgcodecs`),
 * der gemeinsame Code nimmt fertige Bytes. Im Browser liefert die Leinwand sie,
 * unter Node der Pruefstand, auf Android die Huelle.
 */

import * as constants from "./constants.js";
import { Document } from "./draw.js";
import { translate } from "./i18n.js";
import { singlePage, stripHeight } from "./layout.js";
import * as overlays from "./overlays.js";

/**
 * Alles, was der Bediener am Druck einstellen kann.
 *
 * `layout` ist bewusst NICHT constants.LAYOUT_DEFAULT: das ist die Vorgabe der
 * BEDIENUNG, und die ist die Kachelung. Hier, eine Schicht tiefer, ist "eine
 * Seite" der schlichte Fall - ein Bild, eine Seite - und Kachelung eine
 * Betriebsart, die der Aufrufer verlangt. Wer die beiden gleichzieht, aendert
 * stillschweigend, was tests/test_branding.py mit den Vorgaben prueft.
 */
export function exportOptions(overrides = {}) {
    return {
        dpi: constants.DPI_DEFAULT,
        layout: "single", // "single" | "tiles"
        pageFormat: "A4",
        orientation: "auto",
        overlapMm: constants.TILE_OVERLAP_MM_DEFAULT,
        printerMarginMm: constants.PRINTER_MARGIN_MM_DEFAULT,
        pageMarginMm: constants.PAGE_MARGIN_MM_DEFAULT,
        showScalebar: true,
        showGrid: true,
        showFooter: true,
        showMarks: true,
        tileOverview: constants.TILE_OVERVIEW_DEFAULT,
        contour: false,
        title: "ArUco-Homographie",
        // Sprache der Aufdrucke. Die Marke bleibt davon unberuehrt - sie ist ein
        // Zeichen, kein Text (AGENTS.md, Invariante 3).
        locale: constants.DEFAULT_LOCALE,
        ...overrides,
    };
}

/** Einstiegspunkt: baut je nach Option eine Seite oder eine Kachelung. */
export async function buildPdf(jpegBytes, cropWMm, cropHMm, options, footerLines, contourMm = null) {
    return buildSingle(jpegBytes, cropWMm, cropHMm, options, footerLines, contourMm);
}

async function buildSingle(jpegBytes, cropW, cropH, options, footerLines, contourMm) {
    const stripH = stripHeight();
    const page = singlePage(cropW, cropH, options.pageMarginMm, stripH);

    const document = await newDocument(options.title);
    const image = await document.embedJpeg(jpegBytes);
    const sheet = document.addSheet(page.pageW, page.pageH);

    placeImage(sheet, image, { x0: 0, y0: 0, x1: image.width, y1: image.height }, page.image);
    decorate(sheet, page.image, [0.0, 0.0], options, contourMm);
    overlays.drawStrip(
        sheet,
        page.strip,
        options.showScalebar,
        options.showFooter ? footerLines : [],
        { locale: options.locale },
    );

    return {
        data: await document.save(),
        pageSizeMm: [page.pageW, page.pageH],
        imageRectMm: page.image.asTuple(),
        pageCount: 1,
        meta: {},
    };
}

async function newDocument(title) {
    return Document.create({ title, creator: "ArUco-Homographie" });
}

/** Raster und Kontur ueber das Bild legen, sauber auf den Bildbereich beschnitten. */
function decorate(sheet, imageRect, cropOrigin, options, contourMm) {
    if (options.showGrid) {
        overlays.drawGrid(sheet, imageRect, cropOrigin);
    }
    if (options.contour && contourMm && contourMm.length >= 2) {
        sheet.saveState();
        sheet.clipRect(imageRect.x, imageRect.y, imageRect.width, imageRect.height);
        overlays.drawContour(sheet, imageRect, cropOrigin, contourMm);
        sheet.restoreState();
    }
}

/** Bild auf ein exaktes Millimeter-Rechteck setzen. Kein Auto-Scaling. */
function placeImage(sheet, image, pixelRect, rect) {
    sheet.drawImageRegion(image, pixelRect, rect);
}

// Die Platzhalter der beiden Fusszeilen. Was der Aufrufer nicht mitgibt, wird zu "?" -
// eine halb gefuellte Zeile ist immer noch besser als eine fehlende.
const FOOTER_FIELDS = [
    "object_mm",
    "dpi",
    "scale",
    "mode",
    "marker_ids",
    "marker_mm",
    "rms",
    "camera",
    "thickness",
    "extrapolation",
    "source",
    "timestamp",
];

/** Zwei Zeilen Metadaten - alles, was einen Ausdruck spaeter nachvollziehbar macht. */
export function buildFooterLines(meta, locale = constants.DEFAULT_LOCALE) {
    const values = Object.fromEntries(
        FOOTER_FIELDS.map((field) => [field, Object.hasOwn(meta, field) ? meta[field] : "?"]),
    );
    return [
        translate("pdf.footer.line1", locale, values),
        translate("pdf.footer.line2", locale, values),
    ];
}
