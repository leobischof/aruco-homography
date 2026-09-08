// Der C++-Pruefstand gegen shared/fixtures/ - dieselben Szenen, dieselbe
// Grundwahrheit und dieselbe Toleranz wie tests/test_conformance.py.
//
// Gemessen wird gegen die GRUNDWAHRHEIT, nicht gegen Python. Wuerde hier
// Pythons Ergebnis stehen, erbte C++ jede Schiefe der Referenz und niemand saehe
// es (docs/cpp-migration/README.md, Abschnitt 4).
//
// Dieses Programm ist KEIN Kern und duerfte imgcodecs benutzen - es tut es
// trotzdem nicht: die Pixel kommen als rohe Bytes aus dem Fixture-Paket
// (core/tools/make_fixture_pack.py), damit zwischen den beiden Messungen kein
// PNG-Dekoder steht.
//
// Aufruf:  aruco_conformance <pfad/zu/fixtures.txt> [--ecken] [--capi]
//
// `--capi` misst durch die C-Schnittstelle (aruco/capi.h) statt geradewegs durch
// aruco::detect_markers. Dieselben Szenen, dieselbe Grundwahrheit, dieselbe
// Toleranz - und damit ist die Grenze, an der Android andockt, keine Behauptung
// mehr, sondern eine gemessene Strecke. Ohne diesen Schalter waere die C-Schicht
// die einzige Stelle im Kern, die kein Pruefstand je ausfuehrt.
//
// `--ecken` haengt hinter jede Szene eine Zeile je Ecke mit der vollen
// double-Genauigkeit (%.17g, also verlustfrei zurueckzulesen). Die gerundeten
// 0,4 Stellen der Normalausgabe reichen, um eine Toleranz zu pruefen, aber nicht,
// um zwei ZIELE gegeneinander zu halten: Windows, Android und WASM sollen
// dieselben Bits liefern, und ein Unterschied in der 12. Stelle waere in
// "0.2337 px" unsichtbar. Genau dieser Vergleich ist der Zweck von Stufe 4
// (docs/cpp-migration/stage-4-cross-targets.md).

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

#include "aruco/capi.h"
#include "aruco/detect.hpp"

namespace {

struct SceneFixture {
    std::string name;
    std::string raw;
    int width = 0;
    int height = 0;
    int channels = 0;
    double corner_tolerance_px = 0.0;
    std::map<int, std::vector<double>> corners;  // ID -> 8 Zahlen, TL TR BR BL
};

/// Ein Wort erwarten und einlesen, was danach kommt.
void expect(std::ifstream& stream, const char* word) {
    std::string token;
    if (!(stream >> token) || token != word) {
        throw std::runtime_error(std::string("Fixture-Paket: '") + word + "' erwartet, '" +
                                 token + "' gelesen");
    }
}

template <typename T>
T read(std::ifstream& stream) {
    T value{};
    if (!(stream >> value)) {
        throw std::runtime_error("Fixture-Paket: unerwartetes Ende");
    }
    return value;
}

std::vector<SceneFixture> read_manifest(const std::string& path) {
    std::ifstream stream(path);
    if (!stream) {
        throw std::runtime_error("Fixture-Paket nicht lesbar: " + path);
    }

    expect(stream, "scenes");
    const int count = read<int>(stream);

    std::vector<SceneFixture> scenes;
    for (int index = 0; index < count; ++index) {
        SceneFixture scene;
        expect(stream, "scene");
        scene.name = read<std::string>(stream);
        expect(stream, "raw");
        scene.raw = read<std::string>(stream);
        expect(stream, "size");
        scene.width = read<int>(stream);
        scene.height = read<int>(stream);
        scene.channels = read<int>(stream);
        expect(stream, "tol_corner_px");
        scene.corner_tolerance_px = read<double>(stream);

        expect(stream, "markers");
        const int markers = read<int>(stream);
        for (int marker = 0; marker < markers; ++marker) {
            expect(stream, "marker");
            const int id = read<int>(stream);
            std::vector<double> values(8);
            for (double& value : values) {
                value = read<double>(stream);
            }
            scene.corners[id] = values;
        }
        scenes.push_back(scene);
    }
    return scenes;
}

std::vector<std::uint8_t> read_raw(const std::string& path, std::size_t expected) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) {
        throw std::runtime_error("Rohbild nicht lesbar: " + path);
    }
    std::vector<std::uint8_t> bytes((std::istreambuf_iterator<char>(stream)),
                                    std::istreambuf_iterator<char>());
    if (bytes.size() != expected) {
        throw std::runtime_error("Rohbild " + path + ": " + std::to_string(bytes.size()) +
                                 " Bytes statt " + std::to_string(expected));
    }
    return bytes;
}

/// Eine Szene messen. Gibt den groessten Eckfehler zurueck; `ok` sagt, ob die
/// Toleranz gehalten wurde.
///
/// `mode` benennt den Durchlauf in der Ecken-Ausgabe ("clahe" oder "grau"); ist
/// er leer, unterbleibt sie.
double check(const SceneFixture& scene, const std::string& directory, bool enhance_contrast,
             bool& ok, const char* mode, bool through_capi) {
    const std::size_t expected =
        static_cast<std::size_t>(scene.width) * scene.height * scene.channels;
    const std::vector<std::uint8_t> pixels = read_raw(directory + "/" + scene.raw, expected);

    aruco::ImageView image;
    image.data = pixels.data();
    image.width = scene.width;
    image.height = scene.height;
    image.stride = scene.width * scene.channels;
    image.channels = scene.channels;

    // Beide Wege fuellen dieselbe Liste. Hinter der C-Schnittstelle steckt genau
    // dieselbe Funktion - geprueft wird also keine zweite Rechnung, sondern dass
    // beim Umpacken nichts verlorengeht. Genau das kann schiefgehen: ein
    // vertauschtes Eckenpaar in capi.cpp saehe in jeder Einzelzahl richtig aus
    // und verzoege trotzdem jede Homographie, die darauf aufbaut.
    std::vector<aruco::Marker> markers;
    if (through_capi) {
        const std::int32_t capacity = aruco_dictionary_size();
        if (capacity < 0) {
            throw std::runtime_error("aruco_dictionary_size() fehlgeschlagen");
        }
        std::vector<aruco_marker> found(static_cast<std::size_t>(capacity));
        char error[512] = {0};
        const std::int32_t count = aruco_detect_markers(
            image.data, image.width, image.height, image.stride, image.channels,
            enhance_contrast ? 1 : 0, found.data(), capacity, error,
            static_cast<std::int32_t>(sizeof(error)));
        if (count < 0) {
            throw std::runtime_error(std::string("aruco_detect_markers: ") + error);
        }
        for (std::int32_t index = 0; index < count; ++index) {
            aruco::Marker marker;
            marker.id = found[index].id;
            for (int corner = 0; corner < 4; ++corner) {
                marker.corners[corner][0] = found[index].corners[corner * 2];
                marker.corners[corner][1] = found[index].corners[corner * 2 + 1];
            }
            markers.push_back(marker);
        }
    } else {
        markers = aruco::detect_markers(image, enhance_contrast);
    }

    if (markers.size() != scene.corners.size()) {
        std::printf("  [x] %zu Marker gefunden, %zu erwartet\n", markers.size(),
                    scene.corners.size());
        ok = false;
        return 0.0;
    }

    double worst = 0.0;
    double sum = 0.0;
    int counted = 0;
    for (const aruco::Marker& marker : markers) {
        const auto truth = scene.corners.find(marker.id);
        if (truth == scene.corners.end()) {
            std::printf("  [x] Marker %d steht nicht in der Grundwahrheit\n", marker.id);
            ok = false;
            continue;
        }

        double marker_worst = 0.0;
        for (int corner = 0; corner < 4; ++corner) {
            const double dx = marker.corners[corner][0] - truth->second[corner * 2];
            const double dy = marker.corners[corner][1] - truth->second[corner * 2 + 1];
            const double error = std::sqrt(dx * dx + dy * dy);
            marker_worst = std::max(marker_worst, error);
            sum += error;
            ++counted;

            if (mode != nullptr) {
                // Eine Zeile, sechs Felder, keine Ausrichtung: das liest ein
                // diff und kein Mensch. Die Grundwahrheit steht bewusst NICHT
                // dabei - sie kommt auf jedem Ziel aus derselben Datei und
                // wuerde den Vergleich nur verwaessern.
                std::printf("ecke %s %s %d %d %.17g %.17g %.17g\n", scene.name.c_str(), mode,
                            marker.id, corner, marker.corners[corner][0],
                            marker.corners[corner][1], error);
            }
        }
        worst = std::max(worst, marker_worst);

        const bool held = marker_worst <= scene.corner_tolerance_px;
        std::printf("  %s Marker %d: groesster Eckfehler %.4f px (Toleranz %.4f px)\n",
                    held ? "[ok]" : "[x] ", marker.id, marker_worst, scene.corner_tolerance_px);
        if (!held) {
            ok = false;
        }
    }

    std::printf("       Mittel %.4f px, groesster %.4f px ueber %d Ecken\n",
                counted > 0 ? sum / counted : 0.0, worst, counted);
    return worst;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr,
                     "Aufruf: aruco_conformance <pfad/zu/fixtures.txt> [--ecken] [--capi]\n");
        return 2;
    }
    bool dump_corners = false;
    bool through_capi = false;
    for (int index = 2; index < argc; ++index) {
        const std::string flag = argv[index];
        if (flag == "--ecken") {
            dump_corners = true;
        } else if (flag == "--capi") {
            through_capi = true;
        } else {
            std::fprintf(stderr, "Unbekannter Schalter: %s\n", argv[index]);
            return 2;
        }
    }

    const std::string manifest = argv[1];
    const std::string directory = manifest.substr(0, manifest.find_last_of("/\\"));

    try {
        bool ok = true;
        for (const SceneFixture& scene : read_manifest(manifest)) {
            std::printf("Szene %s (%dx%d, %d Kanaele)\n", scene.name.c_str(), scene.width,
                        scene.height, scene.channels);

            std::printf("  CLAHE + Subpixel%s:\n",
                        through_capi ? " (durch die C-Schnittstelle)" : "");
            check(scene, directory, true, ok, dump_corners ? "clahe" : nullptr, through_capi);

            // Zweiter Lauf nur zur Anschauung: er belegt, dass CLAHE wirklich
            // greift. Waeren beide Zeilen gleich, liefe der Schalter ins Leere.
            // Gewertet wird er nicht - Python misst mit CLAHE (Vorgabe true).
            bool ignored = true;
            std::printf("  Nur Graustufen (nicht gewertet):\n");
            check(scene, directory, false, ignored, dump_corners ? "grau" : nullptr, through_capi);
            std::printf("\n");
        }

        if (!ok) {
            std::printf("FEHLGESCHLAGEN - mindestens eine Ecke ausserhalb der Toleranz.\n");
            return 1;
        }
        std::printf("BESTANDEN - alle Ecken innerhalb der Toleranz aus shared/fixtures/.\n");
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "FEHLER: %s\n", error.what());
        return 3;
    }
}
