// Uebersetzung von app/vision/contour.py::find_contour_mm.

#include "aruco/contour.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

#include <opencv2/core.hpp>
#include <opencv2/geometry.hpp>
#include <opencv2/imgproc.hpp>

#include "aruco/constants.hpp"
#include "image_bridge.hpp"

namespace aruco {
namespace {

/// Der Median eines 8-Bit-Bildes, genau wie np.median: bei gerader Anzahl das
/// Mittel der beiden mittleren Werte.
///
/// Ueber ein Histogramm und nicht ueber Sortieren - bei einem Rasterbild von
/// hundert Megapixeln ist das der Unterschied zwischen Millisekunden und
/// Sekunden, und exakt ist es genauso: es gibt nur 256 moegliche Werte.
double median_of(const cv::Mat& gray) {
    std::array<std::size_t, 256> histogram{};
    for (int row = 0; row < gray.rows; ++row) {
        const std::uint8_t* pixel = gray.ptr<std::uint8_t>(row);
        for (int column = 0; column < gray.cols; ++column) {
            ++histogram[pixel[column]];
        }
    }

    const std::size_t count =
        static_cast<std::size_t>(gray.rows) * static_cast<std::size_t>(gray.cols);
    if (count == 0) {
        return 0.0;
    }

    // Bei ungerader Anzahl ist es der Wert an Position (count-1)/2, bei gerader
    // das Mittel der Positionen count/2 - 1 und count/2.
    const std::size_t lower_rank = (count - 1) / 2;
    const std::size_t upper_rank = count / 2;

    std::size_t seen = 0;
    double lower = 0.0;
    double upper = 0.0;
    bool have_lower = false;
    for (std::size_t value = 0; value < histogram.size(); ++value) {
        seen += histogram[value];
        if (!have_lower && seen > lower_rank) {
            lower = static_cast<double>(value);
            have_lower = true;
        }
        if (seen > upper_rank) {
            upper = static_cast<double>(value);
            break;
        }
    }
    return (lower + upper) / 2.0;
}

}  // namespace

std::vector<Point2> find_contour_mm(const ImageView& rectified_bgr, double px_per_mm) {
    if (!(px_per_mm > 0.0)) {
        throw std::invalid_argument("find_contour_mm: px_per_mm muss positiv sein");
    }

    const cv::Mat view = as_mat(rectified_bgr);
    if (view.channels() != 3) {
        throw std::invalid_argument("find_contour_mm erwartet ein BGR-Bild");
    }

    cv::Mat gray;
    cv::cvtColor(view, gray, cv::COLOR_BGR2GRAY);
    cv::Mat equalised;
    cv::createCLAHE(2.0, cv::Size(8, 8))->apply(gray, equalised);
    cv::Mat blurred;
    cv::GaussianBlur(equalised, blurred, cv::Size(0, 0), 1.0);

    // Canny-Schwellen aus dem Bildmedian: robuster als feste Werte ueber
    // verschiedene Belichtungen hinweg. `int()` schneidet ab, wie in Python.
    const double median = median_of(blurred);
    const int low = static_cast<int>(std::max(0.0, 0.66 * median));
    const int high = static_cast<int>(std::min(255.0, 1.33 * median));
    cv::Mat edges;
    cv::Canny(blurred, edges, low, high);

    cv::Mat closed;
    cv::morphologyEx(edges, closed, cv::MORPH_CLOSE,
                     cv::Mat::ones(5, 5, CV_8U));

    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(closed, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    if (contours.empty()) {
        return {};
    }

    // Pythons `max(..., key=...)` behaelt bei Gleichstand den ERSTEN - deshalb
    // striktes `>` und kein `>=`.
    std::size_t best = 0;
    double best_area = cv::contourArea(contours[0]);
    for (std::size_t index = 1; index < contours.size(); ++index) {
        const double area = cv::contourArea(contours[index]);
        if (area > best_area) {
            best = index;
            best_area = area;
        }
    }

    const double image_area = static_cast<double>(view.rows) * static_cast<double>(view.cols);
    if (best_area < constants::CONTOUR_MIN_AREA_FRAC * image_area) {
        return {};
    }

    std::vector<cv::Point> simplified;
    cv::approxPolyDP(contours[best], simplified, constants::CONTOUR_EPS_MM * px_per_mm, true);

    std::vector<Point2> polygon;
    polygon.reserve(simplified.size());
    for (const cv::Point& point : simplified) {
        polygon.push_back(
            Point2{static_cast<double>(point.x) / px_per_mm, static_cast<double>(point.y) / px_per_mm});
    }
    return polygon;
}

}  // namespace aruco
