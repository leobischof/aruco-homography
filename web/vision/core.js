/**
 * core.js - der C++-Rechenkern als WebAssembly, und die einzige Stelle, die
 * seinen Speicher kennt.
 *
 * Emscripten hat keinen Sammler. Was der Kern anlegt, muss von Hand freigegeben
 * werden, und eine Sicht auf den Haldenspeicher gilt nur bis zur naechsten
 * Speicheranforderung (ALLOW_MEMORY_GROWTH tauscht den ArrayBuffer aus). Beide
 * Regeln stehen hier - und NUR hier. Kein anderes Modul unter web/vision/ ruft
 * `_malloc`, `_free` oder `.delete()`; wer das braucht, nimmt `withImage` und
 * `takeRaster`. Ein Leck in einer Schleife ueber mehrere Fotos ist ein
 * abgestuerzter Tab, und der sieht aus wie ein Fehler im Foto.
 *
 * Das `.wasm` wird MITGELIEFERT (web/vendor/core/) und nicht beim Bauen geholt:
 * ein Auslieferungsstand, dessen Rechenkern bei jedem Bau frisch aus dem Netz
 * kommt, ist kein Auslieferungsstand (docs/cpp-migration/README.md, Abschnitt 7).
 */

import createArucoCore from "../vendor/core/aruco_core.mjs";

let corePromise = null;

/**
 * Den Kern laden. Der erste Aufruf holt das wasm, jeder weitere bekommt
 * dieselbe Instanz - eine zweite waere zwei Megabyte und ein zweiter Haufen.
 */
export function loadCore() {
    if (corePromise === null) {
        corePromise = createArucoCore();
    }
    return corePromise;
}

/**
 * Ein Bild in den Haldenspeicher legen, damit arbeiten, wieder freigeben.
 *
 * Der Zeiger geht als Zahl in den Kern; das ist die einzige Stelle im ganzen
 * Baum, an der eine Adresse durch JavaScript wandert. Freigegeben wird im
 * `finally`, damit auch ein geworfener Fehler den Speicher nicht behaelt.
 */
export function withImage(core, image, work) {
    const pointer = core._malloc(image.data.length);
    if (pointer === 0) {
        throw new Error("Kein Speicher fuer das Bild im WebAssembly-Haufen");
    }
    try {
        core.HEAPU8.set(image.data, pointer);
        return work(pointer, image);
    } finally {
        core._free(pointer);
    }
}

/**
 * Ein Ergebnisbild des Kerns uebernehmen: kopieren, dann sofort freigeben.
 *
 * `raster.data()` ist eine SICHT in den Haldenspeicher. Sie ueberlebt weder das
 * `delete()` noch die naechste Speicheranforderung - deshalb wird sie hier
 * kopiert, in derselben Anweisung, ohne etwas dazwischen.
 */
export function takeRaster(raster) {
    try {
        return {
            data: new Uint8Array(raster.data()),
            width: raster.width(),
            height: raster.height(),
            channels: raster.channels(),
        };
    } finally {
        raster.delete();
    }
}

/** Ein Bild aus dem Kern durch eine Rechnung schicken, die ein Raster liefert. */
export function rasterFrom(core, image, work) {
    return withImage(core, image, (pointer) => takeRaster(work(pointer)));
}
