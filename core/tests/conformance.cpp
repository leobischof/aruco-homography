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
// Aufruf:  aruco_conformance <pfad/zu/fixtures.txt>

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
double check(const SceneFixture& scene, const std::string& directory, bool enhance_contrast,
             bool& ok) {
    const std::size_t expected =
        static_cast<std::size_t>(scene.width) * scene.height * scene.channels;
    const std::vector<std::uint8_t> pixels = read_raw(directory + "/" + scene.raw, expected);

    aruco::ImageView image;
    image.data = pixels.data();
    image.width = scene.width;
    image.height = scene.height;
    image.stride = scene.width * scene.channels;
    image.channels = scene.channels;

    const std::vector<aruco::Marker> markers = aruco::detect_markers(image, enhance_contrast);

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
    if (argc != 2) {
        std::fprintf(stderr, "Aufruf: aruco_conformance <pfad/zu/fixtures.txt>\n");
        return 2;
    }

    const std::string manifest = argv[1];
    const std::string directory = manifest.substr(0, manifest.find_last_of("/\\"));

    try {
        bool ok = true;
        for (const SceneFixture& scene : read_manifest(manifest)) {
            std::printf("Szene %s (%dx%d, %d Kanaele)\n", scene.name.c_str(), scene.width,
                        scene.height, scene.channels);

            std::printf("  CLAHE + Subpixel:\n");
            check(scene, directory, true, ok);

            // Zweiter Lauf nur zur Anschauung: er belegt, dass CLAHE wirklich
            // greift. Waeren beide Zeilen gleich, liefe der Schalter ins Leere.
            // Gewertet wird er nicht - Python misst mit CLAHE (Vorgabe true).
            bool ignored = true;
            std::printf("  Nur Graustufen (nicht gewertet):\n");
            check(scene, directory, false, ignored);
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
