/**
 * contour.js - optionale Umriss-Erkennung im bereits entzerrten Bild.
 * Gegenstueck zu app/vision/contour.py.
 *
 * Das Ergebnis ist eine Schnitthilfe, kein Messwerkzeug: es steht und faellt mit
 * dem Kontrast zwischen Objekt und Untergrund. Findet sich nichts Plausibles,
 * kommt null zurueck und das PDF wird ohne Kontur gebaut - lieber keine Linie
 * als eine falsche.
 *
 * Gerechnet wird im Kern. Hier steht der Weg dorthin und die Umrechnung in die
 * Punktform, die web/pdf/ erwartet.
 */

import { withImage } from "./core.js";

/**
 * Groesste plausible Aussenkontur als [[x, y], ...] in mm, sonst null.
 *
 * web/pdf/overlays.js erwartet Punktpaare und keine flache Liste - deshalb wird
 * hier umgeformt und nicht dort. Die Kontur hat selten mehr als ein paar hundert
 * Punkte; das faellt neben dem Rasterbild nicht ins Gewicht.
 */
export function findContourMm(core, image, pxPerMm) {
    const flat = withImage(core, image, (pointer) =>
        core.findContourMm(
            pointer,
            image.width,
            image.height,
            image.width * image.channels,
            image.channels,
            pxPerMm,
        ),
    );
    if (flat === null || flat === undefined || flat.length === 0) return null;

    const points = [];
    for (let index = 0; index < flat.length; index += 2) {
        points.push([flat[index], flat[index + 1]]);
    }
    return points;
}

/** Breite und Hoehe der Kontur in mm - fuer die Fusszeile. */
export function boundingBoxMm(contourMm) {
    let x0 = Infinity;
    let y0 = Infinity;
    let x1 = -Infinity;
    let y1 = -Infinity;
    for (const [x, y] of contourMm) {
        x0 = Math.min(x0, x);
        x1 = Math.max(x1, x);
        y0 = Math.min(y0, y);
        y1 = Math.max(y1, y);
    }
    return [x1 - x0, y1 - y0];
}
