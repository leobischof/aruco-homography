"""Ende-zu-Ende durch die HTTP-Schicht: Upload, Entzerren, PDF."""

from __future__ import annotations

import cv2
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
import io

from app import config
from app.main import app
from app.schemas import CropMm, ExportRequest


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def uploaded(client, scene):
    ok, encoded = cv2.imencode(".jpg", scene.image, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    assert ok
    response = client.post(
        "/api/upload", files={"file": ("szene.jpg", encoded.tobytes(), "image/jpeg")}
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture(scope="module")
def solved(client, uploaded, scene):
    """Entzerrte Sitzung - der Zustand, den jeder Export voraussetzt.

    Einmal je Modul, weil die Entzerrung die teuerste Rechnung der Kette ist und
    jeder Export danach denselben Zustand vorfindet.
    """
    response = client.post(
        "/api/solve",
        json={"session_id": uploaded["session_id"], "marker_mm": scene.marker_mm, "mode": "sheet"},
    )
    assert response.status_code == 200, response.text
    return uploaded["session_id"]


def test_upload_liefert_sitzung_und_bildmasse(uploaded, scene):
    assert uploaded["width"] == scene.image_size[0]
    assert uploaded["height"] == scene.image_size[1]
    assert uploaded["defaults"]["marker_mm"] == config.MARKER_MM_NOMINAL


def test_solve_liefert_bericht_und_vorschau(client, uploaded, scene):
    response = client.post(
        "/api/solve",
        json={"session_id": uploaded["session_id"], "marker_mm": scene.marker_mm, "mode": "sheet"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert [m["id"] for m in payload["markers"]] == sorted(scene.centers_mm)
    assert payload["rms_px"] < 1.0
    assert payload["mode_used"] == "sheet"
    assert payload["default_crop_mm"]["x1"] > payload["default_crop_mm"]["x0"]

    preview = client.get(payload["preview"]["url"])
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/jpeg"


def test_export_liefert_pdf_mit_exakter_seitengroesse(client, solved):
    response = client.post(
        "/api/export",
        json={
            "session_id": solved,
            "crop_mm": {"x0": 0.0, "y0": 0.0, "x1": 200.0, "y1": 150.0},
            "dpi": 150,
            "layout": "single",
            "overlays": {"scalebar": True, "grid": True, "footer": True, "marks": True},
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["X-Pages"] == "1"

    expected_w = 200.0 + 2 * config.PAGE_MARGIN_MM_DEFAULT
    expected_h = 150.0 + 2 * config.PAGE_MARGIN_MM_DEFAULT + config.STRIP_H_MM
    assert response.headers["X-Page-Size-Mm"] == f"{expected_w:.3f}x{expected_h:.3f}"

    box = PdfReader(io.BytesIO(response.content)).pages[0].mediabox
    assert float(box.width) / config.PT_PER_MM == pytest.approx(expected_w, abs=0.01)


def test_export_ohne_solve_wird_abgelehnt(client, uploaded):
    fresh = client.post(
        "/api/upload", files={"file": ("leer.jpg", _tiny_jpeg(), "image/jpeg")}
    ).json()

    response = client.post(
        "/api/export",
        json={
            "session_id": fresh["session_id"],
            "crop_mm": {"x0": 0.0, "y0": 0.0, "x1": 100.0, "y1": 100.0},
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "not_solved"


def test_abgelaufene_sitzung_wird_erklaert(client):
    response = client.post("/api/solve", json={"session_id": "gibtsnicht", "marker_mm": 50.0})
    assert response.status_code == 422
    assert response.json()["code"] == "session_expired"


def test_markerblatt_kommt_als_pdf(client):
    response = client.get("/api/markersheet")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(PdfReader(io.BytesIO(response.content)).pages) == 1


def test_startseite_wird_ausgeliefert(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "ArUco-Homographie" in response.text


def _export_in(client, session_id: str, locale: str):
    """Einzelseiten-Export in einer bestimmten Sprache."""
    response = client.post(
        "/api/export",
        json={
            "session_id": session_id,
            "crop_mm": {"x0": 0.0, "y0": 0.0, "x1": 200.0, "y1": 150.0},
            "dpi": 150,
            "layout": "single",
            "locale": locale,
        },
    )
    assert response.status_code == 200, response.text
    return response


def _page_text(response) -> str:
    """Der Text der ersten Seite - die Aufdrucke sind echter Text, kein Bild."""
    return PdfReader(io.BytesIO(response.content)).pages[0].extract_text() or ""


def _tiny_jpeg() -> bytes:
    import numpy as np

    ok, encoded = cv2.imencode(".jpg", np.full((40, 40, 3), 255, np.uint8))
    assert ok
    return encoded.tobytes()
