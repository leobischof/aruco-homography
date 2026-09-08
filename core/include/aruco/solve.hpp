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
