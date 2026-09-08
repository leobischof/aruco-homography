/**
 * density.test.mjs - traegt die Bilddatei hinterher wirklich ihre Auflösung?
 *
 * Geprueft wird nicht, dass die Funktion etwas zurueckgibt, sondern dass das
 * Ergebnis eine GUELTIGE Datei ist, aus der ein Leser dieselbe Zahl wieder
 * herausholt. Ein pHYs mit falscher Pruefsumme wuerde von einem strengen
 * Betrachter zurueckgewiesen - und von einem nachsichtigen stillschweigend
 * ignoriert. Beides saehe hier ohne Nachlesen richtig aus.
 *
 *   node --test web/vision/density.test.mjs
 */

import assert from "node:assert/strict";
import { deflateSync } from "node:zlib";
import test from "node:test";

import { withResolution } from "./density.js";

const METRE_PER_INCH = 0.0254;

// --- Ein PNG von Hand, damit es hier keinen Kodierer braucht ----------------

function chunk(name, data) {
    const body = new Uint8Array(4 + data.length);
    body.set([...name].map((letter) => letter.charCodeAt(0)), 0);
    body.set(data, 4);

    const out = new Uint8Array(body.length + 8);
    new DataView(out.buffer).setUint32(0, data.length);
    out.set(body, 4);
    new DataView(out.buffer).setUint32(out.length - 4, crc32(body));
    return out;
}

/** Ein 2x1-PNG, echt genug fuer jeden Leser. */
function tinyPng() {
    const header = new Uint8Array(13);
    const view = new DataView(header.buffer);
    view.setUint32(0, 2);       // Breite
    view.setUint32(4, 1);       // Hoehe
    header[8] = 8;              // Bittiefe
    header[9] = 2;              // Farbtyp: RGB
    // Filter-Byte 0, dann zwei Pixel
    const pixels = deflateSync(Buffer.from([0, 255, 0, 0, 0, 0, 255]));

    return concat([
        new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
        chunk("IHDR", header),
        chunk("IDAT", pixels),
        chunk("IEND", new Uint8Array(0)),
    ]);
}

function concat(parts) {
    const size = parts.reduce((sum, part) => sum + part.length, 0);
    const out = new Uint8Array(size);
    let offset = 0;
    for (const part of parts) {
        out.set(part, offset);
        offset += part.length;
    }
    return out;
}

/** Die Bruchstuecke eines PNG auflisten - Name, Daten, Pruefsumme stimmt? */
function chunksOf(bytes) {
    const found = [];
    let at = 8;
    while (at + 12 <= bytes.length) {
        const view = new DataView(bytes.buffer, bytes.byteOffset + at);
        const length = view.getUint32(0);
        const name = String.fromCharCode(...bytes.subarray(at + 4, at + 8));
        const data = bytes.subarray(at + 8, at + 8 + length);
        const stored = view.getUint32(8 + length);
        found.push({
            name,
            data,
            crcOk: stored === crc32(bytes.subarray(at + 4, at + 8 + length)),
        });
        at += 12 + length;
    }
    assert.equal(at, bytes.length, "das PNG endet nicht auf einer Bruchstueckgrenze");
    return found;
}

function crc32(bytes) {
    let crc = 0xffffffff;
    for (const byte of bytes) {
        crc ^= byte;
        for (let bit = 0; bit < 8; bit += 1) {
            crc = crc & 1 ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1;
        }
    }
    return (crc ^ 0xffffffff) >>> 0;
}

// --- PNG ---------------------------------------------------------------------

test("das PNG traegt ein gueltiges pHYs mit der richtigen Zahl", () => {
    const stamped = withResolution(tinyPng(), "png", 300);
    const chunks = chunksOf(stamped);

    for (const part of chunks) {
        assert.ok(part.crcOk, `Pruefsumme von ${part.name} stimmt nicht`);
    }

    const physical = chunks.filter((part) => part.name === "pHYs");
    assert.equal(physical.length, 1, "genau ein pHYs, sonst ist das PNG ungueltig");

    const view = new DataView(physical[0].data.buffer, physical[0].data.byteOffset);
    assert.equal(physical[0].data.length, 9);
    assert.equal(physical[0].data[8], 1, "Einheit muss der Meter sein");
    // 300 dpi sind 11811 Punkte je Meter (300 / 0,0254, gerundet).
    assert.equal(view.getUint32(0), Math.round(300 / METRE_PER_INCH));
    assert.equal(view.getUint32(4), Math.round(300 / METRE_PER_INCH));
});

test("pHYs steht vor IDAT - hinterher waere es ungueltig", () => {
    const names = chunksOf(withResolution(tinyPng(), "png", 150)).map((part) => part.name);
    assert.deepEqual(names, ["IHDR", "pHYs", "IDAT", "IEND"]);
});

test("die Bildpunkte bleiben Byte fuer Byte dieselben", () => {
    const before = chunksOf(tinyPng()).find((part) => part.name === "IDAT");
    const after = chunksOf(withResolution(tinyPng(), "png", 300)).find((p) => p.name === "IDAT");
    assert.deepEqual([...after.data], [...before.data]);
});

test("zweimal stempeln ergibt nicht zwei pHYs", () => {
    const once = withResolution(tinyPng(), "png", 300);
    const twice = withResolution(once, "png", 600);
    const chunks = chunksOf(twice);

    assert.equal(chunks.filter((part) => part.name === "pHYs").length, 1);
    const physical = chunks.find((part) => part.name === "pHYs");
    const view = new DataView(physical.data.buffer, physical.data.byteOffset);
    assert.equal(view.getUint32(0), Math.round(600 / METRE_PER_INCH));
});

// --- JPEG --------------------------------------------------------------------

/** Ein JPEG-Anfang mit JFIF-Abschnitt, so wie eine Leinwand ihn schreibt. */
function jpegWithJfif() {
    return new Uint8Array([
        0xff, 0xd8,
        0xff, 0xe0, 0x00, 0x10,
        0x4a, 0x46, 0x49, 0x46, 0x00,
        0x01, 0x01,
        0x00,                        // Einheit 0: nur Seitenverhaeltnis
        0x00, 0x01, 0x00, 0x01,      // Dichte 1:1
        0x00, 0x00,
        0xff, 0xd9,
    ]);
}

test("die JFIF-Dichte wird auf dpi gestellt", () => {
    const stamped = withResolution(jpegWithJfif(), "jpeg", 300);

    assert.equal(stamped.length, jpegWithJfif().length, "nichts eingefuegt, nur gesetzt");
    assert.equal(stamped[13], 1, "Einheit muss 'Punkte je Zoll' sein");
    assert.equal((stamped[14] << 8) | stamped[15], 300);
    assert.equal((stamped[16] << 8) | stamped[17], 300);
});

test("fehlt der JFIF-Abschnitt, wird er eingesetzt - und zwar ganz vorn", () => {
    // Ein JPEG, das mit EXIF (APP1) statt JFIF beginnt.
    const withExif = new Uint8Array([0xff, 0xd8, 0xff, 0xe1, 0x00, 0x04, 0x00, 0x00, 0xff, 0xd9]);
    const stamped = withResolution(withExif, "jpeg", 150);

    assert.equal(stamped.length, withExif.length + 18);
    assert.deepEqual([...stamped.subarray(0, 4)], [0xff, 0xd8, 0xff, 0xe0]);
    assert.equal(stamped[13], 1);
    assert.equal((stamped[14] << 8) | stamped[15], 150);
    // Und der Rest steht unveraendert dahinter.
    assert.deepEqual([...stamped.subarray(20)], [...withExif.subarray(2)]);
});

test("was sich nicht stempeln laesst, kommt unveraendert zurueck", () => {
    // Ein Bild ohne Auflösungsangabe ist schlechter als eines mit, aber besser
    // als gar keines - hier wird nichts geworfen.
    const rubbish = new Uint8Array([1, 2, 3, 4]);
    assert.equal(withResolution(rubbish, "png", 300), rubbish);
    assert.equal(withResolution(rubbish, "jpeg", 300), rubbish);

    const png = tinyPng();
    assert.equal(withResolution(png, "png", 0), png, "ohne dpi bleibt alles, wie es war");
    assert.equal(withResolution(png, "webp", 300), png, "unbekanntes Format: unangetastet");
});
