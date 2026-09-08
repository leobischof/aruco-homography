"""Der Zuschnitt als Bilddatei - und die Frage, ob das Mass mitkommt.

Ein PDF traegt seine Millimeter selbst. Ein Bild traegt Pixel, und was ein Pixel
in Millimetern ist, steht nur dann in der Datei, wenn es jemand hineinschreibt.
Genau das wird hier nachgelesen: nicht "es kam eine Datei heraus", sondern "ein
Leser holt dieselbe Zahl wieder heraus".
"""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image

from app import config
from app.notices import AppError
from app.pipeline import run_export_image, run_solve
from app.schemas import CropMm, ExportImageRequest, SolveRequest
from app.session import store
from app.vision.detect import Photo
from app.vision.encode import encode_image, extension, media_type


@pytest.fixture
def raster() -> np.ndarray:
    """Ein kleines BGR-Bild mit unterscheidbaren Kanaelen."""
    image = np.zeros((3, 5, 3), np.uint8)
    image[:, :, 0] = 10   # B
    image[:, :, 1] = 120  # G
    image[:, :, 2] = 230  # R
    return image


@pytest.mark.parametrize("image_format", ["jpeg", "png"])
def test_die_datei_traegt_die_aufloesung(raster, image_format):
    data = encode_image(raster, image_format, 300)
    picture = Image.open(io.BytesIO(data))

    assert picture.size == (5, 3)
    dots_x, dots_y = picture.info["dpi"]
    # PNG speichert Punkte je METER als ganze Zahl; 300 dpi sind 11811, und
    # zurueckgerechnet 299,9994. Das ist die Genauigkeit des Formats, kein Fehler.
    assert abs(float(dots_x) - 300.0) < 0.01
    assert abs(float(dots_y) - 300.0) < 0.01


def test_png_gibt_die_farben_unveraendert_zurueck(raster):
    """PNG ist verlustfrei - wenn hier etwas abweicht, sind B und R vertauscht."""
    picture = Image.open(io.BytesIO(encode_image(raster, "png", 300))).convert("RGB")
    assert picture.getpixel((0, 0)) == (230, 120, 10)


def test_jpeg_liegt_nah_genug_an_den_farben(raster):
    picture = Image.open(io.BytesIO(encode_image(raster, "jpeg", 300))).convert("RGB")
    assert np.allclose(picture.getpixel((0, 0)), (230, 120, 10), atol=4)


def test_unbekanntes_format_bricht_ab(raster):
    with pytest.raises(AppError) as error:
        encode_image(raster, "webp", 300)
    assert error.value.code == "bad_image_format"


def test_endung_und_mime_gehoeren_zusammen():
    assert (extension("jpeg"), media_type("jpeg")) == (".jpg", "image/jpeg")
    assert (extension("png"), media_type("png")) == (".png", "image/png")


def test_der_export_liefert_den_zuschnitt_in_der_richtigen_groesse(scene):
    """Vom Foto bis zur Datei: die Kantenlaengen muessen zum Zuschnitt passen."""
    photo = Photo(bgr=scene.image, focal35_mm=scene.focal35_mm, camera_model=None)
    session = store.create(photo, "probe.jpg")
    run_solve(session, SolveRequest(session_id=session.session_id, marker_mm=scene.marker_mm))

    dpi = 150
    crop = CropMm(x0=0.0, y0=0.0, x1=100.0, y1=50.0)
    result = run_export_image(
        session,
        ExportImageRequest(
            session_id=session.session_id, crop_mm=crop, dpi=dpi, image_format="png"
        ),
    )

    picture = Image.open(io.BytesIO(result.data))
    expected = round(100.0 * dpi / config.MM_PER_INCH), round(50.0 * dpi / config.MM_PER_INCH)
    assert picture.size == expected
    # Die gemeldete Groesse muss die der Datei sein - die Oberflaeche zeigt sie an.
    assert (result.width, result.height) == picture.size

    # Und die Probe aufs Ganze: Breite in Pixeln durch die Auflösung ergibt
    # wieder die Breite in Millimetern, die eingetippt wurde.
    dots_x, _ = picture.info["dpi"]
    assert abs(picture.size[0] / float(dots_x) * config.MM_PER_INCH - 100.0) < 0.5
