// Das Woerterbuch, einmal. INTERNER Kopf - er liegt bewusst in src/ und nicht in
// include/, weil er OpenCV-Typen fuehrt: alles unter include/aruco/ muss ohne
// OpenCV lesbar bleiben, sonst zieht jede Bindung den ganzen Kopfbaum mit.
//
// Warum es diese Datei ueberhaupt gibt: die Abbildung NAME -> OpenCV-Kennung
// stand in detect.cpp, und mit capi.cpp kam ein zweiter Aufrufer dazu (das
// Markerblatt braucht die Modulbits desselben Woerterbuchs). Zwei Tabellen waeren
// zwei Wahrheiten - eine Erkennung aus DICT_4X4_50 und ein Blatt aus einem
// anderen Woerterbuch faende schlicht keine Marker, und das saehe nach einem
// schlechten Foto aus.

#ifndef ARUCO_SRC_DICTIONARY_HPP
#define ARUCO_SRC_DICTIONARY_HPP

#include <string_view>

#include <opencv2/objdetect/aruco_dictionary.hpp>

namespace aruco {

/// Die OpenCV-Kennung zu einem Woerterbuchnamen.
///
/// Ersetzt Pythons `getattr(cv2.aruco, NAME)` (app/config.py). WIRFT
/// `std::invalid_argument` bei einem unbekannten Namen, statt still auf ein
/// Vorgabewoerterbuch zu fallen: ein falsches Woerterbuch findet einfach keine
/// Marker, und das ist von einem Tippfehler in einer Konstanten nicht zu
/// unterscheiden.
cv::aruco::PredefinedDictionaryType dictionary_id(std::string_view name);

/// Das eingestellte Woerterbuch (constants::ARUCO_DICT_NAME).
const cv::aruco::Dictionary& configured_dictionary();

}  // namespace aruco

#endif  // ARUCO_SRC_DICTIONARY_HPP
