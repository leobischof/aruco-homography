// pybind11-Bindung: das Python-Modul `aruco_core`.
//
// Die Bindung ist bewusst duenn. Sie uebersetzt numpy-Arrays in die
// ziel-neutralen Typen des Kerns und zurueck - mehr nicht. Alles, was rechnet,
// steht in core/src/, damit Android und WASM dieselbe Rechnung bekommen und
// nicht eine, die zufaellig in der Python-Bindung wohnt.
//
// Kein Kopieren, wo es sich vermeiden laesst: Bilder werden an Ort und Stelle
// gelesen. Ein 12-MP-Foto sind 36 MB; eine Kopie je Aufruf waere in der
// Vorschau-Schleife spuerbar.

#include <array>
#include <cstring>
#include <string>
#include <vector>

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "aruco/camera.hpp"
#include "aruco/constants.hpp"
#include "aruco/contour.hpp"
#include "aruco/detect.hpp"
#include "aruco/enhance.hpp"
#include "aruco/extent.hpp"
#include "aruco/geometry.hpp"
#include "aruco/rectify.hpp"
#include "aruco/solve.hpp"

namespace py = pybind11;

namespace {

using DoubleArray = py::array_t<double, py::array::c_style | py::array::forcecast>;

/// Ein numpy-Array als ImageView lesen, ohne es zu kopieren.
///
/// Verlangt uint8 und zeilenweise dichte Daten - genau das, was cv2 liefert.
/// Alles andere wird abgewiesen statt stillschweigend umgedeutet: ein Array mit
/// vertauschten Achsen laese sich zwar irgendwie interpretieren, und das
/// Ergebnis waere eine Messung an einem Bild, das so niemand gemeint hat.
aruco::ImageView view_of(const py::array& array) {
    // ValueError und nicht TypeError, so wie die Python-Referenz es tut
    // (app/vision/enhance.py::_require_bgr8 wirft ValueError fuer Datentyp UND
    // Form). Der Umschalter tauscht die Rechnung aus, nicht den Vertrag - ein
    // Aufrufer, der `except ValueError` schreibt, darf nicht davon abhaengen,
    // welcher Kern gerade laeuft. tests/test_enhance.py besteht darauf.
    if (!array.dtype().is(py::dtype::of<std::uint8_t>())) {
        throw py::value_error("Der Kern erwartet ein uint8-Array");
    }
    const py::ssize_t dimensions = array.ndim();
    if (dimensions != 2 && dimensions != 3) {
        throw py::value_error("Der Kern erwartet (H,W) oder (H,W,C)");
    }

    const py::ssize_t height = array.shape(0);
    const py::ssize_t width = array.shape(1);
    const py::ssize_t channels = dimensions == 3 ? array.shape(2) : 1;
    if (channels != 1 && channels != 3) {
        throw py::value_error("Der Kern erwartet 1 (grau) oder 3 (BGR) Kanaele");
    }

    // Schrittweiten stehen in numpy in BYTES. Eine Zeile muss dicht liegen; die
    // Zeilen untereinander duerfen Luecken haben (ein Ausschnitt eines groesseren
    // Bildes tut genau das) - dafuer gibt es ImageView::stride.
    if (array.strides(dimensions - 1) != 1) {
        throw py::value_error("Der Kern erwartet dichte Pixel");
    }
    if (dimensions == 3 && array.strides(1) != channels) {
        throw py::value_error("Der Kern erwartet dichte Bildzeilen");
    }
    if (dimensions == 2 && array.strides(1) != 1) {
        throw py::value_error("Der Kern erwartet dichte Bildzeilen");
    }
    if (array.strides(0) < width * channels) {
        throw py::value_error("Der Kern erwartet aufsteigende Zeilen");
    }

    aruco::ImageView image;
    image.data = static_cast<const std::uint8_t*>(array.data());
    image.width = static_cast<int>(width);
    image.height = static_cast<int>(height);
    image.stride = static_cast<int>(array.strides(0));
    image.channels = static_cast<int>(channels);
    return image;
}

py::array_t<std::uint8_t> array_of(const aruco::ImageBuffer& buffer) {
    py::array_t<std::uint8_t> array(
        {static_cast<py::ssize_t>(buffer.height), static_cast<py::ssize_t>(buffer.width),
         static_cast<py::ssize_t>(buffer.channels)});
    std::memcpy(array.mutable_data(), buffer.data.data(), buffer.data.size());
    return array;
}

/// (N,2)-Array in Punkte. Wirft, wenn die Form nicht stimmt - eine geratene
/// Deutung waere hier eine gespiegelte Schablone.
std::vector<aruco::Point2> points_of(const DoubleArray& array, const char* what) {
    if (array.ndim() != 2 || array.shape(1) != 2) {
        throw py::value_error(std::string(what) + " erwartet ein (N,2)-Array");
    }
    const py::ssize_t count = array.shape(0);
    const double* data = array.data();
    std::vector<aruco::Point2> points;
    points.reserve(static_cast<std::size_t>(count));
    for (py::ssize_t index = 0; index < count; ++index) {
        points.push_back(aruco::Point2{data[2 * index], data[2 * index + 1]});
    }
    return points;
}

DoubleArray array_of(const std::vector<aruco::Point2>& points) {
    DoubleArray array({static_cast<py::ssize_t>(points.size()), static_cast<py::ssize_t>(2)});
    double* data = array.mutable_data();
    for (std::size_t index = 0; index < points.size(); ++index) {
        data[2 * index] = points[index].x;
        data[2 * index + 1] = points[index].y;
    }
    return array;
}

std::array<aruco::Point2, 4> quad_of(const DoubleArray& array, const char* what) {
    const std::vector<aruco::Point2> points = points_of(array, what);
    if (points.size() != 4) {
        throw py::value_error(std::string(what) + " erwartet genau vier Ecken");
    }
    return {points[0], points[1], points[2], points[3]};
}

aruco::Matrix3 matrix_of(const DoubleArray& array, const char* what) {
    if (array.ndim() != 2 || array.shape(0) != 3 || array.shape(1) != 3) {
        throw py::value_error(std::string(what) + " erwartet eine (3,3)-Matrix");
    }
    const double* data = array.data();
    aruco::Matrix3 matrix{};
    for (std::size_t index = 0; index < 9; ++index) {
        matrix[index] = data[index];
    }
    return matrix;
}

DoubleArray array_of(const aruco::Matrix3& matrix) {
    DoubleArray array({static_cast<py::ssize_t>(3), static_cast<py::ssize_t>(3)});
    std::memcpy(array.mutable_data(), matrix.data(), sizeof(double) * matrix.size());
    return array;
}

py::list detect_markers(const py::array& array, bool enhance_contrast) {
    const aruco::ImageView image = view_of(array);

    std::vector<aruco::Marker> markers;
    {
        // Der Detektor braucht kein Python. Die GIL freizugeben laesst einen
        // zweiten Faden weiterarbeiten - cv2 macht es an derselben Stelle
        // genauso. Das Array bleibt am Leben, weil der Aufrufer es haelt.
        py::gil_scoped_release unlocked;
        markers = aruco::detect_markers(image, enhance_contrast);
    }

    py::list found;
    for (const aruco::Marker& marker : markers) {
        py::array_t<double> corners({static_cast<py::ssize_t>(4), static_cast<py::ssize_t>(2)});
        std::memcpy(corners.mutable_data(), marker.corners, sizeof(marker.corners));
        found.append(py::make_tuple(marker.id, std::move(corners)));
    }
    return found;
}

py::tuple fit_free(const DoubleArray& quads, double marker_mm) {
    if (quads.ndim() != 3 || quads.shape(1) != 4 || quads.shape(2) != 2) {
        throw py::value_error("fit_free erwartet ein (M,4,2)-Array");
    }
    const py::ssize_t count = quads.shape(0);
    const double* data = quads.data();

    std::vector<std::array<aruco::Point2, 4>> markers;
    markers.reserve(static_cast<std::size_t>(count));
    for (py::ssize_t index = 0; index < count; ++index) {
        std::array<aruco::Point2, 4> quad{};
        for (std::size_t corner = 0; corner < 4; ++corner) {
            const std::size_t base = static_cast<std::size_t>(index) * 8 + corner * 2;
            quad[corner] = aruco::Point2{data[base], data[base + 1]};
        }
        markers.push_back(quad);
    }

    const aruco::FreeFit fit = aruco::fit_free(markers, marker_mm);
    return py::make_tuple(array_of(fit.homography), array_of(fit.offsets));
}

py::tuple pose_from_homography(const DoubleArray& homography, double focal_px, int width,
                               int height) {
    const aruco::Pose pose = aruco::pose_from_homography(
        matrix_of(homography, "pose_from_homography"), focal_px, width, height);
    return py::make_tuple(pose.height_mm,
                          py::make_tuple(pose.nadir_mm.x, pose.nadir_mm.y), pose.tilt_deg);
}

py::tuple plane_extent(const DoubleArray& homography, int width, int height,
                       const DoubleArray& hull) {
    const aruco::Extent extent =
        aruco::plane_extent(matrix_of(homography, "plane_extent"), width, height,
                            points_of(hull, "plane_extent"));
    return py::make_tuple(extent.x0, extent.y0, extent.x1, extent.y1);
}

double local_px_per_mm(const DoubleArray& homography, const DoubleArray& point) {
    if (point.size() != 2) {
        throw py::value_error("local_px_per_mm erwartet einen Punkt mit zwei Werten");
    }
    const double* data = point.data();
    return aruco::local_px_per_mm(matrix_of(homography, "local_px_per_mm"),
                                  aruco::Point2{data[0], data[1]});
}

py::array_t<std::uint8_t> rectify(const py::array& image, const DoubleArray& homography,
                                  double x0, double y0, double x1, double y1, double px_per_mm,
                                  double source_px_per_mm) {
    const aruco::ImageView view = view_of(image);
    const aruco::Matrix3 matrix = matrix_of(homography, "rectify");
    aruco::ImageBuffer buffer;
    {
        py::gil_scoped_release unlocked;
        buffer = aruco::rectify(view, matrix, aruco::Extent{x0, y0, x1, y1}, px_per_mm,
                                source_px_per_mm);
    }
    return array_of(buffer);
}

py::tuple output_size(double x0, double y0, double x1, double y1, double px_per_mm) {
    int width = 0;
    int height = 0;
    aruco::output_size(aruco::Extent{x0, y0, x1, y1}, px_per_mm, width, height);
    return py::make_tuple(width, height);
}

py::array_t<std::uint8_t> adjust(const py::array& image, bool grayscale, bool invert,
                                 double brightness, double contrast, double saturation,
                                 double local_contrast, double edge_boost, double edge_overlay,
                                 const std::string& color_emphasis, double emphasis_strength,
                                 double threshold) {
    const aruco::ImageView view = view_of(image);
    aruco::AdjustOptions options;
    options.grayscale = grayscale;
    options.invert = invert;
    options.brightness = brightness;
    options.contrast = contrast;
    options.saturation = saturation;
    options.local_contrast = local_contrast;
    options.edge_boost = edge_boost;
    options.edge_overlay = edge_overlay;
    options.color_emphasis = color_emphasis;
    options.emphasis_strength = emphasis_strength;
    options.threshold = threshold;

    aruco::ImageBuffer buffer;
    {
        py::gil_scoped_release unlocked;
        buffer = aruco::adjust(view, options);
    }
    return array_of(buffer);
}

py::object find_contour_mm(const py::array& image, double px_per_mm) {
    const aruco::ImageView view = view_of(image);
    std::vector<aruco::Point2> polygon;
    {
        py::gil_scoped_release unlocked;
        polygon = aruco::find_contour_mm(view, px_per_mm);
    }
    if (polygon.empty()) {
        return py::none();
    }
    return array_of(polygon);
}

}  // namespace

PYBIND11_MODULE(aruco_core, module) {
    module.doc() =
        "Der C++-Rechenkern von ArUco-Homographie. Aktiviert wird er ueber "
        "ARUCO_CORE=cpp (app/vision/backend.py).";

    // Damit die Python-Seite pruefen kann, dass die erzeugten Konstanten wirklich
    // aus shared/constants.json kommen und nicht aus einem alten Bau
    // (tests/test_backend.py). Ein Kern mit veralteten Konstanten misst falsch
    // und sagt es nicht.
    module.attr("ARUCO_DICT_NAME") = std::string(aruco::constants::ARUCO_DICT_NAME);
    module.attr("MARKER_MM_NOMINAL") = aruco::constants::MARKER_MM_NOMINAL;

    module.def("detect_markers", &detect_markers, py::arg("image"),
               py::arg("enhance_contrast") = true,
               "Marker finden. Nimmt ein uint8-Array (H,W,3) in BGR oder (H,W) grau "
               "und gibt [(id, (4,2)-float64-Ecken)] zurueck, nach ID sortiert.");

    module.def(
        "homography_from_quad",
        [](const DoubleArray& plane, const DoubleArray& image) {
            return array_of(aruco::homography_from_quad(quad_of(plane, "homography_from_quad"),
                                                        quad_of(image, "homography_from_quad")));
        },
        py::arg("plane"), py::arg("image"),
        "Homographie aus genau vier Punktpaaren (getPerspectiveTransform).");

    module.def(
        "homography_lmeds",
        [](const DoubleArray& plane, const DoubleArray& image) {
            return array_of(aruco::homography_lmeds(points_of(plane, "homography_lmeds"),
                                                    points_of(image, "homography_lmeds")));
        },
        py::arg("plane"), py::arg("image"),
        "Homographie aus vielen Punktpaaren, robust (findHomography, LMEDS).");

    module.def(
        "refine_homography",
        [](const DoubleArray& start, const DoubleArray& plane, const DoubleArray& image) {
            return array_of(aruco::refine_homography(matrix_of(start, "refine_homography"),
                                                     points_of(plane, "refine_homography"),
                                                     points_of(image, "refine_homography")));
        },
        py::arg("start"), py::arg("plane"), py::arg("image"),
        "Nichtlinearer Ausgleich des Reprojektionsfehlers ueber die 8 freien Parameter.");

    module.def("fit_free", &fit_free, py::arg("quads"), py::arg("marker_mm"),
               "Frei-Modus: Homographie und Markerversaetze gemeinsam schaetzen. "
               "Die Marker muessen absteigend nach Bildflaeche sortiert sein.");

    module.def("pose_from_homography", &pose_from_homography, py::arg("homography"),
               py::arg("focal_px"), py::arg("width"), py::arg("height"),
               "Zerlegt H und gibt (Hoehe_mm, (Lotpunkt_x, Lotpunkt_y), Neigung_grad).");

    module.def("plane_extent", &plane_extent, py::arg("homography"), py::arg("width"),
               py::arg("height"), py::arg("hull_mm"),
               "Bounding-Box des abbildbaren Ebenenbereichs als (x0, y0, x1, y1).");

    module.def(
        "convex_hull",
        [](const DoubleArray& points) {
            return array_of(aruco::convex_hull(points_of(points, "convex_hull")));
        },
        py::arg("points"), "Konvexe Huelle als (N,2)-Array.");

    module.def(
        "convex_intersection_area",
        [](const DoubleArray& first, const DoubleArray& second) {
            return aruco::convex_intersection_area(points_of(first, "convex_intersection_area"),
                                                   points_of(second, "convex_intersection_area"));
        },
        py::arg("first"), py::arg("second"), "Flaeche des Schnitts zweier konvexer Polygone.");

    module.def("local_px_per_mm", &local_px_per_mm, py::arg("homography"), py::arg("point_mm"),
               "Lokaler Abbildungsmassstab Ebene -> Bild an einer Stelle.");

    module.def(
        "quad_area",
        [](const DoubleArray& quad) { return aruco::quad_area(quad_of(quad, "quad_area")); },
        py::arg("quad"), "Bildflaeche eines Markervierecks (contourArea auf float32-Ecken).");

    module.def("rectify", &rectify, py::arg("image"), py::arg("homography"), py::arg("x0"),
               py::arg("y0"), py::arg("x1"), py::arg("y1"), py::arg("px_per_mm"),
               py::arg("source_px_per_mm") = 0.0,
               "Entzerrt den Zuschnitt in ein Raster mit genau px_per_mm Pixeln je mm.");

    module.def("output_size", &output_size, py::arg("x0"), py::arg("y0"), py::arg("x1"),
               py::arg("y1"), py::arg("px_per_mm"),
               "Rastergroesse (Breite, Hoehe) fuer einen Zuschnitt.");

    module.def("adjust", &adjust, py::arg("image"), py::arg("grayscale") = false,
               py::arg("invert") = false, py::arg("brightness") = 0.0, py::arg("contrast") = 0.0,
               py::arg("saturation") = 0.0, py::arg("local_contrast") = 0.0,
               py::arg("edge_boost") = 0.0, py::arg("edge_overlay") = 0.0,
               py::arg("color_emphasis") = std::string("none"),
               py::arg("emphasis_strength") = 0.0, py::arg("threshold") = 0.0,
               "Kosmetische Aufbereitung eines entzerrten BGR-Bildes.");

    module.def("find_contour_mm", &find_contour_mm, py::arg("image"), py::arg("px_per_mm"),
               "Groesste plausible Aussenkontur als (N,2)-Array in mm, sonst None.");
}
