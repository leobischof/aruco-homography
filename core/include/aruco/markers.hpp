// Die Modulbits eines Markers - was auf das Markerblatt gedruckt wird.
//
// Das ist die eine Stelle, an der der Kern nicht misst, sondern erzeugt. Sie
// gehoert trotzdem hierher und nicht in den PDF-Bau: welche schwarzen und
// weissen Quadrate ein Marker hat, sagt das Woerterbuch, und das Woerterbuch
// wohnt in OpenCV. Ein abgeschriebenes Modulraster waere eine zweite Wahrheit
// darueber, wie ein Marker aussieht - und ein vertauschtes Raster saehe auf dem
// Bildschirm voellig normal aus (AGENTS.md, tests/test_markersheet.py).

#ifndef ARUCO_MARKERS_HPP
#define ARUCO_MARKERS_HPP

#include <cstdint>
#include <vector>

namespace aruco {

/// Die Module eines Markers, zeilenweise, 0 = schwarz und 255 = weiss.
///
/// `modules` ist die Kantenlaenge EINSCHLIESSLICH des einen Randmoduls - fuer
/// DICT_4X4_50 also 6. Das Ergebnis hat `modules * modules` Werte.
std::vector<std::uint8_t> marker_bits(int marker_id, int modules);

}  // namespace aruco

#endif  // ARUCO_MARKERS_HPP
