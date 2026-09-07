"""FastAPI-Anwendung: Routen, Fehlerabbildung, Startbanner.

Reines Transportgeschaeft - gerechnet wird in app.pipeline und app.vision.
"""

from __future__ import annotations

import io
import socket
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app import config, i18n
from app.notices import AppError
from app.pdf.markersheet import build_markersheet
from app.pipeline import run_adjust, run_export, run_solve, solve_response
from app.schemas import AdjustRequest, ExportRequest, SolveRequest
from app.session import store
from app.vision.detect import load_photo

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="ArUco-Homographie", docs_url="/api/docs", redoc_url=None)


def request_locale(request: Request) -> str:
    """Sprache dieser Anfrage. Der Browser schickt sie im Accept-Language-Kopf mit."""
    return i18n.negotiate(request.headers.get("accept-language"))


@app.exception_handler(AppError)
async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
    """Fachliche Fehler als 422 mit Code, Parametern, Klartext und betroffenem Feld."""
    locale = request_locale(request)
    return JSONResponse(
        status_code=422,
        content={
            "code": error.code,
            "params": i18n.plain_params(error.params, locale),
            "field": error.field_name,
            "message": error.message(locale),
        },
    )


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, object]:
    """Foto entgegennehmen, EXIF auswerten, Sitzung anlegen."""
    data = await file.read()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > config.MAX_UPLOAD_MB:
        raise AppError(
            "upload_too_large", "file", size_mb=f"{size_mb:.0f}", limit_mb=config.MAX_UPLOAD_MB
        )

    try:
        photo = load_photo(data)
    except Exception as error:  # Pillow wirft je nach Format sehr Verschiedenes.
        raise AppError("unreadable_image", "file", reason=str(error)) from error

    session = store.create(photo, file.filename or "foto.jpg")
    return {
        "session_id": session.session_id,
        "filename": session.filename,
        "width": photo.width,
        "height": photo.height,
        "exif": {
            "focal35_mm": photo.focal35_mm,
            "camera_model": photo.camera_model,
        },
        "defaults": {
            "marker_mm": config.MARKER_MM_NOMINAL,
            "spacing_x_mm": config.SHEET_SPACING_MM[0],
            "spacing_y_mm": config.SHEET_SPACING_MM[1],
            "dpi": config.DPI_DEFAULT,
            "dpi_choices": list(config.DPI_CHOICES),
            "overlap_mm": config.TILE_OVERLAP_MM_DEFAULT,
            "printer_margin_mm": config.PRINTER_MARGIN_MM_DEFAULT,
            "page_margin_mm": config.PAGE_MARGIN_MM_DEFAULT,
        },
    }


@app.post("/api/solve")
async def solve_endpoint(request: SolveRequest, http_request: Request) -> dict[str, object]:
    """Homographie bestimmen, Qualitaet bewerten, entzerrte Vorschau erzeugen."""
    session = store.get(request.session_id)
    return solve_response(
        session, run_solve(session, request), request_locale(http_request)
    )


@app.post("/api/adjust")
async def adjust_endpoint(request: AdjustRequest) -> dict[str, object]:
    """Regler auf die entzerrte Vorschau anwenden, ohne neu zu entzerren."""
    session = store.get(request.session_id)
    return run_adjust(session, request)


@app.post("/api/export")
async def export_endpoint(request: ExportRequest) -> Response:
    """Druckfertiges PDF erzeugen."""
    session = store.get(request.session_id)
    result = run_export(session, request)

    filename = request.filename if request.filename.lower().endswith(".pdf") else "schablone.pdf"
    return Response(
        content=result.data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Page-Size-Mm": f"{result.page_size_mm[0]:.3f}x{result.page_size_mm[1]:.3f}",
            "X-Image-Rect-Mm": ",".join(f"{value:.3f}" for value in result.image_rect_mm),
            "X-Pages": str(result.page_count),
        },
    )


@app.get("/api/markersheet")
async def markersheet_endpoint(
    http_request: Request,
    marker_mm: float = config.MARKER_MM_NOMINAL,
    spacing_x_mm: float = config.SHEET_SPACING_MM[0],
    spacing_y_mm: float = config.SHEET_SPACING_MM[1],
    locale: str | None = None,
) -> Response:
    """Das A4-Markerblatt zum Ausdrucken.

    Das Blatt wird ueber einen einfachen Link geholt, also kann die Oberflaeche ihre
    Sprache nicht als Kopfzeile mitgeben - dafuer gibt es ?locale=. Ohne die Angabe
    entscheidet Accept-Language.
    """
    if marker_mm <= 0.0 or spacing_x_mm <= 0.0 or spacing_y_mm <= 0.0:
        raise AppError("bad_marker_size", "marker_mm")
    if marker_mm + spacing_x_mm > config.SHEET_MM[0] or marker_mm + spacing_y_mm > config.SHEET_MM[1]:
        raise AppError(
            "sheet_too_small",
            "spacing_x_mm",
            marker_mm=f"{marker_mm:.0f}",
            spacing_x_mm=f"{spacing_x_mm:.0f}",
            spacing_y_mm=f"{spacing_y_mm:.0f}",
            sheet_w_mm=f"{config.SHEET_MM[0]:.0f}",
            sheet_h_mm=f"{config.SHEET_MM[1]:.0f}",
        )
    wanted = i18n.normalise(locale) if locale else request_locale(http_request)
    return Response(
        content=build_markersheet(marker_mm, (spacing_x_mm, spacing_y_mm), wanted),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="markerblatt_A4.pdf"'},
    )


@app.get("/api/preview/{session_id}/{kind}")
async def preview_endpoint(session_id: str, kind: str) -> Response:
    """Vorschau-JPEGs (original, detected, rectified, adjusted)."""
    if kind not in {"original", "detected", "rectified", "adjusted"}:
        raise AppError("bad_preview", kind=kind)

    session = store.get(session_id)
    path = session.preview_path(kind)
    if kind == "original" and not path.exists():
        session.write_preview("original", session.photo.bgr)
    if not path.exists():
        raise AppError("preview_missing")

    return FileResponse(path, media_type="image/jpeg")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


def lan_address() -> str:
    """Die IP, unter der das Handy im selben WLAN den Server erreicht."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))  # kein echter Verkehr, nur Routenwahl
        return str(probe.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def print_banner(url: str) -> None:
    """URL plus ASCII-QR-Code, damit man das Handy nur draufhalten muss."""
    print()
    print("  ArUco-Homographie laeuft")
    print(f"  Lokal:      http://127.0.0.1:{config.PORT}")
    print(f"  Im Netzwerk: {url}")
    print()
    try:
        import qrcode

        code = qrcode.QRCode(border=1)
        code.add_data(url)
        code.make(fit=True)
        buffer = io.StringIO()
        code.print_ascii(out=buffer)
        print(buffer.getvalue())
    except ImportError:  # pragma: no cover - QR ist Komfort, kein Muss
        print("  (qrcode nicht installiert - URL bitte von Hand eintippen)")


def main() -> int:
    import uvicorn

    url = f"http://{lan_address()}:{config.PORT}"
    print_banner(url)
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
