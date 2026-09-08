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
 *    **Fuer das Sucherbild gilt das Gegenteil**, und deshalb hat es eine eigene
 *    Funktion: `decodeFrame`. Es gibt keine URI, weil es keine Datei gibt - das
 *    Bild entsteht in der Seite aus einem `<canvas>`. Dort gehen die Bytes also
 *    wirklich hinueber; bei 960 px und Guete 0,6 sind es rund 60 KB.
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

/**
 * Ein Einzelbild des Suchers uebernehmen - und NICHT das gewaehlte Foto.
 *
 * Der Unterschied zu `decodeFile` ist der ganze Grund fuer diese Funktion. Bis
 * 0.1.5-alpha rief local.js auch fuer den Sucher `decodeFile`; auf diesem Ziel
 * heisst das "gib mir das gewaehlte Foto", und im Sucher ist keines gewaehlt.
 * Java antwortete "Es wurde noch kein Bild gewaehlt.", der Sucher meldete "Kein
 * Marker im Bild.", und auf dem Telefon sah es aus, als taugte die Erkennung
 * nichts. Mit einem gewaehlten Foto waere es schlimmer gewesen: dann haette er
 * dessen Marker gezeigt, egal wohin die Kamera zeigt.
 *
 * Hier gehen die Bytes also wirklich hinueber - rund 60 KB je Bild bei
 * FRAME_MAX_PX = 960 und Guete 0,6 (live.js). Das ist der eine Fall, in dem sich
 * der Weg lohnt, den der Modulkopf fuer das 12-MP-Foto ausschliesst: dort waeren
 * es 48 MB, hier ist es eine Scheibe.
 *
 * Der Griff kommt vom eigenen Platz der Arena (NativeImages.frame): das Foto und
 * die Zwischenraster der Kette bleiben unberuehrt, und es lebt hoechstens ein
 * Sucherbild.
 */
export async function decodeFrame(blob) {
    const native = globalThis.__aruco;
    if (!native) {
        throw new AppError("unreadable_image", "file", { reason: "keine native Bruecke" });
    }
    try {
        const frame = await native.decodeFrame(new Uint8Array(await blob.arrayBuffer()));
        return {
            handle: frame.handle,
            width: frame.width,
            height: frame.height,
            channels: 3,
        };
    } catch (error) {
        throw new AppError("unreadable_image", "file", {
            reason: String((error && error.message) || error),
        });
    }
}

/**
 * Ein Einzelbild wieder hergeben.
 *
 * Ohne das bliebe nach dem Schliessen des Suchers ein Bild in Java liegen. Viel
 * ist es nicht - ein 960er Bild sind 2 MB -, aber es ist auch nicht noetig.
 *
 * Wirft nie: Aufraeumen soll den Fehler nicht verdecken, der es ausgeloest hat.
 * Ein doppeltes oder verspaetetes Hergeben ist auf der Java-Seite ausdruecklich
 * kein Fehler (NativeImages.releaseFrame).
 */
export function releaseFrame(image) {
    const native = globalThis.__aruco;
    if (!native || !Number.isInteger(image && image.handle)) return;
    try {
        native.releaseFrame(image.handle);
    } catch (error) {
        console.error("Einzelbild nicht freigegeben", error);
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
