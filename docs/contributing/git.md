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
| `git push` | **Nur nach ausdrücklicher Aufforderung.** Jedes Mal neu. |
| `git push --force` | Nur nach ausdrücklicher Aufforderung **für genau diesen Push**. Eine frühere Erlaubnis gilt nicht weiter. |

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

## 6 · Offener Punkt

Es wird derzeit direkt auf `master` gearbeitet; die ganze Historie liegt dort. Ein
Branch-und-PR-Verfahren ist bewusst **nicht** eingeführt — bei einem Bearbeiter wäre es
Zeremonie ohne Nutzen. Sobald ein zweiter Mensch mitschreibt, gehört diese Entscheidung neu
getroffen und hier ersetzt.
