---
title: docs/design
description: Einstieg ins Designsystem und die drei Dinge, die man vor jeder Änderung wissen muss.
audience: developer
status: current
updated: 2026-09-07
---

# docs/design

Wie dieses Werkzeug aussehen soll und warum.

| Datei | Inhalt |
|---|---|
| [`design-system.md`](design-system.md) | Das Designsystem des Hauses: Farbe, Typografie, Form, Komponenten, Themenwechsel, Mehrsprachigkeit, Bewegung, Mobil — und was aus dem Webprojekt **nicht** zu übernehmen ist. |

**Die arbeitende Fassung ist `app/static/css/tokens.css`.** Dieses Verzeichnis erklärt
sie; es ersetzt sie nicht. Wer einen Wert ändert, ändert beide — ein Dokument, das die
Unwahrheit sagt, ist schlimmer als keines.

Drei Dinge, die man wissen muss, bevor man hier etwas anfasst:

- **Die Quelle ist `snow-service-free/src/main.css`**, das Haus-Designsystem des
  Webprojekts. Die Tokennamen sind dort dieselben. Genau das macht die beiden Werkzeuge
  zu einem Haus — ein neuer Name hier ist eine Abweichung und braucht eine Begründung.
- **Die Farben stehen an drei Orten**: `main.css` (Haus), `tokens.css` (Oberfläche),
  `app/config.py` im Block `# --- Marke ---` (PDF, weil ReportLab Hex braucht). Sie sind
  gegengerechnet und stimmen; siehe design-system.md §3.7.
- **Kein Build-Schritt.** FastAPI liefert die Dateien aus, wie sie dastehen. Alles, was
  in free erst Tailwind erzeugt (`@apply`, `@theme inline`, `@custom-variant`, `dark:`),
  würde hier stillschweigend nichts tun; siehe design-system.md §11.
