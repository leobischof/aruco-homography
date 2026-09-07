# Changelog

Bemerkenswerte Änderungen an diesem Projekt. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach
[SemVer](https://semver.org/lang/de/).

## [0.0.3-alpha] – 2026-09-08

**Die erste Fassung, die keine Vorabversion mehr ist** — und die erste, an der ein Messschieber
war. Dazu bekommt das Programm ein eigenes Fenster.

### Am Papier nachgemessen

**Der gedruckte 100-mm-Kontrollmaßstab misst 100 mm. Das 50-mm-Raster misst 50 mm.** Nachgemessen
am 07.09.2026 mit dem Messschieber an einem echten Ausdruck. Seit dem ersten Tag stand in jeder
Fassung dieses Protokolls derselbe Vorbehalt — „belegt nur gegen synthetische Szenen, der Beweis
am Papier steht aus". Er steht nicht mehr aus.

**Was damit belegt ist: `PDF → Drucker → Papier`.** Die Seitengeometrie stimmt, und der Drucker
skaliert nicht. Das war eine der beiden Hälften, an denen dieses Werkzeug scheitern konnte, und
sie ist zu.

**Was damit nicht belegt ist: `Foto → Marker → Millimeter`.** Und das gehört genauso deutlich
hierher, denn der Unterschied ist nicht offensichtlich: Maßstab und Raster zeichnet die
PDF-Schicht aus **denselben** Millimeterzahlen, in denen der Zuschnitt angegeben ist. Läge die
Homographie daneben, käme die Schablone falsch groß heraus — und Maßstab und Raster mäßen darauf
trotzdem tadellos. Sie können diesen Fehler nicht sehen.

Was ihn sähe: einen Gegenstand **bekannter** Länge mit aufs Foto legen, die Schablone drucken und
**diesen Gegenstand** auf dem Ausdruck nachmessen. Das steht weiter aus.

Deshalb bleibt `alpha` im Namen, obwohl diese Fassung **nicht mehr als Vorabversion**
veröffentlicht wird: geprüft genug, um sie zu benutzen, nicht geprüft genug, um sich das Messen
am fertigen Teil zu sparen.

### Das Programm bekommt ein eigenes Fenster Bis hierher öffnete ein Doppelklick den
Standardbrowser: die Anwendung war ein Reiter zwischen zwanzig anderen, wurde beim Aufräumen des
Browsers mitgeschlossen und sah dann verschwunden aus, obwohl ihr Server weiterlief. Ein Fenster
mit eigenem Namen in der Taskleiste ist ein Programm. Am Rechenweg ändert sich **nichts** — es
ist dieselbe Oberfläche auf demselben Server, nur in einem anderen Rahmen.

### Hinzugefügt

- **Ein eigenes Fenster (pywebview) als Vorgabe.** Ein Doppelklick auf die `.exe` öffnet die
  Anwendung in einem Fenster von 1200 × 860 Punkt, das nicht kleiner als 900 × 600 gezogen
  werden kann. Die Breite ist nicht geraten: der Inhalt der Oberfläche ist auf 68 rem begrenzt
  und braucht mit seinen Rändern rund 1136 Punkt — darüber gewönne man nichts mehr. Beide Maße
  stehen in `app/config.py` (Invariante 4), der Fenstertitel ist der Produktname, der jetzt
  ebenfalls dort steht und nicht mehr an drei Stellen getippt wird.

  **Der Server bleibt, was er war.** Er läuft weiter, gibt weiter LAN-Adresse und QR-Code aus,
  und das Handy erreicht ihn weiter, während das Fenster offen steht. Das Fenster ist eine
  *zweite Ansicht* auf denselben Server, keine zweite Anwendung — und das ist der Punkt, denn
  das Foto kommt vom Handy.

  Zwei Kleinigkeiten, die pywebview anders vorgibt, sind ausdrücklich zurückgestellt: Textauswahl
  bleibt erlaubt und Strg+Mausrad zoomt weiter. Das Fenster soll sich verhalten wie der
  Browser-Reiter, den es ersetzt, und in einer Oberfläche voller Zahlenfelder und kleiner
  Messwerte will man beides haben. Aus demselben Grund läuft es **nicht** im Privatmodus: die
  gewählte Sprache und das gewählte Thema stehen im `localStorage`, und die sollen den nächsten
  Start überleben.
- **`--browser` als Notausgang.** Nimmt statt des Fensters den Browser des Systems — das
  bisherige Verhalten, für den Rechner, auf dem das Fenster nicht taugt.

### Geändert

- **`--no-browser` heißt weiterhin „gar nichts aufmachen"** — weder Fenster noch Browser, nur
  der Server. Die Bedeutung ist absichtlich unverändert geblieben: die Freigabeprüfung fährt die
  Anwendung damit ohne Anzeige hoch, und ein Schalter, der plötzlich ein Fenster öffnete, ließe
  sie auf ein Fenster warten, das niemand schließt. Stehen `--browser` und `--no-browser`
  zusammen da, gewinnt `--no-browser`.
- **`.\dev.ps1 start-server` sagt jetzt das Richtige** und reicht beide Schalter durch.

### Sicherheitsnetz

- **Kein Fenster ist kein Abbruch.** Fehlt pywebview, fehlt die WebView2-Laufzeit (Windows 10
  ohne Nachinstallation) oder wirft die Anzeige-Maschine beim Aufbauen, dann sagt das Programm
  in **einer** Zeile, was fehlt, und öffnet den Browser. Der Server startet in jedem dieser Fälle
  trotzdem — ein Werkstattrechner ohne WebView2 bleibt vom Handy aus voll benutzbar.

  Der heikelste dieser Fälle ist der stille: **ohne WebView2-Laufzeit fällt pywebview unter
  Windows wortlos auf die alte IE-Maschine zurück.** Die kennt keine ES-Module, und die
  Oberfläche besteht aus welchen — das Fenster ginge auf und bliebe leer. Ein leeres Fenster
  sieht aus wie ein Absturz ohne Meldung. Deshalb wird vor dem Öffnen gefragt, *womit* gezeichnet
  würde, und MSHTML ausdrücklich abgelehnt; die Meldung nennt den winget-Befehl, der die
  Laufzeit nachrüstet. `tests/test_window.py` hält beides fest.

### Geprüft

`.\dev.ps1 run-tests`: **161 grün** (153 vorher, acht neue in `tests/test_window.py`).

Das Fenster wurde nicht behauptet, sondern **gesehen** — aus dem Quellbaum und, was allein zählt,
aus der gebauten `.exe`: Fenstertitel `ArUco-Homographie`, Rahmen 1200 × 860, darin die
vollständige Oberfläche mit Kopfzeile, Schritt 1 und Markenstreifen. Der Bau brauchte dafür zwei
Zeilen in `aruco-homographie.spec`: die Anzeige-Module von pywebview als `hiddenimports` (sie
werden erst zur Laufzeit über einen Namen gezogen) und `webview/js` als Datendateien — der
mitgelieferte PyInstaller-Hook sammelt nur `webview/lib`, und ohne die JavaScript-Dateien stirbt
der Fensterstart mit „Cannot find JS directory". Im Quellbaum fällt das nicht auf; es fällt erst
an der ausgelieferten `.exe` auf.

Ebenfalls an der gebauten `.exe` gemessen: `--no-browser` startet **ohne Fenster und ohne
Browser** und beantwortet HTTP; bei offenem Fenster antwortet die **LAN-Adresse** und liefert ein
Markerblatt-PDF; `--browser` ruft den Browser und öffnet kein Fenster.

**Was damit nicht bewiesen ist:** der Rückfall auf den Browser auf einem Rechner, dem die
WebView2-Laufzeit wirklich fehlt. Dieser Rechner hat sie (v152), also ist dieser Weg nur im Test
belegt, nicht am echten Windows 10.

## [0.0.2-alpha] – 2026-09-07

**Die Fassung, die einen richtigen Installer mitbringt.** 0.0.1-alpha kam als ZIP, das man selbst
auspacken musste — und zwar an eine Stelle, die nicht zu tief liegen durfte, sonst starb das
Programm beim Start an Windows' 260-Zeichen-Grenze. Hier gibt es stattdessen **eine Datei**:
doppelklicken, durchklicken, fertig. Am Rechenweg hat sich **nichts** geändert; die Millimeter
kommen aus demselben Code wie vorher.

### Hinzugefügt

- **Ein Windows-Installer — eine Datei, nichts zu entpacken.** `.\dev.ps1 build-installer` baut
  mit Inno Setup `dist\ArUco-Homographie-Setup-<Fassung>.exe`: **rund 78 MB** statt eines
  114-MB-ZIPs, das man erst auspacken muss und dabei auch noch an der richtigen Stelle.
  (Auf die Byte genau steht die Zahl hier bewusst nicht: zwei Bauläufe aus demselben Quellstand
  ergaben 81 780 869 und 81 786 796 Byte. PyInstaller schreibt Zeitstempel ins Bundle, und was
  sich nicht wiederholen lässt, gehört nicht als genaue Zahl in ein Änderungsprotokoll.)
  Doppelklicken, durchklicken, fertig — Startmenü-Eintrag, wahlweise ein Schreibtischsymbol
  (unangehakt, wie es Windows macht) und ein Deinstallierer in *Apps & Features*.

  Installiert wird **ohne Administratorrechte** für den angemeldeten Benutzer nach
  `%LOCALAPPDATA%\Programs\ArUco-Homographie`. Zwei Gründe, und beide zählen an einem
  Werkstattrechner: wer dort sitzt, ist oft kein Administrator — und weil jetzt der *Installer*
  den Zielpfad wählt und nicht der Benutzer beim Entpacken, **ist die MAX_PATH-Falle für diesen
  Weg weg**. Das war der Fehler, der wie ein Codefehler aussah und keiner war: ein zu tiefer
  OneDrive-Ordner riss Windows' 260-Zeichen-Grenze, und die `.exe` starb beim Start mit
  „DLL load failed … Dateiname oder Erweiterung ist zu lang".

  **Das Bundle bleibt One-Folder.** Der Installer ersetzt es nicht, er umhüllt es. One-File
  entpackte weiterhin bei jedem Start über 100 MB OpenCV, NumPy und SciPy in ein
  Temp-Verzeichnis und kostete dafür Sekunden Startzeit — der Installer kopiert einmal.

  Die Bauvorschrift `installer/aruco-homographie.iss` ist versioniert, denn sie ist Quelltext.
  Sie enthält **keine** Fassungsnummer und keine Markenzeichenkette: `dev.ps1` liest beides aus
  `app/config.py` und reicht es als `/D`-Definition hinein. Die `AppId` ist eine feste GUID und
  darf nie geändert werden — sonst stellte die nächste Fassung sich daneben, statt zu ersetzen,
  und es lägen zwei Bundles à 290 MB auf der Platte. `ISCC.exe` wird gesucht statt
  festgeschrieben (`PATH`, Installation pro Benutzer, beide `Program Files`); fehlt sie, nennt
  die Meldung `winget install --id JRSoftware.InnoSetup`.

  Der ZIP-Weg (`.\dev.ps1 build-exe`, ganzer Ordner) bleibt dokumentiert — für Rechner, auf
  denen nichts installiert werden darf.
- **Die `.exe` sagt jetzt, von wem sie ist.** Rechtsklick → Eigenschaften → Details war bei der
  Anwendung **vollständig leer** — PyInstaller legt von sich aus keine Versionsressource an, und
  ohne die steht dort kein Herausgeber, keine Fassung, gar nichts. `aruco-homographie.spec` legt
  sie nun an: `CompanyName` (Bischof Snowboards), `ProductName`, `FileDescription`,
  `FileVersion`, `ProductVersion`, `LegalCopyright`, dazu `InternalName`, `OriginalFilename` und
  die Adresse als `Comments`. Die Setup-`.exe` trug Herausgeber und Produkt schon, aber **keinen
  Urheberrechtsvermerk**; die `VersionInfo*`-Anweisungen in der `.iss` setzen jetzt alle vier
  ausdrücklich, statt sich auf Inno-Vorgaben zu verlassen.

  Nichts davon ist abgetippt: die Vorschrift importiert `app/config.py` (sie ist selbst Python),
  die `.iss` bekommt die Werte wie gehabt als `/D`-Definitionen. Die **Beschreibung** kommt aus
  dem i18n-Katalog — es ist derselbe Satz, den die Kopfzeile der Oberfläche zeigt, denn eine
  sichtbare Zeichenkette gehört in den Katalog (Invariante 7). Fehlt der Schlüssel, **bricht der
  Bau ab**, statt „ui.header.subtitle" in die Eigenschaften der ausgelieferten `.exe` zu schreiben.

  Der Urheberrechtsvermerk steht in `config.py` als reines ASCII (`Copyright (C) …`), weil er
  auf dem Weg zu Inno Setup durch zwei Konsolen-Stationen muss und ein Sonderzeichen dort von
  der Codepage abhinge. Gemessen: auf diesem Rechner steht die Konsole zufällig auf UTF-8 und
  es ginge gut — auf cp850, der Vorgabe, würde aus dem Zeichen lautlos ein anderes. Sichtbar
  wird trotzdem das richtige Zeichen: Inno ersetzt `(C)` von sich aus (nachgemessen), und die
  Bauvorschrift tut im eigenen Prozess dasselbe. Auf beiden `.exe` steht derselbe Text.

  **Das ersetzt keine Signatur.** SmartScreen zeigt weiterhin *Unbekannter Herausgeber*:
  Dateieigenschaften kann jeder hineinschreiben, und Windows weiß das. Dagegen hilft nur ein
  Code-Signing-Zertifikat.
- **`APP_VERSION` in `app/config.py`.** Die Fassungsnummer stand bisher nirgends im Code, nur in
  dieser Datei und im Git-Tag. Jetzt hat sie eine Stelle, und zwar die für Konstanten vorgesehene
  (AGENTS.md, Invariante 4). `dev.ps1` liest sie von dort, wie es den Port schon las. Daneben
  `APP_VERSION_TUPLE`/`APP_VERSION_NUMERIC` (`0.0.2.0`) und `BRAND_COPYRIGHT`. Die binären
  Versionsfelder von Windows nehmen nur vier ganze Zahlen und weisen `0.0.2-alpha` ab —
  abgeschnitten wird deshalb **einmal**, in `config.py`; Bauvorschrift und Installer nehmen beide
  dieses Ergebnis, statt die Regel jeder für sich zu erfinden.
- **`--port N` beim Start.** Verschiebt den *Wunsch*-Port; ausgewichen wird danach wie immer.
  Gebraucht, sobald eine zweite Kopie danebenlaufen soll — etwa, wenn eine frisch installierte
  Fassung neben dem Entwicklungsserver geprüft wird. Ein unbrauchbarer Wert bricht nicht ab,
  sondern fällt auf `config.PORT` zurück: ein Doppelklick, der an einem Komfortargument
  scheitert, wäre schlechter als einer auf dem Vorgabeport.

### Geprüft

Der Installer wurde nicht nur gebaut, sondern **still installiert, gestartet, benutzt und wieder
entfernt**: 287 Dateien / 292 MB landeten unter `%LOCALAPPDATA%\Programs\ArUco-Homographie`, die
installierte Fassung lieferte Oberfläche, Themen-Tokens, `main.js` und beide Sprachkataloge aus,
gab ein echtes Markerblatt-PDF heraus und fuhr eine vollständige synthetische Szene durch Upload,
Entzerrung (RMS 0,093 px) und Export (210,000 × 178,000 mm, eine Seite). Danach war nach der
stillen Deinstallation weder das Verzeichnis noch die Verknüpfung noch der Eintrag in
*Apps & Features* übrig.

Die Dateieigenschaften wurden an **beiden** gebauten `.exe` zurückgelesen. Sie stimmen überein:
Herausgeber `Bischof Snowboards`, Produkt `ArUco-Homographie`, Fassung `0.0.2-alpha`, binär
`0.0.2.0`, `Copyright © Bischof Snowboards`.

**Was damit nicht bewiesen ist:** die Maßhaltigkeit am Papier. Sie ist weiterhin ausschließlich
gegen synthetische Szenen belegt, und geprüft wurde auf **diesem** Rechner, nicht auf einem
fremden ohne Python.

## [0.0.1-alpha] – 2026-09-07

**Die erste veröffentlichte Fassung.** Inhaltlich ist das der Stand von 0.3.0 — neue
Funktionen kommen hier keine dazu. Die Nummern 0.1.0 bis 0.3.0 darunter sind
Entwicklungsschritte, zu denen es nie ein veröffentlichtes Erzeugnis und keinen Tag gab;
die Zählung der *Veröffentlichungen* fängt deshalb bei 0.0.1 neu an, statt eine Herkunft
vorzutäuschen, die es nicht gibt.

**Warum `alpha`:** weil die zentrale Zusage dieses Projekts noch offen ist. Die
Maßhaltigkeit ist bis heute **ausschließlich gegen synthetische Szenen** belegt — eine
virtuelle Kamera, gerenderte Marker, bekannte Grundwahrheit. Der Beweis am echten
Ausdruck steht aus: drucken, mit dem Messschieber nachmessen, das Ergebnis festhalten.
Bis das passiert ist, gilt: **jede Schablone vor dem Sägen am aufgedruckten
100-mm-Maßstab nachmessen.**

### Beigelegt

`ArUco-Homographie-v0.0.1-alpha-win64.zip` — das One-Folder-Bundle für Windows x64.
Entpacken, `ArUco-Homographie.exe` doppelklicken; auf dem Zielrechner muss **kein Python**
installiert sein. Es wird der **ganze Ordner** gebraucht, nicht nur die `.exe` darin.

Zwei bekannte Grenzen, beide keine Codefehler, beide sehen aber wie welche aus: der
Zielordner darf nicht zu tief liegen (Windows' 260-Zeichen-Grenze, siehe README), und die
`.exe` ist nicht signiert, weshalb SmartScreen beim ersten Start warnt.

## [0.3.0] – 2026-09-07

Der Tag, an dem die Oberfläche zweisprachig, umschaltbar hell/dunkel, auf dem Handy
bedienbar und um eine Bildaufbereitung reicher wurde. Am Rechenweg hat sich **nichts**
geändert: die Homographie wird nach wie vor am unberührten Foto gemessen.

### Hinzugefügt

- **Deutsch und Englisch aus einem Katalog.** Jede sichtbare Zeichenkette kommt aus
  `app/static/i18n/`, einer Datei je Sprache — dieselben Dateien für den Browser, für die
  Warnungen und Fehler des Servers und für den PDF-Aufdruck. Keine zweite Fassung, kein
  Nachpflegen an drei Stellen. Warnungen und Fehler tragen jetzt einen Code plus Parameter
  statt eines fertigen Satzes; der Satz entsteht erst am Rand. 184 Schlüssel je Sprache, und
  `tests/test_i18n.py` besteht darauf, dass die Schlüsselmengen gleich bleiben, dass jeder
  Platzhalter auf beiden Seiten existiert und dass jeder in `app/` erhobene Code auch einen
  Text hat.
- **Sprachumschalter in der Kopfzeile.** Der Wechsel rendert die Seite ohne Neuladen, schreibt
  `<html lang>` und `document.title` um und schickt `Accept-Language` an jede Anfrage, damit
  Servermeldungen der App folgen und nicht dem Browser.
- **Der Ausdruck folgt der gewählten Sprache.** `ExportRequest` hat ein `locale`-Feld, über
  `i18n.normalise` normalisiert — ein Export scheitert niemals an einer Sprachangabe, er
  kommt dann eben in der Vorgabesprache. Das Markerblatt nimmt die Sprache als `?locale=`
  entgegen, weil ein einfacher Anker keine Kopfzeile mitschicken kann.
- **Helles und dunkles Thema**, mit einer Schaltfläche in der Kopfzeile. Es gibt **drei**
  Zustände: ausdrücklich hell, ausdrücklich dunkel, und gar keine gespeicherte Wahl — dann
  gilt die Systemvorgabe, auch wenn sie mitten in der Sitzung umschaltet. Die Tokennamen
  stammen aus `snow-service-free`, damit die Werkzeuge des Hauses dieselbe Sprache sprechen.
- **Bildaufbereitung vor dem Druck** (`app/vision/enhance.py`): Schwarzweiß, Negativ,
  Helligkeit, Kontrast, Sättigung, lokaler Kontrast (CLAHE), Kantenanhebung, aufgelegte
  Kantenzeichnung, Farbbetonung und Schwelle. Live-Vorschau über `POST /api/adjust`, dieselben
  Regler im Export.
  **Sie greift ausschließlich am bereits entzerrten Bild an, nie vor der Markererkennung** —
  ein Schärferegler vor dem Detektor würde die Markerecken und damit die Millimeter
  verschieben. `tests/test_enhance.py` misst die Subpixel-Lage einer Kante vor und nach jedem
  einzelnen Eingriff: Schwarzweiß, Schwelle und Kantenanhebung verschieben sie um exakt
  0,000000 px; der lokale Kontrast um 0,11 px, weil CLAHE die Flanke kachelweise kippt — bei
  300 dpi sind das 0,009 mm.
- **Das Zuschnitt-Rechteck lässt sich endlich ändern.** Acht Griffe (vier Ecken, vier
  Kantenmitten), Ziehen im Inneren verschiebt, Ziehen auf freier Fläche zieht wie bisher ein
  neues auf, Pfeiltasten schieben um 1 mm und mit Shift um 10 mm. Vorher gab es genau eine
  Geste: neu aufziehen.
- **Bedienbar auf dem Handy.** Eine Spalte, Berührungsziele von mindestens 44 px, kein
  waagerechter Überlauf bei 360 und 390 px Breite, und die Zuschnittfläche bleibt benutzbar.
  Das Handy, das das Foto gemacht hat, kann damit den ganzen Ablauf über die LAN-Adresse
  fahren.
- **[`docs/plans.md`](docs/plans.md)**: die Vorhaben, an denen niemand arbeitet, die aber
  gebaut werden sollen — Windows-`.exe`, Android-`.apk`, ein geteilter Rechenkern, DXF-Export
  für die Fräse. Mit Weg, bekannten Stolpersteinen und offenen Fragen, damit sie nicht bei
  jedem Gespräch neu hergeleitet werden.
- **[`docs/design/design-system.md`](docs/design/design-system.md)** und
  [`docs/design/README.md`](docs/design/README.md): das Designsystem des Hauses und seine
  Herkunft, samt der drei Tokens, die gegenüber `free` bewusst korrigiert sind, weil sie dort
  auf ihrem eigenen Untergrund unsichtbar wären.
- **[`docs/contributing/git.md`](docs/contributing/git.md)**: die verbindlichen Git-Regeln,
  einmal aufgeschrieben statt in drei Fassungen verstreut.
- **[`docs/README.md`](docs/README.md)**: das Inhaltsverzeichnis der Dokumentation. Jede Datei
  unter `docs/` mit Zweck, Zielgruppe und Stand — und ein YAML-Frontmatter-Schema, an dem ein
  Skript den Baum aufzählen und prüfen kann.

- **Auslieferung als Windows-`.exe`.** `.\dev.ps1 build-exe` baut mit PyInstaller ein
  One-Folder-Bundle nach `dist/ArUco-Homographie/`. Doppelklick startet den Server und
  öffnet den Browser; Python muss auf dem Rechner nicht installiert sein. Weitergegeben
  wird der ganze Ordner, nicht nur die `.exe` darin. Bewusst **nicht** One-File: das
  entpackt bei jedem Start OpenCV, NumPy und SciPy in ein Temp-Verzeichnis und kostet
  Sekunden Startzeit für nichts.
- **`aruco-homographie.spec`** — die Bauvorschrift ist versioniert, nicht eine
  Kommandozeile, die mit dem Terminalfenster verlorengeht. Sie trägt, was die statische
  Analyse von PyInstaller nicht findet: den ganzen Baum `app/static/**` und die
  Datendateien von ReportLab.
- **`config.resource_path()`** löst jeden Pfad auf eine mitgelieferte Datei auf —
  `sys._MEIPASS` im Bundle, `app/` im Quellbaum. Ohne den Helfer startet die `.exe` und
  liefert eine nackte Seite ohne Schrift, ohne Logo und ohne Übersetzung: der gefährliche
  Fehler, weil er wie ein Erfolg aussieht.
- `tests/test_startup.py` prüft die drei Dinge, die sonst erst am Werkstattrechner
  auffallen: Ausweichen auf einen freien Port, ein Banner, das eine Konsole ohne
  Blockzeichen überlebt, und Datenpfade, die dem Bundle folgen.
- VS-Code-Task **„Build Windows .exe"** — ruft wie alle Tasks nur `dev.ps1` auf.

### Geändert

- **Die Vorgabe des Exports ist die Kachelung auf A4 mit Klebeplan**, nicht mehr die
  Einzelseite. Eine Schablone in Originalgröße passt auf keinen Drucker, den hier jemand hat;
  die alte Vorgabe erzeugte also verlässlich etwas Undruckbares und musste vor jedem Gebrauch
  von Hand korrigiert werden. Der Wert steht in `config.LAYOUT_DEFAULT`. Bewusst **nicht**
  mitgezogen wurde `ExportOptions` in der PDF-Schicht: dort ist „eine Seite" der schlichte
  Fall und Kachelung eine Betriebsart, die ein Aufrufer verlangt.
- **Die Oberfläche ist auf Design-Token und i18n-Schlüssel neu gebaut.** Aus einer
  388-Zeilen-`app.js` und einem nur dunklen Stylesheet mit handgeschriebenen Farben wurden
  ES-Module über HTTP, ohne Build-Schritt: `i18n`, `theme`, `api`, `header`, `crop-geometry`,
  `crop-rect`, `crop-info`, `adjust`, `report`, `main` — das Stylesheet entlang derselben
  Linien geteilt. Jede Farbe, jeder Radius und jeder Abstand kommt aus `tokens.css`; im neuen
  CSS steht kein einziges Farbliteral.
- **Committen braucht keine Rückfrage mehr, Pushen immer.** Die Erlaubnisse sind bewusst
  asymmetrisch: ein Commit ist örtlich und umkehrbar, ein Push ist sofort öffentlich. Fertig
  **und geprüft** ist nicht die Erlaubnis zu committen, sondern der Auslöser. Diese Regel
  weicht bewusst von der globalen Fassung in `~/.claude/CLAUDE.md` ab.
- **Testartefakte und Screenshots bleiben aus dem Verzeichnisbaum.** Die Regeln sind an die
  Projektwurzel geheftet, damit ein pauschales `*.png` nicht die Favicons und Logos unter
  `app/static/` verschluckt; `.vscode/` ist ausgeschlossen, `.vscode/tasks.json` ausdrücklich
  wieder hereingeholt, weil die Tasks zum Projekt gehören.

- **`config.PORT` ist jetzt der *bevorzugte* Port, keine Zusage.** Ist 8000 belegt — auf
  einem Werkstattrechner eine Frage der Zeit —, weicht der Server auf einen freien aus,
  statt mit „address already in use" abzubrechen. Die stabile URL bleibt der Normalfall.
- **Den Browser öffnet `app.main` selbst**, nicht mehr `dev.ps1`. Erst dort steht fest,
  welcher Port es geworden ist; eine vorher gebaute URL wäre nach dem Ausweichen falsch.
  `--no-browser` wird jetzt an den Server durchgereicht statt vom Skript abgefangen.
- **`opencv-python` → `opencv-python-headless`.** Die Anwendung öffnet nie ein
  `cv2`-Fenster. `cv2.aruco` ist im Headless-Rad vollständig enthalten (geprüft:
  `ArucoDetector`, `getPredefinedDictionary`, `generateImageMarker`,
  `CORNER_REFINE_SUBPIX`, Erzeugen-und-Wiedererkennen, gesamte Testsuite). Anders als in
  `docs/plans.md` vermutet spart das unter Windows **nicht** 60–80 MB: die
  OpenCV-5-Räder für Windows bringen gar kein Qt mit, gemessener Unterschied 0,42 MB.
- `kill-servers` beendet auch die gebaute `.exe` aus diesem Verzeichnis, nicht nur
  `python -m app.main`. `clean-all` räumt zusätzlich `build/` und `dist/`.

### Behoben

- **Der Hinweis am Zuschnitt nannte eine Farbe, die es nicht mehr gibt** („grüne Fläche"). Die
  Marker-Hülle leitet ihre Füllung seit dem Umzug auf die Token aus `--primary` ab und ist
  petrol. Ein Satz, der in einer Oberfläche mit zwei Themen auf eine Farbe zeigt, veraltet mit
  der nächsten Nachjustierung — der neue Text benennt die Fläche statt ihrer Farbe. Er ist
  zugleich das `aria-label` der Zeichenfläche.
- **Das Overlay der Zuschnittfläche ignorierte `devicePixelRatio`** und war auf jedem Handy
  und jedem HiDPI-Schirm weichgezeichnet — ausgerechnet über einer Schnittkante.
- **Die Farben des Overlays waren fest verdrahtet** und konnten dem Thema nicht folgen. Ein
  Canvas löst `var()` nicht auf; die Tokens werden jetzt mit `getComputedStyle` gelesen und
  bei jedem Themenwechsel neu.
- **Der Cache-Buster der Vorschau hatte Sekundenauflösung.** Ein Regler überschreibt dieselbe
  Datei mehrmals je Sekunde, der Browser bekam also dieselbe URL und hätte ein veraltetes Bild
  gezeigt. Jetzt in Millisekunden.

- **Der ASCII-QR-Code riss den Start mit, wenn die Ausgabe kein Unicode konnte.** Der Code
  besteht aus Blockzeichen; schreibt Python nicht in eine Windows-Konsole, sondern in eine
  Pipe oder Datei, nimmt es die Codepage des Systems (cp1252) und `print()` bricht mit
  `UnicodeEncodeError` ab. In der `.exe` hieß das: der Server startete wegen einer
  Verzierung gar nicht erst. Jetzt kommt an dieser Stelle ein Hinweis, und der Server läuft.

### Bekannte Grenze

- Der Bundle-Ordner darf nicht zu tief liegen: die längste enthaltene Datei hat 101
  Zeichen relativen Pfad, ab etwa 157 Zeichen Zielordner reißt Windows'
  260-Zeichen-Grenze und die `.exe` bricht beim Start mit „DLL load failed … Der
  Dateiname oder die Erweiterung ist zu lang" ab. Kein Codefehler — sieht aber wie einer aus.

### Weiterhin offen

- **Die Maßhaltigkeit ist nach wie vor nur gegen synthetische Szenen belegt.** Der Beweis am
  echten Ausdruck — drucken, den 100-mm-Maßstab mit dem Messschieber nachmessen, das Ergebnis
  aufschreiben — steht weiter aus. Von allem, was dieses Projekt noch vorhat, ist das das
  Wichtigste; es steht als erster Punkt in [`docs/plans.md`](docs/plans.md), Abschnitt 5.
- Objektivverzeichnung unkorrigiert, gewölbte Objekte prinzipiell nicht möglich, Sitzungen nur
  im Arbeitsspeicher — unverändert gegenüber 0.1.0.

## [0.2.0] – 2026-09-06

### Hinzugefügt

- **Markenzeichen auf jedem Blatt.** Logo und „Made with Bischof Snowboards Software"
  stehen im Streifen unter dem Bild — auf der Einzelseite, auf *jeder* Kachel, auf dem
  Klebeplan und auf dem Markerblatt. Das Logo wird als Vektor aus der Original-SVG des
  Webprojekts eingebettet, nicht als Rasterbild, und ist damit bei jeder Druckgröße
  scharf.
- **Markenblock im PDF verlinkt** auf bischof-snowboards.com; in der Oberfläche führen
  Logo, Markenzeile und Fußzeile auf dieselbe Adresse.
- **Markenfarben und Montserrat** in der Oberfläche. Die Farbtokens stammen aus
  `snow-service-free/src/main.css`, dort in oklch notiert, hier als sRGB in
  `app/config.py`. Gegenprobe: `--foreground oklch(0.3717 0.0392 257.29)` ergibt
  `#334155`, exakt die Tinte, die `logo-dark.svg` im Dateikommentar nennt.
- **Originales Favicon** aus dem Webprojekt statt einer Nachbildung.
- `tests/test_branding.py`: prüft über die PDF-Textextraktion, dass **keine** Seite ohne
  Herkunftszeile herauskommt, und über die Link-Annotationen, dass der Markenblock
  verlinkt ist.
- `test_markersheet.py` rastert das erzeugte Markerblatt und schickt es durch den echten
  Detektor. Ein vertauschtes oder gespiegeltes Modulraster sähe auf dem Bildschirm normal
  aus und fiele sonst erst am realen Foto auf. Gemessen: Kante 66,98 mm, Abstände
  121,00 × 170,99 mm.

### Geändert

- **Das Raster ist kräftiger und auf hellem wie dunklem Untergrund lesbar.** Jede Linie
  wird zweimal gezogen: erst ein breiter weißer Saum, dann die Kernlinie in Markentinte.
  Auf Weiß verschwindet der Saum, auf Schwarz trägt er die Linie. Die Beschriftungen
  sitzen auf weißem Träger und werden in den Bildbereich hineingeklemmt.
- **Der Streifen unter dem Bild ist jetzt immer da**, auch wenn Maßstab und Fußzeile
  abgeschaltet sind — er trägt das Markenzeichen. Damit ist eine Seite nie mehr exakt so
  groß wie das Objekt; das **Bild** belegt aber unverändert exakt `crop_w × crop_h`
  Millimeter, und nur das war je die Zusage.

## [0.1.0] – 2026-09-06

Erste Fassung: Handyfoto rein, maßhaltiges PDF in Originalgröße raus.

### Hinzugefügt

- **Homographie in zwei Modi.** Blatt-Modus mit bekanntem Layout; Frei-Modus, der
  Homographie und Markerpositionen gemeinsam schätzt (8 + 2(n−1) Unbekannte gegen 8n
  Gleichungen). Vorgabe ist das real vermessene Blatt: 67 mm Marker, Mittelpunktabstände
  121 × 171 mm.
- **Dickenkorrektur.** Eine Fläche `h` über der Markerebene erscheint radial vom
  Kamera-Lotpunkt weg gestreckt um `d/(d−h)`; Höhe und Lotpunkt fallen aus der Zerlegung
  der Homographie, sobald die EXIF-Brennweite bekannt ist. Ohne EXIF wird der
  Kameraabstand zur Pflichteingabe.
- **Qualitätsbericht** statt blindem Vertrauen: Restfehler in px und mm, jeder Marker
  gegen seine Sollgröße zurückgemessen, Kamerahöhe und -neigung, und der Anteil des
  Zuschnitts außerhalb der Marker-Hülle.
- **PDF-Export** als Einzelseite in Objektgröße oder gekachelt auf A4/A3 mit Überlappung,
  Schnitt- und Klebemarken und vorangestelltem Klebeplan. Aufdrucke: 100-mm-Kontroll­maßstab,
  Metadaten-Fußzeile, 50-mm-Raster, optional der erkannte Umriss als Vektor-Schnittlinie.
- **Markerblatt-Generator**, Marker Modul für Modul als Vektorrechtecke gezeichnet, mit
  eigenem Kontrollmaßstab und dem Hinweis, nach dem Druck nachzumessen.
- **Weboberfläche** mit Foto-Upload (auch HEIC), Crop-Rechteck mit Live-Millimeteranzeige
  und Druckoptionen; der Server nennt beim Start die LAN-Adresse samt QR-Code fürs Handy.
- **Testsuite gegen synthetische Grundwahrheit.** Virtuelle Kamera, bekannte Pose,
  bekanntes Objekt; die Dickenkorrektur wird beidseitig geprüft. Der Renderer filtert vor
  dem Warp tief — ohne das verschiebt Aliasing die Markerecken um bis zu 0,58 px und der
  Test misst den Testaufbau statt den Detektor.
- **Selbstheilendes `dev.ps1`** mit Stempel über den SHA-256 von `requirements.txt`, plus
  passende VS-Code-Tasks.

### Bekannte Grenzen

- Objektivverzeichnung bleibt unkorrigiert; mit vier koplanaren Markern nicht abtrennbar.
  Gegenmittel beim Fotografieren: Tele, großer Abstand, Objekt mittig.
- Gewölbte Objekte gehen nicht — eine Homographie beschreibt genau eine Ebene.
- Die Maßhaltigkeit ist bisher **nur gegen synthetische Szenen** belegt. Der Beweis am
  echten Ausdruck (drucken, 100-mm-Maßstab mit dem Messschieber nachmessen) steht aus.
