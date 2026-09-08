#include "image_bridge.hpp"

#include <cstddef>
#include <cstring>
#include <stdexcept>

namespace aruco {

cv::Mat as_mat(const ImageView& image) {
    if (image.data == nullptr) {
        throw std::invalid_argument("ImageView ohne Daten");
    }
    if (image.width <= 0 || image.height <= 0) {
        throw std::invalid_argument("ImageView ohne Flaeche");
    }
    if (image.channels != 1 && image.channels != 3) {
        throw std::invalid_argument("ImageView: nur 1 (grau) oder 3 (BGR) Kanaele");
    }
    if (image.stride < image.width * image.channels) {
        throw std::invalid_argument("ImageView: Schrittweite kleiner als eine Zeile");
    }

    // const_cast, weil cv::Mat keinen lesenden Konstruktor hat. Geschrieben wird
    // in diesen Puffer nie: jede Rechnung bekommt ein eigenes Ziel.
    //
    // CV_8UC1/CV_8UC3 als MAKRO, nie als Zahl. Die Werte haben sich zwischen
    // OpenCV 4 und 5 geaendert (CV_8UC3: 16 -> 64, CV_32FC2: 13 -> 37; hier
    // nachgemessen an 5.0.0). Das Speicherbild ist dasselbe geblieben, nur die
    // Konstante nicht - eine abgetippte 16 naehme in einem Bau gegen ein anderes
    // OpenCV lautlos den falschen Zweig.
    return cv::Mat(image.height, image.width, image.channels == 1 ? CV_8UC1 : CV_8UC3,
                   const_cast<std::uint8_t*>(image.data), static_cast<std::size_t>(image.stride));
}

ImageBuffer to_buffer(const cv::Mat& image) {
    if (image.depth() != CV_8U) {
        throw std::invalid_argument("to_buffer erwartet ein 8-Bit-Bild");
    }

    ImageBuffer buffer;
    buffer.width = image.cols;
    buffer.height = image.rows;
    buffer.channels = image.channels();

    const std::size_t row_bytes =
        static_cast<std::size_t>(buffer.width) * static_cast<std::size_t>(buffer.channels);
    buffer.data.resize(row_bytes * static_cast<std::size_t>(buffer.height));
    for (int row = 0; row < buffer.height; ++row) {
        std::memcpy(buffer.data.data() + static_cast<std::size_t>(row) * row_bytes,
                    image.ptr<std::uint8_t>(row), row_bytes);
    }
    return buffer;
}

}  // namespace aruco
