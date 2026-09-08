// INTERN. Was sich die beiden Uebersetzungseinheiten der JNI-Schicht teilen.
//
// jni.cpp traegt die Erkennung und die Konstanten, jni_chain.cpp den Rest der
// Messkette. Beide muessen dasselbe tun, wenn etwas schiefgeht: eine Java-
// Ausnahme vormerken und SOFORT zurueckkehren. Steht die Regel zweimal, wird sie
// einmal falsch - und eine C++-Ausnahme, die sich durch einen JNI-Rahmen
// entfaltet, beendet auf Android den Prozess wortlos.
//
// Ausserdem stehen hier die drei Umpackhilfen, die beide brauchen: Java-Feld ->
// double*, double* -> Java-Feld, und der direkte Puffer.

#ifndef ARUCO_JNI_SUPPORT_HPP
#define ARUCO_JNI_SUPPORT_HPP

#include <jni.h>

#include <cstdint>
#include <string>
#include <vector>

namespace aruco {
namespace jni {

/// So gross wie in capi.cpp - der Klartext einer OpenCV-Meldung passt hinein.
constexpr std::int32_t kErrorCapacity = 512;

/// Eine Java-Ausnahme vormerken.
///
/// `ThrowNew` wirft nicht sofort - es merkt die Ausnahme nur vor. Der C++-Code
/// MUSS danach zurueckkehren; jeder weitere JNI-Aufruf mit anstehender Ausnahme
/// ist undefiniert.
void throw_java(JNIEnv* env, const char* class_name, const std::string& message);

/// Den Fehlercode der C-Schnittstelle in die passende Java-Ausnahme uebersetzen.
///
/// Der Unterschied ist nicht kosmetisch: ARUCO_ERR_ARGUMENT bedeutet, dass die
/// Huelle etwas falsch uebergeben hat (ein Programmfehler, der in den Log
/// gehoert), ARUCO_ERR_INTERNAL, dass OpenCV an diesem Bild gescheitert ist (ein
/// Betriebsfall, den die Oberflaeche dem Bediener zeigen soll).
void throw_for(JNIEnv* env, std::int32_t code, const char* error);

/// Ein Java-double-Feld als Vektor. Leer, wenn `array` null ist.
///
/// Kopiert. Das ist hier richtig und nicht nachlaessig: durch diese Funktion
/// gehen Homographien und Punktlisten, also Dutzende bis wenige Tausend Zahlen.
/// Bilder gehen NICHT hier durch - fuer die gibt es den direkten Puffer.
std::vector<double> doubles_of(JNIEnv* env, jdoubleArray array);

/// Ein Vektor als frisches Java-double-Feld. Gibt nullptr zurueck, wenn der
/// Java-Haufen nichts mehr hergibt; dann steht bereits ein OutOfMemoryError an.
jdoubleArray doubles_to_java(JNIEnv* env, const double* values, std::int32_t count);

/// Die Adresse eines DIREKTEN ByteBuffers, mit Groessenpruefung.
///
/// Gibt nullptr zurueck und hat dann bereits eine IllegalArgumentException
/// vorgemerkt - der Aufrufer kehrt sofort zurueck. `needed` ist die Anzahl
/// Bytes, die der Kern lesen oder schreiben wird; ohne diese Pruefung laese er
/// ueber das Ende hinaus, und der Absturz haette keinen Zusammenhang mehr zu
/// dem Tippfehler in Breite, Hoehe oder Schrittweite, der ihn verursacht hat.
std::uint8_t* direct_buffer(JNIEnv* env, jobject buffer, std::int64_t needed, const char* what);

}  // namespace jni
}  // namespace aruco

#endif  // ARUCO_JNI_SUPPORT_HPP
