"""Testbilder mit analytisch exakter Grundwahrheit erzeugen - und den Python-Fehler messen.

Die erzeugten Bilder sind die einzige Referenz des Spikes: dieselben Dateien gehen in
den Python-Detektor und in den Browser. Verglichen wird nicht gegen Perfektion, sondern
gegen das, was Python auf genau diesen Bildern schafft.

Die Ecken aus `ideal_markers()` sind PROJIZIERT, nicht erkannt - die bekannten
Markerecken durch die bekannte Homographie. Deshalb taugen sie als Grundwahrheit.

Aufruf (vom Worktree-Wurzelverzeichnis, mit dem venv-Python):
    python spike/make_scene.py

Erzeugt in spike/:
    scene.png, scene-gray.png, scene-gray.raw, scene-truth.json, python-baseline.json
    scene-12mp.png, scene-12mp-gray.raw, scene-12mp-truth.json, python-baseline-12mp.json

Die .raw-Dateien sind rohe Graustufen (ein Byte je Pixel, zeilenweise). Sie existieren,
damit der Browser BYTEGLEICH dieselben Pixel sieht wie Python - ohne Umweg ueber einen
PNG-Dekoder, dessen Ergebnis man erst wieder belegen muesste. Sie sind gross und
absichtlich nicht eingecheckt; dieses Skript stellt sie wieder her.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.vision.detect import build_detector  # noqa: E402
from tests.conftest import ideal_markers, make_scene  # noqa: E402

OUT = ROOT / "spike"
CLAHE_CLIP, CLAHE_TILE = 2.0, (8, 8)


def corner_error(found: np.ndarray, truth: np.ndarray) -> np.ndarray:
    """Euklidischer Abstand je Ecke, in Pixeln."""
    return np.linalg.norm(np.asarray(found) - np.asarray(truth), axis=1)


def detect_and_score(image: np.ndarray, truth: dict[str, np.ndarray], detector) -> dict:
    corners, ids, _ = detector.detectMarkers(image)
    if ids is None or len(ids) == 0:
        return {"count": 0, "mean_px": None, "max_px": None, "markers": {}}
    markers, errors = {}, []
    for quad, marker_id in zip(corners, ids.flatten()):
        pts = np.asarray(quad, dtype=np.float64).reshape(4, 2)
        err = corner_error(pts, truth[str(int(marker_id))])
        markers[str(int(marker_id))] = {"corners": pts.tolist(), "error_px": err.tolist()}
        errors.append(err)
    errors = np.concatenate(errors)
    return {"count": int(len(ids)), "mean_px": float(errors.mean()),
            "max_px": float(errors.max()), "markers": markers}


def best_ms(image: np.ndarray, detector, repeats: int = 5) -> float:
    """Bestzeit statt Mittelwert - der erste Lauf misst den kalten Cache mit."""
    times = []
    for _ in range(repeats):
        t = time.perf_counter()
        detector.detectMarkers(image)
        times.append((time.perf_counter() - t) * 1000.0)
    return min(times)


def build_scene(size: tuple[int, int], stem: str) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Szene rendern und alles ablegen, was der Browser braucht."""
    scene = make_scene(image_size=size)
    cv2.imwrite(str(OUT / f"{stem}.png"), scene.image)

    truth = {str(m.marker_id): np.asarray(m.corners_px, dtype=np.float64) for m in ideal_markers(scene)}
    json.dump({k: v.tolist() for k, v in truth.items()},
              (OUT / f"{stem}-truth.json").open("w", encoding="utf-8"), indent=2)

    gray = cv2.cvtColor(scene.image, cv2.COLOR_BGR2GRAY)
    (OUT / f"{stem}-gray.raw").write_bytes(gray.tobytes())
    return truth, gray


def main() -> None:
    print(f"OpenCV {cv2.__version__}, cv2-Threads {cv2.getNumThreads()}")
    detector = build_detector()

    # --- Kleine Szene: die Referenz, an der der Browser gemessen wird. ---
    truth, gray = build_scene((2400, 1800), "scene")
    cv2.imwrite(str(OUT / "scene-gray.png"), gray)
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_TILE).apply(gray)

    results = {"opencv_version": cv2.__version__, "image_size": [2400, 1800]}
    for label, image in (("clahe", clahe), ("plain-gray", gray)):
        r = detect_and_score(image, truth, detector)
        r["best_ms"] = best_ms(image, detector)
        results[label] = r
        print(f"  {label:<16} {r['count']} Marker  mean {r['mean_px']:.4f} px  "
              f"max {r['max_px']:.4f} px  best {r['best_ms']:.0f} ms")

    # Gegenprobe: ohne Subpixel-Verfeinerung MUSS der Fehler deutlich groesser sein.
    # Sonst misst der spaetere Browser-Vergleich nichts - ein still ignoriertes
    # Flag saehe genauso aus wie ein wirksames.
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_NONE
    params.adaptiveThreshWinSizeMin = 3
    params.adaptiveThreshWinSizeMax = 53
    params.adaptiveThreshWinSizeStep = 10
    params.minMarkerPerimeterRate = 0.01
    blunt = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(config.ARUCO_DICT_ID), params)
    r = detect_and_score(clahe, truth, blunt)
    results["clahe-no-subpix"] = r
    print(f"  {'clahe-no-subpix':<16} {r['count']} Marker  mean {r['mean_px']:.4f} px  max {r['max_px']:.4f} px")

    json.dump(results, (OUT / "python-baseline.json").open("w", encoding="utf-8"), indent=2)

    # --- 12-MP-Szene: die Groesse, in der ein Handy wirklich fotografiert. ---
    truth_big, gray_big = build_scene((4000, 3000), "scene-12mp")
    clahe_big = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_TILE).apply(gray_big)
    r = detect_and_score(clahe_big, truth_big, detector)
    r["best_ms"] = best_ms(clahe_big, detector, repeats=3)
    r["image_size"] = [4000, 3000]
    json.dump({k: v for k, v in r.items() if k != "markers"},
              (OUT / "python-baseline-12mp.json").open("w", encoding="utf-8"), indent=2)
    print(f"  {'12mp clahe':<16} {r['count']} Marker  mean {r['mean_px']:.4f} px  "
          f"max {r['max_px']:.4f} px  best {r['best_ms']:.0f} ms")

    # Der Markerbogen muss im Browser dieselben Pixel erzeugen wie hier.
    marker = cv2.aruco.generateImageMarker(
        cv2.aruco.getPredefinedDictionary(config.ARUCO_DICT_ID), 0, 120, borderBits=1)
    print(f"  generateImageMarker(0, 120): Pruefsumme {int(marker.astype(np.int64).sum())}")


if __name__ == "__main__":
    main()
