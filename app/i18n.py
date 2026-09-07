"""Sprachkataloge: aus einem Schluessel wird Text in der gewuenschten Sprache.

Die Kataloge liegen unter app/static/i18n/ und haben genau zwei Leser: der Browser
holt sie als statische Datei, Python liest dieselbe Datei von der Platte. Eine Datei
je Sprache, zwei Verbraucher, keine zweite Fassung - sonst laufen Oberflaeche und
PDF frueher oder spaeter auseinander.

Platzhalter heissen `{name}`. Diese Schreibweise ist bewusst gewaehlt: derselbe
Ausdruck laesst sich in JavaScript mit einer einzigen Zeile ersetzen, sodass Server
und Oberflaeche denselben Katalogtext identisch fuellen.

Ein fehlender Schluessel darf nie abbrechen: erst wird auf DEFAULT_LOCALE
ausgewichen, und fehlt er auch dort, kommt der Schluessel selbst zurueck. Damit
faellt die Luecke im Bildschirm auf, statt den Ablauf zu toeten.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache

from app import config

# Nur `{name}` wird ersetzt. Unbekannte Namen bleiben woertlich stehen - sichtbar,
# aber harmlos; ein KeyError mitten im Fehlertext waere das schlechtere Ergebnis.
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class Phrase:
    """Ein Satzbaustein, der erst beim Anzeigen uebersetzt wird.

    Gebraucht, wo ein Text einen zweiten Text einbettet und die Auswahl schon beim
    Rechnen faellt, die Sprache aber erst am Rand feststeht (Beispiel: der
    Aufloesungs-Vorschlag in "output_too_large"). Beim Rendern wird daraus ein
    gewoehnlicher String, sodass die HTTP-Antwort nur flache Werte traegt.
    """

    key: str
    params: dict[str, object] = field(default_factory=dict)


@lru_cache(maxsize=None)
def catalogue(locale: str) -> dict[str, str]:
    """Flachgeklopfter Katalog einer Sprache: "ui.header.title" -> Text.

    Verschachteltes JSON liest sich besser, die Suche braucht aber den Punktpfad.
    Das Ergebnis wird zwischengespeichert; die Dateien aendern sich zur Laufzeit nicht.
    """
    path = config.LOCALE_DIR / f"{locale}.json"
    with path.open(encoding="utf-8") as stream:
        return _flatten(json.load(stream))


def normalise(locale: str | None) -> str:
    """Auf eine unterstuetzte Sprache abbilden. None, Unsinn und "de-CH" gehen durch."""
    if not locale:
        return config.DEFAULT_LOCALE
    tag = str(locale).strip().lower().replace("_", "-")
    primary = tag.split("-")[0]
    return primary if primary in config.SUPPORTED_LOCALES else config.DEFAULT_LOCALE


def translate(key: str, locale: str, /, **params: object) -> str:
    """Text zu einem Punktschluessel, mit `{name}`-Platzhaltern gefuellt.

    Die Parameter stehen positionell vor dem `/`, damit ein Platzhalter ruhig
    "key" oder "locale" heissen darf.
    """
    text = _lookup(key, locale)
    if text is None:
        return key
    return _substitute(text, {name: _plain(value, locale) for name, value in params.items()})


def plain_params(params: dict[str, object], locale: str) -> dict[str, object]:
    """Parameter fuer die HTTP-Antwort: eingebettete Phrase-Bausteine werden Text."""
    return {name: _plain(value, locale) for name, value in params.items()}


def negotiate(accept_language: str | None) -> str:
    """Beste unterstuetzte Sprache aus einem Accept-Language-Kopf, sonst DEFAULT_LOCALE."""
    if not accept_language:
        return config.DEFAULT_LOCALE

    ranked: list[tuple[float, int, str]] = []
    for index, part in enumerate(accept_language.split(",")):
        tag, _, parameters = part.strip().partition(";")
        tag = tag.strip().lower()
        if tag:
            ranked.append((-_quality(parameters), index, tag))

    # Nach Gewicht, bei Gleichstand in der Reihenfolge des Kopfes - so gewinnt bei
    # "de,en" das zuerst genannte Deutsch.
    for _, _, tag in sorted(ranked):
        if tag == "*":
            return config.DEFAULT_LOCALE
        primary = tag.split("-")[0]
        if primary in config.SUPPORTED_LOCALES:
            return primary
    return config.DEFAULT_LOCALE


def _quality(parameters: str) -> float:
    """Das q-Gewicht eines Accept-Language-Eintrags; ohne Angabe gilt 1.0."""
    for parameter in parameters.split(";"):
        parameter = parameter.strip()
        if parameter.startswith("q="):
            try:
                return float(parameter[2:])
            except ValueError:
                return 0.0
    return 1.0


def _lookup(key: str, locale: str) -> str | None:
    """Schluessel in der Wunschsprache, sonst in der Vorgabesprache, sonst None."""
    wanted = normalise(locale)
    text = catalogue(wanted).get(key)
    if text is None and wanted != config.DEFAULT_LOCALE:
        text = catalogue(config.DEFAULT_LOCALE).get(key)
    return text


def _plain(value: object, locale: str) -> object:
    return translate(value.key, locale, **value.params) if isinstance(value, Phrase) else value


def _substitute(text: str, params: dict[str, object]) -> str:
    return _PLACEHOLDER.sub(
        lambda match: str(params[match.group(1)]) if match.group(1) in params else match.group(0),
        text,
    )


def _flatten(data: dict[str, object], prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for name, value in data.items():
        path = f"{prefix}{name}"
        if isinstance(value, dict):
            flat.update(_flatten(value, f"{path}."))
        else:
            flat[path] = str(value)
    return flat
