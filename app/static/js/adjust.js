/**
 * adjust.js - die Regler der Bildaufbereitung samt Live-Vorschau.
 *
 * Die Feldnamen und Wertebereiche unten sind KEINE Erfindung dieser Datei: sie
 * spiegeln `AdjustOptions` in app/vision/enhance.py, und app/schemas.py spiegelt
 * dieselbe Klasse fuer die Leitung. Wer dort einen Regler hinzufuegt, ergaenzt
 * ihn hier - ein Feld, das der Server nicht kennt, wird von Pydantic verworfen.
 *
 * Derselbe Reglerstand geht in /api/adjust (Vorschau) UND in /api/export
 * (Druck). Das ist der ganze Punkt der Vorschau: was man sieht, wird gedruckt.
 *
 * Zwei Dinge, die eine Live-Vorschau ohne sie unbrauchbar machen:
 *
 * 1. **Entprellen.** Ein Schieberegler feuert bei jedem Pixel. Ohne Wartezeit
 *    schickt ein Zug ueber die halbe Spur dutzende Anfragen, und der Server
 *    rechnet jede davon.
 * 2. **Veraltete Antworten verwerfen.** Anfragen koennen sich ueberholen. Ohne
 *    Wachnummer gewinnt die LANGSAMSTE Antwort das Bild - der Regler steht dann
 *    auf einem Wert und das Bild zeigt einen anderen.
 */

import { postJson } from "./api.js";
import { formatNumber, onLocaleChange, t } from "./i18n.js";

const DEBOUNCE_MS = 200;

/**
 * Die Regler in ihrer Reihenfolge auf dem Bildschirm. `stem` ist der Rumpf der
 * Katalogschluessel (ui.adjust.<stem>_label / _hint) - er weicht bei der
 * Farbbetonung ab, weil das Feld auf der Leitung `color_emphasis` heisst, der
 * Katalog aber `emphasis_*` fuehrt.
 */
const CONTROLS = [
    { field: "grayscale", stem: "grayscale", type: "check" },
    { field: "invert", stem: "invert", type: "check" },
    { field: "brightness", stem: "brightness", type: "range", min: -1, max: 1 },
    { field: "contrast", stem: "contrast", type: "range", min: -1, max: 1 },
    { field: "saturation", stem: "saturation", type: "range", min: -1, max: 1 },
    { field: "local_contrast", stem: "local_contrast", type: "range", min: 0, max: 1 },
    { field: "edge_boost", stem: "edge_boost", type: "range", min: 0, max: 1 },
    { field: "edge_overlay", stem: "edge_overlay", type: "range", min: 0, max: 1 },
    {
        field: "color_emphasis",
        stem: "emphasis",
        type: "select",
        // Muss zu config.ADJUST_EMPHASIS_HUES passen, plus "none".
        options: ["none", "red", "yellow", "green", "cyan", "blue", "magenta"],
    },
    { field: "emphasis_strength", stem: "emphasis_strength", type: "range", min: 0, max: 1 },
    { field: "threshold", stem: "threshold", type: "range", min: 0, max: 1 },
];

const STEP = 0.02;

function neutralValues() {
    const values = {};
    for (const control of CONTROLS) {
        if (control.type === "check") values[control.field] = false;
        else if (control.type === "select") values[control.field] = "none";
        else values[control.field] = 0;
    }
    return values;
}

/**
 * @param {object} options
 * @param {HTMLElement} options.container   Wohin die Regler gebaut werden
 * @param {HTMLElement} options.busy        Der kleine Drehring
 * @param {Function} options.getSessionId   Liefert die aktuelle Sitzung oder null
 * @param {Function} options.onPreview      Bekommt {url, extent_mm, px_per_mm}
 * @param {Function} options.onError        Bekommt einen Serverfehler
 */
export function createAdjustPanel({ container, busy, getSessionId, onPreview, onError }) {
    const values = neutralValues();
    const inputs = new Map();
    const readouts = new Map();

    // Solange die Route fehlt (der Server wird gerade nachgezogen), bleiben die
    // Regler bedienbar und wirken beim Export - nur die Live-Vorschau schweigt.
    let previewAvailable = true;
    let timer = null;
    let sequence = 0;

    function labelFor(control) {
        return t(`ui.adjust.${control.stem}_label`);
    }

    function buildCheck(control) {
        // Nur ".check": die Zeile ist waagerecht (Kaestchen, dann Text), waehrend
        // .adjust-control eine Spalte ist - beide zusammen wuerde die Spalte
        // gewinnen und das Kaestchen ueber seine Beschriftung setzen.
        const wrapper = document.createElement("label");
        wrapper.className = "check";

        const input = document.createElement("input");
        input.type = "checkbox";
        const text = document.createElement("span");
        text.dataset.i18n = `ui.adjust.${control.stem}_label`;
        text.textContent = labelFor(control);
        wrapper.dataset.i18nAttr = `title:ui.adjust.${control.stem}_hint`;
        wrapper.title = t(`ui.adjust.${control.stem}_hint`);

        input.addEventListener("change", () => {
            values[control.field] = input.checked;
            schedule();
        });

        wrapper.append(input, text);
        inputs.set(control.field, input);
        return wrapper;
    }

    function buildRange(control) {
        const wrapper = document.createElement("div");
        wrapper.className = "adjust-control";

        const head = document.createElement("div");
        head.className = "slider-head";

        const label = document.createElement("label");
        label.dataset.i18n = `ui.adjust.${control.stem}_label`;
        label.className = "field-label";
        label.textContent = labelFor(control);

        const readout = document.createElement("span");
        readout.className = "slider-value";

        const input = document.createElement("input");
        input.type = "range";
        input.className = "slider";
        input.min = String(control.min);
        input.max = String(control.max);
        input.step = String(STEP);
        input.value = "0";
        // Der Regler traegt seine Beschriftung selbst - <label for> braeuchte
        // eine erfundene id, und die Beschriftung steht ohnehin daneben.
        input.setAttribute("aria-label", labelFor(control));
        input.dataset.i18nAttr = `aria-label:ui.adjust.${control.stem}_label,title:ui.adjust.${control.stem}_hint`;
        input.title = t(`ui.adjust.${control.stem}_hint`);

        input.addEventListener("input", () => {
            values[control.field] = Number(input.value);
            renderReadout(control);
            schedule();
        });

        const hint = document.createElement("small");
        hint.className = "field-hint";
        hint.dataset.i18n = `ui.adjust.${control.stem}_hint`;
        hint.textContent = t(`ui.adjust.${control.stem}_hint`);

        head.append(label, readout);
        wrapper.append(head, input, hint);
        inputs.set(control.field, input);
        readouts.set(control.field, readout);
        renderReadout(control);
        return wrapper;
    }

    function buildSelect(control) {
        const wrapper = document.createElement("label");
        wrapper.className = "adjust-control field";

        const label = document.createElement("span");
        label.className = "field-label";
        label.dataset.i18n = `ui.adjust.${control.stem}_label`;
        label.textContent = labelFor(control);

        const select = document.createElement("select");
        for (const option of control.options) {
            const item = document.createElement("option");
            item.value = option;
            item.dataset.i18n = `ui.adjust.${control.stem}_${option}`;
            item.textContent = t(`ui.adjust.${control.stem}_${option}`);
            select.append(item);
        }
        select.addEventListener("change", () => {
            values[control.field] = select.value;
            schedule();
        });

        const hint = document.createElement("small");
        hint.className = "field-hint";
        hint.dataset.i18n = `ui.adjust.${control.stem}_hint`;
        hint.textContent = t(`ui.adjust.${control.stem}_hint`);

        wrapper.append(label, select, hint);
        inputs.set(control.field, select);
        return wrapper;
    }

    /** Der Zahlenwert neben dem Regler - Ziffern, aber in der Landesschreibweise. */
    function renderReadout(control) {
        const readout = readouts.get(control.field);
        if (!readout) return;
        const value = values[control.field];
        // Vorzeichen nur, wo der Bereich negativ werden kann: bei 0..1 waere ein
        // "+" vor jeder Zahl nur Laerm.
        const sign = control.min < 0 && value > 0 ? "+" : "";
        readout.textContent = sign + formatNumber(value, 2);
    }

    function renderReadouts() {
        for (const control of CONTROLS) renderReadout(control);
    }

    function setBusy(active) {
        if (busy) busy.hidden = !active;
    }

    function schedule() {
        if (!previewAvailable) return;
        if (timer !== null) clearTimeout(timer);
        timer = setTimeout(send, DEBOUNCE_MS);
    }

    async function send() {
        timer = null;
        const sessionId = getSessionId();
        if (!sessionId) return;

        const ticket = ++sequence;
        setBusy(true);
        try {
            const payload = await postJson("/api/adjust", {
                session_id: sessionId,
                adjust: { ...values },
            });
            // Eine neuere Anfrage ist schon unterwegs: diese Antwort ist Schnee
            // von gestern und darf das Bild nicht mehr anfassen.
            if (ticket !== sequence) return;
            if (payload && payload.preview) onPreview(payload.preview);
        } catch (error) {
            if (ticket !== sequence) return;
            // "Route gibt es nicht" (der Server wird gerade nachgezogen, und die
            // statische Auslieferung unter / beantwortet ein unbekanntes
            // /api/adjust mit 404/405): dann endgueltig still werden. Die Regler
            // bleiben bedienbar und wirken beim Export.
            const message = error && typeof error.message === "string" ? error.message : "";
            if (/HTTP 40[45]/.test(message)) {
                previewAvailable = false;
                console.warn("Live-Vorschau nicht verfuegbar", error);
                return;
            }
            // Netzausfall o. ae.: keine Meldung an den Regler haengen, aber auch
            // nicht aufgeben - der naechste Zug versucht es wieder.
            if (!error || !error.code) {
                console.warn("Vorschau fehlgeschlagen", error);
                return;
            }
            if (onError) onError(error);
        } finally {
            if (ticket === sequence) setBusy(false);
        }
    }

    container.replaceChildren(
        ...CONTROLS.map((control) => {
            if (control.type === "check") return buildCheck(control);
            if (control.type === "select") return buildSelect(control);
            return buildRange(control);
        })
    );

    // Der Zahlenwert ist kein Katalogtext, folgt der Sprache aber trotzdem
    // (Komma statt Punkt) - applyTranslations kann ihn also nicht erneuern.
    onLocaleChange(renderReadouts);

    return {
        /** Der Reglerstand fuer /api/adjust und /api/export. */
        read() {
            return { ...values };
        },
        /**
         * Vorschau neu anfordern, ohne einen Regler zu bewegen.
         *
         * Gebraucht nach einem erneuten Entzerren: dort entsteht ein frisches
         * Vorschaubild aus dem ROHEN Bild, die Regler stehen aber noch. Ohne
         * diesen Anstoss zeigte das Bild etwas anderes als die Regler sagen.
         */
        refresh() {
            schedule();
        },
        /** Alles zurueck auf neutral - das Bild kommt dann unveraendert. */
        reset() {
            Object.assign(values, neutralValues());
            for (const control of CONTROLS) {
                const input = inputs.get(control.field);
                if (!input) continue;
                if (control.type === "check") input.checked = false;
                else input.value = control.type === "select" ? "none" : "0";
            }
            renderReadouts();
            schedule();
        },
    };
}
