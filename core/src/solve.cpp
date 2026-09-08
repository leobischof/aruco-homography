// Uebersetzung der Zahlenverfahren aus app/vision/solve.py.
//
// Die Residuen sind Zeile fuer Zeile dieselben wie dort:
//
//     residual(params) = (project(H(params), plane_points) - image_points).ravel()
//
// Nur der Optimierer ist ein anderer - scipy gibt es hier nicht. Was cv::LevMarq
// von seinem Rueckruf erwartet, steht nicht eindeutig in der Kopfdatei (dort ist
// von d(ideal)/d(param) die Rede) und wurde deshalb an der Quelle nachgelesen:
// modules/geometry/src/levmarq.cpp bildet jtj = J^T*J, jtb = J^T*b und loest
// (J^T*J + lambda*D) dx = -J^T*b. Der Schritt ist damit der klassische
// Gauss-Newton-Schritt fuer min ||b||^2 mit J = db/dparam. Also: b IST das
// Residuum, und J ist seine Ableitung - nicht die des Modells.

#include "aruco/solve.hpp"

#include <cmath>
#include <cstddef>
#include <stdexcept>

#include <opencv2/core.hpp>
#include <opencv2/geometry.hpp>

#include "aruco/geometry.hpp"

namespace aruco {
namespace {

// Einheitsquadrat in der Reihenfolge, die cv::aruco fuer die Ecken liefert.
constexpr double kUnitCorners[4][2] = {{0.0, 0.0}, {1.0, 0.0}, {1.0, 1.0}, {0.0, 1.0}};

/// Dieselben Abbruchschranken wie `least_squares(..., xtol=ftol=gtol=1e-14)`.
///
/// Die Vorgaben von cv::LevMarq sind 1e-6 - das ist fuer diese Suite viel zu
/// grob: tests/test_solve.py verlangt im rauschfreien Fall rms < 1e-6 PIXEL, und
/// eine Optimierung, die bei 1e-6 relativer Energieaenderung stehenbleibt, kaeme
/// dort nur zufaellig durch.
cv::LevMarq::Settings tight_settings() {
    cv::LevMarq::Settings settings;
    settings.setStepNormTolerance(1e-14)
        .setRelEnergyDeltaTolerance(1e-14)
        .setMinGradientTolerance(1e-14)
        .setMaxIterations(200);
    return settings;
}

/// Homographie auf h22 == 1 normieren und die 8 freien Parameter zurueckgeben.
std::array<double, 8> as_eight(const Matrix3& homography) {
    if (std::abs(homography[8]) < 1e-15) {
        throw std::invalid_argument("Homographie ist entartet (h22 ~ 0)");
    }
    std::array<double, 8> parameters{};
    for (std::size_t index = 0; index < 8; ++index) {
        parameters[index] = homography[index] / homography[8];
    }
    return parameters;
}

Matrix3 from_eight(const double* parameters) {
    return Matrix3{parameters[0], parameters[1], parameters[2], parameters[3], parameters[4],
                   parameters[5], parameters[6], parameters[7], 1.0};
}

std::vector<cv::Point2f> as_float(const std::vector<Point2>& points) {
    std::vector<cv::Point2f> converted;
    converted.reserve(points.size());
    for (const Point2& point : points) {
        converted.push_back(
            cv::Point2f(static_cast<float>(point.x), static_cast<float>(point.y)));
    }
    return converted;
}

std::vector<cv::Point2d> as_double(const std::vector<Point2>& points) {
    std::vector<cv::Point2d> converted;
    converted.reserve(points.size());
    for (const Point2& point : points) {
        converted.push_back(cv::Point2d(point.x, point.y));
    }
    return converted;
}

/// Residuum und Jacobi-Matrix fuer eine feste Punktmenge in der Ebene.
///
/// `plane` darf sich zwischen den Aufrufen aendern (Frei-Modus verschiebt die
/// Marker mit); deshalb wird sie uebergeben und nicht eingefangen.
void fill_residual(const double* parameters, const std::vector<Point2>& plane,
                   const std::vector<Point2>& image, cv::Mat_<double>& residual) {
    for (std::size_t index = 0; index < plane.size(); ++index) {
        const double x = plane[index].x;
        const double y = plane[index].y;
        const double w = parameters[6] * x + parameters[7] * y + 1.0;
        const double u = (parameters[0] * x + parameters[1] * y + parameters[2]) / w;
        const double v = (parameters[3] * x + parameters[4] * y + parameters[5]) / w;
        residual(static_cast<int>(2 * index), 0) = u - image[index].x;
        residual(static_cast<int>(2 * index + 1), 0) = v - image[index].y;
    }
}

}  // namespace

Matrix3 homography_from_quad(const std::array<Point2, 4>& plane,
                             const std::array<Point2, 4>& image) {
    // float32 wie in Python (`astype(np.float32)` vor getPerspectiveTransform).
    // OpenCV rechnet danach in double weiter; die Rundung der EINGABE gehoert
    // aber zum Ergebnis und muss auf beiden Seiten dieselbe sein.
    cv::Point2f source[4];
    cv::Point2f target[4];
    for (int corner = 0; corner < 4; ++corner) {
        source[corner] = cv::Point2f(static_cast<float>(plane[static_cast<std::size_t>(corner)].x),
                                     static_cast<float>(plane[static_cast<std::size_t>(corner)].y));
        target[corner] = cv::Point2f(static_cast<float>(image[static_cast<std::size_t>(corner)].x),
                                     static_cast<float>(image[static_cast<std::size_t>(corner)].y));
    }

    const cv::Mat matrix = cv::getPerspectiveTransform(source, target);
    Matrix3 result{};
    for (int row = 0; row < 3; ++row) {
        for (int column = 0; column < 3; ++column) {
            result[static_cast<std::size_t>(row * 3 + column)] = matrix.at<double>(row, column);
        }
    }
    return result;
}

Matrix3 homography_lmeds(const std::vector<Point2>& plane, const std::vector<Point2>& image) {
    if (plane.size() != image.size() || plane.size() < 4) {
        throw std::invalid_argument("findHomography braucht mindestens vier Punktpaare");
    }

    // float64 wie in Python: dort geht das ungewandelte Array hinein.
    const cv::Mat matrix = cv::findHomography(as_double(plane), as_double(image), cv::LMEDS);
    if (matrix.empty()) {
        throw std::runtime_error("homography_failed");
    }

    Matrix3 result{};
    for (int row = 0; row < 3; ++row) {
        for (int column = 0; column < 3; ++column) {
            result[static_cast<std::size_t>(row * 3 + column)] = matrix.at<double>(row, column);
        }
    }
    return result;
}

Matrix3 refine_homography(const Matrix3& start, const std::vector<Point2>& plane,
                          const std::vector<Point2>& image) {
    if (plane.size() != image.size() || plane.empty()) {
        throw std::invalid_argument("refine_homography: Punktzahlen passen nicht zueinander");
    }

    const std::array<double, 8> initial = as_eight(start);
    cv::Mat_<double> parameters(8, 1);
    for (int index = 0; index < 8; ++index) {
        parameters(index, 0) = initial[static_cast<std::size_t>(index)];
    }

    const int rows = static_cast<int>(2 * plane.size());
    auto callback = [&plane, &image, rows](cv::InputOutputArray probe, cv::OutputArray err,
                                           cv::OutputArray jacobian) -> bool {
        const cv::Mat_<double> current = probe.getMat();
        const double* p = current.ptr<double>();

        err.create(rows, 1, CV_64F);
        cv::Mat_<double> residual = err.getMat();
        fill_residual(p, plane, image, residual);

        if (jacobian.needed()) {
            jacobian.create(rows, 8, CV_64F);
            cv::Mat_<double> matrix = jacobian.getMat();
            matrix.setTo(0.0);
            for (std::size_t index = 0; index < plane.size(); ++index) {
                const double x = plane[index].x;
                const double y = plane[index].y;
                const double w = p[6] * x + p[7] * y + 1.0;
                const double u = (p[0] * x + p[1] * y + p[2]) / w;
                const double v = (p[3] * x + p[4] * y + p[5]) / w;
                const int row_u = static_cast<int>(2 * index);
                const int row_v = row_u + 1;

                matrix(row_u, 0) = x / w;
                matrix(row_u, 1) = y / w;
                matrix(row_u, 2) = 1.0 / w;
                matrix(row_u, 6) = -u * x / w;
                matrix(row_u, 7) = -u * y / w;

                matrix(row_v, 3) = x / w;
                matrix(row_v, 4) = y / w;
                matrix(row_v, 5) = 1.0 / w;
                matrix(row_v, 6) = -v * x / w;
                matrix(row_v, 7) = -v * y / w;
            }
        }
        return true;
    };

    cv::LevMarq solver(parameters, callback, tight_settings());
    solver.optimize();

    return from_eight(parameters.ptr<double>());
}

FreeFit fit_free(const std::vector<std::array<Point2, 4>>& quads, double marker_mm) {
    if (quads.empty()) {
        throw std::invalid_argument("fit_free braucht mindestens einen Marker");
    }

    // Startwert: der groesste Marker definiert Ursprung und Massstab der Ebene.
    std::array<Point2, 4> anchor_plane{};
    for (std::size_t corner = 0; corner < 4; ++corner) {
        anchor_plane[corner] =
            Point2{kUnitCorners[corner][0] * marker_mm, kUnitCorners[corner][1] * marker_mm};
    }

    const Matrix3 start = homography_from_quad(anchor_plane, quads[0]);
    const Matrix3 inverse = invert(start);

    const std::size_t others = quads.size() - 1;
    std::vector<Point2> offsets(others);
    for (std::size_t index = 0; index < others; ++index) {
        const std::array<Point2, 4>& quad = quads[index + 1];
        const std::vector<Point2> corners(quad.begin(), quad.end());
        const std::vector<Point2> in_plane = project(inverse, corners);
        double sum_x = 0.0;
        double sum_y = 0.0;
        for (const Point2& point : in_plane) {
            sum_x += point.x;
            sum_y += point.y;
        }
        offsets[index] = Point2{sum_x / 4.0 - marker_mm / 2.0, sum_y / 4.0 - marker_mm / 2.0};
    }

    std::vector<Point2> image;
    image.reserve(quads.size() * 4);
    for (const std::array<Point2, 4>& quad : quads) {
        for (const Point2& corner : quad) {
            image.push_back(corner);
        }
    }

    const int variables = static_cast<int>(8 + 2 * others);
    const int rows = static_cast<int>(2 * image.size());

    cv::Mat_<double> parameters(variables, 1);
    const std::array<double, 8> initial = as_eight(start);
    for (int index = 0; index < 8; ++index) {
        parameters(index, 0) = initial[static_cast<std::size_t>(index)];
    }
    for (std::size_t index = 0; index < others; ++index) {
        parameters(static_cast<int>(8 + 2 * index), 0) = offsets[index].x;
        parameters(static_cast<int>(9 + 2 * index), 0) = offsets[index].y;
    }

    // Die Ebenenpunkte haengen an den Parametern: der Anker steht fest, jeder
    // weitere Marker sitzt auf dem Einheitsquadrat plus seinem Versatz.
    auto plane_points = [&anchor_plane, marker_mm, others](const double* p) {
        std::vector<Point2> plane;
        plane.reserve(4 * (others + 1));
        for (const Point2& corner : anchor_plane) {
            plane.push_back(corner);
        }
        for (std::size_t index = 0; index < others; ++index) {
            const double offset_x = p[8 + 2 * index];
            const double offset_y = p[9 + 2 * index];
            for (std::size_t corner = 0; corner < 4; ++corner) {
                plane.push_back(Point2{kUnitCorners[corner][0] * marker_mm + offset_x,
                                       kUnitCorners[corner][1] * marker_mm + offset_y});
            }
        }
        return plane;
    };

    auto callback = [&image, &plane_points, rows, variables, others](
                        cv::InputOutputArray probe, cv::OutputArray err,
                        cv::OutputArray jacobian) -> bool {
        const cv::Mat_<double> current = probe.getMat();
        const double* p = current.ptr<double>();
        const std::vector<Point2> plane = plane_points(p);

        err.create(rows, 1, CV_64F);
        cv::Mat_<double> residual = err.getMat();
        fill_residual(p, plane, image, residual);

        if (jacobian.needed()) {
            jacobian.create(rows, variables, CV_64F);
            cv::Mat_<double> matrix = jacobian.getMat();
            matrix.setTo(0.0);
            for (std::size_t index = 0; index < plane.size(); ++index) {
                const double x = plane[index].x;
                const double y = plane[index].y;
                const double w = p[6] * x + p[7] * y + 1.0;
                const double u = (p[0] * x + p[1] * y + p[2]) / w;
                const double v = (p[3] * x + p[4] * y + p[5]) / w;
                const int row_u = static_cast<int>(2 * index);
                const int row_v = row_u + 1;

                matrix(row_u, 0) = x / w;
                matrix(row_u, 1) = y / w;
                matrix(row_u, 2) = 1.0 / w;
                matrix(row_u, 6) = -u * x / w;
                matrix(row_u, 7) = -u * y / w;

                matrix(row_v, 3) = x / w;
                matrix(row_v, 4) = y / w;
                matrix(row_v, 5) = 1.0 / w;
                matrix(row_v, 6) = -v * x / w;
                matrix(row_v, 7) = -v * y / w;

                // Die ersten vier Punkte gehoeren dem Anker; der hat keinen
                // Versatz. Alle weiteren verschieben sich mit ihrem Markerpaar.
                if (index >= 4) {
                    const std::size_t marker = index / 4 - 1;
                    if (marker < others) {
                        const int column_x = static_cast<int>(8 + 2 * marker);
                        const int column_y = column_x + 1;
                        matrix(row_u, column_x) = (p[0] - u * p[6]) / w;
                        matrix(row_u, column_y) = (p[1] - u * p[7]) / w;
                        matrix(row_v, column_x) = (p[3] - v * p[6]) / w;
                        matrix(row_v, column_y) = (p[4] - v * p[7]) / w;
                    }
                }
            }
        }
        return true;
    };

    cv::LevMarq solver(parameters, callback, tight_settings());
    solver.optimize();

    FreeFit fit;
    fit.homography = from_eight(parameters.ptr<double>());
    fit.offsets.resize(others);
    for (std::size_t index = 0; index < others; ++index) {
        fit.offsets[index] = Point2{parameters(static_cast<int>(8 + 2 * index), 0),
                                    parameters(static_cast<int>(9 + 2 * index), 0)};
    }
    return fit;
}

}  // namespace aruco
