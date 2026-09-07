# ArUco-Homographie

Handyfoto rein, **maßhaltiges PDF in Originalgröße** raus. Gedacht für Schablonen: Foto vom
Deckel machen, entzerren lassen, auf dem Großformatdrucker in 1:1 ausdrucken, auf Holz kleben,
ausschneiden.

Auf dem Foto muss neben dem Werkstück ein Blatt mit **ArUco-Markern** liegen. Aus deren bekannter
Größe rechnet die App die Homographie und damit den Maßstab.

## Loslegen

```powershell
.\dev.ps1 start-server
```

Installiert beim ersten Mal alles selbst, startet den Server, öffnet den Browser und gibt die
Netzwerk-Adresse samt QR-Code aus — damit lädst du das Foto direkt vom Handy hoch.

| Kommando | Wirkung |
|---|---|
| `.\dev.ps1 start-server` | Server starten, Browser öffnen (`--no-browser` unterdrückt das) |
| `.\dev.ps1 install-deps` | venv anlegen und `requirements.txt` installieren |
| `.\dev.ps1 run-tests` | Testsuite (`pytest`) |
| `.\dev.ps1 build-markersheet [mm] [abstand_x] [abstand_y]` | Markerblatt nach `out/markerblatt_A4.pdf` |
| `.\dev.ps1 build-exe` | Windows-Programm nach `dist/ArUco-Homographie/` bauen |
| `.\dev.ps1 kill-servers` | aus diesem Repo gestartete Server beenden |
| `.\dev.ps1 clean-all` | venv, `out/`, `build/`, `dist/` und Caches entfernen |

Dieselben Kommandos liegen als VS-Code-Tasks bereit (`Strg+Shift+P` → *Tasks: Run Task*).

Der Server nimmt Port 8000, wenn er frei ist, und sonst einen anderen — die Adresse, die
wirklich gilt, steht im Startbanner.

## Für die Werkstatt: ohne Python

```powershell
.\dev.ps1 build-exe
```

baut mit PyInstaller `dist\ArUco-Homographie\ArUco-Homographie.exe`. Doppelklick startet den
Server und öffnet den Browser; auf dem Zielrechner muss **kein Python** installiert sein.

Weitergegeben wird der **ganze Ordner**, nicht nur die `.exe` darin — daneben liegt
`_internal\` mit OpenCV, den Schriften und der Oberfläche. Rund 290 MB.

Zwei Dinge, die am Zielrechner schiefgehen können:

- **Der Ablageort darf nicht zu tief sein.** Die längste Datei im Bundle hat einen
  relativen Pfad von 101 Zeichen; ab einem Zielordner über ~157 Zeichen reißt Windows'
  260-Zeichen-Grenze, und das Programm bricht beim Start mit „DLL load failed … Der
  Dateiname oder die Erweiterung ist zu lang" ab. `C:\Programme\` oder der Desktop sind
  unproblematisch, ein tief verschachtelter OneDrive-Ordner nicht.
- **Die `.exe` ist nicht signiert.** Windows SmartScreen warnt beim ersten Start
  („Weitere Informationen" → „Trotzdem ausführen"). Für den Eigengebrauch hinnehmbar,
  für Weitergabe braucht es ein Code-Signing-Zertifikat.

## Markerblatt

Standard ist das real vermessene Blatt: **DICT_4X4_50, IDs 0–3, 67 mm Kantenlänge**,
Mittelpunktabstände **121 mm waagerecht × 171 mm senkrecht**, mittig auf A4 hoch.
ID 0 oben links, 1 oben rechts, 2 unten links, 3 unten rechts.

Die Marker werden als **Vektorrechtecke** gezeichnet, nicht als Rasterbild — die Kanten bleiben
damit unabhängig von der Druckerauflösung scharf, was der Subpixel-Erkennung zugutekommt.

**Nach dem Drucken messen.** Das Blatt trägt einen eigenen 100-mm-Kontrollmaßstab. Miss die
Markerkante *und* beide Mittelpunktabstände mit dem Messschieber und trage die gemessenen Werte
in der App ein. Damit fällt jede Druckerskalierung aus der Rechnung heraus. Genau dafür sind die
drei Felder da — es wird nirgends heimlich hochgerechnet.

Anderes Blatt, andere IDs, irgendwie verteilte Marker? Dann **Frei-Modus**: der braucht nur die
Markergröße und schätzt die Positionen mit. Voraussetzung ist lediglich, dass alle Marker gleich
ausgerichtet gedruckt sind — die App prüft das und warnt sonst.

## So wird es genau

Drei Dinge entscheiden über die Maßhaltigkeit, alles andere ist Komfort:

**1 · Ebene.** Eine Homographie ist nur für *eine* Ebene exakt. Liegt das Markerblatt auf dem
Tisch, während die interessante Fläche 20 mm höher liegt, ist das Ergebnis bei 900 mm
Kameraabstand um 2,2 % zu groß — auf 500 mm sind das 11 mm. Deshalb: Blatt möglichst **auf** die
Objektoberfläche legen. Geht das nicht, trage die **Objektdicke** ein; die App rechnet den
Höhenversatz heraus und holt sich Kamerahöhe und Lotpunkt aus der EXIF-Brennweite. Fehlt die
(z. B. bei weitergeleiteten Bildern), fragt sie nach dem Kameraabstand.

**2 · Objektiv.** Mit vier koplanaren Markern lässt sich die Linsenverzeichnung nicht
mitkalibrieren, sie bleibt also unkorrigiert. Gegenmittel beim Fotografieren: **Tele (1× oder 2×),
großer Abstand, Objekt mittig** — am Bildrand biegt ein Weitwinkel Geraden um mehrere Millimeter.

**3 · Nachmessen.** Auf jedem PDF steht ein 100-mm-Maßstab. Beim Drucken **100 % / keine
Skalierung** wählen und danach mit dem Messschieber nachmessen. Erst das beweist, dass die Kette
vom Foto bis zum Papier stimmt.

Die App hilft beim Misstrauen: sie zeigt den Restfehler in px und mm, misst jeden Marker
zurück (Sollgröße gegen gemessene Größe deckt Verzeichnung und schiefen Aufbau auf), nennt
Kamerahöhe und -neigung, und warnt, wenn der Zuschnitt weit außerhalb der Marker-Hülle liegt —
dort wird die Entzerrung zur Extrapolation.

## Ablauf im Browser

1. Foto hochladen (JPEG, PNG oder HEIC vom iPhone).
2. Markergröße und Mittelpunktabstände eintragen, Modus wählen, ggf. Objektdicke.
3. **Entzerren** → Qualitätsbericht und entzerrte Vorschau.
4. Zuschnitt-Rechteck aufziehen; Kantenlängen, Pixelzahl und Extrapolationsanteil laufen live mit.
5. Druckoptionen wählen → **PDF erzeugen**.

Einzelseite in exakter Objektgröße (für den Plotter) oder Kachelung auf A4/A3 mit Überlappung,
Schnitt- und Klebemarken und vorangestelltem Klebeplan. Aufdrucke: 100-mm-Maßstab,
Metadaten-Fußzeile, 50-mm-Raster, optional der erkannte Umriss als Vektor-Schnittlinie.

Das **50-mm-Raster** wird doppelt gezogen — breiter weißer Saum, darüber die Kernlinie in
Markentinte. Auf einem hellen Foto verschwindet der Saum, auf einem dunklen trägt er die Linie;
so bleibt das Raster auf jedem Untergrund lesbar, ohne das Bild zuzudecken.

## Marke

Jedes Blatt trägt unten das Bischof-Snowboards-Logo und „Made with Bischof Snowboards Software" —
die Einzelseite, *jede* Kachel, der Klebeplan und das Markerblatt. Der Block ist im PDF auf
[bischof-snowboards.com](https://bischof-snowboards.com) verlinkt.

Das Logo kommt als **Vektor** aus derselben SVG, die auch die Website benutzt, und ist damit bei
jeder Druckgröße scharf. Farben und Schrift (Montserrat) stammen aus den Marken-Tokens von
`snow-service-free`; in `app/config.py` stehen sie als sRGB, weil PDF und CSS Hex brauchen.

Weil der Streifen die Marke trägt, ist er **immer** da — auch mit abgeschaltetem Maßstab und
abgeschalteter Fußzeile. Die Seite ist dadurch um 18 mm höher als das Objekt. Das *Bild* belegt
davon unberührt weiterhin exakt seine Millimeter, und nur das war je die Zusage.

## Aufbau

```
app/vision/    Erkennung, Homographie, Kamerapose, Dickenkorrektur, Entzerrung, Kontur
app/pdf/       Seitengeometrie, Aufdrucke, Marke, PDF-Bau, Markerblatt
app/static/    Oberfläche; brand/ trägt Logo und Schrift
app/           config (SSOT aller Konstanten), pipeline (Orchestrierung), main (Routen)
tests/         synthetische Szenen mit bekannter Grundwahrheit
docs/          Spezifikation
```

Wer hier mit einem KI-Agenten arbeitet: [AGENTS.md](AGENTS.md) nennt die Invarianten, die nicht
gebrochen werden dürfen. [CHANGELOG.md](CHANGELOG.md) hält fest, was sich wann geändert hat.

`app/config.py` ist die einzige Stelle für Konstanten — auch `dev.ps1` liest den bevorzugten
Port von dort. Pfade auf mitgelieferte Dateien gehen über `config.resource_path()`, damit sie
im Quellbaum und im gebauten Bundle dasselbe bedeuten.

## Tests

Kein Test hängt an einem echten Foto oder am Augenschein. `tests/conftest.py` baut eine virtuelle
Kamera mit gewählter Brennweite, Höhe und Neigung, rendert die Ebene mit Markern und Testobjekt
und prüft, ob die Pipeline die eingesetzten Zahlen zurückgewinnt:

- Homographie rauschfrei exakt (< 1e-6 mm), mit 0,2 px Detektionsrauschen < 0,5 mm auf 500 mm
- Dickenkorrektur **in beide Richtungen**: ohne Korrektur muss der Fehler exakt dem Höhenfaktor
  entsprechen, mit Korrektur < 0,05 mm — sonst wäre der Test wertlos
- Markerecken subpixelgenau (< 0,3 px), Kachelgeometrie, und die PDF-MediaBox auf 0,01 mm

`.\dev.ps1 run-tests`

## Grenzen

Gewölbte Objekte gehen nicht — eine Homographie beschreibt genau eine Ebene. Die
Objektivverzeichnung bleibt in dieser Fassung unkorrigiert (der Solver ist als
Ausgleichsrechnung gebaut, ein radialer Parameter ließe sich nachrüsten). Sitzungen leben eine
Stunde im Arbeitsspeicher, es gibt keine dauerhafte Speicherung.
