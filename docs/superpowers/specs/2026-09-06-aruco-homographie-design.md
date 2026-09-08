---
title: ArUco-Homographie — Design / Spezifikation
description: Rechenweg, PDF-Geometrie, API, Oberfläche und Konstanten — mit dem Code abgeglichen.
audience: developer
status: current
updated: 2026-09-07
---

# ArUco-Homographie — Design / Spezifikation

**Datum:** 2026-09-06, fortgeschrieben 2026-09-07
**Status:** umgesetzt — dieses Dokument ist mit dem Code abgeglichen (2026-09-07)
**Projektordner:** `SOFTWARE/ArUco-Homographie` (Schwesterordner von `SOFTWARE/OpenCV-Kalibirerung`)

---

## 1 · Zweck

Aus einem **Handyfoto**, auf dem neben dem Werkstück ein Blatt mit **ArUco-Markern** liegt, ein
**maßhaltiges PDF** erzeugen: entzerrte Draufsicht (Homographie), skaliert in **Originalgröße**,
ausdruckbar auf dem Großformatdrucker, aufklebbar auf Holz, ausschneidbar.

Konkreter Anlassfall: Draufsicht eines Deckels als Schablone.

**Erfolgskriterium.** Ein 100-mm-Referenzmaß im gedruckten PDF misst mit dem Messschieber
100 mm ± 0,5 mm, und ein bekanntes Objektmaß von 500 mm liegt innerhalb ± 1 mm — sofern die
Aufnahmeregeln aus §3.5 eingehalten werden.

---

## 2 · Architektur

Lokaler **FastAPI**-Server + statisches Browser-Frontend. Rechenkern in Python
(OpenCV / NumPy / SciPy), PDF-Erzeugung mit ReportLab.

Die **Markererkennung** gibt es seit Stufe 2 zweimal: in Python als geprüft maßhaltige
Referenz und in C++ unter `core/`, damit dieselbe Messtechnik später auf Android und im
Browser rechnet (`docs/cpp-migration/`). Welche läuft, entscheidet `ARUCO_CORE` beim Import
(`app/vision/backend.py`); die Aufrufer merken davon nichts, und es gibt **keine zweite
Testsuite** — die vorhandene läuft gegen beide Kerne.

```
Handy/Browser ──upload──▶ /api/upload   ──▶ Session (Temp-Verzeichnis, TTL 1 h)
              ──solve───▶ /api/solve    ──▶ Marker, Homographie, Kamerapose, Qualitätsbericht,
                                            entzerrte Vorschau + mm-Extent
              ──adjust──▶ /api/adjust   ──▶ aufbereitete Vorschau (Live-Regler, §3.10)
              (Crop-Rechteck im Browser ziehen, live mm-Anzeige)
              ──export──▶ /api/export   ──▶ PDF (einzeln oder gekachelt)
                          /api/markersheet ──▶ A4-Markerblatt-PDF
```

Der Server bindet auf `0.0.0.0` und **bevorzugt** Port 8000; ist der belegt, weicht er auf einen
freien aus (`app.main.choose_port`). Ein fester Port wäre auf einem Werkstattrechner eine Wette,
und ein Start, der mit „address already in use" abbricht, sieht aus wie ein kaputtes Programm.
Beim Start gibt er die LAN-URL plus ASCII-QR-Code auf der Konsole aus, damit das Foto direkt vom
Handy hochgeladen werden kann. Er läuft im Vordergrund (`dev.ps1 start-server` blockiert);
`dev.ps1 kill-servers` beendet hängengebliebene Instanzen.

Die Oberfläche zeigt sich in einem **eigenen Fenster** (pywebview), das genau diesen Server auf
dem Port anzeigt, der es tatsächlich geworden ist — ein Reiter im Browser wäre beim Aufräumen
mitgeschlossen worden und die Anwendung schiene verschwunden, obwohl ihr Server läuft. Das
Fenster ist eine zweite *Ansicht*, keine zweite Anwendung: der Server bleibt in jeder Betriebsart
derselbe, und das Handy erreicht ihn weiter, während das Fenster offen steht. Welche Betriebsart
gilt, entscheidet `app.window.choose_ui_mode` aus der Kommandozeile (§10); kann dieser Rechner
kein Fenster zeigen, tritt der Browser ein und der Server startet trotzdem.


Oberfläche **und** Server sprechen Deutsch und Englisch aus **denselben** Katalogdateien
(`app/static/i18n/`). Sie werden zweimal gelesen — vom Browser über HTTP, von Python von der
Platte — und es gibt bewusst keine zweite Fassung für den Server (§7.2).

### 2.1 Dateien — ein Concern pro Datei, ≤ 300 Zeilen Code

```
ArUco-Homographie/
├─ dev.ps1                      # install-deps | start-server | run-tests | build-markersheet |
│                               #   build-exe | build-installer | kill-servers | clean-all |
│                               #   help  (§10)
├─ aruco-homographie.spec       # PyInstaller-Bauvorschrift (One-Folder), versioniert
├─ installer/
│  └─ aruco-homographie.iss     # Inno-Setup-Bauvorschrift (eine Datei, pro Benutzer), versioniert
├─ requirements.txt
├─ pyproject.toml               # nur die pytest-Einstellungen (pythonpath, testpaths, -q)
├─ README.md · CHANGELOG.md · AGENTS.md · CLAUDE.md
├─ .gitignore
├─ .vscode/tasks.json
├─ docs/superpowers/specs/2026-09-06-aruco-homographie-design.md
├─ shared/                      # sprachneutral, geteilt mit C++ und JS (docs/cpp-migration/)
│  ├─ constants.json            # die Produktkonstanten selbst (§8)
│  └─ fixtures/                 # eingefrorene Prüfszenen samt Grundwahrheit
├─ core/                        # der C++-Rechenkern (Stufe 2, docs/cpp-migration/)
│  ├─ CMakeLists.txt            # ein Bau: das Python-Modul + der Prüfstand
│  ├─ include/aruco/            # types.hpp (die Grenze) · detect.hpp · constants.hpp.in
│  ├─ src/detect.cpp            # ArUco + Subpixel, Übersetzung von app/vision/detect.py
│  ├─ bindings/python.cpp       # pybind11 → Modul `aruco_core`, ohne Kopie des Bildes
│  ├─ tests/conformance.cpp     # gegen shared/fixtures/, dieselben Toleranzen
│  └─ tools/                    # gen_constants.py · make_fixture_pack.py (beides erzeugend)
├─ app/
│  ├─ __init__.py
│  ├─ main.py                   # FastAPI-App, Routen, Static-Mount, Startbanner (LAN-URL + QR)
│  ├─ window.py                 # wie sich die Oberfläche zeigt: Fenster · Browser · nichts (§10)
│  ├─ config.py                 # SSOT aller Konstanten (§8)
│  ├─ schemas.py                # Pydantic-Request-Modelle (SSOT der API-Typen)
│  ├─ notices.py                # Vokabular für Warnungen und Abbrüche: Code + Parameter (§7.1)
│  ├─ i18n.py                   # Sprachkataloge, Platzhalter, Accept-Language (§7.2)
│  ├─ pipeline.py               # Orchestrierung der Rechenkette, hält main.py auf Transport
│  ├─ session.py                # Upload-/Ergebnis-Store im Temp-Verzeichnis, TTL-Aufräumung
│  ├─ vision/
│  │  ├─ __init__.py
│  │  ├─ backend.py             # welcher Rechenkern misst: Python oder C++ (ARUCO_CORE)
│  │  ├─ geometry.py            # projektive Grundrechenarten, von mehreren Modulen geteilt
│  │  ├─ detect.py              # EXIF-Rotation, HEIC, CLAHE, ArUco + Subpixel-Refinement
│  │  ├─ solve.py               # Homographie: Blatt, frei, verstreut; Residuen, Hülle
│  │  ├─ camera.py              # Brennweite aus EXIF, H-Zerlegung → Höhe, Lotpunkt, Neigung
│  │  ├─ thickness.py           # Dickenkorrektur → effektive Homographie
│  │  ├─ extent.py              # abbildbarer Ebenenbereich (Horizont-Clipping)
│  │  ├─ rectify.py             # warpPerspective in exaktes mm-Raster bei Ziel-DPI
│  │  ├─ enhance.py             # kosmetische Bildaufbereitung NACH dem Entzerren (§3.10)
│  │  └─ contour.py             # optionale Umriss-Erkennung im entzerrten Bild
│  ├─ pdf/
│  │  ├─ __init__.py
│  │  ├─ layout.py              # Seiten- und Kachelgeometrie (SSOT der Druckgeometrie)
│  │  ├─ overlays.py            # 100-mm-Maßstab, 50-mm-Raster, Fußzeile, Passermarken
│  │  ├─ branding.py            # Logo als Vektor + Herkunftszeile, auf jedem Blatt (§4.6)
│  │  ├─ build.py               # PDF-Bau: Einzelseite, Kachelung, Klebeplan
│  │  └─ markersheet.py         # A4-Markerblatt generieren
│  └─ static/
│     ├─ index.html             # das Gerüst der sechs Schritte, jede Beschriftung per data-i18n
│     ├─ i18n/de.json · en.json # die Kataloge — von Browser UND Python gelesen (§7.2)
│     ├─ css/                   # tokens · base · layout · components · forms · crop (§6.3)
│     ├─ js/                    # ES-Module: main · i18n · theme · header · api ·
│     │                         #   crop-geometry · crop-rect · crop-info · adjust · report
│     └─ brand/                 # Logo (hell/dunkel/schwarz) und Montserrat als woff2
└─ tests/
   ├─ conftest.py               # Fixtures: synthetische Szene rendern (§9.1)
   ├─ test_detect.py · test_solve.py · test_camera.py · test_thickness.py
   ├─ test_extent.py · test_rectify.py · test_enhance.py
   ├─ test_layout.py · test_markersheet.py · test_pdf_size.py · test_branding.py
   ├─ test_api.py · test_adjust_api.py · test_i18n.py
   ├─ test_conformance.py · test_shared_constants.py · test_backend.py
   ├─ test_startup.py
   └─ test_window.py
```

`app/static/js/` ist bewusst kein einzelnes `app.js` mehr und `app/static/css/` kein einzelnes
`style.css`. Das frühere `app.js` war mit 388 Zeilen deutlich über dem Richtwert und trug Upload,
Parameter, Bericht, Zuschnitt-Rechteck, Export und jede sichtbare Zeichenkette in einer Datei;
`style.css` kannte weder Tokens noch ein zweites Thema. Was jetzt wo liegt, steht in §6.3.

---

## 3 · Rechenkern

### 3.1 Koordinatensysteme

- **Bild:** Pixel, Ursprung oben links, x rechts, y unten (OpenCV).
- **Ebene:** Millimeter, Ursprung = obere linke Ecke des Markerblatts, x rechts, y **unten**.
  Y nach unten vermeidet eine Spiegelung im Warp; die PDF-Erzeugung dreht die y-Achse einmalig
  beim Platzieren (ReportLab rechnet von unten links).
- **Homographie `H`:** Ebene (mm, homogen) → Bild (px, homogen). `H[2,2] = 1`.

### 3.2 Markerblatt-Modus (bekanntes Layout)

Die App erzeugt ihr eigenes A4-Blatt (§5). Das Standardlayout entspricht dem real vermessenen
Blatt: Marker-Kantenlänge **67 mm**, Mittelpunktabstände **121 mm (x) × 171 mm (y)**, mittig auf
A4 hoch. Auf A4 hoch ist diese Zuordnung die einzig mögliche: 121 + 67 = 188 ≤ 210 quer,
171 + 67 = 238 ≤ 297 hoch. Daraus folgen die Mittelpunkte:

| ID | Lage | Mittelpunkt (mm) |
|----|------|------------------|
| 0  | oben links   | (44,5, 63)  |
| 1  | oben rechts  | (165,5, 63) |
| 2  | unten links  | (44,5, 234) |
| 3  | unten rechts | (165,5, 234) |

Die Umrechnung *zwei Abstände → vier Mittelpunkte* steht genau einmal, in
`config.sheet_marker_centers()`; Markerblatt-Erzeugung und Homographie benutzen beide diese
Funktion.

**Druckerskalierung.** Es wird nichts hochgerechnet. Der Bediener misst am Ausdruck die
Markerkante **und** beide Mittelpunktabstände und trägt alle drei Werte ein; die Homographie
benutzt genau diese Zahlen. Damit fällt eine Druckerskalierung heraus, ohne dass irgendwo ein
versteckter Faktor sitzt — ein Faktor, der nur die Markerkante skaliert und die Abstände
mitzieht, wäre schon dann falsch, wenn der Drucker in x und y unterschiedlich skaliert.

Eckpunkte eines Markers mit Zentrum `(cx, cy)` und Kantenlänge `s`, in der Reihenfolge, die
OpenCV liefert (TL, TR, BR, BL):

```
TL = (cx − s/2, cy − s/2)   TR = (cx + s/2, cy − s/2)
BR = (cx + s/2, cy + s/2)   BL = (cx − s/2, cy + s/2)
```

Homographie aus allen erkannten Markern (≥ 2 Marker = 8 Punkte) mit
`cv2.findHomography(..., method=cv2.LMEDS)`, danach nichtlineare Nachoptimierung des
Reprojektionsfehlers (`scipy.optimize.least_squares`, 8 Unbekannte). Bei genau **einem**
erkannten Marker entfällt LMEDS: die vier Ecken gehen direkt in
`cv2.getPerspectiveTransform` (exakt bestimmt, ohne Redundanz — siehe Warnung in §7).

Erkennt die App nur Marker mit IDs außerhalb `{0,1,2,3}`, meldet sie das und schlägt den
Frei-Modus vor.

### 3.3 Frei-Modus (unbekanntes Layout)

Bekannt ist nur `s`. Homographie **und** Markerpositionen werden gemeinsam geschätzt.

- **Unbekannte:** `h11..h32` (8, mit `h33 = 1`) + Offsets `(tx_i, ty_i)` für `i = 1..n−1`.
  Marker 0 ist auf `(0,0)` verankert (Eichfreiheit der Translation).
- **Modell:** Ebenenkoordinate von Marker `i`, Ecke `j`:
  `p_ij = (tx_i, ty_i) + s · u_j` mit `u_j ∈ {(0,0), (1,0), (1,1), (0,1)}`.
- **Residuum:** `‖ π(H · p̃_ij) − q_ij ‖` in px, `q_ij` = detektierte Bildecke.
- **Bestimmtheit:** `8 + 2(n−1)` Unbekannte gegen `8n` Gleichungen — für `n = 4`: 14 gegen 32.
- **Startwert:** Marker mit der größten Bildfläche, `cv2.getPerspectiveTransform` von seinen vier
  Bildecken auf `{(0,0), (s,0), (s,s), (0,s)}`. Die übrigen Marker werden mit `H⁻¹` in die Ebene
  zurückprojiziert; `(tx_i, ty_i) = Schwerpunkt − (s/2, s/2)`.
- **Lösung:** `scipy.optimize.least_squares` (Methode `trf`, Verlust `linear`).

**Vorausgesetzt wird gleiche Ausrichtung aller Marker** (auf einem gedruckten Blatt gegeben).
Geprüft wird das über den Winkel der zurückprojizierten TL→TR-Kante je Marker relativ zum
Ankermarker; über `MARKER_ROT_WARN_DEG` gibt es eine Warnung. Wer die Marker wirklich verstreut
liegen hat, nimmt §3.4.

`n = 1` ist zulässig (8 Unbekannte, 8 Gleichungen, exakt), wird aber deutlich als redundanzfrei
gewarnt.

### 3.4 Streu-Modus (beliebige Winkel)

Der Frei-Modus setzt gleiche Ausrichtung voraus. Liegen die Marker verstreut auf einer
Fläche — jeder so, wie er gefallen ist —, gilt das nicht, und das Ergebnis ist dann nicht
etwa ungenau, sondern falsch: auf der synthetischen Szene misst der Frei-Modus einen
500-mm-Abstand als 148 mm und meldet RMS 71 px
(`tests/test_solve.py::test_freimodus_scheitert_an_gedrehten_markern`).

Der Streu-Modus ist derselbe Ausgleich mit **einer Unbekannten mehr je Marker**.

- **Unbekannte:** `h11..h32` (8) + `(x_i, y_i, θ_i)` für `i = 1..n−1`.
- **Modell:** Ebenenkoordinate von Marker `i`, Ecke `j`:
  `p_ij = (x_i, y_i) + R(θ_i) · s · (u_j − (½, ½))`. Gedreht wird um den **Mittelpunkt**;
  um die Ecke gedreht wäre jede Drehung zugleich eine Verschiebung.
- **Bestimmtheit:** `8 + 3(n−1)` gegen `8n` — für `n = 4`: 17 gegen 32. Jeder weitere Marker
  bringt **fünf** Bestimmungsstücke netto ein statt sechs; der Frei-Modus bleibt deshalb der
  genauere, wenn seine Annahme stimmt. Er ist kein überholter Vorläufer, sondern der engere Fall.
- **Startwert:** wie im Frei-Modus, dazu `θ_i` aus dem Winkel der zurückprojizierten
  TL→TR-Kante — sie zeigt im Marker selbst in `+x`, ihr Winkel in der Ebene *ist* die Drehung.
- **Warnung:** `marker_rotation` entfällt hier. Unterschiedliche Winkel sind der Normalfall
  dieses Modus und keine Auffälligkeit.

#### Die Ebene richtet sich nach dem FOTO

In den anderen beiden Modi legt das Blatt beziehungsweise der Ankermarker Ursprung und Achsen
fest. Hier kann das nicht sein: der größte Marker liegt in einem zufälligen Winkel, und der
Zuschnitt ist ein **achsparalleles** Rechteck — die Schablone stünde schief, und um das Objekt
herum ginge Rand verloren.

Zum Schluss wird deshalb umgerechnet:

- **Achsen:** gesucht ist die Drehung, nach der die Abbildung Ebene → Bild möglichst wenig dreht.
  Für die 2×2-Jacobimatrix `J` in der Mitte der Markerwolke ist die nächstgelegene Drehung
  `φ = atan2(J₁₀ − J₀₁, J₀₀ + J₁₁)`; die Ebene wird um `−φ` gedreht. Übrig bleibt eine
  **symmetrische** Streckung — die perspektivische Verkürzung, die sich nicht wegdrehen lässt.
- **Ursprung:** die Mitte der Markerwolke.

Rechnerisch ist das `H' = H · M` mit `M` = Drehung um `−φ` plus Verschiebung in die Mitte; die
Markerlagen werden mit `M⁻¹` mitgeführt. Weil `M` eine **Bewegung** ist, bleiben alle Abstände
Millimeter — die Umrechnung kostet nichts an Maßhaltigkeit.

**Ein einzelner Marker reicht** (in jedem Modus): vier Punktpaare bestimmen eine Homographie
exakt, denn der Marker trägt sein Koordinatensystem selbst — die Eckenreihenfolge ist über sein
Bitmuster festgelegt. Was er nicht trägt, ist eine Probe: das Residuum ist dann null, ohne dass
der Fehler klein wäre. Dafür gibt es `single_marker`.

**Kollinearitätsmaß** (in allen Modi geprüft, ab 2 Markern): Fläche der konvexen Hülle der
Marker-**Mittelpunkte**, geteilt durch das Quadrat des größten Mittelpunktabstands. Unter
`COLLINEARITY_WARN` ⇒ Warnung.

Das Maß muss auf den Mittelpunkten beruhen, nicht auf der Hülle aller Ecken: jeder Marker bringt
selbst 67 mm Ausdehnung mit, sodass drei Marker in einer Reihe eine völlig unauffällige
Eckenhülle ergeben und die Warnung nie käme. Beim Standardlayout liegt das Maß bei 0,47, bei drei
Markern in einer Reihe bei 0.

### 3.4 Kamerapose aus `H` (Weg A, automatisch)

**Brennweite in Pixel.** Aus EXIF `FocalLengthIn35mmFilm` (Tag 41989):

```
f_px = f35 / 36 mm · max(W, H)        # 35-mm-Äquivalent bezieht sich auf 36 × 24 mm
```

Hauptpunkt = Bildmitte `(W/2, H/2)`, `K = [[f_px,0,cx],[0,f_px,cy],[0,0,1]]`.

**Zerlegung.** Mit `M = K⁻¹ H`, Spalten `m1, m2, m3`:

```
λ  = 2 / (‖m1‖ + ‖m2‖)
r1 = λ m1,  r2 = λ m2,  t = λ m3
falls t_z < 0:  λ ← −λ   (Ebene muss vor der Kamera liegen)
r3 = r1 × r2 ;  R = orthonormalisiert([r1 r2 r3]) via SVD:  R = U Vᵀ
```

Daraus:

```
C   = −Rᵀ t                    # Kamerazentrum in Ebenenkoordinaten (mm)
d   = |C_z|                    # Kamerahöhe über der Markerebene
N   = (C_x, C_y)               # Lotpunkt der Kamera in der Ebene (mm)
θ   = arccos(|R₃₃|)            # Neigung gegen die Ebenennormale
```

**Fallback-Kette (Weg B):**

1. EXIF `FocalLengthIn35mmFilm` vorhanden → `source = "exif"`.
2. Sonst: Feld „Kameraabstand" wird zur Pflichteingabe, Lotpunkt = Bildmitte in die Ebene
   zurückprojiziert → `source = "manual"`.
3. Ist `d` außerhalb `[CAM_HEIGHT_MIN_MM, CAM_HEIGHT_MAX_MM]`, gilt das Ergebnis als
   unplausibel (Warnung `camera_height_implausible`) und die manuelle Eingabe wird erzwungen.

**Ein eingetippter Abstand schlägt die Schätzung**, auch wenn EXIF eine liefert: `source` wird
dann `"manual"`, die Höhe ist die eingetippte, Lotpunkt und Neigung bleiben die aus der
Zerlegung. Ein Hinweis (`camera_height_override`) nennt beide Werte, damit ein Vertipper
auffällt statt still zu wirken. Wer eine Zahl einträgt, meint sie — das Feld wäre sonst eine
Attrappe.

Bei `thickness_mm == 0` wird die Pose nur informativ berechnet und angezeigt; ein Fehlschlag
blockiert dann nichts (`source = "none"`, Hinweis `camera_pose_unknown`).

Die UI zeigt `d`, `N` und `θ` an — das ist die Plausibilitätsprüfung für den Bediener
(„Kamera ca. 870 mm über der Blattebene, 12° schräg").

### 3.5 Dickenkorrektur

Markerebene bei `Z = 0`, Kamera bei `C = (N_x, N_y, d)`, Objektoberfläche bei `Z = h`.
Der Sehstrahl von `C` durch den Objektpunkt `Q = (Q_x, Q_y, h)` trifft `Z = 0` bei

```
t = d / (d − h)
T = N + t · (Q − N)
```

Ein Punkt der Objektoberfläche erscheint in der entzerrten Ebene also **radial vom Lotpunkt weg
gestreckt** um `k = d/(d−h)`. Rückrechnung: `Q = N + (T − N)/k`.

Umgesetzt als Vorschaltmatrix, nicht als Nachskalierung des Rasterbilds:

```
A = [[k, 0, N_x(1−k)],
     [0, k, N_y(1−k)],
     [0, 0, 1      ]]
H_eff = H · A
```

`h = 0` ⇒ `A = I`. Negative `h` (Objektoberfläche unter der Markerebene) sind erlaubt (`k < 1`).
`h ≥ d` ist ein Fehler.

**Größenordnung.** `h/d = 20/900 = 2,2 %`. Ein Fehler von 10 % in `d` hinterlässt nur ≈ 0,2 %
Restfehler — die Korrektur ist gegenüber `d` unkritisch, gegenüber `h` nicht.

**Aufnahmeregeln, die die UI als Hinweis anzeigt:** Markerblatt möglichst *auf* der
Objektoberfläche; sonst Objektdicke eintragen. Tele (1× oder 2×), großer Abstand, Objekt mittig
im Bild — das minimiert die nicht korrigierte Objektivverzeichnung.

### 3.6 Abbildbarer Ebenenbereich

`Hi = H_eff⁻¹` bildet Bild → Ebene. Punkte mit `Hi[2] · p̃ = 0` liegen im Unendlichen
(Horizont). Vorgehen:

1. Vorzeichen `σ = sign(Hi[2] · c̃)` am Schwerpunkt der Markerecken bestimmen.
2. Das Bildrechteck als Polygon gegen `σ · (Hi[2] · p̃) > ε` clippen (Sutherland–Hodgman,
   `ε = HORIZON_EPS · |Hi[2] · c̃|`).
3. Das geclippte Polygon in die Ebene zurückprojizieren, Bounding-Box bilden.
4. Gegen die um `EXTENT_HULL_FACTOR · Hülldiagonale` aufgeweitete Hüll-Bounding-Box schneiden —
   Schutz gegen absurde Extents bei flachem Blickwinkel.

Bleibt nach dem Clippen kein Polygon mit mindestens drei Ecken übrig, oder sind zu wenige der
zurückprojizierten Ecken endlich, fällt das Verfahren auf ebendiese aufgeweitete
Hüll-Bounding-Box zurück. Ein kleiner Extent ist ein bedienbares Ergebnis, `inf` wäre keines.

**Vorschau.** Der gesamte Extent wird entzerrt gerendert, mit `px_per_mm` so gewählt, dass die
längere Kante `PREVIEW_MAX_PX` nicht überschreitet.

**Start-Crop.** = Extent, zentriert auf den Hüllschwerpunkt beschnitten auf höchstens
`DEFAULT_CROP_MAX_MM` je Kante. Der Bediener zieht das Rechteck ohnehin selbst.

### 3.7 Qualitätsbericht

**Lokaler Abbildungsmaßstab.** Mehrere Angaben brauchen ein einziges, eindeutig definiertes Maß
für „Pixel pro Millimeter". Definition: Jacobi-Matrix `J` der Abbildung Ebene → Bild
(`π(H · p̃)`), ausgewertet im Schwerpunkt der Markerecken; dann

```
px_per_mm = sqrt(|det J|)          und      mm_per_px = 1 / px_per_mm
```

Dieses Maß wird in §3.7 (RMS in mm), §3.8 (Interpolationswahl) und der PDF-Fußzeile benutzt —
überall dasselbe.

Bei jedem `solve` berechnet und in UI **und** PDF-Fußzeile ausgegeben:

- Reprojektions-RMS in **px** und in **mm** (`rms_mm = rms_px · mm_per_px`).
- Pro Marker die **gemessene** Kantenlänge: die vier Bildecken mit `H⁻¹` zurückprojizieren und
  die vier Seitenlängen mitteln. Abweichung > `MARKER_SIZE_DEV_WARN` ⇒ Warnung. Das deckt
  Objektivverzeichnung, nicht-planaren Aufbau und falsch eingetragene Markergröße auf.
- Kamerahöhe, Lotpunkt, Neigung, Quelle der Brennweite.
- **Extrapolationsanteil:** Flächenanteil des Crop-Rechtecks außerhalb der konvexen Hülle aller
  Markerecken. Der Wert wird immer angezeigt, denn außerhalb der Hülle ist die Homographie am
  unzuverlässigsten; über `EXTRAPOLATION_WARN_FRAC` färbt die Oberfläche ihn ein. Das ist die
  einzige Schwelle ohne serverseitige Warnung, und zwar zwangsläufig: der Zuschnitt wird erst
  **nach** dem Lösen gewählt. Die Schwelle kommt trotzdem vom Server (`limits`, §6.1), damit sie
  auch hier nur einmal existiert.

Keine dieser Prüfungen bricht ab — sie warnen. Abgebrochen wird nur bei den Fehlern aus §7.

### 3.8 Entzerrung

`spp = dpi / 25.4` (Pixel pro mm). Crop `(x0, y0, x1, y1)` in mm ⇒

```
W = round((x1 − x0) · spp)          H = round((y1 − y0) · spp)
S = [[1/spp, 0, x0 + 0.5/spp],
     [0, 1/spp, y0 + 0.5/spp],
     [0, 0,     1           ]]      # Ausgabepixel → mm, Pixelmitten-Konvention
H_total = H_eff · S                 # Ausgabepixel → Quellpixel
cv2.warpPerspective(src, H_total, (W, H),
                    flags = interp | cv2.WARP_INVERSE_MAP,
                    borderMode = cv2.BORDER_CONSTANT, borderValue = (255,255,255))
```

Der `+0.5/spp`-Versatz setzt die Pixelmitten so, dass die **Außenkanten** des Rasters exakt auf
`x0…x1` bzw. `y0…y1` fallen. Nur dadurch stimmt die spätere Platzierung im PDF auf den
Bruchteil eines Millimeters.

**Interpolation:** `INTER_AREA`, wenn `spp < 0.9 · px_per_mm` (Ziel gröber als die Quelle, also
Verkleinerung), sonst `INTER_LANCZOS4`. `px_per_mm` nach der Definition in §3.7.

**Grenze:** `W · H > MAX_OUTPUT_MPX · 1e6` ⇒ Abbruch mit Hinweis, DPI oder Crop zu reduzieren;
die Meldung nennt den größten DPI-Wert aus `DPI_CHOICES`, der noch passt.

### 3.9 Umriss-Erkennung (optional, standardmäßig aus)

Auf dem entzerrten Crop: Graustufen → CLAHE → Gauß (σ = 1 px) → Canny mit Medianschwellen
(`lower = 0.66 · med`, `upper = 1.33 · med`) → morphologisches Schließen (5 px) →
`findContours` → größte Kontur nach Fläche → `approxPolyDP` mit
`epsilon = CONTOUR_EPS_MM · spp`. Fläche < `CONTOUR_MIN_AREA_FRAC` des Crops ⇒ keine Kontur;
das PDF wird dann ohne Kontur gebaut, ohne Meldung — lieber keine Linie als eine falsche. Die
Kontur wird als **Vektorpfad** ins PDF gezeichnet (Linienbreite `CONTOUR_LINE_MM`), auf den
Bildbereich geclippt und zusätzlich zum Foto; ihre Bounding-Box in mm wird in der Fußzeile
ausgewiesen.

**Gesucht wird auf dem aufbereiteten Bild** (§3.10), nicht auf dem rohen. Ursprünglich war das
rohe entzerrte Bild vorgesehen; der Grund für die Änderung: die Regler werden ja gerade deshalb
gestellt, damit eine blasse Bleistiftlinie überhaupt als Kante erscheint — auf dem rohen Bild
fiele sie durch und die Kontur bliebe leer. Umgekehrt wäre eine Kontur aus dem rohen Bild auf
dem aufbereiteten Ausdruck eine zweite, andere Wahrheit auf demselben Blatt. Millimeter kostet
das nichts: die Aufbereitung färbt Pixel, sie verschiebt keine (§3.10, nachgemessen in
`test_enhance.py`) — **welche** Kante gefunden wird, ändert sich, **wo** sie liegt, nicht.

### 3.10 Bildaufbereitung (`app/vision/enhance.py`)

**Die Invariante dieses Moduls: Aufbereitung ist kosmetisch, nie geometrisch.** Sie greift
ausschließlich am bereits entzerrten Bild an, **niemals vor der Markererkennung**. Die
Homographie wird am unberührten Foto gemessen; ein Schärferegler vor dem Detektor würde die
Markerecken verschieben und damit die Millimeter. Daraus folgt hart:

- Form und Datentyp der Ausgabe sind immer die der Eingabe — es wird nicht skaliert, gedreht,
  entzerrt, beschnitten oder umgerandet.
- Jeder Weichzeichner ist symmetrisch. Ein unsymmetrischer Kern wäre eine Verschiebung, nur
  hübsch verpackt.
- Stehen alle Regler neutral (`AdjustOptions.is_identity`), kommt das Bild Bit für Bit zurück —
  aber immer als **neues** Array, damit der Aufrufer hineinzeichnen darf.
- Die Kantenzeichnung färbt genau die Pixel, die Canny als Kante markiert. Sie legt Tinte dazu,
  sie rückt nichts.

**Belegt ist das subpixelgenau** (`tests/test_enhance.py`): gemessen wird die 50-%-Durchgangslage
einer Kante vor und nach jedem einzelnen Eingriff, an einer harten und an einer weichen Kante —
eine harte Kante zeigt jede Verschiebung um ganze Pixel, erst eine weiche hat für ein
Zehntelpixel überhaupt Platz. Ergebnis: **Graustufen, Schwellwert und Kantenanhebung verschieben
die weiche Kante um exakt 0,000000 px** (Toleranz im Test: 0,0 — auf die letzte Stelle gleich,
nicht „fast gleich"). Einzige Ausnahme ist CLAHE: es bildet kachelweise ab, kippt die Flanke
leicht und verschiebt damit den **Ablesepunkt** einer weichen Kante um rund 0,11 px, ohne dass
ein einziges Pixel wandert. Bei 300 dpi sind das **0,009 mm** — drei Zehnerpotenzen unter dem
Millimeter, um den es geht. Zusätzlich gilt an der harten Kante die schärfere Fassung derselben
Aussage: die Menge der dunklen Pixel bleibt pixelgenau dieselbe.

**Die Regler** (`AdjustOptions` als eingefrorene Dataclass — die einzige Definition dieser Namen
und Wertebereiche; `app/schemas.py` spiegelt sie nur für die Leitung, `test_adjust_api.py`
besteht Feld für Feld und Vorgabe für Vorgabe darauf):

| Feld | Bereich | Wirkung |
|---|---|---|
| `grayscale` | bool | Schwarzweiß, aber weiter dreikanalig (die PDF-Einbettung braucht keinen Sonderfall) |
| `invert` | bool | Negativ |
| `brightness` | −1 … 1 | globale Aufhellung, 1.0 = voller Wertebereich |
| `contrast` | −1 … 1 | Spreizung um das Mittelgrau, 1.0 = doppelter Abstand |
| `saturation` | −1 … 1 | Buntheit, über die Grauachse gemischt (nach `grayscale` wirkungslos) |
| `local_contrast` | 0 … 1 | CLAHE auf L in LAB; Clip 1.0 … `ADJUST_CLAHE_CLIP_MAX` |
| `edge_boost` | 0 … 1 | Unschärfemaske, σ = `ADJUST_UNSHARP_SIGMA_PX`, Anteil bis `ADJUST_UNSHARP_MAX` |
| `edge_overlay` | 0 … 1 | Canny-Kanten (`ADJUST_EDGE_CANNY`) als dunkle Linien aufgelegt |
| `color_emphasis` | `none` + Schlüssel aus `ADJUST_EMPHASIS_HUES` | einen Farbton behalten, den Rest entsättigen |
| `emphasis_strength` | 0 … 1 | Stärke der Entsättigung |
| `threshold` | 0 … 1 | harte Schwelle, nur noch Schwarz und Weiß |

CLAHE arbeitet auf **L in LAB**, nie auf B, G und R einzeln: drei getrennte Histogrammspreizungen
ziehen die Kanäle auseinander und färben das Bild um.

**Die Reihenfolge der Stufen ist fest verdrahtet**, damit dieselben Regler morgen dieselbe
Schablone ergeben: Farbbetonung → Schwarzweiß → lokaler Kontrast → Kantenanhebung → Helligkeit
und Kontrast → Sättigung → Kantenzeichnung → Schwelle → Negativ. Jede Stufe hat ihren Grund:
die Farbbetonung arbeitet auf den Farben, wie sie fotografiert wurden; CLAHE steht vor der
globalen Kurve, weil es eine vorher gesetzte Aufhellung kachelweise wieder auffressen würde;
das Negativ steht am Ende, weil sonst jeder Regler davor verkehrt herum wirkte. Zwischen den
Stufen liegt immer `uint8` — das kostet je Stufe höchstens eine Rundungsstelle, macht aber jede
Stufe einzeln abschaltbar.

**Zwei Wege, ein Reglerstand.** `/api/adjust` rechnet auf dem bereits geschriebenen
Vorschau-JPEG, nicht auf einer frischen Entzerrung: der Regler soll während des Ziehens
antworten, und eine Entzerrung des vollen Fotos dauert um Größenordnungen länger. Erlaubt ist
die Abkürzung, weil die Aufbereitung kosmetisch ist — sie taugt am kleinen Bild wie am großen.
Verbindlich für den Druck ist trotzdem allein der Export: der wendet **dieselben** Regler auf das
volle Raster an. Was man sieht, wird gedruckt.

**Stellung in der Kette:** nach §3.8 (Entzerren), vor §3.9 (Kontur) und vor §4 (PDF).

---

## 4 · PDF-Erzeugung

### 4.1 Invariante

**Das entzerrte Bild belegt auf der Seite exakt `crop_w × crop_h` Millimeter.** Diese Invariante
ist die eigentliche Produktzusage und wird in `test_pdf_size.py` geprüft.

### 4.2 Einzelseite

Alles, was nicht Nutzbild ist, lebt in **einem** Streifen unter dem Bild: links übereinander die
zwei Metadatenzeilen und darüber der 100-mm-Maßstab mit seiner Beschriftung, rechts außen die
Marke (§4.6). Ein Streifen statt Rand-plus-Fußzeile, damit sich Maßstab und Text nie um denselben
Platz streiten. Die Marke bekommt ihren Platz **zuerst**, alles andere richtet sich danach und
wird nötigenfalls mit Auslassungszeichen gekürzt — so verschwindet nie etwas unter dem Logo:

```
strip_h = STRIP_H_MM          immer - der Streifen traegt das Markenzeichen (§4.6)
m       = page_margin_mm      Standard PAGE_MARGIN_MM_DEFAULT, bei 0 randlos
page_w  = crop_w + 2m
page_h  = crop_h + 2m + strip_h
Bildrechteck (von unten links) = (m, m + strip_h, crop_w, crop_h)
```

Maßstab und Fußzeile liegen damit **außerhalb** des Nutzbildes und beschneiden die Schablone
nicht. Der Streifen ist auch dann vorhanden, wenn beide abgeschaltet sind: er trägt Logo und
Herkunftszeile, und die gehören auf jedes Blatt. Eine Seite ist dadurch nie exakt so groß wie
das Objekt — die Invariante aus §4.1 betrifft das **Bild**, und die bleibt unberührt.

### 4.3 Kachelung

`sheet_w × sheet_h` ist das **Papierformat** (A4/A3, Ausrichtung s.u.) — nicht zu verwechseln
mit `page_w/page_h` der Einzelseite aus §4.2:

```
usable_w = sheet_w − 2 · printer_margin_mm
usable_h = sheet_h − 2 · printer_margin_mm − strip_h      # strip_h wie in §4.2
step_w   = usable_w − overlap_mm
step_h   = usable_h − overlap_mm
n_cols   = max(1, ceil((crop_w − overlap_mm) / step_w))
n_rows   = max(1, ceil((crop_h − overlap_mm) / step_h))

Kachel (c, r):  crop_x = c · step_w        crop_y = r · step_h
                src_w  = min(usable_w, crop_w − crop_x)
                src_h  = min(usable_h, crop_h − crop_y)
                Bildrechteck = (printer_margin_mm,
                                printer_margin_mm + strip_h + (usable_h − src_h),
                                src_w, src_h)
```

Die **letzte** Kachel einer Reihe oder Spalte ist damit kleiner als die nutzbare Fläche: sie
zeigt genau den Rest des Zuschnitts, sitzt oben in der nutzbaren Fläche und lässt den Rest des
Blattes leer. (Ursprünglich war vorgesehen, die letzte Kachel über den Crop hinauslaufen zu
lassen und weiß zu füllen. Das Ergebnis sähe gleich aus, verschöbe aber den Inhalt nach unten —
und ein Bildrechteck, das mehr Millimeter beansprucht, als es Bild hat, ist genau die Sorte
Nachlässigkeit, die §4.1 verbietet.)

Ausrichtung `auto` wählt die Variante mit weniger Seiten (bei Gleichstand Hochformat); lässt
sich für keine der beiden ein Plan bauen, entscheidet Hochformat, damit `tile_layout` den
aussagekräftigen Fehler wirft. `step_w`/`step_h` müssen positiv sein — ist `overlap_mm ≥
usable_w` oder `≥ usable_h`, bricht der Export mit `overlap_too_large` ab; bleibt nach Rand und
Streifen gar keine Fläche übrig, mit `margins_too_large`.

Jede Kachel trägt: Bildausschnitt, Passermarken an den Überlappungsrändern, Beschriftung
„Blatt `i`/`N` — Spalte `c+1`, Reihe `r+1`", Fußzeile, Marke. Voran steht der **Klebeplan** mit
dem Kachelraster, derselben Numerierung und der Gesamtgröße (`TILE_OVERVIEW_DEFAULT = True`). Er
liegt auf **demselben Papierformat wie die Kacheln**, nicht auf A4 — ein Kachelsatz kommt aus
einem Drucker, und ein Blatt anderen Formats mittendrin ist genau das, was im Fach hängen
bleibt.

**Unter dem Kachelraster liegt der Zuschnitt selbst** — dasselbe entzerrte Bild, das gekachelt
wird, maßstabsgetreu in dasselbe Rechteck gezeichnet. Ohne es sagt der Plan, *wie viele* Blätter
es gibt, aber nicht, *welches* man gerade in der Hand hält. Es ist ein Daumennagel und keine
Schablone: die längere Kante wird auf `OVERVIEW_MAX_PX = 1600` gedeckelt (bei höchstens 250 mm
Bildhöhe rund 160 dpi). Kachelränder und Außenkante bekommen deshalb denselben weißen Saum wie
das Millimeterraster (§4.4) — eine dünne Linie ist auf einem Foto mal sichtbar und mal nicht —
und die Blattnummern stehen auf weißem Träger.

Woher der Daumennagel kommt, hängt am Weg: **am Stück** ist das ganze Raster ohnehin schon
eingebettet und wird wiederverwendet (ein zweites, kleineres Bild wäre reine Dateigröße);
**blattweise** gibt es kein ganzes Raster, also fragt der Bau die Bildquelle einmal nach dem
ganzen Zuschnitt — mit Deckel, damit nicht genau das Raster entsteht, dessen Vermeidung den
Export auf dem Telefon erst möglich gemacht hat (`web/pdf/build.js`). Die Bildquelle nimmt
dafür ein fünftes Argument `maxPx`; null heißt Druckauflösung. In ReportLab wird stattdessen
intern verkleinert, weil dort jedes `drawImage` neu kodiert und nichts mit den Kachelseiten
teilt.

Der Kopf `X-Image-Rect-Mm` meldet im Kachelmodus das Bildrechteck der **ersten** Kachel.

### 4.4 Overlays

| Overlay | Inhalt |
|---|---|
| 100-mm-Maßstab | Balken mit wechselnd gefüllten 10-mm-Feldern, **oben links im Streifen** (§4.2), darüber die Beschriftung „Kontrollmaßstab 100 mm — nachmessen!"; Nachmessen beweist die Skalierung |
| Fußzeile | **zwei Zeilen unten links im Streifen**. Zeile 1: Objektgröße in mm (samt Kontur-Bounding-Box, falls vorhanden), DPI, mm/px, Modus, Marker-IDs und Markergröße. Zeile 2: RMS in px und mm, Kamerahöhe/Neigung und Quelle, Dicke `h` mit Korrekturfaktor `k`, Extrapolationsanteil, Quelldateiname, Datum/Zeit |
| 50-mm-Raster | Linien alle `GRID_STEP_MM` über dem Bild: erst **alle** weißen Säume (`GRID_HALO_PT`), dann **alle** Kernlinien in `GRID_INK` (`GRID_LINE_PT`), damit kein Saum eine bereits gezogene Kreuzung überdeckt. Beschriftung auf weißem Träger, in den Bildbereich hineingeklemmt |
| Passermarken | Schnitt- und Klebemarken plus Überlappungsschraffur an den Kachelrändern (nur Kachelmodus) |

Alle vier standardmäßig aktiv (so vom Nutzer entschieden), einzeln abschaltbar. Der Streifen
selbst bleibt auch dann stehen — er trägt die Marke (§4.6, AGENTS.md, Invariante 3). Im
Kachelmodus kommt rechtsbündig die Blattnummer dazu.

Das Raster wird **zweimal** gezogen, weil es auf hellem *und* dunklem Untergrund lesbar sein
muss: auf Weiß verschwindet der Saum, auf einem dunklen Foto trägt er die Linie. Eine einzelne
graue Linie wäre auf beiden Untergründen halb unsichtbar (AGENTS.md, Invariante 5).

### 4.5 Bildeinbettung

Das entzerrte Raster wird als JPEG (`JPEG_QUALITY`) zwischengespeichert — das hält die Datei
handhabbar groß — und mit `drawImage` auf das exakte mm-Rechteck gesetzt, mit
`preserveAspectRatio=False`: die Rechteckgröße ist gesetzt, nicht abgeleitet. Nichts darf hier
automatisch skaliert werden, sonst fällt §4.1.

### 4.6 Marke

Jedes Blatt trägt rechts im Streifen das Logo (11 mm), links daneben rechtsbündig den Namen
und die Herkunftszeile „Made with Bischof Snowboards Software". Der gesamte Block ist per
`linkURL` auf `BRAND_URL` verlinkt. Betroffen sind Einzelseite, **jede** Kachel, das
Klebeplan-Blatt und das Markerblatt.

Das Logo wird als **Vektor** eingebettet: `svglib` liest dieselbe SVG, die auch die Website
benutzt (`logo-dark.svg`, Tinte #334155), und liefert eine ReportLab-Zeichnung. Damit gibt es
nur eine Quelle für das Logo, und es bleibt bei jeder Druckgröße scharf. Das Parsen ist
gecacht, weil es spürbar dauert.

Ist die Seite schmaler als `block_width_mm() + 70 mm`, entfällt die Textzeile und nur das Logo
bleibt — lieber ein Blatt ohne Schriftzug als eines mit überlappendem Text.

Auf dem Markerblatt sitzt der Block bei y = 5…16 mm. Das ist bewusst tief: zum untersten
Marker bleiben so gut 13 mm weiß, mehr als das eine Markermodul (11,2 mm), auf das die
Erkennung als Ruhezone angewiesen ist.

**Farben.** Die Marken-Tokens stammen aus `snow-service-free/src/main.css` (dort oklch) und
stehen in `config.py` als sRGB, weil PDF und CSS beide Hex brauchen. Gegenprobe der
Umrechnung: `--foreground oklch(0.3717 0.0392 257.29)` ergibt `#334155` — genau die Tinte, die
`logo-dark.svg` im eigenen Dateikommentar nennt.

### 4.7 Sprache der Aufdrucke

Jeder Text auf dem Papier — Dokumenttitel, Maßstabsbeschriftung, beide Fußzeilen, Blattnummer,
Klebeplan, das ganze Markerblatt — kommt aus demselben Katalog wie die Oberfläche (§7.2).
`ExportOptions.locale` trägt die Sprache durch die PDF-Schicht; die Oberfläche schickt beim
Export die Sprache mit, in der sie gerade steht. Ein Ausdruck folgt damit dem Schalter im Kopf
der Seite und nicht der Vorgabesprache des Servers.

**Die Marke bleibt davon unberührt.** „Made with Bischof Snowboards Software" ist ein Zeichen,
kein Satz, und wird nicht übersetzt (AGENTS.md, Invariante 3).

---

## 5 · Markerblatt-PDF

`GET /api/markersheet?marker_mm=&spacing_x_mm=&spacing_y_mm=&locale=` und
`dev.ps1 build-markersheet` erzeugen ein A4-PDF:

- Vier Marker (`DICT_4X4_50`, IDs 0–3) an den Positionen aus §3.2. Die Marker werden **Modul für
  Modul als Vektorrechtecke** gezeichnet (`generateImageMarker` mit 6 × 6 Pixeln liefert die
  Bitmatrix, jedes Modul wird ein Rechteck). Damit sind die Kanten unabhängig von der
  Druckerauflösung absolut scharf — besser als jedes eingebettete Rasterbild, und ohne dass eine
  Rasterauflösung konfiguriert werden müsste.
- Eigener **100-mm-Kontrollmaßstab** und der Hinweis „**Ohne Skalierung drucken (100 %, nicht
  ‚an Seite anpassen')**" samt der Anweisung, danach Markerkante **und** beide
  Mittelpunktabstände zu messen und die *gemessenen* Werte in der App einzutragen.
- Angabe des Layouts (Wörterbuch, Kantenlänge, Mittelpunktabstände, ID-Zuordnung) als Klartext
  auf dem Blatt, dazu die Marke am unteren Rand (§4.6).

`markersheet.sheet_layout(marker_mm, spacing_mm)` liefert die Platzierungsrechtecke und ist die
von `test_markersheet.py` geprüfte SSOT. Nicht-positive Maße lehnt der Endpunkt mit
`bad_marker_size` ab, nicht auf A4 passende mit `sheet_too_small`.

**`?locale=` statt Accept-Language.** Das Blatt wird über einen gewöhnlichen Anker geholt, und
ein Anker kann keinen Kopf mitschicken. Ohne Parameter entscheidet Accept-Language; die
Oberfläche zieht den Parameter bei jedem Sprachwechsel nach (§6.3), sonst käme das Blatt in der
Sprache des Browsers statt in der der App.

---

## 6 · API und Bedienablauf

### 6.1 Endpunkte

Alle JSON-Endpunkte werten `Accept-Language` aus; Fehler und Warnungen kommen in der
ausgehandelten Sprache (§7.2).

**`POST /api/upload`** — multipart, Feld `file`
→ `{ session_id, filename, width, height,
     exif: {focal35_mm, camera_model},
     defaults: {marker_mm, spacing_x_mm, spacing_y_mm, dpi, dpi_choices[],
                overlap_mm, printer_margin_mm, page_margin_mm} }`
HEIC wird per `pillow_heif.register_heif_opener()` gelesen, EXIF-Orientierung mit
`ImageOps.exif_transpose` angewandt, **bevor** irgendetwas detektiert wird.

Die Vorgabewerte kommen mit der Antwort, statt im Frontend zu stehen: `app/config.py` ist die
einzige Stelle für Konstanten (AGENTS.md, Invariante 4), und ein abgeschriebener Standardwert im
Browser wäre die zweite.

**`POST /api/detect`** — der Körper sind die **Bytes** eines Bildes, kein Formular
→ `{ width, height, markers[{id, corners: [[x,y] × 4]}] }`

Die Route des Live-Bildes (§6.3) und die einzige, die **keine Sitzung anlegt**. Der Sucher
schickt rund achtmal in der Sekunde ein Einzelbild und will nur wissen, wo die Marker liegen;
über `/api/upload` und `/api/solve` hieße das, im Sekundentakt Sitzungen samt Foto anzulegen.
Ein Test hält das fest: nach drei Aufrufen ist die Zahl der Sitzungen dieselbe wie davor.

Die Ecken kommen in Pixeln **des eingeschickten Bildes** — deshalb `width`/`height` in derselben
Antwort, sonst könnte das Overlay sie nicht auf seine Bühne rechnen. Der Ortsbetrieb
(`web/vision/local.js`) formt die acht Zahlen des Kerns dafür in vier Paare um; die Antwortform
ist die des Servers, nicht die des Kerns.

**`POST /api/measure?marker_mm&mode&spacing_x_mm&spacing_y_mm`** — Körper wieder die **Bytes**
→ `{ width, height, grid_mm, markers[…],
     plane: { homography[9], hull_mm[[x,y]…], mm_per_px, rms_px, mode_used } | null }`

Dasselbe Einzelbild, aber bis zur Ebene gerechnet — die messende Betriebsart des Live-Bildes
(§6.3). Der Unterschied zu `/api/solve` ist alles andere: keine Sitzung, kein entzerrtes Bild,
keine Vorschau. Zurück kommt genau, was ein Overlay braucht.

**`plane: null` ist kein Fehler.** Keine Marker, zu wenige für den Modus, eine entartete Lage —
im Sucher ist das der Normalzustand, solange die Kamera noch ausgerichtet wird. Ein Fehler färbte
die Oberfläche rot, während gar nichts falsch ist.

`homography` bildet **Millimeter der Ebene auf Bildpixel** ab, zeilenweise als neun Zahlen.
Gerundet wird hier **nicht**: `/api/solve` rundet für seinen Bericht (5 bzw. 3 Nachkommastellen),
und ein Test hält fest, dass beide Wege für dieselben Bytes bis auf die halbe Rundungsstufe
dieselbe Zahl liefern. Was der Sucher anzeigt, muss dasselbe sein, was ein Foto danach ergäbe.

**`POST /api/solve`**
`{ session_id, marker_mm, mode: "sheet"|"free"|"scattered", thickness_mm, camera_height_mm|null,
   spacing_x_mm, spacing_y_mm }`  — die beiden Abstände nur im Blatt-Modus benutzt
→ `{ session_id, mode_used,
     markers[{id, corners_px, side_mm_measured, residual_px, rotation_deg}],
     rms_px, rms_mm, mm_per_px,
     camera{source, focal_px, height_mm, nadir_mm, tilt_deg},
     thickness_mm, scale_correction_k, hull_mm[], extent_mm{x0,y0,x1,y1},
     default_crop_mm{...}, extrapolation_default,
     preview{url, extent_mm, px_per_mm, detected_url},
     limits{dpi_choices[], max_output_mpx, extrapolation_warn},
     elapsed_s, warnings[{code, params, severity, message}] }`

`limits` trägt dieselben Schwellen, gegen die der Server prüft, in die Oberfläche — damit die
Live-Anzeige (§6.3) keine zweite Wahrheit über Pixelgrenze und Extrapolationswarnung braucht.

**`POST /api/adjust`**
`{ session_id, adjust }` — `adjust` ist der Reglersatz aus §3.10, jedes Feld optional
→ `{ preview: {url, extent_mm, px_per_mm} }`

Stehen alle Regler neutral, zeigt `url` auf die unveränderte `rectified`-Vorschau; sonst wird
`adjusted` geschrieben und zurückgegeben. Die URL trägt einen Millisekundenstempel als
Cache-Brecher — die Vorschau wird unter demselben Dateinamen überschrieben, und der Regler tut
das mehrmals je Sekunde; mit sekundengenauem Stempel bekäme der Browser zweimal dieselbe URL und
zeigte das alte Bild. Ohne vorheriges `solve` antwortet der Endpunkt mit `not_solved`.

**`POST /api/export`**
`{ session_id, crop_mm{x0,y0,x1,y1}, dpi, layout: "single"|"tiles",
   page_format: "A4"|"A3", orientation: "auto"|"portrait"|"landscape",
   overlap_mm, printer_margin_mm, page_margin_mm,
   overlays{scalebar, grid, footer, marks}, tile_overview, contour,
   adjust, locale, filename }`
→ `application/pdf` als Download, dazu die Kopfzeilen `X-Page-Size-Mm`, `X-Image-Rect-Mm`,
`X-Pages` (maschinell prüfbar, von `test_pdf_size.py` genutzt).

- `adjust` ist derselbe Reglersatz wie bei `/api/adjust` (§3.10), hier auf das **volle** Raster
  angewandt. Neutral gestellt geht das entzerrte Bild unverändert ins PDF.
- `locale` bestimmt die Sprache der Aufdrucke (§4.7). Ein unbekanntes oder leeres Kürzel wird
  auf die Vorgabesprache abgebildet, nicht abgelehnt: „de-CH" ist kein Bedienfehler, und ein
  Export soll an einer Sprachangabe niemals scheitern.
- `layout` ist standardmäßig **`config.LAYOUT_DEFAULT = "tiles"`**, nicht `"single"`. Ursprünglich
  war die Einzelseite die Vorgabe; geändert, weil eine Schablone in Originalgröße auf kein Blatt
  passt, das hier jemand im Drucker hat — die Einzelseite ist der Sonderfall, nicht der Regelfall.
  Dazu gehört `tile_overview` als Klebeplan, sonst weiß niemand, welches Blatt wohin gehört.
  **Eine Schicht tiefer gilt bewusst das Gegenteil:** `ExportOptions` in `app/pdf/build.py` steht
  auf `layout = "single"`, weil dort „ein Bild, eine Seite" der schlichte Fall ist und Kachelung
  eine Betriebsart, die der Aufrufer verlangt. Wer die beiden gleichzieht, ändert stillschweigend,
  was `test_branding.py` mit einem blanken `ExportOptions()` prüft.
- `filename` ohne `.pdf`-Endung wird auf `schablone.pdf` zurückgesetzt.

**`GET /api/markersheet?marker_mm=&spacing_x_mm=&spacing_y_mm=&locale=`** → `application/pdf`
**`GET /api/preview/{session_id}/{kind}`** → JPEG
(`kind ∈ {original, detected, rectified, adjusted}`)

### 6.2 Ablauf im Browser

Sechs Abschnitte, jeder erst sichtbar, wenn er etwas zu zeigen hat:

1. **Foto** wählen, mit der Kamera-App aufnehmen oder im **Live-Bild** (§6.3) auslösen →
   Dateiname, Bildmaße und die EXIF-Brennweite, falls vorhanden.
2. **Maßstab**: Markergröße in mm (Vorgabe `MARKER_MM_NOMINAL` = 67), Modus, im Blatt-Modus die
   beiden Mittelpunktabstände, Objektdicke (Vorgabe 0), bei Bedarf der Kameraabstand →
   „Entzerren".
3. **Qualität**: der Bericht aus §3.7 und die Warnungen, in drei Tönen abgestuft.
4. **Bildaufbereitung**: die Regler aus §3.10 mit Live-Vorschau, **zugeklappt als Vorgabe**
   hinter einem `<details>`. Elf Regler sind der längste Abschnitt der Seite, und die meisten
   Fotos brauchen keinen einzigen davon; auf dem Telefon lag der Zuschnitt dadurch eine halbe
   Bildschirmhöhe weiter unten (gemessen: 74 px zugeklappt gegen 603 px aufgeklappt). Der
   Abschnitt steht trotzdem **über** dem Zuschnitt — die Regler verändern genau das Bild, das im
   Schritt darunter zugeschnitten wird, und wer sie aufklappt, hat beide untereinander.

   Ein natives `<details>` und kein nachgebautes Aufklappen: Tastatur, Vorlesen und das Suchen im
   Text bringt der Browser mit. Der Winkel ist gezeichnet (zwei Rahmenkanten, gedreht) und ersetzt
   die Systemmarkierung, die auf jeder Oberfläche anders aussieht — dafür braucht es `list-style:
   none` **und** `::-webkit-details-marker`, keines der beiden ersetzt das andere. Der Fehlerplatz
   bleibt außerhalb: eine Meldung hinter einem zugeklappten Winkel ist keine Meldung.
5. **Zuschnitt**: Rechteck auf der entzerrten Vorschau ziehen; darunter live die Kantenlängen in
   mm, die zu erwartende Ausgabegröße in Pixeln und Megapixeln und der Extrapolationsanteil,
   beides gegen die Schwellen aus `limits` eingefärbt. Die vier Kanten lassen sich auch als Zahl
   eintippen.
6. **Druck**: Auflösung, Einzelseite/Kachelung, Papierformat und Überlappung (die beiden letzten
   nur bei Kachelung), Aufdrucke, Kontur → „PDF erzeugen". Der Reglerstand aus Schritt 4 geht mit,
   ebenso die eingestellte Sprache.

Nicht jedes Feld von `ExportRequest` hat einen Bedienknopf: `orientation`, `printer_margin_mm`
und `page_margin_mm` schickt die Oberfläche nicht mit und überlässt sie den Vorgaben aus §8.

### 6.3 Das Live-Bild

**Wozu.** Ob die Marker im Bild sind, ob keiner angeschnitten ist und ob das Licht reicht, sagt
die App bisher erst *nach* dem Entzerren — ein Weg von zwanzig Sekunden, um zu erfahren, dass man
näher hingehen muss. Der Sucher sagt es sofort.

**Zwei Betriebsarten**, umschaltbar in seiner Fußzeile:

| | |
|---|---|
| **Marker** | Je gefundenem Marker Umriss, Nummer und **sein eigenes Koordinatensystem**. Die Achsenrichtungen folgen ohne Rechnung aus der Eckenreihenfolge des Erkenners (TL, TR, BR, BL): x zeigt von Ecke 0 nach Ecke 1, y von Ecke 0 nach Ecke 3. Ein verdrehter Marker ist damit hier zu sehen und nicht erst am Ausdruck. |
| **Ebene messen** | Dieselben Marker, aber daraus gerechnet (`/api/measure`): das **50-mm-Raster der Ebene** liegt im Bild auf dem Werkstück, dazu Maßstab und Restfehler in der Fußzeile. Wer nur wissen will, wie groß etwas ist, liest es hier ab und macht **gar kein Foto**. |

Der Rasterschritt ist derselbe, den der Ausdruck aufdruckt (`GRID_STEP_MM`), und er kommt mit der
Antwort — im Sucher steht keine zweite 50. Fehlt er, wird **kein** Raster gezeichnet: ein
erfundener Schritt wäre ein zweiter Maßstab, und ein falsches Raster ist schlimmer als keines.
Gezeichnet wird nur einen Schritt über die Markerhülle hinaus; weiter draußen wird die
Homographie fortgeschrieben statt gemessen, und ein Raster über das ganze Bild behauptete eine
Genauigkeit, die dort niemand geprüft hat.

Der Restfehler steht **neben** dem Maßstab, weil ein Maßstab ohne ihn eine Behauptung ist:
dieselben 1,3 mm/px können aus einer sauberen Lage kommen oder aus einer verkanteten Fläche, und
nur die zweite Zahl unterscheidet das. Ein Raster, das sich beim Kippen verzieht, sagt außerdem
sofort, dass die Fläche nicht eben ist — das sieht man an keiner Zahl.

**Festgehalten wird nichts.** Weder Sitzung noch Foto; beide Aufrufe rechnen und vergessen.

Vier Entscheidungen tragen ihn:

| | |
|---|---|
| Erkannt wird auf einem **verkleinerten** Einzelbild (längste Kante 960 px, JPEG-Qualität 0,6) | Ein Marker, der darauf nicht mehr gefunden wird, ist im Sucher ohnehin zu klein. Die volle Auflösung achtmal in der Sekunde durch die Erkennung zu schicken kostet mehr, als der Sucher hergibt. |
| Es läuft immer nur **eine** Erkennung | Ohne diese Sperre stauen sich die Anfragen, und was man sieht, gehört zu einem Bild von vor zwei Sekunden. |
| Gezeichnet wird bei **jedem** Bildschirmbild, erkannt alle 120 ms | Das Overlay klebt damit am Video, auch während die Erkennung läuft. |
| Ein `<dialog>` mit `showModal()`, kein Abschnitt im Seitenfluss | Der Sucher will die ganze Fläche; Fokusfang, Esc-Taste und Verdunklung kommen vom Browser. |

Markergröße, Modus und Blattabstände holt der Sucher aus **denselben Feldern** wie das Entzerren
(Schritt 2). Eine eigene Markergröße im Sucher wäre ein zweiter Maßstab neben dem, mit dem
gerechnet wird.

**Der Auslöser** greift das laufende Bild in der Auflösung des Stroms ab (angefragt wird
`ideal: 4096`, was kommt, entscheidet das Gerät) und übergibt es als Datei an denselben Upload
wie die Dateiwahl. Das ist ausdrücklich **nicht** die volle Sensorauflösung — die gibt nur die
Kamera-App des Systems her, und die zeigt kein Overlay. Ein so entstandenes Bild hat außerdem
**kein EXIF**: die Brennweite fehlt, und eine Dickenkorrektur braucht dann den eingetippten
Kameraabstand.

**Wo es ihn nicht gibt.** `navigator.mediaDevices` fehlt in jedem unsicheren Ursprung — eine über
`file://` geöffnete Seite hat es schlicht nicht. Der Knopf bleibt dort verborgen, statt eine
Kamera zu versprechen, die die Umgebung nicht hergibt. Im APK ist der Ursprung
`https://appassets.androidplatform.net` und damit sicher; die Berechtigung dafür beschreibt
`AndroidManifest.xml`.

Ein erneutes „Entzerren" behält den Reglerstand und zieht die Vorschau nach, damit Bild und
Regler wieder zueinander passen.

### 6.3 Aufbau der Oberfläche

Statisch ausgeliefert, kein Build-Schritt: FastAPI hängt `app/static` unter `/`, der Browser
lädt ES-Module und gewöhnliches CSS. Alles, was Tailwind im Webprojekt erzeugt (`@apply`,
`@theme inline`, die `dark:`-Variante), gibt es hier nicht — es täte stillschweigend nichts.

**Module unter `app/static/js/`**, eine Zuständigkeit je Datei:

| Datei | Zuständigkeit |
|---|---|
| `main.js` | Schrittfolge, Sitzungszustand, Verdrahtung. Rechnet und zeichnet nichts |
| `i18n.js` | Katalog laden, `t()`, `richText()`, `applyTranslations()` über `data-i18n` / `data-i18n-attr`, `<html lang>` mitschreiben |
| `theme.js` | helles/dunkles Thema und `readCssThemeVar()` — die eine Stelle, an der ein Token als fertige Farbe gelesen wird |
| `header.js` | Themenknopf, Sprachumschalter, Verweis aufs Markerblatt (zieht `?locale=` nach) |
| `api.js` | jeder Weg zum Server: `Accept-Language` an **jeder** Anfrage, Serverfehler in eine lesbare Form |
| `crop-geometry.js` | reine Rechenfunktionen des Zuschnitts: acht Griffe, Klemmen, Mindestgröße `MIN_CROP_MM` = 5 mm. Kein DOM, kein Zustand — einzeln nachrechenbar |
| `crop-rect.js` | das Canvas-Overlay: Zeichnen, Zeigergesten, Tastatur |
| `crop-info.js` | die Zeile unter dem Bild: mm, Pixel, Extrapolationsanteil |
| `adjust.js` | die Regler aus §3.10 samt Live-Vorschau |
| `report.js` | Qualitätsbericht und Warnungen aus `/api/solve` |
| `live.js` | der Sucher aus §6.3: Kamerastrom, Takt, Auslöser |
| `live-overlay.js` | was er über das Kamerabild malt — Marker, Achsen, Rasterebene |

**Der Zustand hält die rohen Serverantworten**, nicht die fertigen Zeichenketten. Bei einem
Sprachwechsel muss auch schon gezeichneter Text neu entstehen — Bericht, Bildangaben,
Exportmeldung. Wer nur die Zeichenketten behält, kann sie nicht mehr übersetzen und braucht ein
Neuladen der Seite; genau das soll der Schalter im Kopf nicht.

**Zuschnitt-Rechteck.** Acht Griffe (vier Ecken, vier Kantenmitten): eine Ecke ändert beide
Achsen, ein Kantengriff genau eine. Ziehen im Inneren verschiebt, Pfeiltasten verschieben um
1 mm und mit Shift um 10 mm. Vorher ließ sich ein bestehendes Rechteck überhaupt nicht mehr
ändern — man musste ein neues aufziehen. Drei Dinge, ohne die das nicht trägt:

1. **Pointer Events mit `setPointerCapture`.** Ein Finger, der beim Ziehen den Rand des Canvas
   verlässt, verliert die Geste nicht mehr; zusammen mit `touch-action: none` scrollt die Seite
   dabei auch nicht weg.
2. **Der Canvas-Speicher wird mit `devicePixelRatio` bemessen.** Sonst ist das Overlay auf jedem
   Handy und jedem HiDPI-Schirm weichgezeichnet — und eine unscharfe Linie über einer Schnittkante
   ist die falsche Stelle für Unschärfe.
3. **Die Farben kommen per `getComputedStyle` aus `tokens.css`** und werden beim Themenwechsel neu
   gelesen. Ein Canvas löst `var()` nicht auf; wer die Werte einmal liest und behält, malt nach
   dem Umschalten mit den Farben des anderen Themas.

Die Trefferfläche eines Griffs ist 44 px groß (`--touch-target`), gezeichnet wird er kleiner. Die
Ecken stehen in der Trefferliste vorn: bei einem kleinen Rechteck überlappen sich alle acht
Flächen, und eine Ecke ist dann fast immer gemeint.

**Außerhalb des Rechtecks passiert nichts** — kein Fokus, kein Pointer-Capture, kein
`preventDefault`, kein Neuzeichnen. Bis 0.1.4-alpha zog eine Geste dort ein neues Rechteck auf.
Am Finger ist das die falsche Vorgabe: wer das Bild antippt, um es anzusehen, hatte danach einen
Zuschnitt von null Millimetern, und ein Fehlgriff kostete die ganze bisherige Einstellung. Der
Weg zu einem frischen Rechteck ist stattdessen der Knopf **Zuschnitt zurücksetzen**, der
`default_crop_mm` aus der Lösung noch einmal setzt — dieselbe Zahl, nicht eine nachgerechnete.
`hitTest` nennt den Fall seither `outside` statt `new`: der Name benennt die Lage des Punktes und
nicht mehr eine Absicht.

**Live-Regler.** 200 ms Entprellung, und jede Antwort trägt eine Wachnummer. Ohne Entprellung
schickt ein Zug über die halbe Spur dutzende Anfragen; ohne Wachnummer gewinnt die *langsamste*
Antwort das Bild, und der Regler steht dann auf einem Wert, während das Bild einen anderen zeigt.

**Der Extrapolationsanteil unter dem Bild ist eine Schätzung** — ein 40 × 40-Raster gegen die
Marker-Hülle, gerechnet im Browser, damit die Zahl beim Ziehen mitläuft. Verbindlich ist der
Wert, den der Server rechnet und in die PDF-Fußzeile schreibt (§3.7): dieselbe Hülle, aber ohne
Abtastraster. Wo die beiden um ein Prozent auseinanderliegen, hat der Server recht.

**Stil unter `app/static/css/`.** `tokens.css` trägt ausschließlich Tokens (plus `@font-face` und
`color-scheme`) in zwei Ebenen: die Palette `--bfsb-*`, in der jeder Farbwert genau einmal steht,
und darüber die Rollen (`--background`, `--primary`, `--card`, …), die nur auf einen Palettenwert
zeigen. Ein Thema zu wechseln heißt deshalb, ein paar Zeiger umzulegen, nicht dreißig Farben
abzuschreiben. Die Namen sind dieselben wie im Haus-Designsystem des Webprojekts. Die übrigen
Dateien (`base`, `layout`, `components`, `forms`, `crop`) benutzen **nur** die Rollen.

**Thema — drei Zustände, alle drei müssen gehen:** ausdrücklich hell (`<html data-theme="light">`),
ausdrücklich dunkel (`dark`), und gar keine Wahl — dann gilt `prefers-color-scheme`, auch wenn das
System während der Sitzung umschaltet. Ein kurzer Vorspann in `index.html` setzt das Attribut
**synchron vor dem ersten Zeichnen**; ohne ihn blitzt die Seite hell auf und kippt erst mit dem
Modul ins Dunkle. Der `@media`-Block in `tokens.css` schließt `[data-theme="light"]` aus, damit
die Systemvorgabe eine ausdrückliche Wahl nicht überschreibt. Die Wahl liegt in `localStorage`
unter `THEME_STORAGE_KEY`; im privaten Modus gilt sie eben nur für diese Sitzung.

**Sprachwahl.** Ein natives `<select>` im Kopf, das `header.js` aus `/api/locales` füllt — eine
dritte Sprache ist damit eine Katalogdatei plus ein Eintrag in `config.SUPPORTED_LOCALES` und
kein Markup. Darin steht das **Kürzel** der Sprache (`DE`, `EN`), aus dem Code gerechnet und
nicht übersetzt. Der Grund ist die Breite: nur so stehen Markerblatt-Verweis, Sprache und Thema
auf einem Telefon in **einer** Zeile; der Wähler ist deshalb fest 60 px breit.

`0.1.3-alpha` zeigte hier noch den Eigennamen, sobald die Liste aufging — ein Tausch der
Optionstexte auf `mousedown`/`touchstart`/`focus` und zurück auf `change`/`blur`. **Das ist
zurückgenommen.** Auf einem Xiaomi unter Android 15 blieb der Tausch hängen: wer das Systemrad
öffnet und wieder schließt, ohne die Sprache zu *wechseln*, löst weder `change` noch `blur` aus,
und der Wähler stand danach dauerhaft auf `Deutsch` — abgeschnitten in einem Feld, das für zwei
Großbuchstaben breit ist. HTML kennt für eine Option nur **eine** Beschriftung, geschlossen wie
aufgeklappt; jede andere Lösung wäre derselbe Tausch mit demselben Zeitproblem oder ein
nachgebautes Aufklappmenü, und das native `<select>` ist hier Absicht.

Die Startsprache ist die gespeicherte Wahl (`LOCALE_STORAGE_KEY`), sonst die Browsersprache,
sonst Deutsch. Der Katalog wird geladen, **bevor** irgendetwas gezeichnet wird — die Regler
bekommen ihre Beschriftung beim Erzeugen, nicht nachträglich. Schlägt das Laden fehl, bleibt der
Katalog leer und jede Beschriftung zeigt ihren Schlüssel: hässlich und genau deshalb richtig,
denn die Oberfläche bleibt bedienbar und der Fehler ist nicht zu übersehen.

---

## 7 · Fehlerbehandlung

### 7.1 Vokabular: Code, Parameter — kein fertiger Satz

Warnungen (`Notice`) und Abbrüche (`AppError`) tragen einen **Code** und **benannte Parameter**,
niemals einen ausformulierten Satz. Der Satz entsteht erst am Rand — in der HTTP-Antwort, im PDF,
in der Oberfläche — aus dem Sprachkatalog. Ursprünglich stand der deutsche Klartext direkt in
`notices.py`; damit hätte jede Rechenstufe gewusst, in welcher Sprache das Ergebnis später
gelesen wird, und zwei Sprachen wären ohne Umbau nicht möglich gewesen.

```python
notices.warn("high_residual", rms_px="2.4", rms_mm="1.1")
raise AppError("thickness_too_large", "thickness_mm",
               thickness_mm="30", camera_height_mm="25")
```

Ein fachlicher Abbruch wird zu **HTTP 422** mit
`{code, params, field, message}`; eine Warnung erscheint in `warnings[]` als
`{code, params, severity, message}` mit `severity ∈ {info, warn}`. Der gerenderte `message`
bleibt in der Antwort — er kommt aus demselben Katalog wie die Oberfläche und hält `/api/docs`
und jeden Verbraucher, der kein Browser ist, lesbar. Die Oberfläche übersetzt trotzdem bevorzugt
selbst aus `errors.<code>` / `notices.<code>`; `message` ist ihr Ausweg für einen Code, den ihr
Katalog nicht kennt.

`field` benennt das Eingabefeld, an dem der Fehler hängt (`camera_height_mm`, `dpi`, `crop_mm`),
damit die Oberfläche ihn dort zeigen kann, wo er zu beheben ist.

Ein Sonderfall ist `i18n.Phrase`: ein Satzbaustein, dessen **Auswahl** schon beim Rechnen fällt,
dessen **Sprache** aber erst am Rand feststeht — etwa der Auflösungsvorschlag in
`output_too_large` („Mit 200 dpi passt es." gegen „Auch 150 dpi reicht nicht …"). Beim Rendern
wird daraus ein gewöhnlicher String, sodass die HTTP-Antwort nur flache Werte trägt.

### 7.2 Sprachkataloge und Verhandlung

Die Kataloge liegen unter **`app/static/i18n/de.json` und `en.json`** und haben genau zwei Leser:
der Browser holt sie als statische Datei, Python liest dieselbe Datei von der Platte. **Eine Datei
je Sprache, zwei Verbraucher, keine zweite Fassung für den Server** — sonst laufen Oberfläche und
PDF früher oder später auseinander. Beide Kataloge tragen dieselben **184 Schlüssel** unter fünf
Ästen: `document`, `ui`, `notices`, `errors`, `pdf`.

- **Schlüssel** sind Punktpfade (`ui.steps.export.dpi_label`); verschachteltes JSON liest sich
  besser, gesucht wird flach.
- **Platzhalter** heißen `{name}`. Die Schreibweise ist bewusst gewählt: derselbe Ausdruck lässt
  sich in JavaScript mit einer Zeile ersetzen, sodass Server und Oberfläche denselben
  Katalogtext identisch füllen. Ein Platzhalter ohne Wert bleibt **wörtlich stehen** — sichtbar,
  aber harmlos; ein `KeyError` mitten im Fehlertext wäre das schlechtere Ergebnis.
- **Ein fehlender Schlüssel bricht nie ab:** erst Ausweichen auf `DEFAULT_LOCALE`, sonst kommt
  der Schlüssel selbst zurück. Die Lücke fällt im Bildschirm auf, statt den Ablauf zu töten.
- **Kein nacktes `|`** in einem übersetzbaren Text. Dieses Werkzeug benutzt kein vue-i18n, aber
  die Kataloge sind dieselben Dateien wie im Haus, und dort ist `|` der Trenner der Pluralformen.

**Verhandlung.** `i18n.negotiate()` liest `Accept-Language`, sortiert nach `q`-Gewicht und bei
Gleichstand nach der Reihenfolge im Kopf (so gewinnt bei `de,en` das zuerst genannte Deutsch),
und nimmt die erste unterstützte Sprache; `*` und alles Unbekannte fallen auf `DEFAULT_LOCALE`.
`i18n.normalise()` bildet ein einzelnes Kürzel ab („de-CH" → „de", Unsinn → Vorgabe) und wirft
nie. Zwei Wege umgehen den Kopf, weil sie ihn nicht mitschicken können: `/api/markersheet` nimmt
`?locale=` (§5), `/api/export` das Feld `locale` (§4.7).

`tests/test_i18n.py` bewacht das: gleiche Schlüsselmenge in beiden Sprachen, gleiche Platzhalter
je Schlüssel, und **jeder** im Quelltext benutzte `AppError`- und Warncode hat einen
Katalogeintrag.

### 7.3 Fälle

| Fall | Verhalten |
|---|---|
| 0 Marker erkannt | Fehler `no_markers`; die Erkennungs-Vorschau ist trotzdem geschrieben. Hinweise auf Beleuchtung, Schärfe, Blickwinkel |
| 1 Marker | rechnet weiter, laute Warnung `single_marker`: redundanzfrei, kein Fehlermaß möglich |
| Blatt-Modus, keine ID in `{0..3}` | Fehler `no_sheet_ids` mit den gefundenen IDs und dem Vorschlag, in den Frei-Modus zu wechseln |
| Marker nahezu kollinear | Warnung `collinear_markers`, Homographie schlecht konditioniert |
| Marker unterschiedlich rotiert (Frei-Modus) | Warnung `marker_rotation` über `MARKER_ROT_WARN_DEG` — im Streu-Modus entfällt sie, dort ist das der Normalfall |
| RMS über `RMS_WARN_PX` / `RMS_WARN_MM` | Warnung `high_residual`, kein Abbruch |
| gemessene Markergröße weicht ab | Warnung `marker_size_deviation` mit Prozentwert je Marker |
| Crop außerhalb der Hülle | keine Server-Warnung — der Anteil wird in der Oberfläche angezeigt und über `EXTRAPOLATION_WARN_FRAC` eingefärbt (§3.7) |
| eingetippter Kameraabstand vorhanden | Hinweis `camera_height_override`: der eingetippte Wert schlägt die EXIF-Schätzung |
| EXIF-Brennweite fehlt und `h = 0` | Hinweis `camera_pose_unknown`, Pose bleibt leer, nichts blockiert |
| EXIF-Brennweite fehlt und `h ≠ 0` | Fehler `camera_height_required`, Feld `camera_height_mm` |
| `d` unplausibel | Warnung `camera_height_implausible`, Schätzung verworfen; ohne Ersatzwert dann wie oben |
| `h ≥ d` | Fehler `thickness_too_large` |
| Ausgabe > `MAX_OUTPUT_MPX` | Fehler `output_too_large` mit dem größten DPI-Wert aus `DPI_CHOICES`, der noch passt — oder mit dem Rat, den Zuschnitt zu verkleinern |
| Überlappung ≥ nutzbare Kante | Fehler `overlap_too_large` mit der nutzbaren Fläche |
| Rand + Streifen lassen nichts übrig | Fehler `margins_too_large` |
| Zuschnitt ohne Fläche | Fehler `empty_crop` |
| `/api/adjust` oder `/api/export` ohne vorheriges `solve` | Fehler `not_solved` |
| Upload > `MAX_UPLOAD_MB` | Fehler `upload_too_large` |
| Datei nicht lesbar / unbekannter Typ | Fehler `unreadable_image` mit dem Grund aus Pillow |
| Session abgelaufen | Fehler `session_expired`: „Sitzung ist abgelaufen, bitte das Foto erneut hochladen" |

**Jeder** fachliche Fehler kommt als **HTTP 422** in der Form aus §7.1. Ursprünglich waren 413
für den zu großen Upload, 415 für den unbekannten Typ und 404 für die abgelaufene Sitzung
vorgesehen. Vereinheitlicht, weil die Oberfläche damit genau einen Weg hat, einen Fehler zu
lesen — Code, Parameter, Feld —, statt je Statuscode einen eigenen. Reine Schema-Verstöße
(Wert außerhalb des Bereichs, unbekannter Aufzählungswert) bleiben davon unberührt: die beantwortet
Pydantic selbst mit 422 und `detail`, ohne `code`.

---

## 8 · Konstanten (SSOT `app/config.py`, Produktwerte aus `shared/constants.json`)

Für den Python-Code ändert sich nichts: jeder Name unten steht in `app/config.py` und wird
von dort importiert. Woher der *Wert* kommt, ist zweigeteilt. Aussagen über das **Produkt**
— Millimeter, Schwellen, Farben, Papier — stehen in `shared/constants.json` und werden beim
Import gelesen; Aussagen über dieses **Python-Programm** — Pfade, Port, Fassung,
Speicherschlüssel — stehen im Klartext in `config.py`. Grund ist der Umzug auf einen
C++-Kern und eine JavaScript-PDF-Schicht (`docs/cpp-migration/README.md`): drei Sprachen
brauchen dieselben Zahlen, und abgeschriebene Zahlen driften — hier in Millimetern.

Zwei Folgen, beide beabsichtigt: `ARUCO_DICT_ID` steht **nicht** in der sprachneutralen
Datei, sondern wird aus `ARUCO_DICT_NAME` abgeleitet (eine OpenCV-Nummer wäre dort keine
sprachneutrale Angabe), und es gibt **keinen Rückfallwert** — fehlt die Datei, bricht der
Start ab, statt mit halben Konstanten falsch zu messen.

```python
APP_VERSION              = "0.0.2-alpha"           # einzige Fassung; dev.ps1 gibt sie an den
                                                   #   Installer weiter (§10), folgt CHANGELOG.md
APP_VERSION_TUPLE        = (0, 0, 2, 0)            # dieselbe Fassung für Windows' BINÄRE
APP_VERSION_NUMERIC      = "0.0.2.0"               #   Versionsfelder: vier Zahlen, kein "-alpha"
ARUCO_DICT_NAME          = "DICT_4X4_50"
ARUCO_DICT_ID            = cv2.aruco.DICT_4X4_50
MARKER_MM_NOMINAL        = 67.0                    # am realen Blatt gemessen
SHEET_MM                 = (210.0, 297.0)          # A4 Hochformat
SHEET_SPACING_MM         = (121.0, 171.0)          # Mittelpunktabstände x, y
SHEET_MARKER_IDS         = (0, 1, 2, 3)            # TL, TR, BL, BR
SHEET_FORMATS            = {"A4": (210,297), "A3": (297,420)}   # Kachelpapier, immer hoch
sheet_marker_centers(spacing) -> dict[int, (x, y)] # die einzige Umrechnung (§3.2)

DPI_DEFAULT              = 300
DPI_CHOICES              = (150, 200, 300, 400, 600)
MAX_OUTPUT_MPX           = 300
MAX_UPLOAD_MB            = 60
PREVIEW_MAX_PX           = 1600
DEFAULT_CROP_MAX_MM      = 1500.0
JPEG_QUALITY             = 92

RMS_WARN_PX              = 2.0
RMS_WARN_MM              = 1.0
MARKER_SIZE_DEV_WARN     = 0.02                    # 2 %
MARKER_ROT_WARN_DEG      = 2.0
EXTRAPOLATION_WARN_FRAC  = 0.25
COLLINEARITY_WARN        = 0.05                    # Hüllfläche der Mittelpunkte / größter Abstand²
CAM_HEIGHT_MIN_MM        = 100.0
CAM_HEIGHT_MAX_MM        = 10000.0
HORIZON_EPS              = 0.02
EXTENT_HULL_FACTOR       = 3.0

LAYOUT_DEFAULT           = "tiles"                 # Vorgabe der BEDIENUNG (§6.1)
PAGE_MARGIN_MM_DEFAULT   = 5.0
PRINTER_MARGIN_MM_DEFAULT = 5.0
TILE_OVERLAP_MM_DEFAULT  = 10.0
TILE_OVERVIEW_DEFAULT    = True
STRIP_H_MM               = 18.0                    # Streifen unter dem Bild (§4.2)
GRID_STEP_MM             = 50.0
GRID_INK                 = BRAND_INK               # Kernlinie
GRID_LINE_PT             = 0.5
GRID_HALO_PT             = 1.5                     # weißer Saum darunter (§4.4)
GRID_LABEL_PT            = 6.5
SCALEBAR_MM              = 100.0

BRAND_NAME, BRAND_CLAIM, BRAND_URL                 # Herkunftszeile und Ziel (§4.6)
BRAND_COPYRIGHT          = f"Copyright (C) {BRAND_NAME}"   # Dateieigenschaften beider .exe (§10);
                                                   #   ohne Jahr (veraltet sonst) und rein ASCII
                                                   #   (läuft über eine Kommandozeile)
BRAND_INK                = "#334155"               # --foreground
BRAND_PRIMARY            = "#379992"               # --primary
BRAND_ACTION             = "#ffbf00"               # --action
BRAND_DARK               = "#25242b"               # --action-foreground
BRAND_LIGHT              = "#f1f5f9"               # --primary-foreground
BRAND_SECONDARY          = "#e2e8f0"               # --secondary
BRAND_ACCENT             = "#f0f3f3"               # --accent
BRAND_DESTRUCTIVE        = "#e7000b"               # --destructive
LOGO_INK_SVG, LOGO_MM    = static/brand/logo-dark.svg, 11.0
LOGO_BLACK_SVG, LOGO_LIGHT_SVG                     # für dunklen Grund in der Oberfläche
CONTOUR_LINE_MM          = 0.25
CONTOUR_EPS_MM           = 0.5
CONTOUR_MIN_AREA_FRAC    = 0.05

# --- Sprachen (§7.2) ---
LOCALE_DIR               = app/static/i18n         # Browser UND Python lesen dasselbe
SUPPORTED_LOCALES        = ("de", "en")
DEFAULT_LOCALE           = "de"
LOCALE_STORAGE_KEY       = "aruco-language"        # Namensform folgt snow-service-free
THEME_STORAGE_KEY        = "aruco-theme"

# --- Bildaufbereitung (§3.10) ---
ADJUST_CLAHE_TILES       = 8                       # Kachelraster des lokalen Kontrasts
ADJUST_CLAHE_CLIP_MAX    = 4.0                     # Clip-Limit bei Stärke 1.0
ADJUST_UNSHARP_SIGMA_PX  = 2.0                     # Radius der Unschärfemaske
ADJUST_UNSHARP_MAX       = 2.0                     # Anteil der Maske bei Stärke 1.0
ADJUST_EDGE_CANNY        = (60, 160)               # Schwellen der aufgelegten Kantenzeichnung
ADJUST_EMPHASIS_SIGMA_DEG = 25.0                   # halbe Breite des Farbtonfensters (HSV-Grad)
ADJUST_EMPHASIS_HUES     = {red 0, yellow 22, green 60,
                            cyan 90, blue 120, magenta 150}   # OpenCV-HSV, 0..179

SESSION_TTL_S            = 3600
HOST, PORT               = "0.0.0.0", 8000   # PORT ist der BEVORZUGTE Port, keine Zusage
BROWSER_WAIT_S           = 60.0              # wie lange der Browser-Faden auf den Server wartet

# --- Eigenes Fenster (§10) ---
APP_NAME                 = "ArUco-Homographie"     # Anwendung, Fenstertitel, .exe und Ordner
WINDOW_SIZE              = (1200, 860)             # Inhalt 68 rem + Ränder ≈ 1136 px
WINDOW_MIN_SIZE          = (900, 600)              # über dem Umbruchpunkt der Oberfläche
SERVER_STOP_WAIT_S       = 5.0                     # Frist zum Verabschieden nach dem Schließen

PT_PER_MM                = 72 / 25.4               # ReportLab rechnet in Punkt
MM_PER_INCH              = 25.4
```

Die Auswahl der Farbbetonung wird in `schemas.py` **aus** `ADJUST_EMPHASIS_HUES` gebaut, nicht
abgeschrieben: ein neuer Farbton in `config.py` ist damit sofort gültig, statt still an der
Validierung zu scheitern (`test_adjust_api.py` prüft das für jeden Schlüssel).

Außerhalb von `config.py` steht nur, was keine frei gewählte Größe ist: der Wertebereich von
`uint8` und der Farbkreis in `enhance.py`, die Innenaufteilung des Streifens in `overlays.py`.
Eine Ausnahme ist `MAX_SESSIONS = 8` in `session.py` — eine Obergrenze für den Speicherbedarf,
die nichts außerhalb dieses Moduls sieht.

`sys._MEIPASS` voran, wenn das Programm als PyInstaller-Bundle läuft, und liefert sonst
`app/`. Ohne ihn zeigt `Path(__file__).parent` in der `.exe` neben die Daten, und die
Anwendung startet mit nackter Seite — ohne Schrift, ohne Logo, ohne Übersetzung. Davon
abgeleitet: `STATIC_DIR`, `BRAND_DIR`, `LOGO_*_SVG`, `LOCALE_DIR`.

`requirements.txt`:

```
fastapi
uvicorn[standard]
python-multipart
opencv-python-headless>=5.0 # cv2.aruco liegt ab OpenCV 5 im Hauptpaket (geprüft: 5.0.0.93);
                            # headless, weil nie ein cv2-Fenster geöffnet wird
numpy
scipy
Pillow
pillow-heif
reportlab
svglib                      # liest die Logo-SVG als ReportLab-Zeichnung (§4.6)
qrcode
pywebview                   # das eigene Fenster; unter Windows über pythonnet/WinForms
                            # und die WebView2-Laufzeit (§10)
pytest
pypdf
pymupdf                     # rastert das Markerblatt für den Detektortest (§9.2)
httpx                       # von fastapi.testclient für die Ende-zu-Ende-Tests gebraucht
pyinstaller                 # baut die Windows-.exe (dev.ps1 build-exe)
```

---

## 9 · Verifikation

### 9.1 Synthetische Grundwahrheit (`conftest.py`)

Kein Augenschein, sondern gerechnete Wahrheit: virtuelle Kamera mit gewählten `f_px`, `R`, `t`;
Markerbilder aus `cv2.aruco.generateImageMarker`; ein Testobjekt bekannter Größe in bekannter
Höhe `h`. Die Fixture rendert das „Foto" per projektiver Abbildung und gibt alle
Wahrheitswerte mit zurück. Damit braucht kein Test ein externes Werkzeug oder ein echtes Foto.

Das Objekt in Höhe `h` wird an seiner **scheinbaren** Stelle auf der Ebene `z = 0` gezeichnet
(`T = N + k(Q − N)`). Optisch ist das dasselbe Bild — und die Pipeline muss daraus wieder `Q`
machen.

**Der Renderer muss vor dem Warp tiefpassfiltern.** `warpPerspective` kann nicht flächenmitteln;
die Ebene wird mit 12 px/mm gerendert und auf rund 2 px/mm im Foto verkleinert. Ohne Vorfilterung
verschiebt das Aliasing die Markerecken um mehrere Zehntelpixel — der Test misst dann den
Renderer statt den Detektor. Gemessen: 0,58 px maximaler Eckenfehler ohne Gauß gegen 0,23 px mit
Gauß (σ = 0,5 · Verkleinerungsfaktor), bei sonst identischem Code. Der Gauß ist symmetrisch und
verschiebt Kanten daher nicht.

### 9.2 Tests und Toleranzen

| Test | Prüft | Toleranz |
|---|---|---|
| `test_detect` | IDs und Subpixel-Ecken auf der synthetischen Szene | Ecken < 0,3 px |
| `test_solve` (Blatt, rauschfrei) | rückgewonnene Objektmaße | < 1e-6 mm, RMS < 1e-6 px |
| `test_solve` (Blatt, ±0,2 px Rauschen) | Maß über 500 mm | < 0,5 mm |
| `test_solve` (Frei, rauschfrei) | Maße und rückgewonnenes Layout | < 1e-6 mm |
| `test_solve` (Streu, rauschfrei) | Maße, Winkeldifferenzen, Ursprung | < 1e-6 mm bzw. Grad |
| `test_solve` (Streu, Ausrichtung) | Markerwinkel gegen das Foto | < 0,1 Grad (Rest = Scherung) |
| `scattered.test.mjs` | dieselben Aussagen durch das WebAssembly | wie oben, Rest-Drehung < 1e-9 Grad |
| `test_solve` (Frei, ±0,2 px Rauschen) | Maß über 500 mm | < 1,0 mm |
| `test_solve` (Degeneriert) | kollinear / 1 Marker / fremde IDs erzeugen die richtigen Codes | exakt |
| `test_camera` | `d`, Lotpunkt, Neigung gegen Wahrheit | `d` < 0,5 %, `N` < 1 mm, `θ` < 0,1° |
| `test_thickness` | **beide Richtungen**: ohne Korrektur muss der Fehler ≈ `h/d` sein (Szene ist also aussagekräftig), mit Korrektur | unkorrigiert 2,2 % ± 0,2 %; korrigiert < 0,05 mm |
| `test_extent` | Horizont-Clipping liefert endlichen, konvexen Extent bei flachem Blickwinkel | keine `inf`/`nan`, Extent ⊂ Klammer |
| `test_rectify` | 100-mm-Quadrat bei 300 dpi; Testobjekt im Raster über die 50-%-Flanke subpixelgenau nachgemessen | 1181 px exakt; Objektmaß < 0,3 mm |
| `test_layout` | Kachelzahl gegen Formel; jeder Crop-Millimeter auf ≥ 1 Kachel; Überlappung eingehalten | exakt |
| `test_enhance` | Bildaufbereitung (§3.10): Kantenlage vor/nach **jedem** Regler, an harter und weicher Kante; Silhouette pixelgenau; Form, Typ und Unberührtheit der Eingabe; jedes Feld des Vertrags hat einen Fall | Graustufen/Schwelle/Kantenanhebung **0,0 px**; CLAHE ≤ 0,02 px hart, ≤ 0,15 px weich (gemessen 0,11 px ≙ 0,009 mm bei 300 dpi) |
| `test_markersheet` | Platzierungsrechtecke gegen `SHEET_MARKER_CENTERS_MM`; alle Marker innerhalb A4 mit ≥ 8 mm Ruhezone; Seite = A4. Zusätzlich wird das erzeugte Blatt **gerastert und durch den echten Detektor geschickt** — ein vertauschtes Modulraster sähe am Bildschirm normal aus und fiele sonst erst am realen Foto auf | Layout < 0,01 mm; zurückgemessen Kante und beide Abstände < 0,15 mm |
| `test_pdf_size` | MediaBox und Bildrechteck gegen §4.2 (via `pypdf`, 1 mm = 2,834645669 pt); Seitenzahl im Kachelmodus | < 0,01 mm |
| `test_branding` | die Marke auf **jedem** Blatt: Einzelseite, jede Kachel, Klebeplan, Markerblatt — auch mit abgeschaltetem Maßstab und abgeschalteter Fußzeile; Verlinkung über die Link-Annotationen; schmale Seite behält wenigstens das Logo | exakt |
| `test_api` | Ende-zu-Ende über HTTP: Upload → Solve → Export; Kopfzeilen gegen die berechnete Geometrie; Vorgabe ist die Kachelung auf A4; der Ausdruck folgt der mitgeschickten Sprache; Fehlerpfade (`not_solved`, `session_expired`) | exakt |
| `test_adjust_api` | die Regler über die Leitung: Pydantic-Modell spiegelt die Dataclass **Feld für Feld und Vorgabe für Vorgabe**; jeder Farbton aus `config` wird angenommen, ein fremder abgelehnt; Negativ schlägt bis in die Bildpunkte durch; **ein Export mit Aufbereitung hat dieselbe Seitengröße, dasselbe Bildrechteck und dieselbe Seitenzahl wie einer ohne** | Geometrie identisch, Inhalt verschieden |
| `test_i18n` | beide Kataloge tragen dieselben Schlüssel und je Schlüssel dieselben Platzhalter; jeder im Quelltext benutzte Fehler- und Warncode hat einen Eintrag; `negotiate`/`normalise` über neun bzw. vier Fälle; Rückfall Englisch → Deutsch → Schlüssel; Umlaute wirklich im Katalog | exakt |
| `test_backend` | der Umschalter zwischen den Kernen und der **Quervergleich** zwischen ihnen: beide finden auf den eingefrorenen Szenen dieselben Ecken, mit und ohne CLAHE; der Kontrastschalter bewegt in **beiden** Kernen die Ecken (ein still ignorierter Schalter sähe im Vergleich wie Einigkeit aus); der C++-Kern kennt die Konstanten aus `shared/constants.json`; ein Tippfehler in `ARUCO_CORE` wird abgewiesen statt still zu Python | Kerne ≤ 1e-3 px (gemessen 0,0 px — Ecke für Ecke bitgleich) |
| `test_window` | die Wahl der Betriebsart aus der Kommandozeile: Vorgabe Fenster, `--browser`, `--no-browser`, beide zusammen, jeweils mit und ohne `--port`; und der Rückfall auf den Browser in **allen drei** Sorten von Fehlschlag — pywebview fehlt, die Anzeige-Maschine wäre MSHTML, das Aufbauen wirft. Das Fenster selbst zu öffnen ist hier nicht prüfbar; die Entscheidung davor ist es, und sie ist der Teil, der still falsch wird | exakt |


Erst wenn diese Tests grün sind, gilt die Maßhaltigkeit als belegt.
**Stand 2026-09-08: 183 Tests, alle grün** — mit dem Python-Kern (`.\dev.ps1 run-tests`)
und mit dem C++-Kern (`.\dev.ps1 run-tests-cpp`), **dieselbe Zahl in beiden Läufen**.

### 9.3 Manuelle Abschlussprobe

Markerblatt drucken → Marker messen → Foto eines Objekts bekannter Größe → PDF erzeugen →
drucken → 100-mm-Maßstab und Objektmaß mit dem Messschieber prüfen. Ergebnis wird im README
dokumentiert.

**Diese Probe ist zur Hälfte erbracht (2026-09-07).** Am gedruckten Blatt wurden der
100-mm-Kontrollmaßstab **und** das 50-mm-Raster mit dem Messschieber nachgemessen, beide richtig.

Damit ist der Teil `PDF → Drucker → Papier` belegt: die Seitengeometrie stimmt, und der Drucker
skaliert nicht.

**Der zweite Teil dieser Probe — das Objektmaß — steht aus**, und das ist kein Formalismus. Die
Reihenfolge oben nennt beides aus gutem Grund: Maßstab und Raster zeichnet die PDF-Schicht (§4.2)
aus **denselben** Millimeterzahlen, in denen der Zuschnitt angegeben ist. Eine falsche
Homographie ergäbe eine falsch große Schablone, auf der beide trotzdem tadellos mäßen — sie
können diesen Fehler prinzipiell nicht sehen. Nur ein Gegenstand **bekannter Größe im Foto**,
auf dem Ausdruck nachgemessen, prüft `Foto → Marker → Millimeter`.

Wer das Erfolgskriterium aus §1 zitiert, zitiert bis dahin eine halb belegte Zusage: die
Druckkette ist gemessen, die Messkette nicht.

---

## 10 · Werkzeuge

`dev.ps1` nach der `setup-repo`-Skill, also mit **beschreibenden** Kommandonamen (nicht den
Kurznamen des Nachbarprojekts):

| Kommando | Wirkung |
|---|---|
| `install-deps` | venv anlegen, pip aktualisieren, `requirements.txt` installieren |
| `start-server` | Server im **Vordergrund** starten, URL ausgeben, Oberfläche im eigenen Fenster zeigen, LAN-URL + QR |
| `run-tests` | `pytest -q` |
| `build-markersheet [mm] [x] [y]` | Markerblatt nach `out/markerblatt_A4.pdf` |
| `build-exe` | Windows-Bundle nach `dist/ArUco-Homographie/` (PyInstaller, One-Folder) |
| `build-installer` | Windows-Installer nach `dist/ArUco-Homographie-Setup-<Fassung>.exe` (Inno Setup) |
| `kill-servers` | nur Server **aus diesem Verzeichnis** beenden — `app.main` wie gebaute `.exe` |
| `clean-all` | venv, `out/`, `build/`, `dist/`, Caches entfernen |
| `help` | die Liste ausgeben (auch die Vorgabe ohne Argument) |

`start-server` liest den bevorzugten Port aus `app/config.py` (keine zweite Wahrheit) und zeigt
ihn an. Die **Oberfläche öffnet `app.main` selbst** und nicht der Aufrufer: erst dort steht fest,
welcher Port es geworden ist, denn beim Ausweichen wäre jede vorher gebaute URL falsch. `--port N`
verschiebt den *Wunsch*-Port — ausgewichen wird danach wie immer; ein unbrauchbarer Wert bricht
nicht ab, sondern fällt auf `config.PORT` zurück, denn ein Doppelklick, der an einem
Komfortargument scheitert, wäre schlechter als einer auf dem Vorgabeport.

**Wie sich die Oberfläche zeigt**, entscheidet `app.window.choose_ui_mode` — eine reine Funktion
über den Argumenten, damit die Entscheidung prüfbar ist, auch wenn das Fenster selbst es nicht
ist (§9.2):

| Schalter | Betriebsart |
|---|---|
| *(keiner)* | **eigenes Fenster** — der Doppelklick soll ein Programm aufmachen, keinen Reiter |
| `--browser` | Browser des Systems, in einem Daemon-Faden, der wartet, bis der Port antwortet — so erscheint nie eine Fehlerseite, weil der Server noch nicht bereit war |
| `--no-browser` | **weder noch**, nur der Server |

`--no-browser` sticht `--browser`, wenn beide dastehen: seine Bedeutung ist „nichts aufmachen",
und daran hängt die Freigabeprüfung, die die Anwendung ohne Anzeige hochfährt.

Im Fenstermodus laufen **Server und Fenster auf verschiedenen Fäden**: beide wollen den
Hauptfaden — uvicorn läuft dort normalerweise, pywebview besteht darauf — also bekommt ihn das
Fenster, und der Server einen Daemon-Faden daneben. Wird das Fenster geschlossen, bittet
`app.main` den Server über `should_exit` zu Ende und wartet `SERVER_STOP_WAIT_S`; als Daemon
überlebt er den Prozess ohnehin nicht.

**Kann dieser Rechner kein Fenster zeigen, ist das kein Abbruch.** `app.window.show` sagt in
einer Konsolenzeile, was fehlt, gibt `False` zurück, und der Browser tritt ein — der Server läuft
in jedem Fall weiter, sonst wäre ein Werkstattrechner ohne WebView2-Laufzeit auch vom Handy aus
nicht mehr zu gebrauchen. Drei Fälle: pywebview ist nicht installiert; das Aufbauen wirft; oder
pywebview würde mit **MSHTML** zeichnen. Der letzte ist der heikle: ohne WebView2-Laufzeit fällt
pywebview unter Windows wortlos auf die alte IE-Maschine zurück, und die kennt keine ES-Module —
das Fenster ginge auf und bliebe leer. Ein leeres Fenster sieht aus wie ein Absturz ohne Meldung,
also wird **vor** dem Öffnen gefragt, womit gezeichnet würde (`webview.initialize().renderer`),
und MSHTML abgelehnt.

Zwei Vorgaben von pywebview sind ausdrücklich zurückgestellt, damit sich das Fenster verhält wie
der Browser-Reiter, den es ersetzt: `text_select=True` (sonst spritzt pywebview
`user-select: none` ein) und `zoomable=True` (sonst ist Strg+Mausrad gesperrt). Und es läuft
**nicht** im Privatmodus (`private_mode=False`), weil Sprache und Thema im `localStorage` stehen
und den nächsten Start überleben sollen.

`build-exe` ruft die versionierte Bauvorschrift `aruco-homographie.spec` auf. **One-Folder, nicht
One-File:** One-File entpackt bei jedem Start OpenCV, NumPy und SciPy in ein Temp-Verzeichnis und
kostet Sekunden Startzeit für nichts. Mit muss von Hand, weil die statische Analyse es nicht
findet: der ganze Baum `app/static/**` (Oberfläche, Logo-SVGs, Montserrat-`.woff2`,
i18n-Kataloge), die Datendateien von ReportLab und **zweierlei für pywebview** — die
Anzeige-Module `webview.platforms.winforms` und `.edgechromium` als `hiddenimports` (sie werden
erst zur Laufzeit über einen Namen gezogen) sowie der Ordner `webview/js` als Datendateien. Den
sammelt der mitgelieferte PyInstaller-Hook **nicht**, er nimmt nur `webview/lib` mit den
WebView2-DLLs; ohne die JavaScript-Dateien stirbt der Fensterstart mit „Cannot find JS
directory", und die `.exe` zeigt statt des Fensters den Rückfall auf den Browser. Im Quellbaum
fällt das nicht auf. Weitergegeben wird der ganze Ordner, nicht nur die `.exe` darin.

**Die Dateieigenschaften der Anwendung** entstehen ebenfalls dort, in einem `VSVersionInfo`-Block.
Ohne ihn sind sie **leer** — PyInstaller legt von sich aus keine Versionsressource an, und
Rechtsklick → Eigenschaften → Details zeigte dann nicht einmal einen Herausgeber. Gesetzt werden
`CompanyName`, `ProductName`, `FileDescription`, `FileVersion`, `ProductVersion`,
`LegalCopyright`, `InternalName`, `OriginalFilename` und `Comments`. Die Spec-Datei ist selbst
Python, also **importiert** sie `app/config.py` und `app/i18n.py`, statt irgendetwas abzuschreiben;
die Beschreibung ist `ui.header.subtitle` aus dem Katalog — derselbe Satz wie in der Kopfzeile,
denn eine sichtbare Zeichenkette gehört in den Katalog (§7.2). Fehlt der Schlüssel, bricht der Bau
ab, statt den Schlüsselnamen in die ausgelieferte `.exe` zu schreiben.

**Ausgefüllte Eigenschaften sind keine Signatur.** SmartScreen nennt weiterhin keinen Herausgeber;
dafür braucht es ein Code-Signing-Zertifikat und nichts sonst.

`build-installer` verpackt genau diesen Ordner mit Inno Setup zu **einer** Datei
(`dist/ArUco-Homographie-Setup-<Fassung>.exe`, rund 78 MB bei `lzma2/max` und
`SolidCompression`). Der Modus bleibt One-Folder — der Installer ersetzt das Bundle nicht, er
umhüllt es; One-File entpackte weiterhin bei jedem Start. Vier Entscheidungen, die dort begründet
stehen (`installer/aruco-homographie.iss`):

- **`PrivilegesRequired=lowest`, Ziel `{localappdata}\Programs\ArUco-Homographie`.** Wer an einem
  Werkstattrechner sitzt, ist oft kein Administrator. Und weil der Installer den Pfad wählt statt
  des Benutzers beim Entpacken, ist die MAX_PATH-Falle für diesen Weg ausgeräumt.
- **`AppId` ist eine feste GUID und darf nie geändert werden** — daran erkennt Windows eine
  vorhandene Installation. Eine neue Kennung stellte die nächste Fassung daneben, und dann lägen
  zwei Bundles à 290 MB auf der Platte.
- **Keine Zahl doppelt.** Fassung (`config.APP_VERSION`, dazu `APP_VERSION_NUMERIC` für das
  binäre `VersionInfoVersion`), Herausgeber (`BRAND_NAME`), Adresse (`BRAND_URL`) und
  Urheberrechtsvermerk (`BRAND_COPYRIGHT`) kommen als `/D`-Definitionen von `dev.ps1`, das sie aus
  `app/config.py` liest. Inno Setup kann kein Python importieren; fehlt eine Definition, bricht
  die Übersetzung mit einer Erklärung ab, statt still eine Vorgabe einzusetzen. Die
  `VersionInfo*`-Anweisungen setzen die Eigenschaften der **Setup**-`.exe` — nicht zu verwechseln
  mit denen der Anwendung, die aus `aruco-homographie.spec` kommen.
- **`ISCC.exe` wird gesucht, nicht festgeschrieben** — `PATH`, dann die Installation pro Benutzer
  (`%LOCALAPPDATA%\Programs\Inno Setup 6\`, die *nicht* im `PATH` steht), dann beide
  `Program Files`. Fehlt sie, nennt die Fehlermeldung das winget-Paket `JRSoftware.InnoSetup`.

Selbstheilung über einen Stempel: `venv/.deps-installed` enthält den SHA-256 von
`requirements.txt`. Fehlt das venv oder ändert sich die Datei, installiert jedes Run-Kommando
vorher automatisch nach. `.vscode/tasks.json` ruft ausschließlich `dev.ps1` auf.

`.gitignore` sperrt venv, Caches, `/out/` und die Streuner von Testläufen aus. Zwei Regeln, die
dort im Kopf stehen und beim Erweitern gelten: Muster, die nur den Projektstamm meinen, fangen
mit `/` an (`out/` finge auch ein `app/out/` mit ein), und **nie nach Dateiendung allein
aussperren** — in `app/static/` liegen echte Bildbestandteile (Favicons, Logos), ein pauschales
`*.png` hätte sie stillschweigend aus dem Repo geworfen. `.vscode/tasks.json` ist ausdrücklich
versioniert.

Die beiden Bauvorschriften sind dagegen versioniert — `aruco-homographie.spec` und
`installer/aruco-homographie.iss` sind Quelltext, nicht Erzeugnis. `/dist/` fängt beides ab,
was sie erzeugen: den Bundle-Ordner und die Setup-`.exe` daneben.

---

## 11 · Nicht im Umfang (v1)

Dieses Dokument beschreibt, was **existiert**. Was gebaut werden *soll*, steht in
[`docs/plans.md`](../../plans.md) und gehört ausdrücklich nicht hierher — zwei Listen von
Absichten laufen auseinander, sobald eine davon abgearbeitet wird.

- **Objektivverzeichnung.** Mit vier koplanaren Markern nicht sauber abtrennbar. Der Solver ist
  bereits als Least-Squares gebaut; ein radialer Parameter `k1` kann später als weitere
  Unbekannte eingehängt werden (im Blatt-Modus mit 16 Punkten identifizierbar). Standardmäßig
  aus, als Ausbaustufe vorgesehen.
- Livebild-Aufnahme im Browser, Stapelverarbeitung, Nutzerkonten, dauerhafte Speicherung über
  die TTL hinaus. Sitzungen leben nur im Arbeitsspeicher; ein Neustart des Servers wirft eine
  laufende Arbeit weg.
- **DXF/SVG-Export der Kontur für die CNC** ist hier nicht gebaut (`contour.py` liefert den Pfad
  in mm, mehr nicht). Er ist inzwischen ein beauftragtes Vorhaben — der Lösungsweg samt
  Stolpersteinen steht in `docs/plans.md`, nicht hier.
- Nicht-planare Objekte. Eine Homographie beschreibt genau eine Ebene; gewölbte Deckel bleiben
  außerhalb dessen, was dieses Verfahren leisten kann.
