"""Das A4-Markerblatt erzeugen - der Massstabs-Ursprung des ganzen Verfahrens.

Die Marker werden NICHT als Rasterbild eingebettet, sondern Modul fuer Modul als
Vektorrechtecke gezeichnet. Damit sind die Kanten unabhaengig von der Druckeraufloesung
absolut scharf, was der Subpixel-Erkennung spaeter direkt zugutekommt.

Das Blatt traegt seinen eigenen Kontrollmassstab: nach dem Drucken misst man einen
Marker mit dem Messschieber und traegt den GEMESSENEN Wert in die App ein. Damit
faellt jede Druckerskalierung aus der Rechnung heraus.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import cv2
from reportlab.pdfgen.canvas import Canvas

from app import config
from app.pdf.layout import Rect

# Ein 4x4-Marker hat mit einem Modul Rand 6 x 6 Module.
_MODULES = 6


def sheet_layout(
    marker_mm: float = config.MARKER_MM_NOMINAL,
    spacing_mm: tuple[float, float] | None = None,
) -> dict[int, Rect]:
    """Platzierungsrechtecke der Marker in mm, von der linken UNTEREN Blattecke aus."""
    _, sheet_h = config.SHEET_MM
    half = marker_mm / 2.0
    centers = config.sheet_marker_centers(spacing_mm or config.SHEET_SPACING_MM)
    return {
        marker_id: Rect(cx - half, sheet_h - cy - half, marker_mm, marker_mm)
        for marker_id, (cx, cy) in centers.items()
    }


def build_markersheet(
    marker_mm: float = config.MARKER_MM_NOMINAL,
    spacing_mm: tuple[float, float] | None = None,
) -> bytes:
    """Das komplette Markerblatt als PDF-Bytes."""
    spacing = spacing_mm or config.SHEET_SPACING_MM
    sheet_w, sheet_h = config.SHEET_MM
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=(_pt(sheet_w), _pt(sheet_h)))
    canvas.setTitle("ArUco-Homographie - Markerblatt A4")

    for marker_id, rect in sheet_layout(marker_mm, spacing).items():
        _draw_marker(canvas, marker_id, rect)
        canvas.setFont("Helvetica", 7)
        canvas.setFillGray(0.35)
        canvas.drawCentredString(
            _pt(rect.x + rect.width / 2.0), _pt(rect.y - 4.0), f"ID {marker_id}"
        )

    _draw_instructions(canvas, sheet_w, sheet_h, marker_mm, spacing)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def _draw_marker(canvas: Canvas, marker_id: int, rect: Rect) -> None:
    """Marker als Vektorgrafik: ein Rechteck je Modul, kein Rasterbild."""
    dictionary = cv2.aruco.getPredefinedDictionary(config.ARUCO_DICT_ID)
    bits = cv2.aruco.generateImageMarker(dictionary, marker_id, _MODULES)
    module_mm = rect.width / _MODULES

    canvas.setFillGray(0.0)
    canvas.setStrokeGray(0.0)
    for row in range(_MODULES):
        for col in range(_MODULES):
            if bits[row, col] != 0:  # weisses Modul: einfach frei lassen
                continue
            canvas.rect(
                _pt(rect.x + col * module_mm),
                _pt(rect.y + rect.height - (row + 1) * module_mm),
                _pt(module_mm),
                _pt(module_mm),
                stroke=0,
                fill=1,
            )


def _draw_instructions(
    canvas: Canvas,
    sheet_w: float,
    sheet_h: float,
    marker_mm: float,
    spacing_mm: tuple[float, float],
) -> None:
    """Titel, Bedienhinweis, Layoutangaben und der eigene Kontrollmassstab."""
    centre_x = sheet_w / 2.0
    top = sheet_h / 2.0 + 34.0

    canvas.setFillGray(0.0)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawCentredString(_pt(centre_x), _pt(top), "ArUco-Homographie - Markerblatt")

    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawCentredString(
        _pt(centre_x), _pt(top - 8.0), "Ohne Skalierung drucken (100 %, nicht 'an Seite anpassen')"
    )

    line_step = 4.6
    canvas.setFont("Helvetica", 8)
    canvas.setFillGray(0.2)
    lines = [
        f"Woerterbuch {config.ARUCO_DICT_NAME}, IDs "
        f"{', '.join(str(i) for i in config.SHEET_MARKER_IDS)} "
        "(0 oben links, 1 oben rechts, 2 unten links, 3 unten rechts)",
        f"Nennkantenlaenge {marker_mm:.1f} mm (inkl. schwarzem Rand)",
        f"Mittelpunktabstaende {spacing_mm[0]:.1f} mm x {spacing_mm[1]:.1f} mm",
        "",
        "Nach dem Druck Markerkante UND beide Mittelpunktabstaende messen und",
        "die GEMESSENEN Werte in der App eintragen - damit faellt jede",
        "Druckerskalierung aus der Rechnung heraus.",
    ]
    for index, line in enumerate(lines):
        canvas.drawCentredString(_pt(centre_x), _pt(top - 18.0 - index * line_step), line)

    _draw_control_scale(canvas, centre_x - config.SCALEBAR_MM / 2.0, sheet_h / 2.0 - 32.0)


def _draw_control_scale(canvas: Canvas, x: float, y: float) -> None:
    """100-mm-Balken mit 10-mm-Teilung, gleiche Machart wie im Export-PDF."""
    height = 3.0
    canvas.setFillGray(0.0)
    canvas.setStrokeGray(0.0)
    canvas.setLineWidth(0.4)

    for index in range(int(config.SCALEBAR_MM // 10)):
        if index % 2 == 0:
            canvas.rect(_pt(x + index * 10.0), _pt(y), _pt(10.0), _pt(height), stroke=0, fill=1)
    canvas.rect(_pt(x), _pt(y), _pt(config.SCALEBAR_MM), _pt(height), stroke=1, fill=0)

    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawCentredString(
        _pt(x + config.SCALEBAR_MM / 2.0),
        _pt(y - 5.0),
        f"Kontrollmassstab {config.SCALEBAR_MM:.0f} mm - nachmessen!",
    )


def _pt(millimetres: float) -> float:
    return float(millimetres) * config.PT_PER_MM


def main(argv: list[str] | None = None) -> int:
    """dev.ps1 build-markersheet [marker_mm] [abstand_x] [abstand_y]."""
    args = sys.argv[1:] if argv is None else argv
    marker_mm = float(args[0]) if len(args) > 0 else config.MARKER_MM_NOMINAL
    spacing = (
        (float(args[1]), float(args[2])) if len(args) > 2 else config.SHEET_SPACING_MM
    )

    target = Path(__file__).resolve().parents[2] / "out" / "markerblatt_A4.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(build_markersheet(marker_mm, spacing))
    print(
        f"Markerblatt geschrieben: {target}\n"
        f"  Marker {marker_mm:.1f} mm, Mittelpunktabstaende "
        f"{spacing[0]:.1f} x {spacing[1]:.1f} mm"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
