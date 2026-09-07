"""Backt app/static/brand/logo-dark.svg zu web/pdf/assets/logo.js.

Warum es diesen Umweg gibt: im Browser gibt es kein Dateisystem und keinen
SVG-Leser, den man einem PDF-Bau unterschieben koennte. `svglib` erledigt das
heute auf der Python-Seite; in JavaScript muessen die Pfaddaten IM MODUL liegen.

Das Logo ist eine feste Zeichnung, keine wechselnde Eingabe - es einmal zu backen
ist deshalb kein Verlust an Allgemeinheit, sondern der Verzicht auf einen
SVG-Interpreter, den niemand braucht.

Dieses Werkzeug ist die Herkunftsangabe des Erzeugnisses: wer wissen will, woher
die Zahlen in logo.js kommen, laesst es noch einmal laufen. Es gehoert NICHT in
den Auslieferungspfad und laeuft nur von Hand:

    venv\\Scripts\\python.exe tools\\bake_logo_asset.py

Was es kann und was nicht: Transformationen (translate, scale, rotate, matrix),
verschachtelte Gruppen, `clip-path` mit `clipPathUnits="userSpaceOnUse"` und die
Pfadbefehle M L H V C S Q T Z. KEINE Boegen (A/a) - die kommen in diesem Logo
nicht vor, und ein stiller Naeherungswert waere hier das Schlechteste. Taucht
einer auf, bricht der Lauf ab.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app import config  # noqa: E402  - erst nach dem Pfad-Eintrag importierbar

SVG_NS = "{http://www.w3.org/2000/svg}"
TARGET = REPO_ROOT / "web" / "pdf" / "assets" / "logo.js"

_NUMBER = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
_COMMAND = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]")
_TRANSFORM = re.compile(r"(\w+)\s*\(([^)]*)\)")


# --- Affine Matrizen: (a, b, c, d, e, f) wie in SVG und PDF --------------------
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def multiply(outer: tuple, inner: tuple) -> tuple:
    """outer * inner - erst inner anwenden, dann outer. Wie SVG schachtelt."""
    a1, b1, c1, d1, e1, f1 = outer
    a2, b2, c2, d2, e2, f2 = inner
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def apply(matrix: tuple, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    return (a * x + c * y + e, b * x + d * y + f)


def uniform_scale(matrix: tuple) -> float:
    """Laengenfaktor der Matrix - nur fuer Aehnlichkeitsabbildungen sinnvoll.

    Genau das sind alle Transformationen in diesem Logo (gleichmaessige Skalierung,
    Drehung, Verschiebung). Waere eine davon unsymmetrisch, haette eine Strichbreite
    keinen einzelnen Wert mehr, und der Abbruch hier ist besser als ein gemittelter.
    """
    a, b, c, d, _, _ = matrix
    scale_x = math.hypot(a, b)
    scale_y = math.hypot(c, d)
    if abs(scale_x - scale_y) > 1e-9 * max(scale_x, scale_y, 1.0):
        raise SystemExit(f"Ungleichmaessige Skalierung {scale_x} != {scale_y} - Strichbreite unklar.")
    return scale_x


def parse_transform(text: str | None) -> tuple:
    if not text:
        return IDENTITY
    matrix = IDENTITY
    for name, raw in _TRANSFORM.findall(text):
        values = [float(number) for number in _NUMBER.findall(raw)]
        if name == "matrix":
            step = tuple(values[:6])
        elif name == "translate":
            step = (1.0, 0.0, 0.0, 1.0, values[0], values[1] if len(values) > 1 else 0.0)
        elif name == "scale":
            scale_x = values[0]
            scale_y = values[1] if len(values) > 1 else scale_x
            step = (scale_x, 0.0, 0.0, scale_y, 0.0, 0.0)
        elif name == "rotate":
            angle = math.radians(values[0])
            cos, sin = math.cos(angle), math.sin(angle)
            step = (cos, sin, -sin, cos, 0.0, 0.0)
            if len(values) == 3:
                centre_x, centre_y = values[1], values[2]
                step = multiply(
                    (1.0, 0.0, 0.0, 1.0, centre_x, centre_y),
                    multiply(step, (1.0, 0.0, 0.0, 1.0, -centre_x, -centre_y)),
                )
        else:
            raise SystemExit(f"Unbekannte Transformation: {name}")
        matrix = multiply(matrix, step)
    return matrix


# --- Pfaddaten ------------------------------------------------------------------
def tokenize(data: str) -> list:
    """`d`-Attribut in [Befehl, Zahl, Zahl, ...] zerlegen."""
    tokens: list = []
    position = 0
    while position < len(data):
        character = data[position]
        if character in " ,\t\r\n":
            position += 1
        elif _COMMAND.match(character):
            tokens.append(character)
            position += 1
        else:
            match = _NUMBER.match(data, position)
            if match is None:
                raise SystemExit(f"Unlesbares Zeichen in d: {data[position:position + 20]!r}")
            tokens.append(float(match.group()))
            position = match.end()
    return tokens


def to_absolute_segments(data: str) -> list[list]:
    """Pfad in absolute Segmente ["M", x, y] / ["L", ...] / ["C", ...] / ["Z"]."""
    tokens = tokenize(data)
    segments: list[list] = []
    index = 0
    current = (0.0, 0.0)
    start = (0.0, 0.0)
    previous_control: tuple[float, float] | None = None
    command = ""

    def take(count: int) -> list[float]:
        nonlocal index
        values = tokens[index : index + count]
        if len(values) != count or any(isinstance(value, str) for value in values):
            raise SystemExit(f"Zu wenige Zahlen fuer {command}")
        index += count
        return values

    while index < len(tokens):
        if isinstance(tokens[index], str):
            command = tokens[index]
            index += 1
            if command in "Zz":
                segments.append(["Z"])
                current = start
                previous_control = None
                continue
        elif command in ("M", "m"):
            command = "L" if command == "M" else "l"  # implizite Wiederholung

        relative = command.islower()
        upper = command.upper()
        offset_x, offset_y = current if relative else (0.0, 0.0)

        if upper == "M":
            x, y = take(2)
            current = (x + offset_x, y + offset_y)
            start = current
            segments.append(["M", *current])
            previous_control = None
        elif upper == "L":
            x, y = take(2)
            current = (x + offset_x, y + offset_y)
            segments.append(["L", *current])
            previous_control = None
        elif upper == "H":
            (x,) = take(1)
            current = (x + offset_x, current[1])
            segments.append(["L", *current])
            previous_control = None
        elif upper == "V":
            (y,) = take(1)
            current = (current[0], y + offset_y)
            segments.append(["L", *current])
            previous_control = None
        elif upper == "C":
            x1, y1, x2, y2, x, y = take(6)
            control_1 = (x1 + offset_x, y1 + offset_y)
            control_2 = (x2 + offset_x, y2 + offset_y)
            current = (x + offset_x, y + offset_y)
            segments.append(["C", *control_1, *control_2, *current])
            previous_control = control_2
        elif upper == "S":
            x2, y2, x, y = take(4)
            reflected = (
                (2 * current[0] - previous_control[0], 2 * current[1] - previous_control[1])
                if previous_control
                else current
            )
            control_2 = (x2 + offset_x, y2 + offset_y)
            current = (x + offset_x, y + offset_y)
            segments.append(["C", *reflected, *control_2, *current])
            previous_control = control_2
        elif upper in ("Q", "T"):
            raise SystemExit("Quadratische Kurven kommen im Logo nicht vor - nicht umgesetzt.")
        elif upper == "A":
            raise SystemExit("Bogenbefehl im Logo - dieses Werkzeug naehert nichts still an.")
        else:
            raise SystemExit(f"Unbekannter Pfadbefehl: {command}")

    return segments


def transform_segments(segments: list[list], matrix: tuple) -> list[list]:
    out: list[list] = []
    for segment in segments:
        head, values = segment[0], segment[1:]
        points = [
            apply(matrix, values[i], values[i + 1]) for i in range(0, len(values), 2)
        ]
        out.append([head, *[round(value, 6) for point in points for value in point]])
    return out


# --- SVG durchlaufen ------------------------------------------------------------
def parse_style(element) -> dict[str, str]:
    style = {}
    for declaration in (element.get("style") or "").split(";"):
        name, _, value = declaration.partition(":")
        if name.strip():
            style[name.strip()] = value.strip()
    for name in ("fill", "stroke", "stroke-width", "fill-rule"):
        if element.get(name) is not None:
            style[name] = element.get(name)
    return style


def find_clip(root, reference: str | None) -> list[list] | None:
    """Die Pfadsegmente eines clip-path-Verweises, in dessen eigenem Raum."""
    if not reference:
        return None
    match = re.match(r"url\(#(.+)\)", reference.strip())
    if match is None:
        raise SystemExit(f"Unbekannter clip-path: {reference}")
    for clip in root.iter(f"{SVG_NS}clipPath"):
        if clip.get("id") != match.group(1):
            continue
        if clip.get("clipPathUnits") != "userSpaceOnUse":
            raise SystemExit("Nur clipPathUnits=userSpaceOnUse ist umgesetzt.")
        child = clip.find(f"{SVG_NS}path")
        if child is None:
            raise SystemExit("clipPath ohne <path> - nicht umgesetzt.")
        # Der Clip-Pfad traegt seine eigene Transformation; die Transformation des
        # VERWEISENDEN Elements kommt spaeter dazu, weil `transform` dort auch den
        # Clip mit verschiebt (SVG 1.1, 14.3.5).
        return transform_segments(
            to_absolute_segments(child.get("d")), parse_transform(child.get("transform"))
        )
    raise SystemExit(f"clipPath #{match.group(1)} nicht gefunden.")


def walk(root, node, matrix: tuple, operations: list) -> None:
    for child in node:
        tag = child.tag
        local = multiply(matrix, parse_transform(child.get("transform")))
        if tag == f"{SVG_NS}g":
            walk(root, child, local, operations)
        elif tag == f"{SVG_NS}path":
            style = parse_style(child)
            fill = style.get("fill", "black")
            stroke = style.get("stroke", "none")
            width = float(style.get("stroke-width", "1"))
            clip = find_clip(root, child.get("clip-path"))
            operations.append(
                {
                    "d": transform_segments(to_absolute_segments(child.get("d")), local),
                    "fill": None if fill in ("none", "") else fill,
                    "fillRule": style.get("fill-rule", "nonzero"),
                    "stroke": None if stroke in ("none", "") else stroke,
                    "strokeWidth": round(width * uniform_scale(local), 6),
                    "clip": transform_segments(clip, local) if clip else None,
                }
            )


def main() -> int:
    source = config.LOGO_INK_SVG
    tree = ElementTree.parse(source)
    root = tree.getroot()
    view_box = [float(value) for value in root.get("viewBox").split()]

    operations: list = []
    walk(root, root, IDENTITY, operations)
    if not operations:
        raise SystemExit("Keine Pfade gefunden - ist die SVG-Datei kaputt?")

    body = ",\n    ".join(json.dumps(operation, separators=(",", ":")) for operation in operations)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        f'''/**
 * logo.js - das Markenzeichen als Pfaddaten. ERZEUGT, nicht von Hand geschrieben.
 *
 * Quelle: app/static/brand/logo-dark.svg (Tinte {config.BRAND_INK}, dieselbe Datei,
 * die auch die Website benutzt). Erzeugt von tools/bake_logo_asset.py - wer die
 * SVG-Datei aendert, laesst das Werkzeug noch einmal laufen.
 *
 * Warum gebacken: im Browser gibt es kein Dateisystem und keinen SVG-Leser fuer den
 * PDF-Bau. Das Logo ist eine feste Zeichnung, keine wechselnde Eingabe - die
 * Transformationen sind deshalb schon eingerechnet, und was hier steht, sind
 * absolute Koordinaten im viewBox-Raum ({view_box[2]:.0f} x {view_box[3]:.0f}, y nach UNTEN
 * wie in SVG). Wer sie zeichnet, spiegelt y und skaliert auf die Zielgroesse.
 *
 * Vektor, kein Rasterbild (AGENTS.md): bei jeder Druckgroesse scharf.
 */

export const LOGO_VIEWBOX = {json.dumps(view_box)};

export const LOGO_OPS = [
    {body},
];
''',
        encoding="utf-8",
    )
    print(f"{TARGET.relative_to(REPO_ROOT)} geschrieben: {len(operations)} Pfade, viewBox {view_box}")
    for operation in operations:
        print(
            f"  fill={operation['fill']} stroke={operation['stroke']} "
            f"width={operation['strokeWidth']} clip={'ja' if operation['clip'] else 'nein'} "
            f"segmente={len(operation['d'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
