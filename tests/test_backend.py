"""Der Umschalter zwischen den Kernen - und der Quervergleich zwischen ihnen.

Die uebrigen Tests wissen nicht, welcher Kern rechnet; das ist ihr Sinn. Diese
Datei ist die einzige, die es wissen darf, und sie stellt die eine Frage, die
sonst niemand stellt: **rechnen die beiden gleich?**

Der Vergleich laeuft in BEIDEN Betriebsarten, sobald der C++-Kern gebaut ist.
Ein Auseinanderlaufen faellt damit am selben Tag auf, an dem es entsteht - und
nicht erst, wenn jemand nach Wochen die Millimeter am Ausdruck nachmisst.
"""

from __future__ import annotations

import numpy as np
import pytest

from app import config
from app.vision import backend
from app.vision.detect import _detect_markers_python
from tests.test_conformance import NAMES, load

# Wie weit die beiden Kerne auseinanderliegen duerfen, in Pixeln.
#
# Gemessen am 2026-09-08 auf dieser Werkzeugkette: **0,0 px** - Ecke fuer Ecke
# bitgleich. Die Schranke ist trotzdem nicht null, weil beide Seiten die Ecken als
# float32 herausbekommen: ein anderer Uebersetzer oder ein anderer SIMD-Pfad kann
# das letzte Bit anders runden, und bei rund 1 000 px ist ein float32-ULP schon
# 1,2e-4 px (so gross war der Unterschied nativ gegen WASM in Stufe 0).
#
# 1e-3 px liegt darueber und weit unter allem, was eine Messung waere: die
# vertragliche Eckentoleranz ist 0,75 px, und schon ein vergessenes CLAHE
# verschoebe die Ecken um rund 0,03 px - das 30-Fache dieser Schranke. Wer diese
# Zahl hochsetzen muss, hat einen Befund und keine zu strenge Schranke.
CORE_AGREEMENT_PX = 1e-3


@pytest.fixture(scope="module")
def cpp():
    """Der C++-Kern, oder ein uebersprungener Test, wenn er nicht gebaut ist."""
    core = backend.cpp_core()
    if core is None:
        pytest.skip(f"C++-Kern nicht gebaut ({backend.CORE_DIR}) - ./dev.ps1 build-core")
    return core


def test_aktiver_kern_ist_einer_der_beiden():
    assert backend.ACTIVE in (backend.PYTHON, backend.CPP)


def test_unbekannter_kern_wird_abgewiesen(monkeypatch):
    """Ein Tippfehler in ARUCO_CORE darf nicht still zu Python werden.

    Sonst liefe `run-tests-cpp` gruen und haette den C++-Kern nie angefasst.
    """
    monkeypatch.setenv("ARUCO_CORE", "rust")
    with pytest.raises(RuntimeError, match="rust"):
        backend._requested_core()


def test_der_cpp_kern_kennt_die_geteilten_konstanten(cpp):
    """Der erzeugte Header kommt wirklich aus shared/constants.json.

    Ein Kern mit veralteten Konstanten misst falsch und sagt es nicht - genau
    deshalb wird der Header bei jedem Bau neu erzeugt und nicht eingecheckt.
    """
    assert cpp.ARUCO_DICT_NAME == config.ARUCO_DICT_NAME
    assert cpp.MARKER_MM_NOMINAL == pytest.approx(config.MARKER_MM_NOMINAL)


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("enhance_contrast", [True, False])
def test_beide_kerne_finden_dieselben_ecken(cpp, name, enhance_contrast):
    """Der eigentliche Zweck dieser Datei.

    Verglichen wird auf den eingefrorenen Szenen, mit und ohne CLAHE. Ohne den
    zweiten Fall bliebe unbemerkt, wenn der C++-Kern den Kontrastschalter gar
    nicht auswertet: mit CLAHE laegen beide Kerne dann trotzdem uebereinander.
    """
    image, _ = load(name)

    reference = dict(_detect_markers_python(image, enhance_contrast))
    measured = dict(cpp.detect_markers(image, enhance_contrast))

    assert sorted(measured) == sorted(reference), "verschiedene Marker gefunden"
    for marker_id, expected in reference.items():
        difference = float(np.abs(measured[marker_id] - expected).max())
        assert difference <= CORE_AGREEMENT_PX, (
            f"Marker {marker_id}: die Kerne liegen {difference:.3e} px auseinander"
        )


@pytest.mark.parametrize("name", NAMES)
def test_der_kontrastschalter_wirkt_in_beiden_kernen(cpp, name):
    """CLAHE ist kein Schoenheitsschalter, sondern veraendert die Messung.

    Stufe 0 hat den Unterschied nachgemessen (0,140 px mit, 0,160 px ohne). Ein
    Kern, der den Schalter still ignoriert, faellt hier auf - und nur hier: der
    Vergleich oben saehe zwei ignorierende Kerne als einig an.
    """
    image, _ = load(name)

    for core_markers in (
        (dict(_detect_markers_python(image, True)), dict(_detect_markers_python(image, False))),
        (dict(cpp.detect_markers(image, True)), dict(cpp.detect_markers(image, False))),
    ):
        with_clahe, without = core_markers
        moved = max(float(np.abs(with_clahe[key] - without[key]).max()) for key in with_clahe)
        assert moved > CORE_AGREEMENT_PX, "CLAHE hat die Ecken nicht bewegt"
