"""Ein Raster als Bilddatei - und zwar mit der Auflösung darin.

**Warum das eine eigene Datei ist.** Die Vorschau schreibt `cv2.imwrite`
(app/session.py), und das genügt dort: ein Vorschaubild wird angesehen, nicht
gemessen. Was der Benutzer als JPEG oder PNG herunterlädt, ist etwas anderes -
es ist die Schablone. Ein PDF trägt seine Millimeter selbst, ein Bild nur Pixel;
ohne Auflösungsangabe nimmt das nächste Programm seine eigene Vorgabe an, und aus
einer maßhaltigen Schablone wird stillschweigend eine beliebig große.

OpenCV kann diese Angabe nicht schreiben - weder JFIF-Dichte noch `pHYs` stehen
in seiner Schnittstelle. PIL kann es, und PIL liegt ohnehin im Bündel
(`app/vision/detect.py` dreht damit das EXIF). Also PIL.

Das Gegenstück im Browser und in der App ist `web/vision/density.js`. Dort wird
gestempelt statt kodiert: eine Leinwand und `Bitmap.compress` schreiben die
Angabe nicht, also trägt sie ein eigener Schritt nach. Zwei Wege, dieselbe
Zusage - und beide werden nachgemessen (`tests/test_encode.py`,
`web/vision/density.test.mjs`).
"""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image

from app import config
from app.notices import AppError

#: Was diese Datei kodieren kann. Dieselben zwei Werte kennt ExportImageRequest.
FORMATS = ("jpeg", "png")


def encode_image(image_bgr: np.ndarray, image_format: str, dpi: int) -> bytes:
    """Ein BGR-Raster als JPEG- oder PNG-Bytes, mit `dpi` in der Datei.

    `dpi` ist die Auflösung, mit der entzerrt wurde - nicht eine Angabe über die
    Datei, sondern über den MASSSTAB: ein Pixel ist 25,4/dpi Millimeter.
    """
    if image_format not in FORMATS:
        raise AppError("bad_image_format", "image_format", format=image_format)

    picture = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
    buffer = io.BytesIO()
    if image_format == "jpeg":
        # subsampling=0: kein Unterabtasten der Farbkanäle. Bei einer Schablone
        # sind die dünnen Linien das Produkt, und 4:2:0 zieht genau die breit.
        picture.save(
            buffer,
            "JPEG",
            quality=config.JPEG_QUALITY,
            subsampling=0,
            dpi=(dpi, dpi),
        )
    else:
        picture.save(buffer, "PNG", dpi=(dpi, dpi))
    return buffer.getvalue()


def media_type(image_format: str) -> str:
    """Der MIME-Typ zum Format - die eine Stelle, die diese Zuordnung kennt."""
    return "image/jpeg" if image_format == "jpeg" else "image/png"


def extension(image_format: str) -> str:
    """Die Dateiendung zum Format."""
    return ".jpg" if image_format == "jpeg" else ".png"
