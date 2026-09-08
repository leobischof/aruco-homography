"""Orchestrierung: verkettet Erkennung, Ausgleich, Pose, Korrektur, Entzerrung, PDF.

Die Routen in main.py bleiben dadurch reines Transportgeschaeft, und der komplette
Rechenweg ist ohne HTTP testbar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime

import cv2
import numpy as np

from app import config, i18n
from app.notices import AppError, NoticeList
from app.pdf.build import BuildResult, ExportOptions, build_footer_lines, build_pdf
from app.schemas import AdjustRequest, ExportImageRequest, ExportRequest, SolveRequest
from app.session import Session
from app.vision import contour as contour_module
from app.vision import encode
from app.vision import enhance
from app.vision import rectify as rectify_module
from app.vision.camera import CameraPose, resolve_pose
from app.vision.detect import detect_markers, draw_detection
from app.vision.extent import Extent, default_crop, extrapolation_fraction, plane_extent
from app.vision.solve import Solution, solve
from app.vision.thickness import effective_homography


@dataclass(frozen=True)
class ImageResult:
    """Der Zuschnitt als Bilddatei - und was die Oberflaeche darueber sagt."""

    data: bytes
    width: int
    height: int


@dataclass
class SolveResult:
    """Alles, was die UI nach dem Entzerren anzeigt - und was der Export braucht."""

    solution: Solution
    pose: CameraPose
    homography_effective: np.ndarray
    correction_factor: float
    thickness_mm: float
    marker_mm: float
    extent: Extent
    crop: Extent
    preview_px_per_mm: float
    notices: NoticeList
    elapsed_s: float


def run_solve(session: Session, request: SolveRequest) -> SolveResult:
    """Vom Foto zur entzerrten Vorschau samt Qualitaetsbericht."""
    started = time.perf_counter()
    notices = NoticeList()

    if not session.markers:
        session.markers = detect_markers(session.photo.bgr)
        session.write_preview("detected", draw_detection(session.photo.bgr, session.markers))

    solution = solve(
        session.markers, request.marker_mm, request.mode, notices, request.spacing_mm
    )

    pose = resolve_pose(
        solution.homography,
        session.photo.focal35_mm,
        session.photo.width,
        session.photo.height,
        request.thickness_mm,
        request.camera_height_mm,
        notices,
    )
    homography_effective, factor = effective_homography(
        solution.homography, pose, request.thickness_mm
    )

    extent = plane_extent(
        homography_effective, session.photo.width, session.photo.height, solution.hull_mm
    )
    crop = default_crop(extent, solution.hull_mm)

    preview_px_per_mm = rectify_module.preview_px_per_mm(extent)
    preview = rectify_module.rectify(
        session.photo.bgr,
        homography_effective,
        extent,
        preview_px_per_mm,
        source_px_per_mm=solution.px_per_mm,
    )
    session.write_preview("rectified", preview)

    result = SolveResult(
        solution=solution,
        pose=pose,
        homography_effective=homography_effective,
        correction_factor=factor,
        thickness_mm=request.thickness_mm,
        marker_mm=request.marker_mm,
        extent=extent,
        crop=crop,
        preview_px_per_mm=preview_px_per_mm,
        notices=notices,
        elapsed_s=time.perf_counter() - started,
    )
    session.state["solve"] = result
    return result


def run_adjust(session: Session, request: AdjustRequest) -> dict[str, object]:
    """Regler auf die entzerrte Vorschau anwenden - die Antwort fuer den Live-Regler.

    Gearbeitet wird auf dem bereits geschriebenen Vorschau-JPEG, nicht auf einer
    frischen Entzerrung: der Regler soll waehrend des Ziehens antworten, und eine
    Entzerrung des vollen Fotos dauert um Groessenordnungen laenger. Erlaubt ist
    die Abkuerzung, weil die Aufbereitung kosmetisch ist (app/vision/enhance.py) -
    sie taugt am kleinen Bild genau wie am grossen. Verbindlich fuer den Druck ist
    trotzdem allein der Export: der wendet dieselben Regler auf das volle Raster an.
    """
    solved = session.state.get("solve")
    if not isinstance(solved, SolveResult):
        raise AppError("not_solved", "session_id")

    options = request.adjust.to_enhance()
    if options.is_identity:
        # Nichts zu tun: die unveraenderte Vorschau liegt bereits auf der Platte.
        # Eine zweite, Pixel fuer Pixel gleiche Datei waere nur ein Umweg.
        return {"preview": _preview_payload(session, "rectified", solved)}

    rectified = cv2.imread(str(session.preview_path("rectified")))
    if rectified is None:
        raise AppError("preview_missing")

    session.write_preview("adjusted", enhance.adjust(rectified, options))
    return {"preview": _preview_payload(session, "adjusted", solved)}


def _rectified_crop(
    session: Session, request: ExportRequest | ExportImageRequest
) -> tuple[SolveResult, np.ndarray, Extent, float]:
    """Der gemeinsame Anfang beider Exporte: entzerren und aufbereiten.

    `request` muss `crop_mm`, `dpi` und `adjust` tragen - mehr wird hier nicht
    angefasst. Deshalb passen beide Anfragetypen hinein, ohne dass einer den
    anderen erben muesste: was sie unterscheidet (Seitenformat gegen Dateiformat),
    faengt erst NACH dieser Funktion an.
    """
    solved = session.state.get("solve")
    if not isinstance(solved, SolveResult):
        raise AppError("not_solved", "session_id")

    crop = Extent(request.crop_mm.x0, request.crop_mm.y0, request.crop_mm.x1, request.crop_mm.y1)
    if crop.width <= 0.0 or crop.height <= 0.0:
        raise AppError("empty_crop", "crop_mm")

    rectify_module.check_output_budget(crop, request.dpi)
    px_per_mm = rectify_module.px_per_mm_for_dpi(request.dpi)
    rectified = rectify_module.rectify(
        session.photo.bgr,
        solved.homography_effective,
        crop,
        px_per_mm,
        source_px_per_mm=solved.solution.px_per_mm,
    )

    # Aufbereiten NACH dem Entzerren und VOR allem anderen: die Homographie wurde
    # am unberuehrten Foto gemessen, ab hier aendert sich nur noch Farbe und Ton.
    # Die is_identity-Abkuerzung spart bei neutralen Reglern eine vollstaendige
    # Kopie des Rasters - das sind am oberen Ende des Budgets mehrere hundert MB.
    adjust_options = request.adjust.to_enhance()
    if not adjust_options.is_identity:
        rectified = enhance.adjust(rectified, adjust_options)

    return solved, rectified, crop, px_per_mm


def run_export_image(session: Session, request: ExportImageRequest) -> ImageResult:
    """Denselben Zuschnitt als Bilddatei statt als PDF.

    **Was hier fehlt und fehlen muss:** Massstab, Raster, Fusszeile, Schnittmarken,
    Klebeplan. Alles davon ist ein AUFDRUCK auf einem Ausdruck - auf einem Bild
    waere es Bildinhalt, den ein nachgelagertes Programm nicht von der Schablone
    unterscheiden koennte.

    Was NICHT fehlt, ist die Massangabe: die Auflösung steht in der Datei
    (app/vision/encode.py). Ein Pixel ist damit 25,4/dpi Millimeter, und das laesst
    sich lesen statt raten.
    """
    _, rectified, _, _ = _rectified_crop(session, request)
    return ImageResult(
        data=encode.encode_image(rectified, request.image_format, request.dpi),
        width=int(rectified.shape[1]),
        height=int(rectified.shape[0]),
    )


def run_export(session: Session, request: ExportRequest) -> BuildResult:
    """Vom gewaehlten Zuschnitt zum druckfertigen PDF."""
    # Die Sprache des Ausdrucks kommt aus der Anfrage. normalise ist idempotent -
    # das Schema hat den Wert schon abgebildet; hier steht es noch einmal, damit
    # auch ein von Hand gebautes ExportRequest nicht mit "en-GB" durchrutscht.
    locale = i18n.normalise(request.locale)

    solved, rectified, crop, px_per_mm = _rectified_crop(session, request)

    contour_mm = None
    if request.contour:
        # Gesucht wird auf dem AUFBEREITETEN Bild - also auf genau dem, das gleich
        # gedruckt wird. Der Benutzer stellt die Regler ja gerade deshalb, damit
        # eine blasse Bleistiftlinie ueberhaupt als Kante erkennbar wird; auf dem
        # rohen Bild fiele sie durch und die Kontur bliebe leer. Umgekehrt waere
        # eine Kontur aus dem rohen Bild auf dem aufbereiteten Ausdruck eine
        # zweite, andere Wahrheit auf demselben Blatt.
        # Millimeter kostet das nichts: die Aufbereitung faerbt Pixel, sie
        # verschiebt keine - welche Kante gefunden wird, aendert sich, wo sie
        # liegt, nicht (nachgewiesen in tests/test_enhance.py).
        contour_mm = contour_module.find_contour_mm(rectified, px_per_mm)

    options = ExportOptions(
        dpi=request.dpi,
        layout=request.layout,
        page_format=request.page_format,
        orientation=request.orientation,
        overlap_mm=request.overlap_mm,
        printer_margin_mm=request.printer_margin_mm,
        page_margin_mm=request.page_margin_mm,
        show_scalebar=request.overlays.scalebar,
        show_grid=request.overlays.grid,
        show_footer=request.overlays.footer,
        show_marks=request.overlays.marks,
        tile_overview=request.tile_overview,
        contour=request.contour,
        title=i18n.translate(
            "pdf.document_title", locale, width=f"{crop.width:.0f}", height=f"{crop.height:.0f}"
        ),
        locale=locale,
    )

    footer = build_footer_lines(
        _footer_meta(session, solved, crop, request, contour_mm, locale), locale
    )
    return build_pdf(rectified, crop.width, crop.height, options, footer, contour_mm)


def _footer_meta(
    session: Session,
    solved: SolveResult,
    crop: Extent,
    request: ExportRequest,
    contour_mm: np.ndarray | None,
    locale: str = config.DEFAULT_LOCALE,
) -> dict[str, object]:
    """Die Metadaten der Fusszeile - ein Ausdruck soll spaeter nachvollziehbar sein."""
    pose = solved.pose
    if pose.height_mm is None:
        camera = i18n.translate("pdf.footer.camera_unknown", locale)
    else:
        tilt = (
            ""
            if pose.tilt_deg is None
            else i18n.translate("pdf.footer.camera_tilt", locale, tilt_deg=f"{pose.tilt_deg:.0f}")
        )
        camera = i18n.translate(
            "pdf.footer.camera",
            locale,
            height_mm=f"{pose.height_mm:.0f}",
            tilt=tilt,
            source=pose.source,
        )

    object_text = i18n.translate(
        "pdf.footer.object", locale, width=f"{crop.width:.1f}", height=f"{crop.height:.1f}"
    )
    if contour_mm is not None and len(contour_mm) >= 2:
        width_mm, height_mm = contour_module.bounding_box_mm(contour_mm)
        object_text += i18n.translate(
            "pdf.footer.contour", locale, width=f"{width_mm:.1f}", height=f"{height_mm:.1f}"
        )

    # Der Modus IST der Schluessel - fuer jeden gibt es pdf.footer.mode_*.
    mode_key = solved.solution.mode
    return {
        "object_mm": object_text,
        "dpi": request.dpi,
        "scale": i18n.translate(
            "pdf.footer.scale_source", locale, mm_per_px=f"{solved.solution.mm_per_px:.4f}"
        ),
        "mode": i18n.translate(f"pdf.footer.mode_{mode_key}", locale),
        "marker_ids": ",".join(str(f.marker_id) for f in solved.solution.markers),
        "marker_mm": f"{solved.marker_mm:.1f}",
        "rms": f"{solved.solution.rms_px:.2f} px / {solved.solution.rms_mm:.3f} mm",
        "camera": camera,
        "thickness": f"{solved.thickness_mm:.1f} mm (k={solved.correction_factor:.5f})",
        "extrapolation": f"{extrapolation_fraction(crop, solved.solution.hull_mm) * 100:.0f} %",
        "source": session.filename,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def _preview_payload(session: Session, kind: str, result: SolveResult) -> dict[str, object]:
    """Die Angaben zu einer Vorschau: wo sie liegt und wie sie in mm zu lesen ist.

    Eine Stelle fuer beide Wege - /api/solve und /api/adjust liefern dieselbe Form,
    sodass die Oberflaeche nach dem Regeln nichts anderes auszuwerten hat als nach
    dem Entzerren.
    """
    return {
        "url": f"/api/preview/{session.session_id}/{kind}?t={_cache_buster()}",
        "extent_mm": result.extent.as_dict(),
        "px_per_mm": round(result.preview_px_per_mm, 5),
    }


def _cache_buster() -> int:
    """Ein bei jedem Aufruf neuer Wert fuer die Vorschau-URL.

    Millisekunden, nicht Sekunden: die Vorschau wird unter demselben Dateinamen
    ueberschrieben, und der Regler tut das mehrmals je Sekunde. Mit sekundengenauem
    Stempel bekaeme der Browser zweimal dieselbe URL - und zeigte das alte Bild.
    """
    return time.time_ns() // 1_000_000


def solve_response(
    session: Session, result: SolveResult, locale: str = config.DEFAULT_LOCALE
) -> dict[str, object]:
    """SolveResult in die JSON-Form bringen, die das Frontend erwartet."""
    solution = result.solution
    crop = result.crop
    pose = result.pose

    return {
        "session_id": session.session_id,
        "mode_used": solution.mode,
        "markers": [
            {
                "id": fit.marker_id,
                "corners_px": fit.corners_px.tolist(),
                "side_mm_measured": round(fit.side_mm_measured, 3),
                "residual_px": round(fit.residual_px, 3),
                "rotation_deg": round(fit.rotation_deg, 2),
            }
            for fit in solution.markers
        ],
        "rms_px": round(solution.rms_px, 3),
        "rms_mm": round(solution.rms_mm, 4),
        "mm_per_px": round(solution.mm_per_px, 5),
        "camera": {
            "source": pose.source,
            "focal_px": None if pose.focal_px is None else round(pose.focal_px, 1),
            "height_mm": None if pose.height_mm is None else round(pose.height_mm, 1),
            "nadir_mm": None if pose.nadir_mm is None else [round(v, 1) for v in pose.nadir_mm],
            "tilt_deg": None if pose.tilt_deg is None else round(pose.tilt_deg, 1),
        },
        "thickness_mm": result.thickness_mm,
        "scale_correction_k": round(result.correction_factor, 6),
        "hull_mm": solution.hull_mm.round(3).tolist(),
        "extent_mm": result.extent.as_dict(),
        "default_crop_mm": crop.as_dict(),
        "extrapolation_default": round(
            extrapolation_fraction(crop, solution.hull_mm), 4
        ),
        "preview": {
            **_preview_payload(session, "rectified", result),
            "detected_url": f"/api/preview/{session.session_id}/detected?t={_cache_buster()}",
        },
        "limits": {
            "dpi_choices": list(config.DPI_CHOICES),
            "max_output_mpx": config.MAX_OUTPUT_MPX,
            "extrapolation_warn": config.EXTRAPOLATION_WARN_FRAC,
        },
        "elapsed_s": round(result.elapsed_s, 2),
        "warnings": result.notices.as_dicts(locale),
    }
