/**
 * main.js - die Schrittfolge und ihre Verdrahtung.
 *
 * Diese Datei rechnet nichts und zeichnet nichts. Sie haelt den Zustand der
 * Sitzung, ruft die Bausteine (i18n, theme, api, crop-rect, adjust, report) und
 * schaltet die sechs Abschnitte frei, sobald sie etwas zu zeigen haben.
 *
 * Der Zustand haelt bewusst die ROHEN Serverantworten. Der Grund steht in
 * rerender(): bei einem Sprachwechsel muss auch der schon gezeichnete Text neu
 * entstehen - Bericht, Bildangaben, Exportmeldung. Wer nur die fertigen
 * Zeichenketten behaelt, kann sie nicht mehr uebersetzen und braucht ein
 * Neuladen der Seite. Genau das soll der Schalter im Kopf nicht.
 */

import { createAdjustPanel } from "./adjust.js";
import { describeError, exportPdf, postJson, uploadPhoto } from "./api.js";
import { renderCropInfo } from "./crop-info.js";
import { createCropRect } from "./crop-rect.js";
import { createFilePicker } from "./file-picker.js";
import { createHeader } from "./header.js";
import { formatNumber, initI18n, onLocaleChange, richText, t, getLocale } from "./i18n.js";
import { renderReport } from "./report.js";
import { initTheme } from "./theme.js";

const el = (id) => document.getElementById(id);
const CROP_KEYS = ["x0", "y0", "x1", "y1"];
const PDF_NAME = "schablone.pdf";

const state = {
    sessionId: null,
    upload: null,
    solve: null,
    crop: null,
    exportResult: null,
};

let cropRect = null;
let adjustPanel = null;
let header = null;

// --- Warten und Fehler -------------------------------------------------------

// Der Schluessel, nicht der fertige Satz: waehrend eine Anfrage laeuft, laesst
// sich die Sprache umstellen, und der Schleier bliebe sonst in der alten stehen.
let busyKey = null;

function busy(key) {
    busyKey = key;
    el("busy-text").textContent = t(key);
    el("busy").hidden = false;
}

function idle() {
    busyKey = null;
    el("busy").hidden = true;
}

/** Fehler gehoeren in die Seite, nicht in ein alert(): dort kann man sie lesen,
    vergleichen und stehen lassen, waehrend man den Wert korrigiert. */
function showError(slotId, error) {
    const notice = document.createElement("div");
    notice.className = "notice notice-error";
    notice.textContent = describeError(error);
    el(slotId).replaceChildren(notice);
}

function clearError(slotId) {
    el(slotId).replaceChildren();
}

// --- Schritt 1: Foto ---------------------------------------------------------

async function handleUpload(file) {
    clearError("upload-error");
    busy("ui.busy.upload");
    try {
        const payload = await uploadPhoto(file);
        state.sessionId = payload.session_id;
        state.upload = payload;
        applyDefaults(payload.defaults);
        renderUploadInfo();
        el("step-params").hidden = false;
    } catch (error) {
        showError("upload-error", error);
    } finally {
        idle();
    }
}

function renderUploadInfo() {
    const payload = state.upload;
    if (!payload) return;

    const summary = document.createElement("div");
    summary.append(
        richText(
            "ui.steps.upload.summary",
            { filename: payload.filename, width: payload.width, height: payload.height },
            ["filename"]
        )
    );

    const focal = payload.exif && payload.exif.focal35_mm;
    const exif = document.createElement("div");
    exif.textContent = focal
        ? t("ui.steps.upload.exif_focal", { focal_mm: formatNumber(focal, 0) })
        : t("ui.steps.upload.exif_missing");

    const info = el("upload-info");
    info.replaceChildren(summary, exif);
    info.hidden = false;
}

/** Die Vorgabewerte kommen vom Server - app/config.py ist die einzige Quelle. */
function applyDefaults(defaults) {
    el("marker-mm").value = defaults.marker_mm;
    el("spacing-x").value = defaults.spacing_x_mm;
    el("spacing-y").value = defaults.spacing_y_mm;
    el("overlap").value = defaults.overlap_mm;
    renderDpiOptions(defaults.dpi_choices, defaults.dpi);
    header.syncSheetLink();
}

/** Die Auflösungsliste. Die bisherige Auswahl ueberlebt ein Neuzeichnen -
    sonst wuerde ein Sprachwechsel die Wahl des Benutzers zuruecksetzen. */
function renderDpiOptions(choices, fallback) {
    const select = el("dpi");
    const previous = select.value || String(fallback);
    select.replaceChildren(
        ...choices.map((dpi) => {
            const option = document.createElement("option");
            option.value = String(dpi);
            option.textContent = t("ui.steps.export.dpi_option", { dpi });
            return option;
        })
    );
    select.value = choices.map(String).includes(previous) ? previous : String(fallback);
}

// --- Schritt 2: Entzerren ----------------------------------------------------

async function handleSolve() {
    clearError("params-error");
    busy("ui.busy.solve");
    try {
        const cameraHeight = parseFloat(el("camera-height").value);
        state.solve = await postJson("/api/solve", {
            session_id: state.sessionId,
            marker_mm: parseFloat(el("marker-mm").value),
            mode: el("mode").value,
            thickness_mm: parseFloat(el("thickness").value) || 0,
            camera_height_mm: Number.isFinite(cameraHeight) ? cameraHeight : null,
            spacing_x_mm: parseFloat(el("spacing-x").value),
            spacing_y_mm: parseFloat(el("spacing-y").value),
        });

        renderReport(el("report"), el("warnings"), state.solve);
        el("preview").src = state.solve.preview.url;
        cropRect.setScene({
            extent: state.solve.preview.extent_mm,
            hull: state.solve.hull_mm,
            crop: state.solve.default_crop_mm,
        });

        for (const id of ["step-report", "step-adjust", "step-crop", "step-export"]) {
            el(id).hidden = false;
        }
        // Der Reglerstand ueberlebt ein erneutes Entzerren; damit Bild und
        // Regler wieder zueinander passen, wird die Vorschau nachgezogen.
        adjustPanel.refresh();
    } catch (error) {
        showError("params-error", error);
    } finally {
        idle();
    }
}

/** Im Frei-Modus sind die Blattabstaende bedeutungslos - dann verschwinden sie. */
function updateModeFields() {
    const isSheet = el("mode").value === "sheet";
    for (const element of document.querySelectorAll(".sheet-only")) {
        element.hidden = !isSheet;
    }
}

/** Papierformat und Ueberlappung gelten nur fuer die Kachelung. */
function updateLayoutFields() {
    const tiled = el("layout").value === "tiles";
    for (const element of document.querySelectorAll(".tiles-only")) {
        element.hidden = !tiled;
    }
}

// --- Schritte 4 und 5: Aufbereitung und Zuschnitt ----------------------------

function onCropChange(crop) {
    state.crop = crop;
    for (const key of CROP_KEYS) {
        const input = el(key);
        // Das Feld, in dem gerade getippt wird, bleibt unangetastet - sonst
        // schreibt die Rueckmeldung dem Benutzer mitten ins Wort.
        if (document.activeElement !== input) input.value = crop[key].toFixed(1);
    }
    updateCropInfo();
}

function updateCropInfo() {
    if (!state.solve) return;
    renderCropInfo(el("crop-info"), {
        crop: state.crop,
        hull: state.solve.hull_mm,
        dpi: parseInt(el("dpi").value || "300", 10),
        limits: state.solve.limits,
    });
}

function onCropInput() {
    const next = {};
    for (const key of CROP_KEYS) next[key] = parseFloat(el(key).value);
    if (Object.values(next).every(Number.isFinite)) cropRect.setCrop(next);
}

// --- Schritt 6: Druck --------------------------------------------------------

async function handleExport() {
    clearError("export-error");
    busy("ui.busy.export");
    try {
        const result = await exportPdf({
            session_id: state.sessionId,
            crop_mm: state.crop,
            dpi: parseInt(el("dpi").value, 10),
            layout: el("layout").value,
            page_format: el("page-format").value,
            overlap_mm: parseFloat(el("overlap").value) || 0,
            overlays: {
                scalebar: el("ov-scalebar").checked,
                grid: el("ov-grid").checked,
                footer: el("ov-footer").checked,
                marks: el("ov-marks").checked,
            },
            tile_overview: el("ov-overview").checked,
            contour: el("ov-contour").checked,
            // Dieselben Regler, die die Vorschau erzeugt haben: was man sieht,
            // wird gedruckt.
            adjust: adjustPanel.read(),
            // Die Aufdrucke im PDF sollen der Sprache der Oberflaeche folgen,
            // nicht der Vorgabesprache des Servers.
            locale: getLocale(),
            filename: PDF_NAME,
        });

        download(result.blob, PDF_NAME);
        state.exportResult = result;
        renderExportInfo();
    } catch (error) {
        showError("export-error", error);
    } finally {
        idle();
    }
}

function download(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    // Erst freigeben, wenn der Browser den Klick verarbeitet hat. Sofortiges
    // revokeObjectURL laesst den Download in manchen Browsern ins Leere laufen.
    setTimeout(() => URL.revokeObjectURL(url), 0);
}

function renderExportInfo() {
    const result = state.exportResult;
    if (!result) return;

    const summary = document.createElement("div");
    summary.append(
        richText(
            "ui.steps.export.result",
            { pages: result.pages, page_size: result.pageSize },
            ["pages", "page_size"]
        )
    );

    const hint = document.createElement("div");
    hint.append(
        richText(
            "ui.steps.export.result_hint",
            { emphasis: t("ui.steps.export.result_emphasis") },
            ["emphasis"]
        )
    );

    el("export-info").replaceChildren(summary, hint);
}

// --- Sprachwechsel -----------------------------------------------------------

/**
 * Alles, was aus Daten entstanden ist, neu entstehen lassen.
 *
 * applyTranslations() erneuert nur Text, der im Markup mit data-i18n
 * ausgezeichnet ist. Bericht, Bildangaben und Exportmeldung baut das Skript -
 * die muessen hier von Hand nachgezogen werden, sonst bleibt die halbe Seite in
 * der alten Sprache stehen.
 */
function rerender() {
    if (busyKey) el("busy-text").textContent = t(busyKey);
    if (state.upload) {
        renderUploadInfo();
        renderDpiOptions(state.upload.defaults.dpi_choices, state.upload.defaults.dpi);
    }
    if (state.solve) {
        renderReport(el("report"), el("warnings"), state.solve);
        updateCropInfo();
    }
    if (state.exportResult) renderExportInfo();
}

// --- Aufbau ------------------------------------------------------------------

async function start() {
    initTheme();
    // Erst der Katalog, dann alles, was Text baut: die Regler bekommen ihre
    // Beschriftung beim Erzeugen, nicht nachtraeglich.
    await initI18n();

    header = createHeader({
        themeButton: el("theme-toggle"),
        langSelect: el("lang-select"),
        sheetLink: el("sheet-link"),
        getSheetParams: () => ({
            marker_mm: parseFloat(el("marker-mm").value),
            spacing_x_mm: parseFloat(el("spacing-x").value),
            spacing_y_mm: parseFloat(el("spacing-y").value),
        }),
    });

    cropRect = createCropRect({ canvas: el("overlay"), onChange: onCropChange });

    adjustPanel = createAdjustPanel({
        container: el("adjust-controls"),
        busy: el("adjust-busy"),
        getSessionId: () => state.sessionId,
        onPreview: (preview) => {
            el("preview").src = preview.url;
        },
        onError: (error) => showError("adjust-error", error),
    });

    // Die Dateiwahl bringt ihre eigene Beschriftung mit - das native Feld
    // beschriftet sich in der Sprache des Browsers und liesse sich sonst nicht
    // uebersetzen (siehe file-picker.js).
    createFilePicker({
        input: el("file"),
        cameraInput: el("camera"),
        dropZone: el("file-drop"),
        nameOutput: el("file-name"),
        onFile: handleUpload,
    });

    el("solve").addEventListener("click", handleSolve);
    el("export").addEventListener("click", handleExport);
    el("adjust-reset").addEventListener("click", () => adjustPanel.reset());

    el("mode").addEventListener("change", updateModeFields);
    el("layout").addEventListener("change", updateLayoutFields);
    el("dpi").addEventListener("change", updateCropInfo);

    for (const id of ["marker-mm", "spacing-x", "spacing-y"]) {
        el(id).addEventListener("change", header.syncSheetLink);
    }
    for (const key of CROP_KEYS) {
        el(key).addEventListener("change", onCropInput);
    }

    // Das Bild bestimmt die Groesse der Buehne; erst wenn es steht, kann das
    // Overlay deckungsgleich gezeichnet werden.
    el("preview").addEventListener("load", () => cropRect.redraw());

    onLocaleChange(rerender);
    updateModeFields();
    updateLayoutFields();
}

start();
