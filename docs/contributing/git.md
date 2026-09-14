---
title: Git-Regeln
description: Verbindliche Regeln für Identität, Commits, Pushes und den Aufbau der Commit-Nachricht.
audience: developer
status: current
updated: 2026-09-14
---

# Git-Regeln

Verbindlich für **alle**, die in diesem Repo arbeiten — Menschen wie KI-Agenten. Diese Datei
ist die einzige Fassung dieser Regeln; `CLAUDE.md` und `AGENTS.md` verweisen hierher und
wiederholen sie nicht.

---

## 1 · Identität

Jeder Commit in diesem Repo trägt:

```
Leo Bischof <leo@bischof-snowboards.com>
```

Die Adresse ist lokal gesetzt (`git config user.email`) und gilt damit **nur** für dieses
Repo — eine globale `user.email` bleibt davon unberührt.

Kontrolle vor dem ersten Commit einer Sitzung:

```powershell
git config user.name    # -> Leo Bischof
git config user.email   # -> leo@bischof-snowboards.com
```

Die gesamte Historie wurde am 2026-09-07 auf diese Adresse umgeschrieben. Es gibt keinen
Commit mehr unter der alten. Wer einen findet, hat einen Fehler gefunden.

---

## 2 · Committen: ja. Pushen: nur auf Ansage.

Das ist die wichtigste Regel dieser Datei, und sie ist bewusst **asymmetrisch**.

| Handlung | Erlaubnis |
|---|---|
| `git commit` | **Ohne Rückfrage.** Fertige Arbeit gehört committet, nicht in einem schmutzigen Arbeitsverzeichnis geparkt. |
| `git push` (Feature-Branch) | **Nur nach ausdrücklicher Aufforderung.** Jedes Mal neu. |
| `git push` nach `master` **oder** `develop` | **Geht nicht mehr.** GitHub weist beide ab, auch vom Eigentümer — siehe Abschnitt 7. Der Weg hinein ist ausschließlich der Pull Request. |
| `git push --force` | Nur nach ausdrücklicher Aufforderung **für genau diesen Push**. Eine frühere Erlaubnis gilt nicht weiter. Auf `master` ohnehin gesperrt. |

Warum die Asymmetrie: ein Commit ist örtlich und umkehrbar — er kostet nichts und rettet
Arbeit. Ein Push ist öffentlich und für andere sofort sichtbar; ein `--force` kann fremde
Arbeit vernichten. Örtlich darf man mutig sein, nach außen nicht.

**Eine Erlaubnis gilt einmal.** „Push das" bezieht sich auf den Push, der gerade zur Debatte
steht, nicht auf die nächsten.

### Wann committet wird

**Sobald ein Feature fertig *und* geprüft ist — sofort, ungefragt.** Fertig-und-geprüft ist
nicht nur die *Erlaubnis* zu committen, es ist der *Auslöser*. Nicht sammeln, nicht „am Ende
alles zusammen", nicht auf eine Rückfrage warten.

Beide Hälften zählen, und die zweite ist die, die gern unterschlagen wird:

| | |
|---|---|
| **fertig** | Das Feature tut, was es tun soll — keine Platzhalter, kein „den Rest später". |
| **geprüft** | Es ist *gelaufen*. Testsuite grün, und zwar wirklich ausgeführt und angesehen. |

**„Geprüft" heißt: die Prüfung, die dieses Feature betrifft.** Eine grüne Python-Suite sagt
nichts über eine Änderung an der Oberfläche aus — `tests/` öffnet die Seite nie. Wer am
Frontend etwas ändert, startet den Server, sieht sich das Ergebnis an und beendet den Server
wieder; wer an der Geometrie etwas ändert, lässt die synthetischen Szenen laufen. Die falsche
Prüfung bestanden zu haben ist kein Beweis, sondern eine Verwechslung.

Was **nicht** committet wird: fremde Arbeit, die noch läuft. Ein Zwischenstand, den jemand
anders gerade schreibt, ist per Definition weder fertig noch geprüft — auch dann nicht, wenn
das Arbeitsverzeichnis danach aussieht.

---

## 3 · Ein Feature, ein Commit

Ein Commit ist **genau eine abgeschlossene Sache**. Nicht zwei kleine, weil sie zufällig
zusammen fertig wurden. Nicht eine halbe, weil der Rest noch dauert.

Maßstab: *Lässt sich der Commit in einem Satz beschreiben, ohne „und" zu benutzen?*
Wenn nein, sind es zwei Commits.

Daraus folgt:

- **Jeder Commit ist für sich lauffähig.** `.\dev.ps1 run-tests` ist nach jedem Commit grün
  — nicht erst nach dem dritten. Wer eine Konstante in `app/config.py` einführt, die erst
  ein späterer Commit benutzt, hat den Schnitt falsch gelegt.
- **Aufräumen ist ein eigener Commit.** Formatierung, Umbenennungen und Tippfehler reisen
  nicht als blinde Passagiere in einem `feat:` mit — sie machen den Diff unlesbar und
  verstecken die eigentliche Änderung.
- **Berührt eine Datei zwei Features, wird der Diff aufgeteilt**, nicht der Commit
  vergrößert. Notfalls die eine Hälfte kurz zurücknehmen, den ersten Commit setzen, die
  Hälfte wieder einsetzen, den zweiten Commit setzen.

---

## 4 · Aufbau der Commit-Nachricht

```
<kurze Zusammenfassung, englisch, mit konventionellem Präfix>
                    <- Leerzeile, zwingend
<ausführliche Beschreibung: warum, nicht was>
```

**Die erste Zeile** ist eine sehr kurze Zusammenfassung dessen, was getan wurde.
Englisch. Kleinschreibung nach dem Präfix. Kein Punkt am Ende. Richtwert 50 Zeichen,
Obergrenze 72. Imperativ („add", nicht „added" oder „adds").

Präfixe: `feat:` `fix:` `docs:` `chore:` `test:` `refactor:`

**Dann eine Leerzeile.** Ohne sie ist für Git der ganze Text der Betreff, und jede
Log-Ansicht bricht.

**Dann der Rumpf**, in ganzen Sätzen, umbrochen bei ~72 Zeichen. Der Rumpf erklärt das
**Warum**: welches Problem bestand, warum dieser Weg, was verworfen wurde und weshalb. Das
*Was* steht schon im Diff — es dort abzuschreiben ist verschenkter Platz.

**Der Rumpf ist englisch**, wie der Betreff. Das ist keine Vorliebe, sondern die gelebte
Praxis dieses Repos seit dem ersten Commit — und eine Historie, die auf halber Strecke die
Sprache wechselt, liest sich schlecht. Kommentare und interne Dokumentation bleiben deutsch
(`AGENTS.md`); die Historie ist davon ausgenommen.

### Beispiel

Ein echter Commit aus diesem Repo (`4fa85d1`), gekürzt:

```
feat: add light and dark theme tokens

The interface was hard-wired to dark, with the colours written as hex
straight into style.css. A second theme would have meant copying the
whole stylesheet.

The token names are taken from snow-service-free so that both tools
speak the same language. Three states are served: explicitly light,
explicitly dark, and the system preference as the fallback.

Colours are declared as hex on :root and lifted to oklch inside an
@supports block. The obvious approach -- hex and oklch back to back as
a fallback pair -- does not work for custom properties: their values
are not type-checked at parse time, so the oklch line always wins, and
a browser that cannot parse oklch does not fall back to the hex but to
unset.
```

Woran man einen guten Rumpf erkennt: er beantwortet die Frage, die sich in einem halben Jahr
jemand beim `git blame` stellt — *warum steht das so da und nicht anders?* Der Absatz über
`@supports` oben ist genau das. Ohne ihn würde der nächste Bearbeiter das Rückfallpaar
„aufräumen" und die Unterstützung für ältere Browser stillschweigend zerstören.

### Fußzeile

Von einem KI-Agenten gesetzte Commits tragen am Ende die von der Umgebung geforderte
`Co-Authored-By:`-Zeile. Sie steht nach einer Leerzeile am Schluss und ersetzt **nicht** die
Autorenangabe aus Abschnitt 1 — Autor bleibt Leo Bischof.

---

## 5 · Vor jedem Commit

1. `.\dev.ps1 run-tests` — und das Ergebnis wirklich ansehen.
   **Nie etwas als funktionierend committen, das nicht gelaufen ist.**
2. `git status` — nichts Unbeabsichtigtes dabei? Keine `out/`-Artefakte, keine
   Sitzungsdateien, keine Testbilder.
3. `git diff --staged` — steht im Commit genau das eine Feature?

Schlägt ein Test fehl, wird **nicht** committet und **nicht** „erstmal gesichert". Ein roter
Commit in der Historie ist eine Falle für den Nächsten, der bisecten muss.

---

## 6 · Branches: **niemals auf `master`, niemals auf `develop`**

> **Die Regel, ohne Ausnahme:** Jede Änderung entsteht auf einem **eigenen Branch** und
> kommt ausschließlich über einen **Pull Request** in den Stamm. Kein Commit wird je
> direkt auf `master` oder `develop` gesetzt — auch kein einzeiliger, auch keiner, der
> „nur Dokumentation" ist.

```
feat/…, fix/…, docs/…, chore/…  ──PR──►  develop  ──PR──►  master
```

Das gilt für **jede** Änderung, unabhängig von ihrer Größe. Es gibt keine Schwelle, unter
der sich der Branch nicht lohnt: der Branch kostet zwei Befehle, und die Schwelle wäre das
Einzige, worüber man jedes Mal neu nachdenken müsste.

**Bis 2026-09-14 stand hier das Gegenteil** — „der Normalfall ist, direkt auf `master` zu
arbeiten" —, und das war seit dem 08.09.2026 falsch: an diesem Tag bekamen `develop` und
`master` ihren Schutz (Abschnitt 7), und damit war direktes Arbeiten am Stamm nicht mehr
vorgesehen. Die beiden Abschnitte haben sich sechs Tage lang widersprochen. Der Satz steht
hier nicht aus Reue, sondern weil ein Agent genau diesem veralteten Absatz gefolgt ist und
eine ganze Sitzung auf `master` committet hat.

**Der Branch wird von `develop` abgezweigt, nicht von `master`.** `develop` ist der
Vorgabezweig des Repositories; `master` trägt nur die Release-Squashes und hat mit
`develop` keine gemeinsame Commit-Historie, sondern nur denselben Inhalt. Wer versehentlich
von `master` abzweigt, kommt mit einem Rebase zurück:

```powershell
git fetch origin
git rebase --onto origin/develop master <branch>
```

Benennung: `feat/…`, `fix/…`, `docs/…`, `chore/…`.

**Dazu gehört ein eigenes Arbeitsverzeichnis** (`git worktree`), kein Branch-Wechsel im
selben Ordner:

```powershell
git fetch origin
git worktree add -b feat/kurzname ../ArUco-Homographie-kurzname origin/develop
git worktree list
```

Der Grund ist praktisch. Ein `git checkout` im selben Ordner zieht allen anderen den
Boden weg, die dort gerade arbeiten — laufender Server, offene Datei im Editor, ein
zweiter Agent. Mit einem Worktree liegen beide Stände nebeneinander auf der Platte und
teilen sich ein `.git`. Ein frisches Worktree hat **kein** `venv`; `dev.ps1` legt es beim
ersten Lauf selbst an.

Aufräumen, wenn der Branch zurück im Stamm ist:

```powershell
git worktree remove ../ArUco-Homographie-kurzname
git branch -d feat/kurzname
```

**Was tun, wenn doch einmal auf dem Stamm committet wurde.** Solange nichts gepusht ist,
kostet es drei Befehle und niemand merkt es — der Zweig bekommt die Commits, der Stamm
bekommt seinen alten Stand zurück:

```powershell
git branch docs/kurzname          # die Commits festhalten
git checkout docs/kurzname
git branch -f master origin/master   # den Stamm zuruecksetzen
```

Ist schon gepusht, geht das nicht mehr: `master` und `develop` verbieten Force-Push. Dann
bleibt nur, den Fehlstand mit einem Revert-PR zu bereinigen — ein weiterer Grund, gar
nicht erst dort zu committen.

---

## 7 · Zwei geschützte Zweige: `develop` sammelt, `master` veröffentlicht

Seit 2026-09-08 gibt es **zwei** Stufen, und Arbeit geht nur in einer Richtung durch sie
hindurch:

```
feat/…, fix/…, docs/…  ──PR──►  develop  ──PR──►  master
                                (Sammeln)        (Veröffentlichen)
```

- **`develop` ist das Ziel jedes Feature-PRs.** Was fertig **und geprüft** ist, wird
  hierhin gemergt. `develop` ist auch der **Vorgabezweig** des Repositories — ein
  `gh pr create` ohne `--base` zielt von selbst hierher, damit man `master` nicht aus
  Versehen trifft.
- **`master` bekommt nur `develop`**, und zwar dann, wenn ein Stand ausgeliefert werden
  soll. Kein Feature-Branch zielt je direkt auf `master`.

**Wozu die zweite Stufe.** `master` soll den ausgelieferten Stand zeigen und nicht jeden
Zwischenschritt dorthin. Ein Umzug wie der auf den C++-Kern besteht aus einem Dutzend
Schritten, von denen einzeln keiner eine Fassung wert ist — zusammen sind sie eine. Auf
`master` steht danach **ein** Eintrag je Fassung, nicht zwölf.

Beide Zweige sind gleich hart geschützt: **kein direkter Push**, auch nicht vom Eigentümer
(`enforce_admins`), und der einzige Weg hinein ist ein **Pull Request, per Squash gemergt**.

Am Repository eingestellt (gilt für `develop` **und** `master`):

| Einstellung | Wert | Wozu |
|---|---|---|
| Squash-Merge | **erlaubt** | die einzige Merge-Art |
| Merge-Commit | gesperrt | keine Merge-Blasen in der Historie |
| Rebase-Merge | gesperrt | ausdrücklich nicht gewollt |
| Pull Request nötig | ja | direkte Pushes werden abgewiesen |
| Nötige Freigaben | **0** | Einzelbearbeiter: bei 1 könnte niemand seinen eigenen PR mergen |
| Lineare Historie | erzwungen | passt zu Squash, verbietet Merge-Commits auch am Branch |
| Force-Push, Löschen | gesperrt | `master` lässt sich nicht mehr umschreiben |
| Branch nach Merge löschen | automatisch | räumt die Feature-Branches selbst auf |

### Was daraus für den Zuschnitt folgt

**Ein Feature, ein Branch, ein Pull Request.** Beim Squash-Merge wird der ganze PR zu
**einem** Commit auf `master` — die Einheit der Historie ist also nicht mehr der einzelne
Commit, sondern der PR. Zwei Features in einem PR landen als ein einziger Commit auf
`master`, und damit wäre Abschnitt 3 ausgehebelt.

Innerhalb des Branches darf und soll trotzdem kleinteilig committet werden: diese Commits
sind die Arbeitsspur, der PR-Titel wird der Commit-Betreff auf `master`. Also gilt für den
**PR-Titel** genau, was Abschnitt 4 über den Betreff sagt, und die PR-Beschreibung trägt
das Warum.

### Der Ablauf

**Ein Feature, von `develop` nach `develop`:**

```powershell
git worktree add -b feat/kurzname ../ArUco-Homographie-kurzname develop
# arbeiten, committen, Tests grün halten
git push -u origin feat/kurzname          # nur auf Ansage
gh pr create --title "feat: kurzer betreff" --body "..."   # zielt von selbst auf develop
gh pr merge --squash --delete-branch      # nur auf Ansage
```

Danach das Worktree entfernen (Abschnitt 6). `develop` örtlich wieder einholen mit
`git pull --ff-only` — der Squash-Commit ist ein **anderer** Commit als die eigenen, der
lokale Branch ist danach Geschichte und wird nicht weiterverwendet.

**Eine Fassung, von `develop` nach `master`:**

```powershell
# Ein Zweig, der VON master abzweigt und den Baum von develop traegt.
git fetch origin
git checkout -b release/0.1.1-alpha origin/master
git rm -rq --ignore-unmatch .          # alles weg ...
git checkout origin/develop -- .       # ... und durch develops Baum ersetzen
git commit -m "release: 0.1.1-alpha — …"
git diff --stat origin/develop         # MUSS leer sein
git push -u origin release/0.1.1-alpha

gh pr create --base master --head release/0.1.1-alpha --title "release: 0.1.1-alpha — …"
gh pr merge --squash --delete-branch
```

**Warum nicht `--head develop`?** Weil das ab der zweiten Fassung nicht mehr geht — der
nächste Abschnitt sagt, warum. Die Zeile `git diff --stat origin/develop` ist die
Prüfung, die das Verfahren trägt: sie muss **leer** sein. Ist sie es, hat `master` danach
Zeichen für Zeichen den Baum von `develop`, und das ist der ganze Zweck der zweiten Stufe.

**Danach passiert nichts mehr.** `develop` wird *nicht* auf `master` eingeholt — und das
ist der Punkt, an dem eine frühere Fassung dieses Abschnitts falsch lag. Sie schrieb
`git checkout develop; git merge master; git push` vor. Das geht nicht, und es ist
überflüssig:

**Es geht nicht.** `required_linear_history` gilt auch für `develop` (Tabelle oben) und
weist einen Merge-Commit ab. Am 08.09.2026 auf einem Wegwerf-Zweig mit derselben
Einstellung nachgestellt: ein gewöhnlicher Commit ging durch, der Merge-Commit nicht.

```
remote:   Found 1 violation:
 ! [remote rejected] HEAD -> tmp/linear-probe (protected branch hook declined)
```

**Es ist überflüssig.** Der Squash-Commit auf `master` trägt genau den Baum, den
`develop` in diesem Augenblick hat. Nach dem Merge sind die beiden Zweige inhaltlich
deckungsgleich; verschieden ist nur, wie sie dorthin gekommen sind. Genau das war der
Zweck der zweiten Stufe.

### Warum der Release-Zweig sein muss: ab der zweiten Fassung kollidiert `develop`

Weil der Squash-Commit auf `master` **kein Vorfahr** von `develop` ist, bleibt der
gemeinsame Vorfahr der beiden Zweige stehen, wo er war. In der Drei-Wege-Verschmelzung
sieht Git deshalb **beide Seiten dieselben Dateien seither ändern** — `master` durch den
Squash, `develop` durch die Commits, aus denen der Squash entstand — und ruft einen
Konflikt aus, obwohl niemand widersprüchlich gearbeitet hat.

Am 08.09.2026 beim Ausliefern von `0.1.1-alpha` eingetreten. `gh pr merge` wies ab, und
`git merge-tree origin/develop origin/master` nannte den Grund:

```
CONFLICT (content): Merge conflict in CHANGELOG.md
CONFLICT (add/add): Merge conflict in android/app/build.gradle.kts
```

Zwei Sorten, und beide treffen **jedes** Release ab dem zweiten:

| | |
|---|---|
| `add/add` | Jede Datei, die seit dem gemeinsamen Vorfahren **neu** dazugekommen ist. Für den Vorfahren gibt es sie nicht, also haben beide Seiten sie *angelegt* — mit verschiedenem Inhalt, weil `develop` sie inzwischen weiterentwickelt hat. |
| `content` | `CHANGELOG.md`, immer. Jede Fassung fügt ihren Eintrag **an derselben Stelle** ein, direkt unter dem Kopf. |

**Der erste Release merkt davon nichts** — da war der Squash-Commit selbst noch nicht da.
Deshalb stand hier bis 0.1.1-alpha ein Verfahren, das genau einmal funktioniert hat.

Der Release-Zweig umgeht das, weil er **von `master` abzweigt**: er verschmilzt nichts,
er setzt den Baum. `git diff --stat origin/develop` ist danach leer, und das ist der
einzige Beleg, auf den es ankommt.

**Der Inhalt stimmt immer.** Was eine Fassung *enthält*, sagt `CHANGELOG.md` — nicht die
Commit-Liste des Release-PRs.

Der Ausweg wäre, `required_linear_history` für `develop` abzuschalten; dann ginge der
Merge zurück, der gemeinsame Vorfahr wanderte mit, und `--head develop` funktionierte
wieder. Das ist **nicht** getan: eine Schutzeinstellung wird nicht gelockert, um vier
Zeilen `git` zu sparen — und die vier Zeilen haben eine Prüfung, die der Merge nicht hat
(`git diff --stat origin/develop` ist leer oder es stimmt etwas nicht).

### Wenn der Schutz einmal im Weg steht

Er ist Absicht, nicht Versehen. Er wird nicht „mal eben" abgeschaltet, um einen Push
durchzubekommen — das ist genau der Reflex, gegen den er existiert. Wer ihn wirklich
ändern muss, tut es sichtbar und stellt ihn danach wieder her.
