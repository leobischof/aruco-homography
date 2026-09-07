"""shared/constants.json -> core/include/aruco/constants.hpp.

Aufruf (macht CMake bei jedem Lauf selbst):

    python core/tools/gen_constants.py <constants.json> <constants.hpp.in> <constants.hpp>

Die erzeugte Datei ist NICHT eingecheckt (.gitignore). Sie waere sonst eine
zweite Definition derselben Millimeter und verletzte Invariante 4 - siehe den
Kommentarkopf der Vorlage.

Uebersetzt wird stur nach Typ, damit eine neue Konstante in der JSON-Datei ohne
Handgriff in C++ ankommt:

    "DICT_4X4_50"       -> std::string_view
    true                -> bool
    300                 -> int
    67.0                -> double
    [210.0, 297.0]      -> std::array<double, 2>
    {"A4": [...], ...}  -> std::array<std::pair<std::string_view, ...>, N>

Zwei bewusste Entscheidungen:

* Fliesskommazahlen werden mit repr() geschrieben. Das ist Pythons kuerzeste
  Darstellung, die exakt zurueckliest - der C++-double bekommt Bit fuer Bit
  denselben Wert wie der Python-float. `round(x, 6)` waere schoener zu lesen und
  eine stille Verfaelschung.
* Woerterbuecher werden nach Schluessel sortiert ausgegeben. Damit ist der Lauf
  reproduzierbar und ein `git diff` der erzeugten Datei zeigt echte Aenderungen
  statt umsortierter Zeilen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PLACEHOLDER = "@ARUCO_GENERATED_CONSTANTS@"
SOURCE_PLACEHOLDER = "@ARUCO_CONSTANTS_SOURCE@"


def literal(value: object) -> tuple[str, str]:
    """(C++-Typ, C++-Literal) fuer einen JSON-Wert.

    Wirft bei allem, was sich nicht eindeutig abbilden laesst - lieber ein
    Bauabbruch mit Namen als eine Konstante, die stillschweigend fehlt.
    """
    if isinstance(value, bool):  # vor int pruefen: bool IST ein int in Python
        return "bool", "true" if value else "false"
    if isinstance(value, int):
        return "int", str(value)
    if isinstance(value, float):
        return "double", repr(value)
    if isinstance(value, str):
        return "std::string_view", json.dumps(value)
    if isinstance(value, list):
        return _array_literal(value)
    if isinstance(value, dict):
        return _map_literal(value)
    raise TypeError(f"Kein C++-Gegenstueck fuer {type(value).__name__}: {value!r}")


def _array_literal(values: list) -> tuple[str, str]:
    if not values:
        raise ValueError("Leere Liste - der Elementtyp waere geraten.")
    # Eine Liste aus 3 und 4.5 ist in JSON gemischt, in C++ nicht: sobald ein
    # Element eine Fliesskommazahl ist, wird die ganze Liste double.
    if any(isinstance(item, float) for item in values):
        values = [float(item) for item in values]
    element_types = {literal(item)[0] for item in values}
    if len(element_types) != 1:
        raise TypeError(f"Gemischte Liste: {sorted(element_types)}")
    element = element_types.pop()
    items = ", ".join(literal(item)[1] for item in values)
    return f"std::array<{element}, {len(values)}>", f"{{{{{items}}}}}"


def _typed(value: object) -> str:
    """Ein Literal, das auch als Argument eines std::pair eindeutig ist.

    Eine geschweifte Klammer allein hat dort keinen Typ - `{{297.0, 420.0}}`
    weiss nicht, dass es ein std::array werden soll. Skalare dagegen brauchen
    keinen Typnamen davor, und mit einem waeren sie schlicht falsch ("int120").
    """
    kind, text = literal(value)
    return f"{kind}{text}" if isinstance(value, (list, dict)) else text


def _map_literal(mapping: dict) -> tuple[str, str]:
    if not mapping:
        raise ValueError("Leeres Woerterbuch - der Werttyp waere geraten.")
    pairs = sorted(mapping.items())
    value_types = {literal(value)[0] for _, value in pairs}
    if len(value_types) != 1:
        raise TypeError(f"Gemischtes Woerterbuch: {sorted(value_types)}")
    value_type = value_types.pop()
    entries = ",\n    ".join(
        f"std::pair<std::string_view, {value_type}>{{{json.dumps(key)}, "
        f"{_typed(value)}}}"
        for key, value in pairs
    )
    kind = f"std::array<std::pair<std::string_view, {value_type}>, {len(pairs)}>"
    return kind, f"{{{{\n    {entries},\n}}}}"


def render(constants: dict) -> str:
    lines: list[str] = []
    for name, value in constants.items():
        if name.startswith("_"):  # "_comment" und Verwandtes sind Prosa
            continue
        kind, text = literal(value)
        lines.append(f"inline constexpr {kind} {name} = {text};")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2

    source, template, target = (Path(part) for part in argv[1:])
    constants = json.loads(source.read_text(encoding="utf-8"))

    header = (
        template.read_text(encoding="utf-8")
        .replace(SOURCE_PLACEHOLDER, source.name)
        .replace(PLACEHOLDER, render(constants))
    )

    target.parent.mkdir(parents=True, exist_ok=True)
    # Nur schreiben, wenn sich etwas geaendert hat: sonst stuepst jeder CMake-Lauf
    # den Zeitstempel an und uebersetzt den ganzen Kern neu.
    if not target.exists() or target.read_text(encoding="utf-8") != header:
        target.write_text(header, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
