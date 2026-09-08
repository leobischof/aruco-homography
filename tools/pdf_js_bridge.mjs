/**
 * pdf_js_bridge.mjs - die Node-Seite des Pruefstands.
 *
 * DAS IST KEIN AUSLIEFERUNGSWEG. Node aus Python heraus aufzurufen ist im Betrieb
 * ausdruecklich nicht gewollt - dort baut die Oberflaeche das PDF selbst. Diese
 * Bruecke gibt es zu genau einem Zweck: die vorhandenen 33 PDF-Pruefungen lesen
 * das fertige PDF mit pypdf/pymupdf zurueck und messen es. Sie interessiert nicht,
 * wer es gebaut hat. Also darf der neue Bau gegen genau die Zusicherungen gemessen
 * werden, die der alte schon erfuellt - bevor irgendetwas umgestellt wird.
 *
 * Alles, was hier `fs` anfasst, gehoert dem Pruefstand. `web/pdf/` selbst darf das
 * nicht, und tut es auch nicht - im Browser gibt es kein Dateisystem.
 *
 * Aufruf:  node tools/pdf_js_bridge.mjs <request.json>
 * Antwort: eine Zeile JSON auf der Standardausgabe; das PDF liegt danach in der
 *          Datei, die der Auftrag unter "out" nennt.
 */

import { readFile, writeFile } from "node:fs/promises";

import { ARUCO_DICT_NAME } from "../web/constants.js";
import { buildPdf, exportOptions } from "../web/pdf/build.js";
import { MODULES, buildMarkersheet } from "../web/pdf/markersheet.js";
import { markerBitsFromOpenCv } from "./opencv_markers.mjs";

async function main() {
    const requestPath = process.argv[2];
    if (!requestPath) {
        throw new Error("Aufruf: node tools/pdf_js_bridge.mjs <request.json>");
    }
    const request = JSON.parse(await readFile(requestPath, "utf-8"));

    const handler = { export: doExport, markersheet: doMarkersheet }[request.kind];
    if (handler === undefined) {
        throw new Error(`Unbekannter Auftrag: ${request.kind}`);
    }
    const answer = await handler(request);
    process.stdout.write(`${JSON.stringify(answer)}\n`);
}

async function doExport(request) {
    const jpeg = await readFile(request.jpeg);
    const result = await buildPdf(
        jpeg,
        request.crop_w_mm,
        request.crop_h_mm,
        exportOptions(request.options),
        request.footer_lines,
        request.contour_mm,
    );

    await writeFile(request.out, result.data);
    return {
        page_size_mm: result.pageSizeMm,
        image_rect_mm: result.imageRectMm,
        page_count: result.pageCount,
        meta: result.meta,
    };
}

async function doMarkersheet(request) {
    const data = await buildMarkersheet({
        markerBits: await markerBitsFromOpenCv(ARUCO_DICT_NAME, MODULES),
        markerMm: request.marker_mm,
        spacingMm: request.spacing_mm,
        locale: request.locale,
    });
    await writeFile(request.out, data);
    return { bytes: data.length };
}

main().catch((error) => {
    // Ein AppError traegt einen Code und benannte Parameter, keinen fertigen Satz.
    // Der muss den Uebergang ueberleben, sonst kaeme drueben ein RuntimeError an, wo
    // die Python-Fassung einen AppError wirft - und eine Pruefung auf "overlap_too_large"
    // schluege unter ARUCO_PDF=js fehl, ohne dass am PDF-Bau irgendetwas falsch waere.
    if (error && error.name === "AppError") {
        process.stderr.write(
            `${JSON.stringify({ app_error: { code: error.code, field: error.fieldName, params: error.params } })}\n`,
        );
        process.exit(2);
    }
    process.stderr.write(`${error && error.stack ? error.stack : String(error)}\n`);
    process.exit(1);
});
