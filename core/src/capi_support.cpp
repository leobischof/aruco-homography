// Das gemeinsame Innenleben der C-Schnittstelle: Fehlermeldungen und das
// Auspacken flacher Zahlenfelder.
//
// Es steht hier und nicht dreimal in capi.cpp, capi_geometry.cpp und
// capi_image.cpp, weil `points_of` die eine Schleife ist, in der x und y
// vertauscht werden koennten - und ein vertauschtes Paar saehe in jeder
// Einzelzahl richtig aus, verzoege aber jede Homographie, die darauf aufbaut.
// Dieselbe Ueberlegung wie bei der Eckenreihenfolge in aruco/capi.h.

#include "capi_internal.hpp"

namespace aruco {
namespace capi {

void set_error(char* error, std::int32_t capacity, const std::string& text) {
    if (error == nullptr || capacity <= 0) {
        return;
    }
    const std::size_t room = static_cast<std::size_t>(capacity) - 1U;
    const std::size_t length = text.size() < room ? text.size() : room;
    std::memcpy(error, text.data(), length);
    error[length] = '\0';
}

std::vector<Point2> points_of(const double* flat, std::int32_t count, const char* what) {
    if (count < 0) {
        throw std::invalid_argument(std::string(what) + ": negative Punktanzahl");
    }
    if (count > 0 && flat == nullptr) {
        throw std::invalid_argument(std::string(what) + ": Punktfeld ist NULL");
    }
    std::vector<Point2> points;
    points.reserve(static_cast<std::size_t>(count));
    for (std::int32_t index = 0; index < count; ++index) {
        points.push_back(Point2{flat[index * 2], flat[index * 2 + 1]});
    }
    return points;
}

std::array<Point2, 4> quad_of(const double* flat, const char* what) {
    const std::vector<Point2> points = points_of(flat, 4, what);
    return {points[0], points[1], points[2], points[3]};
}

Matrix3 matrix_of(const double* flat, const char* what) {
    if (flat == nullptr) {
        throw std::invalid_argument(std::string(what) + ": Homographie ist NULL");
    }
    Matrix3 matrix{};
    for (std::size_t index = 0; index < 9; ++index) {
        matrix[index] = flat[index];
    }
    return matrix;
}

std::int32_t write_points(const std::vector<Point2>& points, double* out,
                          std::int32_t capacity_points, char* error,
                          std::int32_t error_capacity, const char* what) {
    if (points.empty()) {
        return 0;
    }
    if (out == nullptr || static_cast<std::size_t>(capacity_points) < points.size()) {
        set_error(error, error_capacity,
                  std::string(what) + ": Ausgabepuffer zu klein - " +
                      std::to_string(points.size()) + " Punkte, Platz fuer " +
                      std::to_string(capacity_points));
        return ARUCO_ERR_CAPACITY;
    }
    for (std::size_t index = 0; index < points.size(); ++index) {
        out[index * 2] = points[index].x;
        out[index * 2 + 1] = points[index].y;
    }
    return static_cast<std::int32_t>(points.size());
}

ImageView view_of(const std::uint8_t* data, std::int32_t width, std::int32_t height,
                  std::int32_t stride, std::int32_t channels) {
    ImageView image;
    image.data = data;
    image.width = width;
    image.height = height;
    image.stride = stride;
    image.channels = channels;
    return image;
}

AdjustOptions settings_of(const aruco_adjust_options* options) {
    AdjustOptions settings;
    if (options == nullptr) {
        return settings;  // die Vorgaben aus enhance.hpp sind bereits neutral
    }
    settings.grayscale = options->grayscale != 0;
    settings.invert = options->invert != 0;
    settings.brightness = options->brightness;
    settings.contrast = options->contrast;
    settings.saturation = options->saturation;
    settings.local_contrast = options->local_contrast;
    settings.edge_boost = options->edge_boost;
    settings.edge_overlay = options->edge_overlay;
    settings.emphasis_strength = options->emphasis_strength;
    settings.threshold = options->threshold;
    // Ein NULL-Zeiger heisst "none" und nicht "leerer Name": ein leerer Name
    // faende keine Farbe, und die Betonung bliebe stumm aus. Dasselbe Ergebnis,
    // aber aus dem falschen Grund - und der naechste Leser suchte den Fehler in
    // der Farbtabelle.
    settings.color_emphasis =
        options->color_emphasis == nullptr ? std::string("none")
                                           : std::string(options->color_emphasis);
    return settings;
}

}  // namespace capi
}  // namespace aruco
