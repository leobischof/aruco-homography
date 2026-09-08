// Uebersetzung von app/vision/enhance.py.
//
// Stufe fuer Stufe dieselbe Rechnung, in derselben Reihenfolge, mit denselben
// Wachklauseln. Zwei Dinge sind dabei absichtlich woertlich uebernommen und
// keine Geschmacksfrage:
//
// * ZWISCHEN den Stufen liegt immer uint8. Das kostet je Stufe hoechstens eine
//   Rundungsstelle, macht aber jede Stufe einzeln abschaltbar - eine neutral
//   gestellte Stufe reicht das Bild unangetastet weiter.
// * Gerechnet wird in float32, nicht in double. numpy tut das dort ebenfalls
//   (`astype(np.float32)`), und ein Rundungsschritt mehr oder weniger ist genau
//   der Unterschied, den ein Quervergleich zwischen den Kernen sonst findet.
//
// Die Reihenfolge der Rechenschritte ist ausgeschrieben und nicht zu einer
// Matrixausdrucksform zusammengefasst: OpenCV darf `(m - a) * b + c` zu einem
// einzigen Skalierschritt verschmelzen, und dann rundet es einmal statt dreimal.
// Das waere ein anderes Bild als das der Referenz.

#include "aruco/enhance.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>

#include "aruco/constants.hpp"
#include "image_bridge.hpp"

namespace aruco {
namespace {

// Der Wertebereich von uint8 und der Farbkreis von OpenCV-HSV. Beides sind
// Eigenschaften der Datentypen, keine frei gewaehlten Groessen - deshalb stehen
// sie hier und nicht in shared/constants.json (AGENTS.md, Invariante 4).
constexpr float kValueMax = 255.0F;
constexpr float kMidGrey = kValueMax / 2.0F;
constexpr float kHuePeriod = 180.0F;

const int* emphasis_hue(const std::string& name) {
    for (const auto& entry : constants::ADJUST_EMPHASIS_HUES) {
        if (entry.first == name) {
            return &entry.second;
        }
    }
    return nullptr;
}

/// Gewicht je Farbton (0..179): Gauss um die Mitte, ueber die Naht hinweg.
std::vector<float> hue_weight_lut(float centre_hue) {
    std::vector<float> weights(static_cast<std::size_t>(kHuePeriod));
    for (std::size_t hue = 0; hue < weights.size(); ++hue) {
        float distance = std::abs(static_cast<float>(hue) - centre_hue);
        // Der Farbkreis ist geschlossen: Rot liegt bei 0 UND bei 179. Ohne diese
        // Faltung an der Naht fiele die halbe Farbe aus dem Fenster - der
        // klassische Fehler an dieser Stelle, und er trifft ausgerechnet Rot.
        distance = std::min(distance, kHuePeriod - distance);
        const float scaled =
            distance / static_cast<float>(constants::ADJUST_EMPHASIS_SIGMA_DEG);
        weights[hue] = std::exp(-0.5F * scaled * scaled);
    }
    return weights;
}

/// Einen Farbton behalten, alles andere entsaettigen.
void emphasise(cv::Mat& image, const AdjustOptions& options) {
    const int* centre = emphasis_hue(options.color_emphasis);
    // Ein unbekannter Schluessel ist ein Fehler der aufrufenden Schicht. Hier
    // gilt trotzdem: lieber keine Betonung als ein Abbruch mitten im Export.
    if (centre == nullptr || options.emphasis_strength <= 0.0) {
        return;
    }

    const std::vector<float> weights = hue_weight_lut(static_cast<float>(*centre));
    const float strength = static_cast<float>(options.emphasis_strength);
    std::vector<float> keep(weights.size());
    for (std::size_t hue = 0; hue < weights.size(); ++hue) {
        // Der betonte Farbton behaelt seine Saettigung, wie sie fotografiert
        // wurde - sie wird nicht angehoben. Angehobene Farbe waere erfundene Farbe.
        keep[hue] = 1.0F - strength * (1.0F - weights[hue]);
    }

    cv::Mat hsv;
    cv::cvtColor(image, hsv, cv::COLOR_BGR2HSV);
    for (int row = 0; row < hsv.rows; ++row) {
        std::uint8_t* pixel = hsv.ptr<std::uint8_t>(row);
        for (int column = 0; column < hsv.cols; ++column, pixel += 3) {
            const float factor = keep[pixel[0]];
            pixel[1] = cv::saturate_cast<std::uint8_t>(static_cast<float>(pixel[1]) * factor);
        }
    }
    cv::cvtColor(hsv, image, cv::COLOR_HSV2BGR);
}

/// Schwarzweiss, aber weiter dreikanalig.
void grayscale(cv::Mat& image, const AdjustOptions& options) {
    if (!options.grayscale) {
        return;
    }
    cv::Mat grey;
    cv::cvtColor(image, grey, cv::COLOR_BGR2GRAY);
    cv::cvtColor(grey, image, cv::COLOR_GRAY2BGR);
}

/// CLAHE auf der Helligkeit - holt Zeichnung aus Schatten und Lichtern.
void local_contrast(cv::Mat& image, const AdjustOptions& options) {
    if (options.local_contrast <= 0.0) {
        return;
    }

    // Auf L in LAB, niemals auf B, G und R einzeln: drei getrennte
    // Histogrammspreizungen ziehen die Kanaele auseinander und faerben das Bild um.
    cv::Mat lab;
    cv::cvtColor(image, lab, cv::COLOR_BGR2Lab);
    std::vector<cv::Mat> planes;
    cv::split(lab, planes);

    // Clip-Limit 1.0 heisst "alles gekappt" und damit praktisch Identitaet; von
    // dort laeuft die Staerke stetig bis ADJUST_CLAHE_CLIP_MAX hoch.
    const double clip = 1.0 + options.local_contrast * (constants::ADJUST_CLAHE_CLIP_MAX - 1.0);
    const cv::Size tiles(constants::ADJUST_CLAHE_TILES, constants::ADJUST_CLAHE_TILES);
    cv::Mat equalised;
    cv::createCLAHE(clip, tiles)->apply(planes[0], equalised);
    planes[0] = equalised;

    cv::merge(planes, lab);
    cv::cvtColor(lab, image, cv::COLOR_Lab2BGR);
}

/// Unschaerfemaske: Kanten steiler, Lage unveraendert.
void edge_boost(cv::Mat& image, const AdjustOptions& options) {
    if (options.edge_boost <= 0.0) {
        return;
    }

    // Der Gauss ist punktsymmetrisch. Die Maske (Bild minus Unschaerfe) ist
    // deshalb antisymmetrisch zur Kante: sie hebt die eine Seite genau so weit
    // an, wie sie die andere absenkt. Der Nulldurchgang - die Kante - bleibt, wo
    // er war. Ein einseitiger Kern wuerde hier Millimeter kosten.
    cv::Mat blurred;
    cv::GaussianBlur(image, blurred, cv::Size(0, 0), constants::ADJUST_UNSHARP_SIGMA_PX);
    const float amount = static_cast<float>(options.edge_boost * constants::ADJUST_UNSHARP_MAX);

    for (int row = 0; row < image.rows; ++row) {
        std::uint8_t* target = image.ptr<std::uint8_t>(row);
        const std::uint8_t* soft = blurred.ptr<std::uint8_t>(row);
        const int count = image.cols * image.channels();
        for (int index = 0; index < count; ++index) {
            const float value = static_cast<float>(target[index]);
            const float mask = value - static_cast<float>(soft[index]);
            target[index] = cv::saturate_cast<std::uint8_t>(value + amount * mask);
        }
    }
}

/// Globale Tonwertkurve: Kontrast um das Mittelgrau, dann Helligkeit.
void tone(cv::Mat& image, const AdjustOptions& options) {
    if (options.brightness == 0.0 && options.contrast == 0.0) {
        return;
    }

    // Kontrast 1.0 verdoppelt den Abstand zum Mittelgrau, -1.0 zieht alles auf
    // Mittelgrau zusammen. Helligkeit 1.0 hebt um den vollen Wertebereich an -
    // beide Enden bedeuten also genau das, was sie versprechen.
    const float gain = static_cast<float>(1.0 + options.contrast);
    const float offset = static_cast<float>(options.brightness) * kValueMax;

    for (int row = 0; row < image.rows; ++row) {
        std::uint8_t* pixel = image.ptr<std::uint8_t>(row);
        const int count = image.cols * image.channels();
        for (int index = 0; index < count; ++index) {
            const float value = static_cast<float>(pixel[index]);
            pixel[index] =
                cv::saturate_cast<std::uint8_t>((value - kMidGrey) * gain + kMidGrey + offset);
        }
    }
}

/// Buntheit, ueber die Grauachse gemischt.
void saturation(cv::Mat& image, const AdjustOptions& options) {
    if (options.saturation == 0.0) {
        return;
    }

    // Mischen statt S in HSV skalieren: das haelt den Farbton exakt und kostet
    // keine zweite Farbraumwandlung. Auf einem bereits grauen Bild ist die
    // Differenz null - deshalb ist der Regler nach Schwarzweiss wirkungslos.
    cv::Mat grey;
    cv::cvtColor(image, grey, cv::COLOR_BGR2GRAY);
    const float factor = static_cast<float>(1.0 + options.saturation);

    for (int row = 0; row < image.rows; ++row) {
        std::uint8_t* pixel = image.ptr<std::uint8_t>(row);
        const std::uint8_t* neutral = grey.ptr<std::uint8_t>(row);
        for (int column = 0; column < image.cols; ++column) {
            const float base = static_cast<float>(neutral[column]);
            for (int channel = 0; channel < 3; ++channel) {
                const float value = static_cast<float>(pixel[column * 3 + channel]);
                pixel[column * 3 + channel] =
                    cv::saturate_cast<std::uint8_t>(base + factor * (value - base));
            }
        }
    }
}

/// Erkannte Kanten als dunkle Linien auflegen.
void edge_overlay(cv::Mat& image, const AdjustOptions& options) {
    if (options.edge_overlay <= 0.0) {
        return;
    }

    cv::Mat grey;
    cv::cvtColor(image, grey, cv::COLOR_BGR2GRAY);
    cv::Mat edges;
    cv::Canny(grey, edges, constants::ADJUST_EDGE_CANNY[0], constants::ADJUST_EDGE_CANNY[1]);

    // Canny markiert das Kantenpixel selbst. Abgedunkelt wird genau dieses Pixel,
    // nichts daneben und nichts dazwischen: die Zeichnung legt Tinte auf die
    // Kante, sie verschiebt sie nicht.
    const float keep = static_cast<float>(1.0 - options.edge_overlay);
    for (int row = 0; row < image.rows; ++row) {
        std::uint8_t* pixel = image.ptr<std::uint8_t>(row);
        const std::uint8_t* ink = edges.ptr<std::uint8_t>(row);
        for (int column = 0; column < image.cols; ++column) {
            if (ink[column] == 0) {
                continue;
            }
            for (int channel = 0; channel < 3; ++channel) {
                const float value = static_cast<float>(pixel[column * 3 + channel]);
                pixel[column * 3 + channel] = cv::saturate_cast<std::uint8_t>(value * keep);
            }
        }
    }
}

/// Harte Schwelle: nur noch Schwarz und Weiss.
void threshold_stage(cv::Mat& image, const AdjustOptions& options) {
    if (options.threshold <= 0.0) {
        return;
    }
    cv::Mat grey;
    cv::cvtColor(image, grey, cv::COLOR_BGR2GRAY);
    cv::Mat binary;
    cv::threshold(grey, binary, options.threshold * static_cast<double>(kValueMax),
                  static_cast<double>(kValueMax), cv::THRESH_BINARY);
    cv::cvtColor(binary, image, cv::COLOR_GRAY2BGR);
}

/// Negativ.
void invert_stage(cv::Mat& image, const AdjustOptions& options) {
    if (!options.invert) {
        return;
    }
    // bitwise_not ist auf uint8 exakt 255 - v: kein Rundungsweg, kein Klemmen.
    cv::bitwise_not(image, image);
}

}  // namespace

bool is_identity(const AdjustOptions& options) {
    // Die Bedingungen spiegeln genau die Wachklauseln der Stufen. Laufen die
    // beiden auseinander, ist das Ergebnis zwar immer noch richtig, aber die
    // Abkuerzung greift nicht mehr - deshalb stehen sie beieinander.
    const bool emphasises =
        emphasis_hue(options.color_emphasis) != nullptr && options.emphasis_strength > 0.0;
    return !(options.grayscale || options.invert || options.brightness != 0.0 ||
             options.contrast != 0.0 || options.saturation != 0.0 ||
             options.local_contrast > 0.0 || options.edge_boost > 0.0 ||
             options.edge_overlay > 0.0 || options.threshold > 0.0 || emphasises);
}

ImageBuffer adjust(const ImageView& image, const AdjustOptions& options) {
    const cv::Mat view = as_mat(image);
    if (view.channels() != 3) {
        throw std::invalid_argument("Bildaufbereitung erwartet ein BGR-Bild aus uint8");
    }

    // Immer eine Kopie, auch bei neutralen Reglern: das Eingabebild wird nie
    // veraendert und nie durchgereicht, damit der Aufrufer ins Ergebnis zeichnen
    // darf, ohne sein Original zu beschaedigen.
    cv::Mat working = view.clone();
    if (is_identity(options)) {
        return to_buffer(working);
    }

    emphasise(working, options);
    grayscale(working, options);
    local_contrast(working, options);
    edge_boost(working, options);
    tone(working, options);
    saturation(working, options);
    edge_overlay(working, options);
    threshold_stage(working, options);
    invert_stage(working, options);
    return to_buffer(working);
}

}  // namespace aruco
