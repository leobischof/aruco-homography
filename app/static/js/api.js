/**
 * api.js - jeder Weg zum Server fuehrt hier durch. Auch dann, wenn es keinen gibt.
 *
 * Drei Aufgaben, und jede gaebe es sonst an vier Stellen:
 *
 * 1. **Accept-Language an JEDER Anfrage.** Der Server uebersetzt seine Fehler
 *    und Warnungen selbst (app/i18n.py). Ohne den Kopf folgte er der
 *    Browsereinstellung statt dem Schalter in der Oberflaeche - die Seite waere
 *    dann englisch und ihre Fehlermeldungen deutsch.
 * 2. **Fehler in eine Form bringen.** Der Server antwortet mit
 *    {code, params, field, message}. Uebersetzt wird bevorzugt HIER, aus
 *    errors.<code> mit den Parametern; `message` ist nur der Ausweg fuer einen
 *    Code, den der Katalog nicht kennt (aelterer Server, neuer Code).
 * 3. **Die Betriebsart waehlen.** Es gibt zwei:
 *
 *        transport = "http"    ->  fetch(), der Desktop-Server
 *        transport = "local"   ->  WASM-Kern und web/pdf/, ganz in der Seite
 *
 *    Gewaehlt wird sie EINMAL, beim Laden, aus `window.ARUCO_TRANSPORT` - so wie
 *    ARUCO_CORE den Rechenkern und ARUCO_PDF den PDF-Bau waehlen. Die Seite unter
 *    web/index.html setzt sie auf "local"; wer die Datei ueber den Server holt,
 *    bekommt die Vorgabe "http". Ueber diese Zeile hinaus weiss NICHTS in
 *    app/static/js/ von der Betriebsart.
 *
 * Der Ortsbetrieb wird per `import()` geholt und nicht oben eingebunden: sonst
 * laedt der Serverbetrieb ein paar Megabyte WebAssembly, die er nie anfasst.
 */

import { getLocale, hasKey, t } from "./i18n.js";

export const HTTP = "http";
export const LOCAL = "local";

/** Die Betriebsart dieser Seite. Steht beim Laden fest und aendert sich nicht. */
export function transport() {
    return globalThis.ARUCO_TRANSPORT === LOCAL ? LOCAL : HTTP;
}

let localModule = null;

/**
 * Der Ortsbetrieb, beim ersten Bedarf geladen.
 *
 * Der Pfad ist relativ zu DIESER Datei und trifft damit in beiden Baeumen: im
 * Quellbaum liegt web/ neben app/, und im ausgelieferten Bau ebenso.
 */
async function local() {
    if (localModule === null) {
        localModule = await import("../../../web/vision/local.js");
    }
    return localModule;
}

/**
 * Einen Fehler des Ortsbetriebs in die Drahtform des Servers bringen.
 *
 * Ohne das saehe derselbe Fehler in den beiden Betriebsarten verschieden aus -
 * und describeError unten koennte ihn nicht mehr uebersetzen.
 */
async function localError(error) {
    const module = await local();
    throw module.errorPayload(error, getLocale());
}

/**
 * Antwort auspacken. Fachliche Fehler kommen als 422 mit JSON-Rumpf; was kein
 * JSON ist (Proxy, 500er Seite), wird zu einer Meldung mit dem Statustext.
 */
async function unwrap(response) {
    let payload = null;
    try {
        payload = await response.json();
    } catch (error) {
        payload = null;
    }
    if (response.ok) return payload;
    throw payload && typeof payload === "object"
        ? payload
        : { message: `HTTP ${response.status} ${response.statusText}` };
}

function jsonHeaders() {
    return {
        "Content-Type": "application/json",
        "Accept-Language": getLocale(),
    };
}

/**
 * Eine JSON-Anfrage. Im Ortsbetrieb entscheidet die URL, welche Rechnung laeuft -
 * dieselbe Zuordnung, die app/main.py mit seinen Routen trifft.
 */
export async function postJson(url, body, { signal } = {}) {
    if (transport() === LOCAL) {
        const module = await local();
        try {
            if (url === "/api/solve") return await module.solve(body, getLocale());
            if (url === "/api/adjust") return await module.adjust(body);
            throw new Error(`Ortsbetrieb kennt ${url} nicht`);
        } catch (error) {
            return localError(error);
        }
    }

    const response = await fetch(url, {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify(body),
        signal,
    });
    return unwrap(response);
}

export async function uploadPhoto(file) {
    if (transport() === LOCAL) {
        const module = await local();
        try {
            return await module.uploadPhoto(file);
        } catch (error) {
            return localError(error);
        }
    }

    const form = new FormData();
    form.append("file", file);
    // Kein Content-Type von Hand: den setzt der Browser samt multipart-Grenze.
    const response = await fetch("/api/upload", {
        method: "POST",
        headers: { "Accept-Language": getLocale() },
        body: form,
    });
    return unwrap(response);
}

/**
 * Derselbe Zuschnitt als Bilddatei. Auch das ist kein JSON, sondern Bytes.
 *
 * Zurueck kommt dieselbe Form wie bei exportPdf - ein Blob plus das, was die
 * Oberflaeche darueber schreiben will.
 */
export async function exportImage(body) {
    if (transport() === LOCAL) {
        const module = await local();
        try {
            return await module.exportImage(body);
        } catch (error) {
            return localError(error);
        }
    }

    const response = await fetch("/api/export-image", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept-Language": getLocale() },
        body: JSON.stringify(body),
    });
    if (!response.ok) throw await unwrap(response);

    const blob = await response.blob();
    return {
        blob,
        format: body.image_format === "png" ? "png" : "jpeg",
        pixels: response.headers.get("X-Image-Pixels") || "",
        mmPerPx: Number(response.headers.get("X-Mm-Per-Px")),
    };
}

/**
 * Der Export liefert kein JSON, sondern das PDF - samt Seitenzahl und
 * Seitenformat in den Kopfzeilen. Deshalb kann er nicht durch postJson.
 */
export async function exportPdf(body) {
    if (transport() === LOCAL) {
        const module = await local();
        try {
            return await module.exportPdf(body);
        } catch (error) {
            return localError(error);
        }
    }

    const response = await fetch("/api/export", {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify(body),
    });
    if (!response.ok) await unwrap(response);
    return {
        blob: await response.blob(),
        pages: response.headers.get("X-Pages") || "1",
        pageSize: response.headers.get("X-Page-Size-Mm") || "",
    };
}

/**
 * Die waehlbaren Sprachen.
 *
 * Frueher holte i18n.js sie selbst mit fetch. Das widersprach dem Satz oben -
 * jeder Weg zum Server fuehrt hier durch - und war im Ortsbetrieb eine Anfrage
 * an einen Server, den es nicht gibt.
 */
export async function fetchLocales() {
    if (transport() === LOCAL) {
        return (await local()).locales();
    }
    const response = await fetch("/api/locales", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`locales: HTTP ${response.status}`);
    return response.json();
}

/**
 * Der Sprachkatalog einer Sprache.
 *
 * Die URL wird aus `import.meta.url` gebaut und nicht als "/i18n/..."
 * geschrieben: dieselbe Datei liegt in beiden Baeumen zwei Ebenen ueber diesem
 * Modul, und eine absolute URL traefe nur den Server, der app/static/ auf /
 * legt. Es ist DIESELBE Datei, die auch app/i18n.py liest - eine zweite Fassung
 * fuer den Ortsbetrieb waere genau die Drift, die Invariante 7 verhindert.
 */
export async function fetchCatalogue(code) {
    const url = new URL(`../i18n/${code}.json`, import.meta.url);
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`i18n ${code}: HTTP ${response.status}`);
    return response.json();
}

/**
 * Die Adresse des Markerblatts.
 *
 * Am Server ein gewoehnlicher Verweis mit Fragezeichen-Parametern, im
 * Ortsbetrieb ein frisch gebautes PDF als Blob-URL. Beide Male ein Versprechen,
 * damit der Aufrufer nicht wissen muss, welcher Fall vorliegt.
 */
export async function markersheetUrl(parameters) {
    if (transport() === LOCAL) {
        return (await local()).markersheet({ ...parameters, locale: getLocale() });
    }
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(parameters)) {
        if (Number.isFinite(value)) query.set(key, String(value));
    }
    query.set("locale", getLocale());
    return `/api/markersheet?${query}`;
}

/**
 * Einen Server-Fehler in einen Satz verwandeln, den der Benutzer lesen kann.
 *
 * Reihenfolge: eigener Katalog (errors.<code> mit Parametern), dann der
 * Klartext des Servers, dann ein allgemeiner Satz. Nie eine leere Meldung -
 * ein Fehler ohne Text ist schlimmer als gar keiner.
 */
export function describeError(error) {
    if (!error) return t("ui.common.error_unknown");

    const key = error.code ? `errors.${error.code}` : "";
    let text = key && hasKey(key) ? t(key, error.params || {}) : "";
    if (!text) text = typeof error.message === "string" ? error.message : "";
    if (!text) text = t("ui.common.error_unknown");

    return error.field ? `${text} ${t("ui.common.error_field", { field: error.field })}` : text;
}

/** Dasselbe fuer die Warnungen aus /api/solve: notices.<code>, sonst message. */
export function describeNotice(notice) {
    const key = notice && notice.code ? `notices.${notice.code}` : "";
    if (key && hasKey(key)) return t(key, notice.params || {});
    return (notice && notice.message) || t("ui.common.error_unknown");
}
