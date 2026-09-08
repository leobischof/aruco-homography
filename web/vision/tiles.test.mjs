/**
 * tiles.test.mjs - blattweise entzerren muss dasselbe ergeben wie am Stueck.
 *
 * **Die Zusage, die hier geprueft wird.** Seit dem Speicherfehler vom 08.09.2026
 * rastert `runExport` die Kachelung BLATTWEISE: nicht ein Raster ueber den ganzen
 * Zuschnitt (bei 810 x 1153 mm und 300 dpi sind das 130 Megapixel und 373 MiB an
 * einem Stueck, die ein Telefon nicht hergibt), sondern eines je A4-Blatt. Das ist
 * nur dann eine reine Speicherfrage und keine Aenderung am Erzeugnis, wenn beide
 * Wege **Bit fuer Bit** dasselbe liefern.
 *
 * **Warum sie ueberhaupt gelten kann.** core/src/rectify.cpp bildet Ausgabepixel u
 * auf `crop.x0 + (u + 0,5) / px_per_mm` ab. Ein Teilraster, das an einer
 * GANZZAHLIGEN Pixelgrenze beginnt, tastet damit genau dieselben Stellen der Ebene
 * ab wie der entsprechende Ausschnitt des grossen Rasters. Die Interpolation liest
 * dabei aus dem QUELLFOTO - das liegt fuer jedes Blatt vollstaendig vor, also gibt
 * es an den Blattgrenzen keinen abgeschnittenen Filterkern und keinen Randeffekt.
 *
 * Diese Datei prueft genau das, und zwar an einer Homographie MIT Perspektivanteil:
 * bei einer reinen Verschiebung waere die Aussage trivial und ein Fehler im
 * Gitterversatz bliebe unsichtbar.
 *
 *   node --test web/vision/tiles.test.mjs
 */

import assert from "node:assert/strict";
import test from "node:test";

import createArucoCore from "../vendor/core/aruco_core.mjs";
import { extent } from "./extent.js";
import { outputSize, rectify } from "./rectify.js";

const core = await createArucoCore();

/**
 * Ein Bild mit Struktur bis in einzelne Pixel.
 *
 * Eine glatte Flaeche wuerde jeden Gitterversatz verzeihen - zwei benachbarte
 * Pixel waeren gleich, und ein Versatz um eines faellt nicht auf. Deshalb hier
 * ein Muster, das sich in JEDEM Pixel aendert.
 */
function scene(width, height) {
    const data = new Uint8Array(width * height * 3);
    for (let y = 0; y < height; y += 1) {
        for (let x = 0; x < width; x += 1) {
            const base = (y * width + x) * 3;
            data[base] = (x * 7 + y * 3) % 256;
            data[base + 1] = (x * 13 + y * 29) % 256;
            data[base + 2] = ((x ^ y) * 5) % 256;
        }
    }
    return { data, width, height, channels: 3 };
}

/**
 * Ebene (mm) -> Bild (px), mit echtem Perspektivanteil.
 *
 * Die letzten beiden Glieder sind nicht null; damit ist die Abbildung wirklich
 * projektiv und nicht bloss affin.
 */
const HOMOGRAPHY = [
    3.10, 0.22, 25.0,
    0.17, 2.95, 18.0,
    0.00042, 0.00031, 1.0,
];

const IMAGE = scene(420, 320);
const PX_PER_MM = 4.0;
const CROP = extent(-12.5, 7.25, 47.5, 47.25);

/** Ein Blatt: dasselbe Gitter, nur ab Pixel (x0, y0) und w x h gross. */
function sheetOf(x0, y0, w, h) {
    return extent(
        CROP.x0 + x0 / PX_PER_MM,
        CROP.y0 + y0 / PX_PER_MM,
        CROP.x0 + (x0 + w) / PX_PER_MM,
        CROP.y0 + (y0 + h) / PX_PER_MM,
    );
}

const whole = rectify(core, IMAGE, HOMOGRAPHY, CROP, PX_PER_MM, 0.0);

test("der Zuschnitt ergibt das erwartete Gitter", () => {
    const [w, h] = outputSize(core, CROP, PX_PER_MM);
    assert.deepEqual([whole.width, whole.height], [w, h]);
    assert.deepEqual([whole.width, whole.height], [240, 160]);
    assert.equal(whole.channels, 3);
});

test("ein Blatt ist Bit fuer Bit der Ausschnitt aus dem Ganzen", () => {
    // Vier Lagen, die zusammen die Faelle abdecken, an denen ein Gitterversatz
    // sichtbar wuerde: Ursprung, versetzt, am rechten Rand, am unteren Rand.
    const sheets = [
        [0, 0, 96, 64],
        [96, 64, 96, 64],
        [144, 0, 96, 64],
        [0, 96, 96, 64],
    ];

    for (const [x0, y0, w, h] of sheets) {
        const sheet = rectify(core, IMAGE, HOMOGRAPHY, sheetOf(x0, y0, w, h), PX_PER_MM, 0.0);
        assert.deepEqual([sheet.width, sheet.height], [w, h],
            `Blatt ${x0},${y0}: ${sheet.width}x${sheet.height} statt ${w}x${h}`);

        for (let row = 0; row < h; row += 1) {
            const from = ((y0 + row) * whole.width + x0) * 3;
            const expected = whole.data.subarray(from, from + w * 3);
            const actual = sheet.data.subarray(row * w * 3, (row + 1) * w * 3);
            // Erst vergleichen, dann suchen: eine Meldung mit dem ersten
            // abweichenden Pixel ist brauchbar, "Buffers differ" ist es nicht.
            if (Buffer.compare(Buffer.from(actual), Buffer.from(expected)) !== 0) {
                const at = actual.findIndex((value, index) => value !== expected[index]);
                assert.fail(
                    `Blatt ${x0},${y0}, Zeile ${row}, Byte ${at}: `
                    + `${actual[at]} statt ${expected[at]}`,
                );
            }
        }
    }
});

test("die Blaetter decken das Ganze luecken- und ueberlappungsfrei", () => {
    // Der zweite Teil der Zusage: nicht nur stimmt jedes Blatt fuer sich, die
    // Blaetter setzen das Ganze auch wieder zusammen. Ohne das koennte jedes
    // einzelne Blatt richtig sein und der Druck trotzdem eine Naht haben.
    const rebuilt = new Uint8Array(whole.data.length);
    const step = 70; // absichtlich kein Teiler von 240 bzw. 160
    for (let y0 = 0; y0 < whole.height; y0 += step) {
        for (let x0 = 0; x0 < whole.width; x0 += step) {
            const w = Math.min(step, whole.width - x0);
            const h = Math.min(step, whole.height - y0);
            const sheet = rectify(core, IMAGE, HOMOGRAPHY, sheetOf(x0, y0, w, h), PX_PER_MM, 0.0);
            for (let row = 0; row < h; row += 1) {
                rebuilt.set(
                    sheet.data.subarray(row * w * 3, (row + 1) * w * 3),
                    ((y0 + row) * whole.width + x0) * 3,
                );
            }
        }
    }
    assert.equal(Buffer.compare(Buffer.from(rebuilt), Buffer.from(whole.data)), 0);
});
