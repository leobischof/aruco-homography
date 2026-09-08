// Uebersetzung von app/vision/camera.py::pose_from_homography.
//
// Schritt fuer Schritt dieselbe Rechnung. Der einzige Ort, an dem C++ etwas
// anderes tut als numpy, ist die SVD: `np.linalg.svd` ruft LAPACK, `cv::SVD`
// rechnet selbst. Das Produkt u*vt ist davon unberuehrt - eine SVD ist bis auf
// paarweise Vorzeichenwechsel in u und vt eindeutig, und die kuerzen sich im
// Produkt heraus. Die Wahl, die nicht eindeutig waere - welche Spalte gespiegelt
// wird, wenn die Determinante negativ ist -, faellt in beiden Fassungen auf die
// letzte Spalte.

#include "aruco/camera.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

#include <opencv2/core.hpp>

namespace aruco {
namespace {

/// Naechstgelegene echte Rotationsmatrix (SVD, Determinante auf +1 gezwungen).
cv::Matx33d orthonormalize(const cv::Matx33d& matrix) {
    cv::Matx33d u;
    cv::Matx31d w;
    cv::Matx33d vt;
    cv::SVD::compute(matrix, w, u, vt);

    cv::Matx33d rotation = u * vt;
    if (cv::determinant(rotation) < 0.0) {
        for (int row = 0; row < 3; ++row) {
            u(row, 2) = -u(row, 2);
        }
        rotation = u * vt;
    }
    return rotation;
}

}  // namespace

Pose pose_from_homography(const Matrix3& homography, double focal_px, int width, int height) {
    // Genau die Grenze, an der auch numpy scheitert: mit f == 0 ist K singulaer
    // und np.linalg.inv wirft. Eine STRENGERE Pruefung waere ein Unterschied zur
    // Referenz - eine unplausible Brennweite faengt resolve_pose ab, nicht hier.
    if (focal_px == 0.0) {
        throw std::invalid_argument("pose_from_homography: Brennweite 0 macht K singulaer");
    }

    const cv::Matx33d intrinsics(focal_px, 0.0, width / 2.0, 0.0, focal_px, height / 2.0, 0.0, 0.0,
                                 1.0);
    const cv::Matx33d matrix(homography[0], homography[1], homography[2], homography[3],
                             homography[4], homography[5], homography[6], homography[7],
                             homography[8]);
    const cv::Matx33d normalized = intrinsics.inv(cv::DECOMP_LU) * matrix;

    cv::Vec3d first(normalized(0, 0), normalized(1, 0), normalized(2, 0));
    cv::Vec3d second(normalized(0, 1), normalized(1, 1), normalized(2, 1));
    cv::Vec3d translation(normalized(0, 2), normalized(1, 2), normalized(2, 2));

    const double scale = 2.0 / (cv::norm(first) + cv::norm(second));
    first *= scale;
    second *= scale;
    translation *= scale;

    if (translation[2] < 0.0) {  // Die Ebene muss vor der Kamera liegen.
        first = -first;
        second = -second;
        translation = -translation;
    }

    const cv::Vec3d third = first.cross(second);
    const cv::Matx33d stacked(first[0], second[0], third[0], first[1], second[1], third[1],
                              first[2], second[2], third[2]);
    const cv::Matx33d rotation = orthonormalize(stacked);

    const cv::Vec3d center = -(rotation.t() * translation);

    Pose pose;
    pose.height_mm = std::abs(center[2]);
    pose.nadir_mm = Point2{center[0], center[1]};
    pose.tilt_deg = std::acos(std::min(1.0, std::abs(rotation(2, 2)))) * 180.0 / CV_PI;
    return pose;
}

}  // namespace aruco
