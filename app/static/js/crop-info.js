/**
 * crop-info.js - die Zeile unter dem Bild: wie gross wird das, wie viele Pixel
 * sind das, und wie viel davon ist hochgerechnet.
 *
 * Der Extrapolationsanteil wird hier NUR GESCHAETZT (Rasterabtastung gegen die
 * Marker-Huelle) und dient der Anzeige. Verbindlich ist der Wert, den der Server
 * rechnet und in die PDF-Fusszeile schreibt - er sieht dieselbe Huelle, aber
 * nicht durch ein 40x40-Raster.
 *
 * Beide Schwellen (Pixelgrenze, Extrapolationswarnung) kommen aus der
 * Serverantwort (`limits`), nicht aus dieser Datei: app/config.py ist die
 * einzige Stelle fuer Konstanten (AGENTS.md, Invariante 4).
 */

import { formatNumber, t } from "./i18n.js";

const MM_PER_INCH = 25.4;
const SAMPLES_PER_AXIS = 40;

function pointInPolygon(x, y, polygon) {
    let inside = false;
    for (let index = 0, previous = polygon.length - 1; index < polygon.length; previous = index++) {
        const [xi, yi] = polygon[index];
        const [xj, yj] = polygon[previous];
        if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
}

/** Flaechenanteil des Zuschnitts ausserhalb der Marker-Huelle, 0..1. */
export function extrapolationFraction(crop, hull) {
    if (!hull || hull.length < 3 || !crop) return 0;

    let outside = 0;
    for (let i = 0; i < SAMPLES_PER_AXIS; i++) {
        for (let j = 0; j < SAMPLES_PER_AXIS; j++) {
            const x = crop.x0 + ((i + 0.5) / SAMPLES_PER_AXIS) * (crop.x1 - crop.x0);
            const y = crop.y0 + ((j + 0.5) / SAMPLES_PER_AXIS) * (crop.y1 - crop.y0);
            if (!pointInPolygon(x, y, hull)) outside++;
        }
    }
    return outside / (SAMPLES_PER_AXIS * SAMPLES_PER_AXIS);
}

function strong(text) {
    const element = document.createElement("b");
    element.textContent = text;
    return element;
}

function tinted(className, text) {
    const element = document.createElement("span");
    element.className = className;
    element.textContent = " " + text;
    return element;
}

export function renderCropInfo(target, { crop, hull, dpi, limits }) {
    if (!crop || !limits) {
        target.replaceChildren();
        return;
    }

    const width = crop.x1 - crop.x0;
    const height = crop.y1 - crop.y0;
    const widthPx = (width * dpi) / MM_PER_INCH;
    const heightPx = (height * dpi) / MM_PER_INCH;
    const megapixels = (widthPx * heightPx) / 1e6;

    const sizeLine = document.createElement("div");
    sizeLine.append(
        strong(
            t("ui.steps.crop.size", {
                width: formatNumber(width, 1),
                height: formatNumber(height, 1),
            })
        ),
        // Der Gedankenstrich ist ein Satzzeichen, kein Text - er steht deshalb
        // hier und nicht im Katalog (und ganz sicher kein "|", siehe i18n.js).
        " – ",
        t("ui.steps.crop.pixels", {
            width_px: Math.round(widthPx),
            height_px: Math.round(heightPx),
            dpi,
            megapixels: formatNumber(megapixels, 1),
        })
    );
    if (megapixels > limits.max_output_mpx) {
        sizeLine.append(
            tinted("over-limit", t("ui.steps.crop.over_limit", { limit: limits.max_output_mpx }))
        );
    }

    const fraction = extrapolationFraction(crop, hull);
    const extrapolationLine = document.createElement("div");
    extrapolationLine.append(
        t("ui.steps.crop.extrapolation", { percent: formatNumber(fraction * 100, 0) })
    );
    if (fraction > limits.extrapolation_warn) {
        extrapolationLine.append(tinted("warn", t("ui.steps.crop.extrapolation_warn")));
    }

    target.replaceChildren(sizeLine, extrapolationLine);
}
