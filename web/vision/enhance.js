/**
 * enhance.js - die Regler der Bildaufbereitung, und sonst nichts.
 *
 * **Gerechnet wird hier nicht.** Alle neun Stufen stehen im Kern
 * (core/src/enhance.cpp), Stufe fuer Stufe uebersetzt aus app/vision/enhance.py
 * und dort gegen tests/test_enhance.py belegt. Diese Datei setzt nur die Namen
 * um: die Oberflaeche schickt sie in der Drahtform des Servers
 * (`local_contrast`), der Kern nimmt sie in seiner (`localContrast`).
 *
 * Zwei Namen fuer dasselbe sind normalerweise eine Warnung. Hier sind sie die
 * Bedingung: die Drahtform IST die des Servers (app/schemas.py), damit
 * app/static/js/adjust.js unveraendert bleibt und dieselbe Anfrage in beiden
 * Betriebsarten gilt.
 */

import { takeRaster, withImage } from "./core.js";

// Die Zuordnung Drahtform -> Kern. Sie ist die einzige Stelle, an der beide
// Schreibweisen nebeneinanderstehen; ein neuer Regler wird hier eingetragen und
// nirgends sonst.
const FIELDS = [
    ["grayscale", "grayscale"],
    ["invert", "invert"],
    ["brightness", "brightness"],
    ["contrast", "contrast"],
    ["saturation", "saturation"],
    ["local_contrast", "localContrast"],
    ["edge_boost", "edgeBoost"],
    ["edge_overlay", "edgeOverlay"],
    ["color_emphasis", "colorEmphasis"],
    ["emphasis_strength", "emphasisStrength"],
    ["threshold", "threshold"],
];

const NEUTRAL = {
    grayscale: false,
    invert: false,
    brightness: 0.0,
    contrast: 0.0,
    saturation: 0.0,
    local_contrast: 0.0,
    edge_boost: 0.0,
    edge_overlay: 0.0,
    color_emphasis: "none",
    emphasis_strength: 0.0,
    threshold: 0.0,
};

/** Reglerstand aus der Anfrage, fehlende Felder neutral. */
export function adjustOptions(wire = {}) {
    const merged = { ...NEUTRAL };
    for (const [name] of FIELDS) {
        if (wire[name] !== undefined && wire[name] !== null) merged[name] = wire[name];
    }
    return merged;
}

/** Dieselben Regler in der Schreibweise des Kerns. */
function forCore(options) {
    const settings = {};
    for (const [wireName, coreName] of FIELDS) settings[coreName] = options[wireName];
    return settings;
}

/** True, wenn keine einzige Stufe etwas zu tun hat - der Kern entscheidet das. */
export function isIdentity(core, options) {
    return core.isIdentity(forCore(options));
}

/** Kosmetische Aufbereitung eines entzerrten BGR-Bildes. */
export function adjust(core, image, options) {
    return withImage(core, image, (pointer) =>
        takeRaster(
            core.adjust(
                pointer,
                image.width,
                image.height,
                image.width * image.channels,
                image.channels,
                forCore(options),
            ),
        ),
    );
}
