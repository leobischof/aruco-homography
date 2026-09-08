// Die C-Schnittstelle. Sie rechnet NICHTS - sie packt um und faengt.
//
// Jede Zeile, die hier rechnete, waere eine Rechnung, die das Python-Modul und
// der Pruefstand nicht sehen: die gehen durch aruco::detect_markers, nicht hier
// vorbei. Deshalb ist diese Datei absichtlich dumm.
//
// Die zweite Aufgabe ist die wichtigere: **hier endet jede Ausnahme.** Auf
// Android sitzt hinter dieser Grenze eine JVM. Eine C++-Ausnahme, die sich durch
// einen JNI-Rahmen entfaltet, ist nicht definiert - in der Praxis stirbt der
// Prozess ohne Meldung, und der Bediener sieht die App verschwinden. Also faengt
// jede Funktion `...` und macht daraus einen Code plus Klartext.

#include "aruco/capi.h"

#include <cstddef>
#include <cstring>
#include <string>
#include <vector>

#include <opencv2/core.hpp>
#include <opencv2/core/version.hpp>

#include "aruco/constants.hpp"
#include "aruco/detect.hpp"
#include "aruco/types.hpp"
#include "capi_internal.hpp"
#include "dictionary.hpp"

namespace {

// set_error und guarded stehen seit der Erweiterung der Schnittstelle in
// src/capi_support.cpp: capi_geometry.cpp und capi_image.cpp brauchen genau
// dieselben, und drei Fassungen desselben Rahmens waeren drei Stellen, an denen
// eine Ausnahme kuenftig doch noch durchkaeme.
using aruco::capi::guarded;
using aruco::capi::set_error;

}  // namespace

extern "C" {

std::int32_t aruco_detect_markers(const std::uint8_t* data, std::int32_t width,
                                  std::int32_t height, std::int32_t stride,
                                  std::int32_t channels, std::int32_t enhance_contrast,
                                  aruco_marker* out, std::int32_t out_capacity, char* error,
                                  std::int32_t error_capacity) {
    if (out == nullptr || out_capacity < 0) {
        set_error(error, error_capacity, "Kein Ausgabepuffer");
        return ARUCO_ERR_ARGUMENT;
    }

    return guarded(error, error_capacity, [&]() -> std::int32_t {
        aruco::ImageView image;
        image.data = data;
        image.width = width;
        image.height = height;
        image.stride = stride;
        image.channels = channels;

        // detect_markers wirft std::invalid_argument bei einer unbrauchbaren
        // ImageView. Das ist ein FEHLER DES AUFRUFERS und kein interner - er
        // bekommt deshalb ARUCO_ERR_ARGUMENT und nicht ARUCO_ERR_INTERNAL,
        // damit die Huelle die beiden Faelle auseinanderhalten kann. Diese
        // Unterscheidung trifft seit der Erweiterung `guarded` selbst, fuer
        // ALLE Funktionen dieser Schnittstelle - hier stand sie frueher von
        // Hand, und dass sie es nur hier tat, war die Ausnahme.
        const std::vector<aruco::Marker> markers = aruco::detect_markers(image,
                                                                        enhance_contrast != 0);

        if (static_cast<std::size_t>(out_capacity) < markers.size()) {
            set_error(error, error_capacity,
                      "Ausgabepuffer zu klein: " + std::to_string(markers.size()) +
                          " Marker gefunden, Platz fuer " + std::to_string(out_capacity) +
                          " (siehe aruco_dictionary_size)");
            return ARUCO_ERR_CAPACITY;
        }

        for (std::size_t index = 0; index < markers.size(); ++index) {
            const aruco::Marker& marker = markers[index];
            out[index].id = marker.id;
            for (int corner = 0; corner < 4; ++corner) {
                out[index].corners[corner * 2] = marker.corners[corner][0];
                out[index].corners[corner * 2 + 1] = marker.corners[corner][1];
            }
        }
        return static_cast<std::int32_t>(markers.size());
    });
}

std::int32_t aruco_marker_bits(std::int32_t marker_id, std::int32_t modules, std::uint8_t* out,
                               std::int32_t out_capacity, char* error,
                               std::int32_t error_capacity) {
    if (out == nullptr || modules <= 0) {
        set_error(error, error_capacity, "Kein Ausgabepuffer oder modules <= 0");
        return ARUCO_ERR_ARGUMENT;
    }
    const std::int32_t needed = modules * modules;
    if (out_capacity < needed) {
        set_error(error, error_capacity,
                  "Ausgabepuffer zu klein: " + std::to_string(needed) + " Bytes noetig");
        return ARUCO_ERR_CAPACITY;
    }

    return guarded(error, error_capacity, [&]() -> std::int32_t {
        const cv::aruco::Dictionary& dictionary = aruco::configured_dictionary();
        if (marker_id < 0 || marker_id >= dictionary.bytesList.rows) {
            set_error(error, error_capacity,
                      "Marker-ID " + std::to_string(marker_id) + " liegt nicht in " +
                          std::string(aruco::constants::ARUCO_DICT_NAME));
            return ARUCO_ERR_ARGUMENT;
        }

        // sidePixels == modules: ein Pixel je Modul. Genau das erwartet
        // web/pdf/markersheet.js, das jedes Modul als Vektorrechteck zeichnet -
        // ein groesseres Bild muesste es erst wieder herunterrechnen, und dabei
        // entstuende die Frage, welcher Rundung man glaubt.
        cv::Mat image;
        dictionary.generateImageMarker(marker_id, modules, image, 1);

        // generateImageMarker liefert CV_8UC1 in genau der Groesse - trotzdem
        // nachsehen. Ein stiller Groessenwechsel in einer kuenftigen
        // OpenCV-Fassung schriebe sonst ueber fremden Speicher.
        if (image.type() != CV_8UC1 || image.rows != modules || image.cols != modules) {
            set_error(error, error_capacity, "generateImageMarker lieferte ein unerwartetes Bild");
            return ARUCO_ERR_INTERNAL;
        }

        for (std::int32_t row = 0; row < modules; ++row) {
            std::memcpy(out + static_cast<std::ptrdiff_t>(row) * modules,
                        image.ptr<std::uint8_t>(row), static_cast<std::size_t>(modules));
        }
        return needed;
    });
}

std::int32_t aruco_dictionary_size(void) {
    // Kein guarded(): der Aufrufer hat hier keinen Fehlerpuffer, und ein Wurf
    // waere ohnehin nur bei einem unbekannten Woerterbuchnamen moeglich - der
    // faellt dann beim ersten Erkennungslauf mit Klartext auf.
    try {
        return aruco::configured_dictionary().bytesList.rows;
    } catch (...) {
        return ARUCO_ERR_INTERNAL;
    }
}

const char* aruco_dictionary_name(void) {
    // constants::ARUCO_DICT_NAME ist ein string_view auf ein Literal im
    // erzeugten Kopf - also statisch und nullterminiert. Trotzdem einmal in ein
    // eigenes std::string kopiert: ein string_view MUSS nicht nullterminiert
    // sein, und diese Zusage will die C-Schnittstelle nicht von der Form der
    // erzeugten Datei abhaengig machen.
    static const std::string name(aruco::constants::ARUCO_DICT_NAME);
    return name.c_str();
}

double aruco_marker_mm_nominal(void) { return aruco::constants::MARKER_MM_NOMINAL; }

const char* aruco_opencv_version(void) { return CV_VERSION; }

}  // extern "C"
