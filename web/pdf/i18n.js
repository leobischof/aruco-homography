/**
 * i18n.js - aus einem Schluessel wird Text. Invariante 7 fuer den PDF-Bau.
 *
 * Es sind DIESELBEN Katalogdateien, die auch app/i18n.py liest und die die
 * Oberflaeche holt (app/static/i18n/). Keine zweite Fassung - genau deshalb kann
 * tests/test_i18n.py darauf bestehen, dass beide Sprachen denselben Schluesselsatz
 * haben, und genau deshalb steht im PDF kein fertiger deutscher Satz im Code.
 *
 * Warum nicht app/static/js/i18n.js benutzt wird, das es schon gibt: das Modul der
 * Oberflaeche holt die Kataloge ueber `fetch`, merkt sich die gewaehlte Sprache,
 * schreibt `<html lang>` und ist asynchron. Ein PDF-Bau braucht davon nichts und
 * darf nichts davon voraussetzen - er braucht eine reine Funktion. Uebernommen ist
 * deshalb die Fassung aus app/i18n.py, nicht die des Browsers.
 *
 * Ein fehlender Schluessel bricht nie ab: erst wird auf DEFAULT_LOCALE ausgewichen,
 * und fehlt er auch dort, kommt der Schluessel selbst zurueck. Damit faellt die
 * Luecke auf dem Papier auf, statt den Ablauf zu toeten.
 */

import de from "../../app/static/i18n/de.json" with { type: "json" };
import en from "../../app/static/i18n/en.json" with { type: "json" };
import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from "./constants.js";

// Nur `{name}` wird ersetzt. Unbekannte Namen bleiben woertlich stehen - sichtbar,
// aber harmlos; ein Absturz mitten im Fehlertext waere das schlechtere Ergebnis.
const PLACEHOLDER = /\{(\w+)\}/g;

const SOURCES = { de, en };

// Statische Importe kann man nicht aus einer Liste erzeugen. Damit eine neue
// Sprache in shared/constants.json nicht still ohne Katalog bleibt, wird der
// Abgleich hier EINMAL beim Laden gemacht - laut und frueh statt spaeter als
// englischer Satz auf einem deutschen Blatt.
for (const locale of SUPPORTED_LOCALES) {
    if (!(locale in SOURCES)) {
        throw new Error(`Sprache "${locale}" steht in shared/constants.json, aber web/pdf/i18n.js kennt keinen Katalog dafuer.`);
    }
}

const CATALOGUES = Object.fromEntries(
    Object.entries(SOURCES).map(([locale, tree]) => [locale, flatten(tree)]),
);

/** Verschachteltes JSON zu "a.b.c" -> Text. */
function flatten(node, prefix = "", target = {}) {
    for (const [name, value] of Object.entries(node)) {
        const path = `${prefix}${name}`;
        if (value !== null && typeof value === "object") {
            flatten(value, `${path}.`, target);
        } else {
            target[path] = String(value);
        }
    }
    return target;
}

/** Auf eine unterstuetzte Sprache abbilden. null, Unsinn und "de-CH" gehen durch. */
export function normalise(locale) {
    if (!locale) return DEFAULT_LOCALE;
    const primary = String(locale).trim().toLowerCase().replace(/_/g, "-").split("-")[0];
    return SUPPORTED_LOCALES.includes(primary) ? primary : DEFAULT_LOCALE;
}

/** Text zu einem Punktschluessel, mit `{name}`-Platzhaltern gefuellt. */
export function translate(key, locale, params = {}) {
    const wanted = normalise(locale);
    let text = CATALOGUES[wanted][key];
    if (text === undefined && wanted !== DEFAULT_LOCALE) {
        text = CATALOGUES[DEFAULT_LOCALE][key];
    }
    if (text === undefined) return key;
    return text.replace(PLACEHOLDER, (match, name) =>
        Object.hasOwn(params, name) ? String(params[name]) : match,
    );
}
