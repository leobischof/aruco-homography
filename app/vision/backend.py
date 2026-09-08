"""Welcher Rechenkern misst: die Python-Referenz oder der C++-Kern.

    ARUCO_CORE=python   ->  app/vision/*.py, die Referenz
    ARUCO_CORE=cpp      ->  core/ ueber die pybind11-Bindung

Die Vorgabe haengt davon ab, WO das Programm laeuft, und das ist Absicht:

    im Quellbaum   ->  python   -- die Referenz, gegen die geprueft wird
    in der .exe    ->  cpp      -- ausgeliefert wird der C++-Kern

Der Quellbaum bleibt bei Python, weil `./dev.ps1 run-tests` sonst je nach
Bauzustand von core/build/ etwas anderes messen wuerde als gestern - ein Lauf,
der sich selbst nicht gleicht, belegt nichts. Die .exe nimmt den C++-Kern, weil
genau er ausgeliefert wird; `./dev.ps1 run-tests-cpp` prueft diesen Fall.

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

from app import config

PYTHON = "python"
CPP = "cpp"

# Wo `aruco_core` liegt, haengt daran, ob eingefroren wurde:
#
#   Quellbaum  ->  core/build/            aus `./dev.ps1 build-core`
#   Bundle     ->  _internal/             aus aruco-homographie.spec
#
# In beiden Faellen liegt opencv_world500.dll DANEBEN, und das ist die ganze
# Wegfindung fuer die DLL: Windows durchsucht das Verzeichnis der .pyd, bevor es
# den PATH befragt. Deshalb braucht es hier keine Umgebungsvariable - aber
# deshalb muss die Bauvorschrift die DLL auch wirklich mitnehmen.
CORE_DIR = (
    config.BUNDLE_DIR
    if config.BUNDLE_DIR is not None
    else Path(__file__).resolve().parents[2] / "core" / "build"
)

# Der Rat muss zum Ort passen. Wer die .exe benutzt, kann nichts "bauen" - dort
# ist ein fehlender Kern kein Arbeitsschritt, sondern eine kaputte Installation.
_HOW_TO_BUILD = (
    f"Der C++-Kern fehlt in dieser Installation (gesucht in {CORE_DIR}). "
    f"Die Anwendung ist unvollstaendig entpackt - bitte neu installieren."
    if config.FROZEN
    else (
        f"ARUCO_CORE={CPP} verlangt den C++-Kern, aber `aruco_core` liess sich "
        f"nicht laden (gesucht in {CORE_DIR}). Bauen mit:  .\\dev.ps1 build-core"
    )
)


def _import_core() -> ModuleType:
    """Das gebaute Modul `aruco_core` laden. Wirft ImportError, wenn es fehlt."""
    location = str(CORE_DIR)
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


# Im Bundle ist der C++-Kern die Vorgabe. Ohne diese Zeile waere er zwar
# mitgeliefert, aber unbenutzt: die .exe rechnete weiter in Python und der
# ganze Umzug waere in der Auslieferung unsichtbar - der teuerste Fehler, den
# es hier gibt, weil alles gruen aussaehe.
DEFAULT = CPP if config.FROZEN else PYTHON


def _requested_core() -> str:
    name = (os.environ.get("ARUCO_CORE") or DEFAULT).strip().lower()
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
