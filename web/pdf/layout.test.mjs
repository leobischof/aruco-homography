/**
 * layout.test.mjs - dieselben elf Faelle wie tests/test_layout.py, dieselben Zahlen.
 *
 * Das ist keine zweite Testsuite fuer dieselbe Sache, sondern die Vorstufe: die
 * Seiten- und Kachelrechnung braucht keine einzige Zeile pdf-lib und laesst sich
 * deshalb pruefen, BEVOR es etwas zu zeichnen gibt. Erst wenn Kachelzahl,
 * Ueberlappung und Abdeckung stimmen, lohnt sich der Rest.
 *
 * Der eigentliche Beweis bleibt die Python-Suite: sie liest das fertige PDF zurueck
 * und misst es. Die hier ist die Landkarte, nicht das Gelaende.
 *
 *   node --test web/pdf/layout.test.mjs
 */

import assert from "node:assert/strict";
import test from "node:test";

import * as constants from "../constants.js";
import { AppError } from "./errors.js";
import { singlePage, stripHeight, tileLayout } from "./layout.js";

// pytest.approx ohne Argumente: rel=1e-6, abs=1e-12. Dieselbe Regel, damit ein
// hier gruener Fall auch drueben gruen ist.
function approx(actual, expected, message = "") {
    const tolerance = Math.max(1e-6 * Math.abs(expected), 1e-12);
    assert.ok(
        Math.abs(actual - expected) <= tolerance,
        `${message} ${actual} != ${expected} (Toleranz ${tolerance})`,
    );
}

function approxAll(actual, expected, message = "") {
    assert.equal(actual.length, expected.length, `${message} Laenge`);
    actual.forEach((value, index) => approx(value, expected[index], `${message}[${index}]`));
}

test("Seite ist Objekt plus Rand plus Streifen", () => {
    const page = singlePage(400.0, 250.0, 5.0, stripHeight());

    approx(page.pageW, 410.0);
    approx(page.pageH, 250.0 + 10.0 + constants.STRIP_H_MM);
    approxAll(page.image.asTuple(), [5.0, 5.0 + constants.STRIP_H_MM, 400.0, 250.0]);
});

test("Streifen ist immer da", () => {
    // Er traegt das Markenzeichen, und das gehoert auf jedes Blatt.
    approx(stripHeight(), constants.STRIP_H_MM);
});

test("randlos belegt das Bild trotzdem exakt den Zuschnitt", () => {
    // Der Streifen vergroessert die SEITE, nie das Bild - die Invariante bleibt.
    const page = singlePage(400.0, 250.0, 0.0, stripHeight());

    approxAll(page.image.asTuple(), [0.0, constants.STRIP_H_MM, 400.0, 250.0]);
    approxAll([page.pageW, page.pageH], [400.0, 250.0 + constants.STRIP_H_MM]);
});

test("leerer Zuschnitt wird abgelehnt", () => {
    assert.throws(
        () => singlePage(0.0, 250.0, 5.0, 0.0),
        (error) => error instanceof AppError && error.code === "empty_crop",
    );
});

test("Kachelzahl folgt der Formel", () => {
    const strip = stripHeight();
    const plan = tileLayout(700.0, 500.0, "A4", "portrait", 5.0, 10.0, strip);

    const usableW = 210.0 - 10.0;
    const usableH = 297.0 - 10.0 - constants.STRIP_H_MM;
    assert.equal(plan.nCols, Math.max(1, Math.ceil((700.0 - 10.0) / (usableW - 10.0))));
    assert.equal(plan.nRows, Math.max(1, Math.ceil((500.0 - 10.0) / (usableH - 10.0))));
    assert.equal(plan.pageCount, plan.nCols * plan.nRows);
});

test("Kacheln decken den ganzen Zuschnitt ab", () => {
    // Jeder Millimeter des Zuschnitts muss auf mindestens einem Blatt liegen.
    const cropW = 700.0;
    const cropH = 500.0;
    const plan = tileLayout(cropW, cropH, "A4", "portrait", 5.0, 10.0, stripHeight());

    for (const position of [0.0, 123.4, 349.9, cropW - 0.01]) {
        assert.ok(
            plan.tiles.some((t) => t.cropX <= position && position <= t.cropX + t.srcW),
            `x = ${position}`,
        );
    }
    for (const position of [0.0, 88.8, 251.0, cropH - 0.01]) {
        assert.ok(
            plan.tiles.some((t) => t.cropY <= position && position <= t.cropY + t.srcH),
            `y = ${position}`,
        );
    }
});

test("Ueberlappung wird eingehalten", () => {
    const plan = tileLayout(700.0, 500.0, "A4", "portrait", 5.0, 10.0, 0.0);
    approx(plan.stepW, plan.usableW - plan.overlapMm);
    approx(plan.stepH, plan.usableH - plan.overlapMm);
});

test("letzte Kachel laeuft nicht ueber den Zuschnitt hinaus", () => {
    const plan = tileLayout(700.0, 500.0, "A4", "portrait", 5.0, 10.0, 0.0);
    for (const tile of plan.tiles) {
        assert.ok(tile.cropX + tile.srcW <= 700.0 + 1e-9);
        assert.ok(tile.cropY + tile.srcH <= 500.0 + 1e-9);
        assert.ok(tile.srcW > 0.0 && tile.srcH > 0.0);
    }
});

test("auto-Ausrichtung waehlt die seitensparende Variante", () => {
    const breit = tileLayout(900.0, 200.0, "A4", "auto", 5.0, 10.0, 0.0);
    const quer = tileLayout(900.0, 200.0, "A4", "landscape", 5.0, 10.0, 0.0);
    const hoch = tileLayout(900.0, 200.0, "A4", "portrait", 5.0, 10.0, 0.0);

    assert.equal(breit.pageCount, Math.min(quer.pageCount, hoch.pageCount));
});

test("zu grosse Ueberlappung bricht ab", () => {
    assert.throws(
        () => tileLayout(700.0, 500.0, "A4", "portrait", 5.0, 250.0, 0.0),
        (error) => error instanceof AppError && error.code === "overlap_too_large",
    );
});

test("A3 braucht weniger Blaetter als A4", () => {
    const a4 = tileLayout(700.0, 500.0, "A4", "auto", 5.0, 10.0, 0.0);
    const a3 = tileLayout(700.0, 500.0, "A3", "auto", 5.0, 10.0, 0.0);
    assert.ok(a3.pageCount < a4.pageCount, `${a3.pageCount} < ${a4.pageCount}`);
});
