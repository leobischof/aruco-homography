/**
 * camera.js - Brennweite, Pose und die Fallback-Kette. Gegenstueck zu
 * app/vision/camera.py.
 *
 * Die Zerlegung H = K [r1 r2 t] rechnet der Kern; hier steht nur, welcher Weg
 * genommen wird und was dabei zu melden ist:
 *
 *   Weg A (automatisch): Brennweite aus EXIF -> Zerlegung -> Hoehe und Lotpunkt.
 *   Weg B (Fallback):    Kameraabstand wird eingetippt, Lotpunkt = Bildmitte.
 *
 * Im Browser ist Weg B haeufiger als am Desktop: der Canvas wirft die
 * EXIF-Angaben weg, sie werden aus den ORIGINALBYTES gelesen (web/vision/exif.js),
 * und manche Aufnahme hat schlicht keine.
 */

import * as constants from "../constants.js";
import { inv3, project } from "./geometry.js";
import { AppError } from "./notices.js";

// 35-mm-Aequivalent bezieht sich auf ein 36 x 24 mm grosses Bildfeld.
const FILM_WIDTH_MM = 36.0;

/** 35-mm-Brennweite in Pixel-Brennweite umrechnen (orientierungsunabhaengig). */
export function focalPxFromFocal35(focal35Mm, width, height) {
    return (focal35Mm / FILM_WIDTH_MM) * Math.max(width, height);
}

/**
 * Pose bestimmen, mit Fallback-Kette und Klartext-Warnungen.
 *
 * Ist die Dicke 0, wird die Pose nur informativ berechnet: ein Fehlschlag darf
 * dann nichts blockieren, weil ohne Hoehenversatz auch nichts zu korrigieren ist.
 */
export function resolvePose(
    core,
    homography,
    focal35Mm,
    width,
    height,
    thicknessMm,
    cameraHeightOverrideMm,
    notices,
) {
    const needsCorrection = Math.abs(thicknessMm) > 1e-9;
    const automatic = tryAutomatic(core, homography, focal35Mm, width, height, notices);

    if (automatic !== null) {
        if (cameraHeightOverrideMm === null || cameraHeightOverrideMm === undefined) {
            return automatic;
        }
        // Ein ausdruecklich eingetippter Abstand schlaegt die Schaetzung.
        notices.info("camera_height_override", {
            height_mm: cameraHeightOverrideMm.toFixed(0),
            estimate_mm: automatic.heightMm.toFixed(0),
        });
        return {
            source: "manual",
            focalPx: automatic.focalPx,
            heightMm: Number(cameraHeightOverrideMm),
            nadirMm: automatic.nadirMm,
            tiltDeg: automatic.tiltDeg,
        };
    }

    if (cameraHeightOverrideMm !== null && cameraHeightOverrideMm !== undefined) {
        return {
            source: "manual",
            focalPx: null,
            heightMm: Number(cameraHeightOverrideMm),
            nadirMm: imageCentreInPlane(homography, width, height),
            tiltDeg: null,
        };
    }

    if (needsCorrection) throw new AppError("camera_height_required", "camera_height_mm");

    notices.info("camera_pose_unknown");
    return { source: "none", focalPx: null, heightMm: null, nadirMm: null, tiltDeg: null };
}

/** Weg A. Gibt null zurueck, wenn EXIF fehlt oder das Ergebnis unplausibel ist. */
function tryAutomatic(core, homography, focal35Mm, width, height, notices) {
    if (focal35Mm === null || focal35Mm === undefined) return null;

    const focalPx = focalPxFromFocal35(focal35Mm, width, height);
    const pose = core.poseFromHomography(homography, focalPx, width, height);

    if (
        pose.heightMm < constants.CAM_HEIGHT_MIN_MM ||
        pose.heightMm > constants.CAM_HEIGHT_MAX_MM
    ) {
        notices.warn("camera_height_implausible", { height_mm: pose.heightMm.toFixed(0) });
        return null;
    }

    return {
        source: "exif",
        focalPx,
        heightMm: pose.heightMm,
        nadirMm: [pose.nadirMm[0], pose.nadirMm[1]],
        tiltDeg: pose.tiltDeg,
    };
}

/** Bildmitte in die Ebene zurueckprojizieren - der Lotpunkt-Ersatz fuer Weg B. */
function imageCentreInPlane(homography, width, height) {
    const centre = project(inv3(homography), new Float64Array([width / 2.0, height / 2.0]));
    return [centre[0], centre[1]];
}

/** True, wenn die Pose fuer die Dickenkorrektur taugt. */
export function usableForThickness(pose) {
    return pose.heightMm !== null && pose.nadirMm !== null;
}
