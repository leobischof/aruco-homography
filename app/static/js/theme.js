/**
 * theme.js - helles und dunkles Thema, und der eine Weg, Tokenfarben in ein
 * Canvas zu bekommen.
 *
 * Es gibt DREI Zustaende, und alle drei muessen funktionieren:
 *
 *   1. ausdruecklich hell   -> <html data-theme="light">
 *   2. ausdruecklich dunkel  -> <html data-theme="dark">
 *   3. keine Wahl getroffen  -> gar kein Attribut, es gilt prefers-color-scheme
 *
 * Gebaut sind die drei in tokens.css; dieses Modul legt nur den Schalter um und
 * merkt sich die Wahl. Der Vorspann in index.html setzt das Attribut schon vor
 * dem ersten Zeichnen - ohne ihn blitzt die Seite hell auf und kippt erst
 * hinterher ins Dunkle.
 *
 * Zustand 3 ist nicht dasselbe wie "hell": wer nie geklickt hat, folgt seinem
 * System, auch wenn es waehrend der Sitzung umschaltet. Deshalb der Lauscher auf
 * die Medienabfrage.
 */

// Muss zu config.THEME_STORAGE_KEY passen.
const STORAGE_KEY = "aruco-theme";

const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
const listeners = new Set();

/** Was der Benutzer TATSAECHLICH sieht - Wahl, sonst Systemvorgabe. */
export function effectiveTheme() {
    const chosen = document.documentElement.dataset.theme;
    if (chosen === "dark" || chosen === "light") return chosen;
    return darkQuery.matches ? "dark" : "light";
}

export function setTheme(theme) {
    const wanted = theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = wanted;
    try {
        localStorage.setItem(STORAGE_KEY, wanted);
    } catch (error) {
        /* Privater Modus: die Wahl gilt dann nur fuer diese Sitzung. */
    }
    notify();
}

export function toggleTheme() {
    setTheme(effectiveTheme() === "dark" ? "light" : "dark");
}

export function onThemeChange(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
}

function notify() {
    const theme = effectiveTheme();
    for (const listener of listeners) listener(theme);
}

/**
 * Einen Tokenwert als fertige Farbe lesen.
 *
 * Ein Canvas- oder WebGL-Kontext loest `var(--x)` nicht auf; er will einen
 * ausgerechneten Farbwert. Diese Funktion ist die EINE Lesestelle dafuer -
 * sinngemaess free/src/utils/cssThemeVar.ts, deren Kommentar festhaelt, dass
 * genau diese drei Zeilen dort vorher dreimal kopiert existierten.
 *
 * Der Ausweichwert wird nur benutzt, wenn tokens.css gar nicht geladen ist; dann
 * ist die Seite ohnehin kaputt. Deshalb stehen dort CSS-Systemfarben
 * ("canvastext", "canvas") und keine erfundenen Hexwerte: die folgen wenigstens
 * noch der Helligkeit des Systems.
 */
export function readCssThemeVar(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
}

export function initTheme() {
    // Nur wirksam, solange KEINE ausdrueckliche Wahl gespeichert ist - sonst
    // wuerde das System die Wahl des Benutzers ueberschreiben. Genau das
    // verhindert auch das :not([data-theme="light"]) in tokens.css.
    darkQuery.addEventListener("change", () => {
        if (!document.documentElement.dataset.theme) notify();
    });
}
