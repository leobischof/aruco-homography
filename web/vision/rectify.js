/**
 * rectify.js - Entzerren in ein exaktes Millimeter-Raster. Gegenstueck zu
 * app/vision/rectify.py.
 *
 * Die Entzerrung selbst rechnet der Kern; hier stehen die Umrechnungen um sie
 * herum und die Speichergrenze. Die Grenze bleibt in dieser Schicht, weil sie
 * einen Fehler MIT VORSCHLAG wirft - und ein Vorschlag ist Text, der aus dem
 * Katalog kommt (AGENTS.md, Invariante 7).
 *
 * Im Browser ist sie ausserdem nicht die einzige Grenze. Ein Rasterbild muss
 * hier durch eine Leinwand, um ein JPEG zu werden, und Leinwaende haben eigene
 * Obergrenzen (web/vision/image.js). MAX_OUTPUT_MPX bleibt trotzdem die
 * verbindliche Zahl - sie steht in shared/constants.json und gilt fuer alle
 * Ziele gleich.
 */

import * as constants from "../constants.js";
import { takeRaster, withImage } from "./core.js";
import { height, width } from "./extent.js";
import { AppError } from "./notices.js";

/** Rastergroesse in Pixeln fuer einen Zuschnitt bei gegebener Aufloesung. */
export function outputSize(core, crop, pxPerMm) {
    const size = core.outputSize(crop.x0, crop.y0, crop.x1, crop.y1, pxPerMm);
    return [size.width, size.height];
}

export function pxPerMmForDpi(dpi) {
    return dpi / constants.MM_PER_INCH;
}

/** Aufloesung, bei der die Vorschau gerade noch unter PREVIEW_MAX_PX bleibt. */
export function previewPxPerMm(area) {
    const longestMm = Math.max(width(area), height(area), 1e-6);
    return constants.PREVIEW_MAX_PX / longestMm;
}

/** Bricht ab, wenn das Rasterbild die Speichergrenze sprengt - mit Vorschlag. */
export function checkOutputBudget(core, crop, dpi) {
    const [pixelWidth, pixelHeight] = outputSize(core, crop, pxPerMmForDpi(dpi));
    const megapixels = (pixelWidth * pixelHeight) / 1e6;
    if (megapixels <= constants.MAX_OUTPUT_MPX) return;

    const affordable = constants.DPI_CHOICES.filter(
        (choice) => megapixelsFor(core, crop, choice) <= constants.MAX_OUTPUT_MPX,
    );
    // Welcher Rat hilft, steht hier fest - in welcher Sprache er ankommt, erst
    // am Rand. Deshalb reist der Vorschlag als Schluessel mit Parametern.
    const hint =
        affordable.length > 0
            ? { key: "errors.output_too_large_hint_dpi", params: { dpi: Math.max(...affordable) } }
            : {
                  key: "errors.output_too_large_hint_crop",
                  params: { dpi: Math.min(...constants.DPI_CHOICES) },
              };

    throw new AppError("output_too_large", "dpi", {
        width_px: pixelWidth,
        height_px: pixelHeight,
        megapixels: megapixels.toFixed(0),
        limit_mpx: constants.MAX_OUTPUT_MPX.toFixed(0),
        hint,
    });
}

function megapixelsFor(core, crop, dpi) {
    const [pixelWidth, pixelHeight] = outputSize(core, crop, pxPerMmForDpi(dpi));
    return (pixelWidth * pixelHeight) / 1e6;
}

/**
 * Entzerrt den Zuschnitt in ein Raster mit exakt pxPerMm Pixeln je Millimeter.
 *
 * `sourcePxPerMm` ist 0, solange niemand die Quellaufloesung kennt - dann wird
 * interpoliert statt flaechengemittelt.
 */
export function rectify(core, image, homography, crop, pxPerMm, sourcePxPerMm = 0.0) {
    return withImage(core, image, (pointer) =>
        takeRaster(
            core.rectify(
                pointer,
                image.width,
                image.height,
                image.width * image.channels,
                image.channels,
                homography,
                crop.x0,
                crop.y0,
                crop.x1,
                crop.y1,
                pxPerMm,
                sourcePxPerMm,
            ),
        ),
    );
}
