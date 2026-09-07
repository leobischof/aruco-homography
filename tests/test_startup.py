"""Was beim Start passiert - Portwahl, Banner, Pfade im eingefrorenen Bundle.

Diese drei Dinge fallen sonst erst am Werkstattrechner auf, und dort sieht jedes
davon aus wie "das Programm ist kaputt": ein belegter Port, eine Konsole ohne
Blockzeichen, eine .exe ohne ihre Datendateien.
"""

from __future__ import annotations

import io
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from app import config
from app.main import choose_port, print_banner

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_freier_wunschport_wird_genommen():
    """Die stabile URL ist die bessere - ausgewichen wird nur im Notfall."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((config.HOST, 0))
        free_port = probe.getsockname()[1]

    assert choose_port(free_port) == free_port


def test_belegter_port_wird_umgangen():
    """Ein belegter Port darf kein Startfehler sein, sondern ein anderer Port.

    Ohne das bricht ein Doppelklick auf die .exe mit "address already in use" ab,
    sobald irgendetwas anderes auf dem Rechner die 8000 haelt - und das sieht fuer
    den Bediener aus wie ein kaputtes Programm.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind((config.HOST, 0))
        blocker.listen(1)
        taken = blocker.getsockname()[1]

        chosen = choose_port(taken)

        assert chosen != taken
        # Und der neue Port muss wirklich frei sein, nicht bloss eine andere Zahl.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as check:
            check.bind((config.HOST, chosen))


def test_banner_ueberlebt_eine_konsole_ohne_blockzeichen(monkeypatch, capsys):
    """Der QR-Code ist Komfort - er darf den Server nicht mitreissen.

    Der Code besteht aus Blockzeichen. Schreibt Python nicht in eine
    Windows-Konsole, sondern in eine Pipe oder Datei, nimmt es die Codepage des
    Systems (cp1252), und print() bricht mit UnicodeEncodeError ab. In der
    gebauten .exe hiess das: der Server startete wegen einer Verzierung gar nicht.
    """
    with capsys.disabled():
        narrow = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
        monkeypatch.setattr(sys, "stdout", narrow)

        # Gegenprobe: dieser Datenstrom kann Blockzeichen wirklich nicht.
        with pytest.raises(UnicodeEncodeError):
            narrow.write("█")

        print_banner("http://127.0.0.1:8000", "http://192.168.0.2:8000")


def test_datendateien_folgen_dem_bundle_verzeichnis(tmp_path):
    """Eingefroren muessen alle Datenpfade unter sys._MEIPASS liegen.

    Getestet wird in einem eigenen Prozess, weil `sys._MEIPASS` VOR dem Import von
    app.config gesetzt sein muss - danach ist die Entscheidung gefallen.

    Faellt dieser Test, startet die .exe trotzdem und liefert eine nackte Seite
    ohne Schrift, ohne Logo und ohne Uebersetzung. Genau das ist der gefaehrliche
    Fall: er sieht aus wie ein Erfolg.
    """
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import sys\n"
        f"sys._MEIPASS = r'{tmp_path}'\n"
        f"sys.path.insert(0, r'{REPO_ROOT}')\n"
        "from app import config\n"
        "print(config.STATIC_DIR)\n"
        "print(config.LOCALE_DIR)\n"
        "print(config.BRAND_DIR)\n"
        "print(config.LOGO_INK_SVG)\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(probe)], capture_output=True, text=True, check=True
    )
    static, locales, brand, logo = result.stdout.split()

    assert Path(static) == tmp_path / "app" / "static"
    assert Path(locales) == tmp_path / "app" / "static" / "i18n"
    assert Path(brand) == tmp_path / "app" / "static" / "brand"
    assert Path(logo) == tmp_path / "app" / "static" / "brand" / "logo-dark.svg"


def test_ohne_bundle_zeigen_die_pfade_in_den_quellbaum():
    """Derselbe Helfer, aus dem Quellbaum heraus - und die Dateien sind wirklich da."""
    assert config.STATIC_DIR == REPO_ROOT / "app" / "static"
    assert config.LOGO_INK_SVG.exists()
    assert (config.LOCALE_DIR / "de.json").exists()
    assert (config.BRAND_DIR / "fonts" / "Montserrat-VariableFont_wght.woff2").exists()
