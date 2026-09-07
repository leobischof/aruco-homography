/**
 * errors.js - Abbruchfehler mit Code und Parametern, KEIN fertiger Satz.
 *
 * Das Gegenstueck zu `AppError` aus app/notices.py. Es liegt hier und nicht in
 * einem eigenen `web/notices.js`, weil in dieser Stufe nur die PDF-Schicht
 * portiert wird; zieht spaeter die Oberflaeche nach, wandert die Klasse mit nach
 * oben und dieses Modul verschwindet.
 *
 * Der Text entsteht erst am Rand aus dem Katalog (AGENTS.md, Invariante 7) -
 * deshalb traegt der Fehler nur `code`, `fieldName` und benannte Parameter. Die
 * `message` der Exception ist der Code selbst, damit ein durchgereichter Fehler
 * in einem Protokoll wenigstens seinen Schluessel nennt.
 */

export class AppError extends Error {
    constructor(code, fieldName = null, params = {}) {
        super(code);
        this.name = "AppError";
        this.code = code;
        this.fieldName = fieldName;
        this.params = params;
    }
}
