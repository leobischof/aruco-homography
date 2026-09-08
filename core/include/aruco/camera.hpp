// Kamerapose aus der Homographie - Uebersetzung von app/vision/camera.py.
//
// Gebraucht wird das fuer die Dickenkorrektur: sie streckt radial vom LOTPUNKT
// der Kamera aus, also muss man wissen, wo der liegt und wie hoch die Kamera
// darueber steht. Beides faellt aus der Zerlegung H = K [r1 r2 t] heraus.
//
// Die Fallback-Kette (EXIF - eingetippter Abstand - gar nichts) bleibt in der
// Hostsprache: sie erzeugt Warnungen und Abbrueche mit Codes, und die gehoeren
// an den Rand (app/notices.py, Invariante 7).

#ifndef ARUCO_CAMERA_HPP
#define ARUCO_CAMERA_HPP

#include "aruco/types.hpp"

namespace aruco {

/// Was die Zerlegung ueber die Kamera hergibt.
struct Pose {
    double height_mm = 0.0;
    Point2 nadir_mm{};
    double tilt_deg = 0.0;
};

/// Zerlegt H in Rotation und Translation. Rueckgabe in Ebenen-mm bzw. Grad.
Pose pose_from_homography(const Matrix3& homography, double focal_px, int width, int height);

}  // namespace aruco

#endif  // ARUCO_CAMERA_HPP
