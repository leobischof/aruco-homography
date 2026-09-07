"""API-Typen. Einmal definiert, von den Routen und vom Frontend gemeinsam benutzt."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app import config, i18n
from app.vision import enhance

# Waehlbare Farbbetonungen: "keine" plus jeder Farbton, den config kennt. Aus dem
# Woerterbuch gebaut und nicht abgeschrieben - ein neuer Farbton in config.py ist
# damit sofort gueltig, statt still an der Validierung zu scheitern.
EMPHASIS_CHOICES = ("none", *config.ADJUST_EMPHASIS_HUES)


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


class AdjustOptions(BaseModel):
    """Die Drahtform der Bildaufbereitung - der HTTP-Spiegel der Dataclass.

    SSOT der Namen, Vorgaben und Wertebereiche ist `app.vision.enhance.AdjustOptions`;
    dieses Modell spiegelt sie und erfindet nichts dazu. Hier steht ausschliesslich,
    wie die Regler ueber die Leitung kommen und welche Werte ueberhaupt zugelassen
    sind - gerechnet wird allein in enhance.py. Wer dort einen Regler hinzufuegt,
    ergaenzt ihn hier, und `test_adjust_api.py` besteht darauf, dass beide Fassungen
    Feld fuer Feld und Vorgabe fuer Vorgabe uebereinstimmen.
    """

    grayscale: bool = False
    invert: bool = False
    brightness: float = Field(default=0.0, ge=-1.0, le=1.0)
    contrast: float = Field(default=0.0, ge=-1.0, le=1.0)
    saturation: float = Field(default=0.0, ge=-1.0, le=1.0)
    local_contrast: float = Field(default=0.0, ge=0.0, le=1.0)
    edge_boost: float = Field(default=0.0, ge=0.0, le=1.0)
    edge_overlay: float = Field(default=0.0, ge=0.0, le=1.0)
    color_emphasis: Literal[EMPHASIS_CHOICES] = "none"
    emphasis_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)

    def to_enhance(self) -> enhance.AdjustOptions:
        """In die Dataclass umsetzen, mit der die Aufbereitung rechnet.

        Feldweise Zuweisung waere eine zweite Liste derselben Namen - genau die,
        die auseinanderlaufen wuerde. Ein fehlendes oder ueberzaehliges Feld
        scheitert hier sofort mit TypeError, statt sich lautlos zu verlieren.
        """
        return enhance.AdjustOptions(**self.model_dump())


class AdjustRequest(BaseModel):
    """Live-Vorschau: dieselben Regler wie beim Export, nur auf dem Vorschaubild."""

    session_id: str
    adjust: AdjustOptions = Field(default_factory=AdjustOptions)


class ExportRequest(BaseModel):
    session_id: str
    crop_mm: CropMm
    dpi: int = config.DPI_DEFAULT
    # Vorgabe ist die Kachelung, nicht die Einzelseite - siehe config.LAYOUT_DEFAULT.
    # Dazu gehoert tile_overview als Klebeplan, sonst weiss niemand, welches Blatt
    # wohin gehoert.
    layout: Literal["single", "tiles"] = config.LAYOUT_DEFAULT
    page_format: Literal["A4", "A3"] = "A4"
    orientation: Literal["auto", "portrait", "landscape"] = "auto"
    overlap_mm: float = Field(default=config.TILE_OVERLAP_MM_DEFAULT, ge=0.0)
    printer_margin_mm: float = Field(default=config.PRINTER_MARGIN_MM_DEFAULT, ge=0.0)
    page_margin_mm: float = Field(default=config.PAGE_MARGIN_MM_DEFAULT, ge=0.0)
    overlays: OverlayFlags = Field(default_factory=OverlayFlags)
    tile_overview: bool = config.TILE_OVERVIEW_DEFAULT
    contour: bool = False
    # Die Aufbereitung des Ausdrucks. Neutral gestellt heisst: das entzerrte Bild
    # geht unveraendert ins PDF.
    adjust: AdjustOptions = Field(default_factory=AdjustOptions)
    # Sprache der Aufdrucke. Der Ausdruck folgt damit der Sprache, die in der App
    # gewaehlt ist, statt immer der Vorgabesprache des Servers.
    locale: str = config.DEFAULT_LOCALE
    filename: str = "schablone.pdf"

    @field_validator("locale")
    @classmethod
    def _normalise_locale(cls, value: str) -> str:
        """Sprachkuerzel auf eine unterstuetzte Sprache abbilden.

        Abbilden statt ablehnen: "de-CH" und ein leeres Feld sind keine
        Bedienfehler, und ein Export soll an einer Sprachangabe niemals scheitern -
        er kommt dann eben in der Vorgabesprache. i18n.normalise ist die einzige
        Stelle, die diese Abbildung kennt.
        """
        return i18n.normalise(value)
