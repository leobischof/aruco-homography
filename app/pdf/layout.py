"""Druckgeometrie - die SSOT dafuer, was "Originalgroesse" auf der Seite bedeutet.

Invariante des ganzen Projekts: das entzerrte Bild belegt auf der Seite exakt
crop_w x crop_h Millimeter. Alles andere (Massstab, Metadaten, Passermarken) lebt
in einem Streifen ausserhalb des Nutzbildes und beschneidet die Schablone nie.

Alle Rechtecke sind in Millimetern und von der linken UNTEREN Ecke aus gemessen -
so, wie ReportLab rechnet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app import config
from app.notices import AppError


@dataclass(frozen=True)
class Rect:
    """Rechteck in mm, Ursprung linke untere Ecke der Seite."""

    x: float
    y: float
    width: float
    height: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.width, self.height)


@dataclass(frozen=True)
class PageLayout:
    """Eine Einzelseite in exakter Objektgroesse plus Streifen."""

    page_w: float
    page_h: float
    image: Rect
    strip: Rect
    margin_mm: float


@dataclass(frozen=True)
class Tile:
    """Eine Kachel: welcher Teil des Zuschnitts, an welcher Stelle der Seite."""

    index: int
    col: int
    row: int
    crop_x: float
    crop_y: float
    src_w: float
    src_h: float
    placement: Rect


@dataclass(frozen=True)
class TileLayout:
    """Kachelplan fuer einen Zuschnitt auf einem Papierformat."""

    sheet_w: float
    sheet_h: float
    usable_w: float
    usable_h: float
    step_w: float
    step_h: float
    n_cols: int
    n_rows: int
    overlap_mm: float
    printer_margin_mm: float
    strip: Rect
    tiles: list[Tile]

    @property
    def page_count(self) -> int:
        return len(self.tiles)


def strip_height() -> float:
    """Hoehe des Streifens unter dem Bild.

    Der Streifen ist IMMER da, auch wenn Massstab und Fusszeile abgeschaltet sind:
    er traegt das Markenzeichen, und das gehoert auf jedes Blatt. Die Schalter
    steuern nur, was ausser der Marke darin steht. Der Preis dafuer ist, dass eine
    Seite nie exakt die Objektgroesse hat - die Invariante aus 4.1 betrifft das
    BILD, und die bleibt unberuehrt.
    """
    return config.STRIP_H_MM


def single_page(crop_w: float, crop_h: float, margin_mm: float, strip_h: float) -> PageLayout:
    """Seitengeometrie fuer die Einzelseite (Spec 4.2)."""
    if crop_w <= 0.0 or crop_h <= 0.0:
        raise AppError("empty_crop", "crop_mm")

    page_w = crop_w + 2.0 * margin_mm
    page_h = crop_h + 2.0 * margin_mm + strip_h
    return PageLayout(
        page_w=page_w,
        page_h=page_h,
        image=Rect(margin_mm, margin_mm + strip_h, crop_w, crop_h),
        strip=Rect(margin_mm, margin_mm, crop_w, strip_h),
        margin_mm=margin_mm,
    )


def sheet_size(page_format: str, orientation: str) -> tuple[float, float]:
    """Papierformat in mm. orientation ist hier bereits entschieden."""
    if page_format not in config.SHEET_FORMATS:
        raise AppError(
            "bad_page_format",
            "page_format",
            page_format=page_format,
            formats=", ".join(sorted(config.SHEET_FORMATS)),
        )
    width, height = config.SHEET_FORMATS[page_format]
    return (height, width) if orientation == "landscape" else (width, height)


def tile_layout(
    crop_w: float,
    crop_h: float,
    page_format: str,
    orientation: str,
    printer_margin_mm: float,
    overlap_mm: float,
    strip_h: float,
) -> TileLayout:
    """Kachelplan berechnen. orientation "auto" waehlt die seitensparende Variante."""
    if orientation == "auto":
        orientation = _cheaper_orientation(
            crop_w, crop_h, page_format, printer_margin_mm, overlap_mm, strip_h
        )

    sheet_w, sheet_h = sheet_size(page_format, orientation)
    usable_w = sheet_w - 2.0 * printer_margin_mm
    usable_h = sheet_h - 2.0 * printer_margin_mm - strip_h
    step_w = usable_w - overlap_mm
    step_h = usable_h - overlap_mm

    if usable_w <= 0.0 or usable_h <= 0.0:
        raise AppError("margins_too_large", "printer_margin_mm", page_format=page_format)
    if step_w <= 0.0 or step_h <= 0.0:
        raise AppError(
            "overlap_too_large",
            "overlap_mm",
            overlap_mm=f"{overlap_mm:.0f}",
            page_format=page_format,
            usable_w_mm=f"{usable_w:.0f}",
            usable_h_mm=f"{usable_h:.0f}",
        )

    n_cols = max(1, math.ceil((crop_w - overlap_mm) / step_w))
    n_rows = max(1, math.ceil((crop_h - overlap_mm) / step_h))

    tiles: list[Tile] = []
    for row in range(n_rows):
        for col in range(n_cols):
            crop_x = col * step_w
            crop_y = row * step_h
            src_w = min(usable_w, crop_w - crop_x)
            src_h = min(usable_h, crop_h - crop_y)
            # Der Inhalt sitzt oben in der nutzbaren Flaeche; die letzte Kachel
            # laeuft unten leer aus, statt den Inhalt zu verschieben.
            placement = Rect(
                printer_margin_mm,
                printer_margin_mm + strip_h + (usable_h - src_h),
                src_w,
                src_h,
            )
            tiles.append(
                Tile(len(tiles) + 1, col, row, crop_x, crop_y, src_w, src_h, placement)
            )

    return TileLayout(
        sheet_w=sheet_w,
        sheet_h=sheet_h,
        usable_w=usable_w,
        usable_h=usable_h,
        step_w=step_w,
        step_h=step_h,
        n_cols=n_cols,
        n_rows=n_rows,
        overlap_mm=overlap_mm,
        printer_margin_mm=printer_margin_mm,
        strip=Rect(printer_margin_mm, printer_margin_mm, usable_w, strip_h),
        tiles=tiles,
    )


def _cheaper_orientation(
    crop_w: float,
    crop_h: float,
    page_format: str,
    printer_margin_mm: float,
    overlap_mm: float,
    strip_h: float,
) -> str:
    """Hoch- oder Querformat - was weniger Blaetter braucht. Gleichstand: hoch."""
    counts: dict[str, int] = {}
    for candidate in ("portrait", "landscape"):
        try:
            plan = tile_layout(
                crop_w, crop_h, page_format, candidate, printer_margin_mm, overlap_mm, strip_h
            )
            counts[candidate] = plan.page_count
        except AppError:
            continue

    if not counts:
        return "portrait"  # tile_layout wirft dann den aussagekraeftigen Fehler
    return min(counts, key=lambda key: (counts[key], key != "portrait"))
