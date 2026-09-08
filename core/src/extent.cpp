// Uebersetzung von app/vision/extent.py::plane_extent samt dem Beschneiden an
// der Horizontlinie (clip_polygon_halfplane, dort in geometry.py).
//
// Das Beschneiden steht hier und nicht in geometry.cpp, weil es genau einen
// Aufrufer hat und der Horizont sein einziger Zweck ist. Eine allgemeine
// Polygonschere in der Grundrechenart-Datei waere ein Angebot ohne Nachfrage.

#include "aruco/extent.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

#include "aruco/constants.hpp"
#include "aruco/geometry.hpp"

namespace aruco {
namespace {

/// Schneidet ein Polygon an der Halbebene a*x + b*y + c >= eps (Sutherland-Hodgman).
std::vector<Point2> clip_halfplane(const std::vector<Point2>& polygon, double a, double b,
                                   double c, double eps) {
    std::vector<Point2> output;
    if (polygon.empty()) {
        return output;
    }

    auto side = [a, b, c, eps](const Point2& point) { return a * point.x + b * point.y + c - eps; };
    auto crossing = [](const Point2& start, const Point2& end, double side_start,
                       double side_end) {
        const double denominator = side_start - side_end;
        if (std::abs(denominator) < 1e-15) {
            return start;
        }
        const double t = side_start / denominator;
        return Point2{start.x + t * (end.x - start.x), start.y + t * (end.y - start.y)};
    };

    for (std::size_t index = 0; index < polygon.size(); ++index) {
        const Point2& current = polygon[index];
        const Point2& previous = polygon[(index + polygon.size() - 1) % polygon.size()];
        const double side_current = side(current);
        const double side_previous = side(previous);

        if (side_current >= 0.0) {
            if (side_previous < 0.0) {
                output.push_back(crossing(previous, current, side_previous, side_current));
            }
            output.push_back(current);
        } else if (side_previous >= 0.0) {
            output.push_back(crossing(previous, current, side_previous, side_current));
        }
    }
    return output;
}

/// Die Marker-Huelle, aufgeweitet um EXTENT_HULL_FACTOR mal ihre Diagonale.
Extent hull_clamp(const std::vector<Point2>& hull_mm) {
    double x_min = hull_mm[0].x;
    double x_max = hull_mm[0].x;
    double y_min = hull_mm[0].y;
    double y_max = hull_mm[0].y;
    for (const Point2& point : hull_mm) {
        x_min = std::min(x_min, point.x);
        x_max = std::max(x_max, point.x);
        y_min = std::min(y_min, point.y);
        y_max = std::max(y_max, point.y);
    }
    const double diagonal = std::hypot(x_max - x_min, y_max - y_min);
    const double pad = constants::EXTENT_HULL_FACTOR * std::max(diagonal, 1.0);
    return Extent{x_min - pad, y_min - pad, x_max + pad, y_max + pad};
}

Extent clamped_to(const Extent& self, const Extent& other) {
    return Extent{std::max(self.x0, other.x0), std::max(self.y0, other.y0),
                  std::min(self.x1, other.x1), std::min(self.y1, other.y1)};
}

}  // namespace

Extent plane_extent(const Matrix3& homography, int width, int height,
                    const std::vector<Point2>& hull_mm) {
    if (hull_mm.empty()) {
        throw std::invalid_argument("plane_extent braucht eine nicht leere Markerhuelle");
    }

    const Matrix3 inverse = invert(homography);
    const double a = inverse[6];
    const double b = inverse[7];
    const double c = inverse[8];

    // Referenzvorzeichen dort bestimmen, wo die Marker liegen - dieser Teil des
    // Bildes ist garantiert die "richtige" Seite des Horizonts.
    double sum_x = 0.0;
    double sum_y = 0.0;
    for (const Point2& point : hull_mm) {
        sum_x += point.x;
        sum_y += point.y;
    }
    const Point2 centroid{sum_x / static_cast<double>(hull_mm.size()),
                          sum_y / static_cast<double>(hull_mm.size())};
    const Point2 reference_px = project(homography, {centroid})[0];
    const double reference_w = a * reference_px.x + b * reference_px.y + c;
    const double sign = reference_w >= 0.0 ? 1.0 : -1.0;
    const double epsilon = constants::HORIZON_EPS * std::abs(reference_w);

    const std::vector<Point2> image_rect{Point2{0.0, 0.0},
                                         Point2{static_cast<double>(width), 0.0},
                                         Point2{static_cast<double>(width),
                                                static_cast<double>(height)},
                                         Point2{0.0, static_cast<double>(height)}};
    const std::vector<Point2> visible =
        clip_halfplane(image_rect, sign * a, sign * b, sign * c, epsilon);
    if (visible.size() < 3) {  // Kein brauchbarer Bereich: auf die Marker zurueckfallen.
        return hull_clamp(hull_mm);
    }

    const std::vector<Point2> mapped = project(inverse, visible);
    std::vector<Point2> finite;
    finite.reserve(mapped.size());
    for (const Point2& point : mapped) {
        if (std::isfinite(point.x) && std::isfinite(point.y)) {
            finite.push_back(point);
        }
    }
    if (finite.size() < 3) {
        return hull_clamp(hull_mm);
    }

    Extent candidate{finite[0].x, finite[0].y, finite[0].x, finite[0].y};
    for (const Point2& point : finite) {
        candidate.x0 = std::min(candidate.x0, point.x);
        candidate.y0 = std::min(candidate.y0, point.y);
        candidate.x1 = std::max(candidate.x1, point.x);
        candidate.y1 = std::max(candidate.y1, point.y);
    }
    return clamped_to(candidate, hull_clamp(hull_mm));
}

}  // namespace aruco
