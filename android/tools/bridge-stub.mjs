/**
 * bridge-stub.mjs - die Java-Seite, nachgebaut in JavaScript. NUR zum Pruefen.
 *
 * **Was das ist.** Ein Doppelgaenger von CoreBridge.java und NativeImages.java:
 * dieselben Namen, dieselbe Argumentreihenfolge, dieselbe Antwortform, dieselbe
 * Verwaltung der Bildgriffe. Gerechnet wird dabei im WASM-Bau desselben Kerns
 * statt in der nativen Bibliothek - es ist dieselbe C++-Funktion, nur ein
 * anderes Ziel.
 *
 * **Wozu.** Auf diesem Rechner laeuft kein Android. Ohne diesen Doppelgaenger
 * liesse sich `web/vision/core-android.js` nirgends ausfuehren, und die einzige
 * Datei unter web/vision/, die auf dem Geraet anders ist, waere die einzige, die
 * niemand je laufen sieht. Mit ihm laeuft sie zweimal:
 *
 *   node --test web/vision/core-android.test.mjs   das Umpacken, Wert fuer Wert
 *   ./dev.ps1 check-android-ui                     die ganze Kette im Chromium
 *
 * **Was er NICHT beweist, und das gehoert in jeden Bericht darueber.** Er ist ein
 * NACHBAU. Weicht CoreBridge.java eines Tages von dieser Datei ab - ein
 * vertauschtes Argument, ein anderer Feldname -, bleiben beide Pruefungen gruen
 * und die App scheitert auf dem Geraet. Was dagegen steht: die Java-Seite selbst
 * ist an anderer Stelle gemessen (core/tools/ChainCheck.java schickt dieselben
 * zwanzig Funktionen ueber JNI durch eine echte JVM), und beide Dateien tragen
 * dieselbe Liste in derselben Reihenfolge.
 */

/**
 * Einen Doppelgaenger der Bruecke bauen.
 *
 * @param wasm der geladene WASM-Kern (web/vendor/core/aruco_core.mjs)
 * @returns `{ core, put, image, raster }` - `core` ist das, was
 *     `window.__aruco.core` auf dem Geraet ist.
 */
export function makeBridgeStub(wasm) {
    const images = new Map();
    let nextHandle = 1;

    /** Ein Bild in den Haufen legen und einen Griff darauf vergeben. */
    function put(data, width, height, channels) {
        const pointer = wasm._malloc(data.length);
        wasm.HEAPU8.set(data, pointer);
        const handle = nextHandle++;
        images.set(handle, { pointer, width, height, channels });
        return handle;
    }

    function image(handle) {
        const found = images.get(handle);
        if (!found) throw new Error(`Bild ${handle} gibt es nicht mehr`);
        return found;
    }

    /** Ein Ergebnisraster uebernehmen - dasselbe, was NativeImages.allocate tut. */
    function keep(result) {
        try {
            return put(new Uint8Array(result.data()), result.width(), result.height(),
                       result.channels());
        } finally {
            result.delete();
        }
    }

    /** Der Griff plus die Masse - genau das, was CoreBridge.raster liefert. */
    function raster(handle) {
        const found = image(handle);
        return { handle, width: found.width, height: found.height, channels: found.channels };
    }

    /** Die Zuordnung Name -> Kernfunktion. Spiegelt CoreBridge.call, Zeile fuer Zeile. */
    function dispatch(method, a) {
        switch (method) {
            case "detectMarkers": {
                const source = image(a[0]);
                return wasm.detectMarkers(source.pointer, source.width, source.height,
                    source.width * source.channels, source.channels, a[5])
                    .map((marker) => ({ id: marker.id, corners: Array.from(marker.corners) }));
            }
            case "homographyFromQuad":
                return Array.from(wasm.homographyFromQuad(a[0], a[1]));
            case "homographyLmeds":
                return Array.from(wasm.homographyLmeds(a[0], a[1]));
            case "refineHomography":
                return Array.from(wasm.refineHomography(a[0], a[1], a[2]));
            case "fitFree": {
                const fit = wasm.fitFree(a[0], a[1]);
                return {
                    homography: Array.from(fit.homography),
                    offsets: Array.from(fit.offsets),
                };
            }
            case "poseFromHomography": {
                const pose = wasm.poseFromHomography(a[0], a[1], a[2], a[3]);
                return {
                    heightMm: pose.heightMm,
                    nadirMm: Array.from(pose.nadirMm),
                    tiltDeg: pose.tiltDeg,
                };
            }
            case "planeExtent":
                return Array.from(wasm.planeExtent(a[0], a[1], a[2], a[3]));
            case "convexHull":
                return Array.from(wasm.convexHull(a[0]));
            case "convexIntersectionArea":
                return wasm.convexIntersectionArea(a[0], a[1]);
            case "localPxPerMm":
                return wasm.localPxPerMm(a[0], a[1], a[2]);
            case "quadArea":
                return wasm.quadArea(a[0]);
            case "outputSize": {
                const size = wasm.outputSize(a[0], a[1], a[2], a[3], a[4]);
                return { width: size.width, height: size.height };
            }
            case "rectify": {
                const source = image(a[0]);
                return raster(keep(wasm.rectify(source.pointer, source.width, source.height,
                    source.width * source.channels, source.channels, a[5], a[6], a[7], a[8],
                    a[9], a[10], a[11])));
            }
            case "adjust": {
                const source = image(a[0]);
                return raster(keep(wasm.adjust(source.pointer, source.width, source.height,
                    source.width * source.channels, source.channels, a[5])));
            }
            case "isIdentity":
                return wasm.isIdentity(a[0]);
            case "findContourMm": {
                const source = image(a[0]);
                const polygon = wasm.findContourMm(source.pointer, source.width, source.height,
                    source.width * source.channels, source.channels, a[5]);
                return polygon === null || polygon === undefined ? null : Array.from(polygon);
            }
            case "markerBits":
                return Array.from(wasm.markerBits(a[0], a[1]));
            default:
                throw new Error(`Der Kern kennt "${method}" nicht.`);
        }
    }

    /**
     * Ein Bild wieder hergeben - das Gegenstueck zu NativeImages.releaseFrame.
     *
     * Ein unbekannter Griff ist KEIN Fehler, genau wie dort: doppeltes oder
     * verspaetetes Hergeben soll nicht werfen. Der Puffer wird wirklich
     * freigegeben; ohne _free waechst der WASM-Haufen mit jedem Sucherbild, und
     * genau die Sorte Leck soll dieser Doppelgaenger sichtbar machen.
     */
    function drop(handle) {
        const found = images.get(handle);
        if (!found) return;
        wasm._free(found.pointer);
        images.delete(handle);
    }

    return {
        images,
        put,
        image,
        drop,
        /**
         * Ein Aufruf, wie `window.__aruco.core` ihn macht.
         *
         * Argumente UND Antwort gehen durch JSON - genau die Strecke, die auf dem
         * Geraet zwischen der Seite und Java liegt. Ohne das bliebe der haeufigste
         * Fehler unentdeckt: ein `Float64Array` ist fuer JSON.stringify kein Feld,
         * sondern ein Objekt mit Zifferschluesseln.
         */
        core(method, args) {
            const crossed = JSON.parse(JSON.stringify(args));
            return JSON.parse(JSON.stringify(dispatch(method, crossed)));
        },
    };
}
