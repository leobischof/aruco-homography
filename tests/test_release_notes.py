"""Was die Werkbank aus dem Repo liest, bevor sie irgendetwas baut.

Die beiden Angaben - welche Fassung, und was in ihr steht - stehen schon im Repo.
Diese Tests halten fest, dass sie richtig herausgeholt werden: sonst erschiene
eine Fassung mit der Beschreibung einer anderen, und das faellt niemandem auf.
"""

from __future__ import annotations

import pytest

from tools import release_notes

CHANGELOG = """# Changelog

Bemerkenswerte Aenderungen.

## [0.2.0-alpha] – 2026-10-01

Der neue Abschnitt.

### Behoben

- Etwas.

## [0.1.7-alpha] – 2026-09-09

Der aeltere Abschnitt.

## [0.1.6-alpha] – 2026-09-08

Der aelteste.
"""


def test_holt_den_abschnitt_der_gefragten_fassung():
    assert "Der aeltere Abschnitt." in release_notes.extract_notes(CHANGELOG, "0.1.7-alpha")


def test_hoert_an_der_naechsten_ueberschrift_auf():
    """Sonst traegt jede Fassung die Beschreibung aller aelteren mit sich."""
    notes = release_notes.extract_notes(CHANGELOG, "0.2.0-alpha")
    assert "Der neue Abschnitt." in notes
    assert "Der aeltere Abschnitt." not in notes


def test_der_letzte_abschnitt_reicht_bis_zum_ende():
    assert release_notes.extract_notes(CHANGELOG, "0.1.6-alpha").strip() == "Der aelteste."


def test_die_ueberschrift_selbst_steht_nicht_in_der_beschreibung():
    """Die Fassungsseite nennt die Fassung schon in ihrem Titel."""
    notes = release_notes.extract_notes(CHANGELOG, "0.1.7-alpha")
    assert "0.1.7-alpha" not in notes
    assert "2026-09-09" not in notes


def test_eine_fehlende_fassung_ist_ein_fehler_und_kein_leerer_text():
    """Eine Fassung ohne Beschreibung wird nicht ausgeliefert - sie bricht ab."""
    with pytest.raises(KeyError):
        release_notes.extract_notes(CHANGELOG, "9.9.9-alpha")


def test_die_fassung_wird_woertlich_gesucht():
    """'0.1.7' darf nicht auf '0x1x7' passen - der Punkt ist ein Punkt."""
    with pytest.raises(KeyError):
        release_notes.extract_notes("## [0x1x7-alpha] – 2026-09-09\n\nFalsch.\n", "0.1.7-alpha")


def test_ast_und_import_sagen_dasselbe():
    """Der ganze Grund, warum hier geparst und nicht importiert wird.

    release_notes liest APP_VERSION mit ast, damit die Pruefaufgabe der
    Werkbank ohne OpenCV auskommt. Dieser Test ist die Zusage, dass das kein
    zweiter Wert ist, sondern ein zweiter Leser desselben.
    """
    from app import config

    assert release_notes.read_version() == config.APP_VERSION


def test_der_echte_changelog_hat_einen_abschnitt_fuer_die_echte_fassung():
    """Faellt dieser Test, wuerde release.yml den Bau abbrechen - hier faellt es frueher auf."""
    changelog = release_notes.CHANGELOG_PATH.read_text(encoding="utf-8")
    assert release_notes.extract_notes(changelog, release_notes.read_version())
