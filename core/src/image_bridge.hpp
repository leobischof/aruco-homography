// INTERN. Die Bruecke zwischen den ziel-neutralen Bildtypen des Kerns und
// cv::Mat.
//
// Diese Datei liegt bewusst in src/ und nicht in include/: sie fasst OpenCV an,
// und die oeffentlichen Kopfdateien des Kerns tun das nicht. Wer gegen den Kern
// bindet - die pybind11-Bindung, die embind-Bindung, die JNI-Schicht - soll
// `ImageView` und `ImageBuffer` sehen und kein cv::Mat; sonst wandert OpenCV in
// jede Huelle, die den Kern nur benutzen wollte.

#ifndef ARUCO_IMAGE_BRIDGE_HPP
#define ARUCO_IMAGE_BRIDGE_HPP

#include <opencv2/core.hpp>

#include "aruco/types.hpp"

namespace aruco {

/// Die ImageView als cv::Mat lesen, ohne sie zu kopieren.
///
/// Wirft `std::invalid_argument`, wenn die Sicht keine lesbare Form hat. Der
/// Puffer gehoert weiter dem Aufrufer; die Mat schreibt nie hinein.
cv::Mat as_mat(const ImageView& image);

/// Ein cv::Mat in einen ImageBuffer kopieren (Zeilen dicht).
///
/// Kopiert wirklich: das Ergebnis muss den Aufruf ueberleben, und ein cv::Mat,
/// dessen Daten in der Bindung weiterleben sollen, waere genau die Sorte
/// Besitzfrage, die in Emscripten ohne Sammler zum Leck wird.
ImageBuffer to_buffer(const cv::Mat& image);

}  // namespace aruco

#endif  // ARUCO_IMAGE_BRIDGE_HPP
