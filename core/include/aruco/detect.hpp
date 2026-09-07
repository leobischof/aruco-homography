// Markererkennung - die Messtechnik selbst.
//
// Die Vorlage ist app/vision/detect.py. Diese Uebersetzung ist der einzige
// Modulumzug, an dem der C++-Kern scheitern kann: alles andere im Kern ist
// Numerik, die sich nachrechnen laesst, aber die Subpixel-Verfeinerung der
// Markerecken IST die Millimetergenauigkeit dieses Projekts.

#ifndef ARUCO_DETECT_HPP
#define ARUCO_DETECT_HPP

#include <vector>

#include "aruco/types.hpp"

namespace aruco {

/// Alle Marker im Bild finden, nach ID sortiert.
///
/// `enhance_contrast` legt CLAHE vor die Erkennung. Das ist kein Schoenheits-
/// schalter: gemessen an der eingefrorenen Szene liegt der groesste Eckfehler
/// mit CLAHE bei 0,140 px und ohne bei 0,160 px (Stufe 0).
///
/// Wird eine ID mehrfach erkannt, gewinnt der Marker mit der groesseren
/// Bildflaeche. Doppelerkennungen sind selten, wuerden die Homographie aber
/// verziehen - und der Kern raeumt das selbst auf, weil auf Android und im
/// Browser niemand hinter ihm steht, der es noch tun koennte.
///
/// Wirft `std::invalid_argument`, wenn die ImageView keine lesbare Form hat.
std::vector<Marker> detect_markers(const ImageView& image, bool enhance_contrast = true);

}  // namespace aruco

#endif  // ARUCO_DETECT_HPP
