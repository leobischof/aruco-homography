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
    ./dev.ps1 build-markersheet  # Markerblatt-PDF nach out/ schreiben
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
# Der Port steht in app/config.py - er wird von dort GELESEN, nicht hier wiederholt.
function Get-ServerPort {
    $port = & $VenvPython -c "from app import config; print(config.PORT)"
    if ($LASTEXITCODE -ne 0 -or -not $port) { throw 'Port konnte nicht aus app/config.py gelesen werden.' }
    return [int]$port.Trim()
}

# Wartet im Hintergrund, bis der Port antwortet, und oeffnet dann den Browser.
# So oeffnet sich nie eine Fehlerseite, weil der Server noch nicht bereit war.
function Start-BrowserWhenReady {
    param([string]$Url, [int]$Port)
    Start-Job -ScriptBlock {
        param($JobUrl, $JobPort)
        for ($attempt = 0; $attempt -lt 75; $attempt++) {
            try {
                $client = New-Object System.Net.Sockets.TcpClient
                $client.Connect('127.0.0.1', $JobPort)
                $client.Close()
                Start-Process $JobUrl
                return
            } catch {
                Start-Sleep -Milliseconds 400
            }
        }
    } -ArgumentList $Url, $Port | Out-Null
}

function Invoke-StartServer {
    Confirm-Deps

    $port = Get-ServerPort
    $localUrl = "http://127.0.0.1:$port"

    Write-Step 'Starting the ArUco-Homographie server'
    Write-Host ''
    Write-Ok   "Weboberflaeche: $localUrl"
    Write-Host '     Der Browser oeffnet sich gleich von selbst.' -ForegroundColor DarkGray
    Write-Host '     Die Netzwerk-Adresse fuers Handy (samt QR-Code) gibt der Server unten aus.' -ForegroundColor DarkGray
    Write-Host '     Beenden mit Strg+C.' -ForegroundColor DarkGray
    Write-Host ''

    if ($Rest -notcontains '--no-browser') { Start-BrowserWhenReady -Url $localUrl -Port $port }

    $serverArgs = @($Rest | Where-Object { $_ -ne '--no-browser' })
    Invoke-Native -What 'start-server' -Action { & $VenvPython -m app.main @serverArgs }
}

function Invoke-RunTests {
    Confirm-Deps
    Write-Step 'Running tests'
    Invoke-Native -What 'run-tests' -Action { & $VenvPython -m pytest -q @Rest }
}

function Invoke-BuildMarkersheet {
    Confirm-Deps
    Write-Step 'Building the A4 marker sheet PDF'
    Invoke-Native -What 'build-markersheet' -Action { & $VenvPython -m app.pdf.markersheet @Rest }
}

# Stop only servers started FROM THIS REPOSITORY - never someone else's python.
function Invoke-KillServers {
    Write-Step 'Stopping servers started from this repository'
    $needle = $RepoRoot.ToLowerInvariant()
    $killed = 0
    foreach ($proc in (Get-CimInstance Win32_Process -Filter "Name = 'python.exe'")) {
        $cmd = $proc.CommandLine
        if ($cmd -and $cmd.ToLowerInvariant().Contains($needle) -and $cmd.Contains('app.main')) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
            $killed = $killed + 1
        }
    }
    if ($killed -eq 0) { Write-Ok 'No running server found' } else { Write-Ok "Stopped $killed server process(es)" }
}

function Invoke-CleanAll {
    Write-Step 'Removing venv, outputs and caches'
    foreach ($path in @('venv', 'out', '.pytest_cache')) {
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
    Write-Cmd 'start-server'      'Webserver starten, Browser oeffnen, LAN-URL + QR ausgeben (--no-browser moeglich)'
    Write-Cmd 'run-tests'         'Testsuite ausfuehren (pytest)'
    Write-Cmd 'build-markersheet' 'A4-Markerblatt nach out/markerblatt_A4.pdf schreiben'
    Write-Cmd 'kill-servers'      'Aus diesem Repo gestartete Server beenden'
    Write-Cmd 'clean-all'         'venv, out/ und Caches entfernen'
    Write-Cmd 'help'              'Diese Hilfe anzeigen'
    Write-Host ''
}

# --- Dispatcher (keep entries in sync with the functions above) --------------
switch ($Command.ToLowerInvariant()) {
    'install-deps'      { Invoke-InstallDeps }
    'start-server'      { Invoke-StartServer }
    'run-tests'         { Invoke-RunTests }
    'build-markersheet' { Invoke-BuildMarkersheet }
    'kill-servers'      { Invoke-KillServers }
    'clean-all'         { Invoke-CleanAll }
    'help'              { Show-Help }
    default             { Write-Err "Unknown command: $Command"; Show-Help; exit 1 }
}
