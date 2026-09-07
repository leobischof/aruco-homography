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
 * Accept-Language-Kopf mitschicken. Deshalb hat /api/markersheet den
 * Fragezeichen-Parameter ?locale= - und deshalb muss dieser Parameter bei jedem
 * Sprachwechsel nachgezogen werden, sonst kommt das Blatt in der Sprache des
 * Browsers statt in der der Oberflaeche.
 */

import { getLocale, onLocaleChange, setLocale, t } from "./i18n.js";
import { effectiveTheme, onThemeChange, toggleTheme } from "./theme.js";

export function createHeader({ themeButton, langButtons, sheetLink, getSheetParams }) {
    function syncTheme() {
        // Der Knopf zeigt, was er TUT, nicht was ist: im hellen Thema den Mond
        // ("auf dunkel schalten"). Welches Symbol sichtbar ist, entscheidet
        // [data-theme-only] in base.css; hier steht nur die Beschriftung, denn
        // die haengt am Katalog und nicht am Stylesheet.
        const label = effectiveTheme() === "dark" ? t("ui.theme.to_light") : t("ui.theme.to_dark");
        themeButton.title = label;
        themeButton.setAttribute("aria-label", label);
    }

    function syncLanguage() {
        const current = getLocale();
        for (const button of langButtons) {
            button.setAttribute("aria-pressed", String(button.dataset.locale === current));
        }
    }

    function syncSheetLink() {
        const parameters = new URLSearchParams();
        for (const [key, value] of Object.entries(getSheetParams())) {
            if (Number.isFinite(value)) parameters.set(key, String(value));
        }
        parameters.set("locale", getLocale());
        sheetLink.href = `/api/markersheet?${parameters}`;
    }

    themeButton.addEventListener("click", toggleTheme);
    onThemeChange(syncTheme);

    for (const button of langButtons) {
        button.addEventListener("click", async () => {
            if (button.dataset.locale === getLocale()) return;
            await setLocale(button.dataset.locale);
        });
    }

    // setLocale ruft applyTranslations selbst auf - was dort NICHT erneuert wird,
    // sind Beschriftungen, die von einem Zustand abhaengen (welches Thema,
    // welche Sprache ist aktiv). Genau das holt dieser Lauscher nach.
    onLocaleChange(() => {
        syncTheme();
        syncLanguage();
        syncSheetLink();
    });

    syncTheme();
    syncLanguage();
    syncSheetLink();

    return { syncSheetLink };
}
