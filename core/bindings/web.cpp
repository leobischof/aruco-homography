// embind-Bindung: der Rechenkern als ES-Modul fuer den Browser.
//
// Das Gegenstueck zu bindings/python.cpp, und genauso duenn. Sie uebersetzt
// Typenfelder (Float64Array, Uint8Array) in die ziel-neutralen Typen des Kerns
// und zurueck; gerechnet wird ausschliesslich in core/src/.
//
// DREI DINGE, die hier anders sind als in Python, und jedes hat einen Grund:
//
// 1. **Bilder kommen als Zeiger, nicht als Objekt.** Der Aufrufer legt sie mit
//    `Module._malloc` in den Haldenspeicher und schreibt sie mit `HEAPU8.set()`
//    hinein. Ein `val` je Pixel waere eine Kopie durch die JavaScript-Grenze,
//    und ein Handyfoto sind 36 MB.
//
// 2. **Ergebnisbilder sind ein Objekt mit `delete()`.** Emscripten hat keinen
//    Sammler: was hier entsteht, muss der Aufrufer freigeben. Ein `Raster`, das
//    niemand loescht, ist in einer Schleife ueber mehrere Fotos ein Absturz.
//
// 3. **`data()` ist eine SICHT auf den Haldenspeicher, keine Kopie.** Sie gilt
//    nur bis zur naechsten Speicheranforderung: mit ALLOW_MEMORY_GROWTH tauscht
//    Emscripten den ArrayBuffer aus, und alle vorher gereichten Sichten zeigen
//    dann ins Leere. Der Aufrufer kopiert sie deshalb sofort - web/vision/core.js
//    tut genau das und ist die einzige Stelle, die diese Regel kennen muss.

#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

#include <emscripten/bind.h>
#include <emscripten/val.h>

#include "aruco/camera.hpp"
#include "aruco/constants.hpp"
#include "aruco/contour.hpp"
#include "aruco/detect.hpp"
#include "aruco/enhance.hpp"
#include "aruco/extent.hpp"
#include "aruco/geometry.hpp"
#include "aruco/markers.hpp"
#include "aruco/rectify.hpp"
#include "aruco/solve.hpp"

using emscripten::val;

namespace {

/// Ein Ergebnisbild, das dem JavaScript gehoert - und das es freigeben muss.
class Raster {
public:
    explicit Raster(aruco::ImageBuffer&& buffer) : buffer_(std::move(buffer)) {}

    int width() const { return buffer_.width; }
    int height() const { return buffer_.height; }
    int channels() const { return buffer_.channels; }

    /// Sicht auf die Pixel. Sofort kopieren - siehe Kopf dieser Datei.
    val data() const {
        return val(emscripten::typed_memory_view(buffer_.data.size(), buffer_.data.data()));
    }

private:
    aruco::ImageBuffer buffer_;
};

/// Ein Pixelpuffer im Haldenspeicher als ImageView.
///
/// Der Zeiger kommt als `uintptr_t` durch die Bindung, weil embind keine rohen
/// Zeiger kennt. Wer hier eine falsche Zahl hineingibt, liest fremden Speicher -
/// deshalb ist das die einzige Stelle, an der JavaScript rechnen muss, und
/// web/vision/core.js kapselt sie vollstaendig.
aruco::ImageView view_of(std::uintptr_t data, int width, int height, int stride, int channels) {
    aruco::ImageView image;
    image.data = reinterpret_cast<const std::uint8_t*>(data);
    image.width = width;
    image.height = height;
    image.stride = stride;
    image.channels = channels;
    return image;
}

std::vector<aruco::Point2> points_of(const val& array, const char* what) {
    const std::vector<double> flat = emscripten::convertJSArrayToNumberVector<double>(array);
    if (flat.size() % 2 != 0) {
        throw std::invalid_argument(std::string(what) +
                                    " erwartet eine gerade Anzahl Koordinaten (x,y,x,y,...)");
    }
    std::vector<aruco::Point2> points;
    points.reserve(flat.size() / 2);
    for (std::size_t index = 0; index + 1 < flat.size(); index += 2) {
        points.push_back(aruco::Point2{flat[index], flat[index + 1]});
    }
    return points;
}

std::array<aruco::Point2, 4> quad_of(const val& array, const char* what) {
    const std::vector<aruco::Point2> points = points_of(array, what);
    if (points.size() != 4) {
        throw std::invalid_argument(std::string(what) + " erwartet genau vier Ecken");
    }
    return {points[0], points[1], points[2], points[3]};
}

aruco::Matrix3 matrix_of(const val& array, const char* what) {
    const std::vector<double> flat = emscripten::convertJSArrayToNumberVector<double>(array);
    if (flat.size() != 9) {
        throw std::invalid_argument(std::string(what) +
                                    " erwartet eine Homographie aus neun Zahlen");
    }
    aruco::Matrix3 matrix{};
    for (std::size_t index = 0; index < 9; ++index) {
        matrix[index] = flat[index];
    }
    return matrix;
}

/// Zahlen als Float64Array zurueck. Kopiert - eine Sicht wuerde den Aufruf nicht
/// ueberleben, weil der Vektor am Ende der Funktion stirbt.
val numbers(const std::vector<double>& values) {
    const val view(emscripten::typed_memory_view(values.size(), values.data()));
    val copy = val::global("Float64Array").new_(values.size());
    copy.call<void>("set", view);
    return copy;
}

val numbers(const std::vector<aruco::Point2>& points) {
    std::vector<double> flat;
    flat.reserve(points.size() * 2);
    for (const aruco::Point2& point : points) {
        flat.push_back(point.x);
        flat.push_back(point.y);
    }
    return numbers(flat);
}

val numbers(const aruco::Matrix3& matrix) {
    return numbers(std::vector<double>(matrix.begin(), matrix.end()));
}

double field(const val& options, const char* name, double fallback) {
    const val value = options[name];
    if (value.isUndefined() || value.isNull()) {
        return fallback;
    }
    return value.as<double>();
}

bool flag(const val& options, const char* name) {
    const val value = options[name];
    return !(value.isUndefined() || value.isNull()) && value.as<bool>();
}

// --- Die Bindung selbst ------------------------------------------------------

val detect_markers(std::uintptr_t data, int width, int height, int stride, int channels,
                   bool enhance_contrast) {
    const std::vector<aruco::Marker> markers =
        aruco::detect_markers(view_of(data, width, height, stride, channels), enhance_contrast);

    val found = val::array();
    for (const aruco::Marker& marker : markers) {
        std::vector<double> corners;
        corners.reserve(8);
        for (const auto& corner : marker.corners) {
            corners.push_back(corner[0]);
            corners.push_back(corner[1]);
        }
        val entry = val::object();
        entry.set("id", marker.id);
        entry.set("corners", numbers(corners));
        found.call<void>("push", entry);
    }
    return found;
}

val homography_from_quad(const val& plane, const val& image) {
    return numbers(aruco::homography_from_quad(quad_of(plane, "homographyFromQuad"),
                                               quad_of(image, "homographyFromQuad")));
}

val homography_lmeds(const val& plane, const val& image) {
    return numbers(aruco::homography_lmeds(points_of(plane, "homographyLmeds"),
                                           points_of(image, "homographyLmeds")));
}

val refine_homography(const val& start, const val& plane, const val& image) {
    return numbers(aruco::refine_homography(matrix_of(start, "refineHomography"),
                                            points_of(plane, "refineHomography"),
                                            points_of(image, "refineHomography")));
}

val fit_free(const val& quads, double marker_mm) {
    const std::vector<aruco::Point2> corners = points_of(quads, "fitFree");
    if (corners.empty() || corners.size() % 4 != 0) {
        throw std::invalid_argument("fitFree erwartet vier Ecken je Marker");
    }

    std::vector<std::array<aruco::Point2, 4>> markers;
    markers.reserve(corners.size() / 4);
    for (std::size_t index = 0; index < corners.size(); index += 4) {
        markers.push_back({corners[index], corners[index + 1], corners[index + 2],
                           corners[index + 3]});
    }

    const aruco::FreeFit fit = aruco::fit_free(markers, marker_mm);
    val result = val::object();
    result.set("homography", numbers(fit.homography));
    result.set("offsets", numbers(fit.offsets));
    return result;
}

val pose_from_homography(const val& homography, double focal_px, int width, int height) {
    const aruco::Pose pose = aruco::pose_from_homography(
        matrix_of(homography, "poseFromHomography"), focal_px, width, height);
    val result = val::object();
    result.set("heightMm", pose.height_mm);
    result.set("nadirMm", numbers(std::vector<double>{pose.nadir_mm.x, pose.nadir_mm.y}));
    result.set("tiltDeg", pose.tilt_deg);
    return result;
}

val plane_extent(const val& homography, int width, int height, const val& hull) {
    const aruco::Extent extent = aruco::plane_extent(matrix_of(homography, "planeExtent"), width,
                                                     height, points_of(hull, "planeExtent"));
    return numbers(std::vector<double>{extent.x0, extent.y0, extent.x1, extent.y1});
}

val convex_hull(const val& points) {
    return numbers(aruco::convex_hull(points_of(points, "convexHull")));
}

double convex_intersection_area(const val& first, const val& second) {
    return aruco::convex_intersection_area(points_of(first, "convexIntersectionArea"),
                                           points_of(second, "convexIntersectionArea"));
}

double local_px_per_mm(const val& homography, double x, double y) {
    return aruco::local_px_per_mm(matrix_of(homography, "localPxPerMm"), aruco::Point2{x, y});
}

double quad_area(const val& quad) { return aruco::quad_area(quad_of(quad, "quadArea")); }

val output_size(double x0, double y0, double x1, double y1, double px_per_mm) {
    int width = 0;
    int height = 0;
    aruco::output_size(aruco::Extent{x0, y0, x1, y1}, px_per_mm, width, height);
    val result = val::object();
    result.set("width", width);
    result.set("height", height);
    return result;
}

Raster* rectify(std::uintptr_t data, int width, int height, int stride, int channels,
                const val& homography, double x0, double y0, double x1, double y1,
                double px_per_mm, double source_px_per_mm) {
    aruco::ImageBuffer buffer =
        aruco::rectify(view_of(data, width, height, stride, channels),
                       matrix_of(homography, "rectify"), aruco::Extent{x0, y0, x1, y1}, px_per_mm,
                       source_px_per_mm);
    return new Raster(std::move(buffer));
}

Raster* adjust(std::uintptr_t data, int width, int height, int stride, int channels,
               const val& options) {
    aruco::AdjustOptions settings;
    settings.grayscale = flag(options, "grayscale");
    settings.invert = flag(options, "invert");
    settings.brightness = field(options, "brightness", 0.0);
    settings.contrast = field(options, "contrast", 0.0);
    settings.saturation = field(options, "saturation", 0.0);
    settings.local_contrast = field(options, "localContrast", 0.0);
    settings.edge_boost = field(options, "edgeBoost", 0.0);
    settings.edge_overlay = field(options, "edgeOverlay", 0.0);
    settings.emphasis_strength = field(options, "emphasisStrength", 0.0);
    settings.threshold = field(options, "threshold", 0.0);

    const val emphasis = options["colorEmphasis"];
    settings.color_emphasis =
        (emphasis.isUndefined() || emphasis.isNull()) ? "none" : emphasis.as<std::string>();

    aruco::ImageBuffer buffer =
        aruco::adjust(view_of(data, width, height, stride, channels), settings);
    return new Raster(std::move(buffer));
}

bool is_identity(const val& options) {
    aruco::AdjustOptions settings;
    settings.grayscale = flag(options, "grayscale");
    settings.invert = flag(options, "invert");
    settings.brightness = field(options, "brightness", 0.0);
    settings.contrast = field(options, "contrast", 0.0);
    settings.saturation = field(options, "saturation", 0.0);
    settings.local_contrast = field(options, "localContrast", 0.0);
    settings.edge_boost = field(options, "edgeBoost", 0.0);
    settings.edge_overlay = field(options, "edgeOverlay", 0.0);
    settings.emphasis_strength = field(options, "emphasisStrength", 0.0);
    settings.threshold = field(options, "threshold", 0.0);
    const val emphasis = options["colorEmphasis"];
    settings.color_emphasis =
        (emphasis.isUndefined() || emphasis.isNull()) ? "none" : emphasis.as<std::string>();
    return aruco::is_identity(settings);
}

val find_contour_mm(std::uintptr_t data, int width, int height, int stride, int channels,
                    double px_per_mm) {
    const std::vector<aruco::Point2> polygon =
        aruco::find_contour_mm(view_of(data, width, height, stride, channels), px_per_mm);
    if (polygon.empty()) {
        return val::null();
    }
    return numbers(polygon);
}

/// Die Modulbits eines Markers als Uint8Array - fuer web/pdf/markersheet.js.
///
/// Damit braucht der Browser kein zweites OpenCV mehr: bis hierher holte
/// tools/opencv_markers.mjs sie aus @techstark/opencv-js (13,3 MB), und das war
/// die letzte Stelle, an der die Seite eine fremde WASM-Fassung gebraucht haette.
val marker_bits(int marker_id, int modules) {
    const std::vector<std::uint8_t> bits = aruco::marker_bits(marker_id, modules);
    const val view(emscripten::typed_memory_view(bits.size(), bits.data()));
    val copy = val::global("Uint8Array").new_(bits.size());
    copy.call<void>("set", view);
    return copy;
}

std::string dictionary_name() { return std::string(aruco::constants::ARUCO_DICT_NAME); }

double marker_mm_nominal() { return aruco::constants::MARKER_MM_NOMINAL; }

}  // namespace

EMSCRIPTEN_BINDINGS(aruco_core) {
    emscripten::class_<Raster>("Raster")
        .function("width", &Raster::width)
        .function("height", &Raster::height)
        .function("channels", &Raster::channels)
        .function("data", &Raster::data);

    emscripten::function("detectMarkers", &detect_markers);
    emscripten::function("homographyFromQuad", &homography_from_quad);
    emscripten::function("homographyLmeds", &homography_lmeds);
    emscripten::function("refineHomography", &refine_homography);
    emscripten::function("fitFree", &fit_free);
    emscripten::function("poseFromHomography", &pose_from_homography);
    emscripten::function("planeExtent", &plane_extent);
    emscripten::function("convexHull", &convex_hull);
    emscripten::function("convexIntersectionArea", &convex_intersection_area);
    emscripten::function("localPxPerMm", &local_px_per_mm);
    emscripten::function("quadArea", &quad_area);
    emscripten::function("outputSize", &output_size);
    emscripten::function("rectify", &rectify, emscripten::allow_raw_pointers());
    emscripten::function("adjust", &adjust, emscripten::allow_raw_pointers());
    emscripten::function("isIdentity", &is_identity);
    emscripten::function("findContourMm", &find_contour_mm);
    emscripten::function("markerBits", &marker_bits);

    // Damit die Seite pruefen kann, dass das wasm wirklich aus dieser
    // shared/constants.json gebaut wurde und nicht aus einer aelteren. Ein Kern
    // mit veralteten Konstanten misst falsch und sagt es nicht.
    emscripten::function("dictionaryName", &dictionary_name);
    emscripten::function("markerMmNominal", &marker_mm_nominal);
}
