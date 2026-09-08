/**
 * image.js - die Grenze zwischen Browserbild und Rechenkern.
 *
 * **Dekodieren ist Sache des Browsers, nicht des Kerns.** Der WASM-Bau von
 * OpenCV hat kein `imgcodecs` - kein imread, kein imdecode, kein imencode
 * (docs/cpp-migration/stage-0-opencv-js.md, Abschnitt 5). Der Kern nimmt rohe
 * Pixel und gibt rohe Pixel; hier stehen die beiden Uebersetzungen dorthin und
 * zurueck, und sonst nirgends.
 *
 * Dass der Umweg ueber die Leinwand die Messung nicht anfasst, ist gemessen und
 * nicht gehofft: Stufe 0 hat die Markerecken vor und nach einem
 * Leinwand-Rundlauf verglichen und **0,000 px** Unterschied gefunden.
 *
 * BGR und nicht RGB: der Kern erwartet die Kanalreihenfolge von OpenCV, und die
 * ist dieselbe, die das numpy-Array auf der Python-Seite traegt. Ein vertauschtes
 * B und R saehe auf dem Bildschirm falsch aus - in der Erkennung dagegen fast
 * richtig, weil sie ohnehin nach Grau wandelt. Genau die Sorte Fehler, die spaet
 * auffaellt.
 */

import { JPEG_QUALITY } from "../constants.js";
import { AppError } from "./notices.js";

// Chrome verweigert Leinwaende ueber rund 268 Megapixel und ueber 65535 Pixel
// Kantenlaenge; darueber liefert getImageData nichts und toBlob null. Die Grenze
// gehoert dem BROWSER und nicht dem Produkt - deshalb steht sie hier und nicht in
// shared/constants.json, wo MAX_OUTPUT_MPX fuer alle Ziele gleich gilt.
const CANVAS_MAX_MPX = 268.0;
const CANVAS_MAX_SIDE = 65535;

/**
 * Eine Bilddatei in einen BGR-Puffer verwandeln, EXIF-Drehung angewandt.
 *
 * `imageOrientation: "from-image"` ist das Gegenstueck zu PILs
 * `ImageOps.exif_transpose`: ohne es suchte der Detektor in einem gedrehten Bild
 * und alle Koordinaten waeren falsch (app/vision/detect.py, Modulkopf).
 */
export async function decodeFile(file) {
    let bitmap;
    try {
        bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    } catch (error) {
        throw new AppError("unreadable_image", "file", { reason: String(error && error.message) });
    }

    try {
        const canvas = makeCanvas(bitmap.width, bitmap.height);
        const context = canvas.getContext("2d", { willReadFrequently: true });
        context.drawImage(bitmap, 0, 0);
        const rgba = context.getImageData(0, 0, bitmap.width, bitmap.height).data;
        return { data: rgbaToBgr(rgba), width: bitmap.width, height: bitmap.height, channels: 3 };
    } finally {
        // Ein ImageBitmap haelt einen eigenen Puffer ausserhalb des Haufens. Wer
        // ihn nicht schliesst, sammelt in einer Sitzung mit mehreren Fotos
        // hunderte Megabyte an, die kein Sammler anfasst.
        bitmap.close();
    }
}

/** Ein BGR-Raster als JPEG-Bytes - das, was web/pdf/ erwartet. */
export async function toJpegBytes(raster, quality = JPEG_QUALITY / 100.0) {
    const blob = await toJpegBlob(raster, quality);
    return new Uint8Array(await blob.arrayBuffer());
}

/** Ein BGR-Raster als JPEG-Blob. */
export async function toJpegBlob(raster, quality = JPEG_QUALITY / 100.0) {
    const canvas = makeCanvas(raster.width, raster.height);
    const context = canvas.getContext("2d");
    context.putImageData(new ImageData(bgrToRgba(raster), raster.width, raster.height), 0, 0);

    if (typeof canvas.convertToBlob === "function") {
        return canvas.convertToBlob({ type: "image/jpeg", quality });
    }
    return new Promise((resolve, reject) => {
        canvas.toBlob(
            (blob) => (blob ? resolve(blob) : reject(new AppError("preview_missing"))),
            "image/jpeg",
            quality,
        );
    });
}

/** Eine Leinwand der gewuenschten Groesse - oder ein lesbarer Abbruch. */
function makeCanvas(width, height) {
    const megapixels = (width * height) / 1e6;
    if (width > CANVAS_MAX_SIDE || height > CANVAS_MAX_SIDE || megapixels > CANVAS_MAX_MPX) {
        throw new AppError("canvas_too_large", "dpi", {
            width_px: width,
            height_px: height,
            megapixels: megapixels.toFixed(0),
            limit_mpx: CANVAS_MAX_MPX.toFixed(0),
        });
    }
    if (typeof OffscreenCanvas === "function") {
        return new OffscreenCanvas(width, height);
    }
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    return canvas;
}

function rgbaToBgr(rgba) {
    const pixels = rgba.length / 4;
    const bgr = new Uint8Array(pixels * 3);
    for (let index = 0; index < pixels; index += 1) {
        bgr[index * 3] = rgba[index * 4 + 2];
        bgr[index * 3 + 1] = rgba[index * 4 + 1];
        bgr[index * 3 + 2] = rgba[index * 4];
    }
    return bgr;
}

function bgrToRgba(raster) {
    const pixels = raster.width * raster.height;
    const rgba = new Uint8ClampedArray(pixels * 4);
    const source = raster.data;
    for (let index = 0; index < pixels; index += 1) {
        rgba[index * 4] = source[index * 3 + 2];
        rgba[index * 4 + 1] = source[index * 3 + 1];
        rgba[index * 4 + 2] = source[index * 3];
        rgba[index * 4 + 3] = 255;
    }
    return rgba;
}
