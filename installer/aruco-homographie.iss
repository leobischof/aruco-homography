; Bauvorschrift fuer den Windows-Installer. Gebaut wird er mit `.\dev.ps1 build-installer`.
;
; Diese Datei ist QUELLE, kein Erzeugnis - sie steht in der Versionsverwaltung.
; Sie verpackt das fertige One-Folder-Bundle aus `dist\ArUco-Homographie\` in eine
; einzige .exe. Der Bediener bekommt damit: eine Datei, doppelklicken, fertig -
; nichts entpacken, nichts an die richtige Stelle schieben.
;
; **Der Installer ersetzt das Bundle nicht, er umhuellt es.** PyInstaller bleibt im
; One-Folder-Modus (siehe aruco-homographie.spec): One-File entpackt bei JEDEM Start
; ueber 100 MB OpenCV, NumPy und SciPy in ein Temp-Verzeichnis und kostet dafuer
; Sekunden Startzeit. Ein Installer kopiert einmal und danach nie wieder.
;
; **Es gibt keine Zahl in dieser Datei, die auch woanders steht.** Fassung, Marke und
; Adresse kommen als /D-Definitionen von `dev.ps1`, das sie aus `app/config.py` liest -
; der einzigen Stelle fuer Konstanten (AGENTS.md, Invariante 4). Inno Setup kann kein
; Python importieren, also reicht der Bauschritt sie durch. Wer diese Datei von Hand
; mit ISCC uebersetzt, bekommt darum unten eine Fehlermeldung statt stiller Vorgaben.

#ifndef AppName
  #error AppName fehlt. Diese Datei wird ueber `.\dev.ps1 build-installer` gebaut, nicht direkt mit ISCC.
#endif
#ifndef AppVersion
  #error AppVersion fehlt. Sie steht in app/config.py (APP_VERSION) und wird von dev.ps1 durchgereicht.
#endif
#ifndef AppVersionNumeric
  #error AppVersionNumeric fehlt. Sie steht in app/config.py (APP_VERSION_NUMERIC) und wird von dev.ps1 durchgereicht.
#endif
#ifndef AppCopyright
  #error AppCopyright fehlt. Er steht in app/config.py (BRAND_COPYRIGHT) und wird von dev.ps1 durchgereicht.
#endif
#ifndef AppPublisher
  #error AppPublisher fehlt. Er steht in app/config.py (BRAND_NAME) und wird von dev.ps1 durchgereicht.
#endif
#ifndef AppUrl
  #error AppUrl fehlt. Sie steht in app/config.py (BRAND_URL) und wird von dev.ps1 durchgereicht.
#endif

; Alle Pfade haengen an dieser Datei, nicht am Arbeitsverzeichnis des Aufrufers:
; SourcePath ist das Verzeichnis dieser .iss, die Projektwurzel liegt eins darueber.
#define RepoRoot ExtractFilePath(RemoveBackslash(SourcePath))
#define BundleDir RepoRoot + "dist\" + AppName
#define OutputPath RepoRoot + "dist"
#define IconFile RepoRoot + "app\static\favicon.ico"
#define AppExe AppName + ".exe"

#if !FileExists(AddBackslash(BundleDir) + AppExe)
  #error Das One-Folder-Bundle fehlt. Erst `.\dev.ps1 build-exe`, dann den Installer bauen.
#endif

[Setup]
; NIEMALS aendern. An dieser Kennung erkennt Windows eine bereits installierte
; Fassung: gleiche Kennung heisst "ersetzen", eine neue heisst "danebenstellen" -
; und dann liegen zwei Installationen mit je 290 MB auf der Platte, von denen die
; Deinstallation nur eine erwischt.
AppId={{7A4B9B15-F1A6-47B0-AB2E-70FC276227C7}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}
AppUpdatesURL={#AppUrl}

; Die Dateieigenschaften der SETUP-.exe selbst (Rechtsklick -> Eigenschaften ->
; Details) - nicht zu verwechseln mit denen der Anwendung, die aus
; aruco-homographie.spec kommen. Ohne diese Zeilen traegt das Setup zwar einen
; Herausgeber, aber keinen Urheberrechtsvermerk.
;
; `VersionInfoVersion` ist ein BINAERES Feld und nimmt nur Zahlen: "0.0.2-alpha"
; weist Windows ab. Abgeschnitten wird deshalb einmal in app/config.py
; (APP_VERSION_NUMERIC); hier kommt nur noch das Ergebnis an. Die lesbare Fassung
; steht daneben in den Textfeldern, wo sie erlaubt ist.
VersionInfoVersion={#AppVersionNumeric}
VersionInfoProductVersion={#AppVersionNumeric}
VersionInfoTextVersion={#AppVersion}
VersionInfoProductTextVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoCopyright={#AppCopyright}

; **Installation fuer den angemeldeten Benutzer, ohne Administrator.** Zwei Gruende,
; und beide zaehlen an einem Werkstattrechner:
;
; 1. Wer dort arbeitet, ist oft kein Administrator. Ein Installer, der nach einem
;    Kennwort fragt, das niemand im Raum kennt, ist kein Installer.
; 2. Der Zielpfad wird dadurch kurz UND vom Installer bestimmt. Genau das raeumt
;    den MAX_PATH-Fehler aus dem README weg: die laengste Datei im Bundle hat 101
;    Zeichen relativen Pfad, und wer das ZIP von Hand in einen tiefen
;    OneDrive-Ordner entpackte, riss damit Windows' 260-Zeichen-Grenze - die .exe
;    starb beim Start mit "DLL load failed ... Dateiname oder Erweiterung ist zu
;    lang". Kein Codefehler, sah aber wie einer aus. Hier waehlt niemand mehr
;    daneben, deshalb ist auch die Verzeichnisseite abgeschaltet.
;    (Ein Sonderfall bleibt moeglich: `Setup.exe /DIR="D:\Pfad"`.)
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#AppName}
DisableDirPage=yes
DisableProgramGroupPage=yes
; Nach der Sprache wird nur gefragt, wenn Windows keine der beiden nahelegt - siehe
; [Languages]. Eine Frage, die sich beantworten laesst, soll man nicht stellen.
ShowLanguageDialog=auto

; Der Eintrag in "Apps & Features": Name, Fassung, Symbol, und ein Deinstallierer,
; der das ganze Bundle wieder mitnimmt.
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExe}

; Das Bundle ist rund 290 MB, davon fast alles OpenCV, SciPy und NumPy. Solid
; komprimiert mit lzma2/max wird daraus ein Bruchteil - der Bau dauert dafuer laenger,
; und das ist der richtige Tausch: gebaut wird selten, geladen wird oft.
Compression=lzma2/max
SolidCompression=yes

OutputDir={#OutputPath}
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
SetupIconFile={#IconFile}
WizardStyle=modern
; Die Raeder von OpenCV, NumPy und SciPy im Bundle sind x64 - auf einem 32-Bit-Windows
; koennte das Ergebnis nur scheitern, also gar nicht erst installieren.
ArchitecturesAllowed=x64compatible

[Languages]
; Dieselben zwei Sprachen, die auch die Oberflaeche spricht (config.SUPPORTED_LOCALES).
; Deutsch zuerst, weil die Werkstatt deutsch ist. `auto` heisst: gefragt wird nur,
; wenn Windows keine der beiden Sprachen nahelegt.
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Unangehakt - so macht Windows das. Ein Programm, das sich ungefragt auf den
; Schreibtisch legt, ist eines zu viel.
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Der GANZE Baum, rekursiv - `_internal\` ist kein Beiwerk, sondern die Anwendung.
; Ohne ihn startet die .exe nicht. Deshalb hier ein Muster und keine Dateiliste:
; eine Liste veraltete mit der naechsten Abhaengigkeit, ohne dass es jemand merkte.
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Direkt unter "Programme", ohne eigenen Ordner: eine Anwendung, ein Eintrag.
; `{autoprograms}` ist bei PrivilegesRequired=lowest das Startmenue DIESES Benutzers.
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; Anbieten, nicht tun: `postinstall` setzt nur das Haekchen am Ende des Assistenten,
; `skipifsilent` haelt eine unbeaufsichtigte Installation davon ab, einen Server zu
; starten, den niemand bestellt hat.
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Der Deinstallierer entfernt von sich aus nur, was er selbst gelegt hat. Ein
; PyInstaller-Bundle kann daneben Streuner hinterlassen (Reste eines abgebrochenen
; Starts), und dann bliebe ein Ordner mit ein paar hundert Megabyte stehen. Das
; Verzeichnis gehoert allein dieser Anwendung - es darf ganz weg.
Type: filesandordirs; Name: "{app}"
