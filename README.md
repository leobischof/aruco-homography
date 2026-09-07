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
is no separate setup step. Then it starts the server, opens the application **in its own
window**, and prints the LAN address together with an ASCII QR code. Point your phone's camera
at that code and the phone runs the whole thing over the network — the server keeps serving the
LAN while the window is open, because the phone is where the photo comes from. Close the window
to stop, or press Ctrl+C in the console.

| Command | What it does |
|---|---|
| `.\dev.ps1 start-server` | Start the server and open the app window (`--browser` uses the system browser instead, `--no-browser` opens neither, `--port N` asks for a different port) |
| `.\dev.ps1 install-deps` | Create the venv and install `requirements.txt` |
| `.\dev.ps1 run-tests` | Run the test suite (`pytest`; extra arguments are forwarded) |
| `.\dev.ps1 build-markersheet [mm] [spacing_x] [spacing_y]` | Write the marker sheet to `out/markerblatt_A4.pdf` |
| `.\dev.ps1 build-exe` | Build the standalone Windows program into `dist/ArUco-Homographie/` |
| `.\dev.ps1 build-installer` | Build the Windows installer — **one file** — into `dist/` |
| `.\dev.ps1 kill-servers` | Stop servers started **from this repository** — nobody else's Python |
| `.\dev.ps1 clean-all` | Remove the venv, `out/`, `build/`, `dist/` and the caches |
| `.\dev.ps1 help` | List all commands |

The same commands are available as VS Code tasks (`Ctrl+Shift+P` → *Tasks: Run Task*). They
only call into `dev.ps1`; the script is the single source of truth for what a command does.

The server takes port 8000 when it is free and a different one when it is not — the address
that actually applies is printed in the start banner.

### Its own window — and the ways out of it

The interface comes up in a **native desktop window** that hosts the local server, not in a
browser tab. A tab is closed with all the others and the program looks gone while its server is
still running; a window is a program. The window is a second *view* of that server, not a second
application: the LAN address stays reachable while it is open, which is the whole point, because
the phone is where the photo comes from.

| Flag | What it does |
|---|---|
| *(none)* | Open the app in its own window. This is what a double-click does. |
| `--browser` | Open the system browser instead — the way out on a machine where the window is no good. |
| `--no-browser` | Open neither. The server runs on its own; for scripts, and for working only from the phone. |
| `--port N` | Ask for a different port. A wish, not a promise: a port already taken is stepped around. |

The window needs the **Microsoft Edge WebView2 runtime**. Windows 11 has it; a Windows 10
machine may not (`winget install --id Microsoft.EdgeWebView2Runtime` adds it). If it is missing —
or if `pywebview` is not installed at all — the program says so in one line and opens the browser
instead. It never refuses to start over a missing window: server, LAN address and QR code come up
either way, so a workshop PC that cannot show the window is still fully usable from the phone.

## Running it without Python

Neither route below needs Python on the machine that runs the program. The first hands over
**one file**; the second hands over a folder, for people who cannot or will not install
anything.

### The installer — one file, nothing to unpack

```powershell
.\dev.ps1 build-installer
```

builds `dist\ArUco-Homographie-Setup-<version>.exe` — one file, 78 MB, because `lzma2/max` with
solid compression squeezes the 290 MB bundle harder than the zip did. Double-click it, click
through, done: the program lands on the machine with a Start Menu entry, an optional desktop icon
(offered unchecked, as Windows does it), and an uninstaller in *Apps & Features*. Nothing to
unpack, nothing to move to the right place. About 292 MB on disk once installed.

It installs **for the current user only**, into `%LOCALAPPDATA%\Programs\ArUco-Homographie`, and
therefore needs **no administrator rights** — the person at a workshop PC often does not have
them. That same choice removes the path-length trap the folder route has below: the installer
picks a short target, so Windows' 260-character limit is nowhere near.

Building it needs [Inno Setup 6](https://jrsoftware.org/isinfo.php), which
`winget install --id JRSoftware.InnoSetup` installs. `dev.ps1` looks for `ISCC.exe` on the
`PATH`, in the per-user location and in both `Program Files` locations, and names that winget
command if it finds none. The build recipe is `installer\aruco-homographie.iss` — checked in,
because it is source, not output. Version, publisher and URL are not typed into it: `dev.ps1`
reads them out of `app/config.py` and passes them in, so there is one place to change them.

### The folder — the alternative, without an installation

```powershell
.\dev.ps1 build-exe
```

builds `dist\ArUco-Homographie\ArUco-Homographie.exe` with PyInstaller. Double-clicking it starts
the server and opens the app in its own window; a console window comes up beside it with the LAN
address and the QR code, and it belongs there — that is how the phone finds the server. This is
what the release `.zip` contains, and what to use when installing is not an option — on a machine
where nothing may be installed, or from a USB stick.

Pass on the **whole folder**, not just the `.exe` inside it — `_internal\` sits beside it and
holds OpenCV, the fonts and the interface. Around 290 MB.

**Then the folder must not sit too deep.** The longest file in the bundle has a relative path of
101 characters, so a target folder beyond roughly 157 characters runs into Windows'
260-character limit and the program aborts at startup with *DLL load failed … The filename or
extension is too long*. `C:\Program Files\` or the desktop are fine; a deeply nested OneDrive
folder is not. It is not a bug, but it looks exactly like one — and it is the single best reason
to prefer the installer.

### Either way: the file properties say who made it

Right-click either `.exe` → *Properties* → *Details* and the publisher is there: company
`Bischof Snowboards`, the product name, the version, and a copyright line. PyInstaller writes no
version resource unless you give it one, so the application's comes from a `VSVersionInfo` block
in `aruco-homographie.spec` and the setup's from the `VersionInfo*` directives in the `.iss` —
both fed from `app/config.py`, neither retyped.

**That is not a signature.** Neither binary is code-signed, so SmartScreen still warns on the
first launch (*More info* → *Run anyway*) and still shows **Unknown publisher** — filled-in file
properties are metadata anyone can write, and Windows knows it. Acceptable for personal use;
handing it to other people without that warning needs a code-signing certificate, and nothing
short of one will do.

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

## Worked example: a panel that fits an irregular opening

There is a hole in the workshop wall where a cellar window used to sit. Roughly 470 × 600 mm,
not one straight edge on it, one corner rounded off where the render broke away. It needs a
12 mm plywood panel that drops in flush.

The usual method is cardboard, a pencil and three trips back to the saw. This is the other one:
photograph the opening beside the marker sheet, print that photograph back out at true size,
glue it to the plywood, saw along the edge of the opening as it appears in the picture, peel the
paper off. What follows is that job from start to finish — including the handful of places where
a good template still turns into a bad panel.

### Before the photo

**1 · Print the marker sheet, then measure what came out.**

Press **Print marker sheet (A4)** in the header (or run `.\dev.ps1 build-markersheet`) and print
it at 100 %, no scaling. Then take a caliper to the paper and read three numbers off it: the
edge length of one marker including its black border (nominally 67 mm), the horizontal centre
spacing (nominally 121 mm), and the vertical centre spacing (nominally 171 mm). Those three
measured numbers are the ruler for everything that follows. The nominal ones are not.

Centre-to-centre is easier to measure than it sounds: measure the same feature on both markers.
Left edge of the left marker to left edge of the right marker *is* the centre spacing, and a
caliper finds a printed edge far more reliably than an imagined centre.

Print on matte paper if you have it — gloss throws a highlight that can swallow a marker corner
— and keep the sheet flat. A curled sheet is not a plane, and one plane is the whole basis of
the method. The detail is in [The marker sheet](#the-marker-sheet).

**2 · Put the sheet in the plane of the opening.**

This is the step that decides whether the panel fits, and it is the one that goes wrong first. A
homography is exact for exactly one plane. The tool measures the plane the markers lie in, and
then treats the whole photograph as though it lay in that plane. So the markers have to lie in
the plane you are going to cut to.

Work out which plane that is before you reach for the tape: the seat in the rebate if the panel
drops in behind the frame, the face of the wall if it covers over. Then get the sheet there —
taped to a straight batten laid across the opening flush with that face, or taped flat to the
wall right beside the opening if that is the plane you want. Tape all four corners; a sheet that
bows in the middle has stopped being one plane too.

What it must not do is lie on the sill, 60 mm in front of the opening. That looks close enough,
and it is not. Photographed from 1.5 m, a 60 mm offset makes everything in the opening come out
3.9 % too small — 19 mm across a 500 mm span, in both directions. From 900 mm it is 6.3 %, over
30 mm. Nothing warns you, either, because from the tool's side nothing is wrong: it measured a
plane exactly. Just not yours.

If the sheet has to sit on top of something whose thickness you know — laid on a 19 mm board
beside the opening, say — enter that number as **Object thickness (mm)** in step 2 of the
interface and the tool takes the offset back out. It needs the camera height to do that, which
it reads from the EXIF focal length, or asks you for as a camera distance when the photo carries
no EXIF. The correction is forgiving about the distance and unforgiving about the thickness:
10 % out on the distance leaves about 0.2 % of error, while a thickness that is wrong leaves all
of the error it was meant to remove.

One thing no setting fixes: the opening has to be flat. If its edge runs around a curved wall,
or the panel has to follow a bulge, one homography cannot describe it — and no care with the
photograph will change that.

**3 · Take the photograph.** One frame, containing the whole opening and all four markers.

- **Use the tele lens (1× or 2×) and stand well back.** Lens distortion is not corrected, and it
  cannot be: four coplanar markers cannot separate it from the homography. At the edge of a
  wide-angle frame a straight line bends by several millimetres, and this tool will faithfully
  print that bend at 1:1.
- **Keep the opening in the middle of the frame.** Distortion is smallest at the centre, and the
  middle is also where you have the most pixels to spend.
- **Get it sharp.** Marker corners are found to a fraction of a pixel, and that is where the
  accuracy comes from. Tap to focus on the sheet, brace yourself, take a second frame.
- **Light it evenly.** A hard shadow edge across the opening becomes a convincing false edge on
  the template.
- **Square-on beats steep.** The homography handles perspective, but a steep angle spends
  resolution and pushes the far side of the opening out towards the part of the lens that bends
  most.
- **Do not crop it and do not send it through a messenger.** Re-compression softens the marker
  edges, and forwarding strips the EXIF focal length. Move the file across, or open the app on
  the phone that took the picture — `.\dev.ps1 start-server` prints a LAN address and a QR code
  for exactly that.

### At the screen

**4 · Photo.** Upload the file: JPEG, PNG or HEIC straight off the phone, up to 60 MB. The step
reports the pixel size and whether an EXIF focal length came with it.

**5 · Scale.** Type in the three numbers from step 1 — **Marker size (mm)**, **Centre spacing,
horizontal (mm)**, **Centre spacing, vertical (mm)** — exactly as measured. All three, because a
printer that stretches x by 0.4 % need not stretch y by the same amount, and nothing here is
derived from anything else. Leave **Mode** on *Marker sheet*, leave **Object thickness** at 0 if
the sheet lay in the plane of the opening, and press **Rectify**.

**6 · Quality.** Read the report before you trust the picture.

- **Residual error** — how well the four markers fit one single homography. A good photograph
  lands well under the warning thresholds of 2 px and 1 mm. Above them the app names the usual
  causes: lens distortion, an unsharp photo, or a sheet that is not flat.
- **Measured edges** — every marker measured back and held against the 67 mm you typed. If three
  read 67.0 and one reads 65.2, that one marker is the problem: a lifted corner, a curl in the
  paper, or a marker sitting far out at the edge of the frame. The app warns past 2 % deviation.
- **Source resolution**, in millimetres per pixel — how fine the photograph really is in the
  plane. At 0.30 mm/px, printing at 600 dpi (0.042 mm/px) adds no information whatsoever. 300 dpi
  is plenty for a line you are going to saw along.
- **Camera** and **Thickness correction** — height, tilt, and the factor k that was applied. With
  a thickness of 0 it says *none* and k is 1.

**7 · Image adjustment.** The line you are going to cut is the edge of the opening: usually the
shadow boundary between wall and dark hole, sometimes a pencil line you drew yourself. Either
way it has to become unmistakable. A starting combination that works on most photographs:

- **Grayscale** on. Colour has nothing to offer a cutting line, and everything else behaves more
  predictably without it.
- **Local contrast** about a third up. CLAHE pulls detail out of evenly lit areas — the shaded
  inside of an opening — where a global curve only crushes it.
- **Edge boost** about a quarter. An unsharp mask: the edge gets steeper, it does not move.
- **Contrast** a little, and **brightness** last, once the two above have done their work.
- **Edge overlay** if the transition is still soft — it draws the detected edges on top of the
  image as lines. It is also the control that most eagerly finds edges you did not want, so raise
  it slowly.
- **Threshold** only when the edge is genuinely unambiguous. It reduces everything to black and
  white, which is the hardest line you can follow, and throws away every trace of the edges it
  decided were not edges.
- **Colour emphasis** if you marked the outline in a colour: pick the hue, raise the strength,
  and the pencil comes forward while the wood falls back.

None of this can move a millimetre — it all runs on the already rectified image, never before
marker detection, and the movement is measured rather than asserted; see
[Image adjustment, and why it cannot move the millimetres](#image-adjustment-and-why-it-cannot-move-the-millimetres).
If you want the outline printed as a vector cutting line (*Outline as a cutting line*, in step
6), it is found on the adjusted image — on exactly what you are looking at here. Making the edge
visible in this step is what makes that option work at all.

**8 · Crop.** The rectangle you drag is what gets printed, in millimetres. Its coordinates count
from the top left corner of the marker sheet, so negative values are perfectly normal — they
just mean "left of the sheet" or "above it".

Grab the rectangle by a corner or an edge midpoint to resize it, drag inside it to move it, or
type x0/y0/x1/y1 into the four fields; the arrow keys nudge by 1 mm, 10 mm with Shift. Give the
opening about 40 mm of air all round — paper to hold on to while gluing, and margin for the fact
that the outline is not the last word until the panel has been offered up. For our 470 × 600 mm
hole that is **550 × 680 mm**.

Then read the extrapolation figure, and do not panic at it. The shaded area is the marker hull —
188 × 238 mm, the rectangle the four markers actually span. A 550 × 680 mm crop lies about 88 %
outside it, and the app says so, because that is the truth: out there the homography is being
extended beyond anything that was measured, and the uncorrected lens distortion has nothing
holding it in check. That is a risk, not a verdict. Three things reduce it:

1. **Put the sheet in the middle of the opening**, not off to one side. The extrapolation is then
   short and even in every direction instead of long in one.
2. **Stand further back with the tele**, so the opening sits well inside the frame.
3. **Switch to free mode with more markers** if the opening is much larger than about two sheets.
   Print a second marker sheet and cut its four markers apart — they are all printed the same way
   up, which is exactly what free mode requires — and tape them around the opening. Free mode
   estimates their positions along with the homography, so the hull covers what you are cutting.
   The price is that the scale then rests on the 67 mm marker edge alone instead of on the 121 mm
   and 171 mm spacings as well, so measure that edge with real care.

Whatever you choose, check it against the world: run a tape measure across the widest part of the
real opening, and measure the same run on the printed template. Those two numbers agreeing is
worth more than every figure on this page.

**9 · Print.** 300 dpi, **Tiling onto standard paper** (the default), A4, 10 mm overlap. Leave
the 100 mm control scale, the 50 mm grid, the cut and glue marks and the assembly plan switched
on — every one of them earns its ink in the next three steps. Press **Create PDF** and
`schablone.pdf` downloads. For 550 × 680 mm that is eight A4 sheets plus the assembly plan, nine
pages in all; the app turns the paper landscape by itself, because for this shape that needs
fewer sheets than portrait.

### On paper

**10 · Print at 100 %, and measure the bar before you cut anything.**

Choose **100 % / no scaling** in the print dialogue, and check the PDF viewer as well — most of
them have a scale setting of their own, and "Fit" is a common default.

Then put the caliper on the printed 100 mm control scale. If it reads 100.0, carry on. If it
reads 99.2, stop. The print is 0.8 % short, a 600 mm panel would come out 5 mm small, and nothing
at the saw gets that back. In order:

1. **Do not fix it in the app.** The marker numbers describe the sheet you measured. Bending them
   to compensate for a print scaling puts a second, invisible factor into the chain — the one
   thing this tool is built to avoid.
2. **Find the setting.** Scale or zoom at anything but 100 %; "fit to printable area"; "shrink
   oversized pages"; poster or tile modes in the driver; and the classic, an A4 page sent to a
   printer loaded with Letter, which most drivers quietly shrink to about 94 %.
3. **Check both directions.** The control scale is horizontal, so it only proves x. The 50 mm
   grid proves both: four squares across and four down should each measure 200 mm. Printers do
   not always scale the two axes alike.
4. **Print one sheet, measure, repeat** — then print the rest.

If nothing gets that printer to 100 %, it cannot print a template. Use another one, or a copy
shop, and tell them 1:1 with no fitting.

**11 · Assemble the sheets.**

Page one is the assembly plan: the whole template drawn small, the sheets numbered in their grid,
with the overall size, the sheet count and the overlap written above it. Each sheet also repeats
its own place in the strip below the image — *Sheet 5/8 - Column 1, row 3*.

Lay them all out on the floor in that order before any tape comes out. Every sheet carries corner
ticks marking the cut line of its usable area, and where it has a neighbour to the right or
below, a dashed line 10 mm in from that edge. That dashed line is where the neighbour's picture
starts again: lay the neighbour's leading edge exactly on it, so the doubled 10 mm strip lies
underneath. Always put the higher-numbered sheet on top, and every joint is made the same way.

**Align by numbers, not by eye.** The 50 mm grid is labelled with its absolute position in the
template, and the same line carries the same number on both sheets — line up "300" with "300" and
the joint is right, however featureless the photograph happens to be at that spot. Tape from the
back, so the front stays flat and nothing lies across the line you are about to cut.

When the sheet is whole, measure it once end to end using those same grid numbers: 0 to 500
should be 500 mm. That one measurement catches a bad joint, a missing sheet, and a print that was
scaling after all.

**12 · Glue the template to the board — dry.**

Trim the assembled template roughly to shape first, a hand's width outside the line, so you are
handling something manageable. Then use a **repositionable** adhesive: a light coat of spray
mount on the back of the paper — not on the wood — left half a minute to go tacky before it goes
down. That is enough to hold paper flat under a saw and little enough to peel off afterwards
without lifting veneer with it. Low-tack masking tape laid over the board with the paper sprayed
onto the tape does the same job and comes off even more kindly.

What not to use: anything wet. PVA, glue stick and wallpaper paste all put water into the paper,
and wet paper grows — easily a percent across a long sheet. That is millimetres, at the very last
step, after everything else was done carefully.

Lay it down from one edge and sweep it flat as you go, so no bubble is trapped. A bubble is a
local stretch, and it will sit exactly where you are about to saw.

### At the saw

**13 · Cut on the correct side of the line.**

This is where a good template still produces a bad panel. A saw does not cut *at* the line, it
removes a slot of material — the kerf. Roughly 1.2 to 1.5 mm for a jigsaw, 0.6 to 1 mm for a
bandsaw, 2.5 to 3 mm for a circular saw. Where you put that slot decides the size of the panel:

| Blade runs | Panel comes out |
|---|---|
| Centred on the line | half a kerf smaller all round |
| Entirely outside the line (waste side) | at the drawn size |
| Entirely inside the line | a full kerf smaller all round |

**Mark the waste side before you start.** For a panel that fills an opening, the panel is inside
the line and the waste is outside — hatch the outside with a pencil, all the way round. On a
freeform curve, with the template covering the board and sawdust covering the template, it is
genuinely easy to lose track halfway round, and half a lap on the wrong side is not recoverable.

**The recommendation: run the blade centred on the line, and know your kerf.** A panel cut
exactly to the drawn size is a zero-clearance panel and will not drop into anything — real
openings are not straight and wood moves with the season. Centring the blade gives up half a kerf
per side, which is 0.6 to 0.75 mm with a jigsaw and about 0.4 mm with a bandsaw: near enough the
clearance a drop-in panel wants anyway, given away deliberately instead of by accident.

Two cases where that is the wrong choice. With a wide kerf — a circular saw at 3 mm — half a kerf
per side is 1.5 mm of gap on every edge, too much: run just on the waste side of the line and
take the rest off with a plane. And when the fit has to be tight and gap-free, cut on the waste
side as well, so the panel leaves the saw deliberately a shade oversize, then bring it down to
the line with a block plane or a sanding block, offering it up as you go. Fitting by hand is slow
and cannot overshoot; the saw is fast and cannot be undone.

The error to prefer is the small panel. A millimetre under drops in and takes a bead of filler or
a strip of trim. A millimetre over does not go in at all, and by then the outer half of your line
is sawdust.

Keep the blade square to the face. A blade leaning two degrees through 12 mm ply takes 0.4 mm off
the back edge that you never see until the panel binds — and jigsaw blades lean under load in a
tight curve more than anyone expects. Go slowly through the curves and let the blade do it.

**14 · Peel it off and offer it up.**

Peel while the adhesive is fresh; spray mount only gets harder to remove. Pull the paper back on
itself at a shallow angle rather than straight up, and warm it gently if it resists. Residue
comes off with a rag and a little white spirit.

Then offer the panel up. Cut centred on the line, it should drop in with a hair of clearance all
round. If it binds, rub a pencil along the opening edge to find the spot, take that spot down
with a sanding block, and try again — a two-minute job, not a re-cut.

**And on the first panel you make this way, check the tool.** Measure one long dimension of the
finished panel and compare it with the same dimension on the template and with the opening
itself. The dimensional accuracy of this chain has so far been proven only against synthetic
scenes: a virtual camera with a known pose, checked against the numbers that went into it. That
is a good foundation and it is not a measurement on paper — nothing in this repository has ever
seen a printer. See [Limits](#limits).

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
app/           config (SSOT for every constant), pipeline (orchestration), main (routes),
               window (how the interface shows up: own window, browser, or neither)
installer/     aruco-homographie.iss — the Inno Setup recipe for the Windows installer
tests/         synthetic scenes with known ground truth
docs/          documentation — start at docs/README.md
```

`app/config.py` is the only place constants are defined — `dev.ps1` reads the preferred port,
the version (`APP_VERSION`) and the brand strings from there rather than repeating them, and
hands the last three to the installer recipe, which therefore contains no version of its own.
Paths to bundled files go through `config.resource_path()`, so they mean the same thing in the
source tree and inside the built bundle.

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
zeigt die Oberfläche **in einem eigenen Fenster** und gibt die Netzwerk-Adresse samt QR-Code aus.
Der Server bleibt dabei, was er war: die Adresse fürs Handy antwortet weiter, während das Fenster
offen steht, und damit lässt sich der ganze Ablauf vom Handy aus bedienen. `--browser` nimmt
statt des Fensters den Browser, `--no-browser` öffnet gar nichts. Das Fenster braucht die
**WebView2-Laufzeit**; fehlt sie, sagt das Programm das in einer Zeile und öffnet den Browser,
statt abzubrechen. Die vollständige Befehlstabelle steht oben unter *Getting started*.

**Auf einen Rechner ohne Python bringen.** `.\dev.ps1 build-installer` baut
`dist\ArUco-Homographie-Setup-<Fassung>.exe` — **eine** Datei. Doppelklicken, durchklicken,
fertig: Startmenü-Eintrag, wahlweise ein Schreibtischsymbol, Deinstallation über *Apps &
Features*. Nichts entpacken, nichts an die richtige Stelle schieben. Installiert wird **ohne
Administratorrechte** für den angemeldeten Benutzer nach `%LOCALAPPDATA%\Programs\`, und weil
der Installer den Zielpfad wählt, ist die 260-Zeichen-Grenze von Windows kein Thema mehr — der
Fehler, der beim Entpacken in einen tiefen OneDrive-Ordner zuschlug. Zum Bauen wird Inno Setup 6
gebraucht (`winget install --id JRSoftware.InnoSetup`). Wer nichts installieren kann oder will,
nimmt weiter `.\dev.ps1 build-exe` und gibt den **ganzen Ordner** weiter; Einzelheiten oben unter
*Running it without Python*.

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

**Ein Beispiel von Anfang bis Ende.** In der Werkstattwand klafft ein Loch, wo einmal ein
Kellerfenster saß: rund 470 × 600 mm, keine gerade Kante daran. Hinein soll eine
12-mm-Sperrholzplatte, die bündig sitzt. Ausführlich steht der Durchgang oben unter
[Worked example](#worked-example-a-panel-that-fits-an-irregular-opening) — hier in Kurzform:

1. **Markerblatt drucken** (100 %, keine Skalierung) und **nachmessen**: Kantenlänge sowie
   waagerechter und senkrechter Mittelpunktabstand. Kniff: von linker Kante zu linker Kante
   messen — das ist derselbe Mittelpunktabstand, und eine gedruckte Kante trifft der
   Messschieber viel sicherer als einen gedachten Mittelpunkt.
2. **Das Blatt in die Ebene der Öffnung** legen, nicht auf die Fensterbank davor. Eine
   Homographie ist für genau eine Ebene exakt: 60 mm Versatz, aus 1,5 m fotografiert, machen die
   Öffnung 3,9 % zu klein — 19 mm auf 500 mm, und nichts warnt davor. Liegt das Blatt auf einer
   Fläche bekannter Dicke, trägt man diese als **Objektdicke** ein. Gewölbte Öffnungen gehen
   prinzipiell nicht.
3. **Ein Foto:** Tele (1× oder 2×), großer Abstand, Öffnung mittig und scharf, gleichmäßiges
   Licht, alle vier Marker im Bild. Weitwinkel biegt die Ränder, und diese Verzeichnung wird
   nicht korrigiert. Das Bild weder beschneiden noch durch einen Messenger schicken — das kostet
   Schärfe und EXIF.
4. **Foto → Maßstab → Qualität:** die drei gemessenen Zahlen eintragen, *Entzerren*, dann den
   Bericht lesen. Restfehler unter 2 px / 1 mm, und jede zurückgerechnete Markerkante nahe an den
   eingetragenen 67 mm.
5. **Bildaufbereitung:** Graustufen an, lokaler Kontrast etwa ein Drittel, Kantenanhebung etwa
   ein Viertel, Helligkeit und Kontrast zuletzt. Kein Regler verschiebt Millimeter.
6. **Zuschnitt:** rund 40 mm Luft um die Öffnung, hier also 550 × 680 mm. Der
   Extrapolationsanteil ist dabei hoch — die Marker-Hülle misst nur 188 × 238 mm. Das Blatt
   deshalb **mittig in die Öffnung** legen — und zur Gegenprobe eine lange Strecke der echten
   Öffnung mit dem Bandmaß messen und mit derselben Strecke auf der Schablone vergleichen.
7. **Druck:** 300 dpi, Kachelung auf A4, 10 mm Überlappung, Klebeplan an. Aus 550 × 680 mm werden
   acht A4-Blätter quer plus Klebeplan.
8. **Mit 100 % drucken, dann den aufgedruckten 100-mm-Maßstab nachmessen.** Steht dort 99,2 mm,
   liegt es am Druck und nicht am Werkzeug: Skalierung, „an Seitengröße anpassen", oder
   A4-Inhalt auf Letter-Papier. Beide Achsen prüfen — der Maßstab belegt nur die waagerechte, das
   50-mm-Raster beide.
9. **Blätter zusammensetzen** nach dem Klebeplan. Die gestrichelte Linie markiert den
   Überlappungsstreifen; ausgerichtet wird über die **beschrifteten Rasterlinien** („300" auf
   „300"), nicht nach Augenmaß. Von hinten kleben.
10. **Schablone trocken aufkleben.** Sprühkleber, repositionierbar, dünn auf das Papier und kurz
    ablüften lassen. Nassleim, Klebestift und Kleister quellen das Papier auf — aufgequollenes
    Papier ist genau der Fehler, den dieses Werkzeug vermeiden soll.
11. **Auf der richtigen Seite der Linie sägen.** Die Abfallseite vorher schraffieren; sie liegt
    außerhalb der Linie. Das Sägeblatt nimmt Material weg (Stichsäge 1,2–1,5 mm), deshalb **mittig
    auf der Linie sägen**: dann fehlt je Seite eine halbe Schnittfuge, und genau dieses Spiel
    braucht eine Platte, die hineinfallen soll. Bei breiter Fuge (Handkreissäge, 3 mm) knapp auf
    der Abfallseite bleiben und den Rest mit dem Hobel wegnehmen. Zu klein ist zu retten, zu groß
    heißt zurück an die Säge.
12. **Papier abziehen und einpassen.** Flach abziehen, solange der Kleber frisch ist. Klemmt es,
    die Stelle anzeichnen und mit dem Schleifklotz wegnehmen. **Beim ersten Stück mit dem
    Messschieber gegenprüfen** — die Maßhaltigkeit ist bislang nur gegen synthetische Szenen
    belegt.

**Grenzen, offen gesagt.** Die Objektivverzeichnung bleibt unkorrigiert. Gewölbte Objekte gehen
prinzipiell nicht — eine Homographie beschreibt genau eine Ebene. Und: **die Maßhaltigkeit ist
bislang nur gegen synthetische Szenen belegt; der Beweis am echten Ausdruck, mit dem Messschieber
nachgemessen, steht noch aus.**

**Weiterlesen.** [docs/README.md](docs/README.md) ist das Inhaltsverzeichnis der Dokumentation —
dort steht jedes Dokument mit Zweck, Zielgruppe und Stand. Die Invarianten für Agenten stehen in
[AGENTS.md](AGENTS.md), die Vorhaben in [docs/plans.md](docs/plans.md).
