# CLAUDE.md

**Die Projektregeln stehen in [AGENTS.md](AGENTS.md) — dort zuerst lesen.** Diese Datei
wiederholt sie nicht; eine zweite Fassung würde nur auseinanderlaufen.

Hier steht nur, was speziell für Claude Code in diesem Repo gilt.

## Vor dem Anfassen

- `AGENTS.md` lesen, besonders die **Invarianten**. Millimeter sind das Produkt.
- Die Spezifikation liegt in `docs/superpowers/specs/` und ist mit dem Code abgeglichen.
  Wer Verhalten ändert, ändert sie mit — ein Spec, der die Unwahrheit sagt, ist
  schlimmer als keiner.

## Werkzeuge in diesem Repo

- **Dateien anlegen mit dem Write-Werkzeug.** Sehr lange Heredocs brechen in dieser
  Shell mitten im Dokument ab und hinterlassen eine ratlose Fehlermeldung.
- **PDFs kann man ansehen.** `pymupdf` ist installiert:
  ```python
  import pymupdf
  pymupdf.open(stream=pdf_bytes, filetype="pdf")[0].get_pixmap(dpi=110).save("check.png")
  ```
  Danach das PNG wirklich anschauen. Ein Layout, das niemand gesehen hat, ist ungeprüft.
- **Die Oberfläche kann man ansehen.** Server auf einem freien Port starten
  (`python -m uvicorn app.main:app --port 8010`), mit Playwright einen Screenshot machen,
  Server danach **sofort** beenden. Nie den Server beenden, den der Benutzer gestartet
  hat — `dev.ps1 kill-servers` trifft beide.

## Behauptungen

Nichts als funktionierend melden, was nicht gelaufen ist. `.\dev.ps1 run-tests` und das
Ergebnis nennen. Wenn etwas nicht geprüft werden konnte, das so sagen — insbesondere,
dass die Maßhaltigkeit bis heute nur gegen synthetische Szenen belegt ist und der
Beweis am echten Ausdruck (drucken, mit dem Messschieber nachmessen) noch aussteht.

## Git

**Die Regeln stehen in [docs/contributing/git.md](docs/contributing/git.md)** — dort steht
die verbindliche Fassung, hier nur das, was man ohnehin auswendig können muss:

- **Committen ohne Rückfrage, pushen nur auf Ansage.** Örtlich mutig, nach außen nicht.
  Eine Push-Erlaubnis gilt für genau einen Push, nicht für die nächsten.
- **Ein Feature, ein Commit.** Braucht die Beschreibung ein „und", sind es zwei.
- **Betreff englisch** mit konventionellem Präfix, dann eine **Leerzeile**, dann der Rumpf,
  der das *Warum* erklärt.
- Jeder Commit ist für sich lauffähig: `.\dev.ps1 run-tests` ist grün, bevor er gesetzt wird.

Diese Regel weicht bewusst von der globalen `~/.claude/CLAUDE.md` ab, die das Committen an
eine Rückfrage bindet. Für dieses Repo gilt die hiesige Fassung.
