# AGENTS.md — Arbeitsanweisung für KI-Agenten in diesem Repo

Dieses Dokument ist die Einstiegsseite für jeden Agenten, der hier Code ändert.
`CLAUDE.md` verweist hierher; es gibt keine zweite Fassung dieser Regeln.

## Worum es geht

Aus einem Handyfoto mit ArUco-Markern wird ein **maßhaltiges PDF in Originalgröße**.
Anwendungsfall: Schablone für einen Deckel, die 1:1 gedruckt, auf Holz geklebt und
ausgeschnitten wird.

Das heißt: **Millimeter sind das Produkt.** Eine Änderung, die das Bild hübscher macht
und dabei 0,5 mm verschiebt, ist eine Verschlechterung. Wer Geometrie anfasst, muss die
Tests aus `tests/` grün halten — sie sind der einzige Beweis, den dieses Projekt hat.

## Kommandos

`dev.ps1` ist die einzige Quelle für Projektbefehle. `.vscode/tasks.json` ruft nur hinein.

```powershell
.\dev.ps1 start-server        # Server + Browser, LAN-URL und QR-Code fürs Handy
.\dev.ps1 run-tests           # pytest
.\dev.ps1 build-markersheet   # Markerblatt nach out/
.\dev.ps1 build-exe           # Windows-Bundle nach dist/ (läuft ohne Python)
.\dev.ps1 build-installer     # Windows-Installer nach dist/ — eine Datei, ohne Adminrechte
.\dev.ps1 kill-servers        # nur Server aus DIESEM Verzeichnis (auch die gebaute .exe)
.\dev.ps1 clean-all
```

Der Port aus `app/config.py` ist der **bevorzugte**, keine Zusage: ist er belegt, weicht der
Server aus. Die geltende Adresse steht im Startbanner.

Ein selbst gestarteter Server darf den eigenen Arbeitsschritt nicht überleben. Einen
Server, den der Benutzer gestartet hat, niemals beenden — `kill-servers` trifft beide.

## Aufbau

```
app/config.py        SSOT: jede Konstante, jede Markenfarbe, das Blattlayout. Auch
                     dev.ps1 liest von hier — Port, Fassung (APP_VERSION) und
                     Marke — und reicht die letzten beiden an den Installer weiter.
app/notices.py       Vokabular für Warnungen und Abbrüche: Code + Parameter, KEIN
                     fertiger Satz. Der Text entsteht erst am Rand, aus dem Katalog.
app/i18n.py          Katalog laden, übersetzen, Accept-Language aushandeln
app/pipeline.py      Orchestrierung der Rechenkette; main.py bleibt reiner Transport
app/vision/          geometry · detect · solve · camera · thickness · extent · rectify ·
                     contour · enhance
app/pdf/             layout · overlays · branding · build · markersheet
app/static/          Oberfläche: css/ (Tokens + Stylesheets), js/ (ES-Module, kein
                     Bundler), i18n/ (de.json · en.json), brand/ (Logo und Schrift)
tests/               synthetische Szenen mit bekannter Grundwahrheit
docs/                README.md ist der Index; docs/superpowers/specs/ die Spezifikation,
                     mit dem Code abgeglichen
installer/           aruco-homographie.iss — Inno-Setup-Bauvorschrift für den
                     Windows-Installer. Quelle, kein Erzeugnis: sie ist versioniert.
aruco-homographie.spec   PyInstaller-Bauvorschrift für die Windows-.exe
```

## Invarianten — hier nichts kaputt machen

1. **Das entzerrte Bild belegt auf der Seite exakt `crop_w × crop_h` Millimeter.**
   Der Streifen unter dem Bild vergrößert die *Seite*, nie das *Bild*.
   Geprüft in `tests/test_pdf_size.py`.
2. **Es wird nichts hochgerechnet.** Markerkante und beide Mittelpunktabstände kommen so,
   wie der Benutzer sie am Ausdruck gemessen hat. Ein Faktor, der nur die Kante skaliert
   und die Abstände mitzieht, wäre schon falsch, sobald ein Drucker x und y verschieden
   skaliert.
3. **Der Markenstreifen ist immer da.** Maßstab und Fußzeile sind abschaltbar, das Logo
   und „Made with Bischof Snowboards Software" nicht — sie gehören auf jedes Blatt.
   Geprüft in `tests/test_branding.py`, für *jede* Seite eines gekachelten Exports.
4. **`app/config.py` ist die einzige Stelle für Konstanten.** Keine zweite Definition,
   auch nicht „nur kurz" in einem Modul.
5. **Das Raster muss auf hellem und dunklem Untergrund lesbar sein.** Deshalb weißer
   Saum unter der Kernlinie — nicht durch eine einzelne graue Linie ersetzen.
6. **Die Bildaufbereitung ist kosmetisch, niemals geometrisch.** `app/vision/enhance.py`
   läuft ausschließlich auf dem **bereits entzerrten** Bild, nie vor der Markererkennung:
   die Homographie wird am unveränderten Foto gemessen. Ein Schärferegler vor dem Detektor
   verschöbe die Markerecken und damit die Millimeter. Kein Regler darf die Bildgröße
   ändern, und ein unsymmetrischer Kern hat hier nichts zu suchen.
   Geprüft in `tests/test_enhance.py` mit einem Subpixel-Schätzer an einer *weichen* Kante —
   eine harte Stufe kann eine Verschiebung von einem Zehntelpixel gar nicht darstellen und
   bestünde den Test auch dann, wenn er nichts prüft.
7. **Jede sichtbare Zeichenkette kommt aus dem Katalog.** `app/static/i18n/de.json` und
   `en.json` haben denselben Schlüsselsatz — `tests/test_i18n.py` besteht darauf. Kein
   fertiger deutscher Satz im Code, weder in der Oberfläche noch in `notices.py` noch im
   PDF: dort steht der Code, der Text entsteht am Rand.

## Wie hier getestet wird

Kein Test hängt an einem echten Foto oder am Augenschein. `tests/conftest.py` baut eine
virtuelle Kamera mit gewählter Brennweite, Höhe und Neigung, rendert die Ebene mit
Markern und Testobjekt und prüft, ob die Pipeline die eingesetzten Zahlen zurückgewinnt.

Zwei Muster, die beim Erweitern beizubehalten sind:

- **Beidseitig prüfen.** Der Dickentest belegt zuerst, dass der Fehler *ohne* Korrektur
  exakt dem Höhenfaktor entspricht, und erst dann, dass er *mit* Korrektur verschwindet.
  Ein einseitiger Test wäre auch dann grün, wenn die Szene gar keinen Höhenversatz hätte.
- **Den Renderer nicht mitmessen.** `_photograph` filtert vor dem Warp tief. Ohne das
  verschiebt Aliasing die Markerecken um bis zu 0,58 px, und der Detektortest misst dann
  den Testaufbau statt den Detektor.

Das Markerblatt wird gerastert und durch den echten Detektor geschickt
(`test_markersheet.py`). Ein vertauschtes Modulraster sähe auf dem Bildschirm normal aus
und fiele sonst erst am realen Foto auf.

## Konventionen

- **Deutsch** in Kommentaren, Docstrings und interner Dokumentation. Die Oberfläche selbst
  spricht Deutsch **und** Englisch — jede sichtbare Zeichenkette kommt aus einem i18n-Katalog
  (`app/static/i18n/`), keine mehr fest im Code.
- **Git:** committen ohne Rückfrage, **pushen nur auf ausdrückliche Ansage**. Ein Feature,
  ein Commit. Betreff englisch mit konventionellem Präfix, Leerzeile, dann das Warum.
  Verbindlich in [docs/contributing/git.md](docs/contributing/git.md).
- Kommentare erklären **warum**, nicht was.
- Eine Datei, ein Zweck, etwa 300 Zeilen Code als Richtwert.
- Wiederverwenden statt neu bauen: nie eine zweite Art, dasselbe zu tun.

## Fallstricke, die hier schon zugeschlagen haben

| Stolperstein | Was gilt |
|---|---|
| `ndarray.ptp()` | In NumPy 2 entfernt. `np.ptp(array)` benutzen. |
| `cv2.aruco` | Steckt ab OpenCV 5 im Hauptpaket; `opencv-contrib-python` ist nicht nötig. Auch im **headless**-Rad vollständig vorhanden — das benutzt dieses Projekt, weil es nie ein `cv2`-Fenster öffnet. |
| Pfade auf mitgelieferte Dateien | Immer über `config.resource_path()`. `Path(__file__).parent` zeigt in der gebauten `.exe` neben die Daten, und die Anwendung startet dann mit nackter Seite — ohne Schrift, ohne Logo, ohne Übersetzung. Das sieht wie ein Erfolg aus und ist deshalb der teuerste Fehler hier. |
| Neue Datei unter `app/static/` | Kommt automatisch mit ins Bundle (der ganze Baum wird kopiert). Eine neue Datendatei **außerhalb** `app/static/` muss in `aruco-homographie.spec` eingetragen werden, sonst fehlt sie nur in der `.exe`. |
| Dateieigenschaften der `.exe` | PyInstaller legt **von sich aus keine Versionsressource an** — ohne den `version_info`-Block in `aruco-homographie.spec` sind Rechtsklick → Eigenschaften → Details komplett leer, ohne Herausgeber. Die binären Felder (`filevers`, `prodvers`, Inno-`VersionInfoVersion`) nehmen nur vier ganze Zahlen; `0.0.2-alpha` weist Windows ab. Deshalb `config.APP_VERSION_NUMERIC`. **Ausgefüllte Eigenschaften sind keine Signatur** — SmartScreen nennt weiterhin keinen Herausgeber. |
| Unicode auf der Konsole | Der ASCII-QR-Code besteht aus Blockzeichen. Landet die Ausgabe in einer Pipe oder Datei statt in einer Windows-Konsole, gilt cp1252 und `print()` bricht ab. Verzierungen dürfen den Server nicht mitreißen — siehe `print_banner`. Dieselbe Falle beim Bauen: was `dev.ps1` per `Get-ConfigValue` aus `config.py` liest und an ISCC weitergibt, läuft durch zwei Codepage-Stationen. Werte, die diesen Weg nehmen, bleiben **reines ASCII** (siehe `BRAND_COPYRIGHT`); das Sonderzeichen entsteht erst am Ziel. |
| Tiefer Ablageort des Bundles | Die längste Datei im Bundle hat 101 Zeichen relativen Pfad. Über etwa 157 Zeichen Zielordner reißt MAX_PATH, und die `.exe` stirbt beim Start mit „DLL load failed … Dateiname oder Erweiterung ist zu lang". Kein Codefehler, aber es sieht wie einer aus. Gilt nur noch für den **entpackten Ordner**: der Installer wählt den Zielpfad selbst (`%LOCALAPPDATA%\Programs\`) und kann gar nicht zu tief landen. |
| CSS-Spezifität | `#id { display: flex }` schlägt `.hidden { display: none }`. `.hidden` trägt deshalb `!important`. |
| Rasterbild statt Vektor | Marker und Logo werden als Vektor gezeichnet. Ein eingebettetes Rasterbild kostet Kantenschärfe, und die braucht die Subpixel-Erkennung. |
| Lange Heredocs | In dieser Shell brechen sehr lange Heredocs mitten im Dokument ab. Dateien mit dem Schreib-Werkzeug anlegen. |

## Was bewusst nicht gelöst ist

Objektivverzeichnung bleibt unkorrigiert — mit vier koplanaren Markern nicht abtrennbar.
Der Solver ist als Ausgleichsrechnung gebaut, ein radialer Parameter ließe sich später
als weitere Unbekannte einhängen. Gewölbte Objekte gehen prinzipiell nicht: eine
Homographie beschreibt genau eine Ebene.
