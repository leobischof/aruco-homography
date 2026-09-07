# Vorhaben — was noch nicht gebaut ist

Diese Datei sammelt **Vorhaben, an denen gerade niemand arbeitet**, die aber gebaut werden
sollen. Sie ist bewusst getrennt von `CHANGELOG.md` (was fertig ist) und von
`docs/superpowers/specs/` (die Spezifikation dessen, was existiert).

Was hier steht, ist **noch keine Zusage und noch kein Entwurf**, sondern eine begründete
Absicht mit der Vorarbeit, die ein Umsetzer sonst zweimal machen müsste: der Lösungsweg, die
Stolpersteine, die offenen Fragen. Wer ein Vorhaben angeht, schreibt zuerst eine Spec nach
`docs/superpowers/specs/` und streicht den Eintrag hier.

**Sprache:** Interne Dokumentation ist deutsch (Konvention aus `AGENTS.md`). Einzige Ausnahme
ist `README.md` — die Eingangstür ist englisch mit deutscher Kurzfassung.

| Zustand | Bedeutung |
|---|---|
| 🔵 gewollt | Vom Auftraggeber ausdrücklich gewünscht |
| ⚪ Kandidat | Beim Arbeiten am Code aufgefallen, nicht beauftragt |

---

## 1 · 🔵 Als Windows-`.exe` ausliefern

**Warum.** Heute braucht der Rechner Python, ein venv und `dev.ps1`. In der Werkstatt soll
eine Datei liegen, die man doppelklickt.

### Weg

PyInstaller im **One-Folder-Modus**, nicht One-File. One-File entpackt bei jedem Start
OpenCV und NumPy in ein Temp-Verzeichnis; das kostet mehrere Sekunden Startzeit für nichts.

Die Anwendung bleibt, was sie ist: ein lokaler Server. Zwei Ausbaustufen:

1. **Klein:** `.exe` startet Uvicorn und öffnet den Standardbrowser — genau das, was
   `main()` heute schon tut. Wenig Arbeit, funktioniert sofort.
2. **Größer:** `pywebview` legt ein eigenes Fenster um die Oberfläche, damit es sich wie ein
   Programm anfühlt und nicht wie ein Tab. Kostet ein zusätzliches Fenster-Toolkit.

Stufe 1 zuerst; Stufe 2 nur, wenn der Browser-Tab wirklich stört.

### Stolpersteine, die vorher bekannt sind

| Punkt | Was zu tun ist |
|---|---|
| Paketgröße | `opencv-python` zieht Qt und die GUI-Fensterfunktionen mit. Die Anwendung öffnet **nie** ein `cv2`-Fenster → auf `opencv-python-headless` wechseln. Spart grob 60–80 MB. Vorher prüfen, dass `cv2.aruco` im Headless-Rad enthalten ist. |
| Datendateien | `app/static/**` (Logo-SVGs, Montserrat-`.woff2`, die i18n-Kataloge) sind **keine** Python-Module. Sie müssen über `--add-data` mit; sonst startet die `.exe` und zeigt eine nackte Seite ohne Schrift und ohne Übersetzung. |
| Pfade | `Path(__file__).parent` zeigt im Bundle woandershin. Einen Helfer bauen, der `sys._MEIPASS` berücksichtigt, und **alle** Pfade in `app/config.py` darüber auflösen. |
| Fester Port | `config.PORT = 8000` ist belegt, sobald irgendetwas anderes darauf läuft. Freien Port suchen und ihn dem Browser übergeben. |
| Versteckte Importe | ReportLab lädt Schriften und Renderer zur Laufzeit nach; PyInstaller findet das nicht von allein. |
| SmartScheme/Defender | Eine unsignierte `.exe` aus dem Netz wird gewarnt. Für den Eigengebrauch hinnehmbar, für Weitergabe nicht — dann Code-Signing-Zertifikat. |

### Prüfung

Die `.exe` auf einem Rechner **ohne Python** starten, ein echtes Foto durchlaufen lassen,
das PDF drucken und mit dem Messschieber nachmessen. Alles andere beweist nichts.

### Aufwand

Stufe 1: überschaubar, ein Arbeitstag inklusive der Pfad-Umstellung. Der Umstieg auf
`headless` ist der einzige Teil, der die Testsuite anfassen kann.

---

## 2 · 🔵 Als Android-`.apk` ausliefern

**Ehrliche Vorbemerkung.** Das ist das schwerste Vorhaben in dieser Datei — deutlich
schwerer, als es klingt. Der Grund ist eine einzige Tatsache: **für `opencv-python` gibt es
keine offiziellen Android-Räder.** Der gesamte Rechenweg dieses Projekts hängt an OpenCV und
NumPy. Man kann das Problem nicht wegkonfigurieren, man muss sich für einen Weg entscheiden.

### Vier Wege, mit dem, was sie wirklich kosten

**a) PWA — die Oberfläche installierbar machen.** Kein APK, aber der größte Teil des
Nutzens für den kleinsten Teil der Arbeit. Ein Web-App-Manifest, ein Service Worker, Icons.
Das Handy zeigt dann ein Symbol auf dem Startbildschirm, die Seite startet ohne Browser-Leiste.

Das funktioniert heute schon fast: der Server gibt beim Start die LAN-Adresse samt QR-Code
aus, das Handy lädt das Foto direkt hoch. Der PC bleibt nötig.

**b) Chaquopy — Python im Android-Projekt.** Klingt nach der Abkürzung, ist aber genau da am
schwächsten, wo es zählt: NumPy geht, OpenCV nicht ohne Weiteres. Man landet doch bei der
OpenCV-Android-SDK über JNI. Halber Weg mit vollen Kosten.

**c) Rechenkern portieren.** `app/vision/` gegen die OpenCV-Android-SDK in Kotlin oder C++
neu schreiben. Ergebnis: echte Offline-App, keine Serverbindung, schnell. Kosten: der Kern
existiert danach **zweimal** — und damit ist die Regel gebrochen, auf der dieses Projekt
steht (`AGENTS.md`, Invariante 4: eine Wahrheit, an einer Stelle). Zwei Implementierungen
derselben Homographie driften auseinander, und die Millimeter driften mit. Wer das geht,
braucht die synthetische Testsuite aus `tests/` **auf beiden Seiten**, mit denselben
Grundwahrheiten.

**d) Gehosteter Server, dünner Client.** Das APK ist nur noch Kamera plus Ansicht, gerechnet
wird auf einem Server. Technisch der einfachste Weg. Ändert aber die Eigenschaften des
Produkts: Fotos verlassen das Haus, ohne Netz geht nichts, und es gibt laufende Kosten.

### Empfehlung

**(a) zuerst** — klein, sofort nützlich, verbaut nichts. Danach ehrlich entscheiden, ob
Offline-Betrieb in der Werkstatt wirklich gebraucht wird. Falls ja: **(c)**, mit
Doppelprüfung durch die Testsuite. Falls nein: **(a)** reicht dauerhaft und **(d)** ist die
Antwort, sobald es außerhalb des eigenen WLANs laufen soll.

### Offene Frage an den Auftraggeber

Muss die App **ohne PC und ohne WLAN** auf dem Handy allein rechnen — oder genügt es, dass
das Handy die Kamera und die Anzeige ist, während der Rechner im Raum rechnet? Von dieser
einen Antwort hängt ab, ob das ein Wochenprojekt oder ein Monatsprojekt ist.

---

## 3 · 🔵 Ein Codebestand für Web, Windows und Android

Die Frage hinter Punkt 1 und 2: **kann man das einmal schreiben und dreimal ausliefern?**
Ja — aber die Antwort hängt daran, *was* geteilt werden soll.

### Was überhaupt geteilt werden müsste

Nicht „die Anwendung". Oberfläche, PDF-Bau und Server sind entweder schon portabel oder
billig neu zu schreiben. Portiert werden müsste genau ein Ding: der **Rechenkern** in
`app/vision/`, rund **1 400 Zeilen**.

Dessen Fremdabhängigkeiten sind gemessen, nicht geschätzt. Von den 54 benutzten
`cv2`-Symbolen sind die meisten Konstanten und Farbraum-Kennungen. Wirklich zu ersetzen
sind etwa ein Dutzend Algorithmen:

| Abhängigkeit | Warum sie wehtut |
|---|---|
| `cv2.aruco.*` (Detector, Wörterbuch, `CORNER_REFINE_SUBPIX`) | Der Brocken. Markererkennung **mit Subpixel-Verfeinerung** — und die Subpixel sind hier die Millimeter. |
| `scipy.optimize.least_squares` | Die zweite Altlast, gern übersehen: der Ausgleich in `solve.py`. Ein Levenberg-Marquardt, den man mitbringen muss. |
| `findHomography` (LMEDS), `getPerspectiveTransform`, `warpPerspective` | Standardnumerik, gut portierbar. `INTER_LANCZOS4` beim Entzerren nicht stillschweigend gegen etwas Billigeres tauschen. |
| `findContours`, `approxPolyDP`, `convexHull`, `contourArea`, `intersectConvexConvex` | Hülle, Kontur, Extrapolationsanteil — und die Grundlage des DXF-Exports aus Punkt 4. |
| `createCLAHE`, `Canny`, `Sobel`, `GaussianBlur`, `morphologyEx` | Bildaufbereitung. Vergleichsweise harmlos. |

Dazu PIL für Laden und EXIF.

### Die drei ernsthaften Wege

**a) Rust-Kern + Tauri v2 — die direkte Antwort auf „andere Sprachen".**
Rust übersetzt nach nativem Windows-Programm, nach Android (NDK) **und** nach WebAssembly.
Tauri v2 legt darum die Hülle für Desktop *und* Android aus einem Bestand.

Der Punkt, der hier besonders gut passt: **Tauris Oberflächenschicht ist HTML/CSS/JS** —
also genau das, was dieses Projekt schon hat und was gerade um Mehrsprachigkeit, Themes und
Mobilansicht erweitert wird. Diese Arbeit wäre nicht verloren, sie würde die Hülle für alle
drei Ziele.

Der Preis, klar benannt: ArUco-Erkennung und der LM-Ausgleich müssten **neu geschrieben**
werden. Beides ist dokumentiert und begrenzt (Erkennung: adaptive Schwelle → Konturen →
Vierecke → Entzerren → Bits abtasten → Hamming-Dekodierung; Ausgleich: `nalgebra` plus
`levenberg-marquardt`). Die Bindings `opencv-rust` helfen **nicht**: sie binden an das
native OpenCV und nehmen damit das WASM-Ziel wieder weg.

**b) C++-Kern — behält das erprobte OpenCV.**
OpenCV hat ein offizielles Android-SDK und einen offiziellen WASM-Bau (`opencv.js`). Ein
C++-Kern behält also die **echte** ArUco-Implementierung, statt sie nachzubauen. Für ein
Projekt, dessen Produkt Millimeter sind, ist „die Messtechnik nicht neu schreiben" ein
ernstzunehmendes Argument. Kosten: drei Werkzeugketten und ein rund 8 MB großes
`opencv.js` im Web.

**c) Python behalten, den Server teilen — null neue Sprachen.**
Das ist der Weg, der zu ~80 % schon gebaut ist. Die `.exe` bündelt den Server, Web ist
heute, Android ist eine PWA über die LAN-Adresse. Ein Bestand, kein Neuschrieb, **keine
zweite Implementierung der Mathematik**. Grenze: das Handy rechnet nie allein.

**d) Pyodide** (Python samt NumPy im Browser) klingt verlockend. Vor jeder Wette darauf
**nachprüfen**, ob `cv2.aruco` im dortigen OpenCV-Bau enthalten ist und was SciPy an
Ladezeit kostet — ungeprüft ist das kein Plan, sondern eine Hoffnung. Android löst es
ohnehin nicht.

### Empfehlung

Es hängt an derselben Frage wie Punkt 2: **muss das Handy ohne PC rechnen?**

- **Nein** → **(c)**. Fast fertig, keine neue Sprache, keine zweite Wahrheit.
- **Ja** → **(a)**, und die HTML-Oberfläche zieht unverändert mit um. **(b)** immer dann
  vorziehen, wenn das Nachbauen der Markererkennung als zu großes Risiko für die
  Maßhaltigkeit gilt — ein vertretbarer Standpunkt.

Für **(a)** und **(b)** gilt unverhandelbar: die synthetische Testsuite aus `tests/` läuft
**auf beiden Seiten**, gegen dieselben Grundwahrheiten. Zwei Implementierungen ohne
gemeinsamen Test driften, und sie driften in Millimetern.

### Was sich heute lohnt, egal wie man sich entscheidet

**Die Portierungsgrenze sauber ziehen.** `cv2` steht derzeit auch außerhalb des
Rechenkerns — in `app/pdf/build.py`, `app/session.py` und `app/config.py`. Die Verwendungen
sind flach (JPEG-Kodierung, eine Wörterbuchkennung), aber jede einzelne wäre bei einer
Portierung ein zusätzlicher Faden zum Entwirren.

OpenCV hinter einer dünnen Bildschnittstelle auf `app/vision/` einzugrenzen kostet heute
wenig und ist die wirksamste Vorbereitung auf **jeden** der Wege — auch auf den
Entschluss, keinen davon zu gehen.

---

## 4 · 🔵 DXF-Export für CNC, mit auswählbaren Kanten

**Warum.** Heute endet die Kette am gedruckten Papier: aufkleben, aussägen. Für die Fräse
soll stattdessen eine DXF-Datei herausfallen — und zwar **nicht** alles, was das Bild an
Kanten hergibt, sondern die Linien, die man vorher ausgewählt hat.

### Der Grundsatz, der alles bestimmt

**Die DXF muss auf denselben Millimetern liegen wie das PDF.** Beide Ausgaben beschreiben
dasselbe Werkstück. Wenn Papier und Fräsbahn um 0,3 mm auseinanderlaufen, ist der Fehler
schlimmer als gar kein DXF-Export, weil er erst am Werkstück auffällt.

Praktisch heißt das: die DXF entsteht aus **derselben** entzerrten Ebene und **demselben**
Zuschnitt wie das PDF — aus `crop_mm` und `px_per_mm`, nicht aus einem zweiten Rechenweg.

### Weg

```
entzerrtes Bild (Zuschnitt, px_per_mm)
   → Kantenbild                     (Canny; die Bildaufbereitung aus app/vision/enhance.py
                                      ist hier kein Luxus, sondern die halbe Miete)
   → Konturen                        (cv2.findContours — app/vision/contour.py kann das
                                      im Ansatz schon, für die Schnittlinie im PDF)
   → Polygonzüge vereinfachen        (Douglas-Peucker, cv2.approxPolyDP, Epsilon in mm)
   → optional Kreise/Bögen erkennen  (eine gefräste Bohrung will ein CIRCLE sein,
                                      kein 200-Punkte-Polygon)
   → Auswahl durch den Bediener      (im Browser, auf der Vorschau)
   → DXF schreiben                   (ezdxf, Einheiten Millimeter)
```

### Auswahl-Oberfläche

Die gefundenen Züge werden über die Vorschau gelegt, jeder einzeln anklickbar. Der Bediener
schaltet an und aus und kann jedem Zug eine **Ebene (Layer)** geben — „Außenkontur",
„Bohrungen", „Gravur" —, weil genau daran die CAM-Software später die Operationen hängt.
Das ist derselbe Umgang wie beim Zuschnitt-Rechteck: sehen, anfassen, umschalten.

### Stolpersteine, die vorher bekannt sind

| Punkt | Was gilt |
|---|---|
| **Y-Achse** | Bildkoordinaten zählen y nach unten, DXF zählt y nach oben. Wer das vergisst, exportiert ein gespiegeltes Werkstück — und merkt es erst an der gefrästen Platte. Der klassische Fehler dieses Formats. |
| **Einheiten** | `$INSUNITS = 4` (Millimeter) setzen. Fehlt die Angabe, rät die CAM-Software, und manche raten Zoll. |
| **Nullpunkt** | Festlegen und dokumentieren: linke untere Ecke des Zuschnitts, oder die Bounding-Box des Werkstücks. Nicht dem Zufall überlassen. |
| **Geschlossen vs. offen** | Eine Außenkontur muss ein **geschlossener** Polygonzug sein, sonst kann die CAM keinen Werkzeugradius versetzen. Beim Vereinfachen darf der Ring nicht aufbrechen. |
| **Vereinfachungs-Epsilon** | Das ist ein **Genauigkeitsregler**, kein Schönheitsregler. Er gehört sichtbar in die Oberfläche, in Millimetern beschriftet, mit Vorgabe aus `config.CONTOUR_EPS_MM` — und er gehört in die Fußzeile des Protokolls. |
| **Was der Export nicht kann** | Die Kante im Bild ist die Kante des **Fotos**, nicht die Ideallinie. Objektivverzeichnung bleibt unkorrigiert (`AGENTS.md`, „Was bewusst nicht gelöst ist"). Der Export erbt jede Ungenauigkeit der Entzerrung — er darf keine Präzision vortäuschen, die die Kette nicht hat. |
| **Fräserradius** | Bewusst **nicht** hier. Aufmaß und Radiuskorrektur macht die CAM-Software. Wir liefern die Geometrie, nicht die Bahn. |

### Prüfung

Genau wie der Rest dieses Projekts: **synthetisch, gegen bekannte Grundwahrheit.** Eine
Szene mit einem Rechteck bekannter Kantenlänge und einem Kreis bekannten Durchmessers
rendern, exportieren, die DXF mit `ezdxf` wieder einlesen und die Maße nachmessen. Toleranz
klein wählen — der Test ist der einzige Beweis, den auch dieser Weg haben wird.
Zusätzlich einmal echt: DXF in die CAM laden und ansehen, ob Nullpunkt und Orientierung
stimmen.

### Abhängigkeiten

Setzt die gerade entstehende **Bildaufbereitung** (`app/vision/enhance.py`) voraus — die
Qualität der Vektorisierung steht und fällt mit dem Kantenbild. Neue Abhängigkeit: `ezdxf`.

---

## 5 · ⚪ Weitere Kandidaten

Beim Lesen des Codes aufgefallen, **nicht beauftragt** — hier notiert, damit sie nicht
verloren gehen.

- **Der Beweis am echten Ausdruck fehlt.** `CLAUDE.md` sagt es selbst: die Maßhaltigkeit ist
  bislang nur gegen synthetische Szenen belegt. Einmal drucken, mit dem Messschieber
  nachmessen, das Ergebnis dokumentieren. Bis das passiert ist, steht die zentrale Zusage
  des Projekts ungeprüft im Raum. Von allem in dieser Datei ist das das Wichtigste.
- **Sitzungen leben nur im Arbeitsspeicher** (`app/session.py`, `SESSION_TTL_S`). Ein
  Neustart des Servers wirft eine laufende Arbeit weg.
- **Objektivverzeichnung.** In `AGENTS.md` als bewusst offen vermerkt. Der Solver ist als
  Ausgleichsrechnung gebaut, ein radialer Parameter ließe sich als weitere Unbekannte
  einhängen. Würde die Genauigkeit am Bildrand spürbar heben — und damit auch den
  DXF-Export aus Punkt 4.
- **Mehr als vier Marker.** Heute ist das Blatt auf IDs 0–3 festgelegt. Mehr Marker über eine
  größere Fläche würden die Extrapolation verkleinern, die die Oberfläche heute nur warnend
  anzeigt.
