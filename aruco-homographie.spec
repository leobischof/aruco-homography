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
"""

import os

from PyInstaller.utils.hooks import collect_data_files

# Relativ zur Spec-Datei, nicht zum Arbeitsverzeichnis: `pyinstaller` darf aus
# jedem Ordner heraus aufgerufen werden.
ROOT = SPECPATH  # noqa: F821 - von PyInstaller in den Namensraum gelegt

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

hiddenimports = [
    # svglib waehlt seine Schrift ueber reportlab.rl_config; das Modul wird nur
    # ueber einen Namen gezogen und faellt der statischen Analyse durch.
    "reportlab.rl_config",
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
    name="ArUco-Homographie",
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
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ArUco-Homographie",
)
