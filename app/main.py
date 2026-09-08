"""FastAPI-Anwendung: Routen, Fehlerabbildung, Startbanner.

Reines Transportgeschaeft - gerechnet wird in app.pipeline und app.vision, und
wie sich die Oberflaeche zeigt (Fenster, Browser, gar nicht) steht in app.window.
"""

from __future__ import annotations

import io
import socket
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app import config, i18n, window
from app.notices import AppError
from app.pdf.markersheet import build_markersheet
from app.pipeline import (
    run_adjust,
    run_export,
    run_export_image,
    run_solve,
    solve_response,
)
from app.schemas import AdjustRequest, ExportImageRequest, ExportRequest, SolveRequest
from app.session import store
from app.notices import NoticeList
from app.vision import backend, encode
from app.vision.detect import detect_markers, load_photo
from app.vision.solve import solve as solve_plane

if TYPE_CHECKING:  # nur fuer die Typangabe - uvicorn wird erst beim Start geladen
    from uvicorn import Server

app = FastAPI(title=config.APP_NAME, docs_url="/api/docs", redoc_url=None)


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


@app.get("/api/locales")
async def locales_endpoint() -> dict[str, object]:
    """Die waehlbaren Sprachen: Code und Anzeigename, aus config.SUPPORTED_LOCALES.

    Ohne diese Route fuehrte der Browser eine zweite Liste neben der in config -
    genau die zweite Definition, die AGENTS.md (Invariante 4) verbietet. So ist
    eine neue Sprache eine Katalogdatei plus ein Eintrag in config, sonst nichts.
    """

    def label(code: str) -> str:
        # Der Name kommt aus dem Katalog DIESER Sprache: "Deutsch" heisst auch in
        # der englischen Oberflaeche "Deutsch". Fehlt er, tritt der Code ein -
        # eine Sprache ohne Beschriftung soll waehlbar bleiben, nicht ausfallen.
        key = f"ui.language.{code}"
        text = i18n.translate(key, code)
        return code.upper() if text == key else text

    return {
        "default": config.DEFAULT_LOCALE,
        "locales": [{"code": code, "label": label(code)} for code in config.SUPPORTED_LOCALES],
    }


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


@app.post("/api/detect")
async def detect_endpoint(http_request: Request) -> dict[str, object]:
    """Marker in EINEM Bild finden - ohne Sitzung, ohne Zustand. Fuer das Live-Bild.

    Der Sucher schickt zehnmal in der Sekunde ein Einzelbild und will nur wissen,
    wo die Marker liegen. Ueber /api/upload und /api/solve ginge das auch, aber
    jeder dieser Aufrufe legt eine Sitzung an, behaelt das Foto und rechnet eine
    Entzerrung - dreissigmal in drei Sekunden waere das ein Speicherleck mit
    Ansage. Diese Route haelt nichts fest.

    Der Koerper sind die Bytes eines Bildes (JPEG), nicht ein Formular: ein
    Einzelbild hat keinen Dateinamen und keinen zweiten Teil. Die Obergrenze ist
    dieselbe wie beim Upload - grosszuegig fuer ein Einzelbild, aber die Grenze
    soll hier nicht die zweite Zahl sein, die jemand pflegen muss.
    """
    data = await http_request.body()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > config.MAX_UPLOAD_MB:
        raise AppError(
            "upload_too_large", "file", size_mb=f"{size_mb:.0f}", limit_mb=config.MAX_UPLOAD_MB
        )

    try:
        photo = load_photo(data)
    except Exception as error:  # Pillow wirft je nach Format sehr Verschiedenes.
        raise AppError("unreadable_image", "file", reason=str(error)) from error

    markers = detect_markers(photo.bgr)
    return {
        "width": photo.width,
        "height": photo.height,
        "markers": [
            {"id": marker.marker_id, "corners": marker.corners_px.tolist()}
            for marker in markers
        ],
    }


@app.post("/api/measure")
async def measure_endpoint(
    http_request: Request,
    marker_mm: float = config.MARKER_MM_NOMINAL,
    mode: str = "sheet",
    spacing_x_mm: float = config.SHEET_SPACING_MM[0],
    spacing_y_mm: float = config.SHEET_SPACING_MM[1],
) -> dict[str, object]:
    """Ein Einzelbild bis zur Homographie rechnen - fuer das messende Live-Bild.

    Der Unterschied zu /api/detect ist die zweite Haelfte: dort endet es bei den
    Ecken, hier wird daraus die Ebene. Der Unterschied zu /api/solve ist alles
    andere - keine Sitzung, kein entzerrtes Bild, keine Vorschau. Was
    zurueckkommt, reicht genau fuer ein Overlay: die Abbildung Ebene -> Bild, der
    Massstab dort, wo die Marker liegen, und der Restfehler.

    Die Einstellungen stehen in der Abfrage und nicht im Koerper: der Koerper ist
    das Bild. Ein Formular mit einem Bildteil und vier Zahlenteilen waere je
    Einzelbild dieselbe Verpackung fuer dieselben vier Zahlen.

    `no_markers` ist hier KEIN Fehlerfall - im Sucher ist das der Normalzustand,
    solange die Kamera noch gesucht wird. Die Antwort sagt dann schlicht, dass es
    keine Ebene gibt (`plane: null`), und der Sucher zeichnet nichts.

    **`warnings` gehoert zur Antwort und nicht zum Beiwerk.** Bis 0.1.6-alpha
    bekam solve_plane hier eine WEGGEWORFENE NoticeList, und der Sucher zeigte
    jede Loesung als Messwert - auch eine mit 64 px Restfehler bei zwei fast
    deckungsgleichen Markern. Auf dem Telefon sah man dann ein Raster, das quer
    ueber das Bild schoss, neben einer Zahl mit vier Nachkommastellen. Die
    Schwellen dafuer gibt es laengst (RMS_WARN_PX, COLLINEARITY_WARN); es hat
    nur niemand zugehoert. Was der Sucher daraus macht, entscheidet er selbst -
    diese Route liefert die Warnungen in derselben Form wie /api/solve.
    """
    data = await http_request.body()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > config.MAX_UPLOAD_MB:
        raise AppError(
            "upload_too_large", "file", size_mb=f"{size_mb:.0f}", limit_mb=config.MAX_UPLOAD_MB
        )

    try:
        photo = load_photo(data)
    except Exception as error:  # Pillow wirft je nach Format sehr Verschiedenes.
        raise AppError("unreadable_image", "file", reason=str(error)) from error

    markers = detect_markers(photo.bgr)
    answer: dict[str, object] = {
        "width": photo.width,
        "height": photo.height,
        "grid_mm": config.GRID_STEP_MM,
        "markers": [
            {"id": marker.marker_id, "corners": marker.corners_px.tolist()}
            for marker in markers
        ],
        "plane": None,
        "warnings": [],
    }
    if not markers:
        return answer

    notices = NoticeList()
    try:
        solution = solve_plane(
            markers, marker_mm, mode, notices, (spacing_x_mm, spacing_y_mm)
        )
    except AppError:
        # Zu wenige Marker fuer diesen Modus, ein unbekannter Modus, eine
        # entartete Lage: im Sucher ist das eine Zwischenstufe und kein Abbruch.
        return answer

    answer["warnings"] = notices.as_dicts(request_locale(http_request))
    answer["plane"] = {
        "homography": [float(value) for value in solution.homography.reshape(9)],
        "hull_mm": solution.hull_mm.tolist(),
        "mm_per_px": solution.mm_per_px,
        "rms_px": solution.rms_px,
        "mode_used": solution.mode,
    }
    return answer


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


@app.post("/api/export-image")
async def export_image_endpoint(request: ExportImageRequest) -> Response:
    """Denselben Zuschnitt als JPEG oder PNG."""
    session = store.get(request.session_id)
    result = run_export_image(session, request)

    # Der Name kommt vom Aufrufer, die Endung vom Format. Beides zu uebernehmen
    # hiesse, ein PNG "schablone.jpg" nennen zu koennen.
    stem = Path(request.filename).stem or "schablone"
    filename = f"{stem}{encode.extension(request.image_format)}"
    return Response(
        content=result.data,
        media_type=encode.media_type(request.image_format),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Image-Pixels": f"{result.width}×{result.height}",
            "X-Mm-Per-Px": f"{config.MM_PER_INCH / request.dpi:.6f}",
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


app.mount("/", StaticFiles(directory=config.STATIC_DIR, html=True), name="static")


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


def choose_port(preferred: int = config.PORT) -> int:
    """Der bevorzugte Port, wenn er frei ist - sonst ein beliebiger freier.

    Ein fester Port ist genau so lange richtig, wie ihn niemand sonst belegt; auf
    einem Werkstattrechner ist das eine Wette. Ein Doppelklick, der mit "address
    already in use" abbricht, sieht fuer den Bediener aus wie ein kaputtes Programm.
    Deshalb wird zuerst der stabile Port versucht und erst dann ausgewichen.

    Gebunden wird auf dieselbe Adresse wie spaeter von uvicorn, sonst wuerde der
    Test die falsche Frage stellen. SO_REUSEADDR wird bewusst NICHT gesetzt: unter
    Windows erlaubt das, sich auf einen bereits belegten Port zu setzen - die
    Pruefung wuerde dann immer "frei" sagen.
    """
    for candidate in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((config.HOST, candidate))
            except OSError:
                continue
            return int(probe.getsockname()[1])
    raise OSError("Kein freier Port gefunden.")


def preferred_port(args: list[str]) -> int:
    """Der gewuenschte Port aus der Kommandozeile, sonst der aus config.

    `--port 8123` und `--port=8123` sind beide erlaubt. Gebraucht wird das dort, wo
    der Vorgabeport schon vergeben ist oder wo eine zweite Kopie danebenlaufen soll -
    etwa, wenn eine frisch installierte Fassung neben dem Entwicklungsserver geprueft
    wird. Ausgewichen wird danach wie immer: choose_port nimmt diesen Port nur, wenn
    er frei ist.

    Ein unbrauchbarer Wert beendet das Programm NICHT. Ein Doppelklick, der wegen
    eines Komfortarguments gar nicht erst startet, ist schlimmer als einer, der auf
    dem Vorgabeport landet - gesagt wird es trotzdem.
    """
    for index, argument in enumerate(args):
        if argument.startswith("--port="):
            raw = argument.split("=", 1)[1]
        elif argument == "--port" and index + 1 < len(args):
            raw = args[index + 1]
        else:
            continue

        port = int(raw) if raw.isdigit() else -1
        if 1 <= port <= 65535:
            return port
        print(f"  (--port {raw} ist keine gueltige Portnummer - es gilt {config.PORT})")
        break

    return config.PORT


def build_server(port: int) -> Server:
    """Der Server, gebaut aber noch nicht gestartet.

    Gebaut statt gleich gestartet, weil das Fenster ihn auf einem Nebenfaden
    braucht und danach wieder anhalten koennen muss (`should_exit`). `uvicorn.run`
    tut nichts anderes als diese zwei Zeilen und dann `run()`.
    """
    import uvicorn

    return uvicorn.Server(uvicorn.Config(app, host=config.HOST, port=port, log_level="info"))


def serve_in_window(url: str, port: int) -> int:
    """Server auf einem Nebenfaden, Fenster auf dem Hauptfaden.

    Beide wollen den Hauptfaden: uvicorn laeuft dort normalerweise, pywebview
    besteht darauf. Also bekommt ihn das Fenster - es ist das, was der Bediener
    sieht - und der Server einen Daemon-Faden daneben. Daemon, damit ein
    haengender Server das geschlossene Fenster nicht ueberlebt.

    Kann dieser Rechner kein Fenster zeigen, laeuft der Server trotzdem weiter und
    der Browser tritt ein. Eine fehlende Anzeige-Maschine darf den Server nicht
    aufhalten - sonst ist ein Werkstattrechner ohne WebView2-Laufzeit gar nicht
    mehr zu gebrauchen, auch nicht vom Handy aus.
    """
    server = build_server(port)
    thread = threading.Thread(target=server.run, name="uvicorn", daemon=True)
    thread.start()

    # Strg+C muss auch hier beenden. uvicorn faengt es nur ab, wenn es auf dem
    # Hauptfaden laeuft; hier laeuft es daneben, also kommt es bei uns an.
    try:
        if not window.show(url):
            window.open_browser_when_ready(url, port)
            # Gewartet wird in Scheiben und nicht in einem Zug, damit der
            # Hauptfaden zwischendurch ansprechbar bleibt.
            while thread.is_alive():
                thread.join(0.5)
    except KeyboardInterrupt:
        pass

    # Das Fenster ist zu (oder es kam Strg+C): der Server darf gehen. Ohne diese
    # Bitte liefe er weiter, bis der Prozess ihn beim Beenden abraeumt.
    server.should_exit = True
    thread.join(config.SERVER_STOP_WAIT_S)
    return 0


# Welcher Kern misst, gehoert ins Banner und nicht in eine Protokolldatei: es ist
# die einzige Stelle, an der jemand OHNE Werkzeug sieht, was gerade rechnet. Die
# .exe nimmt C++, der Quellbaum die Python-Referenz - und wer das eine erwartet
# und das andere liest, hat den Fehler gefunden, bevor er eine Messung erklaeren
# muss. (Konsolenausgabe, kein Oberflaechentext: Invariante 7 gilt hier nicht.)
_CORE_LABEL = {
    backend.PYTHON: "Python (app/vision/, die Referenz)",
    backend.CPP: "C++ (core/)",
}


def print_banner(local_url: str, lan_url: str) -> None:
    """URL plus ASCII-QR-Code, damit man das Handy nur draufhalten muss."""
    print()
    print(f"  {config.APP_NAME} {config.APP_VERSION} laeuft")
    print(f"  Lokal:       {local_url}")
    print(f"  Im Netzwerk: {lan_url}")
    # flush, weil stdout blockweise puffert, sobald es KEINE Konsole ist -
    # in eine Datei umgeleitet stuende das Banner sonst erst am Ende darin,
    # und ausgerechnet die Zeile darueber soll man SOFORT lesen koennen.
    print(f"  Rechenkern:  {_CORE_LABEL[backend.ACTIVE]}", flush=True)
    print()
    try:
        import qrcode

        code = qrcode.QRCode(border=1)
        code.add_data(lan_url)
        code.make(fit=True)
        buffer = io.StringIO()
        code.print_ascii(out=buffer)
        print(buffer.getvalue())
    except ImportError:  # pragma: no cover - QR ist Komfort, kein Muss
        print("  (qrcode nicht installiert - URL bitte von Hand eintippen)")
    except UnicodeEncodeError:  # pragma: no cover - haengt an der Konsole, nicht am Code
        # Der QR-Code besteht aus Blockzeichen. Schreibt Python nicht in eine
        # Windows-Konsole, sondern in eine Pipe oder Datei, nimmt es die
        # Codepage des Systems (cp1252) - und print() bricht ab. In der .exe
        # hiess das: der Server startete gar nicht erst, wegen einer Verzierung.
        print("  (Konsole kann den QR-Code nicht darstellen - URL bitte eintippen)")


def main(argv: list[str] | None = None) -> int:
    """Server starten und die Oberflaeche zeigen.

    Vorgabe ist das eigene Fenster. `--browser` nimmt stattdessen den Browser des
    Systems, `--no-browser` oeffnet gar nichts und laesst nur den Server laufen;
    `--port N` verschiebt den Wunschport. Welcher Schalter was bedeutet, steht in
    `app.window.choose_ui_mode`.

    Die Oberflaeche geht HIER auf und nicht im Aufrufer: erst hier steht fest,
    welcher Port es geworden ist. Ein Aufrufer, der vorher eine URL baut, trifft
    die falsche, sobald ausgewichen werden musste.
    """
    args = sys.argv[1:] if argv is None else argv

    port = choose_port(preferred_port(args))
    local_url = f"http://127.0.0.1:{port}"
    print_banner(local_url, f"http://{lan_address()}:{port}")

    mode = window.choose_ui_mode(args)
    if mode == window.WINDOW:
        return serve_in_window(local_url, port)

    if mode == window.BROWSER:
        window.open_browser_when_ready(local_url, port)

    build_server(port).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
