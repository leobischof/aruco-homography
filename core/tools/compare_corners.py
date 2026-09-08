"""Zwei `--ecken`-Ausgaben des Pruefstands Ecke fuer Ecke gegeneinanderhalten.

    aruco_conformance <fixtures.txt> --ecken | findstr "^ecke" > windows.txt
    node aruco_conformance.js <fixtures.txt> --ecken | findstr "^ecke" > wasm.txt
    python core/tools/compare_corners.py windows.txt wasm.txt Windows WASM

Wozu es das braucht: der Pruefstand rundet seine Meldung auf vier Nachkommastellen.
Das genuegt, um eine Toleranz von 0,75 px zu pruefen, aber nicht, um zwei ZIELE
gegeneinanderzuhalten. `0.2337 px` sieht auf Windows, unter Node und in Chrome
gleich aus - und ist es nicht ganz (docs/cpp-migration/stage-4-cross-targets.md).

Der Massstab ist der **float32-ULP**: der kleinste Schritt, den die Darstellung
kennt, in der OpenCV die Markerecken fuehrt. Ein Unterschied von einem ULP ist
kein Fehler, sondern die Aufloesungsgrenze - zwei Uebersetzer duerfen dort
auseinanderliegen, ohne dass jemand etwas falsch gemacht hat. Deshalb rechnet
dieses Werkzeug den Unterschied in ULP um und nicht nur in Pixel: erst damit
laesst sich sagen, ob ein Befund die Rundung ist oder ein Befund.

Rueckgabe 0, wenn beide Ausgaben dieselbe Eckenmenge tragen, sonst 1. Es urteilt
NICHT ueber die Groesse des Unterschieds - das bleibt beim Leser, weil die
Schranke davon abhaengt, was gerade verglichen wird.
"""

from __future__ import annotations

import struct
import sys

# Die eingefrorenen Szenen zeigen 50 mm Markerkante auf rund 128 px. Nur zur
# Anschauung: eine Abweichung in Pixeln sagt niemandem etwas, eine in Millimetern
# schon - und Millimeter sind das Produkt (AGENTS.md).
MM_PER_PX = 50.0 / 128.0


def load(path: str) -> dict[tuple[str, str, int, int], tuple[float, float, float]]:
    """Alle `ecke`-Zeilen einer Ausgabe einlesen, nach Szene/Modus/ID/Ecke."""
    corners = {}
    with open(path, encoding="ascii") as stream:
        for line in stream:
            if not line.startswith("ecke "):
                continue
            _, scene, mode, marker, index, x, y, error = line.split()
            corners[(scene, mode, int(marker), int(index))] = (float(x), float(y), float(error))
    return corners


def f32_ulp(value: float) -> float:
    """Der Abstand zweier benachbarter float32 bei diesem Betrag."""
    if value == 0.0:
        return struct.unpack("<f", struct.pack("<I", 1))[0]
    bits = struct.unpack("<I", struct.pack("<f", abs(value)))[0]
    lower = struct.unpack("<f", struct.pack("<I", bits))[0]
    upper = struct.unpack("<f", struct.pack("<I", bits + 1))[0]
    return upper - lower


def main(argv: list[str]) -> int:
    if not 3 <= len(argv) <= 5:
        print(__doc__, file=sys.stderr)
        return 2

    left, right = load(argv[1]), load(argv[2])
    name_left = argv[3] if len(argv) > 3 else argv[1]
    name_right = argv[4] if len(argv) > 4 else argv[2]

    if left.keys() != right.keys():
        print("Die beiden Ausgaben tragen verschiedene Ecken - da stimmt mehr nicht als "
              "das letzte Bit.", file=sys.stderr)
        return 1

    worst_coordinate = 0.0
    worst_ulp = 0.0
    worst_error = 0.0
    differing = []

    for key in sorted(left):
        lx, ly, le = left[key]
        rx, ry, re = right[key]
        dx, dy = abs(lx - rx), abs(ly - ry)
        delta = max(dx, dy)
        if delta > 0.0 or le != re:
            differing.append((key, lx, ly, rx, ry, delta))
        worst_coordinate = max(worst_coordinate, delta)
        worst_error = max(worst_error, abs(le - re))
        for value, difference in ((lx, dx), (ly, dy)):
            if difference:
                worst_ulp = max(worst_ulp, difference / f32_ulp(value))

    print(f"{name_left}  vs  {name_right}")
    print(f"  Ecken verglichen:                 {len(left)}")
    print(f"  davon verschieden:                {len(differing)}")
    print(f"  groesster Koordinatenunterschied: {worst_coordinate!r} px")
    print(f"  das sind:                         {worst_ulp:g} float32-ULP")
    print(f"  groesster Fehlerunterschied:      {worst_error!r} px")
    print(f"  in mm (50 mm ~ 128 px):           {worst_coordinate * MM_PER_PX:.3e} mm")
    for key, lx, ly, rx, ry, delta in differing:
        print(f"    {key}: {lx!r},{ly!r}  ->  {rx!r},{ry!r}   d={delta!r} px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
