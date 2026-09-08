/**
 * exif.js - Brennweite und Kameramodell aus den ORIGINALBYTES einer Datei.
 *
 * Warum es diese Datei ueberhaupt gibt: **EXIF ueberlebt den Canvas nicht.**
 * Sobald ein Bild gezeichnet ist, sind nur noch Pixel da; Brennweite,
 * Kameramodell und Bildlage sind weg (docs/cpp-migration/stage-0-opencv-js.md,
 * Abschnitt 6a). Am Desktop liest PIL sie aus der Datei, bevor irgendetwas
 * dekodiert wird - im Browser muss das hier geschehen, an denselben Bytes.
 *
 * Gebraucht wird davon genau so viel, wie app/vision/detect.py::_read_exif
 * liest: `FocalLengthIn35mmFilm` und `Model`. Alles andere waere ein
 * EXIF-Leser, und den braucht niemand.
 *
 * Die Bildlage (`Orientation`) steht bewusst NICHT hier: die wendet der Browser
 * beim Dekodieren selbst an (`imageOrientation: "from-image"`, web/vision/image.js),
 * genau wie PIL es mit `ImageOps.exif_transpose` tut. Zweimal drehen waere
 * schlimmer als gar nicht.
 *
 * Faellt hier etwas aus - kein EXIF, ein Format ohne APP1, ein abgeschnittener
 * Block -, kommt `{ focal35Mm: null, cameraModel: null }` zurueck und der
 * Bediener tippt den Kameraabstand ein. Genau dafuer hat app/vision/camera.py
 * seinen Weg B; ein Abbruch waere hier die falsche Antwort.
 */

const TAG_MODEL = 0x0110;
const TAG_EXIF_IFD = 0x8769;
const TAG_FOCAL_35MM = 0xa405;

// Typkennungen des TIFF-Verzeichnisses. Gebraucht werden ASCII (Modell) sowie
// SHORT und LONG (Brennweite); RATIONAL steht dabei, weil manche Kameras die
// Brennweite so ablegen.
const TYPE_SIZES = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8 };

/** Brennweite (35-mm-Aequivalent) und Kameramodell, beides moeglicherweise null. */
export function readExif(bytes) {
    try {
        const tiff = findTiffHeader(bytes);
        if (tiff === null) return empty();
        return readTiff(new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength), tiff);
    } catch (error) {
        // Ein defekter EXIF-Block ist kein Fehlerfall - dieselbe Haltung wie in
        // app/vision/detect.py::_read_exif, das jede Ausnahme schluckt.
        return empty();
    }
}

function empty() {
    return { focal35Mm: null, cameraModel: null };
}

/**
 * Anfang des TIFF-Blocks suchen (Byte-Versatz), sonst null.
 *
 * Nur JPEG: dort steht EXIF im APP1-Segment. HEIC und AVIF legen es in einer
 * ISO-BMFF-Box ab, und die zu durchwandern waere ein zweiter Parser fuer einen
 * Fall, den Chrome auf Windows ohnehin nicht dekodieren kann.
 */
function findTiffHeader(bytes) {
    if (bytes.length < 4 || bytes[0] !== 0xff || bytes[1] !== 0xd8) return null;

    let offset = 2;
    while (offset + 4 <= bytes.length) {
        if (bytes[offset] !== 0xff) return null;
        const marker = bytes[offset + 1];
        // SOS (0xDA) heisst: ab hier kommen Bilddaten, keine Segmente mehr.
        if (marker === 0xda || marker === 0xd9) return null;
        const length = (bytes[offset + 2] << 8) | bytes[offset + 3];
        if (length < 2) return null;

        if (marker === 0xe1 && offset + 10 <= bytes.length) {
            const header = String.fromCharCode(...bytes.subarray(offset + 4, offset + 8));
            if (header === "Exif") return offset + 10;  // "Exif\0\0" ist sechs Bytes
        }
        offset += 2 + length;
    }
    return null;
}

function readTiff(view, tiff) {
    const byteOrder = view.getUint16(tiff, false);
    if (byteOrder !== 0x4949 && byteOrder !== 0x4d4d) return empty();
    const little = byteOrder === 0x4949;
    if (view.getUint16(tiff + 2, little) !== 42) return empty();

    const ifd0 = tiff + view.getUint32(tiff + 4, little);
    const entries = readDirectory(view, tiff, ifd0, little);

    let focal35 = numberOf(entries.get(TAG_FOCAL_35MM));
    const model = stringOf(entries.get(TAG_MODEL));

    // FocalLengthIn35mmFilm steht normalerweise in der Exif-Sub-IFD, nicht in
    // IFD0 - beide werden abgefragt, weil manche Kameras und Apps die Tags anders
    // einsortieren. Dieselbe Reihenfolge wie in app/vision/detect.py.
    if (focal35 === null) {
        const pointer = numberOf(entries.get(TAG_EXIF_IFD));
        if (pointer !== null) {
            const sub = readDirectory(view, tiff, tiff + pointer, little);
            focal35 = numberOf(sub.get(TAG_FOCAL_35MM));
        }
    }

    return {
        focal35Mm: focal35 !== null && focal35 > 0.0 ? focal35 : null,
        cameraModel: model,
    };
}

/** Ein IFD lesen: Tag -> { type, count, valueOffset }. */
function readDirectory(view, tiff, directory, little) {
    const entries = new Map();
    if (directory + 2 > view.byteLength) return entries;

    const count = view.getUint16(directory, little);
    for (let index = 0; index < count; index += 1) {
        const entry = directory + 2 + index * 12;
        if (entry + 12 > view.byteLength) break;

        const tag = view.getUint16(entry, little);
        const type = view.getUint16(entry + 2, little);
        const length = view.getUint32(entry + 4, little);
        const size = (TYPE_SIZES[type] || 0) * length;
        // Bis zu vier Bytes stehen im Eintrag selbst, laengere Werte anderswo.
        const offset = size <= 4 ? entry + 8 : tiff + view.getUint32(entry + 8, little);
        entries.set(tag, { view, type, length, offset, little });
    }
    return entries;
}

function numberOf(entry) {
    if (!entry) return null;
    const { view, type, offset, little } = entry;
    if (offset + (TYPE_SIZES[type] || 0) > view.byteLength) return null;
    if (type === 3) return view.getUint16(offset, little);
    if (type === 4) return view.getUint32(offset, little);
    if (type === 5) {
        const denominator = view.getUint32(offset + 4, little);
        return denominator === 0 ? null : view.getUint32(offset, little) / denominator;
    }
    return null;
}

function stringOf(entry) {
    if (!entry || entry.type !== 2) return null;
    const { view, length, offset } = entry;
    if (offset + length > view.byteLength) return null;

    let text = "";
    for (let index = 0; index < length; index += 1) {
        const code = view.getUint8(offset + index);
        if (code === 0) break;
        text += String.fromCharCode(code);
    }
    text = text.trim();
    return text.length > 0 ? text : null;
}
