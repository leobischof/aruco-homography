/**
 * header.js - die drei Bedienelemente im Kopf: Themenknopf, Sprachumschalter,
 * Verweis auf das Markerblatt.
 *
 * Sie stehen zusammen in einer Datei, weil sie ein Problem teilen: alle drei
 * muessen sich neu ausrichten, sobald sich Sprache ODER Thema aendert - und
 * zwar auch dann, wenn die Aenderung nicht von ihnen ausging (Systemvorgabe
 * kippt, Sprache kommt aus dem Speicher).
 *
 * Der Sonderfall, um den es hier eigentlich geht: das Markerblatt wird ueber
 * einen gewoehnlichen Anker geholt, und ein Anker kann keinen
 * Accept-Language-Kopf mitschicken. Deshalb nimmt api.js::markersheetUrl die
 * Sprache als Parameter - und deshalb muss die Adresse bei jedem Sprachwechsel
 * nachgezogen werden, sonst kommt das Blatt in der Sprache des Browsers statt
 * in der der Oberflaeche.
 *
 * Der Sprachwaehler steht NICHT im Markup, sondern entsteht hier aus der Liste,
 * die i18n.js ueber api.js geholt hat. Vorher waren es zwei fest
 * hingeschriebene Knoepfe, DE und EN: eine dritte Sprache haette Markup,
 * Stylesheet und zwei Konstantenlisten angefasst. Jetzt genuegen die
 * Katalogdatei und ein Eintrag in config.SUPPORTED_LOCALES.
 */

import { markersheetUrl } from "./api.js";
import { getLocale, getLocales, onLocaleChange, setLocale, t } from "./i18n.js";
import { effectiveTheme, onThemeChange, toggleTheme } from "./theme.js";

export function createHeader({ themeButton, langSelect, sheetLink, getSheetParams }) {
    function syncTheme() {
        // Der Knopf zeigt, was er TUT, nicht was ist: im hellen Thema den Mond
        // ("auf dunkel schalten"). Welches Symbol sichtbar ist, entscheidet
        // [data-theme-only] in base.css; hier steht nur die Beschriftung, denn
        // die haengt am Katalog und nicht am Stylesheet.
        const label = effectiveTheme() === "dark" ? t("ui.theme.to_light") : t("ui.theme.to_dark");
        themeButton.title = label;
        themeButton.setAttribute("aria-label", label);
    }

    /**
     * Die Eintraege einmal aufbauen: das Kuerzel der Sprache, "DE" und "EN".
     *
     * Das Kuerzel wird aus dem Code GERECHNET und nicht uebersetzt - eine dritte
     * Sprache bleibt damit eine Katalogdatei plus ein Eintrag in
     * config.SUPPORTED_LOCALES.
     *
     * <b>Warum nicht der Eigenname.</b> Bis 0.1.3-alpha stand hier ein Tausch:
     * geschlossen das Kuerzel, aufgeklappt "Deutsch"/"English", umgeschaltet auf
     * mousedown/touchstart/focus und zurueck auf change/blur. Auf einem Xiaomi
     * unter Android 15 blieb er haengen - wer das Systemrad oeffnet und wieder
     * schliesst, ohne die Sprache zu WECHSELN, loest weder `change` noch `blur`
     * aus. Der Waehler stand danach dauerhaft auf "Deutsch", abgeschnitten in
     * einem Feld, das fuer zwei Grossbuchstaben breit ist.
     *
     * HTML kann das nicht: eine Option hat EINE Beschriftung, und sie gilt
     * geschlossen wie aufgeklappt. Jede Loesung waere entweder ein Tausch mit
     * demselben Zeitproblem oder ein nachgebautes Aufklappmenue - und das native
     * <select> ist hier Absicht (index.html sagt, warum). Zwei Sprachen, zwei
     * eindeutige Kuerzel, und was der Waehler tut, steht in aria-label und title.
     */
    function buildLanguageOptions() {
        langSelect.replaceChildren(
            ...getLocales().map(({ code }) => {
                const option = document.createElement("option");
                option.value = code;
                option.textContent = code.toUpperCase();
                return option;
            })
        );
    }

    function syncLanguage() {
        langSelect.value = getLocale();
    }

    /**
     * Die Adresse des Markerblatts nachziehen.
     *
     * Sie ist ein Versprechen und kein Wert: im Ortsbetrieb wird das Blatt erst
     * gebaut, wenn jemand danach fragt. Bis es da ist, bleibt der alte Verweis
     * stehen - besser ein Blatt in der vorigen Sprache als ein toter Knopf.
     */
    function syncSheetLink() {
        Promise.resolve(markersheetUrl(getSheetParams()))
            .then((url) => {
                sheetLink.href = url;
            })
            .catch((error) => console.error("Markerblatt nicht erreichbar", error));
    }

    themeButton.addEventListener("click", toggleTheme);
    onThemeChange(syncTheme);

    langSelect.addEventListener("change", () => {
        // Schlaegt der Katalog fehl, zeigte die Auswahl eine Sprache, die gar
        // nicht gilt - dann zurueck auf die, die wirklich laeuft.
        setLocale(langSelect.value).catch((error) => {
            console.error("Sprachwechsel fehlgeschlagen", error);
            syncLanguage();
        });
    });

    // setLocale ruft applyTranslations selbst auf - was dort NICHT erneuert wird,
    // sind Beschriftungen, die von einem Zustand abhaengen (welches Thema,
    // welche Sprache ist aktiv). Genau das holt dieser Lauscher nach.
    onLocaleChange(() => {
        syncTheme();
        syncLanguage();
        syncSheetLink();
    });

    syncTheme();
    buildLanguageOptions();
    syncLanguage();
    syncSheetLink();

    return { syncSheetLink };
}
