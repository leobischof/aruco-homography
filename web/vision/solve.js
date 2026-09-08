/**
 * solve.js - Modus waehlen, loesen, Qualitaet bewerten. Das Gegenstueck zu
 * app/vision/solve.py.
 *
 * **Was hier NICHT steht, ist die Rechnung.** Die vier Zahlenverfahren -
 * getPerspectiveTransform, findHomography(LMEDS), der nichtlineare Ausgleich und
 * der gemeinsame Frei-Modus-Fit - kommen aus dem C++-Kern, genau wie auf der
 * Python-Seite. Hier steht nur, welches davon wann laeuft, wie die Marker auf
 * das Blatt gehoeren und welche Warnungen daraus folgen. Genau die Grenze zieht
 * app/vision/solve.py auch: dort holt sie `backend.implementation`, hier das
 * geladene wasm.
 *
 * Der Grund fuer diese Grenze ist der ganze Umzug: zwei Umsetzungen derselben
 * Homographie driften, und sie driften in Millimetern
 * (docs/cpp-migration/README.md, Abschnitt 4).
 */

import * as constants from "../constants.js";
import { centroid, inv3, markerPlaneCorners, polygonArea, project } from "./geometry.js";
import { AppError } from "./notices.js";

/**
 * Sollpositionen der Blatt-Marker aus den GEMESSENEN Blattmassen.
 *
 * Es wird nichts hochgerechnet (AGENTS.md, Invariante 2): Markergroesse und die
 * beiden Mittelpunktabstaende kommen so, wie sie am Ausdruck gemessen wurden.
 */
export function sheetPlaneCorners(markerMm, spacingMm) {
    const centres = constants.sheetMarkerCenters(spacingMm);
    const layout = new Map();
    for (const [id, [cx, cy]] of Object.entries(centres)) {
        layout.set(Number(id), markerPlaneCorners(cx, cy, markerMm));
    }
    return layout;
}

/** Einstiegspunkt: Modus waehlen, loesen, Qualitaet bewerten. */
export function solve(core, markers, markerMm, mode, notices, spacingMm) {
    if (markers.length === 0) throw new AppError("no_markers");
    if (!(markerMm > 0.0)) throw new AppError("bad_marker_size", "marker_mm");

    let result;
    if (mode === "sheet") {
        result = solveSheet(core, markers, markerMm, spacingMm);
    } else if (mode === "free") {
        result = solveFree(core, markers, markerMm);
    } else {
        throw new AppError("bad_mode", "mode", { mode });
    }

    const used = markers.filter((marker) => result.planeById.has(marker.id));
    return finalize(core, result.homography, result.planeById, used, markerMm, mode, notices);
}

function solveSheet(core, markers, markerMm, spacingMm) {
    const layout = sheetPlaneCorners(markerMm, spacingMm);
    const usable = markers.filter((marker) => layout.has(marker.id));
    if (usable.length === 0) {
        throw new AppError("no_sheet_ids", "mode", {
            found: markers.map((marker) => marker.id).join(", "),
            expected: constants.SHEET_MARKER_IDS.join(", "),
        });
    }

    const planeById = new Map(usable.map((marker) => [marker.id, layout.get(marker.id)]));
    const planePoints = concat(usable.map((marker) => planeById.get(marker.id)));
    const imagePoints = concat(usable.map((marker) => marker.corners));

    let homography;
    if (usable.length === 1) {
        // Vier Punkte: exakt bestimmt, LMEDS braucht mehr. Kein Ausgleich moeglich.
        homography = core.homographyFromQuad(planePoints, imagePoints);
    } else {
        try {
            homography = core.homographyLmeds(planePoints, imagePoints);
        } catch (error) {
            throw new AppError("homography_failed");
        }
    }

    return {
        homography: core.refineHomography(homography, planePoints, imagePoints),
        planeById,
    };
}

function solveFree(core, markers, markerMm) {
    // Der groesste Marker wird der Anker - er definiert Ursprung und Massstab der
    // Ebene. Sortiert wird HIER und nicht im Kern, weil nur diese Schicht die
    // Marker-IDs kennt, die hinterher wieder zugeordnet werden muessen.
    const ordered = [...markers].sort((a, b) => b.areaPx - a.areaPx);
    const fit = core.fitFree(concat(ordered.map((marker) => marker.corners)), markerMm);

    const unit = markerPlaneCorners(markerMm / 2.0, markerMm / 2.0, markerMm);
    const planeById = new Map([[ordered[0].id, unit]]);
    for (let index = 1; index < ordered.length; index += 1) {
        const offsetX = fit.offsets[(index - 1) * 2];
        const offsetY = fit.offsets[(index - 1) * 2 + 1];
        planeById.set(
            ordered[index].id,
            markerPlaneCorners(markerMm / 2.0 + offsetX, markerMm / 2.0 + offsetY, markerMm),
        );
    }
    return { homography: fit.homography, planeById };
}

function finalize(core, homography, planeById, markers, markerMm, mode, notices) {
    const inverse = inv3(homography);
    const fits = [];
    let squaredSum = 0.0;
    let squaredCount = 0;

    for (const marker of markers) {
        const plane = planeById.get(marker.id);
        const reprojected = project(homography, plane);

        let markerSquared = 0.0;
        for (let corner = 0; corner < 4; corner += 1) {
            const dx = reprojected[corner * 2] - marker.corners[corner * 2];
            const dy = reprojected[corner * 2 + 1] - marker.corners[corner * 2 + 1];
            markerSquared += dx * dx + dy * dy;
        }
        squaredSum += markerSquared;
        squaredCount += 4;

        const measured = project(inverse, marker.corners);
        fits.push({
            id: marker.id,
            cornersPx: marker.corners,
            planeMm: plane,
            residualPx: Math.sqrt(markerSquared / 4.0),
            sideMmMeasured: meanSideLength(measured),
            rotationDeg: rotationDeviation(measured),
        });
    }

    const rmsPx = squaredCount > 0 ? Math.sqrt(squaredSum / squaredCount) : 0.0;
    const hullMm = core.convexHull(concat(fits.map((fit) => fit.planeMm)));
    const [hullCentreX, hullCentreY] = centroid(hullMm);
    const pxPerMm = core.localPxPerMm(homography, hullCentreX, hullCentreY);

    const solution = {
        homography,
        mode,
        markers: fits,
        rmsPx,
        hullMm,
        pxPerMm,
        mmPerPx: pxPerMm ? 1.0 / pxPerMm : Infinity,
        rmsMm: rmsPx * (pxPerMm ? 1.0 / pxPerMm : Infinity),
    };
    addQualityNotices(core, solution, markerMm, notices);
    return solution;
}

/** Mittlere Kantenlaenge eines zurueckprojizierten Markers, in mm. */
function meanSideLength(quad) {
    let sum = 0.0;
    for (let corner = 0; corner < 4; corner += 1) {
        const next = (corner + 1) % 4;
        sum += Math.hypot(quad[next * 2] - quad[corner * 2], quad[next * 2 + 1] - quad[corner * 2 + 1]);
    }
    return sum / 4.0;
}

/** Abweichung von der Achsparallelitaet, in Grad (-45..45). */
function rotationDeviation(quad) {
    const angle = (Math.atan2(quad[3] - quad[1], quad[2] - quad[0]) * 180.0) / Math.PI;
    return (((angle + 45.0) % 90.0) + 90.0) % 90.0 - 45.0;
}

/** Alle Warnungen aus Spec 3.7 - keine bricht ab, jede wird sichtbar. */
function addQualityNotices(core, solution, markerMm, notices) {
    if (solution.markers.length === 1) notices.warn("single_marker");

    // Kollinearitaet an den MITTELPUNKTEN messen, nicht an der Eckenhuelle: jeder
    // Marker bringt selbst 67 mm Ausdehnung mit, sodass drei Marker in einer Reihe
    // eine voellig unauffaellige Eckenhuelle ergeben - und die Warnung nie kaeme.
    const centres = new Float64Array(solution.markers.length * 2);
    solution.markers.forEach((fit, index) => {
        const [x, y] = centroid(fit.planeMm);
        centres[index * 2] = x;
        centres[index * 2 + 1] = y;
    });

    if (solution.markers.length >= 2) {
        const spread =
            solution.markers.length >= 3 ? polygonArea(core.convexHull(centres)) : 0.0;
        let span = 0.0;
        for (let a = 0; a < solution.markers.length; a += 1) {
            for (let b = 0; b < solution.markers.length; b += 1) {
                span = Math.max(
                    span,
                    Math.hypot(centres[a * 2] - centres[b * 2], centres[a * 2 + 1] - centres[b * 2 + 1]),
                );
            }
        }
        if (span > 0.0 && spread / (span * span) < constants.COLLINEARITY_WARN) {
            notices.warn("collinear_markers");
        }
    }

    if (solution.rmsPx > constants.RMS_WARN_PX || solution.rmsMm > constants.RMS_WARN_MM) {
        notices.warn("high_residual", {
            rms_px: solution.rmsPx.toFixed(2),
            rms_mm: solution.rmsMm.toFixed(2),
        });
    }

    for (const fit of solution.markers) {
        const deviation = Math.abs(fit.sideMmMeasured - markerMm) / markerMm;
        if (deviation > constants.MARKER_SIZE_DEV_WARN) {
            notices.warn("marker_size_deviation", {
                marker_id: fit.id,
                measured_mm: fit.sideMmMeasured.toFixed(1),
                expected_mm: markerMm.toFixed(1),
                deviation_pct: (deviation * 100.0).toFixed(1),
            });
        }
    }

    if (solution.mode === "free") {
        const reference = solution.markers[0].rotationDeg;
        for (const fit of solution.markers.slice(1)) {
            if (Math.abs(fit.rotationDeg - reference) > constants.MARKER_ROT_WARN_DEG) {
                notices.warn("marker_rotation", {
                    marker_id: fit.id,
                    rotation_deg: Math.abs(fit.rotationDeg - reference).toFixed(1),
                });
            }
        }
    }
}

/** Mehrere Punktlisten zu einer flachen Float64Array verketten. */
function concat(parts) {
    let length = 0;
    for (const part of parts) length += part.length;
    const joined = new Float64Array(length);
    let offset = 0;
    for (const part of parts) {
        joined.set(part, offset);
        offset += part.length;
    }
    return joined;
}

export { concat };
