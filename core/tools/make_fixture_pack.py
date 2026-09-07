"""shared/fixtures/ -> ein Paket, das der C++-Pruefstand ohne imgcodecs lesen kann.

Aufruf (macht CMake bei jedem Lauf selbst):

    python core/tools/make_fixture_pack.py <shared/fixtures> <zielverzeichnis>

Das Paket ist ERZEUGT und liegt im Bauverzeichnis; eingecheckt ist es nicht.
Jede Zahl darin stammt aus shared/fixtures/ - hier wird nichts getippt.

Warum es das ueberhaupt gibt, zwei Gruende:

1. **Der Kern darf kein imgcodecs anfassen.** Im WASM-Bau ist es abgeschaltet
   (Stufe 0). Das Pruefprogramm ist zwar kein Kern und duerfte `imread` benutzen -
   aber dann laege ein PNG-Dekoder zwischen den beiden Messungen, und ein
   Unterschied im Ergebnis waere nicht mehr eindeutig dem Detektor zuzuordnen.
   Die rohen BGR-Bytes kommen deshalb aus DEMSELBEN `cv2.imread`, das auch
   tests/test_conformance.py benutzt. Beide Kerne sehen Byte fuer Byte dasselbe.

2. **C++ hat keinen JSON-Leser.** Einen dafuer zu vendorn (oder selbst zu
   schreiben) waere mehr Angriffsflaeche als die Uebersetzung wert ist. Das Paket
   ist eine stumpfe Liste aus Wort und Zahl, in vier Zeilen zu lesen.

Fliesskommazahlen werden mit repr() geschrieben - Pythons kuerzeste Darstellung,
die exakt zurueckliest. Der C++-double bekommt Bit fuer Bit denselben Wert wie
die goldene Datei.

Heute steht im Paket nur, was Aufgabe 1 braucht: Bild, Groesse, Eck-Toleranz und
die exakten Ecken. Sobald `solve` portiert ist, kommen `rms_px` und `centre_mm`
dazu - beide stehen bereits in shared/fixtures/expected/*.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

SCENES = ("flat", "thick")


def write_scene(name: str, fixtures: Path, target: Path, manifest: list[str]) -> None:
    truth = json.loads((fixtures / "expected" / f"{name}.json").read_text("utf-8"))

    image = cv2.imread(str(fixtures / truth["image"]), cv2.IMREAD_COLOR)
    if image is None:
        raise SystemExit(f"Szene {name} nicht lesbar: {fixtures / truth['image']}")

    height, width, channels = image.shape
    if [width, height] != truth["image_size_px"]:
        raise SystemExit(f"Szene {name}: {width}x{height} statt {truth['image_size_px']}")

    raw = f"{name}.raw"
    # `tobytes()` und nicht `image.data`: das erzwingt eine dichte Kopie, auch
    # wenn OpenCV je eine Zeilenluecke liefern sollte. Der C++-Leser darf sich
    # darauf verlassen, dass stride == width * channels ist.
    (target / raw).write_bytes(image.tobytes())

    corners = truth["marker_corners_px"]
    manifest.append(f"scene {name}")
    manifest.append(f"raw {raw}")
    manifest.append(f"size {width} {height} {channels}")
    manifest.append(f"tol_corner_px {truth['tolerances']['corner_px']!r}")
    manifest.append(f"markers {len(corners)}")
    for marker_id in sorted(corners, key=int):
        manifest.append(f"marker {int(marker_id)}")
        for point in corners[marker_id]:
            manifest.append(f"{float(point[0])!r} {float(point[1])!r}")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2

    fixtures, target = Path(argv[1]), Path(argv[2])
    target.mkdir(parents=True, exist_ok=True)

    manifest = [f"scenes {len(SCENES)}"]
    for name in SCENES:
        write_scene(name, fixtures, target, manifest)

    (target / "fixtures.txt").write_text("\n".join(manifest) + "\n", encoding="ascii")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
