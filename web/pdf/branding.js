/**
 * branding.js - Markenzeichen auf dem Papier: Logo und Herkunftszeile.
 *
 * Hier wohnt Invariante 3: Logo und "Made with Bischof Snowboards Software"
 * stehen auf JEDEM Blatt - Einzelseite, jede Kachel, Klebeplan, Markerblatt.
 * Massstab und Fusszeile sind abschaltbar, diese beiden nicht. Geprueft in
 * tests/test_branding.py, und zwar fuer jede Seite eines gekachelten Exports.
 *
 * Das Logo ist ein VEKTOR, kein Rasterbild - bei jeder Druckgroesse scharf. Wo
 * app/pdf/branding.py `svglib` die Originaldatei lesen laesst, liegen hier die
 * gebackenen Pfaddaten aus assets/logo.js: im Browser gibt es kein Dateisystem.
 * Dieselbe Zeichnung, derselbe Weg zur Marke - nur die Quelle ist eine andere.
 *
 * Die Tinte ist bewusst die von logo-dark.svg (#334155, das Marken-Foreground):
 * auf Papier liest sich das ruhiger als reines Schwarz und passt zur Fusszeile
 * daneben.
 */

import { LOGO_OPS, LOGO_VIEWBOX } from "./assets/logo.js";
import * as constants from "./constants.js";
import { HELVETICA, HELVETICA_BOLD, colorFromHex } from "./draw.js";

export const CLAIM_PT = 5.6;
export const NAME_PT = 6.4;
export const GAP_MM = 2.0;

/** Markenfarbe als pdf-lib-Farbe. */
export function ink(hexColour) {
    return colorFromHex(hexColour);
}

/** Zeichnet das Logo mit der linken unteren Ecke bei (x, y). Gibt die Breite in mm. */
export function drawLogo(sheet, xMm, yMm, heightMm = constants.LOGO_MM) {
    return sheet.drawVectorArt(LOGO_OPS, LOGO_VIEWBOX, xMm, yMm, heightMm);
}

/**
 * Logo rechtsbuendig, Herkunftszeile links daneben. Gibt die linke Kante in mm.
 *
 * Der Aufrufer kann am Rueckgabewert ablesen, wie viel Platz noch frei ist -
 * auf schmalen Seiten laesst er die Herkunftszeile weg, das Logo bleibt.
 */
export function drawBrandBlock(sheet, rightXMm, yMm, heightMm, withClaim = true) {
    const logoMm = Math.min(constants.LOGO_MM, heightMm - 1.0);
    const logoX = rightXMm - logoMm;
    drawLogo(sheet, logoX, yMm + (heightMm - logoMm) / 2.0, logoMm);

    if (!withClaim) {
        link(sheet, logoX, yMm, rightXMm, yMm + heightMm);
        return logoX;
    }

    const textRight = logoX - GAP_MM;
    sheet.setFillColor(ink(constants.BRAND_INK));

    sheet.setFont(HELVETICA_BOLD, NAME_PT);
    sheet.drawRightString(textRight, yMm + heightMm / 2.0 + 0.4, constants.BRAND_NAME);
    sheet.setFont(HELVETICA, CLAIM_PT);
    sheet.drawRightString(textRight, yMm + heightMm / 2.0 - 2.6, constants.BRAND_CLAIM);

    const left = textRight - claimWidthMm(sheet);
    link(sheet, left, yMm, rightXMm, yMm + heightMm);
    return left;
}

/** Den ganzen Markenblock im PDF anklickbar machen. */
function link(sheet, x0, y0, x1, y1) {
    sheet.linkURL(constants.BRAND_URL, [x0, y0, x1, y1]);
}

/** Breite der Herkunftszeile in mm - fuer die Platzentscheidung des Aufrufers. */
export function claimWidthMm(sheet) {
    return Math.max(
        sheet.stringWidthMm(constants.BRAND_CLAIM, HELVETICA, CLAIM_PT),
        sheet.stringWidthMm(constants.BRAND_NAME, HELVETICA_BOLD, NAME_PT),
    );
}

/** Gesamtbreite des Markenblocks - damit Aufrufer vorher Platz reservieren koennen. */
export function blockWidthMm(sheet, withClaim = true) {
    if (!withClaim) return constants.LOGO_MM;
    return constants.LOGO_MM + GAP_MM + claimWidthMm(sheet);
}
