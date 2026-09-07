/**
 * markersheet.js - das A4-Markerblatt, der Massstabs-Ursprung des Verfahrens.
 *
 * Die Marker werden NICHT als Rasterbild eingebettet, sondern Modul fuer Modul als
 * Vektorrechtecke gezeichnet. Damit sind die Kanten unabhaengig von der
 * Druckeraufloesung absolut scharf, was der Subpixel-Erkennung direkt zugutekommt.
 *
 * Das Blatt traegt seinen eigenen Kontrollmassstab: nach dem Drucken misst man
 * einen Marker mit dem Messschieber und traegt den GEMESSENEN Wert in die App ein.
 * Damit faellt jede Druckerskalierung aus der Rechnung heraus.
 *
 * **Die Modulbits kommen von aussen.** `markerBits(id)` liefert sie; wer das ist,
 * entscheidet die Huelle: im Browser das schon geladene opencv.js, unter Node der
 * Pruefstand, auf Android die dortige OpenCV-Bindung. Das ist dieselbe Grenze, die
 * docs/cpp-migration/README.md zieht - der Kern rechnet, die Oberflaeche gestaltet.
 * Ein `import` von opencv.js an dieser Stelle haenge 13 MB WASM an einen PDF-Bau,
 * der nur vier feste Zeichnungen braucht, und zwaenge jedem Ziel denselben
 * Ladeweg auf, den keines von ihnen teilt.
 */

import * as branding from "./branding.js";
import * as constants from "./constants.js";
import { Document, HELVETICA, HELVETICA_BOLD } from "./draw.js";
import { translate } from "./i18n.js";
import { Rect } from "./layout.js";

// Ein 4x4-Marker hat mit einem Modul Rand 6 x 6 Module.
export const MODULES = 6;

/** Platzierungsrechtecke der Marker in mm, von der linken UNTEREN Blattecke aus. */
export function sheetLayout(
    markerMm = constants.MARKER_MM_NOMINAL,
    spacingMm = constants.SHEET_SPACING_MM,
) {
    const sheetH = constants.SHEET_MM[1];
    const half = markerMm / 2.0;
    const centers = constants.sheetMarkerCenters(spacingMm);
    return Object.fromEntries(
        Object.entries(centers).map(([markerId, [cx, cy]]) => [
            Number(markerId),
            new Rect(cx - half, sheetH - cy - half, markerMm, markerMm),
        ]),
    );
}

/** Das komplette Markerblatt als PDF-Bytes. */
export async function buildMarkersheet({
    markerBits,
    markerMm = constants.MARKER_MM_NOMINAL,
    spacingMm = constants.SHEET_SPACING_MM,
    locale = constants.DEFAULT_LOCALE,
}) {
    const [sheetW, sheetH] = constants.SHEET_MM;
    const document = await Document.create({
        title: translate("pdf.markersheet.document_title", locale),
        creator: "ArUco-Homographie",
    });
    const sheet = document.addSheet(sheetW, sheetH);

    for (const [markerId, rect] of Object.entries(sheetLayout(markerMm, spacingMm))) {
        drawMarker(sheet, markerBits(Number(markerId)), rect);
        sheet.setFont(HELVETICA, 7);
        sheet.setFillGray(0.35);
        sheet.drawCentredString(
            rect.x + rect.width / 2.0,
            rect.y - 4.0,
            translate("pdf.markersheet.marker_label", locale, { marker_id: Number(markerId) }),
        );
    }

    drawInstructions(sheet, sheetW, sheetH, markerMm, spacingMm, locale);
    drawBrandFooter(sheet, sheetW, markerMm, spacingMm, locale);
    return document.save();
}

/**
 * Markenzeichen am unteren Blattrand.
 *
 * Die Hoehe ist so gewaehlt, dass zwischen Text und unterstem Marker mehr als ein
 * Markermodul (hier gut 11 mm) weiss bleibt - die Ruhezone, auf die der Detektor
 * angewiesen ist. Naeher heran darf hier nichts.
 */
function drawBrandFooter(sheet, sheetW, markerMm, spacingMm, locale = constants.DEFAULT_LOCALE) {
    const stripY = 5.0;
    const stripH = 11.0;
    branding.drawBrandBlock(sheet, sheetW - 15.0, stripY, stripH, true);

    sheet.setFillColor(branding.ink(constants.BRAND_INK));
    sheet.setFont(HELVETICA, 6.0);
    sheet.drawString(
        15.0,
        stripY + stripH / 2.0 - 1.0,
        translate("pdf.markersheet.footer", locale, {
            dictionary: constants.ARUCO_DICT_NAME,
            marker_mm: markerMm.toFixed(1),
            spacing_x_mm: spacingMm[0].toFixed(1),
            spacing_y_mm: spacingMm[1].toFixed(1),
        }),
    );
}

/** Marker als Vektorgrafik: ein Rechteck je Modul, kein Rasterbild. */
function drawMarker(sheet, bits, rect) {
    if (!bits || bits.length !== MODULES * MODULES) {
        throw new Error(
            `Modulbits fehlen oder haben die falsche Groesse: erwartet ${MODULES * MODULES}, bekommen ${bits ? bits.length : "nichts"}.`,
        );
    }
    const moduleMm = rect.width / MODULES;

    sheet.setFillGray(0.0);
    sheet.setStrokeGray(0.0);
    for (let row = 0; row < MODULES; row += 1) {
        for (let col = 0; col < MODULES; col += 1) {
            if (bits[row * MODULES + col] !== 0) continue; // weisses Modul: frei lassen
            sheet.rect(
                rect.x + col * moduleMm,
                rect.y + rect.height - (row + 1) * moduleMm,
                moduleMm,
                moduleMm,
                { stroke: false, fill: true },
            );
        }
    }
}

/** Titel, Bedienhinweis, Layoutangaben und der eigene Kontrollmassstab. */
function drawInstructions(sheet, sheetW, sheetH, markerMm, spacingMm, locale = constants.DEFAULT_LOCALE) {
    const centreX = sheetW / 2.0;
    const top = sheetH / 2.0 + 34.0;

    sheet.setFillGray(0.0);
    sheet.setFont(HELVETICA_BOLD, 13);
    sheet.drawCentredString(centreX, top, translate("pdf.markersheet.title", locale));

    sheet.setFont(HELVETICA_BOLD, 9);
    sheet.drawCentredString(centreX, top - 8.0, translate("pdf.markersheet.print_hint", locale));

    const lineStep = 4.6;
    sheet.setFont(HELVETICA, 8);
    sheet.setFillGray(0.2);
    // Die drei Messzeilen stehen einzeln im Katalog: sie werden zentriert gesetzt,
    // und wo der Umbruch sitzt, entscheidet die Sprache - nicht der Code.
    const lines = [
        translate("pdf.markersheet.dictionary", locale, {
            dictionary: constants.ARUCO_DICT_NAME,
            ids: constants.SHEET_MARKER_IDS.join(", "),
        }),
        translate("pdf.markersheet.side", locale, { marker_mm: markerMm.toFixed(1) }),
        translate("pdf.markersheet.spacing", locale, {
            spacing_x_mm: spacingMm[0].toFixed(1),
            spacing_y_mm: spacingMm[1].toFixed(1),
        }),
        "",
        translate("pdf.markersheet.measure_1", locale),
        translate("pdf.markersheet.measure_2", locale),
        translate("pdf.markersheet.measure_3", locale),
    ];
    lines.forEach((line, index) => {
        sheet.drawCentredString(centreX, top - 18.0 - index * lineStep, line);
    });

    drawControlScale(sheet, centreX - constants.SCALEBAR_MM / 2.0, sheetH / 2.0 - 32.0, locale);
}

/** 100-mm-Balken mit 10-mm-Teilung, gleiche Machart wie im Export-PDF. */
function drawControlScale(sheet, x, y, locale = constants.DEFAULT_LOCALE) {
    const height = 3.0;
    sheet.setFillGray(0.0);
    sheet.setStrokeGray(0.0);
    sheet.setLineWidth(0.4);

    for (let index = 0; index < Math.floor(constants.SCALEBAR_MM / 10); index += 1) {
        if (index % 2 === 0) {
            sheet.rect(x + index * 10.0, y, 10.0, height, { stroke: false, fill: true });
        }
    }
    sheet.rect(x, y, constants.SCALEBAR_MM, height, { stroke: true, fill: false });

    sheet.setFont(HELVETICA_BOLD, 8);
    sheet.drawCentredString(
        x + constants.SCALEBAR_MM / 2.0,
        y - 5.0,
        translate("pdf.markersheet.scale_caption", locale, {
            length: constants.SCALEBAR_MM.toFixed(0),
        }),
    );
}
