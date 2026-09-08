// INTERN. Was sich alle Uebersetzungseinheiten der C-Schnittstelle teilen.
//
// Diese Datei liegt in src/ und nicht in include/: sie ist keine Schnittstelle,
// sondern das gemeinsame Innenleben von capi.cpp, capi_geometry.cpp und
// capi_image.cpp. Wer gegen den Kern bindet, sieht sie nie.
//
// Drei Dinge stehen hier, und alle drei genau einmal:
//
//  1. `set_error` - Klartext in den Puffer des Aufrufers.
//  2. `guarded`   - der Rahmen, an dem JEDE Ausnahme endet.
//  3. Die Umformung flacher double-Felder in die Typen des Kerns.
//
// Der dritte Punkt ist der Grund, warum es diese Datei ueberhaupt gibt: die drei
// Uebersetzungseinheiten packen dieselben Punktlisten aus, und drei Fassungen
// derselben Schleife waeren drei Stellen, an denen x und y vertauscht werden
// koennen. Ein vertauschtes Paar saehe in jeder Einzelzahl richtig aus.

#ifndef ARUCO_CAPI_INTERNAL_HPP
#define ARUCO_CAPI_INTERNAL_HPP

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <exception>
#include <stdexcept>
#include <string>
#include <vector>

#include "aruco/capi.h"
#include "aruco/enhance.hpp"
#include "aruco/types.hpp"

namespace aruco {
namespace capi {

/// Klartext in den Puffer des Aufrufers, immer nullterminiert.
///
/// `error` darf NULL sein - ein Aufrufer, der die Meldung nicht will, soll nicht
/// gezwungen sein, einen Puffer zu stellen. Gekuerzt wird stumm: eine
/// abgeschnittene Meldung ist immer noch besser als keine.
void set_error(char* error, std::int32_t capacity, const std::string& text);

/// Der Rahmen um jeden Aufruf: Ausnahme -> Rueckgabecode.
///
/// `std::invalid_argument` zuerst, weil das ein Fehler des AUFRUFERS ist (er
/// bekommt ARUCO_ERR_ARGUMENT und kann ihn von einem internen unterscheiden);
/// dann `std::exception`, damit die Meldung von OpenCV wirklich ankommt; dann
/// `...`, damit nichts durchrutscht. Eine Ausnahme durch einen JNI-Rahmen
/// beendet auf Android den Prozess wortlos.
template <typename Work>
std::int32_t guarded(char* error, std::int32_t error_capacity, Work work) {
    try {
        return work();
    } catch (const std::invalid_argument& bad) {
        set_error(error, error_capacity, bad.what());
        return ARUCO_ERR_ARGUMENT;
    } catch (const std::exception& failure) {
        set_error(error, error_capacity, failure.what());
        return ARUCO_ERR_INTERNAL;
    } catch (...) {
        set_error(error, error_capacity, "Unbekannter Fehler im Rechenkern");
        return ARUCO_ERR_INTERNAL;
    }
}

/// Ein flaches (x,y,x,y,...)-Feld als Punktliste.
///
/// Wirft `std::invalid_argument` bei NULL oder negativer Anzahl - `guarded`
/// macht daraus ARUCO_ERR_ARGUMENT.
std::vector<Point2> points_of(const double* flat, std::int32_t count, const char* what);

/// Genau vier Punkte - acht Zahlen.
std::array<Point2, 4> quad_of(const double* flat, const char* what);

/// Neun Zahlen als Homographie, zeilenweise.
Matrix3 matrix_of(const double* flat, const char* what);

/// Eine Punktliste in ein flaches Feld schreiben. Der Aufrufer stellt den Platz;
/// `capacity_points` zaehlt PUNKTE und nicht Zahlen, weil das die Einheit ist,
/// in der sich der Aufrufer verrechnen koennte.
///
/// Rueckgabe: Anzahl geschriebener Punkte, oder ARUCO_ERR_CAPACITY.
std::int32_t write_points(const std::vector<Point2>& points, double* out,
                          std::int32_t capacity_points, char* error,
                          std::int32_t error_capacity, const char* what);

/// Eine ImageView aus den Angaben des Aufrufers. Prueft nichts weiter - der Kern
/// wirft selbst, wenn die Form unbrauchbar ist, und diese Meldung ist besser als
/// eine hier erfundene.
ImageView view_of(const std::uint8_t* data, std::int32_t width, std::int32_t height,
                  std::int32_t stride, std::int32_t channels);

/// Die Reglerstellung aus der C-Form in die des Kerns. `options` darf NULL sein
/// und bedeutet dann "alles neutral" - dieselbe Vorgabe, die AdjustOptions
/// selbst traegt.
AdjustOptions settings_of(const aruco_adjust_options* options);

}  // namespace capi
}  // namespace aruco

#endif  // ARUCO_CAPI_INTERNAL_HPP
