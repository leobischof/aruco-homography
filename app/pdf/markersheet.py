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
from app.i18n import translate
from app.pdf import branding
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
    locale: str = config.DEFAULT_LOCALE,
) -> bytes:
    """Das komplette Markerblatt als PDF-Bytes."""
    spacing = spacing_mm or config.SHEET_SPACING_MM
    sheet_w, sheet_h = config.SHEET_MM
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=(_pt(sheet_w), _pt(sheet_h)))
    canvas.setTitle(translate("pdf.markersheet.document_title", locale))

    for marker_id, rect in sheet_layout(marker_mm, spacing).items():
        _draw_marker(canvas, marker_id, rect)
        canvas.setFont("Helvetica", 7)
        canvas.setFillGray(0.35)
        canvas.drawCentredString(
            _pt(rect.x + rect.width / 2.0),
            _pt(rect.y - 4.0),
            translate("pdf.markersheet.marker_label", locale, marker_id=marker_id),
        )

    _draw_instructions(canvas, sheet_w, sheet_h, marker_mm, spacing, locale)
    _draw_brand_footer(canvas, sheet_w, marker_mm, spacing, locale)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def _draw_brand_footer(
    canvas: Canvas,
    sheet_w: float,
    marker_mm: float,
    spacing_mm: tuple[float, float],
    locale: str = config.DEFAULT_LOCALE,
) -> None:
    """Markenzeichen am unteren Blattrand.

    Die Hoehe ist so gewaehlt, dass zwischen Text und unterstem Marker mehr als ein
    Markermodul (hier gut 11 mm) weiss bleibt - die Ruhezone, auf die der Detektor
    angewiesen ist. Naeher heran darf hier nichts.
    """
    strip_y, strip_h = 5.0, 11.0
    branding.draw_brand_block(canvas, sheet_w - 15.0, strip_y, strip_h, with_claim=True)

    canvas.setFillColor(branding.ink(config.BRAND_INK))
    canvas.setFont("Helvetica", 6.0)
    canvas.drawString(
        _pt(15.0),
        _pt(strip_y + strip_h / 2.0 - 1.0),
        translate(
            "pdf.markersheet.footer",
            locale,
            dictionary=config.ARUCO_DICT_NAME,
            marker_mm=f"{marker_mm:.1f}",
            spacing_x_mm=f"{spacing_mm[0]:.1f}",
            spacing_y_mm=f"{spacing_mm[1]:.1f}",
        ),
    )


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
    locale: str = config.DEFAULT_LOCALE,
) -> None:
    """Titel, Bedienhinweis, Layoutangaben und der eigene Kontrollmassstab."""
    centre_x = sheet_w / 2.0
    top = sheet_h / 2.0 + 34.0

    canvas.setFillGray(0.0)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawCentredString(_pt(centre_x), _pt(top), translate("pdf.markersheet.title", locale))

    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawCentredString(
        _pt(centre_x), _pt(top - 8.0), translate("pdf.markersheet.print_hint", locale)
    )

    line_step = 4.6
    canvas.setFont("Helvetica", 8)
    canvas.setFillGray(0.2)
    # Die drei Messzeilen stehen einzeln im Katalog: sie werden zentriert gesetzt, und
    # wo der Umbruch sitzt, entscheidet die Sprache - nicht der Code.
    lines = [
        translate(
            "pdf.markersheet.dictionary",
            locale,
            dictionary=config.ARUCO_DICT_NAME,
            ids=", ".join(str(i) for i in config.SHEET_MARKER_IDS),
        ),
        translate("pdf.markersheet.side", locale, marker_mm=f"{marker_mm:.1f}"),
        translate(
            "pdf.markersheet.spacing",
            locale,
            spacing_x_mm=f"{spacing_mm[0]:.1f}",
            spacing_y_mm=f"{spacing_mm[1]:.1f}",
        ),
        "",
        translate("pdf.markersheet.measure_1", locale),
        translate("pdf.markersheet.measure_2", locale),
        translate("pdf.markersheet.measure_3", locale),
    ]
    for index, line in enumerate(lines):
        canvas.drawCentredString(_pt(centre_x), _pt(top - 18.0 - index * line_step), line)

    _draw_control_scale(
        canvas, centre_x - config.SCALEBAR_MM / 2.0, sheet_h / 2.0 - 32.0, locale
    )


def _draw_control_scale(
    canvas: Canvas, x: float, y: float, locale: str = config.DEFAULT_LOCALE
) -> None:
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
        translate(
            "pdf.markersheet.scale_caption", locale, length=f"{config.SCALEBAR_MM:.0f}"
        ),
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
