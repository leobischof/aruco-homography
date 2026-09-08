"""Den Browser-Bau zusammenstellen: web/index.html erzeugen, dist/web/ fuellen.

Aufruf (macht ./dev.ps1 build-web):

    python tools/build_web.py [--dist]

**web/index.html ist ERZEUGT und nicht eingecheckt.** Der Grund ist derselbe wie
beim Konstanten-Header des C++-Kerns: es waere sonst eine zweite Fassung
derselben Oberflaeche. 352 Zeilen Markup zweimal im Repo laufen auseinander, und
zwar an der Stelle, an der es niemand merkt - ein Regler, den nur eine der beiden
Fassungen hat.

Erzeugt wird aus `app/static/index.html`, und der Unterschied ist klein genug,
um ihn hier vollstaendig aufzuzaehlen:

1. **Die Betriebsart.** `window.ARUCO_TRANSPORT = "local"` vor dem Hauptskript.
   Ohne sie spraeche api.js mit einem Server, den es im Browser-Bau nicht gibt.
2. **Die Import-Karte fuer `pdf-lib`.** web/pdf/draw.js schreibt einen blossen
   Namen (`from "pdf-lib"`), und den kann ein Browser nicht aufloesen. Node
   findet ihn in node_modules; hier zeigt die Karte auf das mitgelieferte Modul.
3. **Die Pfade.** Im Serverbetrieb haengt app/static unter "/", also stimmt
   `/css/base.css`. Der Browser-Bau liegt unter /web/, und app/static daneben -
   dort muss dasselbe `../app/static/css/base.css` heissen.

Alles andere - Markup, Beschriftungen, Reihenfolge der Abschnitte - kommt
unveraendert aus der einen Vorlage.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app" / "static" / "index.html"
TARGET = ROOT / "web" / "index.html"
DIST = ROOT / "dist" / "web"

# pdf-lib schreibt web/pdf/draw.js als blossen Namen ("from \"pdf-lib\""), und
# den kann kein Browser aufloesen - die Import-Karte in der erzeugten Seite zeigt
# deshalb auf diese Kopie. Sie entsteht beim Bauen aus node_modules und ist nicht
# eingecheckt: package-lock.json nagelt die Fassung fest, und `npm ci` holt sie
# zurueck. Das wasm daneben ist eingecheckt - siehe .gitignore, warum.
PDF_LIB_SOURCE = ROOT / "node_modules" / "pdf-lib" / "dist" / "pdf-lib.esm.min.js"
PDF_LIB_TARGET = ROOT / "web" / "vendor" / "pdf-lib.esm.min.js"

# Was in den ausgelieferten Bau gehoert. Der Bau SPIEGELT den Quellbaum: dieselben
# Verzeichnisse an denselben Stellen. Das ist keine Bequemlichkeit, sondern
# Bedingung - web/pdf/i18n.js holt seine Kataloge mit "../../app/static/i18n/",
# und api.js den Ortsbetrieb mit "../../../web/vision/". Wer die Tiefe aendert,
# bricht Importe, die kein Uebersetzer prueft.
BUNDLE = [
    Path("app/static/css"),
    Path("app/static/js"),
    Path("app/static/i18n"),
    Path("app/static/brand"),
    Path("shared/constants.json"),
    Path("web/constants.js"),
    Path("web/pdf"),
    Path("web/vision"),
    Path("web/vendor"),
    Path("web/index.html"),
]

# Die Favicons liegen einzeln in app/static/ und nicht in einem Unterverzeichnis.
ICONS = ["favicon.ico", "favicon-16x16.png", "favicon-32x32.png", "apple-touch-icon.png"]

PREAMBLE = """  <!-- ERZEUGT von tools/build_web.py - nicht von Hand aendern.
       Die Vorlage ist app/static/index.html; hier stehen nur die drei
       Unterschiede des Browser-Baus (siehe den Kopf jenes Skripts). -->
  <script>
    // Kein Server. api.js rechnet in der Seite: WASM-Kern und web/pdf/.
    window.ARUCO_TRANSPORT = "local";
  </script>
  <script type="importmap">
    {"imports": {"pdf-lib": "../web/vendor/pdf-lib.esm.min.js"}}
  </script>
"""


def render(html: str) -> str:
    """Die Vorlage in die Fassung fuer /web/index.html bringen."""
    # Absolute Verweise auf app/static: /css/... -> ../app/static/css/...
    # Der Markerblatt-Verweis bleibt unberuehrt - header.js setzt ihn ohnehin neu,
    # und im Ortsbetrieb wird daraus eine Blob-URL.
    html = re.sub(
        r'((?:href|src)=")/(?!/)(?!api/)',
        r"\1../app/static/",
        html,
    )
    marker = "</head>"
    if marker not in html:
        raise SystemExit("app/static/index.html hat kein </head> - Vorlage unerwartet.")
    return html.replace(marker, PREAMBLE + marker, 1)


def build_entry() -> Path:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(render(SOURCE.read_text(encoding="utf-8")), encoding="utf-8")
    return TARGET


def copy_pdf_lib() -> Path:
    if not PDF_LIB_SOURCE.exists():
        raise SystemExit(
            f"{PDF_LIB_SOURCE.relative_to(ROOT)} fehlt - erst `npm ci` (oder `npm install`)."
        )
    PDF_LIB_TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PDF_LIB_SOURCE, PDF_LIB_TARGET)
    return PDF_LIB_TARGET


def build_dist() -> Path:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    for relative in BUNDLE:
        source = ROOT / relative
        if not source.exists():
            raise SystemExit(f"Fehlt im Quellbaum: {relative}")
        target = DIST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

    for icon in ICONS:
        source = ROOT / "app" / "static" / icon
        if source.exists():
            shutil.copy2(source, DIST / "app" / "static" / icon)

    # Ein Wegweiser an der Wurzel. Die Seite selbst liegt unter /web/, weil der
    # Bau den Quellbaum spiegelt; wer die Wurzel oeffnet, soll trotzdem ankommen.
    (DIST / "index.html").write_text(
        '<!doctype html>\n<meta charset="utf-8">\n'
        '<meta http-equiv="refresh" content="0; url=web/index.html">\n'
        '<title>ArUco-Homographie</title>\n'
        '<a href="web/index.html">ArUco-Homographie</a>\n',
        encoding="utf-8",
    )
    return DIST


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", action="store_true", help="zusaetzlich dist/web/ fuellen")
    arguments = parser.parse_args(argv)

    entry = build_entry()
    print(f"  {entry.relative_to(ROOT)} erzeugt aus {SOURCE.relative_to(ROOT)}")
    library = copy_pdf_lib()
    print(f"  {library.relative_to(ROOT)} kopiert aus node_modules/")
    if arguments.dist:
        target = build_dist()
        size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
        print(f"  {target.relative_to(ROOT)} gefuellt ({size / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
