// Kosmetische Aufbereitung des bereits entzerrten Bildes - Uebersetzung von
// app/vision/enhance.py.
//
// Die eine Regel, aus der hier alles folgt (AGENTS.md, Invariante 6):
// Aufbereitung ist KOSMETISCH, NIE GEOMETRISCH. Kein Regler aendert die
// Bildgroesse, jeder Weichzeichner ist symmetrisch, und stehen alle Regler
// neutral, kommt das Bild Bit fuer Bit zurueck.
//
// Die Reihenfolge der Stufen ist fest verdrahtet und steht ausfuehrlich
// begruendet im Kopf von app/vision/enhance.py. Sie hier zu aendern hiesse, dass
// dieselben Regler morgen eine andere Schablone ergeben.

#ifndef ARUCO_ENHANCE_HPP
#define ARUCO_ENHANCE_HPP

#include <string>

#include "aruco/types.hpp"

namespace aruco {

/// Alle Regler der Bildaufbereitung. Neutral heisst: nichts tun.
///
/// Die Namen und Wertebereiche spiegeln app/vision/enhance.py::AdjustOptions;
/// dort ist die Definition, hier die Uebersetzung.
struct AdjustOptions {
    bool grayscale = false;           ///< Schwarzweiss
    bool invert = false;              ///< Negativ
    double brightness = 0.0;          ///< -1..1, 0 = unveraendert
    double contrast = 0.0;            ///< -1..1, 0 = unveraendert
    double saturation = 0.0;          ///< -1..1, 0 = unveraendert
    double local_contrast = 0.0;      ///< 0..1, CLAHE-Staerke
    double edge_boost = 0.0;          ///< 0..1, Unschaerfemaske
    double edge_overlay = 0.0;        ///< 0..1, erkannte Kanten aufgelegt
    std::string color_emphasis = "none";  ///< "none" oder ein Schluessel aus ADJUST_EMPHASIS_HUES
    double emphasis_strength = 0.0;   ///< 0..1
    double threshold = 0.0;           ///< 0..1, 0 = aus
};

/// True, wenn keine einzige Stufe etwas zu tun hat.
bool is_identity(const AdjustOptions& options);

/// Bereitet ein entzerrtes BGR-Bild auf. Geometrie bleibt unangetastet.
///
/// Zurueck kommt immer ein NEUER Puffer - auch dann, wenn nichts zu tun war.
ImageBuffer adjust(const ImageView& image, const AdjustOptions& options);

}  // namespace aruco

#endif  // ARUCO_ENHANCE_HPP
