/**
 * overlays.js - Aufdrucke: Kontrollmassstab, Metadaten, Raster, Passermarken, Kontur.
 *
 * Zeile fuer Zeile aus app/pdf/overlays.py. Alle Funktionen rechnen in
 * Millimetern; in Punkte umgerechnet wird erst in draw.js. Der Bezugspunkt ist
 * immer die linke UNTERE Ecke der Seite.
 *
 * Das Raster wird doppelt gezogen - breiter weisser Saum, darueber die Kernlinie
 * in Markentinte (AGENTS.md, Invariante 5). Der Grund: die Schablone liegt mal auf
 * einem hellen, mal auf einem dunklen Foto. Eine einzelne graue Linie verschwindet
 * auf dem einen oder dem anderen; die Kombination ist auf beidem lesbar, ohne dass
 * das Bild darunter zugedeckt wird.
 */

import * as branding from "./branding.js";
import * as constants from "./constants.js";
import { HELVETICA, HELVETICA_BOLD, grayColor, rgbColor } from "./draw.js";
import { translate } from "./i18n.js";
import { ptToMm } from "./units.js";

// Innenaufteilung des Streifens, von seiner Unterkante aus (Summe <= STRIP_H_MM).
const TEXT_LINE_1_MM = 1.8;
const TEXT_LINE_2_MM = 5.4;
const SCALEBAR_BASE_MM = 10.0;
const SCALEBAR_HEIGHT_MM = 3.0;
const SCALEBAR_LABEL_MM = 14.2;
const TEXT_SIZE_PT = 6.0;
const GAP_MM = 2.5;

const WHITE = grayColor(1.0);

/** Punkt aus dem Zuschnitt (y nach unten) auf die Seite (y nach oben) abbilden. */
export function cropToPage(imageRect, cropOrigin, pointMm) {
    const [cropX, cropY] = cropOrigin;
    return [
        imageRect.x + (Number(pointMm[0]) - cropX),
        imageRect.y + imageRect.height - (Number(pointMm[1]) - cropY),
    ];
}

/** Den Streifen unter dem Bild fuellen: Massstab, Metadaten, Blattnummer, Marke. */
export function drawStrip(
    sheet,
    strip,
    showScalebar,
    footerLines,
    { tileLabel = null, locale = constants.DEFAULT_LOCALE } = {},
) {
    // Die Marke sitzt immer rechts aussen und bekommt ihren Platz zuerst; alles
    // andere richtet sich danach, damit nie etwas unter dem Logo verschwindet.
    const withClaim = strip.width > branding.blockWidthMm(sheet) + 70.0;
    const brandLeft = branding.drawBrandBlock(
        sheet,
        strip.x + strip.width,
        strip.y,
        strip.height,
        withClaim,
    );
    const available = Math.max(10.0, brandLeft - GAP_MM - strip.x);

    if (showScalebar) {
        drawScalebar(sheet, strip, available, locale);
    }

    sheet.setFillColor(branding.ink(constants.BRAND_INK));
    footerLines.slice(0, 2).forEach((line, index) => {
        const offset = index === 1 ? TEXT_LINE_2_MM : TEXT_LINE_1_MM;
        sheet.setFont(HELVETICA, TEXT_SIZE_PT);
        sheet.drawString(strip.x, strip.y + offset, fit(sheet, line, HELVETICA, TEXT_SIZE_PT, available));
    });

    if (tileLabel) {
        sheet.setFont(HELVETICA_BOLD, TEXT_SIZE_PT + 1.0);
        sheet.drawRightString(strip.x + available, strip.y + SCALEBAR_BASE_MM + 0.6, tileLabel);
    }
}

/** Kuerzt Text mit Auslassungszeichen, statt ihn unter das Logo laufen zu lassen. */
function fit(sheet, text, font, sizePt, widthMm) {
    if (sheet.stringWidthMm(text, font, sizePt) <= widthMm) {
        return text;
    }
    while (text && sheet.stringWidthMm(`${text}...`, font, sizePt) > widthMm) {
        text = text.slice(0, -1);
    }
    return `${text}...`;
}

/** 100-mm-Balken mit 10-mm-Teilung. Nachmessen beweist die Skalierung. */
function drawScalebar(sheet, strip, availableMm, locale = constants.DEFAULT_LOCALE) {
    const length = Math.min(constants.SCALEBAR_MM, availableMm);
    const baseY = strip.y + SCALEBAR_BASE_MM;

    sheet.setLineWidth(0.4);
    sheet.setStrokeColor(branding.ink(constants.BRAND_INK));
    sheet.setFillColor(branding.ink(constants.BRAND_INK));

    // Wechselnd gefuellte 10-mm-Felder: auch aus der Entfernung eindeutig ablesbar.
    let position = 0.0;
    let filled = true;
    while (position < length - 1e-9) {
        const segment = Math.min(10.0, length - position);
        if (filled) {
            sheet.rect(strip.x + position, baseY, segment, SCALEBAR_HEIGHT_MM, {
                stroke: false,
                fill: true,
            });
        }
        position += segment;
        filled = !filled;
    }

    sheet.rect(strip.x, baseY, length, SCALEBAR_HEIGHT_MM, { stroke: true, fill: false });
    sheet.setFont(HELVETICA_BOLD, TEXT_SIZE_PT);
    sheet.drawString(
        strip.x,
        strip.y + SCALEBAR_LABEL_MM,
        translate("pdf.scalebar_caption", locale, { length: length.toFixed(0) }),
    );
}

/**
 * Hilfsraster ueber dem Bild, ausgerichtet am absoluten Zuschnittraster.
 *
 * Zwei Durchgaenge: erst alle weissen Saeume, dann alle Kernlinien. So legt sich
 * kein Saum ueber eine bereits gezogene Kernlinie einer Kreuzung.
 */
export function drawGrid(sheet, imageRect, cropOrigin, stepMm = constants.GRID_STEP_MM) {
    const [cropX, cropY] = cropOrigin;
    const verticalOffsets = gridOffsets(cropX, imageRect.width, stepMm);
    const horizontalOffsets = gridOffsets(cropY, imageRect.height, stepMm);
    const vertical = verticalOffsets.map((offset) => imageRect.x + (offset - cropX));
    const horizontal = horizontalOffsets.map(
        (offset) => imageRect.y + imageRect.height - (offset - cropY),
    );

    sheet.saveState();
    for (const [widthPt, colour] of [
        [constants.GRID_HALO_PT, WHITE],
        [constants.GRID_LINE_PT, null],
    ]) {
        sheet.setLineWidth(widthPt);
        sheet.setStrokeColor(colour === null ? branding.ink(constants.GRID_INK) : colour);
        for (const x of vertical) {
            sheet.line(x, imageRect.y, x, imageRect.y + imageRect.height);
        }
        for (const y of horizontal) {
            sheet.line(imageRect.x, y, imageRect.x + imageRect.width, y);
        }
    }

    verticalOffsets.forEach((offset, index) => {
        gridLabel(sheet, imageRect, vertical[index] + 0.7, imageRect.y + 0.8, offset.toFixed(0));
    });
    horizontalOffsets.forEach((offset, index) => {
        gridLabel(sheet, imageRect, imageRect.x + 0.7, horizontal[index] + 0.8, offset.toFixed(0));
    });
    sheet.restoreState();
}

/**
 * Rasterbeschriftung auf weissem Traeger - lesbar auch auf dunklem Foto.
 *
 * Die Beschriftung wird in den Bildbereich hineingeklemmt. Ohne das rutscht die
 * Null-Linie oben aus dem Bild in den Rand, und die aeusserste rechte Beschriftung
 * haengt ueber die Bildkante hinaus.
 */
function gridLabel(sheet, imageRect, x, y, text) {
    const size = constants.GRID_LABEL_PT;
    const width = sheet.stringWidthMm(text, HELVETICA_BOLD, size);
    // Die Schriftgroesse wird hier als HOEHE gelesen - `size / PT_PER_MM` in der
    // Vorlage. Eine Naeherung, ja, aber dieselbe wie drueben: der weisse Traeger
    // soll den Text decken, nicht ihn vermessen.
    const height = ptToMm(size);

    x = Math.min(Math.max(x, imageRect.x + 0.5), imageRect.x + imageRect.width - width - 0.5);
    y = Math.min(Math.max(y, imageRect.y + 0.5), imageRect.y + imageRect.height - height - 0.5);

    sheet.setFillColor(WHITE);
    sheet.rect(x - 0.4, y - 0.4, width + 0.8, height * 0.95, { stroke: false, fill: true });
    sheet.setFillColor(branding.ink(constants.GRID_INK));
    sheet.setFont(HELVETICA_BOLD, size);
    sheet.drawString(x, y, text);
}

/** Absolute Rasterpositionen innerhalb eines Abschnitts [start, start+length]. */
export function gridOffsets(start, length, stepMm) {
    const first = Math.ceil(start / stepMm) * stepMm;
    const stop = start + length + 1e-9;
    // np.arange: Anzahl aus ceil((stop - first) / step), Werte als first + i*step -
    // NICHT aufsummiert. Aufsummieren driftet, und die Beschriftung stuende dann
    // bei "150" ein Tausendstel neben der Linie.
    const count = Math.max(0, Math.ceil((stop - first) / stepMm));
    return Array.from({ length: count }, (_, index) => first + index * stepMm);
}

/** Erkannten Umriss als Vektorpfad zeichnen - scharfe Schnittkante statt Fotorand. */
export function drawContour(sheet, imageRect, cropOrigin, contourMm) {
    if (!contourMm || contourMm.length < 2) return;

    sheet.saveState();
    sheet.setStrokeColor(rgbColor(1.0, 0.0, 0.6));
    sheet.setLineWidthMm(constants.CONTOUR_LINE_MM);
    sheet.polyline(
        contourMm.map((point) => cropToPage(imageRect, cropOrigin, point)),
        { close: true, stroke: true, fill: false },
    );
    sheet.restoreState();
}

/** Schnitt- und Klebemarken: wo geschnitten und wie ueberlappt geklebt wird. */
export function drawTileMarks(sheet, placement, overlapMm, hasRightNeighbour, hasBottomNeighbour) {
    sheet.saveState();
    sheet.setStrokeColor(branding.ink(constants.BRAND_INK));
    sheet.setLineWidth(0.4);

    // Eckmarken: die Schnittlinie des Nutzbereichs.
    const tick = 4.0;
    for (const [cornerX, cornerY, dx, dy] of [
        [placement.x, placement.y, 1, 1],
        [placement.x + placement.width, placement.y, -1, 1],
        [placement.x, placement.y + placement.height, 1, -1],
        [placement.x + placement.width, placement.y + placement.height, -1, -1],
    ]) {
        sheet.line(cornerX, cornerY, cornerX + dx * tick, cornerY);
        sheet.line(cornerX, cornerY, cornerX, cornerY + dy * tick);
    }

    // Klebezone: gestrichelt markiert, damit klar ist, welcher Streifen doppelt ist.
    sheet.setDash(2, 2);
    sheet.setStrokeColor(branding.ink(constants.BRAND_PRIMARY));
    if (hasRightNeighbour) {
        const x = placement.x + placement.width - overlapMm;
        sheet.line(x, placement.y, x, placement.y + placement.height);
    }
    if (hasBottomNeighbour) {
        const y = placement.y + overlapMm;
        sheet.line(placement.x, y, placement.x + placement.width, y);
    }
    sheet.restoreState();
}
