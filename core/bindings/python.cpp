// pybind11-Bindung: das Python-Modul `aruco_core`.
//
// Die Bindung ist bewusst duenn. Sie uebersetzt ein numpy-Array in eine
// ImageView und Marker in (ID, Ecken) - mehr nicht. Alles, was rechnet, steht in
// core/src/, damit Android und WASM spaeter dieselbe Rechnung bekommen und nicht
// eine, die zufaellig in der Python-Bindung wohnt.
//
// Kein Kopieren: das numpy-Array wird an Ort und Stelle gelesen. Ein 12-MP-Foto
// sind 36 MB; eine Kopie je Aufruf waere in der Vorschau-Schleife spuerbar.

#include <cstring>
#include <string>
#include <vector>

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

#include "aruco/constants.hpp"
#include "aruco/detect.hpp"

namespace py = pybind11;

namespace {

/// Ein numpy-Array als ImageView lesen, ohne es zu kopieren.
///
/// Verlangt uint8 und zeilenweise dichte Daten - genau das, was cv2 liefert.
/// Alles andere wird abgewiesen statt stillschweigend umgedeutet: ein Array mit
/// vertauschten Achsen laese sich zwar irgendwie interpretieren, und das
/// Ergebnis waere eine Messung an einem Bild, das so niemand gemeint hat.
aruco::ImageView view_of(const py::array& array) {
    if (!array.dtype().is(py::dtype::of<std::uint8_t>())) {
        throw py::type_error("aruco_core.detect_markers erwartet ein uint8-Array");
    }
    const py::ssize_t dimensions = array.ndim();
    if (dimensions != 2 && dimensions != 3) {
        throw py::value_error("aruco_core.detect_markers erwartet (H,W) oder (H,W,C)");
    }

    const py::ssize_t height = array.shape(0);
    const py::ssize_t width = array.shape(1);
    const py::ssize_t channels = dimensions == 3 ? array.shape(2) : 1;
    if (channels != 1 && channels != 3) {
        throw py::value_error("aruco_core.detect_markers erwartet 1 (grau) oder 3 (BGR) Kanaele");
    }

    // Schrittweiten stehen in numpy in BYTES. Eine Zeile muss dicht liegen; die
    // Zeilen untereinander duerfen Luecken haben (ein Ausschnitt eines groesseren
    // Bildes tut genau das) - dafuer gibt es ImageView::stride.
    if (array.strides(dimensions - 1) != 1) {
        throw py::value_error("aruco_core.detect_markers erwartet dichte Pixel");
    }
    if (dimensions == 3 && array.strides(1) != channels) {
        throw py::value_error("aruco_core.detect_markers erwartet dichte Bildzeilen");
    }
    if (dimensions == 2 && array.strides(1) != 1) {
        throw py::value_error("aruco_core.detect_markers erwartet dichte Bildzeilen");
    }
    if (array.strides(0) < width * channels) {
        throw py::value_error("aruco_core.detect_markers erwartet aufsteigende Zeilen");
    }

    aruco::ImageView image;
    image.data = static_cast<const std::uint8_t*>(array.data());
    image.width = static_cast<int>(width);
    image.height = static_cast<int>(height);
    image.stride = static_cast<int>(array.strides(0));
    image.channels = static_cast<int>(channels);
    return image;
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
}
