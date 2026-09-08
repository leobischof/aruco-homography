/**
 * scattered.test.mjs - der Streu-Modus, gemessen im Browser-Kern.
 *
 * **Warum das hier noch einmal steht.** tests/test_solve.py prueft denselben
 * Modus - aber durch die Python-Bindung. Im Browser und in der App laeuft eine
 * andere Grenze: web/vision/solve.js gegen das WebAssembly. Zwischen beiden
 * liegt das Umpacken der Lagen, und ein vertauschtes x/y/Winkel-Tripel faellt
 * dort auf keiner Einzelzahl auf - es ergibt eine Schablone, die plausibel
 * aussieht und falsch ist.
 *
 * Geprueft wird an einer Homographie MIT Perspektivanteil. Bei einer reinen
 * Aehnlichkeitsabbildung waere die Ausrichtung nach dem Foto trivial, und ein
 * Vorzeichenfehler in der Drehung bliebe unsichtbar.
 *
 *   node --test web/vision/scattered.test.mjs
 */

import assert from "node:assert/strict";
import test from "node:test";

import createArucoCore from "../vendor/core/aruco_core.mjs";
import { markerPlaneCornersAt, project } from "./geometry.js";
import { NoticeList } from "./notices.js";
import { solve } from "./solve.js";

const core = await createArucoCore();

/** Ebene (mm) -> Bild (px), mit echtem Perspektivanteil. */
const HOMOGRAPHY = new Float64Array([
    3.10, 0.22, 25.0,
    0.17, 2.95, 18.0,
    0.00042, 0.00031, 1.0,
]);

const MARKER_MM = 67.0;

// Vier Marker, verstreut und in Winkeln ohne Muster. Keiner ist ein Vielfaches
// von 90 Grad: ein um 90 Grad gedrehter Marker sieht wie ein ungedrehter aus,
// wenn man die Eckenreihenfolge verwechselt, und genau das soll auffallen.
const PLACED = [
    { id: 0, centre: [40.0, 50.0], deg: 37.0 },
    { id: 1, centre: [220.0, 35.0], deg: -62.0 },
    { id: 2, centre: [55.0, 260.0], deg: 128.0 },
    { id: 3, centre: [240.0, 275.0], deg: 15.0 },
];

/** Die Marker so, wie die Erkennung sie liefern wuerde. */
function detected() {
    return PLACED.map((marker) => {
        const plane = markerPlaneCornersAt(
            marker.centre[0], marker.centre[1], (marker.deg * Math.PI) / 180.0, MARKER_MM,
        );
        const corners = project(HOMOGRAPHY, plane);
        return { id: marker.id, corners, areaPx: core.quadArea(corners) };
    });
}

/** Der Winkel eines Markers in der Ebene, aus der Kante Ecke 0 -> Ecke 1. */
function angleDeg(quad) {
    return (Math.atan2(quad[3] - quad[1], quad[2] - quad[0]) * 180.0) / Math.PI;
}

const solution = solve(core, detected(), MARKER_MM, "scattered", new NoticeList());

test("der Ausgleich geht rauschfrei auf", () => {
    assert.ok(solution.rmsPx < 1e-6, `rms ${solution.rmsPx} px`);
    for (const fit of solution.markers) {
        assert.ok(Math.abs(fit.sideMmMeasured - MARKER_MM) < 1e-6,
            `Marker ${fit.id}: ${fit.sideMmMeasured} statt ${MARKER_MM} mm`);
    }
});

test("ein bekannter Abstand kommt in Millimetern zurueck", () => {
    // Zwei Punkte der WAHREN Ebene, 500 mm auseinander. Durch die wahre
    // Homographie ins Bild, durch die GELOESTE zurueck - was herauskommt, muss
    // wieder 500 mm sein.
    const truth = new Float64Array([-100.0, 150.0, 400.0, 150.0]);
    const inImage = project(HOMOGRAPHY, truth);
    const back = project(inverse(solution.homography), inImage);
    const measured = Math.hypot(back[2] - back[0], back[3] - back[1]);
    assert.ok(Math.abs(measured - 500.0) < 1e-6, `${measured} mm statt 500`);
});

test("jeder Marker bekommt seinen Winkel zurueck", () => {
    const found = new Map(solution.markers.map((fit) => [fit.id, angleDeg(fit.planeMm)]));

    // Die UNTERSCHIEDE der Winkel stecken allein in den Markerecken und muessen
    // deshalb exakt herauskommen.
    const reference = PLACED[0];
    for (const marker of PLACED) {
        const expected = marker.deg - reference.deg;
        const measured = found.get(marker.id) - found.get(reference.id);
        const off = Math.abs((((measured - expected + 180.0) % 360.0) + 360.0) % 360.0 - 180.0);
        assert.ok(off < 1e-6, `Marker ${marker.id}: ${measured} statt ${expected} Grad`);
    }
});

test("die Ebene richtet sich nach dem Foto, nicht nach dem groessten Marker", () => {
    // Haette der Anker die Achsen gesetzt, stuende er bei 0 Grad und alle
    // anderen relativ zu ihm - der groesste Marker liegt hier bei 37 Grad, die
    // Schablone stuende also um 37 Grad schief.
    //
    // Stattdessen steht jeder Marker fast in dem Winkel da, in dem er in der
    // WAHREN Ebene liegt. Fast: uebrig bleibt ein knappes Grad, und das ist
    // richtig so. Diese Homographie dreht selbst ein wenig und schert dazu; die
    // Drehung nimmt die Ausrichtung heraus, die Scherung kann sie nicht - eine
    // Drehung macht aus einer gescherten Abbildung keine unverzerrte. Der Rest
    // ist fuer JEDEN Marker derselbe (der Test darueber nagelt die Unterschiede
    // auf 1e-6 fest), also ist es eine Lage der Ebene und kein Markerfehler.
    const found = new Map(solution.markers.map((fit) => [fit.id, angleDeg(fit.planeMm)]));
    for (const marker of PLACED) {
        const off = Math.abs(found.get(marker.id) - marker.deg);
        assert.ok(off < 1.5, `Marker ${marker.id}: ${found.get(marker.id)} statt ${marker.deg}`);
    }

    // Und die Probe darauf, dass es wirklich die Scherung ist: nach der
    // Ausrichtung dreht die Abbildung Ebene -> Bild in der Wolkenmitte nicht
    // mehr. Was bleibt, ist eine symmetrische Streckung.
    const h = solution.homography;
    const w = h[8];
    const u = h[2] / w;
    const v = h[5] / w;
    const duDx = (h[0] - u * h[6]) / w;
    const duDy = (h[1] - u * h[7]) / w;
    const dvDx = (h[3] - v * h[6]) / w;
    const dvDy = (h[4] - v * h[7]) / w;
    const turnDeg = (Math.atan2(dvDx - duDy, duDx + dvDy) * 180.0) / Math.PI;
    assert.ok(Math.abs(turnDeg) < 1e-9, `Rest-Drehung ${turnDeg} Grad`);
});

test("der Ursprung liegt in der Mitte der Markerwolke", () => {
    let x = 0.0;
    let y = 0.0;
    for (const fit of solution.markers) {
        for (let corner = 0; corner < 4; corner += 1) {
            x += fit.planeMm[corner * 2] / (4 * solution.markers.length);
            y += fit.planeMm[corner * 2 + 1] / (4 * solution.markers.length);
        }
    }
    assert.ok(Math.hypot(x, y) < 1e-9, `Mitte bei ${x}, ${y}`);
});

test("ein einzelner Marker reicht - und wird gemeldet", () => {
    const notices = new NoticeList();
    const single = solve(core, detected().slice(0, 1), MARKER_MM, "scattered", notices);

    assert.ok(single.rmsPx < 1e-6);
    assert.ok(notices.items.some((notice) => notice.code === "single_marker"));
});

/** 3x3 invertieren - hier nur fuer die Rueckrechnung des Pruefabstands. */
function inverse(matrix) {
    const [a, b, c, d, e, f, g, h, i] = matrix;
    const determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
    return new Float64Array([
        (e * i - f * h) / determinant, (c * h - b * i) / determinant,
        (b * f - c * e) / determinant,
        (f * g - d * i) / determinant, (a * i - c * g) / determinant,
        (c * d - a * f) / determinant,
        (d * h - e * g) / determinant, (b * g - a * h) / determinant,
        (a * e - b * d) / determinant,
    ]);
}
