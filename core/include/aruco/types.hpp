// Die Grenze des Rechenkerns. Hier dockt spaeter Android an, hier dockt WASM an -
// und deshalb steht in dieser Datei NICHTS aus imgcodecs.
//
// Im WASM-Bau ist imgcodecs abgeschaltet (nachgemessen, Stufe 0:
// docs/cpp-migration/stage-0-opencv-js.md, Abschnitt 5). Es gibt dort kein
// imread, kein imdecode, kein imencode, kein imwrite. Ein Kern, der eine Datei
// oeffnet, laesst sich fuer den Browser nicht uebersetzen. Also nimmt er einen
// rohen Pixelpuffer entgegen und gibt Zahlen zurueck; das Dekodieren gehoert auf
// jedes Ziel einzeln (Browser: Canvas, Windows/Android: die Plattform).

#ifndef ARUCO_TYPES_HPP
#define ARUCO_TYPES_HPP

#include <array>
#include <cstdint>
#include <vector>

namespace aruco {

/// Ein Bild, das dem Kern NICHT gehoert.
///
/// Wem es gehoert, weiss der Aufrufer: im Browser der Canvas, in Python ein
/// numpy-Array, auf Android ein Bitmap. Der Kern liest nur - deshalb `const`,
/// deshalb kein Dekodieren, kein Laden, keine Besitzuebernahme. Wer eine
/// ImageView weiterreicht, buergt dafuer, dass der Puffer den Aufruf ueberlebt.
struct ImageView {
    const std::uint8_t* data = nullptr;
    int width = 0;
    int height = 0;
    /// Bytes je Zeile, NICHT Pixel. Ein Ausschnitt aus einem groesseren Bild hat
    /// eine groessere Schrittweite als `width * channels`; ohne dieses Feld
    /// laese der Kern in die falsche Zeile.
    int stride = 0;
    /// 1 = grau, 3 = BGR (dieselbe Kanalreihenfolge wie OpenCV und wie das
    /// numpy-Array, das `app/vision/detect.py` herumreicht).
    int channels = 0;
};

/// Ein Bild, das dem Kern GEHOERT - das Ergebnis von Entzerrung und Aufbereitung.
///
/// Das Gegenstueck zu ImageView, und der Grund, warum es eine zweite Form gibt:
/// ein Ergebnis hat keinen Aufrufer, der den Speicher schon haelt. Zeilen liegen
/// hier immer dicht (stride == width * channels); ein Aufrufer, der etwas anderes
/// annimmt, laege falsch.
struct ImageBuffer {
    std::vector<std::uint8_t> data;
    int width = 0;
    int height = 0;
    int channels = 0;
};

/// Ein erkannter Marker: ID und die vier Bildecken.
///
/// Die Reihenfolge ist TL, TR, BR, BL - genau die von cv::aruco. Eine andere
/// Reihenfolge spiegelte die Homographie, und das Ergebnis saehe plausibel aus
/// (tests/test_detect.py::test_eckenreihenfolge_stimmt).
///
/// Die Ecken sind `double`, obwohl OpenCV sie als `float` liefert: die Messung
/// rechnet ab hier in doppelter Genauigkeit weiter, genau wie die Python-Seite,
/// die das float32-Ergebnis sofort nach float64 verbreitert.
struct Marker {
    int id = -1;
    double corners[4][2] = {};
};

/// Ein Punkt in der Ebene (mm) oder im Bild (px) - welches von beidem, sagt der
/// Name der Groesse, nicht der Typ. Ein eigener Typ je Einheit waere hier
/// Zeremonie: die Rechnung mischt sie nie, die Homographie fuehrt von einer in
/// die andere.
struct Point2 {
    double x = 0.0;
    double y = 0.0;
};

/// Eine Homographie, ZEILENWEISE: {h00, h01, h02, h10, h11, h12, h20, h21, h22}.
///
/// Zeilenweise, weil numpy, OpenCV und JavaScript-Typenfelder es alle so halten;
/// eine spaltenweise Fassung waere genau die Sorte stiller Transposition, die
/// eine plausibel aussehende, gespiegelte Schablone ergibt.
using Matrix3 = std::array<double, 9>;

/// Ein achsparalleler Bereich in Ebenen-Millimetern. Das Gegenstueck zu
/// app/vision/extent.py::Extent.
struct Extent {
    double x0 = 0.0;
    double y0 = 0.0;
    double x1 = 0.0;
    double y1 = 0.0;
};

}  // namespace aruco

#endif  // ARUCO_TYPES_HPP
