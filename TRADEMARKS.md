# Trademarks

**Additional terms under Section 7(e) of the GNU General Public License, version 3.**

This file is the notice referred to in [`LICENSE`](LICENSE). It does not modify the GPL
and does not restrict any right the GPL grants. Section 7(e) of the GPL expressly permits
a licensor to decline to grant rights under trademark law; that is all this file does.

---

## 1 · The marks

The following are trademarks of Leo Bischof / Bischof Snowboards:

| Mark | Where it appears |
|---|---|
| **Bischof Snowboards** — the name, in any form | the branding strip on every generated sheet, the app's signing certificate (`CN=Bischof Snowboards`), the application ID `com.bischofsnowboards.aruco` |
| **The Bischof Snowboards logo** | `app/static/brand/logo-black.svg`, `logo-dark.svg`, `logo-light.svg`, and every PDF this program produces |
| **"Made with Bischof Snowboards Software"** | the branding strip on every generated sheet |

These marks are asserted as common-law / unregistered trademarks unless a registration is
recorded here. **If a registration exists or is later granted, its number and jurisdiction
belong in this table** — an unregistered mark is still protected against confusing use,
but a registered one is protected further, and the difference should be stated rather than
implied.

## 2 · What is not granted

**No trademark licence is granted by the GPL, and none is granted here.**

Permission to copy, modify and redistribute the *software* — including the logo files,
which are licensed under the GPL exactly like every other file in this repository — does
**not** include permission to use the marks in Section 1 **as marks**: that is, to
identify, name, brand or advertise a product, service or distribution.

Concretely, without separate written permission you may **not**:

- publish a modified version of this program under the name "Bischof Snowboards", or
  under a name confusingly similar to it;
- use the Bischof Snowboards logo as the icon, branding or store listing of your version;
- publish under the application ID `com.bischofsnowboards.aruco`;
- state or imply that your version is produced, endorsed or supported by Bischof
  Snowboards.

## 3 · What is expressly permitted

To be clear, because trademark notices are often read as broader than they are:

- **Redistributing this program unmodified, marks intact** — that is the normal case and
  needs no permission.
- **Nominative use**: referring to this project by name, truthfully. "Based on ArUco
  Homography by Leo Bischof", "a fork of ArUco Homography", "compatible with…" — all fine
  and no permission required. Naming a thing is not branding your own thing with it.
- **Keeping the branding strip** in a modified version, if you want to. Nothing obliges
  you to remove it; Section 2 only forbids using the marks to pass your version off as
  this one.

## 4 · Why the logo files are under the GPL anyway

The obvious alternative would be to carve the brand assets out of the licence — *all
rights reserved, redistribution only unmodified*. That was considered and **deliberately
not done**.

**F-Droid does not accept non-free components.** A repository in which individual files
are not free software earns the `NonFreeAssets` anti-feature at best and rejection at
worst. An exception for three SVG files would have cost the entire distribution route, to
buy protection that trademark law already provides.

So: everything is free under the GPL, and the question of *origin* stays where it belongs
— in trademark law, which exists for exactly that question and nothing else.

## 5 · The branding strip is a rule of this repository, not of this licence

[`AGENTS.md`](AGENTS.md), invariant 3, requires the logo and "Made with Bischof Snowboards
Software" on **every** sheet, not switchable off. It is enforced by
`tests/test_branding.py`.

**That is a rule for contributions to this repository. It is not a condition of the
licence.** A fork that removes the strip does not violate the GPL and does not violate
this file — it must merely not use the marks, which under Section 2 it could not anyway.

> **Deliberately left open:** GPLv3 §7(b) would additionally allow requiring that an
> *author attribution* be preserved, which could make the line "Made with Bischof
> Snowboards Software" binding on forks without the work ceasing to be free software.
> That has **not** been done. It is a real tightening — every downstream redistributor
> must carry it, and F-Droid reviewers read §7 additions closely — and it is the
> copyright holder's decision, not a tidy-up. To adopt it, add it here as a clearly
> marked additional term.

---

*This file describes the intent of the copyright holder. It is not legal advice. Reasoning
about the licence as a whole is in [`docs/licensing/README.md`](docs/licensing/README.md).*
