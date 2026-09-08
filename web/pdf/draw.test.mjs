/**
 * draw.test.mjs - die eine Falle des Zeichenblocks, festgenagelt.
 *
 * `font.widthOfTextAtSize()` von pdf-lib zieht die Unterschneidung der
 * Buchstabenpaare ab, gezeichnet wird der Text aber ohne sie. Wer die Zeile in
 * draw.js "vereinfacht", bekommt einen rechtsbuendigen Markenblock, der um einen
 * Zehntelmillimeter danebensteht - und keine der 33 Python-Pruefungen sieht das,
 * weil keine die Textbreite misst. Gefunden wurde es nur, weil beide Erzeuger
 * Textmarke fuer Textmarke nebeneinander vermessen wurden.
 *
 * Die Sollwerte sind reportlab.pdfbase.pdfmetrics.stringWidth der geprueften
 * Referenz, auf vier Nachkommastellen abgelesen:
 *
 *   stringWidth("Bischof Snowboards", "Helvetica-Bold", 6.4)            -> 63.6544 pt
 *   stringWidth("Made with Bischof Snowboards Software", "Helvetica", 5.6) -> 101.7744 pt
 *
 *   node --test web/pdf/draw.test.mjs
 */

import assert from "node:assert/strict";
import test from "node:test";

import { BRAND_CLAIM, BRAND_NAME } from "../constants.js";
import { Document, HELVETICA, HELVETICA_BOLD } from "./draw.js";
import { CLAIM_PT, NAME_PT } from "./branding.js";
import { mmToPt } from "./units.js";

test("Textbreite stimmt mit reportlab.stringWidth ueberein, ohne Kerning", async () => {
    const document = await Document.create({ title: "breiten", creator: "test" });

    const cases = [
        [BRAND_NAME, HELVETICA_BOLD, NAME_PT, 63.6544],
        [BRAND_CLAIM, HELVETICA, CLAIM_PT, 101.7744],
    ];
    for (const [text, font, sizePt, expectedPt] of cases) {
        const measuredPt = mmToPt(document.stringWidthMm(text, font, sizePt));
        assert.ok(
            Math.abs(measuredPt - expectedPt) < 1e-9,
            `${font} ${sizePt} pt: ${measuredPt} != ${expectedPt} (reportlab)`,
        );
    }
});
