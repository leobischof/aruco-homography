"""Kosmetische Aufbereitung des bereits entzerrten Bildes.

Dieses Modul macht das Bild lesbarer: eine blasse Bleistiftlinie schneidbar, eine
farbige Anzeichnung vom Holz unterscheidbar, ein Umriss als reines Schwarzweiss.
Es macht das Bild nicht groesser, kleiner, gerader oder anders beschnitten.

Die eine Regel, aus der hier alles folgt: Aufbereitung ist KOSMETISCH, NIE
GEOMETRISCH. Die Homographie wird am unberuehrten Foto gemessen; dieses Modul
greift erst danach an, am fertig entzerrten Bild. Millimeter sind das Produkt
(AGENTS.md) - ein Schaerferegler, der eine Kante um ein halbes Pixel verschiebt,
verschiebt sie auf dem Ausdruck mit, und der Deckel passt nicht mehr. Daraus
folgt hart:

- Form und Datentyp der Ausgabe sind immer die der Eingabe.
- Es wird nicht skaliert, gedreht, entzerrt, beschnitten oder umgerandet.
- Jeder Weichzeichner ist symmetrisch. Ein unsymmetrischer Kern waere eine
  Verschiebung, nur huebsch verpackt.
- Stehen alle Regler neutral, kommt das Bild Bit fuer Bit zurueck.
- Die Kantenzeichnung faerbt genau die Pixel, die Canny als Kante markiert. Sie
  legt Tinte dazu, sie rueckt nichts.

Nachgewiesen wird das in tests/test_enhance.py: dort wird die Subpixel-Lage einer
Kante vor und nach jedem einzelnen Eingriff gemessen.

Die Reihenfolge der Stufen ist fest verdrahtet, damit dieselben Regler morgen
dieselbe Schablone ergeben:

1. Farbbetonung - arbeitet auf den Farben, wie sie fotografiert wurden. Jede
   Tonwertkurve davor haette die Farbtoene schon verbogen.
2. Schwarzweiss - danach ist alles neutral. Die Saettigung wird dadurch von
   selbst wirkungslos, genau wie im Vertrag zugesagt.
3. Lokaler Kontrast (CLAHE) - vor der globalen Kurve, denn CLAHE gleicht
   Helligkeit kachelweise wieder aus und wuerde eine vorher gesetzte Aufhellung
   schlicht auffressen.
4. Kantenanhebung - schaerft den Kontrast, den Stufe 3 gerade hergestellt hat.
5. Helligkeit und Kontrast - die globale Kurve hat das letzte Wort ueber den
   sichtbaren Bereich, und geklemmt wird genau einmal, hier.
6. Saettigung - der letzte Eingriff in der Farbe, weil eine Kontrastaenderung
   die Buntheit bereits mitzieht. So tut der Regler, was draufsteht.
7. Kantenzeichnung - wird aufgelegt, nachdem der Ton steht. Frueher gezogen,
   wuerde die naechste Kurve die Linien wieder verwaschen; und Canny findet auf
   dem geschaerften Bild mehr als auf dem rohen.
8. Schwelle - bindet die aufgelegten Linien mit ins Schwarz ein.
9. Negativ - ganz am Ende, weil sonst jeder Regler davor verkehrt herum wirkte:
   "heller" wuerde dunkler machen.

Zwischen den Stufen liegt immer uint8. Das kostet je Stufe hoechstens eine
Rundungsstelle, macht aber jede Stufe einzeln abschaltbar - eine neutral
gestellte Stufe reicht das Bild unangetastet weiter, statt es durch einen
Fliesskomma-Umweg zu schicken.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app import config

# Der Wertebereich von uint8 und der Farbkreis von OpenCV-HSV. Beides sind
# Eigenschaften der Datentypen, keine frei gewaehlten Groessen - deshalb stehen
# sie hier und nicht in config.py (AGENTS.md, Invariante 4).
_VALUE_MAX = float(np.iinfo(np.uint8).max)
_MID_GREY = _VALUE_MAX / 2.0
_HUE_PERIOD = 180.0


@dataclass(frozen=True)
class AdjustOptions:
    """Alle Regler der Bildaufbereitung. Neutral heisst: nichts tun.

    Diese Klasse ist die einzige Definition dieser Namen und Wertebereiche; die
    Pydantic-Fassung der API spiegelt sie, sie erfindet nichts dazu.
    """

    grayscale: bool = False          # Schwarzweiss
    invert: bool = False             # Negativ
    brightness: float = 0.0          # -1.0 .. 1.0, 0 = unveraendert
    contrast: float = 0.0            # -1.0 .. 1.0, 0 = unveraendert
    saturation: float = 0.0          # -1.0 .. 1.0, 0 = unveraendert (bei grayscale wirkungslos)
    local_contrast: float = 0.0      # 0.0 .. 1.0, CLAHE-Staerke
    edge_boost: float = 0.0          # 0.0 .. 1.0, Unschaerfemaske
    edge_overlay: float = 0.0        # 0.0 .. 1.0, erkannte Kanten aufgelegt
    color_emphasis: str = "none"     # "none" | einer der Schluessel aus ADJUST_EMPHASIS_HUES
    emphasis_strength: float = 0.0   # 0.0 .. 1.0
    threshold: float = 0.0           # 0.0 .. 1.0, 0 = aus, sonst Schwelle -> reines Schwarzweiss

    @property
    def is_identity(self) -> bool:
        """True, wenn keine einzige Stufe etwas zu tun hat.

        Die Bedingungen spiegeln genau die Wachklauseln der Stufen. Laufen die
        beiden auseinander, ist das Ergebnis zwar immer noch richtig, aber die
        Abkuerzung greift nicht mehr - deshalb stehen sie beieinander.
        """
        return not (
            self.grayscale
            or self.invert
            or self.brightness != 0.0
            or self.contrast != 0.0
            or self.saturation != 0.0
            or self.local_contrast > 0.0
            or self.edge_boost > 0.0
            or self.edge_overlay > 0.0
            or self.threshold > 0.0
            or (self.color_emphasis in config.ADJUST_EMPHASIS_HUES
                and self.emphasis_strength > 0.0)
        )


def adjust(bgr: np.ndarray, options: AdjustOptions) -> np.ndarray:
    """Bereitet ein entzerrtes BGR-Bild auf. Geometrie bleibt unangetastet.

    Zurueck kommt immer ein NEUES Array - auch dann, wenn nichts zu tun war. Das
    Eingabebild wird nie veraendert und nie durchgereicht, damit der Aufrufer ins
    Ergebnis zeichnen darf, ohne sein Original zu beschaedigen.
    """
    image = _require_bgr8(bgr)
    if options.is_identity:
        return image.copy()

    image = _emphasise(image, options)
    image = _grayscale(image, options)
    image = _local_contrast(image, options)
    image = _edge_boost(image, options)
    image = _tone(image, options)
    image = _saturation(image, options)
    image = _edge_overlay(image, options)
    image = _threshold(image, options)
    return _invert(image, options)


def _require_bgr8(bgr: np.ndarray) -> np.ndarray:
    """Wachklausel: dieses Modul rechnet ausschliesslich in 8-Bit-BGR."""
    image = np.asarray(bgr)
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(
            f"Bildaufbereitung erwartet ein BGR-Bild aus uint8, bekam "
            f"{image.shape} / {image.dtype}."
        )
    # OpenCV braucht zusammenhaengenden Speicher; ein Ausschnitt waere es nicht.
    return np.ascontiguousarray(image)


def _emphasise(image: np.ndarray, options: AdjustOptions) -> np.ndarray:
    """Einen Farbton behalten, alles andere entsaettigen."""
    centre_hue = config.ADJUST_EMPHASIS_HUES.get(options.color_emphasis)
    # Ein unbekannter Schluessel ist ein Fehler der aufrufenden Schicht, die ihn
    # per Literal-Typ gar nicht durchlaesst. Hier gilt trotzdem: lieber keine
    # Betonung als ein Abbruch mitten im Export.
    if centre_hue is None or options.emphasis_strength <= 0.0:
        return image

    hue, saturation, value = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2HSV))
    weight = _hue_weight_lut(float(centre_hue))[hue]
    # Der betonte Farbton behaelt seine Saettigung, wie sie fotografiert wurde -
    # sie wird nicht angehoben. Angehobene Farbe waere erfundene Farbe.
    keep = 1.0 - options.emphasis_strength * (1.0 - weight)
    saturation = _to_uint8(saturation.astype(np.float32) * keep)
    return cv2.cvtColor(cv2.merge((hue, saturation, value)), cv2.COLOR_HSV2BGR)


def _hue_weight_lut(centre_hue: float) -> np.ndarray:
    """Gewicht je Farbton (0..179): Gauss um die Mitte, ueber die Naht hinweg."""
    hues = np.arange(_HUE_PERIOD, dtype=np.float32)
    distance = np.abs(hues - centre_hue)
    # Der Farbkreis ist geschlossen: Rot liegt bei 0 UND bei 179. Ohne diese
    # Faltung an der Naht fiele die halbe Farbe aus dem Fenster - der klassische
    # Fehler an dieser Stelle, und er trifft ausgerechnet Rot.
    distance = np.minimum(distance, _HUE_PERIOD - distance)
    return np.exp(-0.5 * (distance / float(config.ADJUST_EMPHASIS_SIGMA_DEG)) ** 2)


def _grayscale(image: np.ndarray, options: AdjustOptions) -> np.ndarray:
    """Schwarzweiss, aber weiter dreikanalig."""
    if not options.grayscale:
        return image
    # Dreikanalig zurueck, damit die PDF-Einbettung keinen Sonderfall braucht.
    return cv2.cvtColor(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)


def _local_contrast(image: np.ndarray, options: AdjustOptions) -> np.ndarray:
    """CLAHE auf der Helligkeit - holt Zeichnung aus Schatten und Lichtern."""
    if options.local_contrast <= 0.0:
        return image

    # Auf L in LAB, niemals auf B, G und R einzeln: drei getrennte
    # Histogrammspreizungen ziehen die Kanaele auseinander und faerben das Bild um.
    lightness, green_red, blue_yellow = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2LAB))
    # Clip-Limit 1.0 heisst "alles gekappt" und damit praktisch Identitaet; von
    # dort laeuft die Staerke stetig bis ADJUST_CLAHE_CLIP_MAX hoch.
    clip = 1.0 + options.local_contrast * (config.ADJUST_CLAHE_CLIP_MAX - 1.0)
    tiles = (config.ADJUST_CLAHE_TILES, config.ADJUST_CLAHE_TILES)
    lightness = cv2.createCLAHE(clipLimit=clip, tileGridSize=tiles).apply(lightness)
    return cv2.cvtColor(cv2.merge((lightness, green_red, blue_yellow)), cv2.COLOR_LAB2BGR)


def _edge_boost(image: np.ndarray, options: AdjustOptions) -> np.ndarray:
    """Unschaerfemaske: Kanten steiler, Lage unveraendert."""
    if options.edge_boost <= 0.0:
        return image

    # Der Gauss ist punktsymmetrisch. Die Maske (Bild minus Unschaerfe) ist
    # deshalb antisymmetrisch zur Kante: sie hebt die eine Seite genau so weit
    # an, wie sie die andere absenkt. Der Nulldurchgang - die Kante - bleibt, wo
    # er war. Ein einseitiger Kern wuerde hier Millimeter kosten.
    blurred = cv2.GaussianBlur(image, (0, 0), config.ADJUST_UNSHARP_SIGMA_PX)
    amount = options.edge_boost * config.ADJUST_UNSHARP_MAX
    values = image.astype(np.float32)
    return _to_uint8(values + amount * (values - blurred.astype(np.float32)))


def _tone(image: np.ndarray, options: AdjustOptions) -> np.ndarray:
    """Globale Tonwertkurve: Kontrast um das Mittelgrau, dann Helligkeit."""
    if options.brightness == 0.0 and options.contrast == 0.0:
        return image

    # Kontrast 1.0 verdoppelt den Abstand zum Mittelgrau, -1.0 zieht alles auf
    # Mittelgrau zusammen. Helligkeit 1.0 hebt um den vollen Wertebereich an -
    # beide Enden bedeuten also genau das, was sie versprechen.
    gain = 1.0 + options.contrast
    offset = options.brightness * _VALUE_MAX
    values = image.astype(np.float32)
    return _to_uint8((values - _MID_GREY) * gain + _MID_GREY + offset)


def _saturation(image: np.ndarray, options: AdjustOptions) -> np.ndarray:
    """Buntheit, ueber die Grauachse gemischt."""
    if options.saturation == 0.0:
        return image

    # Mischen statt S in HSV skalieren: das haelt den Farbton exakt und kostet
    # keine zweite Farbraumwandlung. Auf einem bereits grauen Bild ist die
    # Differenz null - deshalb ist der Regler nach Schwarzweiss wirkungslos.
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)[:, :, None]
    values = image.astype(np.float32)
    return _to_uint8(grey + (1.0 + options.saturation) * (values - grey))


def _edge_overlay(image: np.ndarray, options: AdjustOptions) -> np.ndarray:
    """Erkannte Kanten als dunkle Linien auflegen."""
    if options.edge_overlay <= 0.0:
        return image

    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(grey, *config.ADJUST_EDGE_CANNY)
    # Canny markiert das Kantenpixel selbst. Abgedunkelt wird genau dieses Pixel,
    # nichts daneben und nichts dazwischen: die Zeichnung legt Tinte auf die
    # Kante, sie verschiebt sie nicht.
    ink = edges > 0
    result = image.copy()
    result[ink] = _to_uint8(result[ink].astype(np.float32) * (1.0 - options.edge_overlay))
    return result


def _threshold(image: np.ndarray, options: AdjustOptions) -> np.ndarray:
    """Harte Schwelle: nur noch Schwarz und Weiss."""
    if options.threshold <= 0.0:
        return image

    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(grey, options.threshold * _VALUE_MAX, _VALUE_MAX, cv2.THRESH_BINARY)
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


def _invert(image: np.ndarray, options: AdjustOptions) -> np.ndarray:
    """Negativ."""
    if not options.invert:
        return image
    # bitwise_not ist auf uint8 exakt 255 - v: kein Rundungsweg, kein Klemmen.
    return cv2.bitwise_not(image)


def _to_uint8(values: np.ndarray) -> np.ndarray:
    """Zurueck nach uint8: erst runden, dann klemmen.

    Ohne das Klemmen laeuft eine Aufhellung ueber 255 hinaus um und macht aus
    einem Glanzlicht ein schwarzes Loch - der haesslichste Fehler, den dieses
    Modul haben koennte. cv2.convertScaleAbs waere hier ebenfalls falsch: es
    nimmt den Betrag, und ein tief abgedunkelter Schatten kaeme weiss zurueck.
    """
    return np.clip(np.rint(values), 0.0, _VALUE_MAX).astype(np.uint8)
