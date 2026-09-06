"""Markenzeichen auf dem Papier: Logo und Herkunftszeile.

Das Logo wird als **Vektor** eingebettet, nicht als Rasterbild: svglib liest die
Original-SVG aus dem Webprojekt und liefert eine ReportLab-Zeichnung, die direkt
auf die Seite gemalt wird. Damit ist es bei jeder Druckgroesse scharf, und es gibt
nur eine Quelle fuer das Logo - dieselbe Datei, die auch die Website benutzt.

Die Tinte ist bewusst logo-dark.svg (#334155, das Marken-Foreground): auf Papier
liest sich das ruhiger als reines Schwarz und passt zur Fusszeile daneben.
"""

from __future__ import annotations

from functools import lru_cache

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from svglib.svglib import svg2rlg

from app import config

CLAIM_PT = 5.6
NAME_PT = 6.4
GAP_MM = 2.0


def ink(hex_colour: str) -> HexColor:
    """Markenfarbe als ReportLab-Farbe."""
    return HexColor(hex_colour)


@lru_cache(maxsize=8)
def logo_drawing(svg_path: str, height_mm: float) -> Drawing:
    """Logo als skalierte Vektorzeichnung. Gecacht, weil das Parsen spuerbar dauert."""
    drawing = svg2rlg(svg_path)
    if drawing is None:  # pragma: no cover - nur bei kaputter Asset-Datei
        raise FileNotFoundError(f"Logo konnte nicht gelesen werden: {svg_path}")

    target = height_mm * config.PT_PER_MM
    scale = target / drawing.height
    drawing.scale(scale, scale)
    drawing.width, drawing.height = drawing.width * scale, target
    return drawing


def draw_logo(canvas: Canvas, x_mm: float, y_mm: float, height_mm: float = config.LOGO_MM) -> float:
    """Zeichnet das Logo mit der linken unteren Ecke bei (x, y). Gibt die Breite in mm."""
    drawing = logo_drawing(str(config.LOGO_INK_SVG), height_mm)
    renderPDF.draw(drawing, canvas, x_mm * config.PT_PER_MM, y_mm * config.PT_PER_MM)
    return drawing.width / config.PT_PER_MM


def draw_brand_block(
    canvas: Canvas,
    right_x_mm: float,
    y_mm: float,
    height_mm: float,
    with_claim: bool = True,
) -> float:
    """Logo rechtsbuendig, Herkunftszeile links daneben. Gibt die linke Kante in mm.

    Der Aufrufer kann am Rueckgabewert ablesen, wie viel Platz noch frei ist -
    auf schmalen Seiten laesst er die Herkunftszeile weg, das Logo bleibt.
    """
    logo_mm = min(config.LOGO_MM, height_mm - 1.0)
    logo_x = right_x_mm - logo_mm
    draw_logo(canvas, logo_x, y_mm + (height_mm - logo_mm) / 2.0, logo_mm)

    if not with_claim:
        _link(canvas, logo_x, y_mm, right_x_mm, y_mm + height_mm)
        return logo_x

    text_right = logo_x - GAP_MM
    canvas.setFillColor(ink(config.BRAND_INK))

    canvas.setFont("Helvetica-Bold", NAME_PT)
    canvas.drawRightString(
        text_right * config.PT_PER_MM,
        (y_mm + height_mm / 2.0 + 0.4) * config.PT_PER_MM,
        config.BRAND_NAME,
    )
    canvas.setFont("Helvetica", CLAIM_PT)
    canvas.drawRightString(
        text_right * config.PT_PER_MM,
        (y_mm + height_mm / 2.0 - 2.6) * config.PT_PER_MM,
        config.BRAND_CLAIM,
    )

    left = text_right - claim_width_mm()
    _link(canvas, left, y_mm, right_x_mm, y_mm + height_mm)
    return left


def _link(canvas: Canvas, x0: float, y0: float, x1: float, y1: float) -> None:
    """Den ganzen Markenblock im PDF anklickbar machen."""
    canvas.linkURL(
        config.BRAND_URL,
        (
            x0 * config.PT_PER_MM,
            y0 * config.PT_PER_MM,
            x1 * config.PT_PER_MM,
            y1 * config.PT_PER_MM,
        ),
        relative=0,
        thickness=0,
    )


def claim_width_mm() -> float:
    """Breite der Herkunftszeile in mm - fuer die Platzentscheidung des Aufrufers."""
    return (
        max(
            stringWidth(config.BRAND_CLAIM, "Helvetica", CLAIM_PT),
            stringWidth(config.BRAND_NAME, "Helvetica-Bold", NAME_PT),
        )
        / config.PT_PER_MM
    )


def block_width_mm(with_claim: bool = True) -> float:
    """Gesamtbreite des Markenblocks - damit Aufrufer vorher Platz reservieren koennen."""
    if not with_claim:
        return config.LOGO_MM
    return config.LOGO_MM + GAP_MM + claim_width_mm()
