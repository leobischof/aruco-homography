// JNI-Bindung: die Java-Klasse com.bischofsnowboards.aruco.NativeCore.
//
// Das Gegenstueck zu bindings/python.cpp, und mit derselben Haltung geschrieben:
// **die Bindung rechnet nicht.** Sie packt einen Puffer aus, ruft die
// C-Schnittstelle (aruco/capi.h) und packt Zahlen ein. Alles, was misst, steht
// in core/src/ - damit Android, Windows und der Browser dieselbe Rechnung
// bekommen und nicht eine, die zufaellig in einer Bindung wohnt.
//
// Diese Datei uebersetzt auch auf dem BAURECHNER. Das ist kein Zufall: jni.h
// kommt aus dem JDK und nicht aus dem NDK, und eine JVM gibt es auf beiden
// Seiten. Damit laesst sich genau dieser Marshalling-Code auf einem echten
// Java-Prozess ausfuehren, obwohl kein Android-Geraet in Reichweite ist
// (core/tools/JniCheck.java, ./dev.ps1 check-jni). Was danach ungeprueft bleibt,
// ist Androids Linker und die WebView - nicht mehr das Umpacken hier.
//
// **Ein direkter ByteBuffer und kein byte[].** Ein 12-MP-Foto sind 48 MB in
// RGBA. `GetByteArrayElements` darf dafuer eine Kopie anlegen (auf Android tut
// es das), und `GetPrimitiveArrayCritical` haelt stattdessen den
// Speicherbereiniger an - waehrend einer Erkennung, die Sekunden dauert. Ein
// direkter Puffer liegt ausserhalb des Java-Haufens: kein Kopieren, kein
// Anhalten, und der Kern liest genau die Bytes, die die Huelle hineingelegt hat.

#include <jni.h>

#include <cstdint>
#include <string>
#include <vector>

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>

#include "aruco/capi.h"
#include "jni_support.hpp"

// Die gemeinsamen Hilfen dieser Schicht - hier definiert, in jni_support.hpp
// erklaert, und von jni_chain.cpp mitbenutzt. Sie stehen in dieser Datei und
// nicht in einer eigenen, weil sie ohne die Bindung keinen Zweck haben: ein
// Umpacker fuer eine Schnittstelle, die es nicht gibt, ist nichts.
namespace aruco {
namespace jni {

void throw_java(JNIEnv* env, const char* class_name, const std::string& message) {
    jclass failure = env->FindClass(class_name);
    if (failure != nullptr) {
        env->ThrowNew(failure, message.c_str());
    }
}

void throw_for(JNIEnv* env, std::int32_t code, const char* error) {
    const std::string message = error[0] != '\0' ? error : "Rechenkern ohne Meldung";
    if (code == ARUCO_ERR_ARGUMENT || code == ARUCO_ERR_CAPACITY) {
        throw_java(env, "java/lang/IllegalArgumentException", message);
        return;
    }
    throw_java(env, "java/lang/RuntimeException", message);
}

std::vector<double> doubles_of(JNIEnv* env, jdoubleArray array) {
    if (array == nullptr) {
        return {};
    }
    const jsize count = env->GetArrayLength(array);
    std::vector<double> values(static_cast<std::size_t>(count));
    if (count > 0) {
        // GetDoubleArrayRegion und nicht GetDoubleArrayElements: es kopiert
        // ohnehin, gibt aber nichts zurueckzugeben - und ein vergessenes
        // Release waere ein Leck je Reglerzug. Durch diese Funktion gehen
        // Homographien und Punktlisten, nie ein Bild.
        env->GetDoubleArrayRegion(array, 0, count, values.data());
    }
    return values;
}

jdoubleArray doubles_to_java(JNIEnv* env, const double* values, std::int32_t count) {
    jdoubleArray result = env->NewDoubleArray(count);
    if (result == nullptr) {
        return nullptr;  // OutOfMemoryError steht bereits an
    }
    if (count > 0) {
        env->SetDoubleArrayRegion(result, 0, count, values);
    }
    return result;
}

std::uint8_t* direct_buffer(JNIEnv* env, jobject buffer, std::int64_t needed,
                            const char* what) {
    auto* data = static_cast<std::uint8_t*>(env->GetDirectBufferAddress(buffer));
    if (data == nullptr) {
        throw_java(env, "java/lang/IllegalArgumentException",
                   std::string(what) + " erwartet einen DIREKTEN ByteBuffer "
                                       "(ByteBuffer.allocateDirect)");
        return nullptr;
    }
    const jlong provided = env->GetDirectBufferCapacity(buffer);
    if (provided < needed) {
        throw_java(env, "java/lang/IllegalArgumentException",
                   std::string(what) + ": ByteBuffer fasst " + std::to_string(provided) +
                       " Bytes, gebraucht werden " + std::to_string(needed));
        return nullptr;
    }
    return data;
}

}  // namespace jni
}  // namespace aruco

namespace {

using aruco::jni::direct_buffer;
using aruco::jni::kErrorCapacity;
using aruco::jni::throw_for;
using aruco::jni::throw_java;

}  // namespace

extern "C" {

JNIEXPORT jstring JNICALL
Java_com_bischofsnowboards_aruco_NativeCore_openCvVersion(JNIEnv* env, jclass) {
    return env->NewStringUTF(aruco_opencv_version());
}

JNIEXPORT jstring JNICALL
Java_com_bischofsnowboards_aruco_NativeCore_dictionaryName(JNIEnv* env, jclass) {
    return env->NewStringUTF(aruco_dictionary_name());
}

JNIEXPORT jdouble JNICALL
Java_com_bischofsnowboards_aruco_NativeCore_markerMmNominal(JNIEnv*, jclass) {
    return aruco_marker_mm_nominal();
}

JNIEXPORT jint JNICALL
Java_com_bischofsnowboards_aruco_NativeCore_dictionarySize(JNIEnv*, jclass) {
    return aruco_dictionary_size();
}

/// Marker finden. Rueckgabe: je Marker NEUN double - ID, dann TL,TR,BR,BL als x,y.
///
/// Ein flaches double[] und keine Objektliste. Ein Marker-Objekt je Fund waere
/// lesbarer und braechte fuenf JNI-Aufrufe je Marker mit sich (FindClass,
/// GetMethodID, NewObject, ...) - und die Oberflaeche reicht die Zahlen ohnehin
/// als JSON an die WebView weiter, wo sie wieder flach sind. Die ID passt
/// verlustfrei in ein double: sie ist ein kleiner ganzzahliger Wert, und double
/// stellt jede ganze Zahl bis 2^53 exakt dar.
///
/// `channels` ist 1 (grau), 3 (BGR) oder 4 (RGBA). Vier ist der Fall, den
/// Android liefert - `Bitmap.copyPixelsToBuffer` gibt bei ARGB_8888 RGBA in
/// dieser Byte-Reihenfolge, und eine Bitmap-Konfiguration in BGR gibt es dort
/// nicht. Umgewandelt wird deshalb HIER, in der Huelle, und nicht im Kern: der
/// Kern nimmt rohe Pixel in genau zwei Formen entgegen (aruco/types.hpp), und
/// das Dekodieren gehoert auf jedes Ziel einzeln.
JNIEXPORT jdoubleArray JNICALL Java_com_bischofsnowboards_aruco_NativeCore_detectMarkers(
    JNIEnv* env, jclass, jobject pixels, jint width, jint height, jint stride, jint channels,
    jboolean enhance_contrast) {
    if (width <= 0 || height <= 0) {
        throw_java(env, "java/lang/IllegalArgumentException", "Bild ohne Flaeche");
        return nullptr;
    }
    if (stride < width * channels) {
        throw_java(env, "java/lang/IllegalArgumentException",
                   "Schrittweite kleiner als eine Bildzeile");
        return nullptr;
    }
    // Ohne die Groessenpruefung in direct_buffer laese der Kern ueber das Ende
    // des Puffers hinaus. Der Aufrufer nennt Breite, Hoehe und Schrittweite
    // selbst; ein Tippfehler dort ist sonst ein Absturz ohne Zusammenhang.
    const std::uint8_t* data =
        direct_buffer(env, pixels, static_cast<std::int64_t>(stride) * height, "detectMarkers");
    if (data == nullptr) {
        return nullptr;
    }

    // RGBA -> BGR. Nur in diesem Zweig entsteht eine Kopie; bei 1 und 3 Kanaelen
    // liest der Kern den Puffer der Huelle unveraendert.
    cv::Mat converted;
    const std::uint8_t* view = data;
    jint view_stride = stride;
    jint view_channels = channels;
    if (channels == 4) {
        const cv::Mat rgba(height, width, CV_8UC4, const_cast<std::uint8_t*>(data),
                           static_cast<std::size_t>(stride));
        cv::cvtColor(rgba, converted, cv::COLOR_RGBA2BGR);
        view = converted.ptr<std::uint8_t>(0);
        view_stride = static_cast<jint>(converted.step);
        view_channels = 3;
    }

    const std::int32_t capacity = aruco_dictionary_size();
    if (capacity < 0) {
        throw_java(env, "java/lang/RuntimeException", "Woerterbuch nicht lesbar");
        return nullptr;
    }

    std::vector<aruco_marker> found(static_cast<std::size_t>(capacity));
    char error[kErrorCapacity] = {0};
    const std::int32_t count =
        aruco_detect_markers(view, width, height, view_stride, view_channels,
                             enhance_contrast == JNI_TRUE ? 1 : 0, found.data(), capacity, error,
                             kErrorCapacity);
    if (count < 0) {
        throw_for(env, count, error);
        return nullptr;
    }

    jdoubleArray result = env->NewDoubleArray(count * 9);
    if (result == nullptr) {
        return nullptr;  // OutOfMemoryError steht bereits an
    }
    std::vector<jdouble> flat(static_cast<std::size_t>(count) * 9U);
    for (std::int32_t index = 0; index < count; ++index) {
        flat[static_cast<std::size_t>(index) * 9U] = static_cast<jdouble>(found[index].id);
        for (int value = 0; value < 8; ++value) {
            flat[static_cast<std::size_t>(index) * 9U + 1U + static_cast<std::size_t>(value)] =
                found[index].corners[value];
        }
    }
    env->SetDoubleArrayRegion(result, 0, count * 9, flat.data());
    return result;
}

/// Die Modulbits eines Markers - ein Byte je Modul, zeilenweise, 0 = schwarz.
///
/// Damit zeichnet web/pdf/markersheet.js das Markerblatt auf dem Geraet, ohne
/// dass ein zweites OpenCV in die WebView muesste. Genau dafuer nimmt jenes
/// Modul die Bits von aussen entgegen.
JNIEXPORT jbyteArray JNICALL Java_com_bischofsnowboards_aruco_NativeCore_markerBits(
    JNIEnv* env, jclass, jint marker_id, jint modules) {
    if (modules <= 0 || modules > 64) {
        throw_java(env, "java/lang/IllegalArgumentException", "modules ausserhalb 1..64");
        return nullptr;
    }
    std::vector<std::uint8_t> bits(static_cast<std::size_t>(modules) *
                                   static_cast<std::size_t>(modules));
    char error[kErrorCapacity] = {0};
    const std::int32_t written = aruco_marker_bits(marker_id, modules, bits.data(),
                                                   static_cast<std::int32_t>(bits.size()), error,
                                                   kErrorCapacity);
    if (written < 0) {
        throw_for(env, written, error);
        return nullptr;
    }

    jbyteArray result = env->NewByteArray(written);
    if (result == nullptr) {
        return nullptr;
    }
    env->SetByteArrayRegion(result, 0, written, reinterpret_cast<const jbyte*>(bits.data()));
    return result;
}

}  // extern "C"
