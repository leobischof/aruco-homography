---
title: Dokumentation
description: Verzeichnis aller Dokumente dieses Repos, mit Zweck, Zielgruppe und Stand.
audience: developer
status: current
updated: 2026-09-07
---

# Dokumentation

Diese Seite ist das **Inhaltsverzeichnis**. Jede Markdown-Datei unter `docs/` steht in der
Tabelle unten, mit Pfad, Zweck, Zielgruppe und Stand. Wer hier ankommt, soll nach einmal
Lesen wissen, welche Datei er aufmachen muss — und keine zweite Suchrunde brauchen.

---

## 1 · Alle Dokumente

### Unter `docs/`

| Datei | Wozu | Für wen | Stand |
|---|---|---|---|
| [`README.md`](README.md) | Diese Seite: Verzeichnis, Ordnungsregeln, Frontmatter-Schema | developer | current |
| [`plans.md`](plans.md) | Vorhaben, die beschlossen, aber **nicht gebaut** sind — mit Weg, Stolpersteinen und offenen Fragen | developer | current |
| [`design/README.md`](design/README.md) | Einstieg ins Designsystem: die drei Dinge, die man vorher wissen muss | developer | current |
| [`design/design-system.md`](design/design-system.md) | Farbe, Typografie, Form, Komponenten, Themen, Sprachen, Bewegung, Mobil — und was aus dem Webprojekt **nicht** zu übernehmen ist | developer | current |
| [`contributing/git.md`](contributing/git.md) | Verbindliche Git-Regeln: Identität, wann committet und wann gepusht wird, Aufbau der Commit-Nachricht | developer | current |
| [`superpowers/specs/2026-09-06-aruco-homographie-design.md`](superpowers/specs/2026-09-06-aruco-homographie-design.md) | Die Spezifikation dessen, was **existiert**, mit dem Code abgeglichen | developer | current |
| [`cpp-migration/stage-4-web.md`](cpp-migration/stage-4-web.md) | Stufe 4: die ganze Kette ohne Server im Browser — was gemessen ist, wie gebaut wird, und was der Bau nicht kann | developer | current |

### Außerhalb von `docs/` — die Dateien an der Wurzel

Sie gehören dazu, stehen aber bewusst dort, wo ein Werkzeug oder ein Besucher sie zuerst
sucht. Deshalb tragen sie **kein** Frontmatter (siehe [§3](#3--frontmatter)).

| Datei | Wozu | Für wen |
|---|---|---|
| [`../README.md`](../README.md) | Die Eingangstür: was das Werkzeug ist, wie man es startet, wie man richtig druckt | operator |
| [`../CHANGELOG.md`](../CHANGELOG.md) | Was sich wann geändert hat, nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/) | developer |
| [`../AGENTS.md`](../AGENTS.md) | Arbeitsanweisung für KI-Agenten: die **Invarianten**, die nicht gebrochen werden dürfen | agent |
| [`../CLAUDE.md`](../CLAUDE.md) | Was speziell für Claude Code in diesem Repo gilt; verweist auf `AGENTS.md` | agent |

---

## 2 · Warum die Ordner so heißen

Zwei Ebenen, mehr nicht. **Ein Ordner trägt entweder den Namen seiner Leserschaft oder den
Namen seines Gegenstands** — nie den einer Dateiart („guides", „misc", „notes"). Ein
einzelnes Dokument, das zu keiner Gruppe gehört, liegt direkt unter `docs/`.

| Ordner | Was drin ist | Warum der Name |
|---|---|---|
| `design/` | Wie das Werkzeug aussehen soll und warum | Gegenstand. Wächst um Komponenten- und Layoutseiten, ohne den Namen zu sprengen. |
| `contributing/` | Regeln für alle, die hier schreiben — Mensch wie Agent | Leserschaft. Nimmt später Test- und Release-Regeln auf. |
| `superpowers/specs/` | Die Spezifikation dessen, was existiert | Herkunft: der Name kommt vom Werkzeug, das diese Specs erzeugt und wiederfindet. Er bleibt deshalb, wie er ist. |

`plans.md` liegt **flach**. Ein Ordner um eine einzige Datei ist ein zusätzlicher Klick ohne
Gegenwert; er kommt an dem Tag, an dem daraus drei Dateien werden — und dann heißt er nach
seinem Gegenstand, nicht nach seiner Form.

Was hier bewusst **nicht** steht: eine Bedienungsanleitung. Die steht in
[`../README.md`](../README.md), weil ein Bediener genau eine Seite lesen will und nicht
einen Ordnerbaum.

**Die drei Zeitformen liegen bewusst auseinander** — sie widersprechen sich sonst:

| Frage | Datei |
|---|---|
| Was ist **fertig**? | [`../CHANGELOG.md`](../CHANGELOG.md) |
| Was **existiert** heute, im Detail? | [`superpowers/specs/`](superpowers/specs/) |
| Was ist **noch nicht gebaut**? | [`plans.md`](plans.md) |

---

## 3 · Frontmatter

**Jede Markdown-Datei unter `docs/` beginnt mit einem YAML-Block.** Er macht den Baum
maschinenlesbar: ein Skript kann alle Dokumente aufzählen, prüfen und die Tabelle in §1
gegen die Wirklichkeit halten, ohne eine Zeile Fließtext zu verstehen.

```yaml
---
title: Designsystem Bischof Snowboards
description: Farbe, Typografie, Form und Komponenten des Hauses.
audience: developer
status: current
updated: 2026-09-07
---
```

Genau diese fünf Schlüssel, alle Pflicht, keine weiteren:

| Schlüssel | Typ | Bedeutung |
|---|---|---|
| `title` | Text | Die Überschrift des Dokuments. Deckungsgleich mit der ersten `#`-Zeile. |
| `description` | Text, **eine Zeile** | Wozu das Dokument da ist. Der Satz, der in §1 in der Spalte „Wozu" steht. |
| `audience` | `operator` \| `developer` \| `agent` | Wer es liest. `operator` bedient das Werkzeug, `developer` ändert Code, `agent` ist eine KI, die hier arbeitet. Genau einer der drei — wer sich nicht entscheiden kann, hat zwei Dokumente. |
| `status` | `current` \| `draft` \| `superseded` | `current` = gilt und ist mit dem Code abgeglichen. `draft` = im Werden, noch nicht verbindlich. `superseded` = überholt, bleibt nur der Historie wegen liegen; die Ablösung wird im Text genannt. |
| `updated` | `YYYY-MM-DD` | Tag der letzten inhaltlichen Änderung. Tippfehler zählen nicht. |

### Wer welchen Block bekommt

- **Alles unter `docs/`**: ja, ausnahmslos — die Spezifikation unter `superpowers/specs/`
  eingeschlossen. Sie wird allerdings von dem Werkzeug gepflegt, das sie erzeugt und
  fortschreibt; wer nur an der Ordnung arbeitet, fasst ihren Inhalt nicht nebenbei mit an.
- **Die Dateien an der Wurzel** (`README.md`, `CHANGELOG.md`, `AGENTS.md`, `CLAUDE.md`):
  nein. GitHub rendert Frontmatter dort als graue Tabelle über der Überschrift — die
  Eingangstür des Projekts würde mit Verwaltungsangaben beginnen. Ihr Platz ist stattdessen
  die zweite Tabelle in §1.

### Aufzählen und prüfen

```powershell
Get-ChildItem docs -Recurse -Filter *.md |
    ForEach-Object {
        $meta = @{}
        foreach ($line in (Get-Content $_.FullName -TotalCount 8)) {
            if ($line -match '^(\w+):\s*(.+)$') { $meta[$Matches[1]] = $Matches[2] }
        }
        [pscustomobject]@{
            Datei      = Resolve-Path -Relative $_.FullName
            Zielgruppe = $meta['audience']
            Stand      = $meta['status']
            Geaendert  = $meta['updated']
        }
    } | Format-Table -AutoSize
```

Für eine echte **Prüfung** — fünf Schlüssel vorhanden, Werte aus dem erlaubten Vorrat,
`updated` als Datum lesbar, jeder Querverweis auf eine existierende Datei — reicht ein
kurzes Python-Skript, das den Block zwischen der ersten und der zweiten `---`-Zeile durch
`yaml.safe_load` schickt. Ein solches Skript existiert **noch nicht**; dieses Schema ist die
Voraussetzung dafür, nicht sein Ersatz.

---

## 4 · Regeln für neue Dokumente

1. **Sprache: Deutsch.** Interne Dokumentation ist deutsch (`AGENTS.md`, Konventionen).
   Einzige Ausnahme ist die Eingangstür [`../README.md`](../README.md).
2. **Frontmatter zuerst**, dann eine `#`-Überschrift, die dem `title` entspricht.
3. **In §1 eintragen.** Ein Dokument, das nicht im Verzeichnis steht, findet niemand.
4. **Querverweise relativ** (`design/design-system.md`, nicht `/docs/design/...`), damit sie
   im Editor, auf GitHub und in einer lokalen Vorschau gleichermaßen funktionieren.
5. **Ein Zweck, eine Datei.** Wer zwei Zielgruppen bedienen will, schreibt zwei Dokumente.
6. **Wird ein Dokument abgelöst**, bekommt es `status: superseded` und einen Satz nach oben,
   der auf die Ablösung zeigt. Gelöscht wird es nicht — sonst zeigen alte Verweise ins Leere.
