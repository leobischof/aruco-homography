---
title: Designsystem Bischof Snowboards
description: Farbe, Typografie, Form, Komponenten, Themen, Sprachen und Mobil — und was aus dem Webprojekt nicht zu übernehmen ist.
audience: developer
status: current
updated: 2026-09-07
---

# Designsystem Bischof Snowboards

Diese Seite beantwortet eine Frage: **jemand baut morgen ein neues Werkzeug für
Bischof Snowboards — was muss er wissen, damit es aussieht und sich anfühlt, als
gehöre es dazu?**

Die Quelle ist das Webprojekt `snow-service-free` (im Folgenden **free**), genauer
`free/src/main.css`. Dort steht das Haus-Designsystem im Original. Alles hier ist
daraus abgeleitet, und jede Behauptung nennt ihre Datei. Wo dieses Repo abweicht,
steht die Abweichung mit Begründung in [§3.6](#36-wo-dieses-repo-abweicht) — nicht
versteckt, weil eine unbegründete Abweichung beim nächsten Mal als Vorbild
missverstanden wird.

Die arbeitende Fassung für dieses Repo ist `app/static/css/tokens.css`.

---

## 1 Die Kurzfassung

| | |
|---|---|
| Schrift | Montserrat variabel, 400/500/600/700 |
| Markenfarbe | `--primary` Petrol `#379992` |
| Handlungsfarbe | `--action` Bernstein `#ffbf00` |
| Grundradius | `--radius: 0.625rem` (10px), vier abgeleitete Stufen |
| Themen | hell **und** dunkel, beide vollwertig |
| Sprachen | Deutsch und Englisch, Deutsch zuerst |
| Rhythmus | Vielfache von `0.25rem` |

Zwei Sätze, die den Rest erklären:

- **Farben treten paarweise auf.** `--x` ist eine Fläche, `--x-foreground` ist die
  Tinte, die darauf lesbar ist. Nie einzeln benutzen.
- **`--primary` ist Identität, `--action` ist Aufforderung.** Petrol sagt „das hier
  ist von uns“. Bernstein sagt „drück hier“. Es gibt pro Ansicht genau eine
  Bernsteinfläche.

---

## 2 Herkunft und Geltungsbereich

**free** ist eine Vue-3-SPA mit Vite, Tailwind 4 und shadcn-vue. Sie hat einen
Build-Schritt, und ein großer Teil ihres Aussehens entsteht erst darin.

**Dieses Repo** ist FastAPI mit statischen Dateien: ein `<link>` auf ein Stylesheet,
eine `app.js`, kein Node, kein Bundler, kein Framework. Das ist keine Zwischenstufe,
die später ersetzt wird, sondern die Bauform — ein Werkzeug, das man auf einem
Werkstattrechner mit `dev.ps1 start-server` startet, darf keine Node-Installation
voraussetzen.

Daraus folgt die wichtigste Regel dieses Dokuments: **die Werte werden übernommen,
die Mechanik nicht.** Welche Muster als reines CSS tragen und welche nicht, steht
in [§11](#11-was-nicht-zu-übernehmen-ist).

Ein dritter Ort führt dieselben Farben: `app/config.py`, Block `# --- Marke ---`.
Er ist die SSOT für die Farben im **PDF** (ReportLab braucht Hex). Die Werte dort
und die Tokens hier sind gegengerechnet und stimmen auf das Byte — siehe
[§3.7](#37-gegenprobe-gegen-configpy).

---

## 3 Farbe

### 3.1 Das Paar-Prinzip

`free/src/main.css` führt fast jede Farbe als Paar:

```
--card              die Fläche
--card-foreground   die Tinte darauf
```

Der Grund ist der Themenwechsel. Wenn die Fläche im dunklen Thema kippt, kippt die
Tinte mit, und zwar in derselben Zeile Gedankenarbeit. Eine Vordergrundfarbe auf
einer fremden Fläche ist deshalb immer ein Fehler, auch wenn sie zufällig gerade
lesbar ist — sie ist es nur in einem der beiden Themen.

Nicht gepaart sind die reinen Zustandsfarben (`--border`, `--input`, `--ring`) und
`--muted-foreground`, das trotz seines Namens keine Tinte für `--muted` ist, sondern
die **Nebentinte auf dem Seitengrund**: Beschriftungen, Hinweise, Einheiten. Das ist
der einzige Name im System, der irreführt, und er ist aus shadcn geerbt.

### 3.2 `--primary` und `--action`

Zwei Markenfarben, zwei Aufgaben, und sie sind nicht austauschbar.

**`--primary`** ist das Petrol der Marke, `#379992`. Es trägt Identität und Zustand:
Fokusring (`--ring` zeigt darauf), aktive Auswahl, die Ziffern der Schrittfolge, die
Markenzeile im Kopf. In free ist es zusätzlich die Farbe der Sidebar-Akzente
(`--sidebar-primary`, `--sidebar-accent`) und der primären Flanke im Kurveneditor
(`--curve-flank-primary: var(--primary)`).

**`--action`** ist Bernstein, `#ffbf00`. Es trägt **genau eine** Sache pro Ansicht:
den Knopf, der die Sache tut. `free/src/components/shadcn/ui/button/index.ts` führt
`action` und `primary` als getrennte Varianten, und das ist der Punkt — zwei
Bernsteinknöpfe nebeneinander heben sich gegenseitig auf.

Merkhilfe für die Entscheidung: *Petrol sagt, wer wir sind. Bernstein sagt, was du
als Nächstes tun sollst.*

Praktisch wichtig: Bernstein erreicht auf Weiß **1,65:1**. Als Textfarbe ist es im
hellen Thema unbenutzbar; als Fläche mit `--action-foreground` darauf steht es bei
**9,30:1**. Deshalb hat der Qualitätsbericht eigene Töne, siehe [§3.5](#35-tokens-dieser-anwendung).

### 3.3 Tokentabelle — helles Thema

sRGB-Hex und oklch sind derselbe Wert; die Hex-Spalte ist die nachgerechnete
sRGB-Umrechnung. Wo die Zeile mit ° markiert ist, liegt der oklch-Wert außerhalb von
sRGB, und die beiden Notationen unterscheiden sich auf einem P3-Bildschirm minimal.

| Token | Hex | oklch | Wofür |
|---|---|---|---|
| `--background` | `#f0f3f3` | `oklch(0.9619 0.0032 197.1)` | Seitengrund |
| `--foreground` | `#334155` | `oklch(0.3717 0.0392 257.29)` | Haupttinte; zugleich die Tinte des Logos |
| `--card` | `#ffffff` | `oklch(1 0 0)` | Karte, Abschnitt, Panel |
| `--card-foreground` | `#334155` | `oklch(0.3717 0.0392 257.29)` | Tinte auf der Karte |
| `--popover` | `#ffffff` | `oklch(1 0 0)` | aufklappendes Menü, Hinweisblase |
| `--popover-foreground` | `#334155` | `oklch(0.3717 0.0392 257.29)` | Tinte darin |
| `--primary` | `#379992` | `oklch(0.6245 0.0905 188.44)` | Marke, Fokus, aktiver Zustand |
| `--primary-foreground` | `#f1f5f9` | `oklch(0.9683 0.0069 247.9)` | helle Haustinte (siehe Warnung unten) |
| `--action` | `#ffbf00` ° | `oklch(0.8403 0.1724 84.08)` | die eine Handlung der Ansicht |
| `--action-foreground` | `#25242b` | `oklch(0.2643 0.013 292.04)` | Tinte auf Bernstein |
| `--secondary` | `#e2e8f0` | `oklch(0.9288 0.0126 255.51)` | ruhige Fläche, Chip |
| `--secondary-foreground` | `#25242b` | `oklch(0.2643 0.013 292.04)` | Tinte darauf |
| `--muted` | `#e2e8f0` | `oklch(0.9288 0.0126 255.51)` | Feldfläche, Tabellenzeile |
| `--muted-foreground` | `#596474` | `oklch(0.5 0.029 257.29)` | Nebentinte: Beschriftung, Hinweis, Einheit |
| `--accent` | `#f0f3f3` | `oklch(0.9619 0.0032 197.1)` | leiseste Fläche, Hover-Grund |
| `--accent-foreground` | `#334155` | `oklch(0.3717 0.0392 257.29)` | Tinte darauf |
| `--destructive` | `#e7000b` ° | `oklch(0.577 0.245 27.325)` | Abbruchknopf, Fehlerbanner (Fläche) |
| `--destructive-foreground` | `#ffffff` | `oklch(1 0 0)` | Tinte darauf |
| `--border` | `#cbd5e1` | `oklch(0.869 0.0198 252.89)` | Trennlinie, Rahmen |
| `--input` | `#e2e8f0` | `oklch(0.9288 0.0126 255.51)` | Feldfläche und -rahmen |
| `--ring` | → `--primary` | | Fokusring |
| `--ring-soft` | `rgba(55,153,146,.5)` | `oklch(0.6245 0.0905 188.44 / 0.5)` | weicher Außenring des Fokus (§6.7) |

**Warnung zu `--primary-foreground`.** Der Wert ist der des Hauses und stimmt mit
`BRAND_LIGHT` in `app/config.py` überein; auf dem dunklen Markenstreifen im PDF steht
er bei 14:1. Direkt auf einer `--primary`-Fläche erreicht er aber nur **3,13:1** und
fällt als Knopfbeschriftung durch. Dort gehört `--action-foreground` hin (**4,49:1**).
Das ist ein Fehler, den free ebenfalls hat; der Token bleibt trotzdem auf seinem Wert,
weil ein stillschweigend abweichender vierter Wert die drei Orte auseinanderführen
würde.

### 3.4 Tokentabelle — dunkles Thema

Nur die Tokens, die sich ändern. Alles Nichtgenannte gilt aus §3.3 weiter — besonders
`--primary`, `--action` und deren Vordergründe: **eine Marke, die je nach Tageslicht
die Farbe wechselt, ist keine.**

| Token | Hex | oklch | Wofür |
|---|---|---|---|
| `--background` | `#25242b` | `oklch(0.2643 0.013 292.04)` | Seitengrund |
| `--foreground` | `#f1f5f9` | `oklch(0.9683 0.0069 247.9)` | Haupttinte |
| `--card` | `#2d2c34` | `oklch(0.2974 0.0144 291.23)` | Karte, Abschnitt |
| `--card-foreground` | `#f1f5f9` | `oklch(0.9683 0.0069 247.9)` | Tinte darauf |
| `--popover` | `#2d2c34` | `oklch(0.2974 0.0144 291.23)` | Menü, Hinweisblase |
| `--popover-foreground` | `#f1f5f9` | `oklch(0.9683 0.0069 247.9)` | Tinte darin |
| `--secondary` | `#36353c` | `oklch(0.3327 0.0122 292.28)` | ruhige Fläche |
| `--secondary-foreground` | `#f1f5f9` | `oklch(0.9683 0.0069 247.9)` | Tinte darauf |
| `--muted` | `#36353c` | `oklch(0.3327 0.0122 292.28)` | Feldfläche |
| `--muted-foreground` | `#9ca3af` | `oklch(0.7137 0.0192 261.32)` | Nebentinte |
| `--accent` | `#36353c` | `oklch(0.3327 0.0122 292.28)` | Hover-Grund |
| `--accent-foreground` | `#f1f5f9` | `oklch(0.9683 0.0069 247.9)` | Tinte darauf |
| `--destructive` | `#82181a` | `oklch(0.396 0.141 25.723)` | Fehlerfläche |
| `--destructive-foreground` | `#f1f5f9` | `oklch(0.9683 0.0069 247.9)` | Tinte darauf |
| `--border` | `#43424c` | `oklch(0.3839 0.0169 290.17)` | Trennlinie |
| `--input` | `#36353c` | `oklch(0.3327 0.0122 292.28)` | Feldfläche |

Die Höhenleiter ist in beiden Themen dieselbe Idee, nur gespiegelt:
**Seite < Karte < Feld.** Hell `#f0f3f3 → #ffffff → #e2e8f0`, dunkel
`#25242b → #2d2c34 → #36353c`.

### 3.5 Tokens dieser Anwendung

free kennt sie nicht, weil es diese Aufgaben nicht hat. Alle sind aus den
Markentokens abgeleitet; keine neue Farbe wurde erfunden.

| Token | hell | dunkel | Wofür |
|---|---|---|---|
| `--tone-good` | `#00736d` | `#5ab8b1` | Qualitätsbericht: Wert in Ordnung |
| `--tone-warn` | `#935800` | `#ffbf00` | Qualitätsbericht: Schwelle gerissen |
| `--tone-bad` | `#d20000` | `#fd736c` | Qualitätsbericht: unbrauchbar |
| `--hull-fill` | `rgba(55,153,146,.14)` | gleich | Füllung der Marker-Hülle |
| `--hull-stroke` | `rgba(55,153,146,.85)` | gleich | Kontur der Marker-Hülle |
| `--crop-stroke` | → `--action` | gleich | Kontur des Zuschnitt-Rechtecks |
| `--crop-fill` | `rgba(255,191,0,.10)` | gleich | Füllung darin |
| `--crop-halo` | `rgba(37,36,43,.55)` | gleich | dunkle Naht unter der hellen Kernlinie |
| `--crop-dim` | `rgba(37,36,43,.45)` | gleich | Abdunklung außerhalb des Rechtecks |
| `--crop-handle` | → `--card` | → `--card` | Füllung der Eckgriffe (deckend) |
| `--crop-handle-stroke` | → `--crop-stroke` | gleich | Kontur der Griffe |
| `--crop-handle-hover` | → `--action` | gleich | Griff unter dem Zeiger |
| `--crop-handle-active` | `#dd9f00` | gleich | Griff im Zugriff |
| `--scrim` | `rgba(240,243,243,.88)` | `rgba(37,36,43,.85)` | Schleier während der Berechnung |
| `--touch-target` | `2.75rem` | gleich | Mindestgröße am Handy |

Drei Entscheidungen darin sind erklärungsbedürftig:

**Die Hülle ist Petrol, das Rechteck ist Bernstein.** Die Marker-Hülle sagt „hier ist
gemessen, dort wird fortgeschrieben“ — eine Vertrauensaussage, also Identität, also
Petrol. Das Zuschnitt-Rechteck **ist** die Handlung der Seite: der Benutzer zieht
daran, und was darin liegt, wird gedruckt. Also Bernstein. Bisher stand in
`app/static/app.js` ein fest verdrahtetes `rgba(78, 201, 122, …)` — ein Grün, das zu
keiner Marke gehört und aus keinem Token stammt.

**Die Naht (`--crop-halo`).** `AGENTS.md`, Invariante 5, verlangt für das Raster im
PDF einen weißen Saum unter der dunklen Kernlinie, weil es auf hellem *und* dunklem
Untergrund lesbar sein muss. Dieselbe Physik gilt für jede Linie, die über ein Foto
läuft: eine einzelne Linie ist irgendwann genau so hell wie das, worüber sie liegt.
Das Paar aus hell und dunkel ist es nie. Hier ist der Kern hell (Bernstein), die Naht
also dunkel — die Umkehrung des PDF-Falls, nicht seine Wiederholung.

**Was auf dem Foto liegt, folgt dem Thema nicht.** `--crop-halo`, `--crop-dim`,
`--hull-*` sind in beiden Themen identisch definiert, und zwar an genau einer Stelle.
Der Grund steht in `free/src/main.css` beim Token `--curve-zone`: zwei Definitionen,
die sich heute zufällig gleichen, sind der Weg, auf dem sie eines Tages
auseinanderlaufen. Was unter diesen Farben liegt, ist das Foto des Benutzers, und das
ist in beiden Themen dasselbe.

### 3.6 Wo dieses Repo abweicht

Fünf Abweichungen von `free/src/main.css`. Alle fünf sind gemessen, nicht empfunden.

| Token | free | hier | Warum |
|---|---|---|---|
| `--background` hell | `#ffffff` | `#f0f3f3` | In free ist der Seitengrund ein Verlauf, der in `index.html` steht — außerhalb des Tokensystems; `--background` ist dort das Weiß der Karten. Hier gibt es keinen Verlauf und keinen zweiten Ort. Mit `#ffffff` wäre eine weiße Karte auf weißem Grund nur an ihrem Rand erkennbar, und der ist in free hell unsichtbar (nächste Zeile). |
| `--border` | hell `#ffffff`, dunkel `#25242b` | hell `#cbd5e1`, dunkel `#43424c` | Beide free-Werte sind exakt die Farbe ihres Hintergrunds, also unsichtbar; free trennt mit Schatten. Diese Oberfläche trennt mit Linien (Felder, Abschnitte, Tabellen). Hell ist `#cbd5e1` die einzige Kantenfarbe, die das Haus hat (`--cube-edge` in main.css), dunkel ist `#43424c` die Linienfarbe, die diese Oberfläche schon benutzt. |
| `--muted-foreground` | `#25242b` in **beiden** Themen | hell `#596474`, dunkel `#9ca3af` | Im dunklen Thema ist der free-Wert identisch mit `--background`: **1,00:1**, die Schrift ist schlicht weg. shadcn benutzt `--muted-foreground` freistehend (`placeholder:text-muted-foreground/50`, Symbole im Menü), nicht nur auf `--muted`. Hier stehen echte Grautöne auf dem Farbton von `--foreground`; der dunkle ist free-eigen (`.dark body` in `free/index.html`). |
| `--secondary`, `--muted` dunkel | bleiben auf `#e2e8f0` | `#36353c` | In free stimmig als *heller Chip mit dunkler Schrift*, kippt aber jedes Eingabefeld ins Helle, während die Seite dunkel bleibt. Für ein Werkzeug, das nachts in der Werkstatt bedient wird, ist das die falsche Blendung. |
| `--destructive-foreground` hell | `#e7000b` (= `--destructive`) | `#ffffff` | Schrift in Flächenfarbe. Erkennbar ein Versehen: die Knopfkomponente in free umgeht es mit fest verdrahtetem `text-white`. Hier steht das Weiß als Token, damit niemand es noch einmal verdrahtet — **4,77:1**. |

Zusätzlich: `--card` und `--popover` sind im dunklen Thema `#2d2c34` statt wie in free
gleich `--background`. free trennt Karten mit Schatten, was auf `#25242b` nicht
funktioniert — ein Schatten kann dort nichts abdunkeln, was nicht schon dunkel wäre.

### 3.7 Gegenprobe gegen `config.py`

`app/config.py` führt dieselben Farben für das PDF. Nachgerechnet (oklch → Oklab →
lineares sRGB → sRGB), alle acht stimmen exakt:

| `config.py` | Wert | Token in free |
|---|---|---|
| `BRAND_INK` | `#334155` | `--foreground` hell |
| `BRAND_PRIMARY` | `#379992` | `--primary` |
| `BRAND_ACTION` | `#ffbf00` | `--action` |
| `BRAND_DARK` | `#25242b` | `--background` dunkel / `--action-foreground` |
| `BRAND_LIGHT` | `#f1f5f9` | `--primary-foreground` |
| `BRAND_SECONDARY` | `#e2e8f0` | `--secondary` hell |
| `BRAND_ACCENT` | `#f0f3f3` | `--accent` hell |
| `BRAND_DESTRUCTIVE` | `#e7000b` | `--destructive` hell |

`config.py` bleibt die SSOT für das PDF, `tokens.css` für die Oberfläche. Wer eine
Markenfarbe ändert, ändert beide — und `free/src/main.css` zuerst, weil das Haus dort
steht.

### 3.8 Gemessener Kontrast

Alle Werte nach WCAG 2.1. Schwelle für Fließtext ist 4,5:1, für Bedienelemente und
große Schrift 3:1.

**Helles Thema**

| Paar | Verhältnis | |
|---|---|---|
| `--foreground` auf `--card` | 10,35:1 | ✔ |
| `--foreground` auf `--background` | 9,28:1 | ✔ |
| `--muted-foreground` auf `--card` | 6,00:1 | ✔ |
| `--muted-foreground` auf `--background` | 5,38:1 | ✔ |
| `--muted-foreground` auf `--muted` | 4,87:1 | ✔ |
| `--tone-good` auf `--card` | 5,72:1 | ✔ |
| `--tone-warn` auf `--card` | 5,77:1 | ✔ |
| `--tone-bad` auf `--card` | 5,61:1 | ✔ |
| `--action-foreground` auf `--action` | 9,30:1 | ✔ |
| `--destructive-foreground` auf `--destructive` | 4,77:1 | ✔ |
| `--secondary-foreground` auf `--secondary` | 12,47:1 | ✔ |
| `--primary` als Fließtext auf `--card` | 3,42:1 | ✘ nur als Fläche/Linie |
| `--primary-foreground` auf `--primary` | 3,13:1 | ✘ siehe §3.3 |

**Dunkles Thema**

| Paar | Verhältnis | |
|---|---|---|
| `--foreground` auf `--background` | 14,03:1 | ✔ |
| `--foreground` auf `--card` | 12,60:1 | ✔ |
| `--muted-foreground` auf `--background` | 6,06:1 | ✔ |
| `--muted-foreground` auf `--card` | 5,44:1 | ✔ |
| `--muted-foreground` auf `--muted` | 4,78:1 | ✔ |
| `--tone-good` auf `--card` | 5,87:1 | ✔ |
| `--tone-warn` auf `--card` | 8,35:1 | ✔ |
| `--tone-bad` auf `--card` | 5,16:1 | ✔ |
| `--destructive-foreground` auf `--destructive` | 9,15:1 | ✔ |

Warum die Berichtstöne nicht einfach `--primary`, `--action` und `--destructive` sind,
zeigt dieselbe Rechnung auf `--card` hell: **3,42:1 / 1,65:1 / 4,77:1**. Zwei davon
sind unlesbar. Die Töne sind deren abgedunkelte Geschwister — gleicher Farbton,
gleiche Buntheit, andere Helligkeit; der einzige Freiheitsgrad, den oklch dafür
vorsieht.

„Gut“ ist bewusst Petrol und nicht Grün: Grün gegen Rot ist bei der häufigsten
Farbsehschwäche kein Unterschied, Petrol gegen Rot dagegen schon — und Petrol ist
ohnehin die Farbe, die dieses Haus für „in Ordnung“ benutzt.

---

## 4 Typografie

### 4.1 Die Schrift

**Montserrat**, variabel, als eine woff2-Datei mit Gewichtsbereich 100–900.
In free: `free/src/assets/fonts/Montserrat/Montserrat-VariableFont_wght.woff2`
(plus ein kursiver Schnitt, den dieses Repo nicht mitführt). Deklariert am Ende von
`free/src/main.css`:

```css
@font-face {
    font-family: 'Montserrat';
    src: url('…/Montserrat-VariableFont_wght.woff2') format('woff2');
    font-weight: 100 900;
    font-style: normal;
    font-display: swap;
}
```

`format('woff2')` zusammen mit dem Bereich `100 900` ist die richtige Schreibweise.
`format('woff2-variations')` ist eine Sackgasse aus der Anfangszeit variabler
Schriften: Browser, die den String nicht kennen, verwerfen die ganze `@font-face`-Regel
und fallen wortlos auf die Ersatzschrift zurück. (Dieses Repo hatte genau das in
`app/static/style.css` stehen.)

`font-display: swap` heißt: erst die Ersatzschrift, dann tauschen. Für eine Oberfläche
richtig — Text, den man nicht lesen kann, ist schlimmer als Text im falschen Schnitt.
Der Nebeneffekt ist ein Umbruch beim Tausch; free hat das an einer Stelle gemerkt, wo
eine Textur zur falschen Zeit gebacken wurde (`free/src/lib/three/objects/OrientationCube.ts`
und `faceLabelTexture.ts`, das die Schrift erst per `document.fonts.load()` anfordert).

Schriftstapel für dieses Repo:

```
"Montserrat", "Segoe UI", system-ui, -apple-system, sans-serif
```

`"Segoe UI"` steht vor `system-ui`, weil die Werkstattrechner Windows sind und
`system-ui` dort auf denselben Schnitt zeigt — aber erst nach einer Auflösung, die
ältere Browser nicht können.

**In free ist Montserrat opt-in**, nicht die Grundschrift: `main.css` legt in
`@layer utilities` eine Klasse `.font-montserrat` an, und nur wer sie setzt, bekommt
sie. In diesem Repo ist Montserrat die Schrift des `body`. Das ist eine bewusste
Abweichung und die richtige: eine Oberfläche mit einem einzigen Textstil braucht
keinen Schalter.

### 4.2 Gewichte

Gezählt über alle `.vue`-Dateien in `free/src`:

| Gewicht | Vorkommen | Wofür |
|---|---|---|
| `600` semibold | 21× | Überschriften, Werte, alles Betonte |
| `500` medium | 16× | Beschriftungen, Knopftext |
| `400` normal | 5× | Fließtext (der Standard, deshalb selten geschrieben) |
| `700` bold | 1× | die Wortmarke |
| `800` extrabold | 1× | ein Sonderfall |

Vier Gewichte, mehr braucht es nicht. Als `font-weight` notieren, nicht als
`font-variation-settings`: bei einer variablen Schrift mit deklariertem Bereich tut
`font-weight` dasselbe, wird aber von fetten Ersatzschriften und von der Suchfunktion
des Browsers richtig verstanden.

### 4.3 Größen

Gezählt in derselben Menge:

| Token | Wert | Vorkommen |
|---|---|---|
| `--text-sm` | `0.875rem` | 49× — die Arbeitsgröße |
| `--text-xs` | `0.75rem` | 25× — Hinweise, Beschriftungen, Marken |
| `--text-lg` | `1.125rem` | 2× |
| `--text-base` | `1rem` | 2× |
| `--text-2xl` | `1.5rem` | 1× |

Die Oberfläche ist **klein gesetzt**. `text-sm` ist der Normalfall, nicht `text-base`.
Eine Stufe, die niemand benutzt, ist eine Einladung, sie zu benutzen — deshalb führt
`tokens.css` nur diese fünf.

Zeilenhöhe: `1.55` für Fließtext, `1.25` für Überschriften.

### 4.4 Die Markenzeile

Die Wortmarke wird **versalisiert, gesperrt und halbfett** gesetzt.
`free/src/components/layouts/ConfiguratorDesktop.vue:74`:

```html
<div class="font-montserrat dark:text-shadow-lg text-lg uppercase font-bold …">
```

Versalien brauchen Luft — ohne Sperrung klebt Montserrat in Großbuchstaben zusammen.
Zwei Dosierungen:

- `--tracking-brand: 0.08em` für die Markenzeile
- `--tracking-wide: 0.05em` für kleine Großbuchstaben-Beschriftungen
  (die Feldnamen im Qualitätsbericht)

free benutzt für den Sprachcode im Umschalter dasselbe Muster
(`LocaleSwitch.vue:44`, `class="uppercase"`) und `tracking-widest` für
Tastenkürzel (`DropdownMenuShortcut.vue:13`).

`dark:text-shadow-lg` in der Zeile oben ist bemerkenswert: die Wortmarke bekommt im
dunklen Thema einen Schatten, damit sie sich vom Bild dahinter löst. In diesem Repo
steht die Markenzeile auf einer ruhigen Fläche und braucht das nicht.

### 4.5 Eine gemessene Erkenntnis über hell und dunkel

`free/src/main.css` führt `--dimension-text-weight-adjust: -0.0125` (hell) und `0`
(dunkel), mit dieser Begründung: beide Themen zeichnen dieselbe Glyphenmaske, und
**dunkel-auf-hell liest sich schwerer** — im hellen Thema wurden 12 % mehr massive
Strichfläche gemessen als im dunklen. Ausgeglichen wird nach unten, hell wird
ausgedünnt, dunkel bleibt die Referenz.

Für eine reine HTML-Oberfläche ist das kein Token, aber es ist die Erklärung für ein
Gefühl, das sonst zu falschen Schlüssen führt: **wenn das helle Thema „fetter“ wirkt
als das dunkle, liegt es nicht am Gewicht.** Nicht nachjustieren.

---

## 5 Form und Raum

### 5.1 Radien

`free/src/main.css` führt einen Grundwert und rechnet vier Stufen daraus
(`@theme inline`):

| Token | Rechnung | Wert | Wofür |
|---|---|---|---|
| `--radius` | — | `0.625rem` = 10px | der Grundwert |
| `--radius-sm` | `r - 4px` | 6px | Menüeintrag, Marke, Kleinteiliges |
| `--radius-md` | `r - 2px` | 8px | Knopf, Feld, Auswahl, Hinweisblase |
| `--radius-lg` | `r` | 10px | Abschnitt, größere Fläche |
| `--radius-xl` | `r + 4px` | 14px | Karte |
| `--radius-full` | — | `9999px` | runder Symbolknopf |

Belegt an den Komponenten: Card `rounded-xl`, Button/Input/SelectTrigger/Tooltip/
DropdownMenuContent `rounded-md`, DropdownMenuItem `rounded-sm`, Button `size="icon"`
`rounded-full`.

Fünf Stufen. Ein sechster Radius sagt nichts, was diese fünf nicht schon sagen.

### 5.2 Rhythmus

free rechnet in Tailwinds Skala, also in Vielfachen von `0.25rem`. Was tatsächlich
vorkommt:

| Wert | Wo |
|---|---|
| `0.25rem` | Innenabstand eines Menüs (`p-1`) |
| `0.375rem` | Abstand im Kartenkopf (`gap-1.5`), Höhe des Menüeintrags (`py-1.5`) |
| `0.5rem` | Abstand zwischen Symbol und Text (`gap-2`), `px-2` im Menüeintrag |
| `0.75rem` | `px-3` in Knopf, Feld, Auswahl, Hinweisblase |
| `1rem` | `px-4` im Standardknopf |
| `1.5rem` | `px-6`/`py-6`/`gap-6` in der Karte |

Merkregel: **innen 0,375–0,75rem, außen 1,5rem.** Karten sind großzügig, ihr Inhalt
ist dicht.

### 5.3 Linien und Erhebung

free trennt vorwiegend mit **Schatten**, nicht mit Linien — deshalb steht `--border`
dort auf der Hintergrundfarbe (siehe §3.6). Die Schattenstufen sind Tailwinds
Vorgaben:

| Token | Wert (helles Thema) | Wo in free |
|---|---|---|
| `--shadow-xs` | `0 1px 2px 0 rgba(0,0,0,.05)` | Knopf, Feld, SelectTrigger |
| `--shadow-sm` | `0 1px 3px 0 rgba(0,0,0,.1), 0 1px 2px -1px rgba(0,0,0,.1)` | Karte, Hinweisblase, schwebender Knopf |
| `--shadow-md` | `0 4px 6px -1px rgba(0,0,0,.1), 0 2px 4px -2px rgba(0,0,0,.1)` | aufklappendes Menü |

Im dunklen Thema werden sie in `tokens.css` kräftiger nachgezogen (0,30 / 0,45 / 0,50):
ein Schatten aus 10 % Schwarz ist auf `#25242b` nicht vorhanden.

Für dieses Repo gilt: **Linie zuerst, Schatten als Zugabe.** Formularfelder,
Abschnitte und Tabellen brauchen eine sichtbare Kante, und eine Werkstattbeleuchtung
frisst feine Schatten.

---

## 6 Komponenten

Alle Angaben aus `free/src/components/shadcn/ui/*`. Die Klassennamen sind Tailwind
und lassen sich nicht übernehmen — die **Maße** schon.

### 6.1 Knopf

`free/src/components/shadcn/ui/button/index.ts`

Gemeinsame Grundlage aller Varianten:

```
inline-flex items-center justify-center gap-2   Symbol und Text mit 0.5rem Abstand
rounded-md   text-sm   font-medium              8px, 0.875rem, Gewicht 500
transition-all                                  jeder Zustandswechsel wird geblendet
disabled:pointer-events-none disabled:opacity-50
outline-none
focus-visible:border-ring
focus-visible:ring-ring/50 focus-visible:ring-[3px]
aria-invalid:border-destructive
[&_svg:not([class*='size-'])]:size-4            Symbole 1rem, wenn nicht anders gesagt
```

Größen:

| Größe | Höhe | Innenabstand |
|---|---|---|
| `sm` | `2rem` (h-8) | `px-3`, `gap-1.5` |
| `default` | `2.25rem` (h-9) | `px-4 py-2` |
| `lg` | `2.5rem` (h-10) | `px-6` |
| `icon-sm` / `icon` / `icon-lg` | `2rem` / `2.25rem` / `2.5rem` quadratisch | `rounded-full` |

Varianten und was sie bedeuten:

| Variante | Fläche | Wann |
|---|---|---|
| `default` | `--accent`, Rahmen `--foreground/10` | der normale Knopf |
| `primary` | `--primary` | Marke/Bestätigung |
| `action` | `--action` | die **eine** Handlung der Ansicht |
| `secondary` | `--secondary` | nachgeordnet |
| `outline` | `--background` + Rahmen | nachgeordnet, leiser |
| `ghost` | nichts, erst beim Hover `--background` + Schatten | Symbolknöpfe in Leisten |
| `floating` | `--background` + `shadow-sm` | über Inhalt schwebend |
| `destructive` | `--destructive`, Text weiß | löschen, abbrechen |
| `link` | nur Text `--primary`, unterstrichen beim Hover | Verweis im Fließtext |

Hover ist durchgängig **dieselbe Farbe mit weniger Deckkraft** (`hover:bg-primary/90`,
`hover:bg-accent/70`) — nicht eine zweite Farbe. In reinem CSS ohne `color-mix()`
erreicht man das über eine zweite Helligkeitsstufe desselben Farbtons (so machen es
`--bfsb-petrol-deep` / `-bright` und `--bfsb-amber-press` in `tokens.css`).

Deaktiviert ist immer `opacity: .5` plus `pointer-events: none` — nie eine graue
Sonderfarbe.

### 6.2 Eingabefeld

`free/src/components/shadcn/ui/input/Input.vue`

```
h-9 w-full min-w-0 rounded-md border px-3 py-1     2.25rem hoch, 8px Radius
bg-muted text-muted-foreground                     gefüllt, nicht durchsichtig
shadow-xs   transition-[color,box-shadow]
placeholder:text-muted-foreground/50               Platzhalter halb so laut
selection:bg-primary selection:text-primary-foreground
focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]
aria-invalid:border-destructive
disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none
```

Bemerkenswert: das Feld benutzt **`bg-muted`, nicht `bg-input`**. In shadcn ist
`--input` streng genommen die Rahmenfarbe. Deshalb setzt `tokens.css` `--input` auf
den Wert, den free tatsächlich malt (`--muted`), und lässt es Rahmen *und* Fläche
tragen — die Felder dieser Oberfläche sind gefüllt.

### 6.3 Auswahl

`free/src/components/shadcn/ui/select/SelectTrigger.vue`

Wie das Eingabefeld, aber `bg-accent hover:bg-accent/70`, Rahmen `--foreground/10`,
`px-3 py-2`, `w-fit` statt `w-full`, `data-[size=sm]:h-8`. Der Pfeil ist
`ChevronDown` in `size-4 opacity-50`. Der Platzhalterzustand färbt auf
`--muted-foreground`.

### 6.4 Karte

`free/src/components/shadcn/ui/card/`

| Teil | Maße |
|---|---|
| `Card` | `rounded-xl border py-6 shadow-sm`, `flex flex-col gap-6`, `bg-card text-card-foreground` |
| `CardHeader` | `px-6 gap-1.5`, Raster `[auto_auto]`, mit Aktion `[1fr_auto]` |
| `CardContent` | `px-6` |

Der senkrechte Abstand sitzt **an der Karte** (`py-6` plus `gap-6`), der waagerechte
**an den Teilen** (`px-6`). So kann ein Teil ganze Breite einnehmen — ein Bild, eine
Trennlinie —, ohne aus dem Rhythmus zu fallen. Für die Abschnitte dieser Anwendung
(`<section>`) ist das das Vorbild.

### 6.5 Hinweisblase

`free/src/components/shadcn/ui/tooltip/TooltipContent.vue`

```
bg-background text-foreground shadow-sm
rounded-md px-3 py-1.5 text-xs w-fit text-balance
z-50   sideOffset 4
```

Der Pfeil ist ein gedrehtes Quadrat: `size-2.5 rotate-45 rounded-[2px]`,
`translate-y-[calc(-50%_-_2px)]`.

Blende: `fade-in-0 zoom-in-95` beim Öffnen, `fade-out-0 zoom-out-95` beim Schließen,
plus `slide-in-from-*-2` je nach Seite — also 2 Einheiten (0,5rem) aus der Richtung,
aus der sie kommt. **Bewegung erklärt Herkunft.**

Auffällig: die Blase steht auf `--background`, nicht auf `--popover`. Das ist in free
gewollt (sie soll leichter wirken als ein Menü), aber es macht sie im hellen Thema von
der Karte darunter ununterscheidbar, sobald `--background` und `--card` beide weiß
sind — noch ein Grund für die Trennung in §3.6.

### 6.6 Aufklappendes Menü

`free/src/components/shadcn/ui/dropdown-menu/`

| Teil | Maße |
|---|---|
| `Content` | `bg-popover text-popover-foreground rounded-md border p-1 shadow-md`, `min-w-[8rem]`, `z-50`, `sideOffset 4`, Höhe begrenzt auf den verfügbaren Platz, senkrecht scrollbar |
| `Item` | `rounded-sm px-2 py-1.5 text-sm gap-2`, Fokus `bg-accent text-accent-foreground`, deaktiviert `opacity-50 pointer-events-none`, Symbole `size-4` in `--muted-foreground` |
| `Shortcut` | `tracking-widest`, gedämpft, rechtsbündig |

Der Eintrag hat **keinen** Hover, sondern einen **Fokus**-Zustand (`focus:bg-accent`).
Das ist der Unterschied zwischen Maus und Tastatur, und beide sollen dasselbe sehen.

Die Auswahl der aktuellen Sprache wird in `LocaleSwitch.vue` mit derselben Farbe
markiert: `:class="{ 'bg-accent': app.locale === lang.code }"`.

### 6.7 Fokus — die eine Regel, die überall gleich ist

```
focus-visible:border-ring
focus-visible:ring-ring/50
focus-visible:ring-[3px]
```

Ein **3px** breiter Ring in `--ring` (= `--primary`) mit halber Deckkraft, plus der
Rahmen in voller. Auf `:focus-visible`, nicht auf `:focus` — der Mausklick soll keinen
Ring hinterlassen, die Tabulatortaste schon.

In reinem CSS:

```css
:focus-visible {
    outline: none;
    border-color: var(--ring);
    box-shadow: 0 0 0 3px var(--ring-soft);
}
```

`--ring-soft` ist Petrol bei 50 % und existiert nur, weil `ring-ring/50` reine
Tailwind-Syntax ist: die Schrägstrich-Deckkraft lässt sich ohne `color-mix()` — das
genauso jung ist wie `oklch()` — nicht nachbauen. Lieber ein Token als eine fest
verdrahtete Zahl im Stylesheet.

Das ist der einzige Zustand, den **jedes** bedienbare Element dieser Oberfläche
zeigen muss. Ein Werkzeug, das man mit der Tastatur nicht durchlaufen kann, ist auf
einem Werkstattrechner ohne Maus nicht bedienbar.

---

## 7 Themenwechsel

### 7.1 Wie free es macht

Drei Teile:

**1. Die Klasse.** `.dark` am `<html>`. In `main.css` als Tailwind-Variante
registriert: `@custom-variant dark (&:is(.dark *))`. Der Themenblock ist ein
gewöhnlicher Selektor `.dark { … }`, der dieselben Tokens neu belegt.

**2. Das Skript vor dem Bundle.** `free/index.html` enthält ein synchrones Skript im
`<head>`:

```js
let colorMode = localStorage.getItem('vueuse-color-scheme');
if (!colorMode) {
    colorMode = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
if (colorMode === 'dark') document.documentElement.classList.add('dark');
```

Es läuft **bevor** irgendetwas gezeichnet wird. Ohne das blitzt die Seite hell auf und
kippt erst mit dem Bundle ins Dunkle. Der Speicherschlüssel `vueuse-color-scheme` wird
von VueUse vorgegeben, nicht selbst gewählt.

**3. Der Speicher.** `free/src/stores/app/store.ts` hält `useColorMode()` von VueUse
und bietet `isLightMode`, `isDarkMode`, `setColorMode(mode)` und `toggleColorMode()`.
`free/src/components/utilities/ColorModeSwitch.vue` ist ein `ghost`-Symbolknopf mit
Sonne/Mond und einer Hinweisblase, deren Text sich mit dem Zustand ändert.

**4. Für alle, die `var()` nicht können.** `free/src/utils/cssThemeVar.ts`:

```ts
export function readCssThemeVar(name: string, fallback: string): string {
    if (typeof window === 'undefined' || typeof document === 'undefined') return fallback;
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
}
```

Ein Canvas- oder WebGL-Kontext löst `var(--x)` nicht auf; er will einen fertigen
Farbwert. Die Datei ist die eine gemeinsame Lesestelle dafür — ihr Kommentar hält
fest, dass genau diese Funktion vorher **dreimal** kopiert existierte.

**Und die Falle dazu**, dokumentiert in `main.css` bei `--curve-label`: paper.js kann
in `fillStyle` keine Farbfunktion mit Alpha auflösen (`oklch()`, `color-mix()`) — sein
`fromCSS` fällt auf einen Canvas-Rückleseweg zurück, der nur das RGB-Tripel liefert und
**die Deckkraft verschluckt**. Das Token wurde deshalb undurchsichtig gemacht und die
Transparenz von beiden Zeichnern getrennt angewandt. Wer hier `--hull-fill` per
`readCssThemeVar` in ein Canvas gibt: der 2D-Kontext des Browsers kann `rgba()` und
`oklch(… / α)`, das ist unproblematisch — aber jede Bibliothek dazwischen ist zu prüfen.

### 7.2 Was dieses Repo stattdessen tut

Kein Build-Schritt, also keine `@custom-variant`, kein `dark:`-Präfix. Stattdessen
drei Zustände in reinem CSS, alle drei in `app/static/css/tokens.css`:

```css
:root                      { /* hell — der Ausgangszustand */ }

@media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) { /* dunkel nach Systemvorgabe */ }
}

:root[data-theme="dark"]   { /* dunkel, ausdrücklich gewählt */ }
:root[data-theme="light"]  { color-scheme: light; }
```

Drei Dinge daran sind wichtig und leicht falsch zu machen:

- **Das `:not([data-theme="light"])`.** Ohne das könnte ein Benutzer auf einem dunkel
  eingestellten Telefon nicht mehr auf Hell schalten — die Systemvorgabe würde seine
  Wahl überschreiben.
- **Die Reihenfolge.** `:root[data-theme="dark"]` hat dieselbe Spezifität (0,2,0) wie
  der Selektor im `@media`-Block. Bei Gleichstand entscheidet die Quellreihenfolge,
  also muss die ausdrückliche Wahl **hinter** dem `@media`-Block stehen.
- **`color-scheme`.** `:root { color-scheme: light dark }` sagt dem Browser, dass wir
  beides können, und lässt ihn seine eigenen Teile — Bildlaufleisten, Auswahl,
  eingebaute Formularelemente — nach der Systemeinstellung färben. Die beiden
  `[data-theme]`-Blöcke nageln es fest, sobald der Benutzer selbst gewählt hat. Ohne
  das steht eine helle Oberfläche mit dunklen Bildlaufleisten da.

Der Vorspann in `index.html` ist entsprechend kürzer als der von free: es genügt,
einen gespeicherten Wert auf `document.documentElement.dataset.theme` zu setzen. Ist
nichts gespeichert, macht der `@media`-Block ohne jedes Skript das Richtige — das ist
der Vorteil dieser Bauform gegenüber der Klassenlösung.

### 7.3 Die oklch-Falle

Beide Notationen stehen in `tokens.css`, und zwar so:

```css
:root { --bfsb-petrol: #379992; }

@supports (color: oklch(0 0 0)) {
    :root { --bfsb-petrol: oklch(0.6245 0.0905 188.44); }
}
```

**Nicht** so:

```css
:root {
    --bfsb-petrol: #379992;
    --bfsb-petrol: oklch(0.6245 0.0905 188.44);   /* Falle */
}
```

Bei gewöhnlichen Eigenschaften ist die zweite Form das übliche CSS-Muster: der Browser
verwirft, was er nicht parsen kann, und behält den Wert davor. Bei **Custom Properties
gilt das nicht.** Ihr Wert wird beim Parsen nicht geprüft — jede Tokenfolge ist gültig
—, also gewinnt immer die zweite Zeile. Erst bei `color: var(--bfsb-petrol)` merkt der
Browser, dass er `oklch()` nicht lesen kann, und dann ist es zu spät: die Eigenschaft
ist *invalid at computed-value time* und fällt auf `unset` zurück. Ergebnis wäre
geerbte oder Ausgangsfarbe — schlimmer als gar kein Fallback, weil es aussieht wie ein
Fehler im Stylesheet.

`@supports` prüft vor der Zuweisung und ist deshalb die einzige Form, die trägt.

Warum überhaupt zwei Notationen? `oklch()` kann erst Chrome 111, Firefox 113 und
Safari 15.4. **Dieses Werkzeug wird auf Handys in einer Werkstatt bedient**, und ein
Telefon von 2022 mit altem Systembrowser ist dort ein realistischer Fall. Der Gewinn
der oklch-Ebene ist klein, aber echt: die Hex-Werte sind exakte sRGB-Umrechnungen, und
nur wo der oklch-Wert außerhalb von sRGB liegt (Bernstein, Rot), ist die
oklch-Fassung auf einem P3-Bildschirm etwas satter. Der eigentliche Grund, sie zu
führen, ist ein anderer: **`tokens.css` bleibt gegen `free/src/main.css` diffbar.**

---

## 8 Mehrsprachigkeit

free führt zwei Sprachen, Deutsch und Englisch, als JSON-Bäume in
`free/src/i18n/locales/`. Das Muster ist übertragbar, auch ohne vue-i18n.

### 8.1 Die Konstanten

`free/src/i18n/constants.ts` — bewusst eine abhängigkeitsfreie Blattdatei, weil
`vite.config.ts` sie zur Bauzeit in Node importiert:

| Konstante | Wert | Bedeutung |
|---|---|---|
| `storageKey` | `'free-language'` | localStorage-Schlüssel für die **ausdrücklich gewählte** Sprache |
| `fallbackLocale` | `'en'` | wenn weder Speicher noch Browser eine unterstützte Sprache anbieten |
| `documentTitleKey` | `'document.title'` | Pfad zum Seitentitel im Nachrichtenbaum |

### 8.2 Die Auflösung

`free/src/i18n/index.ts`, `getInitialLocale()` — drei Stufen in dieser Reihenfolge:

1. `localStorage.getItem(storageKey)`, falls unterstützt
2. `navigator.language.split('-')[0].toLowerCase()`, falls unterstützt
   (aus `de-CH` wird `de`)
3. `fallbackLocale`

Die gewählte Sprache wird bei jedem Wechsel zurückgeschrieben
(`free/src/composeables/useI18n.ts`, `setLocale`).

Für dieses Repo: **Deutsch ist die Ausgangssprache**, nicht Englisch — die Oberfläche
ist deutsch (`AGENTS.md`, Konventionen), und der Benutzer steht in einer Werkstatt in
der Schweiz.

### 8.3 `<html lang>` — der Fehler, der zweimal weh tat

`free/src/i18n/documentLanguage.ts` ist die **einzige** Stelle, die `lang` schreibt.
Der Kommentar hält den Vorfall fest (SNOW-282): `index.html` kann nur die Bauzeit-
Vorgabe deklarieren, weil die echte Sprache von localStorage und `navigator.language`
abhängt. Blieb sie stehen,

- bot Chrome an, die bereits deutsche Oberfläche aus dem Englischen ins Deutsche zu
  übersetzen, und
- lasen Screenreader deutschen Text mit englischer Stimme vor.

`index.ts` ruft `syncDocumentToLocale()` einmal beim Laden und danach in einem
`watch(…, { flush: 'sync' })` — synchron, nicht im üblichen Vorlauf, weil ein
veraltetes `lang` genau der Fehler ist, den das behebt. Kosten: ein Attributschreiben
bei einer seltenen Benutzeraktion.

Für dieses Repo ist das eine Zeile: beim Sprachwechsel
`document.documentElement.lang` mitschreiben.

### 8.4 Die `|`-Falle — bitte übernehmen

Aus `free/src/i18n/index.ts`, Funktion `resolveDocumentTitle`:

> **vue-i18n liest `|` als Trenner der Pluralformen.** Aus
> `"Bischof Snowboards | Konfigurator"` kommt über `t()` nur
> `"Bischof Snowboards"` zurück — die erste Pluralform —, und der Seitentitel
> verliert stillschweigend seine Hälfte, sobald das Bundle geladen ist.

free umgeht es, indem der Titel **roh** aus dem Nachrichtenbaum gelesen wird statt
über `t()`.

Die Regel, die daraus folgt und für jedes Werkzeug dieses Hauses gilt:
**kein nacktes `|` in einem übersetzbaren Text.** Wer einen senkrechten Strich als
Trenner im Titel will, nimmt einen Halbgeviertstrich (`–`) oder setzt ihn außerhalb
der Übersetzung zusammen. Der Fehler ist besonders tückisch, weil er nicht knallt —
er kürzt.

### 8.5 `td()` — Übersetzen mit Vorgabe

`free/src/composeables/useI18n.ts` bietet neben `t()` ein `td(key, defaultText)`: wenn
`t()` den Schlüssel unverändert zurückgibt, fehlt die Übersetzung, und `td()` liefert
den Vorgabetext. Nützlich für Texte, die aus Daten kommen und nur manchmal übersetzt
sind. Ein kleines Muster, das viel `key.not.found` in der Oberfläche verhindert.

---

## 9 Bewegung und Zugänglichkeit

### 9.1 Blenden

free blendet mit Tailwinds Vorgaben: `transition-all` an Knöpfen,
`transition-[color,box-shadow]` an Feldern — also **150ms**, `ease`. Auftritte von
Menü und Blase: `fade-in-0 zoom-in-95` plus `slide-in-from-*-2`.

`tokens.css` führt dafür `--duration-fast: 150ms` (alles, was am Zeiger hängt),
`--duration-slow: 300ms` (alles, was erscheint oder verschwindet) und
`--ease-out: cubic-bezier(0, 0, 0.2, 1)`.

Die Regel dahinter: **eine Blende erklärt Herkunft.** Ein Menü, das aus der Richtung
seines Auslösers hereinschiebt, sagt, wozu es gehört. Eine Blende ohne Richtung ist
Dekoration.

### 9.2 Der Erinnerungspuls

`free/src/main.css`:

```css
@keyframes reminder-pulse {
    0%   { box-shadow: 0 0 0 0   var(--primary); }
    70%  { box-shadow: 0 0 0 8px transparent; }
    100% { box-shadow: 0 0 0 0   transparent; }
}
.reminder-pulse { border-radius: var(--radius); animation: reminder-pulse 0.9s ease-out 2; }
```

Ein Ring, der zweimal aufgeht und verblasst. Zweimal, nicht endlos — eine Dauerschleife
wird zum Hintergrundrauschen und hört auf zu erinnern.

Der Kommentar dazu ist eine Lektion für sich: die relative Farbschreibweise
`oklch(from var(--primary) l c h / a)` wird **absichtlich vermieden**, weil sie
Safari 16.4+/Chrome 119+ braucht. Auf einem älteren Handy, das den Rest des
oklch-Themas anstandslos zeichnet, gäbe es dann gar keinen Ring — und es ist eine
Handyfunktion. Stattdessen wird das Token direkt nach `transparent` animiert, was
jeder oklch-fähige Browser nativ interpoliert.

**Diese Denkweise ist das eigentlich Übertragbare:** die neue Schreibweise nicht
deshalb nehmen, weil sie eleganter ist, sondern prüfen, wer sie auf dem *Zielgerät*
lesen kann.

### 9.3 Weniger Bewegung

```css
@media (prefers-reduced-motion: reduce) {
    .reminder-pulse { animation: none; outline: 2px solid var(--primary); outline-offset: 2px; }
}
```

Der Puls wird nicht **weggelassen**, sondern **ersetzt**: aus der Animation wird ein
ruhender Rahmen. Die Aussage bleibt, die Bewegung geht.

`tokens.css` macht dasselbe eine Ebene tiefer und setzt unter
`prefers-reduced-motion: reduce` die Dauern auf `0ms`. Damit gilt es für jede Regel,
die die Tokens benutzt, statt in jeder einzeln wiederholt zu werden. Zustände bleiben
erhalten — eine Blende von 0ms ist ein Sprung, kein fehlender Zustand.

### 9.4 Bildlaufleisten

`free/src/main.css`, `@layer base`:

```css
* { scrollbar-width: thin; scrollbar-color: var(--border) transparent; }
*::-webkit-scrollbar        { width: 6px; }
*::-webkit-scrollbar-track  { background: transparent; margin: 4px 0; }
*::-webkit-scrollbar-thumb  { background-color: var(--border); border-radius: 10px; }
*::-webkit-scrollbar-thumb:hover { background-color: var(--foreground); }
```

Beide Schreibweisen, weil die eine Firefox bedient und die andere den Rest. Der
Greifer ist `--border` und wird beim Hover zu `--foreground` — er folgt also dem Thema
und wird nicht mit einem festen Grau gemalt.

Dazu die Klasse `.no-native-scrollbar` mit einem Kommentar, der eine echte
Fehlerursache festhält: bei einem Panel, dessen **Inhaltshöhe aus seiner gemessenen
Breite folgt**, ist eine ein- und ausblendende Bildlaufleiste eine Rückkopplung — sie
erscheint, nimmt ~6px Breite, der Inhalt wird kürzer, der Überlauf verschwindet, die
Breite kommt zurück, der Inhalt wächst wieder in den Überlauf. Für immer. Wer hier ein
Element baut, dessen Höhe aus seiner Breite folgt: daran denken.

### 9.5 Sichtbarer Fokus

Siehe §6.7. Der Ring ist 3px breit, hat die Markenfarbe und sitzt auf
`:focus-visible`. Er ist nicht verhandelbar.

---

## 10 Mobil

Die Grenze ist im ganzen Haus **768px**: `useMediaQuery("(max-width: 768px)")` in
`free/src/stores/app/store.ts` (`app.isMobile`) und dieselbe Zahl in den Toast-Regeln
in `main.css`. Nicht 767, nicht 640 — 768.

### 10.1 Die gemessene Rampe

Der lehrreichste Block in `free/src/main.css`:

```css
--menubar-control: clamp(2rem, calc(23.5vw - 43.3px), 2.5rem);
--menubar-control-icon: calc(var(--menubar-control) * 0.6);
```

Das Problem: die mobile Menüleiste muss ihre Symbolknöpfe **und** den Preis auf **eine**
Zeile bringen. Feste 40px-Knöpfe brachen unter ~350px auf zwei und drei Zeilen um und
verdoppelten die Höhe der Leiste bei jeder Preisneuberechnung.

Beide Enden der Rampe sind **gemessen, nicht gewählt**:

- Bei voller Größe (2.5rem) hört die Leiste bei **347px** (üblicher Preis) bzw.
  **354px** (fünfstellig) auf zu passen — darüber darf nichts schrumpfen.
- Der Boden ist **2rem**, weil das bei 320px einen fünfstelligen Preis ungeschnitten
  lässt (und ein freundlicheres Ziel ist als die 1.75rem davor).

```
slope  = (2.5rem − 2rem) / (354px − 320px) = 0.235  → 23.5vw
offset = 2rem − 0.235 · 320px              = −43.3px
```

Der erste Versuch — ein glattes `9.3vw`, das erst bei 430px die volle Größe erreichte —
schrumpfte die Leiste schon bei 360px sichtbar, während zwischen Preis und letztem
Symbol noch ~13px Luft standen.

Drei übertragbare Punkte:

1. **Neu kalibrieren, wenn ein Knopf dazukommt oder wegfällt.** Die Schwelle wandert
   um rund 5px Bildschirmbreite je 1px Knopfgröße; ein fünfter Knopf schiebt sie auf
   ~395px.
2. **`vw` statt Container-Query, wenn die Leiste tatsächlich den Bildschirm füllt.**
   Hier ist die Bildschirmbreite die Containerbreite.
3. **Abgeleitet statt zweitem `clamp`.** Das Symbol ist `0.6 × Knopf`, weil das genau
   das Verhältnis 24/40 des festen Paares davor war. Zwei `clamp`s könnten
   auseinanderlaufen, eine Multiplikation nicht.

Und einer, der genauso wichtig ist: **Abstände und Innenabstand liegen bewusst
*nicht* auf der Rampe.** Sie zu schrumpfen brachte ein paar Pixel und kostete die
Leiste ihre Proportionen.

Dieses Repo hat keine solche Leiste. Es hat `--touch-target: 2.75rem` (44px) — Apples
Untergrenze und die kleinste Größe, die mit Arbeitshandschuhen zuverlässig trifft.
Weil hier nichts auf eine Zeile passen muss, darf die Untergrenze großzügiger sein als
free's 2rem.

### 10.2 Kompakte Meldungen

`free/src/main.css`, unter `@media (max-width: 768px)` (SNOW-394): Meldungen stiegen
von oben ein und deckten den Arbeitsbereich zu, und sie waren größer gesetzt als die
Bedienelemente der App. Korrigiert auf:

| | Standard | mobil |
|---|---|---|
| Innenabstand | 16px | `0.5rem 0.625rem` |
| Abstand | — | `0.375rem` |
| Text | 13px | `0.75rem` |
| Symbol | — | `0.875rem` |
| Beschreibung | — | `0.6875rem` |

Und die Breite: `width: fit-content`, gedeckelt auf
`min(356px, calc(100vw − 2rem))`. Eine kurze Meldung ist eine kurze Meldung, kein
Kasten mit Leerraum.

Der Grundsatz dahinter: **eine Meldung muss aussehen wie ein Teil der Oberfläche, nicht
wie eine Einblendung darüber.** Ihre Textgröße ist die der mobilen Bedienelemente
(`0.75rem`).

Ergänzend gibt es dort ein Muster, das man kennen sollte, ohne es zu brauchen: die
Meldung endet einen Knopfabstand vor der Steuerungsspalte in der gegenüberliegenden
Ecke, gerechnet aus `--scene-controls-side` und `--scene-controls-width`, die die
Steuerungskomponente selbst ins `:root` schreibt
(`free/src/components/utilities/SceneControls.vue`). **Ein Bauteil veröffentlicht seine
gemessene Größe als Token, damit ein anderes sich daran ausrichten kann, ohne es zu
kennen.** Beide Tokens haben Fallbacks, weil die Steuerung nicht immer montiert ist.

---

## 11 Was nicht zu übernehmen ist

free ist eine Vue/Tailwind/shadcn-SPA mit Build-Schritt. Dieses Repo hat statische
Dateien hinter FastAPI — **kein Build, kein Tailwind, kein Framework.** Die folgende
Tabelle ist die Grenze.

| Aus free | Trägt hier? | Was stattdessen |
|---|---|---|
| die oklch-Werte | **ja** | wörtlich, plus Hex-Basis (§7.3) |
| die Tokennamen | **ja** | identisch — genau das macht die zwei Werkzeuge zu einem Haus |
| Radienskala, Maße, Innenabstände | **ja** | als eigene Tokens ausrechnen |
| das Paar-Prinzip `--x` / `--x-foreground` | **ja** | reine Konvention, braucht kein Werkzeug |
| Fokusring, Hover-, Deaktiviert-Muster | **ja** | als gewöhnliche CSS-Regeln |
| Scrollbar-Regeln | **ja** | 1:1, ist reines CSS |
| `@keyframes reminder-pulse` + reduced motion | **ja** | 1:1 |
| `readCssThemeVar` | **ja, sinngemäß** | drei Zeilen `getComputedStyle`, für das Overlay-Canvas |
| `@import "tailwindcss"` | **nein** | — |
| `@theme inline { … }` | **nein** | Tokens direkt in `:root`, Radien mit `calc()` |
| `@custom-variant dark (&:is(.dark *))` | **nein** | `[data-theme]` + `@media` (§7.2) |
| `@apply border-border outline-ring/50` | **nein** | die Eigenschaften ausschreiben |
| `@layer base` / `@layer utilities` | **nein** (Tailwind-Bedeutung) | Kaskadenschichten sind natives CSS, hier aber unnötig |
| `dark:`-Präfix an Klassen | **nein** | die Tokens wechseln, nicht die Klassen |
| `bg-primary/90`, `ring-ring/50` | **nein** | Tailwind-Syntax. Ohne `color-mix()`: zweite Helligkeitsstufe desselben Farbtons |
| `size-4`, `h-9`, `px-3` … | **nein** | echte CSS-Eigenschaften mit den Werten aus §6 |
| `cva` / class-variance-authority | **nein** | Varianten sind hier Klassen (`.btn`, `.btn-action`) |
| reka-ui, Portale, `data-[state=open]` | **nein** | eigenes Markup |
| `--chart-1…5`, `--sidebar-*` | **nein** | für Diagramme und eine Seitenleiste, die es hier nicht gibt |
| `--cube-*`, `--boot-*`, `--dimension-*`, `--curve-*` | **nein** | 3D-Konfigurator |
| `.ubq-public[data-ubq-theme]` | **nein** | CE.SDK-Editor. **Das Muster** ist trotzdem lehrreich: eine fremde Komponente einbinden heißt, ihre eigenen Variablen auf unsere zu legen — nicht ihre Regeln zu überschreiben |
| vue-i18n | **nein** | JSON + eigene Auflösung; **die `|`-Falle gilt trotzdem** (§8.4) |
| vue-sonner | **nein** | die Maße aus §10.2 sind trotzdem die Vorgabe |

Die Faustregel: **Werte und Erkenntnisse wandern, Werkzeuge nicht.** Wenn eine Zeile
aus `main.css` ein `@`-Zeichen von Tailwind enthält, ist sie hier falsch. Wenn sie eine
Zahl enthält, ist sie hier wahrscheinlich richtig.

---

## 12 Quellen

Im Webprojekt `snow-service-free`:

| Datei | Was daraus stammt |
|---|---|
| `src/main.css` | alle Farbtokens, Radienskala, Scrollbar, Puls, mobile Meldungen, `@font-face`, die mobile Rampe |
| `index.html` | Themenskript vor dem Bundle, Verlauf des Startbildschirms, `lang`-Vorgabe |
| `tailwind.config.ts` | `action` / `action-foreground` als Tailwind-Farben |
| `components.json` | shadcn-vue, Stil „new-york“, Basisfarbe neutral, CSS-Variablen |
| `src/components/shadcn/ui/button/index.ts` | Knopfvarianten und -größen |
| `src/components/shadcn/ui/input/Input.vue` | Feldmaße und Zustände |
| `src/components/shadcn/ui/select/SelectTrigger.vue` | Auswahl |
| `src/components/shadcn/ui/card/*.vue` | Kartenaufbau |
| `src/components/shadcn/ui/tooltip/TooltipContent.vue` | Hinweisblase |
| `src/components/shadcn/ui/dropdown-menu/*.vue` | Menü und Einträge |
| `src/components/utilities/ColorModeSwitch.vue` | Themenumschalter |
| `src/components/utilities/LocaleSwitch.vue` | Sprachumschalter |
| `src/components/utilities/SceneControls.vue` | Bauteil veröffentlicht seine Maße als Token |
| `src/components/layouts/ConfiguratorDesktop.vue` | Behandlung der Markenzeile |
| `src/stores/app/store.ts` | `toggleColorMode`, `isLightMode`, `isMobile`, `locale` |
| `src/utils/cssThemeVar.ts` | `readCssThemeVar` |
| `src/i18n/index.ts` | Spracherkennung, `<html lang>`-Abgleich, die `\|`-Falle |
| `src/i18n/constants.ts` | Speicherschlüssel, Ausweichsprache |
| `src/i18n/documentLanguage.ts` | der einzige Schreiber von `lang` |
| `src/composeables/useI18n.ts` | `setLocale`, `td()` |
| `src/assets/fonts/Montserrat/` | die Schriftdateien |

In diesem Repo:

| Datei | Rolle |
|---|---|
| `app/static/css/tokens.css` | die arbeitende Fassung dieses Dokuments |
| `app/config.py`, Block `# --- Marke ---` | SSOT der Farben **für das PDF** |
| `app/static/brand/` | Logo (`logo-light`, `logo-dark`, `logo-black`) und Schrift |
| `AGENTS.md` | Konventionen und Invarianten des Repos |
