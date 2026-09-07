# `shared/` — was sich drei Sprachen teilen

Hier liegt, was Python, C++ und JavaScript **gemeinsam** brauchen. Nichts hier ist
Python-spezifisch, und nichts hier darf in einer der drei Sprachen noch einmal
definiert werden.

- `constants.json` — alle Konstanten, die eine Aussage über das *Produkt* machen.
  Konstanten über das *Programm* (Pfade, Port, Fassung) stehen weiter in
  `app/config.py`.
- `fixtures/` — eingefrorene synthetische Szenen samt Grundwahrheit. Jede
  Implementierung des Rechenkerns wird gegen **diese** Dateien geprüft, nicht
  gegeneinander.

Warum das so ist: `docs/cpp-migration/README.md`.
