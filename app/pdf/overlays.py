"""Aufdrucke: Kontrollmassstab, Metadaten, Millimeterraster, Passermarken, Kontur.

Alle Funktionen rechnen in Millimetern und rechnen erst beim Zeichnen in Punkte um.
Der Bezugspunkt ist immer die linke UNTERE Ecke der Seite.
"""

from __future__ import annotations

import numpy as np
from reportlab.pdfgen.canvas import Canvas

from app import config
from app.pdf.layout import Rect

# Innenaufteilung des Streifens, von seiner Unterkante aus (Summe <= STRIP_H_MM).
_TEXT_LINE_1_MM = 1.8
_TEXT_LINE_2_MM = 5.4
_SCALEBAR_BASE_MM = 10.0
_SCALEBAR_HEIGHT_MM = 3.0
_SCALEBAR_LABEL_MM = 14.2
_TEXT_SIZE_PT = 6.0


def crop_to_page(
    image_rect: Rect, crop_origin: tuple[float, float], point_mm: np.ndarray
) -> tuple[float, float]:
    """Punkt aus dem Zuschnitt (y nach unten) auf die Seite (y nach oben) abbilden."""
    crop_x, crop_y = crop_origin
    return (
        image_rect.x + (float(point_mm[0]) - crop_x),
        image_rect.y + image_rect.height - (float(point_mm[1]) - crop_y),
    )


def draw_strip(
    canvas: Canvas,
    strip: Rect,
    show_scalebar: bool,
    footer_lines: list[str],
) -> None:
    """Den Streifen unter dem Bild fuellen: Massstab oben, Metadaten unten."""
    if show_scalebar:
        _draw_scalebar(canvas, strip)
    for index, line in enumerate(footer_lines[:2]):
        offset = _TEXT_LINE_2_MM if index == 1 else _TEXT_LINE_1_MM
        canvas.setFont("Helvetica", _TEXT_SIZE_PT)
        canvas.setFillGray(0.25)
        canvas.drawString(_pt(strip.x), _pt(strip.y + offset), line)


def _draw_scalebar(canvas: Canvas, strip: Rect) -> None:
    """100-mm-Balken mit 10-mm-Teilung. Nachmessen beweist die Skalierung."""
    length = min(config.SCALEBAR_MM, strip.width)
    base_y = strip.y + _SCALEBAR_BASE_MM

    canvas.setLineWidth(0.4)
    canvas.setStrokeGray(0.0)
    canvas.setFillGray(0.0)

    # Wechselnd gefuellte 10-mm-Felder: auch aus der Entfernung eindeutig ablesbar.
    step = 10.0
    position = 0.0
    filled = True
    while position < length - 1e-9:
        segment = min(step, length - position)
        if filled:
            canvas.rect(
                _pt(strip.x + position),
                _pt(base_y),
                _pt(segment),
                _pt(_SCALEBAR_HEIGHT_MM),
                stroke=0,
                fill=1,
            )
        position += segment
        filled = not filled

    canvas.rect(_pt(strip.x), _pt(base_y), _pt(length), _pt(_SCALEBAR_HEIGHT_MM), stroke=1, fill=0)
    canvas.setFont("Helvetica-Bold", _TEXT_SIZE_PT)
    canvas.drawString(
        _pt(strip.x),
        _pt(strip.y + _SCALEBAR_LABEL_MM),
        f"Kontrollmassstab {length:.0f} mm - nachmessen! Teilung 10 mm",
    )


def draw_grid(
    canvas: Canvas,
    image_rect: Rect,
    crop_origin: tuple[float, float],
    step_mm: float = config.GRID_STEP_MM,
) -> None:
    """Duennes Hilfsraster ueber dem Bild, ausgerichtet am absoluten Zuschnittraster."""
    crop_x, crop_y = crop_origin
    canvas.saveState()
    canvas.setStrokeGray(config.GRID_GRAY)
    canvas.setLineWidth(0.15)
    canvas.setFont("Helvetica", 5.0)
    canvas.setFillGray(config.GRID_GRAY * 0.6)

    for offset in _grid_offsets(crop_x, image_rect.width, step_mm):
        x = image_rect.x + (offset - crop_x)
        canvas.line(_pt(x), _pt(image_rect.y), _pt(x), _pt(image_rect.y + image_rect.height))
        canvas.drawString(_pt(x + 0.6), _pt(image_rect.y + 0.6), f"{offset:.0f}")

    for offset in _grid_offsets(crop_y, image_rect.height, step_mm):
        y = image_rect.y + image_rect.height - (offset - crop_y)
        canvas.line(_pt(image_rect.x), _pt(y), _pt(image_rect.x + image_rect.width), _pt(y))
        canvas.drawString(_pt(image_rect.x + 0.6), _pt(y + 0.6), f"{offset:.0f}")

    canvas.restoreState()


def _grid_offsets(start: float, length: float, step_mm: float) -> list[float]:
    """Absolute Rasterpositionen innerhalb eines Abschnitts [start, start+length]."""
    first = np.ceil(start / step_mm) * step_mm
    return list(np.arange(first, start + length + 1e-9, step_mm))


def draw_contour(
    canvas: Canvas,
    image_rect: Rect,
    crop_origin: tuple[float, float],
    contour_mm: np.ndarray,
) -> None:
    """Erkannten Umriss als Vektorpfad zeichnen - scharfe Schnittkante statt Fotorand."""
    if contour_mm is None or len(contour_mm) < 2:
        return

    canvas.saveState()
    canvas.setStrokeColorRGB(1.0, 0.0, 0.6)
    canvas.setLineWidth(config.CONTOUR_LINE_MM * config.PT_PER_MM)
    path = canvas.beginPath()
    start_x, start_y = crop_to_page(image_rect, crop_origin, contour_mm[0])
    path.moveTo(_pt(start_x), _pt(start_y))
    for point in contour_mm[1:]:
        x, y = crop_to_page(image_rect, crop_origin, point)
        path.lineTo(_pt(x), _pt(y))
    path.close()
    canvas.drawPath(path, stroke=1, fill=0)
    canvas.restoreState()


def draw_tile_marks(
    canvas: Canvas,
    placement: Rect,
    overlap_mm: float,
    has_right_neighbour: bool,
    has_bottom_neighbour: bool,
) -> None:
    """Schnitt- und Klebemarken: wo geschnitten und wie ueberlappt geklebt wird."""
    canvas.saveState()
    canvas.setStrokeGray(0.0)
    canvas.setLineWidth(0.3)

    # Eckmarken: die Schnittlinie des Nutzbereichs.
    tick = 4.0
    for corner_x, corner_y, dx, dy in (
        (placement.x, placement.y, 1, 1),
        (placement.x + placement.width, placement.y, -1, 1),
        (placement.x, placement.y + placement.height, 1, -1),
        (placement.x + placement.width, placement.y + placement.height, -1, -1),
    ):
        canvas.line(_pt(corner_x), _pt(corner_y), _pt(corner_x + dx * tick), _pt(corner_y))
        canvas.line(_pt(corner_x), _pt(corner_y), _pt(corner_x), _pt(corner_y + dy * tick))

    # Klebezone: gestrichelt markiert, damit klar ist, welcher Streifen doppelt ist.
    canvas.setDash(2, 2)
    canvas.setStrokeGray(0.55)
    if has_right_neighbour:
        x = placement.x + placement.width - overlap_mm
        canvas.line(_pt(x), _pt(placement.y), _pt(x), _pt(placement.y + placement.height))
    if has_bottom_neighbour:
        y = placement.y + overlap_mm
        canvas.line(_pt(placement.x), _pt(y), _pt(placement.x + placement.width), _pt(y))
    canvas.restoreState()


def draw_tile_label(canvas: Canvas, strip: Rect, text: str) -> None:
    """Blattnummer rechtsbuendig in den Streifen."""
    canvas.setFont("Helvetica-Bold", _TEXT_SIZE_PT + 1.0)
    canvas.setFillGray(0.0)
    canvas.drawRightString(_pt(strip.x + strip.width), _pt(strip.y + _TEXT_LINE_2_MM), text)


def _pt(millimetres: float) -> float:
    return float(millimetres) * config.PT_PER_MM
