// Die C-Schnittstelle, Teil 2: alles, was ZAHLEN hinein- und ZAHLEN
// herausgibt - Homographie, Ausgleich, Kamerapose, Ausdehnung, Geometrie.
//
// Getrennt von capi.cpp und capi_image.cpp, und die Trennlinie ist nicht
// Dateigroesse: hier geht es um Dutzende Bytes, dort um Dutzende Megabyte. Die
// Speicherfrage, die eine Bilddatei stellt, stellt eine Homographie nicht - und
// wer capi_image.cpp aufschlaegt, soll genau diese Frage vor sich haben und
// nicht neun Zahlen dazwischen.
//
// Wie ueberall in dieser Schicht: **hier wird nicht gerechnet.** Jede Zeile
// packt um oder faengt. Gerechnet wird in core/src/solve.cpp, camera.cpp,
// extent.cpp und geometry.cpp - denselben Dateien, aus denen die Python-Bindung
// und der Browser-Bau ihre Zahlen holen.

#include <cstdint>
#include <vector>

#include "aruco/camera.hpp"
#include "aruco/capi.h"
#include "aruco/extent.hpp"
#include "aruco/geometry.hpp"
#include "aruco/rectify.hpp"
#include "aruco/solve.hpp"
#include "capi_internal.hpp"

namespace {

using aruco::capi::guarded;
using aruco::capi::matrix_of;
using aruco::capi::points_of;
using aruco::capi::quad_of;
using aruco::capi::set_error;
using aruco::capi::write_points;

/// Einen Ausgabezeiger pruefen, bevor irgendetwas gerechnet wird.
///
/// Ohne das schriebe ein NULL-Zeiger erst NACH dem teuren Teil ins Nichts. Das
/// ist auf einem Telefon der Unterschied zwischen einer Meldung und einem
/// Absturz, den niemand einem fehlenden Puffer zuordnet.
bool missing(const void* pointer, char* error, std::int32_t capacity, const char* what) {
    if (pointer != nullptr) {
        return false;
    }
    set_error(error, capacity, std::string(what) + ": Ausgabepuffer ist NULL");
    return true;
}

/// Eine Homographie in das Ausgabefeld schreiben.
void write_matrix(const aruco::Matrix3& matrix, double* out) {
    for (std::size_t index = 0; index < 9; ++index) {
        out[index] = matrix[index];
    }
}

}  // namespace

extern "C" {

std::int32_t aruco_homography_from_quad(const double* plane_xy8, const double* image_xy8,
                                        double* out9, char* error,
                                        std::int32_t error_capacity) {
    if (missing(out9, error, error_capacity, "aruco_homography_from_quad")) {
        return ARUCO_ERR_ARGUMENT;
    }
    return guarded(error, error_capacity, [&]() -> std::int32_t {
        write_matrix(aruco::homography_from_quad(quad_of(plane_xy8, "plane"),
                                                 quad_of(image_xy8, "image")),
                     out9);
        return ARUCO_OK;
    });
}

std::int32_t aruco_homography_lmeds(const double* plane_xy, const double* image_xy,
                                    std::int32_t count, double* out9, char* error,
                                    std::int32_t error_capacity) {
    if (missing(out9, error, error_capacity, "aruco_homography_lmeds")) {
        return ARUCO_ERR_ARGUMENT;
    }
    return guarded(error, error_capacity, [&]() -> std::int32_t {
        write_matrix(aruco::homography_lmeds(points_of(plane_xy, count, "plane"),
                                             points_of(image_xy, count, "image")),
                     out9);
        return ARUCO_OK;
    });
}

std::int32_t aruco_refine_homography(const double* start9, const double* plane_xy,
                                     const double* image_xy, std::int32_t count, double* out9,
                                     char* error, std::int32_t error_capacity) {
    if (missing(out9, error, error_capacity, "aruco_refine_homography")) {
        return ARUCO_ERR_ARGUMENT;
    }
    return guarded(error, error_capacity, [&]() -> std::int32_t {
        write_matrix(aruco::refine_homography(matrix_of(start9, "start"),
                                              points_of(plane_xy, count, "plane"),
                                              points_of(image_xy, count, "image")),
                     out9);
        return ARUCO_OK;
    });
}

std::int32_t aruco_fit_free(const double* corners_xy, std::int32_t marker_count,
                            double marker_mm, double* out9, double* out_offsets_xy,
                            std::int32_t capacity_points, char* error,
                            std::int32_t error_capacity) {
    if (missing(out9, error, error_capacity, "aruco_fit_free")) {
        return ARUCO_ERR_ARGUMENT;
    }
    if (marker_count <= 0) {
        set_error(error, error_capacity, "aruco_fit_free braucht mindestens einen Marker");
        return ARUCO_ERR_ARGUMENT;
    }
    // Der Versatzpuffer darf NULL sein, wenn es keinen Versatz gibt: bei einem
    // einzigen Marker ist der Anker alles, und ein Aufrufer soll dann keinen
    // Puffer erfinden muessen.
    if (marker_count > 1 &&
        missing(out_offsets_xy, error, error_capacity, "aruco_fit_free (Versaetze)")) {
        return ARUCO_ERR_ARGUMENT;
    }

    return guarded(error, error_capacity, [&]() -> std::int32_t {
        const std::vector<aruco::Point2> corners =
            points_of(corners_xy, marker_count * 4, "corners");

        std::vector<std::array<aruco::Point2, 4>> quads;
        quads.reserve(static_cast<std::size_t>(marker_count));
        for (std::int32_t index = 0; index < marker_count; ++index) {
            const std::size_t base = static_cast<std::size_t>(index) * 4U;
            quads.push_back({corners[base], corners[base + 1U], corners[base + 2U],
                             corners[base + 3U]});
        }

        const aruco::FreeFit fit = aruco::fit_free(quads, marker_mm);
        // Erst die Versaetze, dann die Homographie: reicht der Platz nicht, soll
        // der Aufrufer NICHTS Halbes bekommen. Eine geschriebene Homographie
        // neben abgeschnittenen Versaetzen saehe wie ein Ergebnis aus.
        const std::int32_t written = write_points(fit.offsets, out_offsets_xy, capacity_points,
                                                  error, error_capacity, "aruco_fit_free");
        if (written < 0) {
            return written;
        }
        write_matrix(fit.homography, out9);
        return written;
    });
}

std::int32_t aruco_pose_from_homography(const double* homography9, double focal_px,
                                        std::int32_t width, std::int32_t height, double* out4,
                                        char* error, std::int32_t error_capacity) {
    if (missing(out4, error, error_capacity, "aruco_pose_from_homography")) {
        return ARUCO_ERR_ARGUMENT;
    }
    return guarded(error, error_capacity, [&]() -> std::int32_t {
        const aruco::Pose pose = aruco::pose_from_homography(
            matrix_of(homography9, "homography"), focal_px, width, height);
        out4[0] = pose.height_mm;
        out4[1] = pose.nadir_mm.x;
        out4[2] = pose.nadir_mm.y;
        out4[3] = pose.tilt_deg;
        return ARUCO_OK;
    });
}

std::int32_t aruco_plane_extent(const double* homography9, std::int32_t width,
                                std::int32_t height, const double* hull_xy,
                                std::int32_t hull_count, double* out4, char* error,
                                std::int32_t error_capacity) {
    if (missing(out4, error, error_capacity, "aruco_plane_extent")) {
        return ARUCO_ERR_ARGUMENT;
    }
    return guarded(error, error_capacity, [&]() -> std::int32_t {
        const aruco::Extent area =
            aruco::plane_extent(matrix_of(homography9, "homography"), width, height,
                                points_of(hull_xy, hull_count, "hull"));
        out4[0] = area.x0;
        out4[1] = area.y0;
        out4[2] = area.x1;
        out4[3] = area.y1;
        return ARUCO_OK;
    });
}

std::int32_t aruco_convex_hull(const double* points_xy, std::int32_t count, double* out_xy,
                               std::int32_t capacity_points, char* error,
                               std::int32_t error_capacity) {
    if (missing(out_xy, error, error_capacity, "aruco_convex_hull")) {
        return ARUCO_ERR_ARGUMENT;
    }
    return guarded(error, error_capacity, [&]() -> std::int32_t {
        return write_points(aruco::convex_hull(points_of(points_xy, count, "points")), out_xy,
                            capacity_points, error, error_capacity, "aruco_convex_hull");
    });
}

std::int32_t aruco_convex_intersection_area(const double* first_xy, std::int32_t first_count,
                                            const double* second_xy, std::int32_t second_count,
                                            double* out_area, char* error,
                                            std::int32_t error_capacity) {
    if (missing(out_area, error, error_capacity, "aruco_convex_intersection_area")) {
        return ARUCO_ERR_ARGUMENT;
    }
    return guarded(error, error_capacity, [&]() -> std::int32_t {
        *out_area = aruco::convex_intersection_area(points_of(first_xy, first_count, "first"),
                                                    points_of(second_xy, second_count, "second"));
        return ARUCO_OK;
    });
}

std::int32_t aruco_local_px_per_mm(const double* homography9, double x_mm, double y_mm,
                                   double* out_px_per_mm, char* error,
                                   std::int32_t error_capacity) {
    if (missing(out_px_per_mm, error, error_capacity, "aruco_local_px_per_mm")) {
        return ARUCO_ERR_ARGUMENT;
    }
    return guarded(error, error_capacity, [&]() -> std::int32_t {
        *out_px_per_mm = aruco::local_px_per_mm(matrix_of(homography9, "homography"),
                                                aruco::Point2{x_mm, y_mm});
        return ARUCO_OK;
    });
}

std::int32_t aruco_quad_area(const double* quad_xy8, double* out_area, char* error,
                             std::int32_t error_capacity) {
    if (missing(out_area, error, error_capacity, "aruco_quad_area")) {
        return ARUCO_ERR_ARGUMENT;
    }
    return guarded(error, error_capacity, [&]() -> std::int32_t {
        *out_area = aruco::quad_area(quad_of(quad_xy8, "quad"));
        return ARUCO_OK;
    });
}

std::int32_t aruco_output_size(double x0, double y0, double x1, double y1, double px_per_mm,
                               std::int32_t* out_width, std::int32_t* out_height, char* error,
                               std::int32_t error_capacity) {
    if (missing(out_width, error, error_capacity, "aruco_output_size") ||
        missing(out_height, error, error_capacity, "aruco_output_size")) {
        return ARUCO_ERR_ARGUMENT;
    }
    return guarded(error, error_capacity, [&]() -> std::int32_t {
        int width = 0;
        int height = 0;
        aruco::output_size(aruco::Extent{x0, y0, x1, y1}, px_per_mm, width, height);
        *out_width = width;
        *out_height = height;
        return ARUCO_OK;
    });
}

}  // extern "C"
