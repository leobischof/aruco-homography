/**
 * layout.js - Druckgeometrie, die SSOT dafuer, was "Originalgroesse" heisst.
 *
 * Zeile fuer Zeile aus app/pdf/layout.py uebernommen. Das ist Absicht und keine
 * Bequemlichkeit: die Python-Fassung ist die einzige, die je an einem Messschieber
 * geprueft wurde. Wer hier etwas "schoener" formuliert, verschiebt womoeglich einen
 * Zehntelmillimeter, und niemand sieht es.
 *
 * Invariante des ganzen Projekts: das entzerrte Bild belegt auf der Seite exakt
 * crop_w x crop_h Millimeter. Alles andere (Massstab, Metadaten, Passermarken)
 * lebt in einem Streifen ausserhalb des Nutzbildes und beschneidet die Schablone
 * nie.
 *
 * Alle Rechtecke sind in Millimetern und von der linken UNTEREN Ecke aus gemessen -
 * so, wie PDF rechnet. Dieses Modul kennt keine Punkte; umgerechnet wird erst beim
 * Zeichnen, in units.js.
 */

import * as constants from "../constants.js";
import { AppError } from "./errors.js";

/** Rechteck in mm, Ursprung linke untere Ecke der Seite. */
export class Rect {
    constructor(x, y, width, height) {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        Object.freeze(this);
    }

    asTuple() {
        return [this.x, this.y, this.width, this.height];
    }
}

/** Eine Einzelseite in exakter Objektgroesse plus Streifen. */
export class PageLayout {
    constructor({ pageW, pageH, image, strip, marginMm }) {
        this.pageW = pageW;
        this.pageH = pageH;
        this.image = image;
        this.strip = strip;
        this.marginMm = marginMm;
        Object.freeze(this);
    }
}

/** Eine Kachel: welcher Teil des Zuschnitts, an welcher Stelle der Seite. */
export class Tile {
    constructor({ index, col, row, cropX, cropY, srcW, srcH, placement }) {
        this.index = index;
        this.col = col;
        this.row = row;
        this.cropX = cropX;
        this.cropY = cropY;
        this.srcW = srcW;
        this.srcH = srcH;
        this.placement = placement;
        Object.freeze(this);
    }
}

/** Kachelplan fuer einen Zuschnitt auf einem Papierformat. */
export class TileLayout {
    constructor(fields) {
        Object.assign(this, fields);
        Object.freeze(this);
    }

    get pageCount() {
        return this.tiles.length;
    }
}

/**
 * Hoehe des Streifens unter dem Bild.
 *
 * Der Streifen ist IMMER da, auch wenn Massstab und Fusszeile abgeschaltet sind:
 * er traegt das Markenzeichen, und das gehoert auf jedes Blatt. Die Schalter
 * steuern nur, was ausser der Marke darin steht. Der Preis dafuer ist, dass eine
 * Seite nie exakt die Objektgroesse hat - die Invariante betrifft das BILD, und
 * die bleibt unberuehrt.
 */
export function stripHeight() {
    return constants.STRIP_H_MM;
}

/** Seitengeometrie fuer die Einzelseite (Spec 4.2). */
export function singlePage(cropW, cropH, marginMm, stripH) {
    if (cropW <= 0.0 || cropH <= 0.0) {
        throw new AppError("empty_crop", "crop_mm");
    }

    const pageW = cropW + 2.0 * marginMm;
    const pageH = cropH + 2.0 * marginMm + stripH;
    return new PageLayout({
        pageW,
        pageH,
        image: new Rect(marginMm, marginMm + stripH, cropW, cropH),
        strip: new Rect(marginMm, marginMm, cropW, stripH),
        marginMm,
    });
}

/** Papierformat in mm. orientation ist hier bereits entschieden. */
export function sheetSize(pageFormat, orientation) {
    if (!Object.hasOwn(constants.SHEET_FORMATS, pageFormat)) {
        throw new AppError("bad_page_format", "page_format", {
            page_format: pageFormat,
            formats: Object.keys(constants.SHEET_FORMATS).sort().join(", "),
        });
    }
    const [width, height] = constants.SHEET_FORMATS[pageFormat];
    return orientation === "landscape" ? [height, width] : [width, height];
}

/** Kachelplan berechnen. orientation "auto" waehlt die seitensparende Variante. */
export function tileLayout(
    cropW,
    cropH,
    pageFormat,
    orientation,
    printerMarginMm,
    overlapMm,
    stripH,
) {
    if (orientation === "auto") {
        orientation = cheaperOrientation(cropW, cropH, pageFormat, printerMarginMm, overlapMm, stripH);
    }

    const [sheetW, sheetH] = sheetSize(pageFormat, orientation);
    const usableW = sheetW - 2.0 * printerMarginMm;
    const usableH = sheetH - 2.0 * printerMarginMm - stripH;
    const stepW = usableW - overlapMm;
    const stepH = usableH - overlapMm;

    if (usableW <= 0.0 || usableH <= 0.0) {
        throw new AppError("margins_too_large", "printer_margin_mm", { page_format: pageFormat });
    }
    if (stepW <= 0.0 || stepH <= 0.0) {
        throw new AppError("overlap_too_large", "overlap_mm", {
            overlap_mm: overlapMm.toFixed(0),
            page_format: pageFormat,
            usable_w_mm: usableW.toFixed(0),
            usable_h_mm: usableH.toFixed(0),
        });
    }

    const nCols = Math.max(1, Math.ceil((cropW - overlapMm) / stepW));
    const nRows = Math.max(1, Math.ceil((cropH - overlapMm) / stepH));

    const tiles = [];
    for (let row = 0; row < nRows; row += 1) {
        for (let col = 0; col < nCols; col += 1) {
            const cropX = col * stepW;
            const cropY = row * stepH;
            const srcW = Math.min(usableW, cropW - cropX);
            const srcH = Math.min(usableH, cropH - cropY);
            // Der Inhalt sitzt oben in der nutzbaren Flaeche; die letzte Kachel
            // laeuft unten leer aus, statt den Inhalt zu verschieben.
            const placement = new Rect(
                printerMarginMm,
                printerMarginMm + stripH + (usableH - srcH),
                srcW,
                srcH,
            );
            tiles.push(
                new Tile({ index: tiles.length + 1, col, row, cropX, cropY, srcW, srcH, placement }),
            );
        }
    }

    return new TileLayout({
        sheetW,
        sheetH,
        usableW,
        usableH,
        stepW,
        stepH,
        nCols,
        nRows,
        overlapMm,
        printerMarginMm,
        strip: new Rect(printerMarginMm, printerMarginMm, usableW, stripH),
        tiles,
    });
}

/** Hoch- oder Querformat - was weniger Blaetter braucht. Gleichstand: hoch. */
function cheaperOrientation(cropW, cropH, pageFormat, printerMarginMm, overlapMm, stripH) {
    const counts = new Map();
    for (const candidate of ["portrait", "landscape"]) {
        try {
            const plan = tileLayout(
                cropW,
                cropH,
                pageFormat,
                candidate,
                printerMarginMm,
                overlapMm,
                stripH,
            );
            counts.set(candidate, plan.pageCount);
        } catch (error) {
            if (!(error instanceof AppError)) throw error;
        }
    }

    if (counts.size === 0) {
        return "portrait"; // tileLayout wirft dann den aussagekraeftigen Fehler
    }
    // Wenige Blaetter gewinnt; bei Gleichstand das Hochformat - dieselbe Ordnung
    // wie das Schluesseltupel (count, key != "portrait") in der Python-Fassung.
    let best = null;
    for (const [candidate, count] of counts) {
        const rank = [count, candidate === "portrait" ? 0 : 1];
        if (best === null || rank[0] < best.rank[0] || (rank[0] === best.rank[0] && rank[1] < best.rank[1])) {
            best = { candidate, rank };
        }
    }
    return best.candidate;
}
