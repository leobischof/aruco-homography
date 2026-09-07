# ArUco Homography

Photograph an object next to a printed sheet of ArUco markers. Get back a PDF that you print
at 1:1, glue onto wood, and cut out.

The markers are the ruler. Their printed size is known — measured with a caliper, not assumed —
so from their corners in the photo the tool computes the homography that maps the photographed
plane back to a flat, square-on view at a known scale. What comes out is not a nice picture of
your object. It is your object, at its true size, on paper.

**Millimetres are the product.** A change that makes the image prettier and moves an edge by
half a millimetre is a regression, not an improvement. Everything on this page that looks like
fussiness — measure the printed sheet, print at 100 %, measure the printed scale bar — is there
because that is the only way the chain stays honest from the photo to the workpiece.

---

## Getting started

Windows with PowerShell and Python 3. One command:

```powershell
.\dev.ps1 start-server
```

The first run creates the virtual environment and installs the dependencies by itself — there
is no separate setup step. Then it starts the server, opens the browser at
`http://127.0.0.1:8000`, and prints the LAN address together with an ASCII QR code. Point your
phone's camera at that code and the phone runs the whole thing over the network. Stop the
server with Ctrl+C.

| Command | What it does |
|---|---|
| `.\dev.ps1 start-server` | Start the server and open the browser (`--no-browser` suppresses that) |
| `.\dev.ps1 install-deps` | Create the venv and install `requirements.txt` |
| `.\dev.ps1 run-tests` | Run the test suite (`pytest`; extra arguments are forwarded) |
| `.\dev.ps1 build-markersheet [mm] [spacing_x] [spacing_y]` | Write the marker sheet to `out/markerblatt_A4.pdf` |
| `.\dev.ps1 kill-servers` | Stop servers started **from this repository** — nobody else's Python |
| `.\dev.ps1 clean-all` | Remove the venv, `out/` and the caches |
| `.\dev.ps1 help` | List all commands |

The same commands are available as VS Code tasks (`Ctrl+Shift+P` → *Tasks: Run Task*). They
only call into `dev.ps1`; the script is the single source of truth for what a command does.

---

## The marker sheet

This is the section that decides whether the millimetres are right. Everything else is comfort.

Print the sheet — from the app's **Print marker sheet (A4)** button, or with
`.\dev.ps1 build-markersheet`. The default is the real, physically measured sheet:

| | |
|---|---|
| Dictionary | `DICT_4X4_50` |
| Markers | IDs 0–3 — 0 top left, 1 top right, 2 bottom left, 3 bottom right |
| Edge length | **67 mm**, black border included |
| Centre spacing | **121 mm** horizontal × **171 mm** vertical |
| Sheet | A4 portrait, the four markers centred on it |

The markers are drawn as **vector rectangles**, never as a raster image, so their edges stay
sharp at any printer resolution — and the corner detection works in subpixels, which is exactly
where the sharpness is spent.

### Then measure what actually came out of your printer

**Take a caliper to the printed sheet and type the measured numbers into the app.** All three of
them: the marker edge length, the horizontal centre spacing, and the vertical centre spacing.
The sheet carries its own 100 mm control scale so you can check the printer before you check
anything else.

This is not a formality. Printers scale, and they do not always scale both axes by the same
amount. Because you enter what you measured, any such scaling drops straight out of the
calculation. That is also why there are three fields and not one: **nothing is ever extrapolated
from a single number.** A factor derived from the edge length alone and applied to the spacings
would already be wrong the moment a printer stretches x differently from y.

Off-the-shelf sheet, different IDs, markers taped down wherever they fit? Use **free mode**. It
needs only the marker size and estimates the positions along with the homography. The one thing
it does require is that all markers are printed in the same orientation — the app checks that
and warns you if they are not.

---

## The workflow

Before any of it: **lay the printed sheet next to the object, in the same plane as the surface
you want to reproduce** — ideally directly on that surface — and take one photo that contains
the object and all four markers. Use the tele lens (1× or 2×), stand well back, keep everything
centred in the frame. That single photo is the whole input.

The interface then walks through six steps, in this order.

**1 · Photo.** Upload the picture — JPEG, PNG or HEIC (straight from an iPhone is fine), up to
60 MB. If the file carries an EXIF focal length, the app says so; it can then work out the
camera height on its own.

**2 · Scale.** Enter the measured marker size and the two measured centre spacings, pick sheet
or free mode, and enter the **object thickness** if the marker sheet is not lying on the surface
you care about. If there is no EXIF focal length and the thickness is greater than zero, the
camera distance becomes a required field.

**3 · Quality.** Press *Rectify* and read the report before trusting anything: the residual
error in px and mm, every marker measured back against its nominal size (which exposes lens
distortion and a skewed setup), the source resolution in mm per pixel, camera height and tilt,
and the thickness correction factor that was applied. Warnings appear in the page, in your
language.

**4 · Image adjustment.** Optional sliders that make the rectified image easier to cut along —
see below. They sit above the crop on purpose: they change exactly the image the next step cuts
up, and you want to see both at once.

**5 · Crop.** Drag a rectangle on the rectified preview. **Grab it by any of its four corners or
four edge midpoints to resize it, or drag inside it to move it**; dragging on empty canvas still
pulls a fresh rectangle, and the arrow keys nudge by 1 mm (10 mm with Shift). The edge lengths,
the pixel count at the chosen resolution and the extrapolated fraction update as you drag. The
shaded area is the marker hull — well outside it the rectification is extrapolating, and the app
says so.

**6 · Print.** Choose resolution (150–600 dpi, 300 by default), layout, paper size and overlap,
tick the extras you want printed, and create the PDF.

### What comes out

**The export defaults to tiling onto A4 sheets with an assembly plan as the first page**, because
a template at original size fits no printer anyone here owns. A single page at true object size
is still available for a plotter — it is the special case, not the normal one. Tiles overlap
(10 mm by default) and carry cut and glue marks; the assembly plan tells you which sheet goes
where.

Printed extras, all switchable: the 100 mm control scale, the metadata footer, a 50 mm grid, cut
and glue marks, and optionally the detected outline as a vector cutting line. The grid is drawn
twice — a wide white halo first, then the core line in brand ink — so it stays readable over a
light photo and a dark one alike, without covering the image.

Every sheet carries the Bischof Snowboards logo and *Made with Bischof Snowboards Software* in
an 18 mm strip below the image: the single page, *every* tile, the assembly plan and the marker
sheet. The strip makes the **page** 18 mm taller. It never makes the **image** anything other
than exactly the millimetres you cropped — that was always the only promise.

---

## Printing correctly

**Choose 100 % / no scaling in the print dialogue.** "Fit to page" and "shrink oversized pages"
are on by default in a lot of printer drivers, and either one quietly destroys everything the
rest of this tool is careful about.

**Then measure the printed 100 mm scale bar with the caliper.** Every PDF carries one. It is the
only proof that the chain from photo to paper actually held — and it takes five seconds.

---

## Image adjustment, and why it cannot move the millimetres

A faint pencil line on light wood is hard to cut along. The sliders make it visible: grayscale,
invert, brightness, contrast, saturation, local contrast (CLAHE), edge boost (unsharp mask), a
detected-edge overlay, colour emphasis on one hue, and a threshold that reduces the image to
hard black and white. The live preview is debounced, so dragging a slider is responsive, and the
print uses exactly the settings you previewed.

**The important part is where this runs: only on the already rectified image, never before
marker detection.** The homography is measured on the untouched photo. A sharpening filter ahead
of the detector would shift the marker corners, and with them the millimetres. Adjustment is
cosmetic by construction, not by discipline — it recolours pixels and never moves them.

That claim is measured rather than asserted. `tests/test_enhance.py` tracks the subpixel position
of an edge through each individual operation: grayscale, threshold and edge boost shift it by
0.000000 px and leave the silhouette bit-identical. Local contrast shifts the read-off point of a
soft edge by 0.11 px, because CLAHE tilts the flank tile by tile — at 300 dpi that is 0.009 mm,
three orders of magnitude below a millimetre. The number is written into the test as a measured
value, not hidden under a loose tolerance.

One consequence worth knowing: the outline used for the optional cutting line is found on the
*adjusted* image. That is deliberate. The sliders exist so a faint line becomes findable, and a
contour taken from the raw image would be a second, different truth printed on top of the picture
you are looking at.

---

## Getting the millimetres right

Three things decide the accuracy. Everything else is convenience.

**1 · One plane.** A homography is exact for exactly one plane. If the marker sheet lies on the
table while the surface you care about is 20 mm higher, then at 900 mm camera distance the result
comes out 2.2 % too large — on a 500 mm object that is 11 mm. So: put the sheet **on** the
object's surface whenever you can. When you cannot, enter the **object thickness**; the app
removes the height offset, taking camera height and nadir point from the decomposed homography
once it knows the EXIF focal length. If EXIF is missing — forwarded images often lose it — it
asks for the camera distance instead.

**2 · The lens.** With four coplanar markers, lens distortion cannot be separated out, so it is
left uncorrected. The remedy is on your side of the camera: **use the tele lens (1× or 2×), stand
well back, keep the object centred.** At the edge of a wide-angle frame, straight lines bend by
several millimetres.

**3 · Measuring the result.** See *Printing correctly* above. Print at 100 %, measure the 100 mm
bar.

The app is built to help you distrust it: it reports the residual error, measures each marker
back against its nominal size, states camera height and tilt, and warns when the crop reaches
well outside the marker hull — because out there, rectification turns into extrapolation.

---

## The interface

**Two languages.** German and English, switched with the DE/EN buttons in the header. The page
re-renders without a reload, and every user-visible string — interface, server warnings and
errors, and the text printed into the PDF — comes from one shared catalogue per language.
**The exported PDF is printed in the language chosen in the app**, and so is the marker sheet.

**Light and dark theme**, switched with the button next to the language. There are three states,
not two: explicitly light, explicitly dark, and — when you have never pressed the button — no
stored choice at all, which follows your system setting and keeps following it if the system
switches mid-session.

**The phone can drive the whole flow.** Open the LAN URL from the start-up banner (or scan the QR
code), and upload, rectify, adjust, crop and export all work on the phone that took the photo.
Single-column layout, touch targets of at least 44 px, no horizontal scrolling, and the crop
rectangle is draggable with a finger.

---

## Limits

Stated plainly, because a tool that measures things should not overstate itself.

- **Lens distortion is not corrected.** Four coplanar markers cannot separate it from the
  homography. The solver is built as a least-squares fit, so a radial parameter could be hung in
  later as another unknown.
- **Curved objects cannot work.** A homography describes exactly one plane. No amount of care
  with the photo changes that.
- **Dimensional accuracy has so far been proven only against synthetic scenes.** The test suite
  renders a virtual camera with a known pose and checks that the pipeline recovers the numbers
  that were put in. **The proof on a real printout — print it, measure the 100 mm scale with a
  caliper, write down what you got — is still outstanding.** Until that has happened, the central
  promise of this project stands unverified.
- **Sessions live one hour in memory.** Restarting the server throws away work in progress;
  nothing is stored on disk.

---

## Repository layout

```
app/vision/    detection, homography, camera pose, thickness correction,
               rectification, image adjustment, contour
app/pdf/       page geometry, printed extras, branding, PDF build, marker sheet
app/static/    the interface — css/ js/ i18n/ and brand/ with the logo and the font
app/           config (SSOT for every constant), pipeline (orchestration), main (routes)
tests/         synthetic scenes with known ground truth
docs/          documentation — start at docs/README.md
```

`app/config.py` is the only place constants are defined — even `dev.ps1` reads the port from
there rather than repeating it.

## Tests

No test depends on a real photo or on the eye. `tests/conftest.py` builds a virtual camera with a
chosen focal length, height and tilt, renders the plane with markers and a test object, and checks
that the pipeline recovers the numbers that went in:

- homography exact without noise (< 1e-6 mm); with 0.2 px of detection noise, < 0.5 mm over 500 mm
- thickness correction **in both directions**: without the correction the error must equal the
  height factor exactly, with it the error must be < 0.05 mm — a one-sided test would pass even on
  a scene with no height offset at all
- marker corners to subpixel accuracy (< 0.3 px), tile geometry, and the PDF MediaBox to 0.01 mm
- the generated marker sheet is rasterised and pushed through the real detector, so a transposed
  or mirrored module grid fails here instead of at the workpiece
- image adjustment measured for edge movement, and both language catalogues checked key by key

```powershell
.\dev.ps1 run-tests
```

## Where to go next

- **[docs/README.md](docs/README.md)** — the documentation index: every document with its
  purpose, audience and status. Start here.
- [docs/plans.md](docs/plans.md) — what is intended but not built: a Windows `.exe`, an Android
  app, a shared core, DXF export for CNC.
- [docs/design/design-system.md](docs/design/design-system.md) — colour, type, components,
  themes and languages.
- [docs/contributing/git.md](docs/contributing/git.md) — the binding Git rules for this repo.
- [AGENTS.md](AGENTS.md) — for anyone working here with an AI agent: the invariants that must
  not be broken.
- [CHANGELOG.md](CHANGELOG.md) — what changed, and when.

---

## Kurzfassung (Deutsch)

**Was das Werkzeug tut.** Ein Handyfoto von einem Gegenstand, daneben ein ausgedrucktes Blatt mit
ArUco-Markern — möglichst in derselben Ebene wie die Fläche, um die es geht — und heraus kommt ein
**maßhaltiges PDF in Originalgröße**. Ausdrucken, auf Holz kleben, aussägen. Die Marker sind das
Lineal: aus ihrer bekannten, **nachgemessenen** Größe folgt die Homographie und damit der Maßstab.
**Millimeter sind das Produkt** — alles andere ist Komfort.

**Starten.**

```powershell
.\dev.ps1 start-server
```

Beim ersten Mal richtet der Befehl venv und Abhängigkeiten selbst ein, startet dann den Server,
öffnet den Browser und gibt die Netzwerk-Adresse samt QR-Code aus. Damit lässt sich der ganze
Ablauf vom Handy aus bedienen. Die vollständige Befehlstabelle steht oben unter *Getting started*.

**Das Wichtigste in drei Sätzen.** Das Markerblatt (DICT_4X4_50, IDs 0–3, 67 mm Kantenlänge,
Mittelpunktabstände 121 × 171 mm auf A4 hoch) **nach dem Drucken mit dem Messschieber nachmessen**
und die gemessenen Werte in der App eintragen — damit fällt jede Druckerskalierung aus der
Rechnung. Beim Ausdrucken der Schablone **100 % / keine Skalierung** wählen und anschließend den
aufgedruckten 100-mm-Maßstab nachmessen. Die Vorgabe des Exports ist die **Kachelung auf A4 mit
Klebeplan**, weil eine Schablone in Originalgröße auf keinen Drucker passt.

**Was die Oberfläche kann.** Sechs Schritte — Foto, Maßstab, Qualität, Bildaufbereitung,
Zuschnitt, Druck. Sie spricht **Deutsch und Englisch** (umschaltbar; der Ausdruck folgt der
gewählten Sprache), hat ein **helles und ein dunkles Thema** (ohne gespeicherte Wahl gilt die
Systemvorgabe), und das Zuschnitt-Rechteck lässt sich an Ecken und Kanten anfassen und
verschieben. Die **Bildaufbereitung** greift ausschließlich am bereits entzerrten Bild an, nie vor
der Markererkennung — sie kann die Millimeter deshalb nicht verschieben.

**Grenzen, offen gesagt.** Die Objektivverzeichnung bleibt unkorrigiert. Gewölbte Objekte gehen
prinzipiell nicht — eine Homographie beschreibt genau eine Ebene. Und: **die Maßhaltigkeit ist
bislang nur gegen synthetische Szenen belegt; der Beweis am echten Ausdruck, mit dem Messschieber
nachgemessen, steht noch aus.**

**Weiterlesen.** [docs/README.md](docs/README.md) ist das Inhaltsverzeichnis der Dokumentation —
dort steht jedes Dokument mit Zweck, Zielgruppe und Stand. Die Invarianten für Agenten stehen in
[AGENTS.md](AGENTS.md), die Vorhaben in [docs/plans.md](docs/plans.md).
