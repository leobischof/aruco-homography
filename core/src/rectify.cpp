// Uebersetzung von app/vision/rectify.py.
//
// Hier stehen nur die zwei Funktionen, die wirklich rechnen. Die
// Speicherbudget-Pruefung (check_output_budget) bleibt in der Hostsprache: sie
// wirft einen Fehler MIT VORSCHLAG, und ein Vorschlag ist Text - der gehoert an
// den Rand (Invariante 7).

#include "aruco/rectify.hpp"

#include <algorithm>
#include <cstring>
#include <stdexcept>

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>

#include "image_bridge.hpp"

namespace aruco {

void output_size(const Extent& crop, double px_per_mm, int& width, int& height) {
    // cvRound rundet zur geraden Zahl - dasselbe wie Pythons round().
    width = std::max(1, cvRound((crop.x1 - crop.x0) * px_per_mm));
    height = std::max(1, cvRound((crop.y1 - crop.y0) * px_per_mm));
}

ImageBuffer rectify(const ImageView& image, const Matrix3& homography, const Extent& crop,
                    double px_per_mm, double source_px_per_mm) {
    if (!(px_per_mm > 0.0)) {
        throw std::invalid_argument("rectify: px_per_mm muss positiv sein");
    }

    const cv::Mat view = as_mat(image);
    if (view.channels() != 3) {
        throw std::invalid_argument("rectify erwartet ein BGR-Bild");
    }

    int width = 0;
    int height = 0;
    output_size(crop, px_per_mm, width, height);

    // Ausgabepixel -> Ebenen-mm, mit Pixelmitten-Versatz (siehe Kopfdatei).
    const double step = 1.0 / px_per_mm;
    const cv::Matx33d scale(step, 0.0, crop.x0 + step / 2.0, 0.0, step, crop.y0 + step / 2.0, 0.0,
                            0.0, 1.0);
    const cv::Matx33d matrix(homography[0], homography[1], homography[2], homography[3],
                             homography[4], homography[5], homography[6], homography[7],
                             homography[8]);
    const cv::Matx33d total = matrix * scale;

    // INTER_AREA beim Verkleinern (vermeidet Aliasing), sonst Lanczos.
    const int interpolation = (source_px_per_mm > 0.0 && px_per_mm < 0.9 * source_px_per_mm)
                                  ? cv::INTER_AREA
                                  : cv::INTER_LANCZOS4;

    cv::Mat warped;
    cv::warpPerspective(view, warped, cv::Mat(total), cv::Size(width, height),
                        interpolation | cv::WARP_INVERSE_MAP, cv::BORDER_CONSTANT,
                        cv::Scalar(255, 255, 255));
    return to_buffer(warped);
}

}  // namespace aruco
