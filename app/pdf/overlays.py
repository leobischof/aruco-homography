"""Aufdrucke: Kontrollmassstab, Metadaten, Millimeterraster, Passermarken, Kontur.

Alle Funktionen rechnen in Millimetern und rechnen erst beim Zeichnen in Punkte um.
Der Bezugspunkt ist immer die linke UNTERE Ecke der Seite.

Das Raster wird doppelt gezogen - breiter weisser Saum, darueber die Kernlinie in
Markentinte. Der Grund: die Schablone liegt mal auf einem hellen, mal auf einem
dunklen Foto. Eine einzelne graue Linie verschwindet auf dem einen oder dem
anderen; die Kombination ist auf beidem lesbar, ohne dass das Bild darunter
zugedeckt wird.
"""

from __future__ import annotations

import numpy as np
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from app import config
from app.i18n import translate
from app.pdf import branding
from app.pdf.layout import Rect

# Innenaufteilung des Streifens, von seiner Unterkante aus (Summe <= STRIP_H_MM).
_TEXT_LINE_1_MM = 1.8
_TEXT_LINE_2_MM = 5.4
_SCALEBAR_BASE_MM = 10.0
_SCALEBAR_HEIGHT_MM = 3.0
_SCALEBAR_LABEL_MM = 14.2
_TEXT_SIZE_PT = 6.0
_GAP_MM = 2.5


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
    tile_label: str | None = None,
    locale: str = config.DEFAULT_LOCALE,
) -> None:
    """Den Streifen unter dem Bild fuellen: Massstab, Metadaten, Blattnummer, Marke."""
    # Die Marke sitzt immer rechts aussen und bekommt ihren Platz zuerst; alles
    # andere richtet sich danach, damit nie etwas unter dem Logo verschwindet.
    with_claim = strip.width > branding.block_width_mm() + 70.0
    brand_left = branding.draw_brand_block(
        canvas, strip.x + strip.width, strip.y, strip.height, with_claim=with_claim
    )
    available = max(10.0, brand_left - _GAP_MM - strip.x)

    if show_scalebar:
        _draw_scalebar(canvas, strip, available, locale)

    canvas.setFillColor(branding.ink(config.BRAND_INK))
    for index, line in enumerate(footer_lines[:2]):
        offset = _TEXT_LINE_2_MM if index == 1 else _TEXT_LINE_1_MM
        canvas.setFont("Helvetica", _TEXT_SIZE_PT)
        canvas.drawString(
            _pt(strip.x), _pt(strip.y + offset), _fit(line, "Helvetica", _TEXT_SIZE_PT, available)
        )

    if tile_label:
        canvas.setFont("Helvetica-Bold", _TEXT_SIZE_PT + 1.0)
        canvas.drawRightString(
            _pt(strip.x + available),
            _pt(strip.y + _SCALEBAR_BASE_MM + 0.6),
            tile_label,
        )


def _fit(text: str, font: str, size_pt: float, width_mm: float) -> str:
    """Kuerzt Text mit Auslassungszeichen, statt ihn unter das Logo laufen zu lassen."""
    if stringWidth(text, font, size_pt) / config.PT_PER_MM <= width_mm:
        return text
    while text and stringWidth(text + "...", font, size_pt) / config.PT_PER_MM > width_mm:
        text = text[:-1]
    return text + "..."


def _draw_scalebar(
    canvas: Canvas, strip: Rect, available_mm: float, locale: str = config.DEFAULT_LOCALE
) -> None:
    """100-mm-Balken mit 10-mm-Teilung. Nachmessen beweist die Skalierung."""
    length = min(config.SCALEBAR_MM, available_mm)
    base_y = strip.y + _SCALEBAR_BASE_MM

    canvas.setLineWidth(0.4)
    canvas.setStrokeColor(branding.ink(config.BRAND_INK))
    canvas.setFillColor(branding.ink(config.BRAND_INK))

    # Wechselnd gefuellte 10-mm-Felder: auch aus der Entfernung eindeutig ablesbar.
    position, filled = 0.0, True
    while position < length - 1e-9:
        segment = min(10.0, length - position)
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
        translate("pdf.scalebar_caption", locale, length=f"{length:.0f}"),
    )


def draw_grid(
    canvas: Canvas,
    image_rect: Rect,
    crop_origin: tuple[float, float],
    step_mm: float = config.GRID_STEP_MM,
) -> None:
    """Hilfsraster ueber dem Bild, ausgerichtet am absoluten Zuschnittraster.

    Zwei Durchgaenge: erst alle weissen Saeume, dann alle Kernlinien. So legt sich
    kein Saum ueber eine bereits gezogene Kernlinie einer Kreuzung.
    """
    crop_x, crop_y = crop_origin
    vertical = [
        image_rect.x + (offset - crop_x)
        for offset in _grid_offsets(crop_x, image_rect.width, step_mm)
    ]
    horizontal = [
        image_rect.y + image_rect.height - (offset - crop_y)
        for offset in _grid_offsets(crop_y, image_rect.height, step_mm)
    ]

    canvas.saveState()
    for width_pt, colour in (
        (config.GRID_HALO_PT, (1.0, 1.0, 1.0)),
        (config.GRID_LINE_PT, None),
    ):
        canvas.setLineWidth(width_pt)
        if colour is None:
            canvas.setStrokeColor(branding.ink(config.GRID_INK))
        else:
            canvas.setStrokeColorRGB(*colour)
        for x in vertical:
            canvas.line(_pt(x), _pt(image_rect.y), _pt(x), _pt(image_rect.y + image_rect.height))
        for y in horizontal:
            canvas.line(_pt(image_rect.x), _pt(y), _pt(image_rect.x + image_rect.width), _pt(y))

    for offset, x in zip(_grid_offsets(crop_x, image_rect.width, step_mm), vertical):
        _grid_label(canvas, image_rect, x + 0.7, image_rect.y + 0.8, f"{offset:.0f}")
    for offset, y in zip(_grid_offsets(crop_y, image_rect.height, step_mm), horizontal):
        _grid_label(canvas, image_rect, image_rect.x + 0.7, y + 0.8, f"{offset:.0f}")
    canvas.restoreState()


def label_width(text: str, size_pt: float) -> float:
    """Breite der Beschriftung in Millimetern - ohne den Rand des Traegers."""
    return stringWidth(text, "Helvetica-Bold", size_pt) / config.PT_PER_MM


def draw_label(canvas: Canvas, x: float, y: float, text: str, size_pt: float) -> None:
    """Beschriftung auf weissem Traeger - lesbar auch auf dunklem Foto.

    Zwei Aufdrucke brauchen das: die Rasterbeschriftung ueber dem entzerrten Bild
    und die Blattnummer ueber dem Klebeplan. Beide stehen auf einem Foto, dessen
    Helligkeit niemand kennt; schwarzer Text allein ist dort mal lesbar und mal
    nicht.

    (x, y) ist die linke Grundlinie des Textes, so wie bei drawString.
    """
    width = label_width(text, size_pt)
    # Die Schriftgroesse wird hier als HOEHE gelesen. Eine Naeherung, ja - der
    # weisse Traeger soll den Text decken, nicht ihn vermessen.
    height = size_pt / config.PT_PER_MM

    canvas.setFillColorRGB(1.0, 1.0, 1.0)
    canvas.rect(
        _pt(x - 0.4), _pt(y - 0.4), _pt(width + 0.8), _pt(height * 0.95), stroke=0, fill=1
    )
    canvas.setFillColor(branding.ink(config.GRID_INK))
    canvas.setFont("Helvetica-Bold", size_pt)
    canvas.drawString(_pt(x), _pt(y), text)


def _grid_label(canvas: Canvas, image_rect: Rect, x: float, y: float, text: str) -> None:
    """Rasterbeschriftung, in den Bildbereich hineingeklemmt.

    Ohne das Klemmen rutscht die Null-Linie oben aus dem Bild in den Rand, und die
    aeusserste rechte Beschriftung haengt ueber die Bildkante hinaus.
    """
    size = config.GRID_LABEL_PT
    width = label_width(text, size)
    height = size / config.PT_PER_MM

    x = min(max(x, image_rect.x + 0.5), image_rect.x + image_rect.width - width - 0.5)
    y = min(max(y, image_rect.y + 0.5), image_rect.y + image_rect.height - height - 0.5)
    draw_label(canvas, x, y, text, size)


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
    canvas.setStrokeColor(branding.ink(config.BRAND_INK))
    canvas.setLineWidth(0.4)

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
    canvas.setStrokeColor(branding.ink(config.BRAND_PRIMARY))
    if has_right_neighbour:
        x = placement.x + placement.width - overlap_mm
        canvas.line(_pt(x), _pt(placement.y), _pt(x), _pt(placement.y + placement.height))
    if has_bottom_neighbour:
        y = placement.y + overlap_mm
        canvas.line(_pt(placement.x), _pt(y), _pt(placement.x + placement.width), _pt(y))
    canvas.restoreState()


def _pt(millimetres: float) -> float:
    return float(millimetres) * config.PT_PER_MM
