"""Die Sprachkataloge - hier faellt auf, was sonst erst beim Bediener auffiele.

Der wichtigste Test ist der erste: gleiche Schluesselmenge in beiden Sprachen. Ohne
ihn driften die Kataloge auseinander, und die englische Oberflaeche zeigt irgendwann
rohe Punktpfade statt Text.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app import config, i18n

APP_DIR = Path(__file__).resolve().parents[1] / "app"

# Codes werden als erstes Argument literal uebergeben; die Aufrufe stehen oft ueber
# mehrere Zeilen, deshalb das grosszuegige \s*.
_ERROR_CALL = re.compile(r'AppError\(\s*"([a-z0-9_]+)"')
_NOTICE_CALL = re.compile(r'notices\.(?:warn|info)\(\s*"([a-z0-9_]+)"')
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def flat_catalogue(locale: str) -> dict[str, str]:
    """Katalog direkt aus der Datei - nicht ueber i18n, damit der Test unabhaengig bleibt."""
    data = json.loads((config.LOCALE_DIR / f"{locale}.json").read_text(encoding="utf-8"))

    def walk(node: dict, prefix: str = "") -> dict[str, str]:
        flat: dict[str, str] = {}
        for key, value in node.items():
            path = f"{prefix}{key}"
            flat.update(walk(value, f"{path}.") if isinstance(value, dict) else {path: value})
        return flat

    return walk(data)


def codes_in_source(pattern: re.Pattern[str]) -> set[str]:
    return {
        match
        for path in APP_DIR.rglob("*.py")
        for match in pattern.findall(path.read_text(encoding="utf-8"))
    }


@pytest.fixture(scope="module")
def catalogues() -> dict[str, dict[str, str]]:
    return {locale: flat_catalogue(locale) for locale in config.SUPPORTED_LOCALES}


def test_beide_kataloge_haben_dieselben_schluessel(catalogues):
    german, english = set(catalogues["de"]), set(catalogues["en"])
    difference = sorted(german ^ english)
    assert not difference, (
        f"Kataloge driften auseinander. Nur in de: {sorted(german - english)}; "
        f"nur in en: {sorted(english - german)}"
    )


def test_platzhalter_stimmen_in_beiden_sprachen_ueberein(catalogues):
    """Ein Platzhalter, den nur eine Sprache kennt, bleibt dort roh stehen."""
    mismatches = {
        key: (sorted(set(_PLACEHOLDER.findall(catalogues["de"][key]))),
              sorted(set(_PLACEHOLDER.findall(catalogues["en"][key]))))
        for key in catalogues["de"]
        if set(_PLACEHOLDER.findall(catalogues["de"][key]))
        != set(_PLACEHOLDER.findall(catalogues["en"].get(key, "")))
    }
    assert not mismatches, f"Platzhalter unterschiedlich: {mismatches}"


def test_jeder_fehlercode_hat_einen_text(catalogues):
    missing = sorted(
        code for code in codes_in_source(_ERROR_CALL) if f"errors.{code}" not in catalogues["de"]
    )
    assert not missing, f"AppError-Codes ohne Katalogeintrag: {missing}"


def test_jeder_warncode_hat_einen_text(catalogues):
    missing = sorted(
        code for code in codes_in_source(_NOTICE_CALL) if f"notices.{code}" not in catalogues["de"]
    )
    assert not missing, f"Warncodes ohne Katalogeintrag: {missing}"


def test_die_quelle_benutzt_wirklich_alle_gefundenen_codes():
    """Absicherung des Greps selbst: findet er nichts, waeren die Tests oben leer."""
    assert len(codes_in_source(_ERROR_CALL)) >= 15
    assert len(codes_in_source(_NOTICE_CALL)) >= 5


def test_platzhalter_werden_ersetzt():
    text = i18n.translate("errors.bad_mode", "de", mode="quer")
    assert "quer" in text and "{mode}" not in text


def test_unbekannter_platzhalter_bleibt_stehen_statt_zu_werfen():
    assert "{mode}" in i18n.translate("errors.bad_mode", "de")


def test_fehlender_schluessel_kommt_als_schluessel_zurueck():
    assert i18n.translate("errors.gibt_es_nicht", "en") == "errors.gibt_es_nicht"


def test_englisch_faellt_auf_deutsch_zurueck(tmp_path, monkeypatch):
    """Ein Schluessel, den nur der deutsche Katalog kennt, darf nicht verschwinden."""
    (tmp_path / "de.json").write_text(
        json.dumps({"probe": {"nur_de": "Nur auf Deutsch", "beides": "deutsch"}}),
        encoding="utf-8",
    )
    (tmp_path / "en.json").write_text(
        json.dumps({"probe": {"beides": "english"}}), encoding="utf-8"
    )
    monkeypatch.setattr(config, "LOCALE_DIR", tmp_path)
    i18n.catalogue.cache_clear()
    try:
        assert i18n.translate("probe.beides", "en") == "english"
        assert i18n.translate("probe.nur_de", "en") == "Nur auf Deutsch"
        assert i18n.translate("probe.nirgends", "en") == "probe.nirgends"
    finally:
        i18n.catalogue.cache_clear()


@pytest.mark.parametrize(
    "header, expected",
    [
        ("de", "de"),
        ("de-DE,de;q=0.9", "de"),
        ("en-US,en;q=0.9", "en"),
        ("fr", "de"),
        ("", "de"),
        (None, "de"),
        ("fr-FR,fr;q=0.9,en;q=0.8,de;q=0.7", "en"),
        ("de;q=0.4,en;q=0.9", "en"),
        ("*", "de"),
    ],
)
def test_negotiate(header, expected):
    assert i18n.negotiate(header) == expected


@pytest.mark.parametrize("locale, expected", [(None, "de"), ("", "de"), ("EN-gb", "en"), ("kl", "de")])
def test_normalise_wirft_nie(locale, expected):
    assert i18n.normalise(locale) == expected


def test_deutsche_umlaute_stehen_wirklich_im_katalog(catalogues):
    """Der Katalog ist UTF-8. "Massstab" statt "Maßstab" waere ein Rueckfall."""
    german = catalogues["de"]
    assert german["ui.steps.params.title"] == "Maßstab"
    assert german["ui.steps.export.dpi_label"] == "Auflösung"
    assert "Markergröße" in german["ui.steps.params.marker_mm_label"]
    assert "Überlappung" in german["ui.steps.export.overlap_label"]


def test_phrase_wird_beim_rendern_zu_text():
    """Ein eingebetteter Satzbaustein darf nicht als Objekt in die Antwort geraten."""
    params = {"hint": i18n.Phrase("errors.output_too_large_hint_dpi", {"dpi": 200})}
    plain = i18n.plain_params(params, "en")
    assert plain["hint"] == "It fits at 200 dpi."
    assert isinstance(plain["hint"], str)
