// Projektive Grundrechenarten - die Uebersetzung von app/vision/geometry.py.
//
// Hier stehen nur die Helfer, die OpenCV braucht (Huelle, Schnittflaeche,
// Markerflaeche). Was reine Formel ist - `project`, die Trapezformel, das
// Beschneiden an einer Halbebene -, bleibt in der jeweiligen Hostsprache: eine
// Matrixmultiplikation ueber die Bindungsgrenze zu schicken kostet mehr, als sie
// wert ist, und driften kann sie nicht.

#ifndef ARUCO_GEOMETRY_HPP
#define ARUCO_GEOMETRY_HPP

#include <array>
#include <vector>

#include "aruco/types.hpp"

namespace aruco {

/// Homographie auf Punkte anwenden und durch w teilen.
///
/// Punkte auf dem Horizont (w == 0) kommen als inf zurueck, statt zu werfen -
/// genau wie in Python. Wer das nicht vertraegt, klippt vorher (siehe
/// plane_extent).
std::vector<Point2> project(const Matrix3& homography, const std::vector<Point2>& points);

/// Homographie invertieren. Wirft, wenn sie singulaer ist.
Matrix3 invert(const Matrix3& homography);

/// Lokaler Abbildungsmassstab Ebene -> Bild: Wurzel aus dem Betrag der
/// Jacobi-Determinante (Spec 3.7). Dieses eine Mass traegt RMS-in-mm, die
/// Interpolationswahl und die PDF-Fusszeile - ueberall dasselbe.
double local_px_per_mm(const Matrix3& homography, const Point2& point_mm);

/// Konvexe Huelle als Polygon.
///
/// Gerechnet wird - wie in Python - ueber float32: `cv2.convexHull` nimmt dort
/// ein `astype(np.float32)`. Die Huellpunkte sind damit auf float32 gerundet,
/// und das ist kein Schoenheitsfehler, sondern muss auf beiden Seiten gleich
/// sein, sonst weicht schon der Startzuschnitt ab.
std::vector<Point2> convex_hull(const std::vector<Point2>& points);

/// Flaeche des Schnitts zweier KONVEXER Polygone (cv::intersectConvexConvex).
double convex_intersection_area(const std::vector<Point2>& first,
                                const std::vector<Point2>& second);

/// Bildflaeche eines Markervierecks (cv::contourArea auf float32-Ecken).
///
/// Gebraucht, um bei doppelt erkannter ID und im Frei-Modus den groessten Marker
/// zu waehlen. Die Wahl ist diskret, aber sie entscheidet, welcher Marker der
/// Anker wird - und ein anderer Anker ist ein anderer Startwert.
double quad_area(const std::array<Point2, 4>& quad);

}  // namespace aruco

#endif  // ARUCO_GEOMETRY_HPP
