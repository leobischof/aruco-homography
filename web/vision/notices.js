/**
 * notices.js - Vokabular fuer Warnungen und Abbrueche, wie app/notices.py.
 *
 * Code und benannte Parameter, KEIN fertiger Satz (AGENTS.md, Invariante 7).
 * Der Satz entsteht erst am Rand: die Oberflaeche uebersetzt `errors.<code>`
 * und `notices.<code>` aus demselben Katalog, den auch Python liest.
 *
 * Warum das hier trotzdem eine `message` mitgibt: die Antwortform ist die des
 * Servers, und der schickt sie mit (app/main.py::handle_app_error). Die
 * Oberflaeche zieht ihren eigenen Katalog vor und benutzt `message` nur als
 * Ausweg fuer einen Code, den sie nicht kennt - also darf sie nicht fehlen,
 * sonst saehe ein unbekannter Code im Ortsbetrieb anders aus als am Server.
 */

/** Ein Abbruch mit Code, Feldbezug und Parametern - das Gegenstueck zu AppError. */
export class AppError extends Error {
    constructor(code, fieldName = null, params = {}) {
        super(code);
        this.name = "AppError";
        this.code = code;
        this.field = fieldName;
        this.params = params;
    }

    /** Die Drahtform, die api.js::describeError erwartet. */
    toPayload(translate) {
        return {
            code: this.code,
            params: { ...this.params },
            field: this.field,
            message: translate(`errors.${this.code}`, this.params),
        };
    }
}

/** Sammler, damit Rechenschritte Warnungen anhaengen koennen, ohne sie zu kennen. */
export class NoticeList {
    constructor() {
        this.items = [];
    }

    warn(code, params = {}) {
        this.items.push({ code, params, severity: "warn" });
    }

    info(code, params = {}) {
        this.items.push({ code, params, severity: "info" });
    }

    asDicts(translate) {
        return this.items.map((notice) => ({
            code: notice.code,
            params: { ...notice.params },
            severity: notice.severity,
            message: translate(`notices.${notice.code}`, notice.params),
        }));
    }
}
