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

#include <cstdint>

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

}  // namespace aruco

#endif  // ARUCO_TYPES_HPP
