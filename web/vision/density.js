/**
 * density.js - die Auflösung IN die Bilddatei schreiben.
 *
 * **Warum das sein muss.** Ein PDF traegt seine Millimeter selbst: eine Seite ist
 * 210 mm breit, und der Drucker weiss das. Ein JPEG oder PNG traegt nur Pixel.
 * Wer ein Bild ohne Auflösungsangabe in ein anderes Programm laedt, bekommt dort
 * die Vorgabe dieses Programms - 72 dpi, 96 dpi, was auch immer -, und aus einer
 * maßhaltigen Schablone wird stillschweigend eine beliebig grosse. Das ist genau
 * die Sorte Fehler, gegen die dieses ganze Vorhaben steht: sie sieht auf dem
 * Bildschirm richtig aus.
 *
 * Beide Formate haben ein Feld dafuer, und beide Kodierer, die hier in Frage
 * kommen, lassen es leer:
 *
 *   - Die Leinwand des Browsers schreibt JFIF mit `units = 0` (Seitenverhaeltnis
 *     statt Auflösung) und ueberhaupt kein `pHYs`.
 *   - `Bitmap.compress` auf Android schreibt ebenfalls keines.
 *
 * Also wird es hier nachgetragen. Diese Datei fasst NUR die Kopfdaten an - die
 * Bildpunkte bleiben Byte fuer Byte, wie der Kodierer sie geschrieben hat.
 *
 * Auf der Python-Seite macht das PIL selbst (`Image.save(..., dpi=...)`);
 * app/vision/encode.py sagt, warum das dort keine zweite Fassung ist.
 */

/** Zoll in Metern - die Einheit, in der PNG rechnet. */
const METRE_PER_INCH = 0.0254;

/**
 * Die Auflösung in die Bytes schreiben. Gibt IMMER ein neues Feld zurueck.
 *
 * `format` ist "jpeg" oder "png"; `dpi` die Auflösung, mit der das Raster
 * gerechnet wurde. Ein unbekanntes Format oder unbrauchbare Bytes werden
 * unveraendert durchgereicht: ein Bild ohne Auflösungsangabe ist schlechter als
 * eines mit, aber besser als gar keines.
 */
export function withResolution(bytes, format, dpi) {
    if (!(dpi > 0)) return bytes;
    if (format === "png") return pngWithResolution(bytes, dpi);
    if (format === "jpeg") return jpegWithResolution(bytes, dpi);
    return bytes;
}

/**
 * PNG: ein `pHYs`-Bruchstueck hinter IHDR.
 *
 * Aufbau eines Bruchstuecks: 4 Bytes Laenge, 4 Bytes Name, die Daten, 4 Bytes
 * CRC ueber Name UND Daten (nicht ueber die Laenge). `pHYs` traegt neun Bytes:
 * Punkte je Meter in x, Punkte je Meter in y, und eine 1 fuer "die Einheit ist
 * der Meter".
 *
 * Es MUSS vor IDAT stehen (PNG-Norm, 11.3.5.3); hinter IHDR ist die Stelle, die
 * immer zulaessig ist. Ist schon eines da, wird es ersetzt statt ein zweites
 * angehaengt - zwei pHYs sind ein ungueltiges PNG.
 */
function pngWithResolution(bytes, dpi) {
    const SIGNATURE = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
    if (bytes.length < 8 + 25) return bytes;
    for (let index = 0; index < 8; index += 1) {
        if (bytes[index] !== SIGNATURE[index]) return bytes;
    }

    const perMetre = Math.round(dpi / METRE_PER_INCH);
    const chunk = new Uint8Array(21);
    const view = new DataView(chunk.buffer);
    view.setUint32(0, 9);
    chunk.set([0x70, 0x48, 0x59, 0x73], 4);   // "pHYs"
    view.setUint32(8, perMetre);
    view.setUint32(12, perMetre);
    chunk[16] = 1;                            // Einheit: Meter
    view.setUint32(17, crc32(chunk.subarray(4, 17)));

    // IHDR ist immer das erste Bruchstueck und immer 25 Bytes lang.
    const afterHeader = 8 + 25;
    const rest = withoutChunk(bytes.subarray(afterHeader), "pHYs");

    const result = new Uint8Array(afterHeader + chunk.length + rest.length);
    result.set(bytes.subarray(0, afterHeader), 0);
    result.set(chunk, afterHeader);
    result.set(rest, afterHeader + chunk.length);
    return result;
}

/** Dieselben Bruchstuecke, nur ohne die mit diesem Namen. */
function withoutChunk(bytes, name) {
    const wanted = [...name].map((letter) => letter.charCodeAt(0));
    const keep = [];
    let at = 0;
    while (at + 12 <= bytes.length) {
        const length = new DataView(bytes.buffer, bytes.byteOffset + at, 4).getUint32(0);
        const total = 12 + length;
        if (at + total > bytes.length) break;
        const matches = wanted.every((code, index) => bytes[at + 4 + index] === code);
        if (!matches) keep.push(bytes.subarray(at, at + total));
        at += total;
    }
    if (at !== bytes.length) return bytes;  // unerwarteter Aufbau: nichts anfassen

    const size = keep.reduce((sum, part) => sum + part.length, 0);
    const result = new Uint8Array(size);
    let offset = 0;
    for (const part of keep) {
        result.set(part, offset);
        offset += part.length;
    }
    return result;
}

/**
 * JPEG: die Dichte im JFIF-Abschnitt (APP0).
 *
 * Aufbau ab dem Marker: FFE0, zwei Bytes Laenge, "JFIF\0", zwei Bytes Fassung,
 * ein Byte Einheit, zwei Bytes x-Dichte, zwei Bytes y-Dichte. Einheit 1 heisst
 * "Punkte je Zoll" - genau unser dpi.
 *
 * Fehlt der Abschnitt, wird er hinter FFD8 eingesetzt. Er muss dort stehen und
 * nicht irgendwo: JFIF verlangt APP0 als ERSTEN Abschnitt der Datei.
 */
function jpegWithResolution(bytes, dpi) {
    if (bytes.length < 4 || bytes[0] !== 0xff || bytes[1] !== 0xd8) return bytes;
    const density = Math.min(65535, Math.max(1, Math.round(dpi)));

    if (bytes[2] === 0xff && bytes[3] === 0xe0 && bytes.length >= 20 &&
        bytes[4 + 2] === 0x4a && bytes[4 + 3] === 0x46 &&
        bytes[4 + 4] === 0x49 && bytes[4 + 5] === 0x46) {
        const result = new Uint8Array(bytes);
        result[13] = 1;                        // Einheit: Punkte je Zoll
        result[14] = density >> 8;
        result[15] = density & 0xff;
        result[16] = density >> 8;
        result[17] = density & 0xff;
        return result;
    }

    const segment = new Uint8Array([
        0xff, 0xe0, 0x00, 0x10,                            // APP0, Laenge 16
        0x4a, 0x46, 0x49, 0x46, 0x00,                      // "JFIF\0"
        0x01, 0x02,                                        // Fassung 1.02
        0x01,                                              // Einheit: dpi
        density >> 8, density & 0xff,
        density >> 8, density & 0xff,
        0x00, 0x00,                                        // kein Vorschaubild
    ]);
    const result = new Uint8Array(bytes.length + segment.length);
    result.set(bytes.subarray(0, 2), 0);
    result.set(segment, 2);
    result.set(bytes.subarray(2), 2 + segment.length);
    return result;
}

/**
 * CRC-32 nach PNG-Norm (Anhang D) - dieselbe Tabelle wie in zlib.
 *
 * Ohne sie waere das Bruchstueck ungueltig, und ein strenger Betrachter wiese
 * die ganze Datei zurueck. Die Tabelle entsteht beim ersten Aufruf; ein Export
 * baut sie einmal und nicht je Bild.
 */
let table = null;

function crc32(bytes) {
    if (table === null) {
        table = new Uint32Array(256);
        for (let index = 0; index < 256; index += 1) {
            let value = index;
            for (let bit = 0; bit < 8; bit += 1) {
                value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
            }
            table[index] = value >>> 0;
        }
    }
    let crc = 0xffffffff;
    for (const byte of bytes) {
        crc = table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
    }
    return (crc ^ 0xffffffff) >>> 0;
}
