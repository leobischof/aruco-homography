"""PDF bauen: Einzelseite in Originalgroesse oder Kachelung mit Uebersichtsblatt.

Die eine Zusage, die dieses Modul einhalten muss: das entzerrte Bild belegt auf der
Seite exakt so viele Millimeter, wie der Zuschnitt gross ist. Deshalb wird jedes
Bild mit gesetzter Breite UND Hoehe platziert (preserveAspectRatio=False) - nichts
darf hier automatisch skaliert werden.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from app import config
from app.i18n import translate
from app.pdf import branding, generator, overlays
from app.pdf.layout import Rect, TileLayout, single_page, strip_height, tile_layout

# Die Blattnummer im Klebeplan. Groesser als die Rasterbeschriftung, weil sie aus
# Armlaenge gefunden werden muss, und kleiner als die Ueberschrift, weil sie in die
# kleinste Kachel passen muss.
_OVERVIEW_LABEL_PT = 10.0
# Kachelrand, Aussenkante des Zuschnitts, und der weisse Saum, der auf beide
# aufgeschlagen wird. Der Saum ist noetig, seit unter den Linien das Bild liegt:
# eine duenne Linie ist auf einem Foto mal sichtbar und mal nicht.
_OVERVIEW_LINE_PT = 0.4
_OVERVIEW_EDGE_PT = 0.8
_OVERVIEW_HALO_PT = 0.8


@dataclass
class ExportOptions:
    """Alles, was der Bediener am Druck einstellen kann."""

    dpi: int = config.DPI_DEFAULT
    # "single" | "tiles". Bewusst NICHT config.LAYOUT_DEFAULT: das ist die Vorgabe
    # der Bedienung, und die ist die Kachelung. Hier, eine Schicht tiefer, ist "eine
    # Seite" der schlichte Fall - ein Bild, eine Seite - und Kachelung eine
    # Betriebsart, die der Aufrufer verlangt. Wer die beiden gleichzieht, aendert
    # stillschweigend, was tests/test_branding.py mit ExportOptions() prueft.
    layout: str = "single"
    page_format: str = "A4"
    orientation: str = "auto"
    overlap_mm: float = config.TILE_OVERLAP_MM_DEFAULT
    printer_margin_mm: float = config.PRINTER_MARGIN_MM_DEFAULT
    page_margin_mm: float = config.PAGE_MARGIN_MM_DEFAULT
    show_scalebar: bool = True
    show_grid: bool = True
    show_footer: bool = True
    show_marks: bool = True
    tile_overview: bool = config.TILE_OVERVIEW_DEFAULT
    contour: bool = False
    title: str = "ArUco-Homographie"
    # Sprache der Aufdrucke. Die Marke bleibt davon unberuehrt - sie ist ein
    # Zeichen, kein Text (AGENTS.md, Invariante 3).
    locale: str = config.DEFAULT_LOCALE


@dataclass
class BuildResult:
    """Das PDF und die Geometrie, mit der es gebaut wurde - fuer Header und Tests."""

    data: bytes
    page_size_mm: tuple[float, float]
    image_rect_mm: tuple[float, float, float, float]
    page_count: int
    meta: dict[str, float] = field(default_factory=dict)


def build_pdf(
    rectified_bgr: np.ndarray,
    crop_w_mm: float,
    crop_h_mm: float,
    options: ExportOptions,
    footer_lines: list[str],
    contour_mm: np.ndarray | None = None,
) -> BuildResult:
    """Einstiegspunkt: baut je nach Option eine Seite oder eine Kachelung."""
    if generator() == "js":
        return _build_via_javascript(
            rectified_bgr, crop_w_mm, crop_h_mm, options, footer_lines, contour_mm
        )
    if options.layout == "tiles":
        return _build_tiles(rectified_bgr, crop_w_mm, crop_h_mm, options, footer_lines, contour_mm)
    return _build_single(rectified_bgr, crop_w_mm, crop_h_mm, options, footer_lines, contour_mm)


def _build_via_javascript(
    image_bgr: np.ndarray,
    crop_w: float,
    crop_h: float,
    options: ExportOptions,
    footer_lines: list[str],
    contour_mm: np.ndarray | None,
) -> BuildResult:
    """Den Bau nach web/pdf/ geben und das Ergebnis unveraendert durchreichen.

    Die Geometrie im BuildResult kommt aus dem JavaScript-Ergebnis und NICHT aus
    einer zweiten Rechnung hier. Sonst pruefte die Suite am Ende die Python-Zahlen
    gegen sich selbst, und genau das soll sie nicht.

    Der Import steht in der Funktion: tools/ gehoert dem Pruefstand und darf im
    ausgelieferten Bundle fehlen. Oben im Modul wuerde sein Fehlen den Start der
    Anwendung kosten - fuer etwas, das im Betrieb nie aufgerufen wird.
    """
    from tools.pdf_js_bridge import build_pdf_via_node

    answer = build_pdf_via_node(
        image_bgr, crop_w, crop_h, options, footer_lines, contour_mm
    )
    return BuildResult(
        data=answer["data"],
        page_size_mm=tuple(answer["page_size_mm"]),
        image_rect_mm=tuple(answer["image_rect_mm"]),
        page_count=answer["page_count"],
        meta=answer["meta"],
    )


def _build_single(
    image_bgr: np.ndarray,
    crop_w: float,
    crop_h: float,
    options: ExportOptions,
    footer_lines: list[str],
    contour_mm: np.ndarray | None,
) -> BuildResult:
    strip_h = strip_height()
    page = single_page(crop_w, crop_h, options.page_margin_mm, strip_h)

    buffer = io.BytesIO()
    canvas = _new_canvas(buffer, page.page_w, page.page_h, options.title)

    _place_image(canvas, image_bgr, page.image)
    _decorate(canvas, page.image, (0.0, 0.0), options, contour_mm)
    overlays.draw_strip(
        canvas,
        page.strip,
        options.show_scalebar,
        footer_lines if options.show_footer else [],
        locale=options.locale,
    )

    canvas.showPage()
    canvas.save()

    return BuildResult(
        data=buffer.getvalue(),
        page_size_mm=(page.page_w, page.page_h),
        image_rect_mm=page.image.as_tuple(),
        page_count=1,
    )


def _build_tiles(
    image_bgr: np.ndarray,
    crop_w: float,
    crop_h: float,
    options: ExportOptions,
    footer_lines: list[str],
    contour_mm: np.ndarray | None,
) -> BuildResult:
    strip_h = strip_height()
    plan = tile_layout(
        crop_w,
        crop_h,
        options.page_format,
        options.orientation,
        options.printer_margin_mm,
        options.overlap_mm,
        strip_h,
    )

    buffer = io.BytesIO()
    canvas = _new_canvas(buffer, plan.sheet_w, plan.sheet_h, options.title)
    pages = 0

    if options.tile_overview:
        _draw_overview(canvas, plan, crop_w, crop_h, footer_lines, image_bgr, options.locale)
        canvas.showPage()
        pages += 1

    px_per_mm = image_bgr.shape[1] / crop_w
    for tile in plan.tiles:
        slice_bgr = _crop_pixels(image_bgr, tile.crop_x, tile.crop_y, tile.src_w, tile.src_h, px_per_mm)
        _place_image(canvas, slice_bgr, tile.placement)
        _decorate(canvas, tile.placement, (tile.crop_x, tile.crop_y), options, contour_mm)

        if options.show_marks:
            overlays.draw_tile_marks(
                canvas,
                tile.placement,
                plan.overlap_mm,
                has_right_neighbour=tile.col < plan.n_cols - 1,
                has_bottom_neighbour=tile.row < plan.n_rows - 1,
            )
        overlays.draw_strip(
            canvas,
            plan.strip,
            options.show_scalebar,
            footer_lines if options.show_footer else [],
            tile_label=_tile_label(tile.index, plan.page_count, tile.col, tile.row, options.locale),
            locale=options.locale,
        )

        canvas.showPage()
        pages += 1

    canvas.save()
    first = plan.tiles[0].placement
    return BuildResult(
        data=buffer.getvalue(),
        page_size_mm=(plan.sheet_w, plan.sheet_h),
        image_rect_mm=first.as_tuple(),
        page_count=pages,
        meta={"n_cols": plan.n_cols, "n_rows": plan.n_rows, "tiles": plan.page_count},
    )


def _tile_label(index: int, count: int, col: int, row: int, locale: str) -> str:
    """Blattnummer und Rasterplatz - zwei Bausteine, damit beide Sprachen frei sind."""
    sheet = translate("pdf.tiles.sheet", locale, index=index, count=count)
    position = translate("pdf.tiles.position", locale, col=col + 1, row=row + 1)
    return f"{sheet} - {position}"


def _new_canvas(buffer: io.BytesIO, width_mm: float, height_mm: float, title: str) -> Canvas:
    canvas = Canvas(buffer, pagesize=(_pt(width_mm), _pt(height_mm)))
    canvas.setTitle(title)
    canvas.setCreator("ArUco-Homographie")
    return canvas


def _decorate(
    canvas: Canvas,
    image_rect: Rect,
    crop_origin: tuple[float, float],
    options: ExportOptions,
    contour_mm: np.ndarray | None,
) -> None:
    """Raster und Kontur ueber das Bild legen, sauber auf den Bildbereich beschnitten."""
    if options.show_grid:
        overlays.draw_grid(canvas, image_rect, crop_origin)
    if options.contour and contour_mm is not None and len(contour_mm) >= 2:
        canvas.saveState()
        _clip_to(canvas, image_rect)
        overlays.draw_contour(canvas, image_rect, crop_origin, contour_mm)
        canvas.restoreState()


def _clip_to(canvas: Canvas, rect: Rect) -> None:
    path = canvas.beginPath()
    path.rect(_pt(rect.x), _pt(rect.y), _pt(rect.width), _pt(rect.height))
    canvas.clipPath(path, stroke=0, fill=0)


def _place_image(canvas: Canvas, image_bgr: np.ndarray, rect: Rect) -> None:
    """Bild auf ein exaktes Millimeter-Rechteck setzen. Kein Auto-Scaling."""
    canvas.drawImage(
        _as_reader(image_bgr),
        _pt(rect.x),
        _pt(rect.y),
        width=_pt(rect.width),
        height=_pt(rect.height),
        preserveAspectRatio=False,
        anchor="sw",
    )


def _as_reader(image_bgr: np.ndarray) -> ImageReader:
    """BGR-Array als JPEG in den PDF-Stream - haelt die Datei handhabbar gross."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    buffer = io.BytesIO()
    Image.fromarray(rgb).save(buffer, format="JPEG", quality=config.JPEG_QUALITY)
    buffer.seek(0)
    return ImageReader(buffer)


def _crop_pixels(
    image_bgr: np.ndarray,
    crop_x: float,
    crop_y: float,
    width_mm: float,
    height_mm: float,
    px_per_mm: float,
) -> np.ndarray:
    """Pixelausschnitt fuer eine Kachel. Das mm-Rechteck bleibt massgeblich."""
    x0 = int(round(crop_x * px_per_mm))
    y0 = int(round(crop_y * px_per_mm))
    x1 = min(image_bgr.shape[1], x0 + max(1, int(round(width_mm * px_per_mm))))
    y1 = min(image_bgr.shape[0], y0 + max(1, int(round(height_mm * px_per_mm))))
    return image_bgr[y0:y1, x0:x1]


def _overview_thumbnail(image_bgr: np.ndarray) -> np.ndarray:
    """Den Zuschnitt auf Daumennagelgroesse bringen.

    Auf dem Klebeplan wird das Bild ANGESEHEN und nicht nachgemessen - es sagt,
    welches Blatt welchen Teil zeigt. In voller Aufloesung waere es ein zweites Mal
    das ganze Raster in derselben Datei: ReportLab kodiert bei jedem drawImage neu,
    teilt also nichts mit den Kachelseiten. config.OVERVIEW_MAX_PX sagt, wo Schluss
    ist, und INTER_AREA ist die Verkleinerung, die nicht aliast.
    """
    height, width = image_bgr.shape[:2]
    longest = max(width, height)
    if longest <= config.OVERVIEW_MAX_PX:
        return image_bgr
    factor = config.OVERVIEW_MAX_PX / longest
    return cv2.resize(
        image_bgr,
        (max(1, int(round(width * factor))), max(1, int(round(height * factor)))),
        interpolation=cv2.INTER_AREA,
    )


def _draw_overview(
    canvas: Canvas,
    plan: TileLayout,
    crop_w: float,
    crop_h: float,
    footer_lines: list[str],
    image_bgr: np.ndarray,
    locale: str = config.DEFAULT_LOCALE,
) -> None:
    """Uebersichtsblatt: welches Blatt gehoert wohin - ueber dem Zuschnitt selbst."""
    ink = branding.ink(config.BRAND_INK)
    title = translate("pdf.assembly.title", locale)
    canvas.setFillColor(ink)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(_pt(plan.printer_margin_mm), _pt(plan.sheet_h - 20.0), title)

    canvas.setFont("Helvetica", 9)
    canvas.drawString(
        _pt(plan.printer_margin_mm),
        _pt(plan.sheet_h - 28.0),
        translate(
            "pdf.assembly.summary",
            locale,
            width=f"{crop_w:.1f}",
            height=f"{crop_h:.1f}",
            pages=plan.page_count,
            cols=plan.n_cols,
            rows=plan.n_rows,
            overlap=f"{plan.overlap_mm:.0f}",
        ),
    )

    # Raster massstabsgetreu in den verbleibenden Platz einpassen. Unten bleibt der
    # Streifen frei, damit Marke und Metadaten auch hier stehen koennen.
    strip = Rect(
        plan.printer_margin_mm,
        plan.printer_margin_mm,
        plan.sheet_w - 2.0 * plan.printer_margin_mm,
        config.STRIP_H_MM,
    )
    area_w = plan.sheet_w - 2.0 * plan.printer_margin_mm
    area_h = plan.sheet_h - 40.0 - (strip.y + strip.height + 8.0)
    scale = min(area_w / max(crop_w, 1e-6), area_h / max(crop_h, 1e-6))
    origin_x = plan.printer_margin_mm
    origin_y = plan.sheet_h - 40.0 - crop_h * scale
    outline = Rect(origin_x, origin_y, crop_w * scale, crop_h * scale)

    # Das Bild ZUERST: alles Weitere ist ein Aufdruck darauf. Wer wissen will,
    # welches Blatt er in der Hand hat, sucht nach dem, was darauf zu sehen ist -
    # eine leere Kachelnummerierung sagt ihm das nicht.
    _place_image(canvas, _overview_thumbnail(image_bgr), outline)

    tiles = [
        (
            Rect(
                origin_x + tile.crop_x * scale,
                origin_y + (crop_h - tile.crop_y - tile.src_h) * scale,
                tile.src_w * scale,
                tile.src_h * scale,
            ),
            str(tile.index),
        )
        for tile in plan.tiles
    ]
    borders = [(rect, _OVERVIEW_LINE_PT, branding.ink(config.BRAND_PRIMARY))
               for rect, _ in tiles]
    borders.append((outline, _OVERVIEW_EDGE_PT, ink))

    # Zwei Durchgaenge wie beim Raster (app/pdf/overlays.draw_grid): erst alle
    # weissen Saeume, dann alle Kernlinien. Der Saum einer Kachel darf die
    # Kernlinie ihrer Nachbarin nicht zudecken - die Kacheln ueberlappen sich.
    for halo in (True, False):
        for rect, width_pt, colour in borders:
            canvas.setLineWidth(width_pt + _OVERVIEW_HALO_PT if halo else width_pt)
            if halo:
                canvas.setStrokeColorRGB(1.0, 1.0, 1.0)
            else:
                canvas.setStrokeColor(colour)
            canvas.rect(_pt(rect.x), _pt(rect.y), _pt(rect.width), _pt(rect.height))

    # Die Nummern zuletzt: kein Saum soll ueber ihnen liegen.
    for rect, label in tiles:
        overlays.draw_label(
            canvas,
            rect.x + rect.width / 2.0 - overlays.label_width(label, _OVERVIEW_LABEL_PT) / 2.0,
            rect.y + rect.height / 2.0,
            label,
            _OVERVIEW_LABEL_PT,
        )

    overlays.draw_strip(canvas, strip, show_scalebar=True, footer_lines=footer_lines,
                        tile_label=title, locale=locale)


# Die Platzhalter der beiden Fusszeilen. Was der Aufrufer nicht mitgibt, wird zu "?" -
# eine halb gefuellte Zeile ist immer noch besser als eine fehlende.
_FOOTER_FIELDS = (
    "object_mm",
    "dpi",
    "scale",
    "mode",
    "marker_ids",
    "marker_mm",
    "rms",
    "camera",
    "thickness",
    "extrapolation",
    "source",
    "timestamp",
)


def build_footer_lines(
    meta: dict[str, object], locale: str = config.DEFAULT_LOCALE
) -> list[str]:
    """Zwei Zeilen Metadaten - alles, was einen Ausdruck spaeter nachvollziehbar macht."""
    values = {field: meta.get(field, "?") for field in _FOOTER_FIELDS}
    return [
        translate("pdf.footer.line1", locale, **values),
        translate("pdf.footer.line2", locale, **values),
    ]


def _pt(millimetres: float) -> float:
    return float(millimetres) * config.PT_PER_MM
