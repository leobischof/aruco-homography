/**
 * app.js - die Verdrahtung der Android-Startseite.
 *
 * Sie rechnet nichts. Jede Zahl auf dieser Seite kommt entweder aus dem nativen
 * Kern (ueber window.__aruco, siehe bridge-shim.js) oder aus shared/constants.json.
 * Eine hier ausgerechnete Millimeterzahl waere eine vierte Fassung derselben
 * Messtechnik - neben Python, C++ und dem, was noch kommt.
 *
 * Geliehen wird alles, was es schon gibt: das Sprachmodul der Oberflaeche
 * (/js/i18n.js), ihr Themenschalter (/js/theme.js) und ihre Stilvorlagen. Diese
 * Datei bringt nur die Knoepfe mit, die es auf dem Rechner nicht gibt.
 */

import {
    applyTranslations, formatNumber, getLocale, getLocales, initI18n, onLocaleChange, setLocale, t,
} from "/js/i18n.js";
import { effectiveTheme, initTheme, onThemeChange, toggleTheme } from "/js/theme.js";

const el = (id) => document.getElementById(id);
const bridge = window.__aruco;

/** Ein Textabsatz mit Klasse - die Seite baut ihre Ausgaben aus diesen. */
function line(text, className = "") {
    const node = document.createElement("p");
    if (className) node.className = className;
    node.textContent = text;
    return node;
}

/**
 * Einen Fehler zeigen, statt ihn in die Konsole zu schreiben.
 *
 * Auf einem Telefon gibt es keine Konsole, die jemand aufklappt. Was hier
 * schiefgeht, muss auf der Seite stehen - sonst sieht der Bediener einen Knopf,
 * der nichts tut.
 */
function showError(target, error) {
    target.replaceChildren(line(String((error && error.message) || error), "error-slot"));
}

/** Einen Knopf waehrend einer langen Arbeit sperren und beschriften. */
async function whileBusy(button, busyKey, work) {
    const original = button.textContent;
    button.disabled = true;
    button.textContent = t(busyKey);
    try {
        return await work();
    } finally {
        button.disabled = false;
        button.textContent = original;
    }
}

// --- 1 · Der Kern ------------------------------------------------------------

function renderNativeInfo() {
    const list = el("native-info");
    const problem = el("native-error");
    list.replaceChildren();

    if (!bridge || !bridge.available) {
        problem.hidden = false;
        problem.textContent = "AndroidCore fehlt - diese Seite laeuft nicht in der App.";
        return;
    }

    let info;
    try {
        info = bridge.info();
    } catch (error) {
        problem.hidden = false;
        problem.textContent = String(error.message || error);
        return;
    }
    problem.hidden = true;

    // Die Beschriftungen: technische Eigennamen bleiben stehen (OpenCV, ABI,
    // Android, WebView - die uebersetzt niemand), der Rest kommt aus dem Katalog.
    const rows = [
        ["OpenCV", info.opencv],
        [t("ui.android.native_dictionary"), `${info.dictionary} (${info.dictionary_size})`],
        [t("ui.android.native_marker_mm"), `${formatNumber(info.marker_mm_nominal, 1)} mm`],
        ["ABI", info.abi],
        [t("ui.android.native_page_size"), `${info.page_size} B`],
        [t("ui.android.native_output_budget"), outputBudgetLine(info)],
        [t("ui.android.native_device"), `${info.device} · Android ${info.android} (API ${info.sdk})`],
        ["WebView", info.webview],
        [t("ui.android.native_app"), info.app_version],
    ];
    for (const [name, value] of rows) {
        const term = document.createElement("dt");
        term.textContent = name;
        const definition = document.createElement("dd");
        definition.textContent = value;
        list.append(term, definition);
    }
}

// --- 2 · Pruefstand ----------------------------------------------------------

el("run-conformance").addEventListener("click", async (event) => {
    const out = el("conformance-out");
    out.replaceChildren();
    try {
        const report = await whileBusy(event.currentTarget, "ui.android.conformance_running",
            () => bridge.runConformance(false));

        const verdict = line(
            report.passed ? t("ui.android.conformance_passed") : t("ui.android.conformance_failed"),
            `verdict ${report.passed ? "pass" : "fail"}`,
        );
        out.append(verdict);

        for (const scene of report.scenes) {
            out.append(line(
                `${scene.scene}: ${t("ui.android.conformance_worst")} `
                + `${formatNumber(scene.worst_corner_px, 4)} px `
                + `(${t("ui.android.conformance_tolerance")} `
                + `${formatNumber(scene.tolerance_px, 4)} px), `
                + `${scene.markers_found}/${scene.markers_expected}, ${scene.elapsed_ms} ms`,
            ));
            // Die Pruefsumme der dekodierten Pixel. Sie beantwortet die einzige
            // Frage, die dieser Lauf sonst offenliesse: hat Androids PNG-Dekoder
            // dieselben Bytes geliefert wie cv2 auf dem Rechner? Der Vergleichswert
            // steht in docs/cpp-migration/stage-4-android.md.
            out.append(line(
                `${t("ui.android.conformance_checksum")}: ${scene.pixels_sha256_rgb}`, "mono",
            ));
        }
    } catch (error) {
        showError(out, error);
    }
});

// --- 3 · Detektor am Foto ----------------------------------------------------

let photoLoaded = false;

function renderPhoto(photo) {
    photoLoaded = true;
    el("run-detect").disabled = false;
    const out = el("detect-out");
    out.replaceChildren(line(
        `${photo.filename} · ${photo.width}x${photo.height} px`
        + (photo.exif_rotation_deg ? ` · EXIF ${photo.exif_rotation_deg} deg` : "")
        + (photo.focal35_mm ? ` · ${formatNumber(photo.focal35_mm, 0)} mm (KB)` : "")
        + (photo.camera_model ? ` · ${photo.camera_model}` : ""),
    ));
}

el("pick-photo").addEventListener("click", async () => {
    try {
        renderPhoto(await bridge.pickPhoto());
    } catch (error) {
        showError(el("detect-out"), error);
    }
});

el("take-photo").addEventListener("click", async () => {
    try {
        renderPhoto(await bridge.takePhoto());
    } catch (error) {
        showError(el("detect-out"), error);
    }
});

el("run-detect").addEventListener("click", async (event) => {
    if (!photoLoaded) return;
    const out = el("detect-out");
    try {
        const result = await whileBusy(event.currentTarget, "ui.android.detect_running",
            () => bridge.detectMarkers(true));

        out.replaceChildren();
        if (result.markers.length === 0) {
            out.append(line(t("ui.android.detect_none")));
            return;
        }
        out.append(line(t("ui.android.detect_found", {
            count: result.markers.length, ms: result.elapsed_ms,
        })));
        for (const marker of result.markers) {
            out.append(line(
                `#${marker.id} · ${t("ui.android.detect_edge")} `
                + `${formatNumber(meanEdgePx(marker.corners_px), 2)} px`,
            ));
        }
    } catch (error) {
        showError(out, error);
    }
});

/**
 * Die mittlere Kantenlaenge eines Markers in Pixeln.
 *
 * Das ist KEINE Messung im Sinne dieses Projekts - es sind Pixel, keine
 * Millimeter, und es steckt kein Ausgleich dahinter. Es steht hier, weil es die
 * eine Zahl ist, an der man auf einen Blick sieht, ob der Fund plausibel ist:
 * vier Marker gleicher Groesse auf einem Blatt muessen aehnlich grosse Kanten
 * haben. Weicht einer stark ab, war es kein Marker.
 */
function meanEdgePx(corners) {
    let sum = 0;
    for (let index = 0; index < 4; index += 1) {
        const [x1, y1] = corners[index];
        const [x2, y2] = corners[(index + 1) % 4];
        sum += Math.hypot(x2 - x1, y2 - y1);
    }
    return sum / 4;
}

// --- 4 · Markerblatt ---------------------------------------------------------

/** Das Blatt bauen - aus web/pdf/, mit den Modulbits des nativen Kerns. */
async function buildMarkersheetBytes() {
    const [{ buildMarkersheet, MODULES }, constants] = await Promise.all([
        import("/web/pdf/markersheet.js"),
        import("/shared/constants.json", { with: { type: "json" } }).then((m) => m.default),
    ]);
    return buildMarkersheet({
        markerBits: (id) => Uint8Array.from(bridge.markerBits(id, MODULES)),
        locale: document.documentElement.lang || constants.DEFAULT_LOCALE,
    });
}

async function withSheet(button, action) {
    const out = el("sheet-out");
    out.replaceChildren();
    try {
        // ui.busy.export ("Erzeuge PDF ..."), nicht ein eigener Schluessel: die
        // Oberflaeche sagt dasselbe schon, und ein zweiter Text fuer denselben
        // Vorgang waere eine zweite Formulierung, die auseinanderlaeuft.
        const bytes = await whileBusy(button, "ui.busy.export",
            async () => buildMarkersheetBytes());
        await action(bytes);
        out.append(line(t("ui.android.sheet_saved")));
    } catch (error) {
        showError(out, error);
    }
}

el("save-sheet").addEventListener("click", (event) =>
    withSheet(event.currentTarget, (bytes) => bridge.savePdf(bytes, "markerblatt_A4.pdf")));

el("share-sheet").addEventListener("click", (event) =>
    withSheet(event.currentTarget, (bytes) => bridge.sharePdf(bytes, "markerblatt_A4.pdf")));

// --- 5 · Die vollstaendige Oberflaeche ---------------------------------------

el("open-full").addEventListener("click", () => {
    // Ueber die Bruecke und nicht per location.href: der Java-Teil kennt den
    // Ursprung, und ein hier zusammengesetzter Pfad waere eine zweite Stelle, an
    // der die Adresse steht.
    if (bridge && bridge.navigate) bridge.navigate("/index.html");
    else window.location.href = "/index.html";
});

// --- Kopfzeile ---------------------------------------------------------------

/**
 * Sprachwahl und Themenknopf verdrahten.
 *
 * Bewusst NICHT ueber js/header.js: jenes Modul ist um den Anker zum Markerblatt
 * herum gebaut (es zieht dessen ?locale= bei jedem Sprachwechsel nach), und
 * genau diesen Anker gibt es hier nicht - auf einem Telefon muss man zwischen
 * "speichern" und "teilen" waehlen, und das kann ein Link nicht. Was dort
 * wirklich Arbeit macht - getLocales, setLocale, toggleTheme - wird trotzdem
 * benutzt und nicht nachgebaut.
 */
function wireHeader() {
    const languages = el("lang-select");
    const themeButton = el("theme-toggle");

    languages.replaceChildren(...getLocales().map(({ code, label }) => {
        const option = document.createElement("option");
        option.value = code;
        option.textContent = label;
        return option;
    }));
    languages.value = getLocale();
    languages.addEventListener("change", () => {
        setLocale(languages.value).catch((error) => {
            console.error("Sprachwechsel fehlgeschlagen", error);
            languages.value = getLocale();
        });
    });

    function syncTheme() {
        // Der Knopf zeigt, was er TUT, nicht was ist - dieselbe Regel wie in
        // js/header.js.
        const label = effectiveTheme() === "dark" ? t("ui.theme.to_light") : t("ui.theme.to_dark");
        themeButton.title = label;
        themeButton.setAttribute("aria-label", label);
    }
    themeButton.addEventListener("click", toggleTheme);
    onThemeChange(syncTheme);
    onLocaleChange(() => {
        syncTheme();
        languages.value = getLocale();
    });
    syncTheme();
}

// --- Aufbau ------------------------------------------------------------------

await initI18n();
initTheme();
wireHeader();
applyTranslations();
renderNativeInfo();

// Beim Sprachwechsel muss auch neu entstehen, was schon gezeichnet ist - die
// Tabelle oben traegt uebersetzte Beschriftungen und kein data-i18n.
onLocaleChange(() => {
    applyTranslations();
    renderNativeInfo();
});

/**
 * Was der Export hoechstens rastern darf - und ob die Zahl ueberhaupt ankam.
 *
 * Zwei Haelften muessen dafuer stimmen: NativeImages.budgetMegapixels rechnet sie
 * aus und nativeInfo() reicht sie durch (das ist `info.max_output_mpx`), und
 * bridge-shim.js setzt sie als globalThis.ARUCO_MAX_OUTPUT_MPX, woraus
 * web/constants.js::outputBudgetMpx() die kleinere von Geraete- und Produktgrenze
 * macht. Angezeigt wird die zweite - die GILT. Steht dort die Produktgrenze,
 * obwohl Java eine kleinere gemeldet hat, ist die Bruecke die Fehlerstelle.
 *
 * Ohne diese Zeile war beim Speicherfehler vom 08.09.2026 auf dem Geraet nicht
 * festzustellen, ob die Sicherung scharf war.
 */
function outputBudgetLine(info) {
    const gemeldet = Number(info.max_output_mpx);
    if (!Number.isFinite(gemeldet) || gemeldet <= 0) {
        return t("ui.android.native_output_budget_missing");
    }
    // Die zweite Haelfte: gilt die Zahl auch IN DER SEITE? bridge-shim.js setzt
    // sie beim Seitenanfang, web/constants.js liest sie beim Export. Genau das
    // war am 08.09.2026 auf dem Geraet nicht ablesbar.
    const angewandt = Number(globalThis.ARUCO_MAX_OUTPUT_MPX);
    const zahl = `${formatNumber(gemeldet, 0)} MPx`;
    if (!Number.isFinite(angewandt) || Math.abs(angewandt - gemeldet) > 0.5) {
        return `${zahl} (${t("ui.android.native_output_budget_missing")})`;
    }
    return zahl;
}
