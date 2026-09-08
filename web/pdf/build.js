/**
 * build.js - PDF bauen: Einzelseite in Originalgroesse oder Kachelung mit Klebeplan.
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
 *
 * **Oder eine Funktion, die je Blatt eines liefert.** Ein Zuschnitt von 810 x 1153 mm
 * ergibt bei 300 dpi ein Raster von 130 Megapixeln - 373 MiB an einem Stueck, und die
 * gibt ein Telefon nicht her (am 08.09.2026 auf einem Xiaomi genau so gescheitert,
 * bei jeder Aufloesung). Gedruckt wird der Zuschnitt aber ohnehin blattweise. Wird
 * hier statt der Bytes eine Funktion `(xMm, yMm, wMm, hMm) => JPEG-Bytes` uebergeben,
 * holt sich jedes Blatt sein eigenes Bild, und der Spitzenbedarf haengt am BLATT
 * statt am Zuschnitt.
 */

import * as branding from "./branding.js";
import * as constants from "../constants.js";
import { Document, HELVETICA, HELVETICA_BOLD } from "./draw.js";
import { translate } from "./i18n.js";
import { Rect, singlePage, stripHeight, tileLayout } from "./layout.js";
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
export async function buildPdf(source, cropWMm, cropHMm, options, footerLines, contourMm = null) {
    if (options.layout === "tiles") {
        return buildTiles(source, cropWMm, cropHMm, options, footerLines, contourMm);
    }
    return buildSingle(source, cropWMm, cropHMm, options, footerLines, contourMm);
}

/**
 * Liefert die Quelle je Blatt ein eigenes Bild - oder ist sie EIN fertiges Bild?
 *
 * Eine Funktion heisst: blattweise, jedes Blatt fragt nach seinem Rechteck. Bytes
 * heissen: ein Bild fuer alles, und die Blaetter schneiden sich ihren Teil daraus.
 */
function isPerSheet(source) {
    return typeof source === "function";
}

async function buildSingle(source, cropW, cropH, options, footerLines, contourMm) {
    const stripH = stripHeight();
    const page = singlePage(cropW, cropH, options.pageMarginMm, stripH);

    const document = await newDocument(options.title);
    // Eine Seite ist ein Blatt: die Bildquelle wird genau einmal gefragt, und
    // zwar nach dem ganzen Zuschnitt. Hier ist also nichts zu gewinnen - wer ein
    // Plakat auf EINER Seite will, braucht das Bild am Stueck.
    const image = await document.embedJpeg(
        isPerSheet(source) ? await source(0.0, 0.0, cropW, cropH) : source);
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

async function buildTiles(source, cropW, cropH, options, footerLines, contourMm) {
    const stripH = stripHeight();
    const plan = tileLayout(
        cropW,
        cropH,
        options.pageFormat,
        options.orientation,
        options.printerMarginMm,
        options.overlapMm,
        stripH,
    );

    const document = await newDocument(options.title);
    const perSheet = isPerSheet(source);

    // Das Pixelgitter des GANZEN Zuschnitts. Blattweise entsteht es nie als Bild,
    // aber seine Masse werden gebraucht: die Blattgrenzen werden auf demselben
    // Gitter gerundet wie bisher, damit die Blaetter luecken- und ueberlappungsfrei
    // aneinanderstossen und jedes Pixel dort landet, wo es auch vorher lag.
    const pxPerMm = constants.pxPerMmForDpi(options.dpi);
    const image = perSheet
        ? {
              width: Math.max(1, roundHalfToEven(cropW * pxPerMm)),
              height: Math.max(1, roundHalfToEven(cropH * pxPerMm)),
          }
        : await document.embedJpeg(source);
    let pages = 0;

    if (options.tileOverview) {
        drawOverview(document, plan, cropW, cropH, footerLines, options.locale);
        pages += 1;
    }

    // Bei fertigen Bytes sagt das Bild selbst, wie fein es ist - eine Kachelung
    // muss auch dann stimmen, wenn jemand ein Bild uebergibt, das nicht genau der
    // eingestellten Aufloesung entspricht.
    const gridPxPerMm = perSheet ? pxPerMm : image.width / cropW;
    for (const tile of plan.tiles) {
        const sheet = document.addSheet(plan.sheetW, plan.sheetH);
        const pixelRect =
            cropPixels(image, tile.cropX, tile.cropY, tile.srcW, tile.srcH, gridPxPerMm);

        // Blattweise: das Bild IST der Ausschnitt, also wird es ganz gezeichnet.
        // Die Millimeter kommen aus dem gerundeten Pixelrechteck zurueck und nicht
        // aus tile.cropX/srcW - nur so faellt das Blatt auf dieselbe Pixelgrenze
        // wie der Ausschnitt, den cropPixels aus einem grossen Bild schneiden
        // wuerde, und nur dann sind beide Wege Bit fuer Bit gleich.
        let drawn = image;
        let region = pixelRect;
        if (perSheet) {
            drawn = await document.embedJpeg(await source(
                pixelRect.x0 / gridPxPerMm,
                pixelRect.y0 / gridPxPerMm,
                (pixelRect.x1 - pixelRect.x0) / gridPxPerMm,
                (pixelRect.y1 - pixelRect.y0) / gridPxPerMm,
            ));
            region = { x0: 0, y0: 0, x1: drawn.width, y1: drawn.height };
        }
        placeImage(sheet, drawn, region, tile.placement);
        decorate(sheet, tile.placement, [tile.cropX, tile.cropY], options, contourMm);

        if (options.showMarks) {
            overlays.drawTileMarks(
                sheet,
                tile.placement,
                plan.overlapMm,
                tile.col < plan.nCols - 1,
                tile.row < plan.nRows - 1,
            );
        }
        overlays.drawStrip(sheet, plan.strip, options.showScalebar, options.showFooter ? footerLines : [], {
            tileLabel: tileLabel(tile.index, plan.pageCount, tile.col, tile.row, options.locale),
            locale: options.locale,
        });

        pages += 1;
    }

    const first = plan.tiles[0].placement;
    return {
        data: await document.save(),
        pageSizeMm: [plan.sheetW, plan.sheetH],
        imageRectMm: first.asTuple(),
        pageCount: pages,
        meta: { n_cols: plan.nCols, n_rows: plan.nRows, tiles: plan.pageCount },
    };
}

/** Blattnummer und Rasterplatz - zwei Bausteine, damit beide Sprachen frei sind. */
function tileLabel(index, count, col, row, locale) {
    const sheet = translate("pdf.tiles.sheet", locale, { index, count });
    const position = translate("pdf.tiles.position", locale, { col: col + 1, row: row + 1 });
    return `${sheet} - ${position}`;
}

/**
 * Pixelausschnitt fuer eine Kachel. Das mm-Rechteck bleibt massgeblich.
 *
 * Auf ganze Pixel gerundet wird hier genauso wie in der Vorlage - nicht, weil es
 * genauer waere (exakt platzieren koennte man auch), sondern weil es DASSELBE sein
 * soll. Ein Ausschnitt, der eine halbe Pixelbreite anders sitzt, ist ein
 * Unterschied zur geprueften Referenz, und Unterschiede zur geprueften Referenz
 * gehoeren begruendet, nicht eingeschmuggelt.
 */
function cropPixels(image, cropX, cropY, widthMm, heightMm, pxPerMm) {
    const x0 = roundHalfToEven(cropX * pxPerMm);
    const y0 = roundHalfToEven(cropY * pxPerMm);
    return {
        x0,
        y0,
        x1: Math.min(image.width, x0 + Math.max(1, roundHalfToEven(widthMm * pxPerMm))),
        y1: Math.min(image.height, y0 + Math.max(1, roundHalfToEven(heightMm * pxPerMm))),
    };
}

/**
 * Runden wie Pythons `round()`: die Haelfte geht zur GERADEN Zahl.
 *
 * `Math.round` rundet die Haelfte immer nach oben. Bei 300 dpi trennt eine
 * Pixelbreite 0,085 mm - achtmal die Toleranz, die dieses Projekt einhaelt. Der
 * Fall tritt selten ein, und genau deshalb faende ihn niemand.
 */
function roundHalfToEven(value) {
    const floor = Math.floor(value);
    const rest = value - floor;
    if (rest > 0.5) return floor + 1;
    if (rest < 0.5) return floor;
    return floor % 2 === 0 ? floor : floor + 1;
}

/** Uebersichtsblatt: welches Blatt gehoert wohin. */
function drawOverview(document, plan, cropW, cropH, footerLines, locale = constants.DEFAULT_LOCALE) {
    const sheet = document.addSheet(plan.sheetW, plan.sheetH);
    const ink = branding.ink(constants.BRAND_INK);
    const title = translate("pdf.assembly.title", locale);
    sheet.setFillColor(ink);
    sheet.setFont(HELVETICA_BOLD, 14);
    sheet.drawString(plan.printerMarginMm, plan.sheetH - 20.0, title);

    sheet.setFont(HELVETICA, 9);
    sheet.drawString(
        plan.printerMarginMm,
        plan.sheetH - 28.0,
        translate("pdf.assembly.summary", locale, {
            width: cropW.toFixed(1),
            height: cropH.toFixed(1),
            pages: plan.pageCount,
            cols: plan.nCols,
            rows: plan.nRows,
            overlap: plan.overlapMm.toFixed(0),
        }),
    );

    // Raster massstabsgetreu in den verbleibenden Platz einpassen. Unten bleibt der
    // Streifen frei, damit Marke und Metadaten auch hier stehen koennen.
    const strip = new Rect(
        plan.printerMarginMm,
        plan.printerMarginMm,
        plan.sheetW - 2.0 * plan.printerMarginMm,
        constants.STRIP_H_MM,
    );
    const areaW = plan.sheetW - 2.0 * plan.printerMarginMm;
    const areaH = plan.sheetH - 40.0 - (strip.y + strip.height + 8.0);
    const scale = Math.min(areaW / Math.max(cropW, 1e-6), areaH / Math.max(cropH, 1e-6));
    const originX = plan.printerMarginMm;
    const originY = plan.sheetH - 40.0 - cropH * scale;

    sheet.setLineWidth(0.4);
    for (const tile of plan.tiles) {
        const x = originX + tile.cropX * scale;
        const y = originY + (cropH - tile.cropY - tile.srcH) * scale;
        sheet.setStrokeColor(branding.ink(constants.BRAND_PRIMARY));
        sheet.rect(x, y, tile.srcW * scale, tile.srcH * scale);
        sheet.setFont(HELVETICA_BOLD, 10);
        sheet.setFillColor(ink);
        sheet.drawCentredString(
            x + (tile.srcW * scale) / 2.0,
            y + (tile.srcH * scale) / 2.0,
            String(tile.index),
        );
    }

    sheet.setStrokeColor(ink);
    sheet.setLineWidth(0.8);
    sheet.rect(originX, originY, cropW * scale, cropH * scale);

    overlays.drawStrip(sheet, strip, true, footerLines, { tileLabel: title, locale });
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
