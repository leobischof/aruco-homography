/**
 * core-android.test.mjs - das Umpacken in core-android.js, gemessen statt behauptet.
 *
 * **Die Frage.** core-android.js ist die einzige Datei unter web/vision/, die auf
 * Android anders ist als im Browser. Sie rechnet nichts; sie schreibt Argumente
 * nach JSON, holt das Ergebnis zurueck und formt es in genau die Gestalt, die
 * core.js liefert. Wenn dabei ein Feld verlorengeht, ein Paar vertauscht wird
 * oder ein `Float64Array` als Objekt statt als Feld verschickt wird, misst die
 * App falsch - und zwar plausibel falsch.
 *
 * **Wogegen gemessen wird.** Gegen denselben Kern, geradewegs aufgerufen: der
 * WASM-Bau aus web/vendor/core/. Beide Wege gehen durch dieselbe C++-Funktion,
 * also muessen sie BITGENAU dasselbe liefern. Die Toleranz ist null, und jede
 * Abweichung ist ein Umpackfehler.
 *
 * **Was diese Datei NICHT prueft, und das gehoert dazu.** Die Java-Seite. Der
 * Stummel unten ist ein NACHBAU von CoreBridge.java in JavaScript - er
 * uebersetzt dieselben Namen, erwartet die Argumente in derselben Reihenfolge
 * und antwortet in derselben Form. Weichen die beiden eines Tages voneinander
 * ab, bleibt dieser Test gruen und die App scheitert auf dem Geraet. Was den
 * Nachbau rechtfertigt: er faehrt die echte JSON-Grenze (jedes Argument geht
 * durch JSON.stringify und JSON.parse) und die echte Griff-Verwaltung, und
 * genau dort sitzen die Fehler, die man sonst erst auf einem Telefon faende.
 * Die Java-Seite selbst ist an anderer Stelle gemessen: core/tools/ChainCheck.java
 * schickt dieselben zwanzig Funktionen ueber JNI durch eine echte JVM.
 *
 *   node --test web/vision/core-android.test.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { makeBridgeStub } from "../../android/tools/bridge-stub.mjs";
import createArucoCore from "../vendor/core/aruco_core.mjs";

const wasm = await createArucoCore();

// --- Der Nachbau von CoreBridge.java ---------------------------------------
// Er steht in android/tools/bridge-stub.mjs und nicht hier: dieselbe Datei
// bedient auch ./dev.ps1 check-android-ui, das die ganze Kette im Chromium
// fahren laesst. Zwei Nachbauten derselben Java-Klasse waeren zwei Stellen, an
// denen sie von ihr wegdriften kann.

const stub = makeBridgeStub(wasm);
const { put, image } = stub;

// Die Bruecke, wie bridge-shim.js sie hinstellt.
globalThis.__aruco = { core: stub.core };

const { loadCore, takeRaster, withImage } = await import("./core-android.js");
const android = await loadCore();

// --- Die Szene -------------------------------------------------------------
// Dieselbe Grundwahrheit wie ueberall: shared/fixtures/expected/flat.json. Die
// Ecken kommen aus der Datei und nicht aus einer Erkennung - der Detektor ist
// hier nicht die Frage, das Umpacken ist es.

const fixtures = fileURLToPath(new URL("../../shared/fixtures/", import.meta.url));
const truth = JSON.parse(readFileSync(`${fixtures}expected/flat.json`, "utf8"));
const markerMm = truth.marker_mm;

const ids = Object.keys(truth.marker_corners_px).map(Number).sort((a, b) => a - b);
const imagePoints = Float64Array.from(ids.flatMap((id) => truth.marker_corners_px[id].flat()));
const planePoints = Float64Array.from(ids.flatMap((id) => {
    const [cx, cy] = truth.marker_centers_mm[id];
    const half = markerMm / 2.0;
    return [cx - half, cy - half, cx + half, cy - half,
            cx + half, cy + half, cx - half, cy + half];
}));

/** Ein kleines, aber echtes BGR-Bild - fuer die Wege, die Pixel brauchen. */
function scene(width, height) {
    const data = new Uint8Array(width * height * 3).fill(230);
    for (let y = height / 4; y < (height * 3) / 4; y += 1) {
        for (let x = width / 4; x < (width * 3) / 4; x += 1) {
            const base = (y * width + x) * 3;
            data[base] = 20;
            data[base + 1] = 30;
            data[base + 2] = 40;
        }
    }
    return { data, width, height, channels: 3 };
}

const SLIDERS = {
    grayscale: false,
    invert: false,
    brightness: 0.1,
    contrast: 0.2,
    saturation: -0.1,
    localContrast: 0.3,
    edgeBoost: 0.2,
    edgeOverlay: 0.15,
    colorEmphasis: "red",
    emphasisStrength: 0.4,
    threshold: 0.0,
};

/** Beide Wege muessen Wert fuer Wert dasselbe liefern. Keine Toleranz. */
function same(actual, expected, what) {
    const left = Array.from(actual);
    const right = Array.from(expected);
    assert.equal(left.length, right.length, `${what}: ${left.length} statt ${right.length} Werte`);
    for (let index = 0; index < left.length; index += 1) {
        assert.ok(Object.is(left[index], right[index]),
            `${what}[${index}]: ${left[index]} != ${right[index]}`);
    }
}

// --- Die Pruefungen ---------------------------------------------------------

test("Homographie, Ausgleich und Frei-Modus kommen unveraendert zurueck", () => {
    same(android.homographyFromQuad(planePoints.slice(0, 8), imagePoints.slice(0, 8)),
        wasm.homographyFromQuad(planePoints.slice(0, 8), imagePoints.slice(0, 8)),
        "homographyFromQuad");

    const lmeds = wasm.homographyLmeds(planePoints, imagePoints);
    same(android.homographyLmeds(planePoints, imagePoints), lmeds, "homographyLmeds");
    same(android.refineHomography(lmeds, planePoints, imagePoints),
        wasm.refineHomography(lmeds, planePoints, imagePoints), "refineHomography");

    const expected = wasm.fitFree(imagePoints, markerMm);
    const actual = android.fitFree(imagePoints, markerMm);
    same(actual.homography, expected.homography, "fitFree.homography");
    same(actual.offsets, expected.offsets, "fitFree.offsets");
});

test("Kamerapose, Ausdehnung und Geometrie kommen unveraendert zurueck", () => {
    const homography = wasm.refineHomography(
        wasm.homographyLmeds(planePoints, imagePoints), planePoints, imagePoints);
    const [width, height] = truth.image_size_px;
    const focalPx = truth.camera.focal_px;

    const expectedPose = wasm.poseFromHomography(homography, focalPx, width, height);
    const pose = android.poseFromHomography(homography, focalPx, width, height);
    assert.ok(Object.is(pose.heightMm, expectedPose.heightMm), "pose.heightMm");
    assert.ok(Object.is(pose.tiltDeg, expectedPose.tiltDeg), "pose.tiltDeg");
    same(pose.nadirMm, expectedPose.nadirMm, "pose.nadirMm");

    const hull = wasm.convexHull(planePoints);
    same(android.convexHull(planePoints), hull, "convexHull");
    same(android.planeExtent(homography, width, height, hull),
        wasm.planeExtent(homography, width, height, hull), "planeExtent");

    assert.ok(Object.is(android.localPxPerMm(homography, 105.0, 148.5),
        wasm.localPxPerMm(homography, 105.0, 148.5)), "localPxPerMm");
    assert.ok(Object.is(android.quadArea(imagePoints.slice(0, 8)),
        wasm.quadArea(imagePoints.slice(0, 8))), "quadArea");

    const rectangle = Float64Array.from([0, 0, 210, 0, 210, 297, 0, 297]);
    assert.ok(Object.is(android.convexIntersectionArea(rectangle, hull),
        wasm.convexIntersectionArea(rectangle, hull)), "convexIntersectionArea");
});

test("Rastergroesse, Entzerren, Aufbereiten und Umriss - Pixel fuer Pixel", () => {
    const source = scene(320, 240);
    const size = android.outputSize(0.0, 0.0, 160.0, 120.0, 2.0);
    assert.deepEqual(size, wasm.outputSize(0.0, 0.0, 160.0, 120.0, 2.0), "outputSize");

    // Der Zuschnitt umfasst die ganze Szene. Das ist Absicht: laege das dunkle
    // Rechteck am Rand des entzerrten Bildes, faende RETR_EXTERNAL keinen
    // geschlossenen Aussenzug, und der Umriss unten pruefte dann nur noch, dass
    // "nichts gefunden" durch die Grenze kommt.

    // Eine Abbildung, die 1 mm auf 2 px legt - mehr braucht es nicht, um zu
    // pruefen, ob dieselben Bytes herauskommen.
    const homography = Float64Array.from([2, 0, 0, 0, 2, 0, 0, 0, 1]);
    const handle = put(source.data, source.width, source.height, source.channels);
    const androidImage = { handle, width: source.width, height: source.height, channels: 3 };

    const rectified = withImage(android, androidImage, (h) =>
        takeRaster(android.rectify(h, source.width, source.height, source.width * 3, 3,
            homography, 0.0, 0.0, 160.0, 120.0, 2.0, 0.0)));
    const expectedRaster = (() => {
        const pointer = wasm._malloc(source.data.length);
        wasm.HEAPU8.set(source.data, pointer);
        try {
            const result = wasm.rectify(pointer, source.width, source.height, source.width * 3, 3,
                homography, 0.0, 0.0, 160.0, 120.0, 2.0, 0.0);
            try {
                return { data: new Uint8Array(result.data()), width: result.width(),
                         height: result.height(), channels: result.channels() };
            } finally {
                result.delete();
            }
        } finally {
            wasm._free(pointer);
        }
    })();

    assert.equal(rectified.width, expectedRaster.width, "rectify.width");
    assert.equal(rectified.height, expectedRaster.height, "rectify.height");
    same(new Uint8Array(wasm.HEAPU8.buffer, image(rectified.handle).pointer,
        expectedRaster.data.length), expectedRaster.data, "rectify (Pixel)");

    assert.equal(android.isIdentity(SLIDERS), wasm.isIdentity(SLIDERS), "isIdentity (Regler)");
    assert.equal(android.isIdentity({}), wasm.isIdentity({}), "isIdentity (neutral)");

    // Und die Aufbereitung: gleiche Groesse (Invariante 6) und dieselben Bytes.
    const adjusted = withImage(android, rectified, (h) =>
        takeRaster(android.adjust(h, rectified.width, rectified.height, rectified.width * 3, 3,
            SLIDERS)));
    assert.equal(adjusted.width, rectified.width, "adjust behaelt die Breite (Invariante 6)");
    assert.equal(adjusted.height, rectified.height, "adjust behaelt die Hoehe (Invariante 6)");

    const expectedAdjusted = (() => {
        const pointer = image(rectified.handle).pointer;
        const result = wasm.adjust(pointer, rectified.width, rectified.height,
            rectified.width * 3, 3, SLIDERS);
        try {
            return new Uint8Array(result.data());
        } finally {
            result.delete();
        }
    })();
    same(new Uint8Array(wasm.HEAPU8.buffer, image(adjusted.handle).pointer,
        expectedAdjusted.length), expectedAdjusted, "adjust (Pixel)");

    // Der Umriss laeuft auf dem ENTZERRTEN Bild, nicht auf dem aufbereiteten:
    // die hier eingestellten Regler (Kantenauflage, Farbbetonung) loeschen an
    // dieser kuenstlichen Szene den einen Kontrast, an dem der Umriss haengt -
    // auf einem echten Foto tun sie das nicht. Geprueft wird hier das Umpacken
    // einer Punktliste, nicht die Tauglichkeit der Umrisserkennung; die misst
    // core/tools/ChainCheck.java an den eingefrorenen Szenen.
    const contour = withImage(android, rectified, (h) =>
        android.findContourMm(h, rectified.width, rectified.height, rectified.width * 3, 3, 2.0));
    assert.ok(contour instanceof Float64Array, "der Umriss kommt als Float64Array");
    assert.ok(contour.length >= 6, "der Umriss des Rechtecks muss gefunden werden");
    same(contour, withImageDirect(rectified, (pointer) => wasm.findContourMm(pointer,
        rectified.width, rectified.height, rectified.width * 3, 3, 2.0)), "findContourMm");
});

/** Dieselbe Rechnung geradewegs im WASM-Kern, auf demselben Bild im Haufen. */
function withImageDirect(rasterHandle, work) {
    return work(image(rasterHandle.handle).pointer);
}

test("Die Erkennung liefert dieselben Ecken - ueber die Bruecke wie geradewegs", () => {
    // Ein Marker, aus den Modulbits des Kerns selbst gezeichnet: damit braucht
    // dieser Test keine PNG-Datei und keinen Dekoder, und die Szene ist
    // trotzdem eine, die der Detektor wirklich findet.
    const modules = 6;
    const scale = 20;
    const margin = 40;
    const side = modules * scale;
    const size = side + 2 * margin;
    const bits = wasm.markerBits(0, modules);

    const data = new Uint8Array(size * size * 3).fill(255);
    for (let row = 0; row < side; row += 1) {
        for (let column = 0; column < side; column += 1) {
            const value = bits[Math.floor(row / scale) * modules + Math.floor(column / scale)];
            const base = ((row + margin) * size + column + margin) * 3;
            data[base] = value;
            data[base + 1] = value;
            data[base + 2] = value;
        }
    }

    const handle = put(data, size, size, 3);
    const found = android.detectMarkers(handle, size, size, size * 3, 3, true);
    const expected = wasm.detectMarkers(image(handle).pointer, size, size, size * 3, 3, true);

    assert.equal(found.length, expected.length, "Anzahl der Marker");
    assert.ok(found.length === 1, `genau ein Marker erwartet, ${found.length} gefunden`);
    for (let index = 0; index < found.length; index += 1) {
        assert.equal(found[index].id, expected[index].id, "Marker-ID");
        assert.ok(found[index].corners instanceof Float64Array, "Ecken als Float64Array");
        same(found[index].corners, expected[index].corners, `Ecken von Marker ${found[index].id}`);
    }
});

test("Modulbits kommen als Uint8Array und Byte fuer Byte gleich zurueck", () => {
    for (const markerId of [0, 1, 2, 3]) {
        const bits = android.markerBits(markerId, 6);
        assert.ok(bits instanceof Uint8Array, "markerBits gibt ein Uint8Array");
        same(bits, wasm.markerBits(markerId, 6), `markerBits(${markerId})`);
    }
});

test("Ein Bild ohne Griff wird abgewiesen, mit uebersetzbarem Code", () => {
    assert.throws(() => withImage(android, { width: 1, height: 1 }, () => 0),
        (error) => error.code === "android_bridge_failed");
});
