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

Nur committen, wenn danach gefragt wurde. Betreff englisch mit konventionellem Präfix,
Rumpf erklärt das Warum. Ein Commit, eine Sache.
