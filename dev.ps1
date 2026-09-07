#Requires -Version 5.1
<#
.SYNOPSIS
    Single source of truth for this repository's developer commands.

.DESCRIPTION
    Self-healing command dispatcher. Every run/test command verifies that the venv
    and its dependencies are present and installs them automatically if not, so a
    fresh clone runs with zero manual steps:  ./dev.ps1 start-server

    This script is the ONLY place project commands are defined. .vscode/tasks.json
    calls into it and never duplicates command logic.

.EXAMPLE
    ./dev.ps1 install-deps       # venv anlegen und Abhaengigkeiten installieren
    ./dev.ps1 start-server       # Server starten (installiert bei Bedarf vorher)
    ./dev.ps1 run-tests          # Testsuite ausfuehren
    ./dev.ps1 build-core         # C++-Rechenkern bauen
    ./dev.ps1 run-tests-cpp      # dieselbe Testsuite gegen den C++-Kern
    ./dev.ps1 build-markersheet  # Markerblatt-PDF nach out/ schreiben
    ./dev.ps1 build-exe          # Windows-.exe nach dist/ bauen
    ./dev.ps1 build-installer    # Windows-Installer (eine Datei) nach dist/ bauen
    ./dev.ps1 help               # alle Kommandos auflisten
#>

[CmdletBinding()]
param(
    # The command to run (see Show-Help for the list).
    [Parameter(Position = 0)]
    [string]$Command = 'help',

    # Remaining args forwarded to the underlying tool (e.g. ./dev.ps1 run-tests -- -k name).
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Splatting a $null array fails under StrictMode - normalise once, here.
if ($null -eq $Rest) { $Rest = @() }

# Operate from the repo root (this script's directory) regardless of caller CWD.
$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot

$VenvPython   = Join-Path $RepoRoot 'venv\Scripts\python.exe'
$Requirements = Join-Path $RepoRoot 'requirements.txt'
$DepsStamp    = Join-Path $RepoRoot 'venv\.deps-installed'
$ExeSpec      = Join-Path $RepoRoot 'aruco-homographie.spec'
$DistDir      = Join-Path $RepoRoot 'dist'
$ExeDist      = Join-Path $DistDir 'ArUco-Homographie'
$IssScript    = Join-Path $RepoRoot 'installer\aruco-homographie.iss'
$CoreDir      = Join-Path $RepoRoot 'core'
$CoreBuildDir = Join-Path $CoreDir 'build'

# Der Ordnername des Bundles IST der Name der .exe und der Name, unter dem der
# Installer die Anwendung kennt. Festgelegt wird er in aruco-homographie.spec
# (EXE/COLLECT name); hier wird er abgeleitet und nicht ein zweites Mal getippt.
$AppName      = Split-Path $ExeDist -Leaf
$ExePath      = Join-Path $ExeDist "$AppName.exe"

# --- Logging gateway (single source of truth for output formatting) ----------
function Write-Step { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Message) Write-Host "[ok] $Message" -ForegroundColor Green }
function Write-Warn { param([string]$Message) Write-Host "[!]  $Message" -ForegroundColor Yellow }
function Write-Err  { param([string]$Message) Write-Host "[x]  $Message" -ForegroundColor Red }

# Run a native command and fail loudly on a non-zero exit code, so failures
# propagate to CI and editor tasks instead of being swallowed.
function Invoke-Native {
    param(
        [Parameter(Mandatory)][scriptblock]$Action,
        [string]$What = 'command'
    )
    # Many CLIs write progress to stderr; under 'Stop' that becomes a terminating
    # error even on exit 0. Relax, and treat the EXIT CODE as the truth.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Action
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($LASTEXITCODE -ne 0) { throw "$What failed (exit $LASTEXITCODE)." }
}

# --- Dependency self-healing -------------------------------------------------

# The stamp records WHICH requirements.txt was installed, so editing that file
# re-triggers an install instead of silently running against stale packages.
function Get-RequirementsHash {
    return (Get-FileHash -Path $Requirements -Algorithm SHA256).Hash
}

function Test-DepsInstalled {
    if (-not (Test-Path $VenvPython)) { return $false }
    if (-not (Test-Path $DepsStamp))  { return $false }
    return ((Get-Content $DepsStamp -Raw).Trim() -eq (Get-RequirementsHash))
}

function Invoke-InstallDeps {
    Write-Step 'Installing dependencies into venv'
    if (-not (Test-Path $VenvPython)) {
        Invoke-Native -What 'python -m venv' -Action { python -m venv (Join-Path $RepoRoot 'venv') }
    }
    Invoke-Native -What 'pip upgrade' -Action { & $VenvPython -m pip install --upgrade pip }
    Invoke-Native -What 'pip install' -Action { & $VenvPython -m pip install -r $Requirements }
    Set-Content -Path $DepsStamp -Value (Get-RequirementsHash) -Encoding utf8
    Write-Ok 'Dependencies installed'
}

# Self-healing guard: every run/test command calls this first.
function Confirm-Deps {
    if (-not (Test-DepsInstalled)) {
        Write-Warn 'Dependencies missing or requirements.txt changed - installing now'
        Invoke-InstallDeps
    }
}

# --- Commands ----------------------------------------------------------------
# Port, Fassung und Marke stehen in app/config.py - sie werden von dort GELESEN,
# nicht hier wiederholt (AGENTS.md, Invariante 4). Ein zweiter Wert in diesem Skript
# oder in der .iss waere die Sorte Duplikat, die still veraltet.
function Get-ConfigValue {
    param([Parameter(Mandatory)][string]$Name)
    $value = & $VenvPython -c "from app import config; print(config.$Name)"
    if ($LASTEXITCODE -ne 0 -or -not $value) { throw "$Name konnte nicht aus app/config.py gelesen werden." }
    return $value.Trim()
}

function Get-ServerPort { return [int](Get-ConfigValue 'PORT') }

function Invoke-StartServer {
    Confirm-Deps

    Write-Step 'Starting the ArUco-Homographie server'
    Write-Host ''
    Write-Ok   ("Bevorzugter Port: {0} - ist er belegt, weicht der Server aus." -f (Get-ServerPort))
    Write-Host '     Die tatsaechliche Adresse, die Netzwerk-Adresse fuers Handy und den' -ForegroundColor DarkGray
    Write-Host '     QR-Code gibt der Server unten aus; die Oberflaeche geht in einem' -ForegroundColor DarkGray
    Write-Host '     eigenen Fenster auf (--browser nimmt stattdessen den Browser).' -ForegroundColor DarkGray
    Write-Host '     Beenden: Fenster schliessen oder Strg+C.' -ForegroundColor DarkGray
    Write-Host ''

    # Fenster oder Browser macht app.main selbst auf - erst dort steht fest, welcher
    # Port es geworden ist. Von hier aus geoeffnet traefe die URL daneben, sobald der
    # bevorzugte Port belegt war. --browser und --no-browser werden durchgereicht,
    # nicht abgefangen.
    Invoke-Native -What 'start-server' -Action { & $VenvPython -m app.main @Rest }
}

function Invoke-RunTests {
    Confirm-Deps
    Write-Step 'Running tests'
    Invoke-Native -What 'run-tests' -Action { & $VenvPython -m pytest -q @Rest }
}

# --- C++-Rechenkern -----------------------------------------------------------
# Warum das hier so umstaendlich aussieht: weder MSVC noch CMake stehen auf dem
# PATH, und vcvars64.bat ist eine BATCHdatei - sie setzt Dutzende Variablen im
# eigenen Prozess, und PowerShell kann sie nicht einlesen. Deshalb wird der ganze
# Bau in ein Wegwerf-.cmd geschrieben und einmal durch cmd.exe geschickt. Das ist
# haesslicher als ein Aufruf, aber es ist EIN Aufruf, und man kann die Datei im
# Fehlerfall ansehen.

function Find-VcInstall {
    if ($env:ARUCO_VS_INSTALL) {
        if (-not (Test-Path (Join-Path $env:ARUCO_VS_INSTALL 'VC\Auxiliary\Build\vcvars64.bat'))) {
            throw "ARUCO_VS_INSTALL zeigt auf keine Installation mit C++-Werkzeugen: $env:ARUCO_VS_INSTALL"
        }
        return $env:ARUCO_VS_INSTALL
    }

    # vswhere ist der offizielle Weg und liegt seit VS 2017 immer hier. Ein fest
    # verdrahteter Pfad auf "18\BuildTools" funktionierte auf genau einem Rechner.
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (Test-Path $vswhere) {
        $found = & $vswhere -latest -products * `
            -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
            -property installationPath
        if ($found) { return ($found | Select-Object -First 1) }
    }

    throw (@(
        'Keine Visual-Studio-Installation mit C++-Werkzeugen gefunden.',
        '     Gebraucht werden die Build Tools (MSVC + CMake + Ninja).',
        '     Eine bestimmte Installation waehlen:  $env:ARUCO_VS_INSTALL = "<pfad>"'
    ) -join [Environment]::NewLine)
}

function Find-OpenCVDir {
    # Das SDK gehoert NICHT ins Repo (rund 1 GB) und liegt deshalb daneben.
    $candidates = @()
    if ($env:OpenCV_DIR) { $candidates += $env:OpenCV_DIR }
    $candidates += Join-Path (Split-Path $RepoRoot -Parent) '_toolchain\opencv\build'

    foreach ($candidate in $candidates) {
        if (Test-Path (Join-Path $candidate 'OpenCVConfig.cmake')) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw (@(
        'Das OpenCV-SDK wurde nicht gefunden (OpenCVConfig.cmake).',
        '     Gesucht wurde in $env:OpenCV_DIR und unter:',
        ("       {0}" -f (Join-Path (Split-Path $RepoRoot -Parent) '_toolchain\opencv\build'))
    ) -join [Environment]::NewLine)
}

function Invoke-BuildCore {
    Confirm-Deps

    $install = Find-VcInstall
    $vcvars  = Join-Path $install 'VC\Auxiliary\Build\vcvars64.bat'
    $cmake   = Join-Path $install 'Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
    $ninja   = Join-Path $install 'Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe'
    foreach ($tool in @($vcvars, $cmake, $ninja)) {
        if (-not (Test-Path $tool)) { throw "Werkzeug fehlt in $install : $tool" }
    }

    $opencv = Find-OpenCVDir
    # Erst einsammeln, dann die erste Zeile nehmen. NICHT ueber `Select-Object
    # -First 1` in der Pipe: das bricht den Aufruf ab, und $LASTEXITCODE meldet
    # danach einen Fehlschlag, den es nie gab.
    $pybindOutput = & $VenvPython -m pybind11 --cmakedir
    if ($LASTEXITCODE -ne 0 -or -not $pybindOutput) { throw 'pybind11 nicht im venv gefunden.' }
    $pybind = ([string[]]$pybindOutput)[0].Trim()

    Write-Step 'Building the C++ core (CMake + Ninja + MSVC)'
    Write-Host ("     Werkzeugkette: {0}" -f $install)   -ForegroundColor DarkGray
    Write-Host ("     OpenCV:        {0}" -f $opencv)    -ForegroundColor DarkGray

    $script = Join-Path ([IO.Path]::GetTempPath()) ("aruco-build-core-{0}.cmd" -f [guid]::NewGuid())
    # OEM und nicht ASCII: cmd.exe liest Batchdateien in der OEM-Codepage. Steht
    # ein Sonderzeichen im Pfad - ein Benutzername mit Umlaut reicht -, machte
    # ASCII daraus ein Fragezeichen und der Bau suchte an der falschen Stelle.
    Set-Content -Path $script -Encoding OEM -Value @(
        '@echo off',
        ('call "{0}" >nul || exit /b 1' -f $vcvars),
        ('"{0}" -S "{1}" -B "{2}" -G Ninja -DCMAKE_MAKE_PROGRAM="{3}" -DCMAKE_BUILD_TYPE=Release -DOpenCV_DIR="{4}" -Dpybind11_DIR="{5}" -DPython_EXECUTABLE="{6}" || exit /b 1' -f
            $cmake, $CoreDir, $CoreBuildDir, $ninja, $opencv, $pybind, $VenvPython),
        ('"{0}" --build "{1}" || exit /b 1' -f $cmake, $CoreBuildDir)
    )
    try {
        Invoke-Native -What 'build-core' -Action { & cmd.exe /c $script }
    } finally {
        Remove-Item $script -Force -ErrorAction SilentlyContinue
    }

    Write-Ok "Fertig: $CoreBuildDir"
}

# Die Testsuite gegen den C++-Kern. Es gibt bewusst keine zweite Suite - zwei
# Suiten driften genauso wie zwei Implementierungen, nur unbemerkt
# (docs/cpp-migration/README.md). Davor laeuft der C++-Pruefstand gegen
# shared/fixtures/: er misst gegen die Grundwahrheit, nicht gegen Python.
function Invoke-RunTestsCpp {
    Invoke-BuildCore

    Write-Step 'Running the C++ conformance program against shared/fixtures/'
    $conformance = Join-Path $CoreBuildDir 'aruco_conformance.exe'
    $pack        = Join-Path $CoreBuildDir 'fixtures\fixtures.txt'
    Invoke-Native -What 'conformance' -Action { & $conformance $pack }

    Write-Step 'Running tests with ARUCO_CORE=cpp'
    $previous = $env:ARUCO_CORE
    $env:ARUCO_CORE = 'cpp'
    try {
        Invoke-Native -What 'run-tests-cpp' -Action { & $VenvPython -m pytest -q @Rest }
    } finally {
        if ($null -eq $previous) { Remove-Item Env:\ARUCO_CORE -ErrorAction SilentlyContinue }
        else { $env:ARUCO_CORE = $previous }
    }
}

function Invoke-BuildMarkersheet {
    Confirm-Deps
    Write-Step 'Building the A4 marker sheet PDF'
    Invoke-Native -What 'build-markersheet' -Action { & $VenvPython -m app.pdf.markersheet @Rest }
}

# Baut die Windows-.exe. Was mitmuss und warum, steht in aruco-homographie.spec -
# hier wird sie nur aufgerufen, damit der Bau genauso selbstheilend ist wie jedes
# andere Kommando. Zusatzargumente gehen an PyInstaller (z. B. --clean).
function Invoke-BuildExe {
    # Vorgabe sind die Argumente der Kommandozeile - ausser der Aufrufer ist
    # build-installer: dessen Zusatzargumente gehoeren ISCC und nicht PyInstaller.
    param([string[]]$ExtraArgs = $Rest)

    Confirm-Deps
    Write-Step 'Building the Windows .exe (PyInstaller, one-folder)'
    Invoke-Native -What 'build-exe' -Action {
        & $VenvPython -m PyInstaller --noconfirm $ExeSpec @ExtraArgs
    }

    # PyInstaller meldet auch dann Erfolg, wenn nur Warnungen kamen - also
    # nachsehen, ob die .exe wirklich dort liegt.
    if (-not (Test-Path $ExePath)) { throw "PyInstaller lief durch, aber $ExePath fehlt." }

    $bytes = (Get-ChildItem -Path $ExeDist -Recurse -File | Measure-Object -Property Length -Sum).Sum
    Write-Ok "Fertig: $ExePath"
    Write-Host ("     {0:N0} MB in {1}" -f ($bytes / 1MB), $ExeDist) -ForegroundColor DarkGray
    Write-Host '     Weitergegeben wird der GANZE Ordner, nicht nur die .exe darin.' -ForegroundColor DarkGray
    Write-Host '     Eine Datei zum Weitergeben macht ./dev.ps1 build-installer daraus.' -ForegroundColor DarkGray
}

# --- Installer ----------------------------------------------------------------

# Ist das Bundle noch das, was der Quellcode beschreibt? Verglichen wird die .exe
# gegen alles, was in sie hineingeht. Ohne diese Frage tuetete der Installer
# klaglos eine alte Fassung ein - und das faellt erst am Zielrechner auf.
function Test-BundleFresh {
    if (-not (Test-Path $ExePath)) { return $false }
    $built = (Get-Item $ExePath).LastWriteTimeUtc

    # shared/ gehoert dazu, seit die Produktkonstanten dort stehen und mit ins
    # Bundle gelegt werden. Ohne diese Zeile gaelte ein Bundle als frisch, obwohl
    # eine geaenderte Millimeterzahl noch gar nicht darin ist - genau die stille
    # Sorte Drift, gegen die shared/ ueberhaupt angelegt wurde.
    $sources = @(Get-ChildItem -Path (Join-Path $RepoRoot 'app'), (Join-Path $RepoRoot 'shared') -Recurse -File |
        Where-Object { $_.FullName -notlike '*__pycache__*' })
    $sources += Get-Item $ExeSpec
    $newest = ($sources | Measure-Object -Property LastWriteTimeUtc -Maximum).Maximum

    return ($newest -le $built)
}

# ISCC.exe SUCHEN statt einen Pfad festzuschreiben. Inno Setup laesst sich pro
# Benutzer oder fuer alle installieren, und nur die zweite Form landet unter
# "Program Files" - ein fest verdrahteter Pfad funktionierte auf genau einem
# Rechner, dem, auf dem er getippt wurde.
function Find-InnoCompiler {
    $onPath = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }

    $candidates = @()
    # Die Installation pro Benutzer kommt zuerst: sie braucht keine Adminrechte und
    # ist deshalb die wahrscheinlichere. Sie steht in KEINEM PATH.
    if ($env:LOCALAPPDATA)        { $candidates += Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe' }
    if (${env:ProgramFiles(x86)}) { $candidates += Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe' }
    if ($env:ProgramFiles)        { $candidates += Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe' }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return $candidate }
    }

    throw (@(
        'Inno Setup wurde nicht gefunden (ISCC.exe).',
        '     Installieren mit:  winget install --id JRSoftware.InnoSetup',
        '     Gesucht wurde im PATH und unter:',
        '       %LOCALAPPDATA%\Programs\Inno Setup 6\',
        '       %ProgramFiles(x86)%\Inno Setup 6\',
        '       %ProgramFiles%\Inno Setup 6\'
    ) -join [Environment]::NewLine)
}

# Baut den Windows-Installer aus dem One-Folder-Bundle. Was hineinkommt und warum,
# steht in installer/aruco-homographie.iss; hier wird nur der Uebersetzer gesucht,
# das Bundle sichergestellt und die Marke aus app/config.py durchgereicht.
# Zusatzargumente gehen an ISCC (z. B. /Q fuer einen stillen Lauf).
function Invoke-BuildInstaller {
    Confirm-Deps
    $compiler = Find-InnoCompiler

    if (-not (Test-BundleFresh)) {
        Write-Warn 'Bundle fehlt oder ist aelter als app/ - es wird zuerst neu gebaut'
        Invoke-BuildExe -ExtraArgs @()
    }

    # Alle Werte VOR dem Aufruf holen: Get-ConfigValue startet Python und setzt dabei
    # $LASTEXITCODE, an dem Invoke-Native den Erfolg von ISCC ablesen will.
    $version   = Get-ConfigValue 'APP_VERSION'
    $numeric   = Get-ConfigValue 'APP_VERSION_NUMERIC'
    $publisher = Get-ConfigValue 'BRAND_NAME'
    $url       = Get-ConfigValue 'BRAND_URL'
    $copyright = Get-ConfigValue 'BRAND_COPYRIGHT'

    Write-Step "Building the Windows installer (Inno Setup, $AppName $version)"
    Write-Host ("     Compiler: {0}" -f $compiler) -ForegroundColor DarkGray

    Invoke-Native -What 'build-installer' -Action {
        & $compiler `
            "/DAppName=$AppName" `
            "/DAppVersion=$version" `
            "/DAppVersionNumeric=$numeric" `
            "/DAppPublisher=$publisher" `
            "/DAppUrl=$url" `
            "/DAppCopyright=$copyright" `
            $IssScript @Rest
    }

    $setupPath = Join-Path $DistDir "$AppName-Setup-$version.exe"
    if (-not (Test-Path $setupPath)) { throw "ISCC lief durch, aber $setupPath fehlt." }

    $bytes = (Get-Item $setupPath).Length
    Write-Ok "Fertig: $setupPath"
    Write-Host ("     {0:N0} MB - eine Datei. Doppelklicken, fertig; nichts zu entpacken." -f ($bytes / 1MB)) -ForegroundColor DarkGray
    Write-Host ("     Installiert wird ohne Adminrechte nach %LOCALAPPDATA%\Programs\{0}\." -f $AppName) -ForegroundColor DarkGray
}

# Stop only servers started FROM THIS REPOSITORY - never someone else's python.
# Zwei Gestalten desselben Servers: aus dem venv (python.exe -m app.main) und als
# gebaute .exe aus dist/. Beide tragen den Repo-Pfad in der Kommandozeile, und nur
# darueber werden sie erkannt.
function Invoke-KillServers {
    Write-Step 'Stopping servers started from this repository'
    $needle = $RepoRoot.ToLowerInvariant()
    $killed = 0
    foreach ($proc in (Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'ArUco-Homographie.exe'")) {
        $cmd = $proc.CommandLine
        if (-not $cmd) { continue }
        $lower = $cmd.ToLowerInvariant()
        if (-not $lower.Contains($needle)) { continue }
        if ($lower.Contains('app.main') -or $lower.Contains('aruco-homographie.exe')) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
            $killed = $killed + 1
        }
    }
    if ($killed -eq 0) { Write-Ok 'No running server found' } else { Write-Ok "Stopped $killed server process(es)" }
}

function Invoke-CleanAll {
    Write-Step 'Removing venv, outputs and caches'
    foreach ($path in @('venv', 'out', 'build', 'dist', '.pytest_cache', 'coreuild')) {
        $full = Join-Path $RepoRoot $path
        if (Test-Path $full) { Remove-Item -Recurse -Force $full }
    }
    Get-ChildItem -Path $RepoRoot -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-Item -Recurse -Force $_.FullName }
    Write-Ok 'Clean complete'
}

# --- Help --------------------------------------------------------------------
function Write-Cmd { param([string]$Name, [string]$Subtitle)
    Write-Host ("  {0}" -f $Name) -ForegroundColor White
    Write-Host ("      {0}" -f $Subtitle) -ForegroundColor DarkGray
}
function Show-Help {
    Write-Host ''
    Write-Host 'dev.ps1 - ArUco-Homographie command dispatcher' -ForegroundColor White
    Write-Host 'Usage: ./dev.ps1 <command> [args...]' -ForegroundColor DarkGray
    Write-Host ''
    Write-Cmd 'install-deps'      'venv anlegen und requirements.txt installieren'
    Write-Cmd 'start-server'      'Server starten, Oberflaeche im eigenen Fenster zeigen, LAN-URL + QR ausgeben (--browser | --no-browser)'
    Write-Cmd 'run-tests'         'Testsuite ausfuehren (pytest, Python-Kern)'
    Write-Cmd 'build-core'        'C++-Rechenkern nach core/build/ bauen (CMake + MSVC + OpenCV-SDK)'
    Write-Cmd 'run-tests-cpp'     'C++-Pruefstand und DIESELBE Testsuite gegen den C++-Kern (ARUCO_CORE=cpp)'
    Write-Cmd 'build-markersheet' 'A4-Markerblatt nach out/markerblatt_A4.pdf schreiben'
    Write-Cmd 'build-exe'         'Windows-.exe nach dist/ArUco-Homographie/ bauen (ohne Python lauffaehig)'
    Write-Cmd 'build-installer'   'Windows-Installer nach dist/ bauen - eine Datei, ohne Adminrechte installierbar'
    Write-Cmd 'kill-servers'      'Aus diesem Repo gestartete Server beenden'
    Write-Cmd 'clean-all'         'venv, out/, build/, dist/ und Caches entfernen'
    Write-Cmd 'help'              'Diese Hilfe anzeigen'
    Write-Host ''
}

# --- Dispatcher (keep entries in sync with the functions above) --------------
switch ($Command.ToLowerInvariant()) {
    'install-deps'      { Invoke-InstallDeps }
    'start-server'      { Invoke-StartServer }
    'run-tests'         { Invoke-RunTests }
    'build-core'        { Invoke-BuildCore }
    'run-tests-cpp'     { Invoke-RunTestsCpp }
    'build-markersheet' { Invoke-BuildMarkersheet }
    'build-exe'         { Invoke-BuildExe }
    'build-installer'   { Invoke-BuildInstaller }
    'kill-servers'      { Invoke-KillServers }
    'clean-all'         { Invoke-CleanAll }
    'help'              { Show-Help }
    default             { Write-Err "Unknown command: $Command"; Show-Help; exit 1 }
}
