// JNI-Bindung, Teil 2: der Rest der Messkette.
//
// jni.cpp findet die Marker. Hier steht alles, was danach kommt - Homographie,
// Ausgleich, Kamerapose, Ausdehnung, Entzerrung, Aufbereitung, Umriss -, und es
// steht in derselben Reihenfolge wie in aruco/capi.h und in
// core/bindings/web.cpp. Wer die drei nebeneinanderlegt, soll dieselbe Kette
// sehen und nicht drei Auslegungen davon.
//
// **Auch diese Datei rechnet nicht.** Sie packt Java-Felder aus, ruft die
// C-Schnittstelle und packt Zahlen ein. Jede Zeile, die hier rechnete, waere
// eine Rechnung, die weder der Pruefstand noch die Python-Testsuite sieht.
//
// ZWEI SORTEN FUNKTION, und der Unterschied ist der Speicher:
//
//   * **Zahlen** gehen als `double[]` hin und zurueck. Eine Homographie sind
//     neun Werte, eine Punktliste selten mehr als ein paar hundert; das darf
//     kopiert werden, und kopiert wird es sowieso.
//
//   * **Bilder** gehen als DIREKTER ByteBuffer, in beide Richtungen. Der
//     Aufrufer stellt auch den AUSGABEPUFFER - genau wie in aruco/capi.h, und
//     aus demselben Grund: was niemandem gehoert, kann niemand vergessen. Wie
//     gross er sein muss, sagt `outputSize` (Entzerren) oder die Eingabe selbst
//     (Aufbereiten). Ein Rasterbild als `byte[]` durch die JNI-Grenze waere bei
//     300 dpi zweistellige Megabyte je Aufruf, kopiert, auf dem Java-Haufen.

#include <jni.h>

#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

#include "aruco/capi.h"
#include "jni_support.hpp"

namespace {

using aruco::jni::direct_buffer;
using aruco::jni::doubles_of;
using aruco::jni::doubles_to_java;
using aruco::jni::kErrorCapacity;
using aruco::jni::throw_for;
using aruco::jni::throw_java;

/// Ein Fehlerpuffer plus die Auswertung in einem Griff.
///
/// Jede Funktion hier endet gleich: Code < 0 heisst Ausnahme vormerken und
/// zurueckkehren. Steht das zwanzigmal von Hand da, fehlt es einmal - und ein
/// nicht ausgewerteter Fehlercode ist auf dieser Seite der Grenze ein
/// Ergebnisfeld voller Nullen, das plausibel aussieht.
struct Call {
    char error[kErrorCapacity] = {0};

    bool failed(JNIEnv* env, std::int32_t code) {
        if (code >= 0) {
            return false;
        }
        throw_for(env, code, error);
        return true;
    }
};

/// Die Anzahl PUNKTE in einem flachen (x,y,...)-Feld. Negativ bei ungerader
/// Laenge - das ist ein Aufrufer, der die Paare verloren hat.
std::int32_t point_count(const std::vector<double>& flat) {
    if (flat.size() % 2 != 0) {
        return -1;
    }
    return static_cast<std::int32_t>(flat.size() / 2);
}

/// Ein Feld genau erwarteter Laenge, sonst IllegalArgumentException.
bool wrong_size(JNIEnv* env, const std::vector<double>& values, std::size_t expected,
                const char* what) {
    if (values.size() == expected) {
        return false;
    }
    throw_java(env, "java/lang/IllegalArgumentException",
               std::string(what) + " erwartet " + std::to_string(expected) + " Zahlen, bekam " +
                   std::to_string(values.size()));
    return true;
}

/// Ein flaches Punktfeld mit gerader Laenge, sonst IllegalArgumentException.
bool odd_pairs(JNIEnv* env, const std::vector<double>& values, const char* what) {
    if (point_count(values) >= 0) {
        return false;
    }
    throw_java(env, "java/lang/IllegalArgumentException",
               std::string(what) + " erwartet Paare (x,y,x,y,...), bekam " +
                   std::to_string(values.size()) + " Zahlen");
    return true;
}

/// Die Reglerstellung aus den Java-Argumenten. `emphasis` darf null sein.
///
/// Ein Struct und keine zwoelf Einzelwerte durch die Kette: die Reihenfolge
/// steht damit genau einmal hier und nicht noch einmal an jeder Aufrufstelle.
aruco_adjust_options adjust_options(jboolean grayscale, jboolean invert, jdouble brightness,
                                    jdouble contrast, jdouble saturation, jdouble local_contrast,
                                    jdouble edge_boost, jdouble edge_overlay,
                                    const char* emphasis, jdouble emphasis_strength,
                                    jdouble threshold) {
    aruco_adjust_options options;
    options.grayscale = grayscale == JNI_TRUE ? 1 : 0;
    options.invert = invert == JNI_TRUE ? 1 : 0;
    options.brightness = brightness;
    options.contrast = contrast;
    options.saturation = saturation;
    options.local_contrast = local_contrast;
    options.edge_boost = edge_boost;
    options.edge_overlay = edge_overlay;
    options.emphasis_strength = emphasis_strength;
    options.threshold = threshold;
    options.color_emphasis = emphasis;  // NULL heisst "none" (capi_support.cpp)
    return options;
}

}  // namespace

extern "C" {

// --- Homographie und Ausgleich ----------------------------------------------

JNIEXPORT jdoubleArray JNICALL Java_com_bischofsnowboards_aruco_NativeCore_homographyFromQuad(
    JNIEnv* env, jclass, jdoubleArray plane, jdoubleArray image) {
    const std::vector<double> plane_xy = doubles_of(env, plane);
    const std::vector<double> image_xy = doubles_of(env, image);
    if (wrong_size(env, plane_xy, 8, "homographyFromQuad(plane)") ||
        wrong_size(env, image_xy, 8, "homographyFromQuad(image)")) {
        return nullptr;
    }

    Call call;
    double homography[9] = {0.0};
    if (call.failed(env, aruco_homography_from_quad(plane_xy.data(), image_xy.data(), homography,
                                                    call.error, kErrorCapacity))) {
        return nullptr;
    }
    return doubles_to_java(env, homography, 9);
}

JNIEXPORT jdoubleArray JNICALL Java_com_bischofsnowboards_aruco_NativeCore_homographyLmeds(
    JNIEnv* env, jclass, jdoubleArray plane, jdoubleArray image) {
    const std::vector<double> plane_xy = doubles_of(env, plane);
    const std::vector<double> image_xy = doubles_of(env, image);
    if (odd_pairs(env, plane_xy, "homographyLmeds(plane)") ||
        wrong_size(env, image_xy, plane_xy.size(), "homographyLmeds(image)")) {
        return nullptr;
    }

    Call call;
    double homography[9] = {0.0};
    if (call.failed(env, aruco_homography_lmeds(plane_xy.data(), image_xy.data(),
                                                point_count(plane_xy), homography, call.error,
                                                kErrorCapacity))) {
        return nullptr;
    }
    return doubles_to_java(env, homography, 9);
}

JNIEXPORT jdoubleArray JNICALL Java_com_bischofsnowboards_aruco_NativeCore_refineHomography(
    JNIEnv* env, jclass, jdoubleArray start, jdoubleArray plane, jdoubleArray image) {
    const std::vector<double> start9 = doubles_of(env, start);
    const std::vector<double> plane_xy = doubles_of(env, plane);
    const std::vector<double> image_xy = doubles_of(env, image);
    if (wrong_size(env, start9, 9, "refineHomography(start)") ||
        odd_pairs(env, plane_xy, "refineHomography(plane)") ||
        wrong_size(env, image_xy, plane_xy.size(), "refineHomography(image)")) {
        return nullptr;
    }

    Call call;
    double homography[9] = {0.0};
    if (call.failed(env, aruco_refine_homography(start9.data(), plane_xy.data(), image_xy.data(),
                                                 point_count(plane_xy), homography, call.error,
                                                 kErrorCapacity))) {
        return nullptr;
    }
    return doubles_to_java(env, homography, 9);
}

/// Frei-Modus. Rueckgabe: neun Zahlen Homographie, dann je Marker AUSSER DEM
/// ERSTEN zwei Zahlen Versatz.
///
/// Ein Feld und kein Objekt mit zwei Feldern: die Java-Seite reicht die Zahlen
/// ohnehin flach weiter, und ein Objekt je Aufruf braechte FindClass,
/// GetMethodID und NewObject mit sich - drei Stellen, an denen ein Tippfehler im
/// Klassennamen erst zur Laufzeit auffiele.
JNIEXPORT jdoubleArray JNICALL Java_com_bischofsnowboards_aruco_NativeCore_fitFree(
    JNIEnv* env, jclass, jdoubleArray corners, jdouble marker_mm) {
    const std::vector<double> corners_xy = doubles_of(env, corners);
    if (corners_xy.empty() || corners_xy.size() % 8 != 0) {
        throw_java(env, "java/lang/IllegalArgumentException",
                   "fitFree erwartet vier Ecken je Marker (8 Zahlen), bekam " +
                       std::to_string(corners_xy.size()));
        return nullptr;
    }
    const std::int32_t markers = static_cast<std::int32_t>(corners_xy.size() / 8);

    Call call;
    double homography[9] = {0.0};
    std::vector<double> offsets(static_cast<std::size_t>(markers - 1) * 2U);
    const std::int32_t written =
        aruco_fit_free(corners_xy.data(), markers, marker_mm, homography,
                       offsets.empty() ? nullptr : offsets.data(), markers - 1, call.error,
                       kErrorCapacity);
    if (call.failed(env, written)) {
        return nullptr;
    }

    std::vector<double> result(9U + offsets.size());
    std::copy(homography, homography + 9, result.begin());
    std::copy(offsets.begin(), offsets.end(), result.begin() + 9);
    return doubles_to_java(env, result.data(), static_cast<std::int32_t>(result.size()));
}

/// Streu-Modus. Rueckgabe: neun Zahlen Homographie, dann je Marker DREI Zahlen
/// Lage (x, y, Winkel) - auch fuer den ersten.
///
/// Ein Feld und kein Objekt, aus demselben Grund wie bei fitFree.
JNIEXPORT jdoubleArray JNICALL Java_com_bischofsnowboards_aruco_NativeCore_fitScattered(
    JNIEnv* env, jclass, jdoubleArray corners, jdouble marker_mm) {
    const std::vector<double> corners_xy = doubles_of(env, corners);
    if (corners_xy.empty() || corners_xy.size() % 8 != 0) {
        throw_java(env, "java/lang/IllegalArgumentException",
                   "fitScattered erwartet vier Ecken je Marker (8 Zahlen), bekam " +
                       std::to_string(corners_xy.size()));
        return nullptr;
    }
    const std::int32_t markers = static_cast<std::int32_t>(corners_xy.size() / 8);

    Call call;
    double homography[9] = {0.0};
    std::vector<double> poses(static_cast<std::size_t>(markers) * 3U);
    const std::int32_t written =
        aruco_fit_scattered(corners_xy.data(), markers, marker_mm, homography, poses.data(),
                            markers, call.error, kErrorCapacity);
    if (call.failed(env, written)) {
        return nullptr;
    }

    std::vector<double> result(9U + poses.size());
    std::copy(homography, homography + 9, result.begin());
    std::copy(poses.begin(), poses.end(), result.begin() + 9);
    return doubles_to_java(env, result.data(), static_cast<std::int32_t>(result.size()));
}

// --- Kamera und Ausdehnung ---------------------------------------------------

JNIEXPORT jdoubleArray JNICALL Java_com_bischofsnowboards_aruco_NativeCore_poseFromHomography(
    JNIEnv* env, jclass, jdoubleArray homography, jdouble focal_px, jint width, jint height) {
    const std::vector<double> homography9 = doubles_of(env, homography);
    if (wrong_size(env, homography9, 9, "poseFromHomography")) {
        return nullptr;
    }

    Call call;
    double pose[4] = {0.0};
    if (call.failed(env, aruco_pose_from_homography(homography9.data(), focal_px, width, height,
                                                    pose, call.error, kErrorCapacity))) {
        return nullptr;
    }
    return doubles_to_java(env, pose, 4);
}

JNIEXPORT jdoubleArray JNICALL Java_com_bischofsnowboards_aruco_NativeCore_planeExtent(
    JNIEnv* env, jclass, jdoubleArray homography, jint width, jint height, jdoubleArray hull) {
    const std::vector<double> homography9 = doubles_of(env, homography);
    const std::vector<double> hull_xy = doubles_of(env, hull);
    if (wrong_size(env, homography9, 9, "planeExtent") ||
        odd_pairs(env, hull_xy, "planeExtent(hull)")) {
        return nullptr;
    }

    Call call;
    double area[4] = {0.0};
    if (call.failed(env, aruco_plane_extent(homography9.data(), width, height, hull_xy.data(),
                                            point_count(hull_xy), area, call.error,
                                            kErrorCapacity))) {
        return nullptr;
    }
    return doubles_to_java(env, area, 4);
}

// --- Geometrie ---------------------------------------------------------------

JNIEXPORT jdoubleArray JNICALL Java_com_bischofsnowboards_aruco_NativeCore_convexHull(
    JNIEnv* env, jclass, jdoubleArray points) {
    const std::vector<double> points_xy = doubles_of(env, points);
    if (odd_pairs(env, points_xy, "convexHull")) {
        return nullptr;
    }

    Call call;
    // Die Huelle hat nie mehr Punkte als die Eingabe - ein Puffer dieser Groesse
    // kann nicht zu klein sein, und ARUCO_ERR_CAPACITY ist hier unerreichbar.
    std::vector<double> hull(points_xy.size());
    const std::int32_t written =
        aruco_convex_hull(points_xy.data(), point_count(points_xy),
                          hull.empty() ? nullptr : hull.data(), point_count(points_xy),
                          call.error, kErrorCapacity);
    if (call.failed(env, written)) {
        return nullptr;
    }
    return doubles_to_java(env, hull.data(), written * 2);
}

JNIEXPORT jdouble JNICALL
Java_com_bischofsnowboards_aruco_NativeCore_convexIntersectionArea(JNIEnv* env, jclass,
                                                                   jdoubleArray first,
                                                                   jdoubleArray second) {
    const std::vector<double> first_xy = doubles_of(env, first);
    const std::vector<double> second_xy = doubles_of(env, second);
    if (odd_pairs(env, first_xy, "convexIntersectionArea(first)") ||
        odd_pairs(env, second_xy, "convexIntersectionArea(second)")) {
        return 0.0;
    }

    Call call;
    double area = 0.0;
    if (call.failed(env, aruco_convex_intersection_area(
                             first_xy.data(), point_count(first_xy), second_xy.data(),
                             point_count(second_xy), &area, call.error, kErrorCapacity))) {
        return 0.0;
    }
    return area;
}

JNIEXPORT jdouble JNICALL Java_com_bischofsnowboards_aruco_NativeCore_localPxPerMm(
    JNIEnv* env, jclass, jdoubleArray homography, jdouble x_mm, jdouble y_mm) {
    const std::vector<double> homography9 = doubles_of(env, homography);
    if (wrong_size(env, homography9, 9, "localPxPerMm")) {
        return 0.0;
    }

    Call call;
    double scale = 0.0;
    if (call.failed(env, aruco_local_px_per_mm(homography9.data(), x_mm, y_mm, &scale, call.error,
                                               kErrorCapacity))) {
        return 0.0;
    }
    return scale;
}

JNIEXPORT jdouble JNICALL Java_com_bischofsnowboards_aruco_NativeCore_quadArea(JNIEnv* env, jclass,
                                                                               jdoubleArray quad) {
    const std::vector<double> quad_xy = doubles_of(env, quad);
    if (wrong_size(env, quad_xy, 8, "quadArea")) {
        return 0.0;
    }

    Call call;
    double area = 0.0;
    if (call.failed(env, aruco_quad_area(quad_xy.data(), &area, call.error, kErrorCapacity))) {
        return 0.0;
    }
    return area;
}

// --- Entzerren und Aufbereiten ------------------------------------------------

JNIEXPORT jintArray JNICALL Java_com_bischofsnowboards_aruco_NativeCore_outputSize(
    JNIEnv* env, jclass, jdouble x0, jdouble y0, jdouble x1, jdouble y1, jdouble px_per_mm) {
    Call call;
    std::int32_t width = 0;
    std::int32_t height = 0;
    if (call.failed(env, aruco_output_size(x0, y0, x1, y1, px_per_mm, &width, &height, call.error,
                                           kErrorCapacity))) {
        return nullptr;
    }

    jintArray result = env->NewIntArray(2);
    if (result == nullptr) {
        return nullptr;
    }
    const jint values[2] = {static_cast<jint>(width), static_cast<jint>(height)};
    env->SetIntArrayRegion(result, 0, 2, values);
    return result;
}

/// Entzerren. Der Aufrufer stellt BEIDE Puffer; zurueck kommt die Anzahl der
/// geschriebenen Bytes.
///
/// Wie gross `target` sein muss, sagt `outputSize` mal drei. Ist er zu klein,
/// gibt es eine IllegalArgumentException und KEIN halb gefuelltes Bild - ein
/// abgeschnittenes Rasterbild sieht wie ein Fehler der Kamera aus.
JNIEXPORT jint JNICALL Java_com_bischofsnowboards_aruco_NativeCore_rectify(
    JNIEnv* env, jclass, jobject source, jint width, jint height, jint stride, jint channels,
    jdoubleArray homography, jdouble x0, jdouble y0, jdouble x1, jdouble y1, jdouble px_per_mm,
    jdouble source_px_per_mm, jobject target) {
    const std::vector<double> homography9 = doubles_of(env, homography);
    if (wrong_size(env, homography9, 9, "rectify")) {
        return 0;
    }
    if (width <= 0 || height <= 0 || stride < width * channels) {
        throw_java(env, "java/lang/IllegalArgumentException",
                   "rectify: Bild ohne Flaeche oder Schrittweite kleiner als eine Bildzeile");
        return 0;
    }

    const std::uint8_t* pixels =
        direct_buffer(env, source, static_cast<std::int64_t>(stride) * height, "rectify(source)");
    if (pixels == nullptr) {
        return 0;
    }
    // Nur die Adresse holen, ohne Mindestgroesse: wie viel gebraucht wird, weiss
    // die C-Schnittstelle selbst und sagt es mit ARUCO_ERR_CAPACITY im Klartext.
    std::uint8_t* out = direct_buffer(env, target, 0, "rectify(target)");
    if (out == nullptr) {
        return 0;
    }
    const jlong capacity = env->GetDirectBufferCapacity(target);

    Call call;
    const std::int32_t written = aruco_rectify(
        pixels, width, height, stride, channels, homography9.data(), x0, y0, x1, y1, px_per_mm,
        source_px_per_mm, out, static_cast<std::int32_t>(std::min<jlong>(capacity, INT32_MAX)),
        call.error, kErrorCapacity);
    if (call.failed(env, written)) {
        return 0;
    }
    return written;
}

JNIEXPORT jint JNICALL Java_com_bischofsnowboards_aruco_NativeCore_adjust(
    JNIEnv* env, jclass, jobject source, jint width, jint height, jint stride, jint channels,
    jboolean grayscale, jboolean invert, jdouble brightness, jdouble contrast, jdouble saturation,
    jdouble local_contrast, jdouble edge_boost, jdouble edge_overlay, jstring color_emphasis,
    jdouble emphasis_strength, jdouble threshold, jobject target) {
    if (width <= 0 || height <= 0 || stride < width * channels) {
        throw_java(env, "java/lang/IllegalArgumentException",
                   "adjust: Bild ohne Flaeche oder Schrittweite kleiner als eine Bildzeile");
        return 0;
    }

    const std::uint8_t* pixels =
        direct_buffer(env, source, static_cast<std::int64_t>(stride) * height, "adjust(source)");
    if (pixels == nullptr) {
        return 0;
    }
    std::uint8_t* out =
        direct_buffer(env, target, static_cast<std::int64_t>(width) * height * 3, "adjust(target)");
    if (out == nullptr) {
        return 0;
    }
    const jlong capacity = env->GetDirectBufferCapacity(target);

    const char* emphasis =
        color_emphasis == nullptr ? nullptr : env->GetStringUTFChars(color_emphasis, nullptr);
    const aruco_adjust_options options =
        adjust_options(grayscale, invert, brightness, contrast, saturation, local_contrast,
                       edge_boost, edge_overlay, emphasis, emphasis_strength, threshold);

    Call call;
    const std::int32_t written =
        aruco_adjust(pixels, width, height, stride, channels, &options, out,
                     static_cast<std::int32_t>(std::min<jlong>(capacity, INT32_MAX)), call.error,
                     kErrorCapacity);
    // Freigeben BEVOR eine Ausnahme vorgemerkt wird: ReleaseStringUTFChars ist
    // zwar auch mit anstehender Ausnahme erlaubt, aber die Reihenfolge hier
    // umzudrehen waere eine Regel mehr, die jemand kennen muesste.
    if (emphasis != nullptr) {
        env->ReleaseStringUTFChars(color_emphasis, emphasis);
    }
    if (call.failed(env, written)) {
        return 0;
    }
    return written;
}

JNIEXPORT jboolean JNICALL Java_com_bischofsnowboards_aruco_NativeCore_isIdentity(
    JNIEnv* env, jclass, jboolean grayscale, jboolean invert, jdouble brightness, jdouble contrast,
    jdouble saturation, jdouble local_contrast, jdouble edge_boost, jdouble edge_overlay,
    jstring color_emphasis, jdouble emphasis_strength, jdouble threshold) {
    const char* emphasis =
        color_emphasis == nullptr ? nullptr : env->GetStringUTFChars(color_emphasis, nullptr);
    const aruco_adjust_options options =
        adjust_options(grayscale, invert, brightness, contrast, saturation, local_contrast,
                       edge_boost, edge_overlay, emphasis, emphasis_strength, threshold);

    Call call;
    const std::int32_t answer = aruco_is_identity(&options, call.error, kErrorCapacity);
    if (emphasis != nullptr) {
        env->ReleaseStringUTFChars(color_emphasis, emphasis);
    }
    if (call.failed(env, answer)) {
        return JNI_FALSE;
    }
    return answer != 0 ? JNI_TRUE : JNI_FALSE;
}

/// Umriss im entzerrten Bild. Leeres Feld heisst "nichts Plausibles gefunden" -
/// das ist kein Fehler, und das PDF entsteht dann ohne Linie.
///
/// Wie viele Punkte es werden, steht vorher nicht fest: `approxPolyDP` verkuerzt
/// den Zug, aber wie stark, haengt am Bild. Deshalb ist das die einzige
/// Funktion dieser Schicht, die einen zweiten Anlauf nimmt statt zu raten - und
/// der zweite Puffer ist so gross, dass ein dritter nicht vorkommen kann.
JNIEXPORT jdoubleArray JNICALL Java_com_bischofsnowboards_aruco_NativeCore_findContourMm(
    JNIEnv* env, jclass, jobject source, jint width, jint height, jint stride, jint channels,
    jdouble px_per_mm) {
    if (width <= 0 || height <= 0 || stride < width * channels) {
        throw_java(env, "java/lang/IllegalArgumentException",
                   "findContourMm: Bild ohne Flaeche oder Schrittweite kleiner als eine Bildzeile");
        return nullptr;
    }
    const std::uint8_t* pixels = direct_buffer(
        env, source, static_cast<std::int64_t>(stride) * height, "findContourMm(source)");
    if (pixels == nullptr) {
        return nullptr;
    }

    // Erster Anlauf: reichlich fuer jeden realistischen Umriss - nach
    // approxPolyDP sind es Dutzende bis wenige hundert Punkte. Zweiter Anlauf:
    // das 64-fache. Wer den auch noch sprengt, hat kein Objekt fotografiert
    // sondern Rauschen, und dann ist eine benannte Ausnahme die richtige
    // Antwort und kein Puffer in Gigabyte-Groesse.
    const std::int64_t generous = 4 * (static_cast<std::int64_t>(width) + height) + 1024;
    for (const std::int64_t capacity : {generous, generous * 64}) {
        Call call;
        std::vector<double> polygon(static_cast<std::size_t>(capacity) * 2U);
        const std::int32_t written = aruco_find_contour_mm(
            pixels, width, height, stride, channels, px_per_mm, polygon.data(),
            static_cast<std::int32_t>(std::min<std::int64_t>(capacity, INT32_MAX)), call.error,
            kErrorCapacity);
        if (written >= 0) {
            return doubles_to_java(env, polygon.data(), written * 2);
        }
        if (written != ARUCO_ERR_CAPACITY || capacity > generous) {
            throw_for(env, written, call.error);
            return nullptr;
        }
    }
    return nullptr;  // unerreichbar - die Schleife kehrt in jedem Zweig zurueck
}

}  // extern "C"
