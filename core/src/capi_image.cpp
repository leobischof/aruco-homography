// Die C-Schnittstelle, Teil 3: die Funktionen, die BILDER zurueckgeben.
//
// Drei davon gibt es - entzerren, aufbereiten, Umriss suchen -, und alle drei
// stellen dieselbe Frage: **wem gehoert das Ergebnis?** Diese Datei ist die
// Antwort, und sie lautet: dem Aufrufer, von Anfang an.
//
// WARUM NICHT WIE IM BROWSER. core/bindings/web.cpp gibt ein `Raster` zurueck,
// das JavaScript freigeben muss. Das ist dort richtig, weil embind gar nichts
// anderes anbietet - und es ist trotzdem genau die Stelle, an der ein Leck
// entsteht: `web/vision/core.js` ist eigens dafuer da, dass NIEMAND SONST im
// Browser-Bau `delete()` schreiben muss. Auf einem Telefon waere derselbe
// Fehler teurer. Ein Rasterbild sind bei 300 dpi zweistellige Megabyte; drei
// vergessene in einer Sitzung, und Android beendet den Prozess. Was der
// Bediener sieht, ist eine App, die beim dritten Foto verschwindet - und was er
// meldet, ist "das dritte Foto war schlecht".
//
// Deshalb: **der Aufrufer stellt den Puffer.** Er kann das, weil die Groesse
// vorher feststeht (aruco_output_size fuer das Entzerren, Breite mal Hoehe mal
// drei fuer die Aufbereitung). Es gibt nichts freizugeben, also gibt es auch
// nichts zu vergessen - und ein zu kleiner Puffer ist ein Fehlercode und keine
// halb gefuellte Bildzeile.
//
// WAS DAS KOSTET, ehrlich: der Kern legt das Rasterbild intern an
// (aruco::rectify gibt einen ImageBuffer) und kopiert es dann hinueber. Die
// Speicherspitze ist also das Doppelte der Ausgabe. Das ist derselbe Faktor,
// den der Browser-Bau ohnehin zahlt (`takeRaster` kopiert aus dem Haldenspeicher
// heraus, bevor es freigibt), und es ist der Preis dafuer, dass core/src/ von
// allen drei Zielen unveraendert benutzt wird. Ein Ausgabepuffer bis nach
// aruco::rectify durchgereicht wuerde diese Spitze halbieren und dafuer alle
// drei Bindungen anfassen; das gehoert in einen eigenen Schritt und nicht
// nebenbei hier hinein.

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include "aruco/capi.h"
#include "aruco/contour.hpp"
#include "aruco/enhance.hpp"
#include "aruco/rectify.hpp"
#include "capi_internal.hpp"

namespace {

using aruco::capi::guarded;
using aruco::capi::matrix_of;
using aruco::capi::set_error;
using aruco::capi::settings_of;
using aruco::capi::view_of;
using aruco::capi::write_points;

/// Ein Ergebnisbild in den Puffer des Aufrufers - oder ARUCO_ERR_CAPACITY.
///
/// Die einzige Stelle in dieser Datei, an der Bildbytes die Seite wechseln.
/// Geprueft wird gegen `std::int64_t`: Breite mal Hoehe mal drei laeuft bei
/// grossen Rastern in `int` ueber, und ein uebergelaufener Vergleich haette
/// genau die Kuerzung erlaubt, die hier verhindert werden soll.
std::int32_t deliver(const aruco::ImageBuffer& buffer, std::uint8_t* out,
                     std::int32_t out_capacity, char* error, std::int32_t error_capacity,
                     const char* what) {
    const std::int64_t needed = static_cast<std::int64_t>(buffer.data.size());
    if (needed > static_cast<std::int64_t>(out_capacity)) {
        set_error(error, error_capacity,
                  std::string(what) + ": Ausgabepuffer zu klein - " + std::to_string(needed) +
                      " Bytes noetig, " + std::to_string(out_capacity) + " vorhanden");
        return ARUCO_ERR_CAPACITY;
    }
    std::memcpy(out, buffer.data.data(), buffer.data.size());
    return static_cast<std::int32_t>(needed);
}

/// Breite mal Hoehe mal drei, ohne Ueberlauf. Negativ, wenn es nicht in einen
/// int32 passt - dann ist der Aufrufer ohnehin am Ende seines Puffers.
std::int64_t bgr_bytes(std::int32_t width, std::int32_t height) {
    if (width <= 0 || height <= 0) {
        return -1;
    }
    return static_cast<std::int64_t>(width) * static_cast<std::int64_t>(height) * 3;
}

}  // namespace

extern "C" {

std::int32_t aruco_rectify(const std::uint8_t* data, std::int32_t width, std::int32_t height,
                           std::int32_t stride, std::int32_t channels,
                           const double* homography9, double x0, double y0, double x1,
                           double y1, double px_per_mm, double source_px_per_mm,
                           std::uint8_t* out, std::int32_t out_capacity, char* error,
                           std::int32_t error_capacity) {
    if (out == nullptr || out_capacity < 0) {
        set_error(error, error_capacity, "aruco_rectify: kein Ausgabepuffer");
        return ARUCO_ERR_ARGUMENT;
    }

    return guarded(error, error_capacity, [&]() -> std::int32_t {
        // Erst die Groesse, dann die Arbeit. Ein zu kleiner Puffer soll den
        // Aufrufer nicht erst NACH einer Sekunde warpPerspective erreichen -
        // und auf einem Telefon ist eine Sekunde umsonst eine spuerbare.
        int out_width = 0;
        int out_height = 0;
        aruco::output_size(aruco::Extent{x0, y0, x1, y1}, px_per_mm, out_width, out_height);
        const std::int64_t needed = bgr_bytes(out_width, out_height);
        if (needed < 0 || needed > static_cast<std::int64_t>(out_capacity)) {
            set_error(error, error_capacity,
                      "aruco_rectify: Ausgabepuffer zu klein - " + std::to_string(needed) +
                          " Bytes noetig (" + std::to_string(out_width) + "x" +
                          std::to_string(out_height) + "x3), " +
                          std::to_string(out_capacity) + " vorhanden");
            return ARUCO_ERR_CAPACITY;
        }

        const aruco::ImageBuffer buffer = aruco::rectify(
            view_of(data, width, height, stride, channels), matrix_of(homography9, "homography"),
            aruco::Extent{x0, y0, x1, y1}, px_per_mm, source_px_per_mm);
        return deliver(buffer, out, out_capacity, error, error_capacity, "aruco_rectify");
    });
}

std::int32_t aruco_adjust(const std::uint8_t* data, std::int32_t width, std::int32_t height,
                          std::int32_t stride, std::int32_t channels,
                          const aruco_adjust_options* options, std::uint8_t* out,
                          std::int32_t out_capacity, char* error,
                          std::int32_t error_capacity) {
    if (out == nullptr || out_capacity < 0) {
        set_error(error, error_capacity, "aruco_adjust: kein Ausgabepuffer");
        return ARUCO_ERR_ARGUMENT;
    }

    return guarded(error, error_capacity, [&]() -> std::int32_t {
        // Invariante 6: die Aufbereitung ist kosmetisch. Die Ausgabe hat exakt
        // die Groesse der Eingabe, und wer hier etwas anderes misst, hat einen
        // Regler gebaut, der Millimeter verschiebt.
        const std::int64_t needed = bgr_bytes(width, height);
        if (needed < 0 || needed > static_cast<std::int64_t>(out_capacity)) {
            set_error(error, error_capacity,
                      "aruco_adjust: Ausgabepuffer zu klein - " + std::to_string(needed) +
                          " Bytes noetig, " + std::to_string(out_capacity) + " vorhanden");
            return ARUCO_ERR_CAPACITY;
        }

        const aruco::ImageBuffer buffer =
            aruco::adjust(view_of(data, width, height, stride, channels), settings_of(options));
        return deliver(buffer, out, out_capacity, error, error_capacity, "aruco_adjust");
    });
}

std::int32_t aruco_is_identity(const aruco_adjust_options* options, char* error,
                               std::int32_t error_capacity) {
    return guarded(error, error_capacity, [&]() -> std::int32_t {
        return aruco::is_identity(settings_of(options)) ? 1 : 0;
    });
}

std::int32_t aruco_find_contour_mm(const std::uint8_t* data, std::int32_t width,
                                   std::int32_t height, std::int32_t stride,
                                   std::int32_t channels, double px_per_mm, double* out_xy,
                                   std::int32_t capacity_points, char* error,
                                   std::int32_t error_capacity) {
    if (out_xy == nullptr || capacity_points < 0) {
        set_error(error, error_capacity, "aruco_find_contour_mm: kein Ausgabepuffer");
        return ARUCO_ERR_ARGUMENT;
    }

    return guarded(error, error_capacity, [&]() -> std::int32_t {
        const std::vector<aruco::Point2> polygon =
            aruco::find_contour_mm(view_of(data, width, height, stride, channels), px_per_mm);
        // Leer ist kein Fehler: dann wird das PDF ohne Kontur gebaut. Lieber
        // keine Linie als eine falsche.
        return write_points(polygon, out_xy, capacity_points, error, error_capacity,
                            "aruco_find_contour_mm");
    });
}

}  // extern "C"
