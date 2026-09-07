/**
 * api.js - jeder Weg zum Server fuehrt hier durch.
 *
 * Zwei Aufgaben, und beide gaebe es sonst an vier Stellen:
 *
 * 1. **Accept-Language an JEDER Anfrage.** Der Server uebersetzt seine Fehler
 *    und Warnungen selbst (app/i18n.py). Ohne den Kopf folgte er der
 *    Browsereinstellung statt dem Schalter in der Oberflaeche - die Seite waere
 *    dann englisch und ihre Fehlermeldungen deutsch.
 * 2. **Fehler in eine Form bringen.** Der Server antwortet mit
 *    {code, params, field, message}. Uebersetzt wird bevorzugt HIER, aus
 *    errors.<code> mit den Parametern; `message` ist nur der Ausweg fuer einen
 *    Code, den der Katalog nicht kennt (aelterer Server, neuer Code).
 */

import { getLocale, hasKey, t } from "./i18n.js";

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

export async function postJson(url, body, { signal } = {}) {
    const response = await fetch(url, {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify(body),
        signal,
    });
    return unwrap(response);
}

export async function uploadPhoto(file) {
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
 * Der Export liefert kein JSON, sondern das PDF - samt Seitenzahl und
 * Seitenformat in den Kopfzeilen. Deshalb kann er nicht durch postJson.
 */
export async function exportPdf(body) {
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
