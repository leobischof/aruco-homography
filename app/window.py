"""Wie sich die Oberflaeche zeigt: eigenes Fenster, Browser - oder nichts davon.

Der Regelfall ist das eigene Fenster. Ein Doppelklick soll ein Programm aufmachen
und keinen Reiter zwischen zwanzig anderen: ein Reiter geht beim Aufraeumen des
Browsers mit weg, und die Anwendung ist dann scheinbar verschwunden, obwohl der
Server noch laeuft.

Das Fenster ist eine zweite Ansicht auf denselben Server, keine andere Anwendung.
Der Server laeuft in JEDER Betriebsart unveraendert weiter und gibt LAN-Adresse und
QR-Code aus - das Handy soll das Foto auch dann liefern koennen, wenn am Rechner
ein Fenster offen steht.
"""

from __future__ import annotations

import socket
import threading
import time
import webbrowser
from collections.abc import Sequence
from typing import Literal

from app import config

# Die drei Betriebsarten. Sie stehen hier und nicht in config.py, weil sie keine
# frei gewaehlte Groesse sind, sondern das Vokabular dieses Moduls - wie die Codes
# in notices.py.
WINDOW = "window"
BROWSER = "browser"
HEADLESS = "headless"

# Dieselben drei Zeichenketten noch einmal als Typ. Aus den Werten gebaut und nicht
# abgeschrieben; Vorbild ist EMPHASIS_CHOICES in app/schemas.py.
UiMode = Literal[WINDOW, BROWSER, HEADLESS]


def choose_ui_mode(args: Sequence[str]) -> UiMode:
    """Welche Betriebsart die Kommandozeile verlangt.

    Ohne Angabe das eigene Fenster - ein Doppelklick soll ein Programm aufmachen.
    `--browser` nimmt stattdessen den Browser des Systems; das ist der Notausgang
    fuer den Rechner, auf dem das Fenster nicht taugt. `--no-browser` oeffnet gar
    nichts und laesst nur den Server laufen.

    Stehen beide Schalter da, gewinnt `--no-browser`. Seine Bedeutung ist "nichts
    aufmachen", und daran haengt die Freigabepruefung, die die Anwendung ohne jede
    Anzeige hochfaehrt: wer beides angibt, meint eher gar nichts als doch etwas.
    Diese Bedeutung darf sich nicht verschieben, auch nicht um eine Kleinigkeit.
    """
    if "--no-browser" in args:
        return HEADLESS
    if "--browser" in args:
        return BROWSER
    return WINDOW


def open_browser_when_ready(url: str, port: int) -> None:
    """Browser erst rufen, wenn der Server antwortet.

    Sofort geoeffnet zeigt der Doppelklick eine Fehlerseite, weil uvicorn noch
    startet. Der Faden ist ein Daemon - er darf das Beenden mit Strg+C nicht
    aufhalten.
    """

    def wait_and_open() -> None:
        deadline = time.monotonic() + config.BROWSER_WAIT_S
        while time.monotonic() < deadline:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.settimeout(0.5)
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    webbrowser.open(url)
                    return
            time.sleep(0.2)

    threading.Thread(target=wait_and_open, daemon=True).start()


def show(url: str) -> bool:
    """Die Oberflaeche in einem eigenen Fenster zeigen und darin bleiben, bis es zugeht.

    Rueckgabe True, wenn wirklich ein Fenster zu sehen war. False heisst "dieser
    Rechner kann keines zeigen" - dann gehoert der Browser her und kein Abbruch.
    Eine fehlende Anzeige-Maschine darf den Server nicht aufhalten: ein
    Werkstattrechner ohne WebView2-Laufzeit muss benutzbar bleiben.

    Laeuft auf dem HAUPTFADEN und kehrt erst zurueck, wenn das Fenster geschlossen
    wird - pywebview besteht auf dem Hauptfaden. Der Server laeuft daneben.
    """
    try:
        import webview
    except ImportError:
        return _fall_back("pywebview ist nicht installiert")

    try:
        # Zuerst fragen, WOMIT pywebview zeichnen wuerde. Fehlt die
        # WebView2-Laufzeit, faellt es unter Windows stillschweigend auf die alte
        # IE-Maschine zurueck, und die kennt keine ES-Module: das Fenster ginge auf
        # und bliebe leer. Ein leeres Fenster sieht aus wie ein Absturz ohne
        # Meldung - der Browser, der einfach funktioniert, ist besser.
        renderer = webview.initialize().renderer
    except Exception as error:  # was hier fliegt, haengt am Rechner, nicht am Code
        return _fall_back(f"kein Fenster moeglich ({error})")

    if renderer == "mshtml":
        return _fall_back(
            "die WebView2-Laufzeit fehlt - nachruesten mit:"
            " winget install --id Microsoft.EdgeWebView2Runtime"
        )

    try:
        webview.create_window(
            config.APP_NAME,
            url,
            width=config.WINDOW_SIZE[0],
            height=config.WINDOW_SIZE[1],
            min_size=config.WINDOW_MIN_SIZE,
            # Das Fenster soll sich verhalten wie der Browser-Reiter, den es
            # ersetzt. pywebview schaltet von sich aus die Textauswahl ab und
            # sperrt Strg+Mausrad; in einer Oberflaeche voller Zahlenfelder und
            # kleiner Messwerte will man beides haben.
            text_select=True,
            zoomable=True,
        )
        # private_mode=False, weil die Oberflaeche Sprache und Thema im
        # localStorage merkt (LOCALE_STORAGE_KEY, THEME_STORAGE_KEY). Im
        # Privatmodus finge jeder Start wieder bei der Vorgabe an - im Browser
        # tut er das nicht, und das Fenster soll sich nicht schlechter benehmen.
        webview.start(private_mode=False)
    except Exception as error:  # dito
        return _fall_back(f"das Fenster liess sich nicht oeffnen ({error})")

    return True


def _fall_back(reason: str) -> bool:
    """Sagen, warum kein Fenster kommt - und den Browser eintreten lassen.

    Die Zeile geht auf die Konsole und nicht durch den Sprachkatalog: die Konsole
    ist in diesem Programm durchgehend deutsch und unuebersetzt (siehe
    `print_banner`). Reines ASCII, aus demselben Grund wie dort.
    """
    print(f"  ({reason} - es oeffnet sich stattdessen der Browser)")
    return False
