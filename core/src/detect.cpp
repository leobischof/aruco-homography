// Uebersetzung von app/vision/detect.py:113-155.
//
// Jede Zeile hier hat ein Gegenstueck dort, und die Reihenfolge ist dieselbe.
// Das ist Absicht: solange beide Kerne nebeneinander laufen, ist die
// Python-Fassung die geprueft masshaltige Referenz (docs/cpp-migration/README.md),
// und ein Leser muss beide Seiten nebeneinanderlegen koennen.

#include "aruco/detect.hpp"

#include <algorithm>
#include <cstddef>
#include <map>
#include <utility>
#include <vector>

#include <opencv2/core.hpp>
// contourArea steht in OpenCV 5 im Modul `geometry`, nicht mehr in `imgproc`.
#include <opencv2/geometry.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/objdetect/aruco_detector.hpp>

#include "dictionary.hpp"
#include "image_bridge.hpp"

namespace aruco {
namespace {

// Die Parameter stehen hier als Zahlen, weil sie auch in app/vision/detect.py als
// Zahlen stehen: sie sind keine Aussage ueber das PRODUKT (das waeren Millimeter),
// sondern ueber den Detektor. Damit sind sie die einzige Stelle, an der die beiden
// Kerne auseinanderlaufen koennen, ohne dass ein Uebersetzer es merkt - wer dort
// etwas aendert, aendert es hier mit. Der Quervergleich in tests/test_backend.py
// faellt sonst um, und das ist der Zweck jenes Tests.
cv::aruco::ArucoDetector build_detector() {
    const cv::aruco::Dictionary dictionary = predefined_dictionary();
    cv::aruco::DetectorParameters params;

    // Subpixel-Refinement: der wichtigste Genauigkeitsschalter dieses Projekts.
    params.cornerRefinementMethod = cv::aruco::CORNER_REFINE_SUBPIX;
    params.cornerRefinementWinSize = 5;
    params.cornerRefinementMaxIterations = 50;
    params.cornerRefinementMinAccuracy = 0.01;

    // Ein 12-MP-Foto braucht deutlich groessere Schwellwertfenster als die
    // Defaults, weil ein 50-mm-Marker darin mehrere hundert Pixel breit ist.
    params.adaptiveThreshWinSizeMin = 3;
    params.adaptiveThreshWinSizeMax = 53;
    params.adaptiveThreshWinSizeStep = 10;
    params.minMarkerPerimeterRate = 0.01;

    return cv::aruco::ArucoDetector(dictionary, params);
}

}  // namespace

std::vector<Marker> detect_markers(const ImageView& image, bool enhance_contrast) {
    const cv::Mat view = as_mat(image);

    cv::Mat gray;
    if (image.channels == 3) {
        cv::cvtColor(view, gray, cv::COLOR_BGR2GRAY);
    } else {
        gray = view;  // teilt sich den Puffer des Aufrufers; wird nur gelesen
    }

    if (enhance_contrast) {
        cv::Mat equalised;
        cv::createCLAHE(2.0, cv::Size(8, 8))->apply(gray, equalised);
        gray = equalised;
    }

    std::vector<std::vector<cv::Point2f>> quads;
    std::vector<int> ids;
    build_detector().detectMarkers(gray, quads, ids);

    // Bei mehrfach erkannter ID gewinnt der Marker mit der groesseren Bildflaeche.
    // std::map haelt die IDs nebenbei sortiert - genau das, was Pythons
    // `sorted(best)` tut. Bei Gleichstand gewinnt der zuerst gefundene, auch das
    // wie in Python (dort steht ein striktes `>`).
    std::map<int, Marker> best;
    std::map<int, double> areas;
    const std::size_t found = std::min(ids.size(), quads.size());
    for (std::size_t index = 0; index < found; ++index) {
        const std::vector<cv::Point2f>& quad = quads[index];
        // contourArea auf den float32-Ecken, die OpenCV geliefert hat. Python
        // rechnet dieselbe Flaeche aus denselben Bits (`.astype(np.float32)`).
        const double area = cv::contourArea(quad);

        const int id = ids[index];
        const auto known = areas.find(id);
        if (known != areas.end() && area <= known->second) {
            continue;
        }

        Marker marker;
        marker.id = id;
        for (int corner = 0; corner < 4; ++corner) {
            marker.corners[corner][0] = static_cast<double>(quad[corner].x);
            marker.corners[corner][1] = static_cast<double>(quad[corner].y);
        }
        best[id] = marker;
        areas[id] = area;
    }

    std::vector<Marker> markers;
    markers.reserve(best.size());
    for (const std::pair<const int, Marker>& entry : best) {
        markers.push_back(entry.second);
    }
    return markers;
}

}  // namespace aruco
