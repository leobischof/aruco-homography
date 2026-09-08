"""Die Modulbits des nativen Kerns gegen cv2 halten.

    java ... JniCheck <fixtures.txt> --bits | findstr "^bits" > bits.txt
    python core/tools/compare_marker_bits.py bits.txt

Wozu. Das Markerblatt wird Modul fuer Modul als Vektorrechteck gezeichnet
(web/pdf/markersheet.js), und die Bits dafuer kommen je nach Ziel aus einer
anderen Quelle: unter Node aus opencv.js, auf Android aus dem nativen Kern. Ein
verschobenes oder vertauschtes Raster ergaebe ein Blatt, das auf dem Bildschirm
voellig normal aussieht - und das kein Detektor je findet. Am Ausdruck faellt das
erst auf, wenn Papier und Zeit schon weg sind.

Die Pruefung im Java-Teil (Groesse, schwarzer Rand) faengt das NICHT: der Rand
ist symmetrisch, eine Transposition kaeme glatt durch. Also wird hier das ganze
Muster verglichen, Byte fuer Byte, gegen dasselbe cv2, das auch die Referenz der
Testsuite ist.

Rueckgabe 0, wenn jedes Muster stimmt, sonst 1.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parents[2]


def expected_bits(dictionary_name: str, marker_id: int, modules: int) -> bytes:
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary_name))
    return bytes(dictionary.generateImageMarker(marker_id, modules, 1).ravel().tolist())


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    constants = json.loads((REPO / "shared" / "constants.json").read_text(encoding="utf-8"))
    dictionary_name = constants["ARUCO_DICT_NAME"]

    lines = [
        line.split()
        for line in Path(argv[1]).read_text(encoding="ascii").splitlines()
        if line.startswith("bits ")
    ]
    if not lines:
        print("Keine 'bits'-Zeilen gefunden - lief JniCheck mit --bits?", file=sys.stderr)
        return 1

    mismatches = 0
    for _, marker_id, modules, hexadecimal in lines:
        marker_id, modules = int(marker_id), int(modules)
        actual = bytes.fromhex(hexadecimal)
        wanted = expected_bits(dictionary_name, marker_id, modules)
        if actual == wanted:
            print(f"  [ok] Marker {marker_id}: {modules}x{modules} Module gleich cv2")
            continue

        mismatches += 1
        print(f"  [x]  Marker {marker_id}: weicht von cv2 ab")
        # Beide Raster untereinander ausgeben. Eine Hex-Zeile sagt niemandem,
        # WAS verschoben ist; zwei Raster nebeneinander sagen es sofort.
        for row in range(modules):
            left = "".join("#" if b == 0 else "." for b in actual[row * modules:(row + 1) * modules])
            right = "".join("#" if b == 0 else "." for b in wanted[row * modules:(row + 1) * modules])
            print(f"       {left}   {right}")
        print(f"       {'nativ':<{modules}}   {'cv2':<{modules}}")

    if mismatches:
        print(f"FEHLGESCHLAGEN - {mismatches} von {len(lines)} Mustern weichen ab.")
        return 1
    print(f"BESTANDEN - alle {len(lines)} Muster stimmen mit cv2 ueberein.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
