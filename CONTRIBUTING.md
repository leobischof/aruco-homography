# Contributing

Thank you for looking. This is a small project with one unusually strict rule, so it is
worth two minutes before you write any code.

**Millimetres are the product.** A change that makes the image prettier and moves an edge
by half a millimetre is a regression, not an improvement. Everything below follows from
that.

> **A note on language.** This file and [`README.md`](README.md) are English, because they
> face outwards. The working documents under [`docs/`](docs/README.md) are German — that
> is where the project actually thinks. If you only read English, the tests and
> [`AGENTS.md`](AGENTS.md) will still tell you everything that is binding; the German is
> reasoning, not rules you could miss.

---

## Before you change anything

Read [`AGENTS.md`](AGENTS.md). It is written for AI agents but the **Invarianten**
(invariants) section is binding for everyone. In short, and not as a substitute for
reading it:

1. The rectified image occupies exactly `crop_w × crop_h` millimetres on the page. The
   branding strip below it grows the *page*, never the *image*.
2. **Nothing is scaled up to fit.** Marker edge length and both centre distances are used
   exactly as the operator measured them on the printed sheet.
3. The branding strip is on every page — see [`TRADEMARKS.md`](TRADEMARKS.md)
   for why that is a rule of this repository and *not* a licence condition.
4. A constant has exactly one home. Product values live in `shared/constants.json`,
   program values in `app/config.py`. No second definition, no fallback value.

Then skim [`docs/superpowers/specs/`](docs/superpowers/specs/). It describes what exists
today and is kept in step with the code. **If you change behaviour, you change the spec in
the same commit.** A spec that tells an untruth is worse than no spec.

## Getting set up

Windows with PowerShell and Python 3. One command does everything, including creating the
virtual environment on first run:

```powershell
.\dev.ps1 start-server
```

`dev.ps1` is the single source of truth for what a command does; `.vscode/tasks.json` only
calls into it. Never add a build step that lives somewhere else.

| Command | What it does |
|---|---|
| `.\dev.ps1 run-tests` | The test suite against the Python core — **this is the gate** |
| `.\dev.ps1 run-tests-cpp` | The same suite against the C++ core |
| `.\dev.ps1 run-tests-pdf-js` | The same suite against the JavaScript PDF builder |
| `.\dev.ps1 build-core` | The C++ core into `core/build/` |
| `.\dev.ps1 build-apk` | The Android APK into `android/out/` |
| `.\dev.ps1 kill-servers` | Stop servers started **from this repository** — nobody else's Python |
| `.\dev.ps1 help` | Everything else |

The C++, Android and WASM targets need toolchains that live **beside** the repository in
`../_toolchain/` (about 15 GB). You do not need any of them to work on the Python side or
the interface. `dev.ps1` tells you what is missing and where it looked.

## The bar for a change

**Run `.\dev.ps1 run-tests` and say what it printed.** Not "tests pass" — the number.
That is the whole culture of this repository in one sentence: the tests in `tests/` and
the frozen scenes in `shared/fixtures/` are the only proof this project has that it
measures correctly.

If you touch geometry — `app/vision/`, `core/src/`, `web/vision/` — you are touching the
part that the millimetres come out of. Expect to be asked for evidence, and expect the
question "against what did you measure it?".

A few specifics that catch people out:

- **Adding a constant?** It goes in `shared/constants.json` if it is a statement about the
  product, `app/config.py` if it is about this Python program. Never both, never a third
  place, never a `or 42` fallback.
- **Touching `core/`?** It must not use `imgcodecs` — that module does not exist in the
  WebAssembly build, and the same source has to compile for the browser.
- **Touching the interface?** `app/static/` is shipped **byte for byte** into the Android
  WebView. There is no bundler and no build step for it, on purpose. Plain ES modules.
- **Adding a dependency?** Check its licence against
  [`docs/licensing/third-party.md`](docs/licensing/third-party.md) first. This project is
  GPL-3.0-or-later, so most things fit — but anything AGPL that reaches `app/` changes the
  obligations of the shipped program, and that is not a casual decision.

## Commits

**The binding rules are in [`docs/contributing/git.md`](docs/contributing/git.md)** (German).
The parts you need before your first commit:

- **Never commit on `master` or `develop`.** Every change — a one-liner and a
  documentation typo included — goes on its own branch off `origin/develop` and comes in
  through a pull request. Both branches reject direct pushes, so this is enforced, not
  merely asked. Branch names: `feat/…`, `fix/…`, `docs/…`, `chore/…`.
- **One feature, one branch, one pull request.** PRs are squash-merged, so the PR — not
  the individual commit — is the unit of history on the trunk. Commit as finely as you
  like inside the branch; the PR title is what lands.
- **One feature, one commit.** If the description needs an "and", it is two commits.
- **English subject line** with a conventional prefix (`fix:`, `feat:`, `docs:`, `build:`),
  then a **blank line**, then a body that explains the **why**. The what is in the diff.
- Every commit stands on its own: `.\dev.ps1 run-tests` is green before it is made.

## Reporting a bug

For anything about measurement, a screenshot is not enough. The useful report has numbers
in it:

- The three measured values you entered — marker edge length, horizontal and vertical
  centre distance — and **what you measured them with**.
- The residual error and mm/px the report showed you.
- What you then measured on the printed result, and what it should have been.
- The photo, if you can share it. Unedited, uncropped, not sent through a messenger — that
  costs sharpness and EXIF.

"The template came out too small" is not actionable. "The template came out 4 mm short over
500 mm, residual 0.3 px" is a bug report, and a good one.

## Licence of your contribution

This project is **GNU GPL, version 3 or later** — see [`LICENSE`](LICENSE) and
[`docs/licensing/README.md`](docs/licensing/README.md).

**Inbound equals outbound.** By opening a pull request you offer your contribution under
that same licence. There is **no CLA and no copyright assignment** — you keep the copyright
to what you wrote. A `Signed-off-by:` line ([DCO](https://developercertificate.org/)) is
welcome and not required.

One thing the licence does **not** give you: the name "Bischof Snowboards" or its logo.
If you publish your own version, it needs its own name and its own mark. The reasoning,
and why the logo files are nevertheless under the GPL like everything else, is in
[`TRADEMARKS.md`](TRADEMARKS.md).

## What this project will probably say no to

Said plainly so nobody wastes an evening:

- **A bundler, a framework, or a build step for `app/static/`.** The absence of one is why
  the same files run in a browser, in a desktop window and inside the Android WebView
  without being copied.
- **A second way to do something that already has a first way.** Add behaviour by adding a
  unit behind a clear interface, not by editing five places.
- **A fallback value for a missing constant.** A missing constant must break loudly. A
  fallback turns a configuration error into a wrong measurement, and a wrong measurement
  gets sawn.
- **Lens distortion correction that is not measured.** It is a genuine and known limit
  (see *Limits* in the README) and a welcome contribution — but only with evidence against
  a known target, not a plausible-looking model.
