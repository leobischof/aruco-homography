// Welcher Teil der Ebene ist ueberhaupt abbildbar - Uebersetzung von
// app/vision/extent.py::plane_extent.
//
// Bei schraeger Aufnahme laeuft ein Teil des Bildes gegen den Horizont der
// Homographie: dort bildet die Ruecktransformation ins Unendliche ab. Ohne
// Clipping kaeme ein Extent von mehreren Kilometern heraus.
//
// `default_crop` und `extrapolation_fraction` bleiben in der Hostsprache: die
// eine ist ein Rechteck um einen Schwerpunkt, die andere ein Flaechenverhaeltnis
// ueber `convex_intersection_area`. Beide sind Formel, nicht Verfahren.

#ifndef ARUCO_EXTENT_HPP
#define ARUCO_EXTENT_HPP

#include <vector>

#include "aruco/types.hpp"

namespace aruco {

/// Bounding-Box des abbildbaren Ebenenbereichs, horizontsicher und geklammert.
///
/// `hull_mm` ist die konvexe Huelle der Markerecken in der Ebene: sie liefert das
/// Referenzvorzeichen fuer die Horizontseite UND die Klammer, ueber die hinaus
/// nicht extrapoliert wird.
Extent plane_extent(const Matrix3& homography, int width, int height,
                    const std::vector<Point2>& hull_mm);

}  // namespace aruco

#endif  // ARUCO_EXTENT_HPP
