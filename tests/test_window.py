"""Welche Betriebsart die Kommandozeile waehlt - und was passiert, wenn keine geht.

Ein Fenster wirklich aufzumachen, laesst sich hier nicht pruefen: es braucht eine
Anzeige und wuerde bis zum Schliessen stehen bleiben. Die Entscheidung DAVOR laesst
sich pruefen, und sie ist der Teil, der still falsch werden kann - besonders
`--no-browser`, an dem die Freigabepruefung haengt.
"""

from __future__ import annotations

import sys
import types

from app import window


def test_ohne_argumente_kommt_das_eigene_fenster():
    """Der Doppelklick ist der Regelfall, und er soll ein Programm aufmachen."""
    assert window.choose_ui_mode([]) == window.WINDOW


def test_browser_schalter_nimmt_den_browser():
    """Der Notausgang fuer den Rechner, auf dem das Fenster nicht taugt."""
    assert window.choose_ui_mode(["--browser"]) == window.BROWSER


def test_no_browser_oeffnet_gar_nichts():
    """Weder Fenster noch Browser - daran haengt die Freigabepruefung.

    Faellt dieser Test, startet die Pruefung eine Anwendung, die auf ein Fenster
    wartet, das niemand schliesst. Die Bedeutung dieses Schalters darf sich nicht
    verschieben, auch nicht um eine Kleinigkeit.
    """
    assert window.choose_ui_mode(["--no-browser"]) == window.HEADLESS


def test_no_browser_sticht_browser():
    """Wer beides angibt, meint eher gar nichts als doch etwas."""
    assert window.choose_ui_mode(["--browser", "--no-browser"]) == window.HEADLESS
    assert window.choose_ui_mode(["--no-browser", "--browser"]) == window.HEADLESS


def test_der_port_aendert_die_betriebsart_nicht():
    """`--port` ist eine Portangabe und keine Aussage ueber die Anzeige."""
    assert window.choose_ui_mode(["--port", "8123"]) == window.WINDOW
    assert window.choose_ui_mode(["--port=8123"]) == window.WINDOW
    assert window.choose_ui_mode(["--port", "8123", "--no-browser"]) == window.HEADLESS
    assert window.choose_ui_mode(["--browser", "--port=8123"]) == window.BROWSER


def test_ohne_pywebview_tritt_der_browser_ein(monkeypatch, capsys):
    """Ein fehlendes Paket ist kein Abbruch, sondern ein Browser.

    `None` in sys.modules laesst `import webview` mit ImportError scheitern - genau
    das, was auf einem Rechner ohne pywebview passiert.
    """
    monkeypatch.setitem(sys.modules, "webview", None)

    assert window.show("http://127.0.0.1:8000") is False
    assert "Browser" in capsys.readouterr().out


def test_ohne_webview2_laufzeit_tritt_der_browser_ein(monkeypatch, capsys):
    """Die IE-Maschine ist kein Fenster, sie sieht nur aus wie eines.

    Ohne WebView2-Laufzeit faellt pywebview unter Windows stillschweigend auf
    MSHTML zurueck. Die Oberflaeche besteht aus ES-Modulen; darin bliebe das
    Fenster leer, und ein leeres Fenster sieht aus wie ein Absturz ohne Meldung.
    Geprueft wird deshalb, dass diese Maschine ABGELEHNT wird - und dass die
    Meldung sagt, was fehlt.
    """
    fake = types.SimpleNamespace(
        initialize=lambda: types.SimpleNamespace(renderer="mshtml"),
        # Wuerde show() trotzdem weitermachen, flogen diese beiden - der Test
        # bestuende dann aus dem falschen Grund. Deshalb bleiben sie weg.
    )
    monkeypatch.setitem(sys.modules, "webview", fake)

    assert window.show("http://127.0.0.1:8000") is False
    ausgabe = capsys.readouterr().out
    assert "WebView2" in ausgabe
    assert "Browser" in ausgabe


def test_eine_kaputte_anzeige_maschine_reisst_nichts_mit(monkeypatch, capsys):
    """Was pywebview beim Aufbauen wirft, haengt am Rechner - der Server bleibt.

    Der Grund gehoert in die Meldung: "es geht nicht" ohne das Warum schickt den
    Bediener auf die Suche.
    """

    def explodiert():
        raise RuntimeError("keine Anzeige vorhanden")

    monkeypatch.setitem(sys.modules, "webview", types.SimpleNamespace(initialize=explodiert))

    assert window.show("http://127.0.0.1:8000") is False
    assert "keine Anzeige vorhanden" in capsys.readouterr().out
