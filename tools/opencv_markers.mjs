/**
 * opencv_markers.mjs - Modulbits aus opencv.js, fuer den Pruefstand unter Node.
 *
 * `web/pdf/markersheet.js` bekommt die Bits von aussen und weiss nicht, woher.
 * Hier steht die eine Antwort fuer Node: derselbe WASM-Bau, den Stufe 0 geprueft
 * hat (`@techstark/opencv-js`, OpenCV 5.0.0 - dieselbe Hauptversion wie der
 * Desktop). Im Browser gibt die Oberflaeche stattdessen ihr schon geladenes
 * `window.cv` weiter, auf Android die dortige Bindung.
 *
 * Damit geht die Pruefung wirklich durch JavaScript: opencv.js erzeugt die Module,
 * markersheet.js zeichnet sie, und tests/test_markersheet.py rastert das Ergebnis
 * und schickt es durch den ECHTEN Detektor. Ein vertauschtes oder gespiegeltes
 * Modulraster saehe auf dem Bildschirm normal aus und fiele sonst erst am realen
 * Foto auf.
 *
 * Der Bau ist MODULARIZE: der Export ist ein Promise, kein fertiges Modul.
 */

let ready = null;

async function openCv() {
    if (ready === null) {
        ready = import("@techstark/opencv-js").then((module) => module.default ?? module);
    }
    return ready;
}

/**
 * Liefert `markerBits(markerId)` fuer web/pdf/markersheet.js.
 *
 * Der Woerterbuchname kommt aus shared/constants.json und wird auf die
 * OpenCV-Kennung abgebildet - so wie app/config.py es mit `getattr(cv2.aruco, ...)`
 * tut. Die ZAHL steht bewusst nirgends abgeschrieben: sie waere keine
 * sprachneutrale Angabe, sondern eine Wette darauf, dass jede Bindung dieselbe
 * Nummerierung benutzt.
 */
export async function markerBitsFromOpenCv(dictionaryName, modules) {
    const cv = await openCv();
    const dictionaryId = cv[dictionaryName];
    if (dictionaryId === undefined) {
        throw new Error(`opencv.js kennt kein "${dictionaryName}".`);
    }
    const dictionary = cv.getPredefinedDictionary(dictionaryId);

    return (markerId) => {
        const mat = new cv.Mat();
        try {
            cv.generateImageMarker(dictionary, markerId, modules, mat, 1);
            return Uint8Array.from(mat.data);
        } finally {
            mat.delete();
        }
    };
}
