/**
 * i18n.js - der Sprachkatalog der Oberflaeche.
 *
 * Die Kataloge unter app/static/i18n/ sind DIESELBEN Dateien, die auch Python
 * liest (app/i18n.py). Es gibt keine zweite Fassung fuer den Browser - genau
 * deshalb kann tests/test_i18n.py darauf bestehen, dass beide Sprachen dieselbe
 * Schluesselmenge haben.
 *
 * Drei Dinge, die hier leicht falsch gemacht werden und in free schon weh taten:
 *
 * 1. `<html lang>` MUSS bei jedem Wechsel mitgeschrieben werden. Bleibt der
 *    Bauzeitwert stehen, bietet Chrome an, die bereits deutsche Oberflaeche aus
 *    dem Englischen ins Deutsche zu uebersetzen, und Screenreader lesen
 *    deutschen Text mit englischer Stimme (design-system.md 8.3).
 * 2. Ein fehlender Schluessel wird SICHTBAR als Schluessel gerendert, nie leer.
 *    Leerer Text sieht aus wie ein Layoutfehler und wird nie gemeldet.
 * 3. Kein nacktes `|` in einem uebersetzbaren Text. vue-i18n liest es als
 *    Trenner der Pluralformen und kuerzt still (design-system.md 8.4). Dieses
 *    Werkzeug benutzt kein vue-i18n, aber die Kataloge sind dieselben Dateien
 *    wie im Haus, und die Regel wandert mit ihnen.
 */

// Muss zu config.LOCALE_STORAGE_KEY passen - dort steht die Begruendung fuer den
// Namen (er folgt free's "free-language").
const STORAGE_KEY = "aruco-language";

// Muss zu config.SUPPORTED_LOCALES und config.DEFAULT_LOCALE passen. Deutsch ist
// die Ausgangssprache: die Oberflaeche ist deutsch, und der Benutzer steht in
// einer Werkstatt in der Schweiz.
export const SUPPORTED_LOCALES = ["de", "en"];
const FALLBACK_LOCALE = "de";

const PLACEHOLDER = /\{(\w+)\}/g;

let locale = FALLBACK_LOCALE;
let messages = {};
const loaded = new Map();
const listeners = new Set();

/** Aus dem verschachtelten JSON eine flache Karte "a.b.c" -> Text machen. */
function flatten(node, prefix = "", target = {}) {
    for (const [key, value] of Object.entries(node)) {
        const path = prefix + key;
        if (value !== null && typeof value === "object") {
            flatten(value, path + ".", target);
        } else {
            target[path] = String(value);
        }
    }
    return target;
}

/** "de-CH" -> "de"; alles Unbekannte auf die Vorgabesprache. */
export function normaliseLocale(value) {
    const code = String(value || "").split("-")[0].toLowerCase();
    return SUPPORTED_LOCALES.includes(code) ? code : FALLBACK_LOCALE;
}

export function getLocale() {
    return locale;
}

/**
 * Text zu einem Schluessel, Platzhalter `{name}` ersetzt.
 *
 * Ein Platzhalter, fuer den kein Wert kommt, bleibt roh stehen - genauso wie in
 * app/i18n.py. Das ist Absicht: er faellt auf und laesst sich beheben, waehrend
 * eine Leerstelle nach Absicht aussieht.
 */
export function t(key, params) {
    const template = messages[key];
    if (typeof template !== "string") return key;
    if (!params) return template;
    return template.replace(PLACEHOLDER, (match, name) =>
        Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : match
    );
}

/** True, wenn der Katalog diesen Schluessel ueberhaupt kennt. */
export function hasKey(key) {
    return typeof messages[key] === "string";
}

/**
 * Uebersetzten Text als DocumentFragment, wobei die genannten Platzhalter fett
 * gesetzt werden.
 *
 * Der Umweg ueber das Fragment statt innerHTML ist kein Zierat: die Werte kommen
 * teils vom Server (Dateiname, Fehlertext), und ein Dateiname mit spitzen
 * Klammern waere sonst Markup.
 */
export function richText(key, params = {}, strongNames = []) {
    const fragment = document.createDocumentFragment();
    const template = messages[key];
    if (typeof template !== "string") {
        fragment.append(key);
        return fragment;
    }

    // Eigene Regex-Instanz: matchAll uebernimmt lastIndex des uebergebenen
    // Musters, und ein geteiltes globales Muster traegt den Stand seines letzten
    // Laufs mit sich.
    let cursor = 0;
    for (const match of template.matchAll(/\{(\w+)\}/g)) {
        if (match.index > cursor) fragment.append(template.slice(cursor, match.index));
        const name = match[1];
        if (Object.prototype.hasOwnProperty.call(params, name)) {
            const value = String(params[name]);
            if (strongNames.includes(name)) {
                const strong = document.createElement("b");
                strong.textContent = value;
                fragment.append(strong);
            } else {
                fragment.append(value);
            }
        } else {
            fragment.append(match[0]);
        }
        cursor = match.index + match[0].length;
    }
    fragment.append(template.slice(cursor));
    return fragment;
}

/** Zahl in der Schreibweise der aktuellen Sprache (Komma oder Punkt). */
export function formatNumber(value, digits = 2) {
    return new Intl.NumberFormat(locale, {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    }).format(value);
}

/**
 * Alle beschrifteten Elemente unter `root` neu beschriften.
 *
 * `data-i18n="schluessel"` setzt den Textinhalt,
 * `data-i18n-attr="placeholder:schluessel,title:schluessel"` setzt Attribute.
 * Beides laeuft bei jedem Sprachwechsel erneut - deshalb darf kein Aufrufer
 * Text, der einmal uebersetzt wurde, danach von Hand ueberschreiben.
 */
export function applyTranslations(root = document) {
    for (const element of root.querySelectorAll("[data-i18n]")) {
        element.textContent = t(element.dataset.i18n);
    }
    for (const element of root.querySelectorAll("[data-i18n-attr]")) {
        for (const pair of element.dataset.i18nAttr.split(",")) {
            const separator = pair.indexOf(":");
            if (separator < 0) continue;
            const attribute = pair.slice(0, separator).trim();
            const key = pair.slice(separator + 1).trim();
            if (attribute && key) element.setAttribute(attribute, t(key));
        }
    }
}

async function catalogue(wanted) {
    if (loaded.has(wanted)) return loaded.get(wanted);
    const response = await fetch(`/i18n/${wanted}.json`, {
        headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`i18n ${wanted}: HTTP ${response.status}`);
    const flat = flatten(await response.json());
    loaded.set(wanted, flat);
    return flat;
}

/** Sprache wechseln: Katalog laden, Dokument beschriften, Wahl merken. */
export async function setLocale(next, { remember = true } = {}) {
    const wanted = normaliseLocale(next);
    messages = await catalogue(wanted);
    locale = wanted;

    document.documentElement.lang = wanted;
    document.title = t("document.title");
    applyTranslations();

    if (remember) {
        try {
            localStorage.setItem(STORAGE_KEY, wanted);
        } catch (error) {
            /* Privater Modus: die Wahl gilt dann nur fuer diese Sitzung. */
        }
    }

    for (const listener of listeners) listener(wanted);
}

export function onLocaleChange(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
}

/**
 * Startsprache: gespeicherte Wahl, sonst Browsersprache, sonst Deutsch.
 * Dieselbe Reihenfolge wie free/src/i18n/index.ts, getInitialLocale().
 */
function initialLocale() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored && SUPPORTED_LOCALES.includes(stored)) return stored;
    } catch (error) {
        /* kein Speicher, kein Problem - dann entscheidet der Browser */
    }
    const browser = String(navigator.language || "").split("-")[0].toLowerCase();
    return SUPPORTED_LOCALES.includes(browser) ? browser : FALLBACK_LOCALE;
}

/**
 * Katalog laden, bevor irgendetwas gezeichnet wird.
 *
 * Schlaegt das fehl, bleibt der Katalog leer und jede Beschriftung zeigt ihren
 * Schluessel. Das ist haesslich und genau deshalb richtig: die Oberflaeche bleibt
 * bedienbar und der Fehler ist nicht zu uebersehen.
 */
export async function initI18n() {
    const wanted = initialLocale();
    try {
        await setLocale(wanted, { remember: false });
    } catch (error) {
        console.error("Sprachkatalog nicht ladbar", error);
        document.documentElement.lang = wanted;
        locale = wanted;
        applyTranslations();
    }
}
