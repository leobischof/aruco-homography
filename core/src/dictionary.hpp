// INTERN. Das ArUco-Woerterbuch dieses Projekts, an genau einer Stelle.
//
// ARUCO_DICT_NAME ist ein NAME, keine Zahl (shared/constants.json). Python
// leitet die OpenCV-Kennung mit getattr(cv2.aruco, NAME) daraus ab; C++ kennt
// keine Reflexion, also steht die Tabelle hier - und nur hier. Sie hat zwei
// Verbraucher: die Erkennung (src/detect.cpp) und das Markerblatt
// (src/markers.cpp). Eine zweite Tabelle waere eine zweite Wahrheit darueber,
// welche Marker dieses Werkzeug ueberhaupt kennt.
//
// In src/ und nicht in include/, weil sie cv::aruco im Typ fuehrt: die
// oeffentlichen Kopfdateien des Kerns bleiben frei von OpenCV.

#ifndef ARUCO_DICTIONARY_HPP
#define ARUCO_DICTIONARY_HPP

#include <opencv2/objdetect/aruco_dictionary.hpp>

namespace aruco {

/// Das Woerterbuch aus shared/constants.json.
///
/// WIRFT bei einem unbekannten Namen, statt still auf ein Vorgabewoerterbuch zu
/// fallen. Ein falsches Woerterbuch findet einfach keine Marker; das saehe nach
/// einem schlechten Foto aus und nicht nach einem Tippfehler in einer Konstanten.
cv::aruco::Dictionary predefined_dictionary();

}  // namespace aruco

#endif  // ARUCO_DICTIONARY_HPP
