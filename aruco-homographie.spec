# -*- mode: python ; coding: utf-8 -*-
"""Bauvorschrift fuer die Windows-.exe. Gebaut wird sie mit `.\\dev.ps1 build-exe`.

Warum eine Spec-Datei und keine Kommandozeile: die Liste unten ist der eigentliche
Wert dieser Arbeit. Sie steht in der Versionsverwaltung, laesst sich begruenden und
geht nicht mit dem Terminalfenster verloren, in dem sie einmal getippt wurde.

**One-Folder, nicht One-File.** One-File packt alles in die .exe und entpackt bei
JEDEM Start OpenCV, NumPy und SciPy - zusammen ueber 100 MB - in ein Temp-Verzeichnis.
Das kostet Sekunden Startzeit fuer nichts; ein Ordner mit einer .exe darin tut es auch.

**Der Pfad-Vertrag.** `app/static` wird als `app/static` ins Bundle gelegt, also unter
`_internal/app/static`. Genau diese Form erwartet `config.resource_path()`, das
`sys._MEIPASS` voranstellt. Wer hier das Ziel umbenennt, muss dort mitziehen -
sonst startet die .exe und zeigt eine nackte Seite ohne Schrift, ohne Logo und ohne
Uebersetzung. Das ist der gefaehrlichste Fehler dieses Bundles, weil er wie ein
Erfolg aussieht.

**Die Dateieigenschaften.** PyInstaller legt von sich aus KEINE Versionsressource an -
ohne den `version_info`-Block weiter unten stuende unter Rechtsklick -> Eigenschaften ->
Details nichts, kein Herausgeber und keine Fassung. Die Werte werden nicht abgetippt,
sondern aus `app/config.py` und den i18n-Katalogen gelesen.
"""

import os
import sys

from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

# Relativ zur Spec-Datei, nicht zum Arbeitsverzeichnis: `pyinstaller` darf aus
# jedem Ordner heraus aufgerufen werden.
ROOT = SPECPATH  # noqa: F821 - von PyInstaller in den Namensraum gelegt

# Marke, Fassung und Beschreibung kommen aus dem Projekt selbst, nicht aus dieser
# Datei. Diese Vorschrift laeuft als gewoehnliches Python, also wird einfach
# importiert - der kuerzeste Weg zur einen Wahrheit (AGENTS.md, Invariante 4).
sys.path.insert(0, ROOT)

from app import config, i18n  # noqa: E402 - erst nach dem sys.path-Eintrag moeglich

# Der Produktname benennt die .exe, den Ordner um sie herum und damit auch das, was
# der Installer verpackt und was in den Dateieigenschaften als Produkt erscheint.
# Er steht in app/config.py, weil ihn auch die Anwendung selbst braucht - als Titel
# ihres eigenen Fensters (AGENTS.md, Invariante 4).
APP_NAME = config.APP_NAME

# Die Beschreibung in den Dateieigenschaften ist eine sichtbare Zeichenkette, also
# kommt sie aus dem Katalog und nicht aus dem Code (AGENTS.md, Invariante 7). Es ist
# derselbe Satz, den die Kopfzeile der Oberflaeche zeigt.
_SUBTITLE_KEY = "ui.header.subtitle"
FILE_DESCRIPTION = i18n.translate(_SUBTITLE_KEY, config.DEFAULT_LOCALE)
if FILE_DESCRIPTION == _SUBTITLE_KEY:
    # translate() gibt bei fehlendem Schluessel den Schluessel zurueck. Ungebremst
    # stuende dann "ui.header.subtitle" in den Eigenschaften der ausgelieferten
    # .exe - falsch, aber an einer Stelle, an die niemand schaut. Lieber der Bau
    # bricht ab.
    raise SystemExit(f"{_SUBTITLE_KEY} fehlt in app/static/i18n/{config.DEFAULT_LOCALE}.json")

# config.BRAND_COPYRIGHT ist reines ASCII, weil es auf dem Weg zu Inno Setup ueber
# eine Kommandozeile muss (Begruendung dort). Inno ersetzt "(C)" beim Uebersetzen
# selbst durch das richtige Zeichen; hier passiert dasselbe im eigenen Prozess,
# damit auf beiden .exe wortgleich dasselbe steht. Kein Kodierungsrisiko: dieser
# Wert wird importiert, nicht durch eine Konsole gereicht.
LEGAL_COPYRIGHT = config.BRAND_COPYRIGHT.replace("(C)", "©")

# Ohne diesen Block bleiben die Dateieigenschaften der .exe LEER: PyInstaller legt
# von sich aus keine Versionsressource an. Rechtsklick -> Eigenschaften -> Details
# zeigte dann nichts, auch keinen Herausgeber.
#
# Zu beachten: `filevers`/`prodvers` sind die BINAEREN Felder und nehmen genau vier
# ganze Zahlen - "0.0.2-alpha" weist Windows ab. Deshalb dort config.APP_VERSION_TUPLE
# (0.0.2.0) und in den Zeichenkettenfeldern daneben die lesbare Fassung.
#
# Das ersetzt KEINE Signatur. SmartScreen nennt weiterhin keinen Herausgeber,
# solange die .exe nicht mit einem Zertifikat signiert ist; die Eigenschaften kann
# jeder hineinschreiben, eine Signatur nicht.
version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=config.APP_VERSION_TUPLE,
        prodvers=config.APP_VERSION_TUPLE,
        mask=0x3F,
        flags=0x0,
        OS=0x40004,      # VOS_NT_WINDOWS32
        fileType=0x1,    # VFT_APP
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                # 0407 = Deutsch, 04B0 = Unicode. Die Vorgabesprache der Anwendung.
                StringTable(
                    "040704B0",
                    [
                        StringStruct("CompanyName", config.BRAND_NAME),
                        StringStruct("ProductName", APP_NAME),
                        StringStruct("FileDescription", FILE_DESCRIPTION),
                        StringStruct("FileVersion", config.APP_VERSION),
                        StringStruct("ProductVersion", config.APP_VERSION),
                        StringStruct("LegalCopyright", LEGAL_COPYRIGHT),
                        StringStruct("InternalName", APP_NAME),
                        StringStruct("OriginalFilename", f"{APP_NAME}.exe"),
                        StringStruct("Comments", config.BRAND_URL),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [0x0407, 1200])]),
    ],
)

datas = [
    # Oberflaeche, Marke und i18n-Kataloge. KEIN Python - die statische Analyse
    # von PyInstaller sieht davon nichts.
    (os.path.join(ROOT, "app", "static"), os.path.join("app", "static")),
]

# ReportLab laedt Schriftmetriken und Type-1-Schriften erst zur Laufzeit aus dem
# eigenen Paketverzeichnis nach. Die mitgelieferten Hooks decken die Module ab
# (`reportlab.pdfbase._fontdata_*`, `reportlab.rl_settings`), die DATEIEN daneben
# aber nicht.
datas += collect_data_files("reportlab")

# pywebview spritzt beim Oeffnen des Fensters eigene JavaScript-Dateien in die
# Seite und liest sie dafuer zur Laufzeit von der Platte (`webview/js/`, ueber
# `webview.util.get_js_dir`). Der mitgelieferte Hook sammelt nur `webview/lib/`
# (die WebView2-DLLs), nicht diesen Ordner - ohne ihn stirbt der Fensterstart mit
# "Cannot find JS directory", und die gebaute .exe zeigt nur den Rueckfall auf den
# Browser. Der Quellbaum merkt davon nichts: dort liegen die Dateien einfach da.
datas += collect_data_files("webview", subdir="js")

hiddenimports = [
    # svglib waehlt seine Schrift ueber reportlab.rl_config; das Modul wird nur
    # ueber einen Namen gezogen und faellt der statischen Analyse durch.
    "reportlab.rl_config",
    # pywebview sucht sich seine Anzeige-Maschine erst zur Laufzeit aus
    # (`webview.guilib.initialize`). Unter Windows ist das WinForms, und darunter
    # Edge Chromium - beide werden nur im Rumpf einer Funktion importiert. Fehlen
    # sie, faellt das Fenster stillschweigend auf den Browser zurueck: es sieht aus
    # wie ein Rechner ohne WebView2, ist aber ein Loch in der Bauvorschrift.
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
]

# Was sicher nicht gebraucht wird. tkinter haengt ueber PIL.ImageTk mit drin und
# schleppt die ganze Tcl/Tk-Laufzeit an; pytest & Co. stehen nur in
# requirements.txt, weil dieses Repo damit geprueft wird.
excludes = [
    "tkinter",
    "matplotlib",
    "pytest",
    "_pytest",
    "pypdf",
    "pymupdf",
    "fitz",
    "PyInstaller",
    "IPython",
    "notebook",
]

a = Analysis(  # noqa: F821
    [os.path.join(ROOT, "app", "main.py")],
    # Die Projektwurzel, damit `from app import config` im Einstiegsskript
    # aufgeloest wird - PyInstaller legt von allein nur app/ auf den Pfad.
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX aus: gepackte DLLs sind der haeufigste Fehlalarm bei Defender und
    # SmartScreen, und die .exe ist ohnehin unsigniert.
    upx=False,
    console=True,  # das Startbanner mit LAN-Adresse und QR-Code gehoert gesehen
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "app", "static", "favicon.ico"),
    version=version_info,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
