"""Fassung und Beschreibung fuer die Werkbank aus dem Repo lesen.

Beides steht schon da: die Fassung in app/config.py, die Beschreibung in
CHANGELOG.md. Sie hier zu LESEN statt der Werkbank zu sagen, ist derselbe
Grundsatz wie ueberall sonst - eine Konstante hat genau eine Stelle
(AGENTS.md, Invariante 4).

    python tools/release_notes.py --version    # -> 0.1.7-alpha
    python tools/release_notes.py --notes      # -> der Abschnitt aus CHANGELOG.md

WARUM APP_VERSION GEPARST UND NICHT IMPORTIERT WIRD. app/config.py importiert
cv2. Die Pruefaufgabe der Werkbank soll die Fassung lesen koennen, BEVOR 90 MB
OpenCV installiert sind - sonst kostet jeder Push nach master die volle
Einrichtung, auch einer, der gar keine Fassung ist. Gelesen wird dieselbe eine
Zeile; dass beide Wege dasselbe ergeben, haelt tests/test_release_notes.py fest.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "app" / "config.py"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"


def read_version() -> str:
    """APP_VERSION aus app/config.py holen, ohne das Modul auszufuehren."""
    tree = ast.parse(CONFIG_PATH.read_text(encoding="utf-8"), filename=str(CONFIG_PATH))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                return ast.literal_eval(node.value)
    raise KeyError(f"APP_VERSION steht nicht in {CONFIG_PATH}")


def extract_notes(changelog: str, version: str) -> str:
    """Den Abschnitt einer Fassung aus einem Keep-a-Changelog-Text holen.

    Ohne die Ueberschrift selbst: die Fassungsseite nennt die Fassung schon in
    ihrem Titel, und zweimal dieselbe Zeile liest sich wie ein Versehen.
    """
    # re.escape, weil der Punkt in "0.1.7" ein Punkt ist und kein Platzhalter.
    heading = re.compile(r"^## \[" + re.escape(version) + r"\].*$", re.MULTILINE)
    match = heading.search(changelog)
    if match is None:
        raise KeyError(version)

    following = re.compile(r"^## ", re.MULTILINE).search(changelog, match.end())
    end = following.start() if following else len(changelog)
    return changelog[match.end():end].strip()


def main(argv: list[str] | None = None) -> int:
    # Die Ausgabe geht in der Werkbank in eine Datei und nicht auf eine Konsole.
    # Ohne diese Zeile gilt dort cp1252, und das erste Sonderzeichen aus dem
    # Changelog bricht den Lauf ab (AGENTS.md, "Unicode auf der Konsole").
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Fassung und Changelog-Abschnitt ausgeben.")
    what = parser.add_mutually_exclusive_group(required=True)
    what.add_argument("--version", action="store_true", help="nur die Fassungsnummer")
    what.add_argument("--notes", action="store_true", help="der Changelog-Abschnitt dazu")
    args = parser.parse_args(argv)

    version = read_version()
    if args.version:
        print(version)
        return 0

    try:
        print(extract_notes(CHANGELOG_PATH.read_text(encoding="utf-8"), version))
    except KeyError:
        print(
            f"CHANGELOG.md hat keinen Abschnitt fuer {version}. "
            "Eine Fassung ohne Beschreibung wird nicht ausgeliefert.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
