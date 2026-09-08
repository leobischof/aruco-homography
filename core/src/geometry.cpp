// Uebersetzung von app/vision/geometry.py.
//
// Jede Funktion hier hat ein Gegenstueck dort, und der Weg ist derselbe. Wo
// Python eine float32-Zwischenstufe einlegt (convexHull, intersectConvexConvex,
// contourArea), legt diese Fassung sie auch ein - die Rundung gehoert zum
// Ergebnis und nicht zum Zufall.

#include "aruco/geometry.hpp"

#include <cmath>
#include <limits>
#include <stdexcept>

#include <opencv2/core.hpp>
// convexHull, intersectConvexConvex und contourArea wohnen in OpenCV 5 im Modul
// `geometry`, nicht mehr in `imgproc`.
#include <opencv2/geometry.hpp>

namespace aruco {
namespace {

cv::Matx33d as_matx(const Matrix3& homography) {
    return cv::Matx33d(homography[0], homography[1], homography[2], homography[3], homography[4],
                       homography[5], homography[6], homography[7], homography[8]);
}

std::vector<cv::Point2f> as_float(const std::vector<Point2>& points) {
    std::vector<cv::Point2f> converted;
    converted.reserve(points.size());
    for (const Point2& point : points) {
        converted.push_back(
            cv::Point2f(static_cast<float>(point.x), static_cast<float>(point.y)));
    }
    return converted;
}

}  // namespace

std::vector<Point2> project(const Matrix3& homography, const std::vector<Point2>& points) {
    std::vector<Point2> mapped;
    mapped.reserve(points.size());
    for (const Point2& point : points) {
        const double x = homography[0] * point.x + homography[1] * point.y + homography[2];
        const double y = homography[3] * point.x + homography[4] * point.y + homography[5];
        const double w = homography[6] * point.x + homography[7] * point.y + homography[8];
        // Division durch null gibt hier bewusst inf und keine Ausnahme: Punkte
        // hinter dem Horizont sind ein normaler Fall (extent.py klippt sie weg),
        // und ein Abbruch mitten in der Ausgleichsrechnung waere das Gegenteil
        // von hilfreich.
        mapped.push_back(Point2{x / w, y / w});
    }
    return mapped;
}

Matrix3 invert(const Matrix3& homography) {
    bool ok = false;
    const cv::Matx33d inverse = as_matx(homography).inv(cv::DECOMP_LU, &ok);
    if (!ok) {
        throw std::invalid_argument("Homographie ist singulaer und laesst sich nicht invertieren");
    }
    Matrix3 result{};
    for (int row = 0; row < 3; ++row) {
        for (int column = 0; column < 3; ++column) {
            result[static_cast<std::size_t>(row * 3 + column)] = inverse(row, column);
        }
    }
    return result;
}

double local_px_per_mm(const Matrix3& homography, const Point2& point_mm) {
    const double x = point_mm.x;
    const double y = point_mm.y;

    const double w = homography[6] * x + homography[7] * y + homography[8];
    if (std::abs(w) < 1e-12) {
        return std::numeric_limits<double>::infinity();
    }
    const double u = (homography[0] * x + homography[1] * y + homography[2]) / w;
    const double v = (homography[3] * x + homography[4] * y + homography[5]) / w;

    const double du_dx = (homography[0] - u * homography[6]) / w;
    const double du_dy = (homography[1] - u * homography[7]) / w;
    const double dv_dx = (homography[3] - v * homography[6]) / w;
    const double dv_dy = (homography[4] - v * homography[7]) / w;

    return std::sqrt(std::abs(du_dx * dv_dy - du_dy * dv_dx));
}

std::vector<Point2> convex_hull(const std::vector<Point2>& points) {
    std::vector<cv::Point2f> hull;
    cv::convexHull(as_float(points), hull);

    std::vector<Point2> result;
    result.reserve(hull.size());
    for (const cv::Point2f& point : hull) {
        result.push_back(Point2{static_cast<double>(point.x), static_cast<double>(point.y)});
    }
    return result;
}

double convex_intersection_area(const std::vector<Point2>& first,
                                const std::vector<Point2>& second) {
    std::vector<cv::Point2f> intersection;
    return cv::intersectConvexConvex(as_float(first), as_float(second), intersection);
}

double quad_area(const std::array<Point2, 4>& quad) {
    std::vector<Point2> points(quad.begin(), quad.end());
    return cv::contourArea(as_float(points));
}

}  // namespace aruco
