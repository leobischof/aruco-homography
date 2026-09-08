/* Die C-Schnittstelle des Rechenkerns - die Grenze, an der eine FREMDE Sprache
 * andockt.
 *
 * Warum C und nicht das C++ aus detect.hpp: eine C++-Schnittstelle ist keine
 * stabile ABI. `std::vector` sieht unter MSVC anders aus als unter clang, ein
 * geworfenes `std::invalid_argument` entfaltet sich nicht durch einen
 * JVM-Rahmen, und der Name einer C++-Funktion haengt an der Namensverzierung des
 * Uebersetzers. Die JNI-Schicht daneben (core/bindings/jni.cpp) koennte damit
 * leben, weil sie im selben Bau steckt - aber jede spaetere Bindung koennte es
 * nicht, und die JNI-Schicht ist nicht der einzige geplante Aufrufer.
 *
 * Drei Regeln, die diese Datei einhaelt und die jede Erweiterung einhalten muss:
 *
 *  1. **Keine Ausnahme verlaesst diesen Kopf.** Jede Funktion faengt alles und
 *     gibt einen negativen Code plus Klartext zurueck. Eine Ausnahme, die durch
 *     die JNI-Grenze laeuft, beendet auf Android den ganzen Prozess.
 *  2. **Kein Besitz wechselt die Seite.** Der Aufrufer stellt jeden Puffer, der
 *     Kern schreibt hinein. Es gibt nichts freizugeben, also gibt es auch nichts
 *     zu vergessen.
 *  3. **Nichts aus imgcodecs.** Wie in aruco/types.hpp: rohe Pixel herein, Zahlen
 *     heraus. Das Dekodieren gehoert auf jedes Ziel einzeln - auf Android macht
 *     es die Plattform (BitmapFactory), im Browser die Leinwand.
 */

#ifndef ARUCO_CAPI_H
#define ARUCO_CAPI_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Rueckgabewerte. Alles >= 0 ist ein Ergebnis (meist eine Anzahl), alles < 0 ein
 * Fehler - dann steht der Klartext im `error`-Puffer. */
#define ARUCO_OK 0
#define ARUCO_ERR_ARGUMENT (-1)  /* Der Aufrufer hat Unsinn uebergeben. */
#define ARUCO_ERR_CAPACITY (-2)  /* Der Ausgabepuffer ist zu klein. */
#define ARUCO_ERR_INTERNAL (-3)  /* OpenCV oder der Kern haben geworfen. */

/* Ein erkannter Marker in flacher Form.
 *
 * Die acht Werte sind TL.x TL.y TR.x TR.y BR.x BR.y BL.x BL.y - genau die
 * Reihenfolge aus aruco/types.hpp und damit die von cv::aruco. Eine andere
 * Reihenfolge spiegelte die Homographie, und das Ergebnis saehe plausibel aus.
 *
 * `double` und nicht `float`, weil die Messung ab der Erkennung in doppelter
 * Genauigkeit weiterrechnet - genau wie die Python-Seite. */
typedef struct aruco_marker {
    int32_t id;
    double corners[8];
} aruco_marker;

/* Alle Marker im Bild finden.
 *
 * `data`      zeilenweise dichte uint8-Pixel, dem Kern NICHT gehoerend.
 * `stride`    Bytes je Zeile (nicht Pixel).
 * `channels`  1 = grau, 3 = BGR.
 * `enhance_contrast`  0/1 - legt CLAHE vor die Erkennung (siehe detect.hpp).
 * `out`       Feld fuer die Ergebnisse, mindestens `out_capacity` Eintraege.
 * `error`     Puffer fuer den Klartext; darf NULL sein.
 *
 * Rueckgabe: Anzahl der geschriebenen Marker (>= 0), sonst ein negativer Code.
 * Reicht `out_capacity` nicht, ist das ARUCO_ERR_CAPACITY und NICHT eine stille
 * Kuerzung: ein fehlender Marker verzoege die Homographie, ohne dass irgendwo
 * etwas rot wuerde. Wie gross der Puffer sein muss, sagt aruco_dictionary_size().
 */
int32_t aruco_detect_markers(const uint8_t* data, int32_t width, int32_t height, int32_t stride,
                             int32_t channels, int32_t enhance_contrast, aruco_marker* out,
                             int32_t out_capacity, char* error, int32_t error_capacity);

/* Die Modulbits eines Markers, zeilenweise, ein Byte je Modul (0 = schwarz).
 *
 * Das braucht das Markerblatt: web/pdf/markersheet.js zeichnet jedes Modul als
 * Vektorrechteck und bekommt die Bits von aussen. Unter Node liefert sie
 * opencv.js (tools/opencv_markers.mjs), auf Android diese Funktion - dieselbe
 * Grenze, dieselbe Form, damit auf beiden Wegen dasselbe Blatt entsteht.
 *
 * `modules` ist die Kantenlaenge IN MODULEN einschliesslich Rand; fuer ein
 * 4x4-Woerterbuch mit einem Modul Rand sind das 6. Geschrieben werden
 * `modules * modules` Bytes.
 *
 * Rueckgabe: Anzahl geschriebener Bytes (>= 0), sonst ein negativer Code. */
int32_t aruco_marker_bits(int32_t marker_id, int32_t modules, uint8_t* out, int32_t out_capacity,
                          char* error, int32_t error_capacity);

/* Wie viele Marker das eingestellte Woerterbuch kennt.
 *
 * Damit ist der Ausgabepuffer von aruco_detect_markers exakt zu bemessen: mehr
 * verschiedene IDs kann es nicht geben, und der Kern raeumt Doppelerkennungen
 * selbst weg. Ein Aufrufer, der das benutzt, kann ARUCO_ERR_CAPACITY nicht
 * bekommen und muss die Erkennung nicht zweimal laufen lassen, um die Anzahl zu
 * erfahren - auf einem 12-MP-Foto waere das die teuerste Zeile der App. */
int32_t aruco_dictionary_size(void);

/* Der Name des Woerterbuchs, erzeugt aus shared/constants.json. Nicht freigeben:
 * der Zeiger zeigt auf statischen Speicher und lebt so lange wie die
 * Bibliothek. */
const char* aruco_dictionary_name(void);

/* Die nominelle Markerkante in Millimetern, aus shared/constants.json.
 *
 * Die Huelle braucht sie fuer die Vorgabe im Eingabefeld. Sie hier zu holen statt
 * sie abzutippen ist Invariante 4: eine Konstante hat genau eine Stelle - und
 * eine abgetippte waere eine, die in Millimetern driftet. */
double aruco_marker_mm_nominal(void);

/* Die OpenCV-Fassung, gegen die gebunden wurde ("5.0.0").
 *
 * Nicht Zierde: die Typkennungen haben sich zwischen 4.x und 5.0 verschoben, und
 * ein Bericht vom Geraet, der die Fassung nicht nennt, laesst genau die Frage
 * offen, die man dann stellen wuerde. */
const char* aruco_opencv_version(void);

#ifdef __cplusplus
}  /* extern "C" */
#endif

#endif /* ARUCO_CAPI_H */
