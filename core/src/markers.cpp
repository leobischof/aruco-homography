// Uebersetzung des einen cv2-Aufrufs, den das Markerblatt braucht:
// cv2.aruco.generateImageMarker(dictionary, id, modules, borderBits=1).
//
// Auf der Python-Seite steht er in app/pdf/markersheet.py, unter Node holt ihn
// tools/opencv_markers.mjs aus @techstark/opencv-js. Im Browser gibt es dieses
// Paket nicht mehr - der Kern kann es selbst, und damit haengt der Bau an einer
// Abhaengigkeit weniger (docs/cpp-migration/README.md, Abschnitt 7).

#include "aruco/markers.hpp"

#include <stdexcept>

#include <opencv2/core.hpp>
#include <opencv2/objdetect/aruco_detector.hpp>

#include "dictionary.hpp"

namespace aruco {

std::vector<std::uint8_t> marker_bits(int marker_id, int modules) {
    if (modules <= 0) {
        throw std::invalid_argument("marker_bits: modules muss positiv sein");
    }

    cv::Mat image;
    // borderBits = 1: das eine schwarze Randmodul gehoert zum Marker. `modules`
    // zaehlt es mit, genau wie MODULES in web/pdf/markersheet.js.
    cv::aruco::generateImageMarker(configured_dictionary(), marker_id, modules, image, 1);

    std::vector<std::uint8_t> bits;
    bits.reserve(static_cast<std::size_t>(modules) * static_cast<std::size_t>(modules));
    for (int row = 0; row < image.rows; ++row) {
        const std::uint8_t* pixel = image.ptr<std::uint8_t>(row);
        for (int column = 0; column < image.cols; ++column) {
            bits.push_back(pixel[column]);
        }
    }
    return bits;
}

}  // namespace aruco
