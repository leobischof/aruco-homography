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

import { buildPdf, exportOptions } from "../web/pdf/build.js";

async function main() {
    const requestPath = process.argv[2];
    if (!requestPath) {
        throw new Error("Aufruf: node tools/pdf_js_bridge.mjs <request.json>");
    }
    const request = JSON.parse(await readFile(requestPath, "utf-8"));

    if (request.kind !== "export") {
        throw new Error(`Unbekannter Auftrag: ${request.kind}`);
    }

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
    process.stdout.write(
        `${JSON.stringify({
            page_size_mm: result.pageSizeMm,
            image_rect_mm: result.imageRectMm,
            page_count: result.pageCount,
            meta: result.meta,
        })}\n`,
    );
}

main().catch((error) => {
    process.stderr.write(`${error && error.stack ? error.stack : String(error)}\n`);
    process.exit(1);
});
