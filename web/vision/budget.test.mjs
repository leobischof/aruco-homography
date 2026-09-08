/**
 * budget.test.mjs - die Obergrenze fuer das Ausgaberaster, geraeteabhaengig.
 *
 * **Der Fehler, gegen den diese Datei steht.** Am 08.09.2026 brach auf einem
 * Xiaomi mit Android 15 der Knopf "PDF erzeugen" ab, und zwar mit:
 *
 *     Error invoking core: Java exception was raised during method invocation
 *
 * Das ist Chromiums Satz fuer eine @JavascriptInterface-Methode, die geworfen
 * hat. Geworfen hatte `ByteBuffer.allocateDirect` in NativeImages.allocate: der
 * Vorgabeausschnitt des Fotos ergab bei 300 dpi ein Raster von rund 169
 * Megapixeln, also 506 MB - und weil `runExport` das entzerrte Raster und seine
 * aufbereitete Fassung gleichzeitig haelt, das Doppelte davon. Ein Telefon hat
 * das nicht.
 *
 * Die Pruefung dagegen gab es bereits (`checkOutputBudget`), nur mass sie gegen
 * `MAX_OUTPUT_MPX` = 300 aus shared/constants.json. Das ist eine Aussage ueber
 * das FORMAT und gilt ueberall gleich; wieviel Speicher da ist, ist eine Aussage
 * ueber die MASCHINE. Auf dem Schreibtisch sind 300 MPx in Ordnung, auf dem
 * Telefon sind sie der sichere Tod - und zwar genau beim letzten Knopf.
 *
 * Geprueft wird hier die JavaScript-Haelfte: dass eine gesenkte Grenze wirklich
 * greift und dass der Abbruch den brauchbaren Rat traegt. Die andere Haelfte -
 * dass Android die Zahl richtig ausrechnet und durchreicht - steckt in
 * NativeImages.budgetMegapixels und bridge-shim.js und ist auf diesem Rechner
 * nicht messbar; sie steht unter den offenen Punkten in stage-4-android.md.
 *
 *   node --test web/vision/budget.test.mjs
 */

import assert from "node:assert/strict";
import test from "node:test";

import * as constants from "../constants.js";
import createArucoCore from "../vendor/core/aruco_core.mjs";
import { checkOutputBudget } from "./rectify.js";

const core = await createArucoCore();

/**
 * Der Vorgabeausschnitt aus shared/fixtures/flat.png, in Millimetern.
 *
 * Nicht erfunden: genau diese Zahlen liefert `/api/solve` fuer die eingefrorene
 * Szene, und genau sie ergaben auf dem Telefon die 169 Megapixel.
 */
const CROP = { x0: -541.221446669155, y0: -336.0211545042241, x1: 716.8210079205405, y1: 625.7669995023339 };

/** Die Grenze setzen, wie es bridge-shim.js auf Android tut - und danach aufraeumen. */
function withDeviceBudget(megapixels, work) {
    const previous = globalThis.ARUCO_MAX_OUTPUT_MPX;
    globalThis.ARUCO_MAX_OUTPUT_MPX = megapixels;
    try {
        return work();
    } finally {
        if (previous === undefined) delete globalThis.ARUCO_MAX_OUTPUT_MPX;
        else globalThis.ARUCO_MAX_OUTPUT_MPX = previous;
    }
}

function refused(dpi) {
    try {
        checkOutputBudget(core, CROP, dpi);
        return null;
    } catch (error) {
        return error;
    }
}

test("ohne Geraetegrenze gilt die Produktgrenze", () => {
    assert.equal(globalThis.ARUCO_MAX_OUTPUT_MPX, undefined);
    assert.equal(constants.outputBudgetMpx(), constants.MAX_OUTPUT_MPX);
});

test("die Geraetegrenze senkt, aber hebt nie", () => {
    withDeviceBudget(40, () => assert.equal(constants.outputBudgetMpx(), 40));
    // Ein Geraet mit viel Speicher darf die Formatgrenze nicht aufweichen.
    withDeviceBudget(9000, () =>
        assert.equal(constants.outputBudgetMpx(), constants.MAX_OUTPUT_MPX));
    // Unsinn faellt auf die Produktgrenze zurueck statt alles zu sperren.
    for (const bad of [0, -5, Number.NaN, "viel", null]) {
        withDeviceBudget(bad, () =>
            assert.equal(constants.outputBudgetMpx(), constants.MAX_OUTPUT_MPX));
    }
});

test("auf dem Schreibtisch geht derselbe Export durch", () => {
    // Der Beleg, dass diese Aenderung Windows und den Browser nicht anfasst:
    // 169 MPx sind unter 300, also faellt hier nichts aus.
    assert.equal(refused(300), null);
});

test("mit Telefonspeicher bricht er ab, statt den Puffer zu versuchen", () => {
    const error = withDeviceBudget(40, () => refused(300));
    assert.notEqual(error, null, "169 MPx muessen bei 40 MPx Budget abgewiesen werden");
    assert.equal(error.code, "output_too_large");
    assert.equal(error.params.limit_mpx, "40");
    assert.equal(Number(error.params.megapixels), 169);
});

test("der Rat nennt eine Aufloesung, die wirklich passt", () => {
    // 60 MPx Budget: bei 150 dpi sind es rund 42 MPx, also geht es eine Stufe
    // tiefer - und genau das soll dastehen.
    const error = withDeviceBudget(60, () => refused(300));
    assert.equal(error.params.hint.key, "errors.output_too_large_hint_dpi");
    assert.equal(error.params.hint.params.dpi, 150);
});

test("passt gar keine Aufloesung, raet er zum kleineren Ausschnitt", () => {
    // 40 MPx: auch 150 dpi ergaeben noch 42 MPx. Dann hilft nur der Ausschnitt,
    // und ein Rat "nimm 150 dpi", der ebenfalls scheitert, waere schlimmer als
    // keiner.
    const error = withDeviceBudget(40, () => refused(300));
    assert.equal(error.params.hint.key, "errors.output_too_large_hint_crop");
});
