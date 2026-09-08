/**
 * extent.js - abbildbarer Bereich, Startzuschnitt und Extrapolationsanteil.
 * Gegenstueck zu app/vision/extent.py.
 *
 * Das Horizont-Clipping selbst rechnet der Kern (`planeExtent`): dort steckt die
 * Ruecktransformation, und die entscheidet, wie gross die Schablone werden darf.
 * Hier stehen die beiden Formeln darum herum - der Startzuschnitt und der Anteil
 * des Zuschnitts, der ausserhalb der gemessenen Markerhuelle liegt.
 */

import * as constants from "../constants.js";
import { centroid, rectPolygon } from "./geometry.js";

/** Achsparalleler Bereich in Ebenen-Millimetern, als schlichtes Objekt. */
export function extent(x0, y0, x1, y1) {
    return { x0, y0, x1, y1 };
}

export function width(area) {
    return area.x1 - area.x0;
}

export function height(area) {
    return area.y1 - area.y0;
}

export function clampedTo(area, other) {
    return extent(
        Math.max(area.x0, other.x0),
        Math.max(area.y0, other.y0),
        Math.min(area.x1, other.x1),
        Math.min(area.y1, other.y1),
    );
}

/** Bounding-Box des abbildbaren Ebenenbereichs, horizontsicher und geklammert. */
export function planeExtent(core, homography, imageWidth, imageHeight, hullMm) {
    const values = core.planeExtent(homography, imageWidth, imageHeight, hullMm);
    return extent(values[0], values[1], values[2], values[3]);
}

/** Startvorschlag fuer den Zuschnitt: der Extent, um den Huellschwerpunkt begrenzt. */
export function defaultCrop(area, hullMm) {
    const limit = constants.DEFAULT_CROP_MAX_MM;
    const [centreX, centreY] = centroid(hullMm);
    const aroundHull = extent(
        centreX - limit / 2.0,
        centreY - limit / 2.0,
        centreX + limit / 2.0,
        centreY + limit / 2.0,
    );
    return clampedTo(area, aroundHull);
}

/**
 * Flaechenanteil des Zuschnitts ausserhalb der konvexen Marker-Huelle (0..1).
 *
 * Genau dort ist die Homographie am unzuverlaessigsten: sie wird ueber den
 * gemessenen Bereich hinaus fortgeschrieben, und Objektivverzeichnung schlaegt
 * ungebremst durch.
 */
export function extrapolationFraction(core, crop, hullMm) {
    const cropPolygon = rectPolygon(crop.x0, crop.y0, crop.x1, crop.y1);
    const cropArea = width(crop) * height(crop);
    if (cropArea <= 0.0) return 0.0;
    const inside = core.convexIntersectionArea(cropPolygon, hullMm);
    return Math.min(1.0, Math.max(0.0, 1.0 - inside / cropArea));
}
