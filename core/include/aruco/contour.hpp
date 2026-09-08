// Optionale Umriss-Erkennung im bereits entzerrten Bild - Uebersetzung von
// app/vision/contour.py.
//
// Das Ergebnis ist eine Schnitthilfe, kein Messwerkzeug: es steht und faellt mit
// dem Kontrast zwischen Objekt und Untergrund. Findet sich nichts Plausibles,
// kommt ein leeres Polygon zurueck und das PDF wird ohne Kontur gebaut - lieber
// keine Linie als eine falsche.
//
// Koordinaten kommen in Millimetern relativ zur linken oberen Ecke des
// Zuschnitts zurueck, y nach unten (wie im Bild). Die PDF-Schicht dreht y
// einmalig um.

#ifndef ARUCO_CONTOUR_HPP
#define ARUCO_CONTOUR_HPP

#include <vector>

#include "aruco/types.hpp"

namespace aruco {

/// Groesste plausible Aussenkontur als Polygon in mm; leer, wenn keine taugt.
std::vector<Point2> find_contour_mm(const ImageView& rectified_bgr, double px_per_mm);

}  // namespace aruco

#endif  // ARUCO_CONTOUR_HPP
