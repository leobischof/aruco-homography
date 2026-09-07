"""Bildaufbereitung: kosmetisch ja, geometrisch nein.

Die wichtigsten Tests dieser Datei sind die drei, die die Kante nachmessen. Alles
andere hier prueft, dass die Regler tun, was sie versprechen; jene pruefen, dass
sie dabei die Millimeter in Ruhe lassen. Ein Schaerferegler, der eine Kante um ein
halbes Pixel verrueckt, verrueckt sie auf dem Ausdruck mit - bei 300 dpi sind das
0,042 mm je Pixel, und ueber mehrere Stufen summiert sich das.

Gemessen wird an zwei Bildern, weil beide etwas anderes beweisen:

- Die HARTE Kante (ein Pixel hell, das naechste dunkel) zeigt jede Verschiebung
  um ganze Pixel und erlaubt zusaetzlich die schaerfste Aussage ueberhaupt: die
  Menge der dunklen Pixel muss hinterher pixelgenau dieselbe sein.
- Die WEICHE Kante kann eine Verschiebung um Bruchteile eines Pixels ueberhaupt
  erst darstellen - an einer harten Kante hat ein Zehntelpixel keinen Platz.

Der Schaetzer ist der klassische 50-%-Durchgang: die beiden Plateauwerte werden
an den Fensterraendern abgelesen, und zwischen den beiden Abtastungen, die den
Mittelwert einschliessen, wird linear interpoliert. Er ist unempfindlich gegen
jede Tonwertaenderung, die die Plateaus flach laesst - und genau das tut ein
Eingriff, der nur Werte aendert und keine Orte.
"""

from __future__ import annotations

from dataclasses import fields

import cv2
import numpy as np
import pytest

from app.vision.enhance import AdjustOptions, adjust

# Lage des Testrechtecks. Die Tonwerte 60 und 195 liegen symmetrisch um das
# Mittelgrau 127,5: so klemmt eine Unschaerfemaske oben und unten gleich weit und
# bleibt antisymmetrisch. Mit reinem 0/255 waere die Maske vollstaendig
# weggeklemmt worden - der Kantentest haette dann nichts geprueft.
RECT_X0, RECT_X1 = 60, 180
RECT_Y0, RECT_Y1 = 50, 190
LEVEL_DARK, LEVEL_BRIGHT = 60, 195
SOFT_SIGMA_PX = 2.0
PATCH_W = 40


def hard_rectangle() -> np.ndarray:
    """Dunkles Rechteck auf hellem Grund, harte Kante an bekannter Stelle."""
    image = np.full((240, 240, 3), LEVEL_BRIGHT, np.uint8)
    image[RECT_Y0:RECT_Y1, RECT_X0:RECT_X1] = LEVEL_DARK
    return image


def soft_rectangle(sigma_px: float = SOFT_SIGMA_PX) -> np.ndarray:
    """Dasselbe Rechteck weichgezeichnet - eine Kante mit Platz fuer Subpixel.

    Der Gauss ist symmetrisch, die Kante liegt danach weiterhin genau auf
    RECT_X0 - 0,5. Das prueft test_die_kantenmessung_trifft_die_bekannte_lage
    ausdruecklich nach, bevor irgendetwas damit gemessen wird.
    """
    return cv2.GaussianBlur(hard_rectangle(), (0, 0), sigma_px)


def sample_photo() -> np.ndarray:
    """Testbild mit jedem Farbton, einem Helligkeitsverlauf und einer harten Kante."""
    hsv = np.zeros((80, 180, 3), np.uint8)
    hsv[:, :, 0] = np.arange(180, dtype=np.uint8)[None, :]
    hsv[:, :, 1] = 200
    hsv[:, :, 2] = np.linspace(40, 240, 80).astype(np.uint8)[:, None]
    image = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    image[30:50, 30:60] = 0
    return image


def hsv_patches(hues: list[int]) -> np.ndarray:
    """Senkrechte Streifen mit vorgegebenen Farbtoenen (OpenCV-HSV, 0..179)."""
    hsv = np.zeros((60, PATCH_W * len(hues), 3), np.uint8)
    for index, hue in enumerate(hues):
        hsv[:, index * PATCH_W : (index + 1) * PATCH_W] = (hue, 220, 200)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def patch_saturation(image: np.ndarray, index: int) -> float:
    """Mittlere Saettigung eines Streifens."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    return float(hsv[:, index * PATCH_W : (index + 1) * PATCH_W, 1].mean())


def edge_position(image: np.ndarray, nominal_x: int, half: int = 14) -> float:
    """Subpixel-Lage einer senkrechten Kante ueber den 50-%-Durchgang."""
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)
    # Nur Zeilen aus der Mitte des Rechtecks, damit keine waagerechte Kante mitzaehlt.
    profile = grey[RECT_Y0 + 20 : RECT_Y1 - 20, nominal_x - half : nominal_x + half].mean(axis=0)

    # Die Plateauwerte am Fensterrand ablesen, nicht global: eine Unschaerfemaske
    # legt Ueber- und Unterschwinger direkt an die Kante, die Fensterraender
    # bleiben davon unberuehrt.
    level = (float(np.median(profile[:4])) + float(np.median(profile[-4:]))) / 2.0
    above = profile >= level
    index = int(np.argmax(above[:-1] != above[1:]))
    # Funktioniert in beide Richtungen: bei der rechten Kante sind Zaehler und
    # Nenner beide negativ.
    return nominal_x - half + index + (profile[index] - level) / (profile[index] - profile[index + 1])


def edge_pair(image: np.ndarray) -> tuple[float, float]:
    return (edge_position(image, RECT_X0), edge_position(image, RECT_X1))


def silhouette(image: np.ndarray) -> np.ndarray:
    """Welche Pixel liegen unter der Mitte zwischen hellstem und dunkelstem Wert."""
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)
    return grey < (float(grey.min()) + float(grey.max())) / 2.0


def gradient_energy(image: np.ndarray) -> float:
    """Mittlere Gradientenstaerke - ein Mass dafuer, wie steil die Kanten stehen."""
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)
    dx = cv2.Sobel(grey, cv2.CV_64F, 1, 0, ksize=3)
    dy = cv2.Sobel(grey, cv2.CV_64F, 0, 1, ksize=3)
    return float(np.hypot(dx, dy).mean())


# Je Feld des Vertrags ein Fall. Der Vollstaendigkeitstest weiter unten wacht
# darueber, dass ein neu hinzugekommenes Feld hier nicht vergessen wird.
EINZELFAELLE = {
    "grayscale": AdjustOptions(grayscale=True),
    "invert": AdjustOptions(invert=True),
    "brightness_auf": AdjustOptions(brightness=0.3),
    "brightness_ab": AdjustOptions(brightness=-0.3),
    "contrast": AdjustOptions(contrast=0.5),
    "saturation": AdjustOptions(saturation=0.6),
    "local_contrast": AdjustOptions(local_contrast=0.7),
    "edge_boost": AdjustOptions(edge_boost=0.8),
    "edge_overlay": AdjustOptions(edge_overlay=0.6),
    "color_emphasis": AdjustOptions(color_emphasis="red", emphasis_strength=1.0),
    "threshold": AdjustOptions(threshold=0.5),
}

# (Name, Einstellung, Toleranz an der harten Kante, Toleranz an der weichen Kante)
# in Pixeln. Null heisst: auf die letzte Stelle gleich, nicht "fast gleich".
KANTENFAELLE = [
    ("grayscale", AdjustOptions(grayscale=True), 0.0, 0.0),
    ("threshold", AdjustOptions(threshold=0.5), 0.0, 0.0),
    ("edge_boost", AdjustOptions(edge_boost=1.0), 0.0, 0.0),
    # CLAHE ist der einzige Fall, der ueberhaupt etwas bewegt, und auch das nur an
    # einer weichen Kante: es bildet kachelweise ab, kippt damit die Flanke
    # leicht und verschiebt den gemessenen 50-%-Punkt um rund 0,11 px. Kein Pixel
    # wandert - der Ort, an dem man die Kante ABLIEST, tut es. Bei 300 dpi sind
    # das 0,009 mm, drei Zehnerpotenzen unter dem Millimeter, um den es geht.
    ("local_contrast", AdjustOptions(local_contrast=1.0), 0.02, 0.15),
]


def assert_kante_bleibt(image: np.ndarray, options: AdjustOptions, toleranz_px: float) -> None:
    links_vorher, rechts_vorher = edge_pair(image)
    links, rechts = edge_pair(adjust(image, options))

    assert abs(links - links_vorher) <= toleranz_px
    assert abs(rechts - rechts_vorher) <= toleranz_px
    # Die Breite ist die Zahl, die als Millimeter auf dem Ausdruck ankommt. Beide
    # Kanten duerfen unabhaengig driften, also gilt hier die doppelte Toleranz.
    assert abs((rechts - links) - (rechts_vorher - links_vorher)) <= 2.0 * toleranz_px


def test_ohne_einstellungen_kommt_das_bild_bitgleich_zurueck():
    image = sample_photo()
    result = adjust(image, AdjustOptions())

    assert AdjustOptions().is_identity
    assert np.array_equal(result, image)
    assert result.shape == image.shape
    assert result.dtype == image.dtype
    # Immer ein neues Array: der Aufrufer darf ins Ergebnis zeichnen.
    assert result is not image


@pytest.mark.parametrize("name", sorted(EINZELFAELLE))
def test_jede_einzelne_einstellung_laesst_form_und_typ_stehen(name):
    image = sample_photo()
    original = image.copy()
    options = EINZELFAELLE[name]

    result = adjust(image, options)

    assert not options.is_identity
    assert result.shape == image.shape
    assert result.dtype == image.dtype
    assert np.array_equal(image, original), "Das Eingabebild wurde veraendert"


def test_die_einzelfaelle_decken_jedes_feld_des_vertrags_ab():
    """Ein neues Feld ohne Test faellt hier auf - nicht erst am Ausdruck."""
    geprueft = {
        feld.name
        for options in EINZELFAELLE.values()
        for feld in fields(AdjustOptions)
        if getattr(options, feld.name) != feld.default
    }
    assert geprueft == {feld.name for feld in fields(AdjustOptions)}


def test_die_kantenmessung_trifft_die_bekannte_lage():
    """Erst das Messwerkzeug pruefen, dann damit messen."""
    for image in (hard_rectangle(), soft_rectangle()):
        links, rechts = edge_pair(image)
        assert links == pytest.approx(RECT_X0 - 0.5, abs=1e-9)
        assert rechts == pytest.approx(RECT_X1 - 0.5, abs=1e-9)


@pytest.mark.parametrize(
    "options,toleranz_px",
    [(fall[1], fall[2]) for fall in KANTENFAELLE],
    ids=[fall[0] for fall in KANTENFAELLE],
)
def test_keine_einstellung_verschiebt_die_harte_kante(options, toleranz_px):
    assert_kante_bleibt(hard_rectangle(), options, toleranz_px)


@pytest.mark.parametrize(
    "options,toleranz_px",
    [(fall[1], fall[3]) for fall in KANTENFAELLE],
    ids=[fall[0] for fall in KANTENFAELLE],
)
def test_auch_eine_weiche_kante_bleibt_stehen(options, toleranz_px):
    """Der eigentliche Subpixel-Test: hier haette ein Zehntelpixel ueberhaupt Platz."""
    assert_kante_bleibt(soft_rectangle(), options, toleranz_px)


@pytest.mark.parametrize(
    "options", [fall[1] for fall in KANTENFAELLE], ids=[fall[0] for fall in KANTENFAELLE]
)
def test_die_silhouette_bleibt_pixelgenau_dieselbe(options):
    """Die schaerfste Fassung derselben Aussage: kein Pixel wechselt die Seite."""
    image = hard_rectangle()

    assert np.array_equal(silhouette(adjust(image, options)), silhouette(image))


def test_schwarzweiss_macht_alle_kanaele_gleich():
    result = adjust(sample_photo(), AdjustOptions(grayscale=True))

    assert result.shape[2] == 3, "Die Ausgabe bleibt dreikanalig"
    assert np.array_equal(result[:, :, 0], result[:, :, 1])
    assert np.array_equal(result[:, :, 1], result[:, :, 2])


def test_saettigung_ist_nach_schwarzweiss_wirkungslos():
    """Zugesagtes Verhalten des Vertrags - nicht bloss ein Nebeneffekt."""
    image = sample_photo()
    nur_grau = adjust(image, AdjustOptions(grayscale=True))
    grau_und_bunt = adjust(image, AdjustOptions(grayscale=True, saturation=1.0))

    assert np.array_equal(nur_grau, grau_und_bunt)


def test_farbbetonung_haelt_rot_und_entsaettigt_den_rest():
    image = hsv_patches([0, 60, 120])  # rot, gruen, blau
    result = adjust(image, AdjustOptions(color_emphasis="red", emphasis_strength=1.0))

    assert patch_saturation(result, 0) > 0.95 * patch_saturation(image, 0)
    assert patch_saturation(result, 1) < 0.10 * patch_saturation(image, 1)
    assert patch_saturation(result, 2) < 0.10 * patch_saturation(image, 2)


def test_die_farbtonnaht_bei_rot_faellt_nicht_auseinander():
    """Rot liegt bei 0 UND bei 179.

    Ohne Faltung am Farbkreis waere die eine Haelfte des Rots "179 Grad entfernt"
    und wuerde grau - der klassische Fehler an dieser Stelle, und er trifft
    ausgerechnet die Farbe, mit der man auf Holz anzeichnet.
    """
    image = hsv_patches([3, 176, 60])  # knapp ueber der Naht, knapp darunter, gruen
    result = adjust(image, AdjustOptions(color_emphasis="red", emphasis_strength=1.0))

    assert patch_saturation(result, 0) > 0.90 * patch_saturation(image, 0)
    assert patch_saturation(result, 1) > 0.90 * patch_saturation(image, 1)
    assert patch_saturation(result, 2) < 0.15 * patch_saturation(image, 2)


@pytest.mark.parametrize(
    "wert,options,erwartung",
    [
        (250, AdjustOptions(brightness=1.0), "hell"),
        (250, AdjustOptions(contrast=1.0), "hell"),
        (5, AdjustOptions(brightness=-1.0), "dunkel"),
        (5, AdjustOptions(contrast=1.0), "dunkel"),
    ],
)
def test_kein_ueberlauf_an_den_enden_des_wertebereichs(wert, options, erwartung):
    """Ein Glanzlicht, das nach Schwarz umschlaegt, ist der haesslichste Fehler hier."""
    image = np.full((20, 20, 3), wert, np.uint8)
    result = adjust(image, options)

    if erwartung == "hell":
        assert result.min() >= wert
    else:
        assert result.max() <= wert


def test_schwelle_liefert_genau_zwei_werte():
    result = adjust(sample_photo(), AdjustOptions(threshold=0.5))

    assert set(np.unique(result).tolist()) == {0, 255}


def test_staerkere_kantenanhebung_hebt_die_kante_staerker():
    """Der Regler muss ueber den ganzen Weg wirken, nicht nur an den Enden."""
    image = soft_rectangle()
    energie = [
        gradient_energy(adjust(image, AdjustOptions(edge_boost=staerke)))
        for staerke in (0.0, 0.25, 0.5, 0.75, 1.0)
    ]

    assert all(b > a for a, b in zip(energie, energie[1:])), energie


def test_staerkere_farbbetonung_entsaettigt_staerker():
    image = hsv_patches([0, 60])
    saettigung = [
        patch_saturation(
            adjust(image, AdjustOptions(color_emphasis="red", emphasis_strength=staerke)), 1
        )
        for staerke in (0.0, 0.25, 0.5, 0.75, 1.0)
    ]

    assert all(b < a for a, b in zip(saettigung, saettigung[1:])), saettigung


def test_unbekannte_farbbetonung_bricht_den_export_nicht_ab():
    """Lieber keine Betonung als ein Abbruch mitten im Export."""
    image = sample_photo()
    options = AdjustOptions(color_emphasis="tuerkis", emphasis_strength=1.0, invert=True)

    assert np.array_equal(adjust(image, options), 255 - image)


def test_fremder_datentyp_wird_abgewiesen():
    with pytest.raises(ValueError):
        adjust(np.zeros((10, 10, 3), np.float32), AdjustOptions(grayscale=True))
