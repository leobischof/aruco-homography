"""Ein Schablonen-PDF nachmessen - am Erzeugnis, nicht am Protokoll.

Aufruf (macht ./dev.ps1 check-android-ui):

    python android/tools/measure_template.py <schablone.pdf> [--eigenes-bild-je-seite]

WOZU. `check-android-ui` faehrt die Android-Rechenkette und bekommt am Ende ein
PDF. Dass dabei eines herauskam, ist noch keine Aussage - ein PDF entsteht auch
mit falschen Zahlen. Hier wird nachgezaehlt, was auf dem Blatt steht:

  1. Jede Seite ist exakt 210,000 x 297,000 mm (Invariante 1 am Papier).
  2. Das 50-mm-Raster hat 50-mm-Abstaende, gemessen an den VEKTORLINIEN im PDF
     und nicht an einem gerasterten Bild - eine Rasterung braechte ihre eigene
     Ungenauigkeit mit, und die will hier niemand mitmessen.
  3. Mit --eigenes-bild-je-seite: jede Seite, die ein Bild traegt, traegt ihr
     EIGENES. Das ist der Beleg fuer die blattweise Rasterung - teilen sich zwei
     Seiten ein Bildobjekt, ist ein Raster ueber den ganzen Zuschnitt entstanden,
     und genau das gibt auf einem Telefon den Speicherfehler vom 08.09.2026.

WAS DIESE MESSUNG NICHT ZEIGT, und das gehoert in jeden Bericht darueber: Raster
und Seitengroesse zeichnet die PDF-Schicht aus denselben Millimeterzahlen, in
denen der Zuschnitt angegeben ist. Laege die Homographie daneben, waere die
Schablone falsch gross, und dieses Raster maesse trotzdem stimmig. Es kann
diesen Fehler gar nicht sehen. Die Kette Foto -> Marker -> Millimeter ist an
anderer Stelle belegt (core/tools/ChainCheck.java, tests/).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

PT_PER_MM = 72.0 / 25.4
PAGE_MM = (210.0, 297.0)
GRID_STEP_MM = 50.0

# Die Seitengroesse steht als Gleitkomma im PDF; ein Mikrometer Spielraum ist
# die Aufloesung der Darstellung und keine Nachgiebigkeit.
PAGE_TOLERANCE_MM = 1e-3
GRID_TOLERANCE_MM = 1e-3


def merge(values: list[float]) -> list[float]:
    """Kernlinie und weisser Saum liegen uebereinander - als eine Linie zaehlen."""
    kept: list[float] = []
    for value in sorted(set(round(v, 6) for v in values)):
        if not kept or value - kept[-1] > 1.0:
            kept.append(value)
    return kept


def lines_of(page: pymupdf.Page) -> tuple[list[float], list[float]]:
    """Senkrechte und waagerechte Linien der Seite, in Millimetern."""
    verticals: list[float] = []
    horizontals: list[float] = []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] != "l":
                continue
            start, end = item[1], item[2]
            if abs(start.x - end.x) < 1e-6 and abs(start.y - end.y) > 20.0:
                verticals.append(start.x / PT_PER_MM)
            elif abs(start.y - end.y) < 1e-6 and abs(start.x - end.x) > 20.0:
                horizontals.append(start.y / PT_PER_MM)
    return merge(verticals), merge(horizontals)


def eigenes_bild_je_seite(document: pymupdf.Document) -> bool:
    """True, wenn etwas nicht stimmt - zwei Seiten teilen sich ein Bild.

    Blattweise gerastert bekommt jedes Blatt sein eigenes Bildobjekt. Die
    Uebersichtsseite traegt keines; ihr Fehlen ist kein Befund.
    """
    gesehen: dict[int, int] = {}
    failed = False
    for number, page in enumerate(document, start=1):
        refs = sorted({item[0] for item in page.get_images(full=True)})
        if not refs:
            continue
        geteilt = [ref for ref in refs if ref in gesehen]
        for ref in geteilt:
            print(f"  [x] Seite {number} teilt Bild {ref} mit Seite {gesehen[ref]} "
                  f"- also NICHT blattweise gerastert")
        if not geteilt:
            print(f"  Seite {number}: eigenes Bild (xref {refs[0]})  [ok]")
        failed = failed or bool(geteilt)
        for ref in refs:
            gesehen[ref] = number
    if not gesehen:
        print("  [x] Keine Seite traegt ein Bild")
        failed = True
    return failed


def main(argv: list[str]) -> int:
    flags = {arg for arg in argv[1:] if arg.startswith("--")}
    names = [arg for arg in argv[1:] if not arg.startswith("--")]
    if len(names) != 1 or flags - {"--eigenes-bild-je-seite"}:
        print(__doc__, file=sys.stderr)
        return 2

    document = pymupdf.open(Path(names[0]))
    failed = False
    print(f"{document.page_count} Seiten")

    if "--eigenes-bild-je-seite" in flags:
        failed = eigenes_bild_je_seite(document) or failed

    for number, page in enumerate(document, start=1):
        width = page.rect.width / PT_PER_MM
        height = page.rect.height / PT_PER_MM
        held = (abs(width - PAGE_MM[0]) < PAGE_TOLERANCE_MM
                and abs(height - PAGE_MM[1]) < PAGE_TOLERANCE_MM)
        print(f"  Seite {number}: {width:.3f} x {height:.3f} mm  "
              f"{'[ok]' if held else '[x]'}")
        failed = failed or not held

    # Gemessen wird auf den Seiten, die ein Raster tragen. Die Uebersichtsseite
    # traegt keines, und ihr Fehlen ist kein Befund.
    measured = 0
    worst = 0.0
    for number, page in enumerate(document, start=1):
        for values, axis in zip(lines_of(page), ("x", "y")):
            gaps = [b - a for a, b in zip(values, values[1:])]
            inner = [gap for gap in gaps if abs(gap - GRID_STEP_MM) < 5.0]
            if not inner:
                continue
            deviation = max(abs(gap - GRID_STEP_MM) for gap in inner)
            worst = max(worst, deviation)
            measured += len(inner)
            print(f"  Seite {number} {axis}: {len(inner)} Rasterabstaende, "
                  f"groesste Abweichung {deviation * 1e6:.4f} nm")

    if measured == 0:
        print("  [x] Kein 50-mm-Raster gefunden - war es abgeschaltet?")
        return 1
    if worst >= GRID_TOLERANCE_MM:
        print(f"  [x] Rasterabstand weicht um {worst:.6f} mm ab")
        return 1

    if failed:
        print("DURCHGEFALLEN - siehe die mit [x] gezeichneten Zeilen.")
        return 1
    print(f"BESTANDEN - {measured} Rasterabstaende, alle {GRID_STEP_MM:.0f} mm "
          f"(groesste Abweichung {worst * 1e6:.4f} nm), jede Seite "
          f"{PAGE_MM[0]:.0f} x {PAGE_MM[1]:.0f} mm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
