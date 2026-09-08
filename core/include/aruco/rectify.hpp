// Entzerren in ein exaktes Millimeter-Raster - Uebersetzung von
// app/vision/rectify.py::rectify.
//
// Der Kniff steckt im halben Pixel: die Abbildung Ausgabepixel -> mm setzt die
// Pixelmitten auf x0 + (u + 0.5)/spp. Dadurch fallen die AUSSENKANTEN des
// Rasters exakt auf die Zuschnittgrenzen, und das Bild belegt im PDF hinterher
// genau crop_w x crop_h Millimeter (Invariante 1).

#ifndef ARUCO_RECTIFY_HPP
#define ARUCO_RECTIFY_HPP

#include "aruco/types.hpp"

namespace aruco {

/// Rastergroesse in Pixeln fuer einen Zuschnitt bei gegebener Aufloesung.
///
/// Gerundet wird zur GERADEN Zahl, wie Pythons `round()`. Bei 300 dpi trennt eine
/// Pixelbreite 0,085 mm - achtmal die Toleranz dieses Projekts; ein anderes
/// Rundungsverfahren waere ein seltener, unauffindbarer Unterschied.
void output_size(const Extent& crop, double px_per_mm, int& width, int& height);

/// Entzerrt den Zuschnitt in ein BGR-Raster mit exakt px_per_mm Pixeln je mm.
///
/// `source_px_per_mm` <= 0 heisst "unbekannt" (Pythons None). Ist die Quelle
/// deutlich feiner als das Ziel, wird flaechengemittelt statt interpoliert -
/// sonst frisst Aliasing die Kanten, die gleich geschnitten werden sollen.
ImageBuffer rectify(const ImageView& image, const Matrix3& homography, const Extent& crop,
                    double px_per_mm, double source_px_per_mm);

}  // namespace aruco

#endif  // ARUCO_RECTIFY_HPP
