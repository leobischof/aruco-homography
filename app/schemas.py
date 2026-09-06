"""API-Typen. Einmal definiert, von den Routen und vom Frontend gemeinsam benutzt."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app import config


class CropMm(BaseModel):
    """Zuschnitt in Ebenen-Millimetern."""

    x0: float
    y0: float
    x1: float
    y1: float


class SolveRequest(BaseModel):
    session_id: str
    marker_mm: float = Field(default=config.MARKER_MM_NOMINAL, gt=0.0)
    mode: Literal["sheet", "free"] = "sheet"
    thickness_mm: float = 0.0
    camera_height_mm: float | None = Field(default=None, gt=0.0)
    # Mittelpunktabstaende des Markerblatts; nur im Blatt-Modus benutzt.
    spacing_x_mm: float = Field(default=config.SHEET_SPACING_MM[0], gt=0.0)
    spacing_y_mm: float = Field(default=config.SHEET_SPACING_MM[1], gt=0.0)

    @property
    def spacing_mm(self) -> tuple[float, float]:
        return (self.spacing_x_mm, self.spacing_y_mm)


class OverlayFlags(BaseModel):
    scalebar: bool = True
    grid: bool = True
    footer: bool = True
    marks: bool = True


class ExportRequest(BaseModel):
    session_id: str
    crop_mm: CropMm
    dpi: int = config.DPI_DEFAULT
    layout: Literal["single", "tiles"] = "single"
    page_format: Literal["A4", "A3"] = "A4"
    orientation: Literal["auto", "portrait", "landscape"] = "auto"
    overlap_mm: float = Field(default=config.TILE_OVERLAP_MM_DEFAULT, ge=0.0)
    printer_margin_mm: float = Field(default=config.PRINTER_MARGIN_MM_DEFAULT, ge=0.0)
    page_margin_mm: float = Field(default=config.PAGE_MARGIN_MM_DEFAULT, ge=0.0)
    overlays: OverlayFlags = Field(default_factory=OverlayFlags)
    tile_overview: bool = config.TILE_OVERVIEW_DEFAULT
    contour: bool = False
    filename: str = "schablone.pdf"
