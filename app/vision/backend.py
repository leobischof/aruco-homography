"""Welcher Rechenkern misst: die Python-Referenz oder der C++-Kern.

    ARUCO_CORE=python   (Vorgabe)  ->  app/vision/*.py, wie bisher
    ARUCO_CORE=cpp                 ->  core/ ueber die pybind11-Bindung

Es gibt bewusst KEINE zweite Testsuite fuer C++. Die vorhandene laeuft gegen
beide Kerne; getauscht wird nur, was hinter `app/vision/` steckt, und die Tests
merken davon nichts (docs/cpp-migration/README.md, Abschnitt 4). Zwei Suiten
driften genauso wie zwei Implementierungen, nur unbemerkt.

**Kein Rueckfall.** Ist `ARUCO_CORE=cpp` verlangt und der Kern nicht gebaut,
bricht der Import ab. Still auf Python zurueckzufallen waere die teuerste Art zu
scheitern, die es hier gibt: `run-tests-cpp` waere gruen und haette den C++-Kern
nie angefasst. Dieselbe Haltung wie bei den Konstanten (AGENTS.md, Invariante 4).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import ModuleType

PYTHON = "python"
CPP = "cpp"

# core/build/ ist das Bauverzeichnis aus `./dev.ps1 build-core`. Daneben liegen
# die Laufzeit-DLLs (opencv_world500.dll), die CMake dorthin kopiert - Windows
# sucht neben einer .pyd, bevor es den PATH befragt, deshalb braucht es hier
# keine Umgebungsvariable.
CORE_BUILD_DIR = Path(__file__).resolve().parents[2] / "core" / "build"

_HOW_TO_BUILD = (
    f"ARUCO_CORE={CPP} verlangt den C++-Kern, aber `aruco_core` liess sich nicht "
    f"laden (gesucht in {CORE_BUILD_DIR}). Bauen mit:  .\\dev.ps1 build-core"
)


def _import_core() -> ModuleType:
    """Das gebaute Modul `aruco_core` laden. Wirft ImportError, wenn es fehlt."""
    location = str(CORE_BUILD_DIR)
    if location not in sys.path:
        sys.path.insert(0, location)
    import aruco_core  # noqa: PLC0415 - erst hier, weil es das Bauergebnis ist

    return aruco_core


def cpp_core() -> ModuleType | None:
    """Der C++-Kern, oder None wenn er nicht gebaut ist.

    Unabhaengig davon, welcher Kern gerade aktiv ist: der Quervergleich in
    tests/test_backend.py stellt beide nebeneinander, und der laeuft auch im
    Python-Lauf. Ein Unterschied faellt so am selben Tag auf, an dem er entsteht.
    """
    try:
        return _import_core()
    except ImportError:
        return None


def _requested_core() -> str:
    name = (os.environ.get("ARUCO_CORE") or PYTHON).strip().lower()
    if name not in (PYTHON, CPP):
        raise RuntimeError(
            f"ARUCO_CORE={name!r} ist unbekannt - erlaubt sind {PYTHON!r} und {CPP!r}."
        )
    return name


ACTIVE = _requested_core()

if ACTIVE == CPP:
    try:
        core: ModuleType | None = _import_core()
    except ImportError as error:
        raise RuntimeError(_HOW_TO_BUILD) from error
else:
    core = None


def implementation(name: str, python_impl):
    """Die aktive Umsetzung von `name` - Python-Referenz oder C++-Kern.

    Jedes portierte Modul in `app/vision/` holt seine Rechnung hier ab, statt
    sie selbst auszuwaehlen. Eine Stelle, an der der Schalter steht.
    """
    if ACTIVE == PYTHON:
        return python_impl
    assert core is not None  # ACTIVE == CPP heisst: der Import oben ist gelungen
    return getattr(core, name)
