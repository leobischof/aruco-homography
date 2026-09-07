---
title: Git-Regeln
description: Verbindliche Regeln für Identität, Commits, Pushes und den Aufbau der Commit-Nachricht.
audience: developer
status: current
updated: 2026-09-07
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
| `git push` nach `master` | **Geht nicht mehr.** GitHub weist es ab — siehe Abschnitt 7. |
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

## 6 · Branches

`master` ist der Stamm, und der Normalfall ist, direkt dort zu arbeiten. Ein
Branch-und-PR-Verfahren für **jede** Änderung ist bewusst nicht eingeführt — bei einem
Bearbeiter wäre es Zeremonie ohne Nutzen, und Abschnitt 3 verlangt ohnehin, dass jeder
einzelne Commit für sich lauffähig ist.

Ein Branch wird dann angelegt, wenn genau diese Regel sonst bricht: wenn ein Vorhaben
**über mehrere Commits hinweg unfertig** wäre und der Stamm in dieser Zeit nicht mehr
grün oder nicht mehr benutzbar bliebe. Ein Umbau der Paketierung ist so ein Fall, das
Hinzufügen eines Reglers nicht.

Benennung: `feat/…`, `fix/…`, `chore/…`.

**Dazu gehört ein eigenes Arbeitsverzeichnis** (`git worktree`), kein Branch-Wechsel im
selben Ordner:

```powershell
git worktree add -b feat/kurzname ../ArUco-Homographie-kurzname master
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

Sobald ein zweiter Mensch mitschreibt, gehört diese Entscheidung neu getroffen und hier
ersetzt.

---

## 7 · `master` ist geschützt — es führt nur ein Weg hinein

Seit 2026-09-07 nimmt GitHub auf `master` **keinen direkten Push mehr an**, auch nicht vom
Eigentümer (`enforce_admins`). Der einzige Weg ist ein **Pull Request, per Squash gemergt**.

Am Repository eingestellt:

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

```powershell
git worktree add -b feat/kurzname ../ArUco-Homographie-kurzname master
# arbeiten, committen, Tests grün halten
git push -u origin feat/kurzname          # nur auf Ansage
gh pr create --base master --title "feat: kurzer betreff" --body "..."
gh pr merge --squash --delete-branch      # nur auf Ansage
```

Danach das Worktree entfernen (Abschnitt 6). `master` örtlich wieder einholen mit
`git pull --ff-only` — der Squash-Commit ist ein **anderer** Commit als die eigenen, der
lokale Branch ist danach Geschichte und wird nicht weiterverwendet.

### Wenn der Schutz einmal im Weg steht

Er ist Absicht, nicht Versehen. Er wird nicht „mal eben" abgeschaltet, um einen Push
durchzubekommen — das ist genau der Reflex, gegen den er existiert. Wer ihn wirklich
ändern muss, tut es sichtbar und stellt ihn danach wieder her.
