/**
 * geometry.js - projektive Grundrechenarten, das Gegenstueck zu
 * app/vision/geometry.py.
 *
 * Hier steht nur, was reine Formel ist: Matrixprodukt, Inverse, Projektion,
 * Trapezformel. Alles, was OpenCV braucht - konvexe Huelle, Schnittflaeche,
 * lokaler Massstab, Markerflaeche -, kommt aus dem Kern (web/vision/core.js).
 * Die Grenze ist dieselbe wie auf der Python-Seite, und sie liegt dort, wo eine
 * zweite Umsetzung driften koennte.
 *
 * Punkte liegen als flache Float64Array vor (x,y,x,y,...) und nicht als Feld von
 * Objekten: so gehen sie ohne Umbau durch die embind-Grenze, und ein Foto mit
 * vier Markern hat 32 Zahlen statt 16 Objekten.
 */

/** Homographie mal Homographie, beide zeilenweise. */
export function matmul3(a, b) {
    const result = new Float64Array(9);
    for (let row = 0; row < 3; row += 1) {
        for (let column = 0; column < 3; column += 1) {
            let sum = 0.0;
            for (let k = 0; k < 3; k += 1) {
                sum += a[row * 3 + k] * b[k * 3 + column];
            }
            result[row * 3 + column] = sum;
        }
    }
    return result;
}

/**
 * Inverse einer 3x3-Matrix ueber die Adjunkte.
 *
 * numpy nimmt an derselben Stelle eine LU-Zerlegung. Beide sind exakte
 * Verfahren; sie unterscheiden sich in der letzten Stelle des Fliesskommaworts,
 * also um rund 1e-16 RELATIV. Auf 500 mm sind das 1e-13 mm. Gebraucht wird die
 * Inverse fuer die zurueckgemessene Markerkante, die Drehung und den
 * Lotpunkt-Ersatz - Anzeigewerte und eine Startschaetzung, keine Kante auf dem
 * Papier. Die Kante selbst entsteht in `rectify`, und dort rechnet der Kern.
 */
export function inv3(matrix) {
    const [a, b, c, d, e, f, g, h, i] = matrix;
    const cofactor0 = e * i - f * h;
    const cofactor1 = f * g - d * i;
    const cofactor2 = d * h - e * g;
    const determinant = a * cofactor0 + b * cofactor1 + c * cofactor2;
    if (determinant === 0 || !Number.isFinite(determinant)) {
        throw new Error("Homographie ist singulaer und laesst sich nicht invertieren");
    }
    return new Float64Array([
        cofactor0 / determinant,
        (c * h - b * i) / determinant,
        (b * f - c * e) / determinant,
        cofactor1 / determinant,
        (a * i - c * g) / determinant,
        (c * d - a * f) / determinant,
        cofactor2 / determinant,
        (b * g - a * h) / determinant,
        (a * e - b * d) / determinant,
    ]);
}

/**
 * Homographie auf Punkte anwenden und durch w teilen.
 *
 * Punkte auf dem Horizont kommen als Infinity zurueck, statt zu werfen - genau
 * wie in Python. Wer das nicht vertraegt, klippt vorher.
 */
export function project(homography, points) {
    const mapped = new Float64Array(points.length);
    for (let index = 0; index < points.length; index += 2) {
        const x = points[index];
        const y = points[index + 1];
        const w = homography[6] * x + homography[7] * y + homography[8];
        mapped[index] = (homography[0] * x + homography[1] * y + homography[2]) / w;
        mapped[index + 1] = (homography[3] * x + homography[4] * y + homography[5]) / w;
    }
    return mapped;
}

/** Rechteck als Polygon, im Uhrzeigersinn bei y-nach-unten. */
export function rectPolygon(x0, y0, x1, y1) {
    return new Float64Array([x0, y0, x1, y0, x1, y1, x0, y1]);
}

/** Flaeche eines einfachen Polygons (Gausssche Trapezformel), immer positiv. */
export function polygonArea(points) {
    const count = points.length / 2;
    if (count < 3) return 0.0;
    let sum = 0.0;
    for (let index = 0; index < count; index += 1) {
        const next = (index + 1) % count;
        sum += points[index * 2] * points[next * 2 + 1] - points[index * 2 + 1] * points[next * 2];
    }
    return Math.abs(sum) / 2.0;
}

/** Schwerpunkt einer Punktwolke. */
export function centroid(points) {
    const count = points.length / 2;
    let x = 0.0;
    let y = 0.0;
    for (let index = 0; index < count; index += 1) {
        x += points[index * 2];
        y += points[index * 2 + 1];
    }
    return [x / count, y / count];
}

/** Kleinstes umschliessendes Rechteck einer Punktwolke als [x0, y0, x1, y1]. */
export function boundingBox(points) {
    let x0 = Infinity;
    let y0 = Infinity;
    let x1 = -Infinity;
    let y1 = -Infinity;
    for (let index = 0; index < points.length; index += 2) {
        x0 = Math.min(x0, points[index]);
        x1 = Math.max(x1, points[index]);
        y0 = Math.min(y0, points[index + 1]);
        y1 = Math.max(y1, points[index + 1]);
    }
    return [x0, y0, x1, y1];
}

/**
 * Die vier Ebenenecken eines achsparallelen Markers (TL, TR, BR, BL).
 *
 * Dieselbe Reihenfolge wie cv::aruco sie liefert. Eine andere spiegelte die
 * Homographie, und das Ergebnis saehe plausibel aus.
 */
export function markerPlaneCorners(centreX, centreY, sideMm) {
    const half = sideMm / 2.0;
    return new Float64Array([
        centreX - half,
        centreY - half,
        centreX + half,
        centreY - half,
        centreX + half,
        centreY + half,
        centreX - half,
        centreY + half,
    ]);
}
