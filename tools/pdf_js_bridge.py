"""pdf_js_bridge.py - die Python-Seite des Pruefstands fuer den JavaScript-PDF-Bau.

`ARUCO_PDF=js` schaltet `app/pdf/build.py` hierher um: Bild und Geometrie gehen an
Node, die PDF-Bytes kommen zurueck, und die vorhandenen 33 Pruefungen messen das
Ergebnis mit demselben Massstab wie beim ReportLab-Bau.

**Das ist ein Pruefstand, kein Auslieferungsweg.** Im Betrieb ruft niemand Node aus
Python heraus auf - dort baut die Oberflaeche das PDF selbst (siehe
docs/cpp-migration/README.md). Der Umweg existiert, damit der neue Bau gegen genau
die Zusicherungen gemessen werden kann, die der alte schon erfuellt.

Das Bild geht als JPEG hinueber, und zwar als DASSELBE JPEG, das ReportLab
einbetten wuerde (`app/pdf/build._as_reader`): gleiche Farbumwandlung, gleiche
Qualitaet. Sonst verglichen die beiden Ausdrucke am Ende zwei verschiedene Bilder,
und ein Unterschied waere nicht mehr dem PDF-Bau zuzuordnen.
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app import config

REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_JS = REPO_ROOT / "tools" / "pdf_js_bridge.mjs"


def _node() -> str:
    """Der Pfad zu node - mit einer Fehlermeldung, die sagt, was zu tun ist."""
    found = shutil.which("node")
    if found is None:
        raise RuntimeError(
            "ARUCO_PDF=js verlangt Node auf dem PATH (getestet mit v22.19.0). "
            "Ausserdem muss 'npm install' gelaufen sein - pdf-lib liegt in node_modules/."
        )
    return found


def _as_jpeg(image_bgr: np.ndarray) -> bytes:
    """BGR-Feld als JPEG - Zeile fuer Zeile wie app/pdf/build._as_reader."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    buffer = io.BytesIO()
    Image.fromarray(rgb).save(buffer, format="JPEG", quality=config.JPEG_QUALITY)
    return buffer.getvalue()


# Die Optionen heissen auf beiden Seiten dasselbe, nur anders geschrieben. Die
# Zuordnung steht EINMAL hier; ein zweiter Ort waere die Sorte Duplikat, die genau
# dann still veraltet, wenn eine Option dazukommt.
_OPTION_NAMES = {
    "dpi": "dpi",
    "layout": "layout",
    "page_format": "pageFormat",
    "orientation": "orientation",
    "overlap_mm": "overlapMm",
    "printer_margin_mm": "printerMarginMm",
    "page_margin_mm": "pageMarginMm",
    "show_scalebar": "showScalebar",
    "show_grid": "showGrid",
    "show_footer": "showFooter",
    "show_marks": "showMarks",
    "tile_overview": "tileOverview",
    "contour": "contour",
    "title": "title",
    "locale": "locale",
}


def _options_payload(options) -> dict:
    return {
        js_name: getattr(options, py_name) for py_name, js_name in _OPTION_NAMES.items()
    }


def _run_node(request: dict, workspace: Path) -> dict:
    """Auftrag schreiben, Node laufen lassen, die Antwortzeile zurueckgeben."""
    request_path = workspace / "request.json"
    request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")

    completed = subprocess.run(
        [_node(), str(BRIDGE_JS), str(request_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Der JavaScript-PDF-Bau ist abgebrochen:\n{completed.stderr.strip()}"
        )
    return json.loads(completed.stdout.strip().splitlines()[-1])


def build_markersheet_via_node(
    marker_mm: float, spacing_mm: tuple[float, float], locale: str
) -> bytes:
    """Das Markerblatt aus web/pdf/markersheet.js.

    Die Modulbits erzeugt dabei opencv.js unter Node - nicht dieses Python. Sonst
    prüfte tests/test_markersheet.py am Ende cv2 gegen cv2, und die Frage, ob
    JavaScript dieselben Marker zeichnet, bliebe offen.
    """
    with tempfile.TemporaryDirectory(prefix="aruco-pdfjs-") as folder:
        workspace = Path(folder)
        out_path = workspace / "markersheet.pdf"
        _run_node(
            {
                "kind": "markersheet",
                "out": str(out_path),
                "marker_mm": float(marker_mm),
                "spacing_mm": [float(spacing_mm[0]), float(spacing_mm[1])],
                "locale": locale,
            },
            workspace,
        )
        return out_path.read_bytes()


def build_pdf_via_node(
    rectified_bgr: np.ndarray,
    crop_w_mm: float,
    crop_h_mm: float,
    options,
    footer_lines: list[str],
    contour_mm: np.ndarray | None = None,
) -> dict:
    """Ruft den JavaScript-Bau auf und gibt PDF-Bytes samt Geometrie zurueck.

    Die Geometrie kommt bewusst aus dem JS-Ergebnis und nicht aus einer zweiten
    Rechnung auf dieser Seite: geprueft werden soll, was JavaScript rechnet.
    """
    with tempfile.TemporaryDirectory(prefix="aruco-pdfjs-") as folder:
        workspace = Path(folder)
        jpeg_path = workspace / "image.jpg"
        out_path = workspace / "out.pdf"

        jpeg_path.write_bytes(_as_jpeg(rectified_bgr))
        answer = _run_node(
            {
                "kind": "export",
                "jpeg": str(jpeg_path),
                "out": str(out_path),
                "crop_w_mm": float(crop_w_mm),
                "crop_h_mm": float(crop_h_mm),
                "options": _options_payload(options),
                "footer_lines": list(footer_lines),
                "contour_mm": (
                    None if contour_mm is None else np.asarray(contour_mm).tolist()
                ),
            },
            workspace,
        )
        answer["data"] = out_path.read_bytes()
        return answer
