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
.\dev.ps1 kill-servers        # nur Server aus DIESEM Verzeichnis
.\dev.ps1 clean-all
```

Ein selbst gestarteter Server darf den eigenen Arbeitsschritt nicht überleben. Einen
Server, den der Benutzer gestartet hat, niemals beenden — `kill-servers` trifft beide.

## Aufbau

```
app/config.py        SSOT: jede Konstante, jede Markenfarbe, das Blattlayout. Auch
                     dev.ps1 liest den Port von hier.
app/notices.py       Vokabular für Warnungen und Abbrüche (Code + deutscher Klartext)
app/pipeline.py      Orchestrierung der Rechenkette; main.py bleibt reiner Transport
app/vision/          geometry · detect · solve · camera · thickness · extent · rectify · contour
app/pdf/             layout · overlays · branding · build · markersheet
app/static/          Oberfläche; app/static/brand/ trägt Logo und Schrift
tests/               synthetische Szenen mit bekannter Grundwahrheit
docs/superpowers/    die Spezifikation, mit dem Code abgeglichen
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
- Commit-Betreffs auf Englisch mit konventionellem Präfix (`feat:` `fix:` `docs:` `chore:`
  `test:` `refactor:`).
- Kommentare erklären **warum**, nicht was.
- Eine Datei, ein Zweck, etwa 300 Zeilen Code als Richtwert.
- Wiederverwenden statt neu bauen: nie eine zweite Art, dasselbe zu tun.

## Fallstricke, die hier schon zugeschlagen haben

| Stolperstein | Was gilt |
|---|---|
| `ndarray.ptp()` | In NumPy 2 entfernt. `np.ptp(array)` benutzen. |
| `cv2.aruco` | Steckt ab OpenCV 5 im Hauptpaket; `opencv-contrib-python` ist nicht nötig. |
| CSS-Spezifität | `#id { display: flex }` schlägt `.hidden { display: none }`. `.hidden` trägt deshalb `!important`. |
| Rasterbild statt Vektor | Marker und Logo werden als Vektor gezeichnet. Ein eingebettetes Rasterbild kostet Kantenschärfe, und die braucht die Subpixel-Erkennung. |
| Lange Heredocs | In dieser Shell brechen sehr lange Heredocs mitten im Dokument ab. Dateien mit dem Schreib-Werkzeug anlegen. |

## Was bewusst nicht gelöst ist

Objektivverzeichnung bleibt unkorrigiert — mit vier koplanaren Markern nicht abtrennbar.
Der Solver ist als Ausgleichsrechnung gebaut, ein radialer Parameter ließe sich später
als weitere Unbekannte einhängen. Gewölbte Objekte gehen prinzipiell nicht: eine
Homographie beschreibt genau eine Ebene.
