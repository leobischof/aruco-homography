"""shared/fixtures/ -> die Sollwerte der ganzen Messkette, fuer den JNI-Pruefstand.

Aufruf (macht ./dev.ps1 check-jni selbst):

    python core/tools/make_chain_reference.py <fixtures.txt> <chain.txt>

`fixtures.txt` ist das Paket aus make_fixture_pack.py - dort liegen die rohen
Pixel. Heraus kommt eine zweite, ebenso stumpfe Liste aus Wort und Zahl, die
core/tools/JniCheck.java liest.

WOZU. Bis hierher konnte der JNI-Pruefstand eine einzige Funktion messen:
detect_markers. Der Rest der Kette - Homographie, Ausgleich, Kamerapose,
Ausdehnung, Entzerrung, Aufbereitung, Umriss - ging durch keinen Pruefstand, den
irgendjemand ausfuehrt. Diese Datei liefert die Sollwerte dafuer.

ZWEI SOLLWERTBLOECKE, und der Unterschied ist der ganze Punkt:

  `cpp.*`  Derselbe C++-Kern, nur durch die pybind11-Bindung statt durch JNI.
           Hier MUSS die JNI-Schicht bitgenau dasselbe liefern - es ist
           buchstaeblich dieselbe Rechnung, und was dazwischenliegt, ist nur das
           Umpacken. Jede Abweichung ist ein Marshalling-Fehler und nichts
           sonst. Das ist die gewertete Pruefung.

  `py.*`   Die Python-Referenz aus app/vision/. Sie rechnet an einer Stelle
           anders (scipy.optimize.least_squares gegen cv::LevMarq), also KANN
           sie nicht bitgleich sein. Ihr Zweck ist die zweite Frage: wie weit
           liegt die Kette durch JNI von der Referenz entfernt, in Millimetern?
           Diese Zahl wird berichtet, nicht gewertet.

WAS HIER NICHT PASSIERT: rechnen. Jede Zeile ruft entweder `aruco_core` (die
pybind11-Bindung) oder die `_..._python`-Funktion aus app/vision/. Eine dritte
Fassung der Messtechnik in einem Pruefwerkzeug waere genau das, wogegen der
ganze Umzug laeuft.

Fliesskommazahlen mit repr() - Pythons kuerzeste Darstellung, die exakt
zurueckliest. Java liest sie mit Double.parseDouble, und das ist die
Umkehrfunktion dazu.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app import config  # noqa: E402
from app.vision import camera as camera_module  # noqa: E402
from app.vision import contour as contour_module  # noqa: E402
from app.vision import enhance as enhance_module  # noqa: E402
from app.vision import extent as extent_module  # noqa: E402
from app.vision import geometry as geometry_module  # noqa: E402
from app.vision import rectify as rectify_module  # noqa: E402
from app.vision import solve as solve_module  # noqa: E402
from app.vision.extent import Extent  # noqa: E402

# Ein Reglerstand, der moeglichst viele Stufen der Aufbereitung wirklich laufen
# laesst - eine neutrale Einstellung wuerde nur die Abkuerzung pruefen.
# `threshold` bleibt 0: eine Binarisierung wuerde den Umriss danach trivial
# machen, und der ist der letzte Schritt dieser Kette.
ADJUST = {
    "grayscale": False,
    "invert": False,
    "brightness": 0.1,
    "contrast": 0.2,
    "saturation": -0.1,
    "local_contrast": 0.3,
    "edge_boost": 0.2,
    "edge_overlay": 0.15,
    "color_emphasis": "red",
    "emphasis_strength": 0.4,
    "threshold": 0.0,
}

# Die Reihenfolge, in der die elf Regler durch jede Grenze gehen - dieselbe wie
# in core/bindings/python.cpp und in NativeCore.adjust. Sie steht hier einmal,
# damit die Datei und der Java-Leser sie nicht getrennt raten muessen.
ADJUST_ORDER = (
    "grayscale",
    "invert",
    "brightness",
    "contrast",
    "saturation",
    "local_contrast",
    "edge_boost",
    "edge_overlay",
    "emphasis_strength",
    "threshold",
)

EXPORT_DPI = 300


class Writer:
    """Die Ausgabedatei: `d <name> <anzahl> <werte...>` oder `s <name> <wort>`."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def numbers(self, name: str, values) -> None:
        flat = np.asarray(values, dtype=np.float64).reshape(-1)
        self.lines.append(f"d {name} {flat.size} " + " ".join(repr(float(v)) for v in flat))

    def text(self, name: str, value: str) -> None:
        self.lines.append(f"s {name} {value}")


def sha256(image: np.ndarray) -> str:
    """Pruefsumme ueber die rohen Bildbytes.

    Ein Bild laesst sich nicht als Zahlenliste in eine Textdatei schreiben, und
    ein Mittelwert taeuschte: er ist gegen fast jede Verschiebung blind. Die
    Pruefsumme ist entweder gleich oder nicht - und genau diese Aussage will man
    ueber ein Rasterbild haben, das gleich gedruckt wird.
    """
    return hashlib.sha256(np.ascontiguousarray(image).tobytes()).hexdigest()


class CppCore:
    """Der C++-Kern durch die pybind11-Bindung - dieselbe Rechnung wie ueber JNI."""

    def __init__(self, core) -> None:
        self.core = core

    def quad_area(self, quad):
        return self.core.quad_area(np.asarray(quad, dtype=np.float64))

    def homography_from_quad(self, plane, image):
        return np.asarray(self.core.homography_from_quad(plane, image))

    def homography_lmeds(self, plane, image):
        return np.asarray(self.core.homography_lmeds(plane, image))

    def refine_homography(self, start, plane, image):
        return np.asarray(self.core.refine_homography(start, plane, image))

    def fit_free(self, quads, marker_mm):
        homography, offsets = self.core.fit_free(quads, marker_mm)
        return np.asarray(homography), np.asarray(offsets)

    def pose_from_homography(self, homography, focal_px, width, height):
        return self.core.pose_from_homography(homography, focal_px, width, height)

    def plane_extent(self, homography, width, height, hull):
        return self.core.plane_extent(homography, width, height, hull)

    def convex_hull(self, points):
        return np.asarray(self.core.convex_hull(points))

    def convex_intersection_area(self, first, second):
        return self.core.convex_intersection_area(first, second)

    def local_px_per_mm(self, homography, point):
        return self.core.local_px_per_mm(homography, np.asarray(point, dtype=np.float64))

    def output_size(self, x0, y0, x1, y1, px_per_mm):
        return self.core.output_size(x0, y0, x1, y1, px_per_mm)

    def rectify(self, image, homography, x0, y0, x1, y1, px_per_mm, source_px_per_mm):
        return self.core.rectify(
            image, homography, x0, y0, x1, y1, px_per_mm, source_px_per_mm
        )

    def adjust(self, image):
        return self.core.adjust(image, **ADJUST)

    def find_contour_mm(self, image, px_per_mm):
        return self.core.find_contour_mm(image, px_per_mm)


class PythonCore:
    """Die Python-Referenz aus app/vision/ - unabhaengig von ARUCO_CORE."""

    def quad_area(self, quad):
        from app.vision.detect import _quad_area_python

        return _quad_area_python(np.asarray(quad, dtype=np.float64))

    def homography_from_quad(self, plane, image):
        return solve_module._homography_from_quad_python(plane, image)

    def homography_lmeds(self, plane, image):
        return solve_module._homography_lmeds_python(plane, image)

    def refine_homography(self, start, plane, image):
        return solve_module._refine_homography_python(start, plane, image)

    def fit_free(self, quads, marker_mm):
        return solve_module._fit_free_python(np.asarray(quads, dtype=np.float64), marker_mm)

    def pose_from_homography(self, homography, focal_px, width, height):
        return camera_module._pose_from_homography_python(homography, focal_px, width, height)

    def plane_extent(self, homography, width, height, hull):
        return extent_module._plane_extent_python(homography, width, height, hull)

    def convex_hull(self, points):
        return geometry_module._convex_hull_python(points)

    def convex_intersection_area(self, first, second):
        return geometry_module._convex_intersection_area_python(first, second)

    def local_px_per_mm(self, homography, point):
        return geometry_module._local_px_per_mm_python(
            homography, np.asarray(point, dtype=np.float64)
        )

    def output_size(self, x0, y0, x1, y1, px_per_mm):
        return rectify_module._output_size_python(x0, y0, x1, y1, px_per_mm)

    def rectify(self, image, homography, x0, y0, x1, y1, px_per_mm, source_px_per_mm):
        return rectify_module._rectify_python(
            image, homography, x0, y0, x1, y1, px_per_mm, source_px_per_mm
        )

    def adjust(self, image):
        return enhance_module._adjust_python(image, **ADJUST)

    def find_contour_mm(self, image, px_per_mm):
        return contour_module._find_contour_mm_python(image, px_per_mm)


def read_manifest(path: Path) -> list[dict]:
    """Das Fixture-Paket lesen - dasselbe Format wie conformance.cpp und JniCheck."""
    tokens = path.read_text("ascii").split()
    index = 0

    def take() -> str:
        nonlocal index
        value = tokens[index]
        index += 1
        return value

    def expect(word: str) -> None:
        got = take()
        if got != word:
            raise SystemExit(f"Fixture-Paket: '{word}' erwartet, '{got}' gelesen")

    expect("scenes")
    scenes = []
    for _ in range(int(take())):
        expect("scene")
        scene = {"name": take()}
        expect("raw")
        scene["raw"] = take()
        expect("size")
        scene["width"], scene["height"], scene["channels"] = (
            int(take()),
            int(take()),
            int(take()),
        )
        expect("tol_corner_px")
        scene["tolerance_px"] = float(take())
        expect("markers")
        corners = {}
        for _ in range(int(take())):
            expect("marker")
            marker_id = int(take())
            corners[marker_id] = [float(take()) for _ in range(8)]
        scene["corners"] = corners
        scenes.append(scene)
    return scenes


def write_chain(writer: Writer, prefix: str, core, scene: dict, image: np.ndarray,
                ids, image_points, plane_points, focal_px, marker_mm) -> dict:
    """Die ganze Kette einmal durchrechnen und jeden Zwischenstand aufschreiben."""
    width, height = scene["width"], scene["height"]

    areas = [core.quad_area(np.asarray(image_points[marker]).reshape(4, 2)) for marker in ids]
    writer.numbers(f"{prefix}.quad_area", areas)

    plane_flat = np.asarray([plane_points[marker] for marker in ids]).reshape(-1, 2)
    image_flat = np.asarray([image_points[marker] for marker in ids]).reshape(-1, 2)

    h_quad = core.homography_from_quad(plane_flat[:4], image_flat[:4])
    writer.numbers(f"{prefix}.h_quad", h_quad)

    h_lmeds = core.homography_lmeds(plane_flat, image_flat)
    writer.numbers(f"{prefix}.h_lmeds", h_lmeds)

    h_refined = core.refine_homography(h_lmeds, plane_flat, image_flat)
    writer.numbers(f"{prefix}.h_refined", h_refined)

    # Frei-Modus: absteigend nach Bildflaeche, so wie solve.py und solve.js es
    # sortieren. Die Reihenfolge ist Teil des Vertrags von fit_free.
    order = [marker for _, marker in sorted(zip(areas, ids), key=lambda pair: -pair[0])]
    # Die Reihenfolge steht in der Datei, weil sie NICHT im Kern wohnt: sortiert
    # wird in solve.py und solve.js. Wer sie hier nachbaute, pruefte eine
    # Sortierung statt einer Bindung.
    writer.numbers(f"{prefix}.free_order", order)
    free_quads = np.asarray([image_points[marker] for marker in order]).reshape(-1, 4, 2)
    free_h, free_offsets = core.fit_free(free_quads, marker_mm)
    writer.numbers(f"{prefix}.fit_free", np.concatenate([np.asarray(free_h).reshape(-1),
                                                        np.asarray(free_offsets).reshape(-1)]))

    pose_height, nadir, tilt = core.pose_from_homography(h_refined, focal_px, width, height)
    writer.numbers(f"{prefix}.pose", [pose_height, nadir[0], nadir[1], tilt])

    hull = np.asarray(core.convex_hull(plane_flat)).reshape(-1, 2)
    writer.numbers(f"{prefix}.hull", hull)

    area = np.asarray(core.plane_extent(h_refined, width, height, hull), dtype=np.float64)
    writer.numbers(f"{prefix}.extent", area)

    # Der Schwerpunkt ist ebenfalls kein Kernwert (er steht in solve.py und
    # solve.js), und eine zweite Summationsreihenfolge in Java koennte in der
    # letzten Stelle abweichen. Also kommt er aus der Datei.
    centroid = hull.mean(axis=0)
    writer.numbers(f"{prefix}.hull_centroid", centroid)
    px_per_mm = core.local_px_per_mm(h_refined, centroid)
    writer.numbers(f"{prefix}.local_px_per_mm", [px_per_mm])

    crop = extent_module.default_crop(Extent(*area), hull)
    writer.numbers(f"{prefix}.crop", [crop.x0, crop.y0, crop.x1, crop.y1])

    inside = core.convex_intersection_area(
        geometry_module.rect_polygon(crop.x0, crop.y0, crop.x1, crop.y1), hull
    )
    writer.numbers(f"{prefix}.intersection", [inside])

    preview_px_per_mm = rectify_module.preview_px_per_mm(Extent(*area))
    writer.numbers(f"{prefix}.preview_px_per_mm", [preview_px_per_mm])
    writer.numbers(
        f"{prefix}.preview_size",
        core.output_size(area[0], area[1], area[2], area[3], preview_px_per_mm),
    )
    writer.numbers(
        f"{prefix}.export_size",
        core.output_size(crop.x0, crop.y0, crop.x1, crop.y1,
                         rectify_module.px_per_mm_for_dpi(EXPORT_DPI)),
    )

    rectified = core.rectify(image, h_refined, area[0], area[1], area[2], area[3],
                             preview_px_per_mm, px_per_mm)
    writer.text(f"{prefix}.rectify_sha", sha256(rectified))

    # Ein zweiter, enger Ausschnitt: genau die Markerhuelle. Auf dem weiten
    # Vorschaubild findet find_contour_mm NICHTS - das Blatt fuellt dort weniger
    # als CONTOUR_MIN_AREA_FRAC der Flaeche, und der Kern gibt zu Recht die leere
    # Antwort. Eine Bindung, die nur den leeren Fall sieht, ist aber nicht
    # geprueft: das Umpacken einer Punktliste faende so niemand kaputt. Der
    # Nahausschnitt liefert eine echte Kontur, und nebenbei geht er durch den
    # ANDEREN Interpolationszweig (Lanczos statt INTER_AREA).
    close = Extent(float(hull[:, 0].min()), float(hull[:, 1].min()),
                   float(hull[:, 0].max()), float(hull[:, 1].max()))
    close_px_per_mm = rectify_module.preview_px_per_mm(close)
    writer.numbers(f"{prefix}.close_crop", [close.x0, close.y0, close.x1, close.y1])
    writer.numbers(f"{prefix}.close_px_per_mm", [close_px_per_mm])
    writer.numbers(f"{prefix}.close_size",
                   core.output_size(close.x0, close.y0, close.x1, close.y1, close_px_per_mm))
    close_raster = core.rectify(image, h_refined, close.x0, close.y0, close.x1, close.y1,
                                close_px_per_mm, px_per_mm)
    writer.text(f"{prefix}.close_sha", sha256(close_raster))

    # Beide Antworten von is_identity: neutral muss 1 sein, der Reglerstand oben
    # 0. Nur eine der beiden zu pruefen liesse eine Bindung durchgehen, die
    # immer dasselbe sagt.
    neutral = enhance_module.AdjustOptions()
    chosen = enhance_module.AdjustOptions(**ADJUST)
    writer.numbers(f"{prefix}.is_identity",
                   [1.0 if neutral.is_identity else 0.0, 1.0 if chosen.is_identity else 0.0])

    adjusted = core.adjust(close_raster)
    writer.text(f"{prefix}.adjust_sha", sha256(adjusted))

    contour = core.find_contour_mm(adjusted, close_px_per_mm)
    writer.numbers(f"{prefix}.contour",
                   np.zeros((0, 2)) if contour is None else np.asarray(contour).reshape(-1, 2))

    return {"extent": area, "px_per_mm": px_per_mm, "pose": pose_height,
            "rectify_sha": sha256(rectified)}


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2

    manifest = Path(argv[1]).resolve()
    target = Path(argv[2])
    # Neben dem Fixture-Paket liegt das gebaute Modul: core/build/fixtures/ ->
    # core/build/. Denselben Weg geht app/vision/backend.py.
    sys.path.insert(0, str(manifest.parent.parent))
    import aruco_core  # noqa: PLC0415 - das Bauergebnis, erst hier ladbar

    writer = Writer()
    scenes = read_manifest(manifest)
    writer.lines.insert(0, f"scenes {len(scenes)}")

    for scene in scenes:
        expected = REPO_ROOT / "shared" / "fixtures" / "expected" / f"{scene['name']}.json"
        truth = json.loads(expected.read_text("utf-8"))
        marker_mm = float(truth["marker_mm"])
        focal_px = float(truth["camera"]["focal_px"])

        raw = (manifest.parent / scene["raw"]).read_bytes()
        image = np.frombuffer(raw, dtype=np.uint8).reshape(
            scene["height"], scene["width"], scene["channels"]
        )

        # Die Eingaben der Kette stehen in der Datei und werden NICHT auf beiden
        # Seiten neu erkannt: sonst pruefte dieser Vergleich den Detektor noch
        # einmal mit, und ein Fehlschlag liesse offen, wo er entstand. Dass die
        # Erkennung durch JNI dieselben Ecken liefert, misst JniCheck davor.
        found = aruco_core.detect_markers(image, True)
        ids = sorted(marker_id for marker_id, _ in found)
        corners = {marker_id: np.asarray(quad, dtype=np.float64) for marker_id, quad in found}
        plane = solve_module.sheet_plane_corners(marker_mm, tuple(config.SHEET_SPACING_MM))

        writer.lines.append(f"scene {scene['name']}")
        writer.numbers("in.image_size", [scene["width"], scene["height"], scene["channels"]])
        writer.numbers("in.marker_mm", [marker_mm])
        writer.numbers("in.focal_px", [focal_px])
        writer.numbers("in.ids", ids)
        writer.numbers("in.corners", np.asarray([corners[i] for i in ids]).reshape(-1, 2))
        writer.numbers("in.plane", np.asarray([plane[i] for i in ids]).reshape(-1, 2))
        writer.numbers("in.adjust", [float(ADJUST[name]) for name in ADJUST_ORDER])
        writer.text("in.color_emphasis", str(ADJUST["color_emphasis"]))
        writer.numbers("in.export_dpi", [EXPORT_DPI])

        cpp = write_chain(writer, "cpp", CppCore(aruco_core), scene, image, ids, corners,
                          plane, focal_px, marker_mm)
        py = write_chain(writer, "py", PythonCore(), scene, image, ids, corners, plane,
                         focal_px, marker_mm)
        writer.lines.append("end")

        # Die eine Zahl, die der Bericht braucht: wie weit liegen die beiden
        # Kerne in Millimetern auseinander, gemessen an der Ausdehnung, die die
        # Schablonengroesse bestimmt.
        print(f"{scene['name']}: groesster Unterschied C++ gegen Python")
        print(f"  Ausdehnung   {np.max(np.abs(cpp['extent'] - py['extent'])):.3e} mm")
        print(f"  Massstab     {abs(cpp['px_per_mm'] - py['px_per_mm']):.3e} px/mm")
        print(f"  Kamerahoehe  {abs(cpp['pose'] - py['pose']):.3e} mm")
        print(f"  Rasterbild   "
              f"{'byteweise gleich' if cpp['rectify_sha'] == py['rectify_sha'] else 'verschieden'}")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(writer.lines) + "\n", encoding="ascii")
    print(f"\n{target} geschrieben ({len(writer.lines)} Zeilen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
