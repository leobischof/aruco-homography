/**
 * core-android.js - derselbe Rechenkern wie core.js, aber als native Bibliothek
 * hinter der JNI-Bruecke statt als WebAssembly.
 *
 * **Die zweite Fassung GENAU DIESER Datei - und keiner anderen.** core.js ist die
 * einzige Stelle im ganzen Baum, die weiss, wo der Kern wohnt und wem sein
 * Speicher gehoert; alles darueber (solve.js, rectify.js, extent.js, contour.js,
 * camera.js, enhance.js, pipeline.js, local.js) laeuft auf Android unveraendert
 * weiter. Eine zweite Fassung der Millimeter ist genau das, wogegen der ganze
 * Umzug nach C++ laeuft (docs/cpp-migration/README.md, Abschnitt 4).
 *
 * Ausgetauscht wird sie ueber die Importkarte in
 * android/app/src/main/assets/www/native/bridge-shim.js. Fehlt die Karte, laedt
 * die Seite das echte core.js, findet das `.wasm` nicht - das liegt absichtlich
 * nicht im APK - und bricht mit einer Ladefehlermeldung ab. Ein lautes
 * Scheitern; die stille Alternative waere ein zweiter Rechenkern im Gepaeck.
 *
 * DREI UNTERSCHIEDE ZU core.js, und jeder hat denselben Grund: die Pixel liegen
 * nicht im selben Speicher wie das JavaScript.
 *
 * 1. **Ein Bild ist eine ZAHL.** Wo core.js einen Zeiger in den WASM-Haufen
 *    reicht, reicht diese Datei einen Griff auf ein Bild in der Java-Seite
 *    (NativeImages.java). Ein entzerrtes Raster sind bei 300 dpi zweistellige
 *    Megabyte, und die JavaScript-Grenze traegt nur Text.
 *
 * 2. **Freigegeben wird nicht hier.** core.js muss `delete()` rufen, weil
 *    Emscripten keinen Sammler hat. Hier haelt die Java-Seite eine ARENA fester
 *    Groesse: kommt ein Raster dazu, faellt das aelteste weg. Das ist die
 *    Antwort auf dieselbe Frage mit anderen Mitteln - `pipeline.js` gibt nichts
 *    frei und soll es auch nicht muessen, weil es dieselbe Datei ist, die im
 *    Browser laeuft.
 *
 * 3. **Zahlen gehen als JSON.** Beide Seiten schreiben Fliesskommazahlen in der
 *    kuerzesten Darstellung, die exakt zurueckliest (`JSON.stringify` hier,
 *    `Double.toString` dort), also ueberlebt jedes Bit den Weg. Durch diese
 *    Grenze gehen Homographien, Punktlisten und Konturen - nie ein Bild.
 *
 * Ein `Float64Array` ist fuer `JSON.stringify` KEIN Feld, sondern ein Objekt mit
 * Zifferschluesseln. Jede Punktliste geht deshalb durch `flat()` - ohne das
 * kaeme auf der Java-Seite `{"0":1,"1":2}` an, und `getJSONArray` scheiterte an
 * einer Stelle, an der niemand ein Zahlenproblem vermutet.
 */

import { AppError } from "./notices.js";

/**
 * Die Bruecke. Sie steht seit bridge-shim.js, also vor jedem Seitenskript.
 *
 * Der Abbruch traegt einen CODE und keinen Satz: der Text kommt aus
 * app/static/i18n/ (Invariante 7), und `errors.android_bridge_failed` gibt es
 * dort in beiden Sprachen.
 */
function bridge() {
    const found = globalThis.__aruco;
    if (!found || typeof found.core !== "function") {
        throw new AppError("android_bridge_failed", null, {
            reason: "window.__aruco fehlt - core-android.js laeuft nur in der App",
        });
    }
    return found;
}

/** Ein Aufruf in den nativen Kern. Synchron, wie das WebAssembly im Browser. */
function call(method, args) {
    return bridge().core(method, args);
}

/** Typenfeld -> gewoehnliches Feld, damit JSON.stringify es als Feld schreibt. */
function flat(values) {
    return Array.isArray(values) ? values : Array.from(values);
}

/** Antwort -> Float64Array, die Form, die core.js liefert und solve.js erwartet. */
function numbers(values) {
    return Float64Array.from(values);
}

const core = {
    detectMarkers(handle, width, height, stride, channels, enhanceContrast) {
        const found = call("detectMarkers", [
            handle, width, height, stride, channels, enhanceContrast,
        ]);
        return found.map((marker) => ({ id: marker.id, corners: numbers(marker.corners) }));
    },

    homographyFromQuad(plane, image) {
        return numbers(call("homographyFromQuad", [flat(plane), flat(image)]));
    },

    homographyLmeds(plane, image) {
        return numbers(call("homographyLmeds", [flat(plane), flat(image)]));
    },

    refineHomography(start, plane, image) {
        return numbers(call("refineHomography", [flat(start), flat(plane), flat(image)]));
    },

    fitFree(quads, markerMm) {
        const fit = call("fitFree", [flat(quads), markerMm]);
        return { homography: numbers(fit.homography), offsets: numbers(fit.offsets) };
    },

    fitScattered(quads, markerMm) {
        const fit = call("fitScattered", [flat(quads), markerMm]);
        return { homography: numbers(fit.homography), poses: numbers(fit.poses) };
    },

    poseFromHomography(homography, focalPx, width, height) {
        const pose = call("poseFromHomography", [flat(homography), focalPx, width, height]);
        return { heightMm: pose.heightMm, nadirMm: numbers(pose.nadirMm), tiltDeg: pose.tiltDeg };
    },

    planeExtent(homography, width, height, hull) {
        return numbers(call("planeExtent", [flat(homography), width, height, flat(hull)]));
    },

    convexHull(points) {
        return numbers(call("convexHull", [flat(points)]));
    },

    convexIntersectionArea(first, second) {
        return call("convexIntersectionArea", [flat(first), flat(second)]);
    },

    localPxPerMm(homography, x, y) {
        return call("localPxPerMm", [flat(homography), x, y]);
    },

    quadArea(quad) {
        return call("quadArea", [flat(quad)]);
    },

    outputSize(x0, y0, x1, y1, pxPerMm) {
        return call("outputSize", [x0, y0, x1, y1, pxPerMm]);
    },

    rectify(handle, width, height, stride, channels, homography, x0, y0, x1, y1, pxPerMm,
            sourcePxPerMm) {
        return call("rectify", [
            handle, width, height, stride, channels, flat(homography),
            x0, y0, x1, y1, pxPerMm, sourcePxPerMm,
        ]);
    },

    adjust(handle, width, height, stride, channels, options) {
        return call("adjust", [handle, width, height, stride, channels, options]);
    },

    isIdentity(options) {
        return call("isIdentity", [options]);
    },

    findContourMm(handle, width, height, stride, channels, pxPerMm) {
        const polygon = call("findContourMm", [handle, width, height, stride, channels, pxPerMm]);
        return polygon === null ? null : numbers(polygon);
    },

    markerBits(markerId, modules) {
        return Uint8Array.from(call("markerBits", [markerId, modules]));
    },
};

/**
 * Den Kern laden. Hier ist nichts zu laden - die Bibliothek haengt seit
 * `System.loadLibrary` im Prozess -, aber die Form bleibt dieselbe wie in
 * core.js, damit local.js nicht zwei Faelle kennen muss.
 */
export function loadCore() {
    return Promise.resolve(core);
}

/**
 * Ein Bild in eine Rechnung geben.
 *
 * Im Browser legt diese Funktion das Bild in den WASM-Haufen und raeumt danach
 * auf. Hier liegt es schon auf der richtigen Seite: `image.handle` benennt es,
 * und es gibt nichts zu kopieren und nichts freizugeben.
 */
export function withImage(module, image, work) {
    if (!Number.isInteger(image && image.handle)) {
        throw new AppError("android_bridge_failed", null, {
            reason: "Bild ohne handle - es liegt nicht im nativen Speicher",
        });
    }
    return work(image.handle);
}

/**
 * Ein Ergebnisbild uebernehmen.
 *
 * Im Browser kopiert diese Funktion die Haldensicht und loescht das Original,
 * weil beides sonst verlorenginge. Hier ist das Ergebnis bereits ein Griff auf
 * ein Bild, das die Java-Seite haelt - uebernommen wird also nichts, es wird nur
 * weitergereicht. Freigegeben wird es, wenn die Arena Platz braucht
 * (NativeImages.java).
 */
export function takeRaster(raster) {
    return raster;
}

/** Ein Bild durch eine Rechnung schicken, die ein Raster liefert. */
export function rasterFrom(module, image, work) {
    return withImage(module, image, (handle) => takeRaster(work(handle)));
}
