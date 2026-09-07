"""Die Bildaufbereitung durch die HTTP-Schicht: Live-Vorschau und Export.

Zwei Dinge werden hier nachgewiesen, und das zweite ist das wichtigere:

1. Die Regler kommen ueber die Leitung an und wirken auf die Bildpunkte.
2. Sie wirken NUR auf die Bildpunkte. Ein Export mit Aufbereitung hat dieselbe
   Seitengroesse und dasselbe Bildrechteck wie einer ohne - Millimeter sind das
   Produkt (AGENTS.md), und ein Schwarzweissregler darf daran nichts aendern.

Dass die Aufbereitung auch im Bild selbst keine Kante verschiebt, ist in
tests/test_enhance.py subpixelgenau nachgemessen; hier geht es um den Weg dorthin.
"""

from __future__ import annotations

from dataclasses import fields

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.schemas import AdjustOptions
from app.vision import enhance


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def solved(client, scene):
    """Eine hochgeladene und entzerrte Sitzung - der Zustand, den /api/adjust verlangt."""
    ok, encoded = cv2.imencode(".jpg", scene.image, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    assert ok
    uploaded = client.post(
        "/api/upload", files={"file": ("szene.jpg", encoded.tobytes(), "image/jpeg")}
    )
    assert uploaded.status_code == 200, uploaded.text
    session_id = uploaded.json()["session_id"]

    response = client.post(
        "/api/solve",
        json={"session_id": session_id, "marker_mm": scene.marker_mm, "mode": "sheet"},
    )
    assert response.status_code == 200, response.text
    return session_id


def adjust(client, session_id: str, **options):
    return client.post("/api/adjust", json={"session_id": session_id, "adjust": options})


def preview_image(client, url: str) -> np.ndarray:
    """Die Vorschau hinter einer URL wirklich holen und dekodieren."""
    response = client.get(url)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "image/jpeg"
    return cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)


def test_die_drahtform_spiegelt_die_dataclass_feld_fuer_feld():
    """Das Pydantic-Modell ist ein Spiegel, keine zweite Definition.

    SSOT sind die Regler in app/vision/enhance.py. Laufen die beiden Fassungen
    auseinander - ein Feld zu viel, ein anderer Vorgabewert -, wuerde entweder ein
    Regler stillschweigend nicht mehr ankommen oder to_enhance() mitten im Export
    mit TypeError abbrechen. Beides faellt hier auf, bevor es jemand ausdruckt.
    """
    dataclass_defaults = {field.name: field.default for field in fields(enhance.AdjustOptions)}
    wire_defaults = {name: info.default for name, info in AdjustOptions.model_fields.items()}

    assert wire_defaults == dataclass_defaults
    assert list(wire_defaults) == list(dataclass_defaults)


def test_adjust_ohne_entzerrung_wird_abgelehnt(client):
    """Ohne Homographie gibt es kein entzerrtes Bild, das man aufbereiten koennte."""
    fresh = client.post(
        "/api/upload", files={"file": ("leer.jpg", _tiny_jpeg(), "image/jpeg")}
    ).json()

    response = adjust(client, fresh["session_id"], grayscale=True)

    assert response.status_code == 422
    assert response.json()["code"] == "not_solved"


def test_neutrale_regler_liefern_die_unveraenderte_vorschau(client, solved):
    """Steht alles neutral, kommt die entzerrte Vorschau zurueck - keine Kopie."""
    response = adjust(client, solved)
    assert response.status_code == 200, response.text

    preview = response.json()["preview"]
    assert f"/api/preview/{solved}/rectified?" in preview["url"]
    assert preview["px_per_mm"] > 0.0
    assert preview["extent_mm"]["x1"] > preview["extent_mm"]["x0"]
    assert preview_image(client, preview["url"]).size > 0


def test_schwarzweiss_liefert_eine_eigene_aufbereitete_vorschau(client, solved):
    """Ein gesetzter Regler erzeugt die Vorschau "adjusted", nicht die rohe.

    Die Bildpunkte selbst KOENNEN sich an dieser Szene nicht unterscheiden: sie
    wird neutral gerendert (R = G = B ueberall), und die Graustufenwandlung bildet
    einen neutralen Wert exakt auf sich ab. Ein Byte-Vergleich wuerde hier also nur
    das erneute JPEG-Kodieren messen. Nachgewiesen wird deshalb, dass eine eigene,
    abrufbare Vorschau in unveraenderter Groesse entsteht - dass die Regler die
    Bildpunkte wirklich erreichen, zeigt der Negativ-Test darunter.
    """
    identity = preview_image(client, adjust(client, solved).json()["preview"]["url"])

    response = adjust(client, solved, grayscale=True)
    assert response.status_code == 200, response.text

    url = response.json()["preview"]["url"]
    assert f"/api/preview/{solved}/adjusted?" in url

    adjusted = preview_image(client, url)
    # Aufbereitung ist kosmetisch: dieselbe Rastergroesse, dieselbe Kanalzahl.
    assert adjusted.shape == identity.shape


def test_negativ_kehrt_die_bildpunkte_wirklich_um(client, solved):
    """Der Beweis, dass die Regler bis in die Bildpunkte durchschlagen."""
    identity = preview_image(client, adjust(client, solved).json()["preview"]["url"])
    inverted = preview_image(client, adjust(client, solved, invert=True).json()["preview"]["url"])

    assert float(inverted.mean()) == pytest.approx(255.0 - float(identity.mean()), abs=1.0)


def test_wert_ausserhalb_des_wertebereichs_wird_abgewiesen(client, solved):
    """Kontrast 5 gibt es nicht - der Bereich steht im Schema, nicht im Frontend."""
    response = adjust(client, solved, contrast=5.0)

    assert response.status_code == 422
    # "detail" statt "code": das ist die Validierung, kein fachlicher Abbruch.
    assert "detail" in response.json()


def test_unbekannte_farbbetonung_wird_abgewiesen(client, solved):
    response = adjust(client, solved, color_emphasis="puce", emphasis_strength=0.5)

    assert response.status_code == 422
    assert "detail" in response.json()


def test_jeder_farbton_aus_der_konfiguration_wird_angenommen(client, solved):
    """Die Auswahl wird aus config.ADJUST_EMPHASIS_HUES gebaut, nicht abgeschrieben.

    Deshalb kann ein dort ergaenzter Farbton nicht still an der Validierung
    scheitern - dieser Test faende es sofort.
    """
    for hue in ("none", *config.ADJUST_EMPHASIS_HUES):
        response = adjust(client, solved, color_emphasis=hue, emphasis_strength=0.5)
        assert response.status_code == 200, f"{hue}: {response.text}"


def test_aufbereitung_veraendert_die_seitengeometrie_nicht(client, solved):
    """Die Millimeter-Invariante: derselbe Zuschnitt, dieselbe Seite - Regler egal.

    Verglichen werden Seitengroesse, Bildrechteck und Seitenzahl. Zusaetzlich muss
    sich das PDF im Inhalt unterscheiden, sonst waere der Test auch dann gruen,
    wenn die Aufbereitung beim Export gar nicht ankaeme.
    """
    plain = _export(client, solved, {})
    fancy = _export(client, solved, {"grayscale": True, "contrast": 0.4, "threshold": 0.5})

    for header in ("X-Page-Size-Mm", "X-Image-Rect-Mm", "X-Pages"):
        assert fancy.headers[header] == plain.headers[header], header
    assert fancy.content != plain.content


def _export(client, session_id: str, adjust_options: dict[str, object]):
    """Ein Export mit Kontur - so laeuft die Kontursuche auf dem aufbereiteten Bild."""
    response = client.post(
        "/api/export",
        json={
            "session_id": session_id,
            "crop_mm": {"x0": 0.0, "y0": 0.0, "x1": 200.0, "y1": 150.0},
            "dpi": 150,
            "layout": "single",
            "contour": True,
            "adjust": adjust_options,
        },
    )
    assert response.status_code == 200, response.text
    return response


def _tiny_jpeg() -> bytes:
    ok, encoded = cv2.imencode(".jpg", np.full((40, 40, 3), 255, np.uint8))
    assert ok
    return encoded.tobytes()
