/**
 * thickness.js - Hoehenversatz zwischen Markerebene und Objektoberflaeche.
 * Gegenstueck zu app/vision/thickness.py.
 *
 * Eine Homographie ist nur fuer GENAU EINE Ebene exakt. Liegt das Markerblatt
 * neben dem Objekt auf dem Tisch, waehrend die interessante Flaeche h Millimeter
 * hoeher liegt, erscheint diese Flaeche radial vom Kamera-Lotpunkt weg gestreckt:
 *
 *     T = N + k * (Q - N)        mit  k = d / (d - h)
 *
 * T ist die scheinbare Lage in der Markerebene, Q die wahre Lage auf der
 * Objektoberflaeche, N der Lotpunkt, d die Kamerahoehe. Die Ruecktransformation
 * wird als Vorschaltmatrix in die Homographie gefaltet, damit das Rasterbild
 * direkt in wahren Objektkoordinaten entsteht.
 *
 * Reine Matrizenrechnung, deshalb bleibt sie hier und geht nicht in den Kern -
 * es gibt nichts, was zwischen zwei Umsetzungen driften koennte.
 */

import { matmul3 } from "./geometry.js";
import { AppError } from "./notices.js";
import { usableForThickness } from "./camera.js";

/** Affine 3x3-Matrix, die wahre Objektkoordinaten auf ihre scheinbare Lage abbildet. */
export function correctionMatrix(nadirMm, cameraHeightMm, thicknessMm) {
    if (Math.abs(thicknessMm) < 1e-9) {
        return new Float64Array([1, 0, 0, 0, 1, 0, 0, 0, 1]);
    }
    if (cameraHeightMm <= thicknessMm) {
        throw new AppError("thickness_too_large", "thickness_mm", {
            thickness_mm: thicknessMm.toFixed(1),
            camera_height_mm: cameraHeightMm.toFixed(0),
        });
    }

    const factor = cameraHeightMm / (cameraHeightMm - thicknessMm);
    const [nadirX, nadirY] = nadirMm;
    return new Float64Array([
        factor, 0.0, nadirX * (1.0 - factor),
        0.0, factor, nadirY * (1.0 - factor),
        0.0, 0.0, 1.0,
    ]);
}

/** Liefert { homography, factor }. Ohne Dicke ist H unveraendert und k = 1. */
export function effectiveHomography(homography, pose, thicknessMm) {
    if (Math.abs(thicknessMm) < 1e-9) {
        return { homography, factor: 1.0 };
    }
    if (!usableForThickness(pose)) {
        throw new AppError("camera_height_required", "camera_height_mm");
    }

    const correction = correctionMatrix(pose.nadirMm, pose.heightMm, thicknessMm);
    return {
        homography: matmul3(homography, correction),
        factor: pose.heightMm / (pose.heightMm - thicknessMm),
    };
}
