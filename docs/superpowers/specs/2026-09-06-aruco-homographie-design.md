# ArUco-Homographie — Design / Spezifikation

**Datum:** 2026-09-06
**Status:** umgesetzt — dieses Dokument ist mit dem Code abgeglichen (2026-09-06)
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

```
Handy/Browser ──upload──▶ /api/upload   ──▶ Session (Temp-Verzeichnis, TTL 1 h)
              ──solve───▶ /api/solve    ──▶ Marker, Homographie, Kamerapose, Qualitätsbericht,
                                            entzerrte Vorschau + mm-Extent
              (Crop-Rechteck im Browser ziehen, live mm-Anzeige)
              ──export──▶ /api/export   ──▶ PDF (einzeln oder gekachelt)
                          /api/markersheet ──▶ A4-Markerblatt-PDF
```

Der Server bindet auf `0.0.0.0` und **bevorzugt** Port 8000; ist der belegt, weicht er auf einen
freien aus (`app.main.choose_port`). Ein fester Port wäre auf einem Werkstattrechner eine Wette,
und ein Start, der mit „address already in use" abbricht, sieht aus wie ein kaputtes Programm.
Beim Start gibt er die LAN-URL plus ASCII-QR-Code auf der Konsole aus, damit das Foto direkt vom
Handy hochgeladen werden kann, und öffnet den Browser auf dem Port, der es tatsächlich geworden
ist. Er läuft im Vordergrund (`dev.ps1 start-server` blockiert); `dev.ps1 kill-servers` beendet
hängengebliebene Instanzen.

### 2.1 Dateien — ein Concern pro Datei, ≤ 300 Zeilen Code

```
ArUco-Homographie/
├─ dev.ps1                      # install-deps | start-server | run-tests | build-markersheet
│                               # | build-exe | kill-servers | clean-all
├─ aruco-homographie.spec       # PyInstaller-Bauvorschrift (One-Folder), versioniert
├─ requirements.txt
├─ README.md
├─ .gitignore
├─ .vscode/tasks.json
├─ docs/superpowers/specs/2026-09-06-aruco-homographie-design.md
├─ app/
│  ├─ __init__.py
│  ├─ main.py                   # FastAPI-App, Routen, Static-Mount, Startbanner (LAN-URL + QR)
│  ├─ config.py                 # SSOT aller Konstanten (§8)
│  ├─ schemas.py                # Pydantic-Request/Response-Modelle (SSOT der API-Typen)
│  ├─ notices.py                # Vokabular für Warnungen und Abbruchfehler (Code + Klartext)
│  ├─ pipeline.py               # Orchestrierung der Rechenkette, hält main.py auf Transport
│  ├─ session.py                # Upload-/Ergebnis-Store im Temp-Verzeichnis, TTL-Aufräumung
│  ├─ vision/
│  │  ├─ __init__.py
│  │  ├─ geometry.py            # projektive Grundrechenarten, von mehreren Modulen geteilt
│  │  ├─ detect.py              # EXIF-Rotation, HEIC, CLAHE, ArUco + Subpixel-Refinement
│  │  ├─ solve.py               # Homographie: Blatt-Modus + Frei-Modus, Residuen, Hülle
│  │  ├─ camera.py              # Brennweite aus EXIF, H-Zerlegung → Höhe, Lotpunkt, Neigung
│  │  ├─ thickness.py           # Dickenkorrektur → effektive Homographie
│  │  ├─ extent.py              # abbildbarer Ebenenbereich (Horizont-Clipping)
│  │  ├─ rectify.py             # warpPerspective in exaktes mm-Raster bei Ziel-DPI
│  │  └─ contour.py             # optionale Umriss-Erkennung im entzerrten Bild
│  ├─ pdf/
│  │  ├─ __init__.py
│  │  ├─ layout.py              # Seiten- und Kachelgeometrie (SSOT der Druckgeometrie)
│  │  ├─ overlays.py            # 100-mm-Maßstab, 50-mm-Raster, Fußzeile, Passermarken
│  │  ├─ build.py               # PDF-Bau: Einzelseite, Kachelung, Übersichtsseite
│  │  └─ markersheet.py         # A4-Markerblatt generieren
│  └─ static/
│     ├─ index.html
│     ├─ app.js                 # Upload, Parameter, Vorschau, Crop-Rechteck mit mm-Anzeige
│     └─ style.css
└─ tests/
   ├─ conftest.py               # Fixtures: synthetische Szene rendern (§9.1)
   ├─ test_detect.py
   ├─ test_solve.py
   ├─ test_camera.py
   ├─ test_thickness.py
   ├─ test_extent.py
   ├─ test_rectify.py
   ├─ test_layout.py
   ├─ test_markersheet.py
   ├─ test_pdf_size.py
   ├─ test_branding.py
   ├─ test_enhance.py
   ├─ test_i18n.py
   ├─ test_adjust_api.py
   ├─ test_api.py
   └─ test_startup.py
```

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
Ankermarker; über `MARKER_ROT_WARN_DEG` gibt es eine Warnung.

`n = 1` ist zulässig (8 Unbekannte, 8 Gleichungen, exakt), wird aber deutlich als redundanzfrei
gewarnt.

**Kollinearitätsmaß** (in beiden Modi geprüft, ab 2 Markern): Fläche der konvexen Hülle der
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
   unplausibel und die manuelle Eingabe wird erzwungen.

Bei `thickness_mm == 0` wird die Pose nur informativ berechnet und angezeigt; ein Fehlschlag
blockiert dann nichts (`source = "none"`).

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
  Markerecken. Über `EXTRAPOLATION_WARN_FRAC` ⇒ Warnung; der Wert wird immer angezeigt, denn
  außerhalb der Hülle ist die Homographie am unzuverlässigsten.

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
`epsilon = CONTOUR_EPS_MM · spp`. Fläche < `CONTOUR_MIN_AREA_FRAC` des Crops ⇒ keine Kontur,
Hinweis in der UI, PDF wird ohne Kontur gebaut. Die Kontur wird als **Vektorpfad** ins PDF
gezeichnet (Linienbreite `CONTOUR_LINE_MM`), zusätzlich zum Foto; ihre Bounding-Box in mm wird
in der Fußzeile ausgewiesen.

---

## 4 · PDF-Erzeugung

### 4.1 Invariante

**Das entzerrte Bild belegt auf der Seite exakt `crop_w × crop_h` Millimeter.** Diese Invariante
ist die eigentliche Produktzusage und wird in `test_pdf_size.py` geprüft.

### 4.2 Einzelseite

Alles, was nicht Nutzbild ist, lebt in **einem** Streifen unter dem Bild — links der
100-mm-Maßstab, rechts der Metadatentext. Ein Streifen statt Rand-plus-Fußzeile, damit sich
Maßstab und Text nie um denselben Platz streiten:

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
Bildrechteck je Kachel = (printer_margin_mm, printer_margin_mm + strip_h, usable_w, usable_h)
```

Kachel `(c, r)` zeigt den Crop-Bereich ab `c · step_w` bzw. `r · step_h`; die letzte Kachel
läuft über den Crop hinaus und wird weiß gefüllt. Ausrichtung `auto` wählt die Variante mit
weniger Seiten (bei Gleichstand Hochformat). `step_w`/`step_h` müssen positiv sein — ist
`overlap_mm ≥ usable_w` oder `≥ usable_h`, ist die Überlappung für das Papierformat zu groß und
der Export bricht mit Klartextmeldung ab.

Jede Kachel trägt: Bildausschnitt, Passermarken an den Überlappungsrändern, Beschriftung
„Blatt `i`/`N` — Spalte `c+1`, Reihe `r+1`", Fußzeile. Voran steht eine **Übersichtsseite**
(A4) mit dem Kachelraster, derselben Numerierung und der Gesamtgröße
(`TILE_OVERVIEW_DEFAULT = True`).

### 4.4 Overlays

| Overlay | Inhalt |
|---|---|
| 100-mm-Maßstab | bemaßter Balken mit 10-mm-Teilung, **links im Streifen** (§4.2); Nachmessen beweist die Skalierung |
| Fußzeile | **rechts im Streifen**: Objektgröße in mm, Datum/Zeit, Quelldateiname, DPI, mm/px, Modus, Marker-IDs, RMS in px und mm, Kamerahöhe/Neigung, Dicke `h`, Korrekturfaktor `k`, Extrapolationsanteil, Rand- und Streifenhöhe |
| 50-mm-Raster | dünne graue Linien (`GRID_GRAY`) alle `GRID_STEP_MM` über dem Bild, mit mm-Beschriftung an den Rändern |
| Passermarken | Schnitt- und Klebemarken plus Überlappungsschraffur an den Kachelrändern (nur Kachelmodus) |

Alle vier standardmäßig aktiv (so vom Nutzer entschieden), einzeln abschaltbar.

### 4.5 Bildeinbettung

Das entzerrte Raster wird als JPEG (`JPEG_QUALITY`) bzw. bei Bildern mit Alpha als PNG
zwischengespeichert und mit `drawImage` auf das exakte mm-Rechteck gesetzt. Kein
`preserveAspectRatio`-Automatismus — die Rechteckgröße ist gesetzt, nicht abgeleitet.

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

---

## 5 · Markerblatt-PDF

`GET /api/markersheet?marker_mm=&spacing_x_mm=&spacing_y_mm=` und `dev.ps1 build-markersheet`
erzeugen ein A4-PDF:

- Vier Marker (`DICT_4X4_50`, IDs 0–3) an den Positionen aus §3.2. Die Marker werden **Modul für
  Modul als Vektorrechtecke** gezeichnet (`generateImageMarker` mit 6 × 6 Pixeln liefert die
  Bitmatrix, jedes Modul wird ein Rechteck). Damit sind die Kanten unabhängig von der
  Druckerauflösung absolut scharf — besser als jedes eingebettete Rasterbild, und ohne dass eine
  Rasterauflösung konfiguriert werden müsste.
- Eigener **100-mm-Kontrollmaßstab** und der Hinweis „**Ohne Skalierung drucken (100 %)** — danach
  Markerkante und beide Mittelpunktabstände messen und die gemessenen Werte in der App eintragen."
- Angabe des Layouts (Kantenlänge, Mittelpunktabstände, ID-Zuordnung) als Klartext auf dem Blatt.

`markersheet.sheet_layout(marker_mm, spacing_mm)` liefert die Platzierungsrechtecke und ist die
von `test_markersheet.py` geprüfte SSOT. Passen Markergröße und Abstände nicht auf A4, lehnt der
Endpunkt mit `sheet_too_small` ab.

---

## 6 · API und Bedienablauf

### 6.1 Endpunkte

**`POST /api/upload`** — multipart, Feld `file`
→ `{ session_id, width, height, preview_url, exif: {focal35, focal_px, model}, warnings[] }`
HEIC wird per `pillow_heif.register_heif_opener()` gelesen, EXIF-Orientierung mit
`ImageOps.exif_transpose` angewandt, **bevor** irgendetwas detektiert wird.

**`POST /api/solve`**
`{ session_id, marker_mm, mode: "sheet"|"free", thickness_mm, camera_height_mm|null,
   spacing_x_mm, spacing_y_mm }`  — die beiden Abstände nur im Blatt-Modus benutzt
→ `{ markers[{id, corners_px, side_mm_measured, residual_px}], mode_used, rms_px, rms_mm,
     mm_per_px_mean, camera{source, focal_px, height_mm, nadir_mm, tilt_deg},
     thickness_mm, scale_correction_k, hull_mm[], extent_mm{x0,y0,x1,y1},
     default_crop_mm{...}, preview{url, extent_mm, px_per_mm}, warnings[{code,message,severity}] }`

**`POST /api/export`**
`{ session_id, crop_mm{x0,y0,x1,y1}, dpi, layout: "single"|"tiles",
   page_format: "A4"|"A3", orientation: "auto"|"portrait"|"landscape",
   overlap_mm, printer_margin_mm, page_margin_mm,
   overlays{scalebar, grid, footer, marks}, tile_overview, contour, filename }`
→ `application/pdf` als Download, dazu die Kopfzeilen `X-Page-Size-Mm`, `X-Image-Rect-Mm`,
`X-Pages` (maschinell prüfbar, von `test_pdf_size.py` genutzt).

**`GET /api/markersheet?marker_mm=…`** → `application/pdf`
**`GET /api/preview/{session_id}/{kind}`** → JPEG (`kind ∈ {original, detected, rectified}`)

### 6.2 Ablauf im Browser

1. Foto wählen (oder vom Handy hochladen) → Vorschau mit eingezeichneten erkannten Markern.
2. Markergröße in mm eintragen (Standard 50), Modus wählen, Objektdicke eintragen (Standard 0).
3. „Entzerren" → Qualitätsbericht (§3.7) und entzerrte Vorschau erscheinen.
4. Crop-Rechteck ziehen; die Kantenlängen werden live in mm angezeigt, ebenso der
   Extrapolationsanteil und die zu erwartende Ausgabegröße in Pixel und MB.
5. Druckoptionen setzen (DPI, Einzelseite/Kachelung, Overlays, Kontur) → „PDF erzeugen".

---

## 7 · Fehlerbehandlung

| Fall | Verhalten |
|---|---|
| 0 Marker erkannt | Fehler mit Erkennungs-Vorschau; Hinweise auf Beleuchtung, Schärfe, Blickwinkel |
| 1 Marker | rechnet weiter, laute Warnung „redundanzfrei, kein Fehlermaß möglich" |
| Blatt-Modus, keine ID in `{0..3}` | Fehler mit Vorschlag, in den Frei-Modus zu wechseln |
| Marker nahezu kollinear | Warnung, Homographie schlecht konditioniert |
| Marker unterschiedlich rotiert (Frei-Modus) | Warnung über `MARKER_ROT_WARN_DEG` |
| RMS über `RMS_WARN_PX` / `RMS_WARN_MM` | Warnung, kein Abbruch |
| gemessene Markergröße weicht ab | Warnung mit Prozentwert je Marker |
| Crop außerhalb der Hülle | Warnung mit Flächenanteil |
| EXIF-Brennweite fehlt und `h ≠ 0` | „Kameraabstand" wird Pflichtfeld (HTTP 422 mit Feldname) |
| `d` unplausibel | wie oben, Pflichtfeld |
| `h ≥ d` | Fehler „Objektdicke muss kleiner als der Kameraabstand sein" |
| Ausgabe > `MAX_OUTPUT_MPX` | Fehler mit konkretem DPI-Vorschlag, der passt |
| Upload > `MAX_UPLOAD_MB` oder unbekannter Typ | HTTP 413 / 415 mit Klartext |
| Session abgelaufen | HTTP 404 „Sitzung abgelaufen, bitte Foto erneut hochladen" |

Alle Meldungen deutsch, Warnungen mit `code` (maschinenlesbar) und `severity ∈ {info, warn}`.

---

## 8 · Konstanten (SSOT `app/config.py`)

```python
ARUCO_DICT_NAME          = "DICT_4X4_50"
MARKER_MM_NOMINAL        = 67.0                    # am realen Blatt gemessen
SHEET_MM                 = (210.0, 297.0)          # A4 Hochformat
SHEET_SPACING_MM         = (121.0, 171.0)          # Mittelpunktabstände x, y
SHEET_MARKER_IDS         = (0, 1, 2, 3)            # TL, TR, BL, BR
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

PAGE_MARGIN_MM_DEFAULT   = 5.0
PRINTER_MARGIN_MM_DEFAULT = 5.0
TILE_OVERLAP_MM_DEFAULT  = 10.0
TILE_OVERVIEW_DEFAULT    = True
STRIP_H_MM               = 18.0                    # Maßstab links, Metadaten rechts (§4.2)
GRID_STEP_MM             = 50.0
GRID_INK                 = BRAND_INK               # Kernlinie
GRID_LINE_PT             = 0.5
GRID_HALO_PT             = 1.5                     # weisser Saum darunter (§4.4)
GRID_LABEL_PT            = 6.5
SCALEBAR_MM              = 100.0

BRAND_NAME, BRAND_CLAIM, BRAND_URL                 # Herkunftszeile und Ziel (§4.6)
BRAND_INK                = "#334155"               # --foreground
BRAND_PRIMARY            = "#379992"               # --primary
BRAND_ACTION             = "#ffbf00"               # --action
BRAND_DARK               = "#25242b"               # --action-foreground
LOGO_INK_SVG, LOGO_MM    = static/brand/logo-dark.svg, 11.0
CONTOUR_LINE_MM          = 0.25
CONTOUR_EPS_MM           = 0.5
CONTOUR_MIN_AREA_FRAC    = 0.05

SESSION_TTL_S            = 3600
HOST, PORT               = "0.0.0.0", 8000   # PORT ist der BEVORZUGTE Port, keine Zusage
BROWSER_WAIT_S           = 60.0              # wie lange der Browser-Faden auf den Server wartet
```

Alle Pfade auf **mitgelieferte Dateien** laufen über `config.resource_path()`. Der Helfer stellt
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
svglib                      # Logo als Vektor ins PDF (§ Marke)
qrcode
pytest
pypdf
pymupdf                     # PDF-Seiten für Prüfungen rastern
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
| `test_solve` (Frei, ±0,2 px Rauschen) | Maß über 500 mm | < 1,0 mm |
| `test_solve` (Degeneriert) | kollinear / 1 Marker / fremde IDs erzeugen die richtigen Codes | exakt |
| `test_camera` | `d`, Lotpunkt, Neigung gegen Wahrheit | `d` < 0,5 %, `N` < 1 mm, `θ` < 0,1° |
| `test_thickness` | **beide Richtungen**: ohne Korrektur muss der Fehler ≈ `h/d` sein (Szene ist also aussagekräftig), mit Korrektur | unkorrigiert 2,2 % ± 0,2 %; korrigiert < 0,05 mm |
| `test_extent` | Horizont-Clipping liefert endlichen, konvexen Extent bei flachem Blickwinkel | keine `inf`/`nan`, Extent ⊂ Klammer |
| `test_rectify` | 100-mm-Quadrat bei 300 dpi; Testobjekt im Raster über die 50-%-Flanke subpixelgenau nachgemessen | 1181 px exakt; Objektmaß < 0,3 mm |
| `test_layout` | Kachelzahl gegen Formel; jeder Crop-Millimeter auf ≥ 1 Kachel; Überlappung eingehalten | exakt |
| `test_markersheet` | Platzierungsrechtecke gegen `SHEET_MARKER_CENTERS_MM`; alle Marker innerhalb A4 mit ≥ 8 mm Ruhezone; Seite = A4 | < 0,01 mm |
| `test_pdf_size` | MediaBox und Bildrechteck gegen §4.2 (via `pypdf`, 1 mm = 2,834645669 pt); Seitenzahl im Kachelmodus | < 0,01 mm |
| `test_api` | Ende-zu-Ende über HTTP: Upload → Solve → Export; Kopfzeilen gegen die berechnete Geometrie; Fehlerpfade (`not_solved`, `session_expired`) | exakt |
| `test_startup` | Portwahl weicht einem belegten Port aus; Banner überlebt eine Konsole ohne Blockzeichen; Datenpfade folgen `sys._MEIPASS` im Bundle und dem Quellbaum ohne | exakt |

Erst wenn diese Tests grün sind, gilt die Maßhaltigkeit als belegt.
**Stand 2026-09-07: 153 Tests, alle grün** (`.\dev.ps1 run-tests`).

### 9.3 Manuelle Abschlussprobe

Markerblatt drucken → Marker messen → Foto eines Objekts bekannter Größe → PDF erzeugen →
drucken → 100-mm-Maßstab und Objektmaß mit dem Messschieber prüfen. Ergebnis wird im README
dokumentiert.

---

## 10 · Werkzeuge

`dev.ps1` nach der `setup-repo`-Skill, also mit **beschreibenden** Kommandonamen (nicht den
Kurznamen des Nachbarprojekts):

| Kommando | Wirkung |
|---|---|
| `install-deps` | venv anlegen, pip aktualisieren, `requirements.txt` installieren |
| `start-server` | Server im **Vordergrund** starten, URL ausgeben, Browser öffnen, LAN-URL + QR |
| `run-tests` | `pytest -q` |
| `build-markersheet [mm] [x] [y]` | Markerblatt nach `out/markerblatt_A4.pdf` |
| `build-exe` | Windows-Bundle nach `dist/ArUco-Homographie/` (PyInstaller, One-Folder) |
| `kill-servers` | nur Server **aus diesem Verzeichnis** beenden — `app.main` wie gebaute `.exe` |
| `clean-all` | venv, `out/`, `build/`, `dist/`, Caches entfernen |

`start-server` liest den bevorzugten Port aus `app/config.py` (keine zweite Wahrheit) und zeigt
ihn an. Den **Browser öffnet `app.main` selbst**, in einem Daemon-Faden, der wartet, bis der Port
antwortet — so erscheint nie eine Fehlerseite, weil der Server noch nicht bereit war. Es muss dort
geschehen und nicht im Aufrufer: erst dort steht fest, welcher Port es geworden ist, denn beim
Ausweichen wäre jede vorher gebaute URL falsch. `--no-browser` unterdrückt das.

`build-exe` ruft die versionierte Bauvorschrift `aruco-homographie.spec` auf. **One-Folder, nicht
One-File:** One-File entpackt bei jedem Start OpenCV, NumPy und SciPy in ein Temp-Verzeichnis und
kostet Sekunden Startzeit für nichts. Mit muss von Hand, weil die statische Analyse es nicht
findet: der ganze Baum `app/static/**` (Oberfläche, Logo-SVGs, Montserrat-`.woff2`,
i18n-Kataloge) und die Datendateien von ReportLab. Weitergegeben wird der ganze Ordner, nicht nur
die `.exe` darin.

Selbstheilung über einen Stempel: `venv/.deps-installed` enthält den SHA-256 von
`requirements.txt`. Fehlt das venv oder ändert sich die Datei, installiert jedes Run-Kommando
vorher automatisch nach. `.vscode/tasks.json` ruft ausschließlich `dev.ps1` auf.

`.gitignore`: `venv/`, `__pycache__/`, `*.pyc`, `out/`, `build/`, `dist/`, `.pytest_cache/`,
`*.log`, `Thumbs.db`. Die Bauvorschrift `aruco-homographie.spec` ist dagegen versioniert — sie
ist Quelltext, nicht Erzeugnis.

---

## 11 · Nicht im Umfang (v1)

- **Objektivverzeichnung.** Mit vier koplanaren Markern nicht sauber abtrennbar. Der Solver ist
  bereits als Least-Squares gebaut; ein radialer Parameter `k1` kann später als weitere
  Unbekannte eingehängt werden (im Blatt-Modus mit 16 Punkten identifizierbar). Standardmäßig
  aus, als Ausbaustufe vorgesehen.
- Livebild-Aufnahme im Browser, Stapelverarbeitung, Nutzerkonten, dauerhafte Speicherung über
  die TTL hinaus.
- DXF/SVG-Export der Kontur für die CNC — technisch naheliegend (`contour.py` liefert den Pfad
  in mm), aber nicht gefordert; bewusst zurückgestellt.
- Nicht-planare Objekte. Eine Homographie beschreibt genau eine Ebene; gewölbte Deckel bleiben
  außerhalb dessen, was dieses Verfahren leisten kann.
