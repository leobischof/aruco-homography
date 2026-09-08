/**
 * overview.test.mjs - der Klebeplan holt sich sein Bild grob, nicht in Druckguete.
 *
 * **Was hier auf dem Spiel steht.** Seit dem Speicherfehler vom 08.09.2026 rastert
 * die Kachelung BLATTWEISE (web/vision/tiles.test.mjs sagt, warum das erlaubt ist).
 * Der Klebeplan braucht aber den GANZEN Zuschnitt in einem Bild - und wenn er den
 * in Druckaufloesung anforderte, entstuende genau das Raster wieder, dessen
 * Vermeidung den Export auf dem Telefon erst moeglich gemacht hat: 810 x 1153 mm
 * bei 300 dpi sind 130 Megapixel und 373 MiB an einem Stueck.
 *
 * Deshalb fragt er mit Deckel. Geprueft wird hier genau diese Frage - womit die
 * Bildquelle gerufen wird - und nicht, was am Ende auf dem Papier steht: dass die
 * Uebersichtsseite ein Bild TRAEGT, misst tests/test_pdf_size.py am fertigen PDF,
 * und zwar fuer beide Erzeuger.
 *
 * Der Python-Pruefstand (tools/pdf_js_bridge.py) kommt hier nie vorbei: er reicht
 * immer fertige Bytes herueber, also den Weg AM STUECK. Der blattweise Weg wird
 * nur an dieser Stelle gefahren.
 *
 *   node --test web/pdf/overview.test.mjs
 */

import assert from "node:assert/strict";
import test from "node:test";

import { OVERVIEW_MAX_PX } from "../constants.js";
import { buildPdf, exportOptions } from "./build.js";

/**
 * Ein winziges, echtes JPEG - 8 x 5 Pixel.
 *
 * pdf-lib liest aus den Bytes die Kantenlaengen; ein Platzhalter aus Nullen taete
 * es also nicht. Erzeugt mit Pillow, damit die Zeile nachvollziehbar bleibt:
 *
 *   Image.new("RGB", (8, 5)) ... .save(buf, format="JPEG", quality=25, optimize=True)
 *
 * Das `new Uint8Array(...)` um den Buffer herum ist kein Zierrat: pdf-lib liest die
 * Bytes als `new DataView(imageData.buffer)` und UEBERGEHT dabei den byteOffset.
 * Node bedient kleine Buffer aus einem gemeinsamen Vorrat, deren Offset also nicht
 * null ist - pdf-lib laese dann den Nachbarn und meldete "SOI not found in JPEG".
 * Die Kopie liegt am Anfang eines eigenen Puffers.
 */
const JPEG = new Uint8Array(Buffer.from(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDACAWGBwYFCAcGhwkIiAmMFA0MCwsMGJGSjpQdGZ6eH"
    + "JmcG6AkLicgIiuim5woNqirr7EztDOfJri8uDI8LjKzsb/2wBDASIkJDAqMF40NF7GhHCExsbG"
    + "xsbGxsbGxsbGxsbGxsbGxsbGxsbGxsbGxsbGxsbGxsbGxsbGxsbGxsbGxsbGxsb/wAARCAAFAA"
    + "gDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAAAP/EABcQAQEBAQAAAAAAAAAAAAAAAAAD"
    + "BCH/xAAVAQEBAAAAAAAAAAAAAAAAAAABA//EABkRAAIDAQAAAAAAAAAAAAAAAAACAxExEv/aAA"
    + "wDAQACEQMRAD8AQxS4AmztehBI3Gn/2Q==",
    "base64",
));

const CROP_W = 700.0;
const CROP_H = 500.0;

/** Eine blattweise Quelle, die sich merkt, wonach sie gefragt wurde. */
function recordingSource() {
    const calls = [];
    const source = async (xMm, yMm, widthMm, heightMm, maxPx = 0) => {
        calls.push({ xMm, yMm, widthMm, heightMm, maxPx });
        return JPEG;
    };
    return { source, calls };
}

const TILED = {
    layout: "tiles",
    pageFormat: "A4",
    orientation: "portrait",
    dpi: 300,
};

test("der Klebeplan fragt den ganzen Zuschnitt mit Deckel", async () => {
    const { source, calls } = recordingSource();
    const result = await buildPdf(
        source,
        CROP_W,
        CROP_H,
        exportOptions({ ...TILED, tileOverview: true }),
        ["Test"],
    );

    const capped = calls.filter((call) => call.maxPx > 0);
    assert.equal(capped.length, 1, "genau eine Anfrage mit Deckel - der Klebeplan");
    assert.equal(capped[0].maxPx, OVERVIEW_MAX_PX);
    assert.deepEqual(
        [capped[0].xMm, capped[0].yMm, capped[0].widthMm, capped[0].heightMm],
        [0.0, 0.0, CROP_W, CROP_H],
        "und zwar nach dem GANZEN Zuschnitt",
    );

    // Der Deckel ist die erste Frage: die Uebersicht steht vor den Kacheln.
    assert.equal(calls[0].maxPx, OVERVIEW_MAX_PX);
    assert.equal(result.pageCount, result.meta.tiles + 1);
});

test("die Kachelblaetter fragen ohne Deckel - sie werden gedruckt", async () => {
    const { source, calls } = recordingSource();
    const result = await buildPdf(
        source,
        CROP_W,
        CROP_H,
        exportOptions({ ...TILED, tileOverview: true }),
        ["Test"],
    );

    const sheets = calls.slice(1);
    assert.equal(sheets.length, result.meta.tiles);
    for (const call of sheets) {
        assert.equal(call.maxPx, 0, "ein Blatt wird in Druckaufloesung gerastert");
    }
});

test("ohne Klebeplan wird nie mit Deckel gefragt", async () => {
    const { source, calls } = recordingSource();
    await buildPdf(
        source,
        CROP_W,
        CROP_H,
        exportOptions({ ...TILED, tileOverview: false }),
        ["Test"],
    );

    assert.ok(calls.length > 0, "die Blaetter werden trotzdem gerastert");
    assert.equal(calls.filter((call) => call.maxPx > 0).length, 0);
});
