/**
 * image-android.js - die Grenze zwischen Bild und Rechenkern, Android-Fassung.
 *
 * Das Gegenstueck zu image.js, und aus demselben Grund eine eigene Datei wie
 * core-android.js: hier steht, wo die Pixel liegen, und nur hier. Ausgetauscht
 * wird sie ueber dieselbe Importkarte (bridge-shim.js); alles darueber -
 * pipeline.js, preview.js, local.js - bleibt Wort fuer Wort das, was auch im
 * Browser laeuft.
 *
 * DREI UNTERSCHIEDE, und alle drei folgen daraus, dass die Pixel in Java liegen:
 *
 * 1. **Dekodiert wird nicht hier.** `BitmapFactory` hat das Foto schon gelesen,
 *    die EXIF-Drehung schon angewandt und das Ergebnis als BGR abgelegt
 *    (Photo.java). `decodeFile` holt also nur den Griff darauf. Das Datei-Objekt
 *    aus dem `<input type="file">` wird dabei NICHT gelesen: Android kennt die
 *    URI seit `onShowFileChooser`, und ein 12-MP-Foto ein zweites Mal durch die
 *    JavaScript-Grenze zu ziehen waeren 48 MB ohne Gegenwert.
 *
 * 2. **Kodiert wird in Java** (`Bitmap.compress`, Rasters.java). Der Kern fasst
 *    `imgcodecs` nicht an - das gilt auf jedem Ziel, im Browser macht es die
 *    Leinwand.
 *
 * 3. **Die JPEG-Bytes kommen als GET und nicht als Base64.** `/api/raster/...`
 *    bedient der WebViewAssetLoader, also kommt ein Binaerstrom in die Seite.
 *    Base64 waere ein Drittel mehr, als Text, bei jedem Reglerzug - der
 *    Unterschied zwischen einer fluessigen Vorschau und einer unbenutzbaren.
 *
 * Eine Leinwand kommt hier nirgends vor. Sie waere die zweite Stelle, an der
 * Pixel entstehen, und die Frage, welcher der beiden man glaubt, will niemand
 * beantworten muessen.
 */

import { JPEG_QUALITY } from "../constants.js";
import { AppError } from "./notices.js";

/**
 * Das gewaehlte Foto uebernehmen.
 *
 * `file` wird bewusst nicht angefasst - siehe oben. Zurueck kommt kein
 * Pixelfeld, sondern der Griff darauf; `withImage` in core-android.js weiss
 * damit umzugehen, und niemand sonst fasst `image.data` an.
 */
export async function decodeFile(file) {
    const native = globalThis.__aruco;
    if (!native) {
        throw new AppError("unreadable_image", "file", { reason: "keine native Bruecke" });
    }
    try {
        const photo = await native.loadPickedPhoto();
        return {
            handle: native.photoHandle(),
            width: photo.width,
            height: photo.height,
            channels: 3,
        };
    } catch (error) {
        throw new AppError("unreadable_image", "file", {
            reason: String((error && error.message) || error),
        });
    }
}

/** Ein Raster als JPEG-Bytes - das, was web/pdf/ zum Einbetten braucht. */
export async function toJpegBytes(raster, quality = JPEG_QUALITY / 100.0) {
    const response = await fetch(rasterUrl(raster, quality, "jpg"));
    if (!response.ok) throw new AppError("preview_missing");
    return new Uint8Array(await response.arrayBuffer());
}

/** Dasselbe als Blob - fuer die Vorschaubilder der Oberflaeche. */
export async function toJpegBlob(raster, quality = JPEG_QUALITY / 100.0) {
    const response = await fetch(rasterUrl(raster, quality, "jpg"));
    if (!response.ok) throw new AppError("preview_missing");
    return response.blob();
}

/**
 * Ein Raster als PNG-Bytes - verlustfrei, fuer den Bildexport.
 *
 * Die Guete steht auch hier im Pfad, obwohl PNG keine hat: der Pfad hat ein
 * festes Muster, und ein zweites einzufuehren waere eine zweite Stelle, an der
 * sich Java und JavaScript ueber die Form einigen muessten. Die Java-Seite
 * ignoriert die Zahl fuer PNG.
 */
export async function toPngBytes(raster) {
    const response = await fetch(rasterUrl(raster, 1.0, "png"));
    if (!response.ok) throw new AppError("preview_missing");
    return new Uint8Array(await response.arrayBuffer());
}

/**
 * Die Adresse eines Rasters.
 *
 * Die Guete steht IM PFAD und nicht als Abfrageparameter: `PathHandler.handle`
 * bekommt nur den Pfad, die Parameter wirft die WebView vorher weg. Wer das
 * uebersieht, kodiert stillschweigend immer mit derselben Guete.
 */
function rasterUrl(raster, quality, extension) {
    if (!Number.isInteger(raster && raster.handle)) {
        throw new AppError("preview_missing");
    }
    const percent = Math.min(100, Math.max(1, Math.round(quality * 100)));
    return `/api/raster/${raster.handle}/${percent}.${extension}`;
}
