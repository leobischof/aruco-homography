"""Orchestrierung: verkettet Erkennung, Ausgleich, Pose, Korrektur, Entzerrung, PDF.

Die Routen in main.py bleiben dadurch reines Transportgeschaeft, und der komplette
Rechenweg ist ohne HTTP testbar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from app import config, i18n
from app.notices import AppError, NoticeList
from app.pdf.build import BuildResult, ExportOptions, build_footer_lines, build_pdf
from app.schemas import ExportRequest, SolveRequest
from app.session import Session
from app.vision import contour as contour_module
from app.vision import rectify as rectify_module
from app.vision.camera import CameraPose, resolve_pose
from app.vision.detect import detect_markers, draw_detection
from app.vision.extent import Extent, default_crop, extrapolation_fraction, plane_extent
from app.vision.solve import Solution, solve
from app.vision.thickness import effective_homography


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


def run_export(session: Session, request: ExportRequest) -> BuildResult:
    """Vom gewaehlten Zuschnitt zum druckfertigen PDF."""
    solved = session.state.get("solve")
    if not isinstance(solved, SolveResult):
        raise AppError("not_solved", "session_id")

    # Die Sprache des Ausdrucks kommt aus der Anfrage. getattr, weil ExportRequest das
    # Feld erst bekommt, wenn app/schemas.py nachzieht - bis dahin gilt die Vorgabe.
    locale = i18n.normalise(getattr(request, "locale", config.DEFAULT_LOCALE))

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

    contour_mm = None
    if request.contour:
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

    mode_key = "sheet" if solved.solution.mode == "sheet" else "free"
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
            "url": f"/api/preview/{session.session_id}/rectified?t={int(time.time())}",
            "detected_url": f"/api/preview/{session.session_id}/detected?t={int(time.time())}",
            "extent_mm": result.extent.as_dict(),
            "px_per_mm": round(result.preview_px_per_mm, 5),
        },
        "limits": {
            "dpi_choices": list(config.DPI_CHOICES),
            "max_output_mpx": config.MAX_OUTPUT_MPX,
            "extrapolation_warn": config.EXTRAPOLATION_WARN_FRAC,
        },
        "elapsed_s": round(result.elapsed_s, 2),
        "warnings": result.notices.as_dicts(locale),
    }
