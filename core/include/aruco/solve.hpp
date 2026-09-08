// Die Ausgleichsrechnung - der Kern des Kerns.
//
// Vorlage ist app/vision/solve.py. Hier stehen nur die ZAHLENVERFAHREN; die
// Modus-Wahl, die Warnungen und der Qualitaetsbericht bleiben in der Hostsprache
// (Python fuer den Desktop, JavaScript im Browser). Das ist dieselbe Grenze wie
// bei der Erkennung: der Kern rechnet, der Rand redet.
//
// `scipy.optimize.least_squares` gibt es in C++ nicht. An seiner Stelle steht
// `cv::LevMarq` (OpenCV 5, Modul `geometry`) mit denselben Abbruchschranken.
// Beides sind Levenberg-Marquardt-Verfahren auf demselben Residuum; dass sie
// dieselbe Loesung finden, ist keine Behauptung, sondern das, was die vorhandene
// Testsuite mit ARUCO_CORE=cpp prueft.

#ifndef ARUCO_SOLVE_HPP
#define ARUCO_SOLVE_HPP

#include <array>
#include <vector>

#include "aruco/types.hpp"

namespace aruco {

/// Homographie aus GENAU vier Punktpaaren (cv::getPerspectiveTransform).
///
/// Exakt bestimmt, kein Ausgleich. Python nimmt diesen Weg, sobald nur ein
/// einziger Marker brauchbar ist - und im Frei-Modus fuer den Ankermarker.
Matrix3 homography_from_quad(const std::array<Point2, 4>& plane,
                             const std::array<Point2, 4>& image);

/// Homographie aus vielen Punktpaaren, robust (cv::findHomography, LMEDS).
///
/// Wirft, wenn OpenCV keine findet - Python macht daraus AppError("homography_failed").
Matrix3 homography_lmeds(const std::vector<Point2>& plane, const std::vector<Point2>& image);

/// Nichtlinearer Ausgleich des Reprojektionsfehlers ueber die 8 freien Parameter.
///
/// `start` wird auf h22 == 1 normiert; eine Homographie mit verschwindendem h22
/// ist entartet und wirft.
Matrix3 refine_homography(const Matrix3& start, const std::vector<Point2>& plane,
                          const std::vector<Point2>& image);

/// Das Ergebnis des Frei-Modus: Homographie und die Lage der uebrigen Marker.
struct FreeFit {
    Matrix3 homography{};
    /// Ein Versatz je Marker AUSSER dem Anker, in der Reihenfolge der Eingabe.
    std::vector<Point2> offsets;
};

/// Eine Markerlage in der Ebene: Mittelpunkt in Millimetern und Drehung.
struct Pose2 {
    double x = 0.0;
    double y = 0.0;
    /// Im Bogenmass, um den Mittelpunkt. `theta == 0` heisst achsparallel - so,
    /// wie ein Marker auf dem Markerblatt liegt.
    double theta = 0.0;
};

/// Das Ergebnis des Streu-Modus: Homographie und die Lage JEDES Markers.
struct ScatteredFit {
    Matrix3 homography{};
    /// Eine Lage je Marker, in der Reihenfolge der Eingabe - auch fuer den
    /// ersten. Im Frei-Modus liegt der Anker hinterher fest im Ursprung und
    /// braucht deshalb keine; hier wird die Ebene zum Schluss neu ausgerichtet,
    /// und das bewegt jeden Marker.
    std::vector<Pose2> poses;
};

/// Streu-Modus: verstreute Marker in BELIEBIGEN Winkeln.
///
/// Wie `fit_free`, nur mit einer Unbekannten mehr je Marker - der Drehung.
/// 8 + 3*(n-1) Unbekannte gegen 8*n Gleichungen; jeder weitere Marker bringt
/// also fuenf Bestimmungsstuecke netto ein und nicht sechs wie im Frei-Modus.
/// Der Frei-Modus setzt voraus, dass alle Marker gleich ausgerichtet liegen;
/// hier darf jeder liegen, wie er faellt.
///
/// **Ein einzelner Marker reicht.** Vier Punktpaare bestimmen eine Homographie
/// exakt - der Marker traegt sein Koordinatensystem selbst, in der festen
/// Eckenreihenfolge. Was er nicht traegt, ist eine Probe: bei n == 1 ist die
/// Rechnung exakt bestimmt, das Residuum also null, und der Fehler dennoch
/// unbekannt. Diese Warnung gehoert in die Hostsprache (Invariante 7).
///
/// `quads` sind die Bildecken, absteigend nach Bildflaeche sortiert - der erste
/// legt den MASSSTAB fest, wie im Frei-Modus. Ursprung und Achsen legt er NICHT
/// fest: bei verstreuten Markern hat kein Marker einen ausgezeichneten Winkel,
/// und der Zuschnitt ist ein ACHSPARALLELES Rechteck. Also richtet sich die
/// fertige Ebene nach dem FOTO - x nach rechts, y nach unten, wie im Bild -,
/// und ihr Ursprung liegt in der Mitte der Markerwolke.
ScatteredFit fit_scattered(const std::vector<std::array<Point2, 4>>& quads, double marker_mm);

/// Frei-Modus: Homographie UND Markerpositionen gemeinsam schaetzen.
///
/// `quads` sind die Bildecken der Marker, absteigend nach Bildflaeche sortiert -
/// der erste ist der Anker und definiert Ursprung und Massstab der Ebene. Wer
/// anders sortiert, bekommt einen anderen Startwert und damit eine andere
/// Ebenenlage; die Sortierung gehoert deshalb zum Verfahren und nicht zum
/// Aufrufer. Sie steht trotzdem dort, weil nur der Aufrufer die Marker-IDs kennt,
/// die hinterher wieder zugeordnet werden muessen.
FreeFit fit_free(const std::vector<std::array<Point2, 4>>& quads, double marker_mm);

}  // namespace aruco

#endif  // ARUCO_SOLVE_HPP
