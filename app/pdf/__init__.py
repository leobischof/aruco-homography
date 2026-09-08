"""PDF-Erzeugung: Seitengeometrie, Overlays, Bau, Markerblatt.

Hier steht ausserdem, WELCHER Bau das PDF macht - die eine Stelle, an der
`ARUCO_PDF` gelesen wird. Sowohl der Export (build.py) als auch das Markerblatt
(markersheet.py) fragen von hier; zwei Auswertungen derselben Umgebungsvariablen
waeren die Sorte Duplikat, bei der eines Tages die eine Haelfte des PDF von
ReportLab und die andere von JavaScript kaeme.
"""

from __future__ import annotations

import os

# "python" ist die Vorgabe und bleibt es: der ReportLab-Bau ist die Fassung, die am
# Messschieber geprueft wurde.
#
# "js" schaltet auf web/pdf/ um und ruft Node ueber tools/pdf_js_bridge.py auf. Das
# ist ein PRUEFSTAND, kein Auslieferungsweg (docs/cpp-migration/README.md): dieselben
# 33 Pruefungen lesen dann ein JavaScript-PDF zurueck und messen es mit demselben
# Massstab. Im Betrieb baut die Oberflaeche ihr PDF selbst, ohne diesen Umweg.
PDF_GENERATORS = ("python", "js")


def generator() -> str:
    """Der gewaehlte Bau. Ein unbekannter Wert bricht ab, statt still zurueckzufallen.

    Gelesen wird bei JEDEM Aufruf und nicht beim Import: ein Test, der die Umgebung
    setzt, soll nicht davon abhaengen, in welcher Reihenfolge Module geladen wurden.
    """
    name = os.environ.get("ARUCO_PDF", "python").strip().lower() or "python"
    if name not in PDF_GENERATORS:
        raise ValueError(
            f"ARUCO_PDF={name!r} ist unbekannt. Moeglich: {', '.join(PDF_GENERATORS)}."
        )
    return name
