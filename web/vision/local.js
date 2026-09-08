/**
 * local.js - der Server, den es nicht gibt.
 *
 * Dieselben vier Aufrufe wie in app/main.py - upload, solve, adjust, export -
 * nur ohne Netz. Alles laeuft in der Seite: der C++-Kern als WebAssembly, der
 * PDF-Bau aus web/pdf/, die Kataloge als statische Dateien.
 *
 * **Die Antwortformen sind Feld fuer Feld die des Servers.** Das ist die eine
 * Regel, aus der hier alles folgt: app/static/js/ bleibt unveraendert, und wer
 * pruefen will, ob beide Betriebsarten dasselbe rechnen, legt zwei JSON
 * nebeneinander. Eine "aehnliche" Antwort waere keine Pruefung mehr, sondern
 * eine Auslegungsfrage.
 *
 * Fehler kommen als dieselbe Form wie vom Server ({code, params, field,
 * message}) und werden deshalb ebenso von api.js::describeError uebersetzt.
 * Eingebettete Satzbausteine - der Aufloesungsvorschlag in `output_too_large` -
 * werden hier zu Text, genau wie i18n.plain_params es am Server tut.
 */

import * as constants from "../constants.js";
import { buildMarkersheet, MODULES } from "../pdf/markersheet.js";
import { translate } from "../pdf/i18n.js";
import { loadCore } from "./core.js";
import { readExif } from "./exif.js";
import { decodeFile } from "./image.js";
import { AppError } from "./notices.js";
import { drawDetection, PreviewUrls } from "./preview.js";
import {
    detectMarkers,
    runAdjust,
    runExport,
    runExportImage,
    runSolve,
    solveResponse,
} from "./pipeline.js";
import { exportRequest, imageRequest, solveRequest } from "./request.js";

// Genau eine Sitzung. Am Server gibt es acht, weil dort mehrere Handys auf
// denselben Rechner zeigen koennen; in einer Seite gibt es genau ein Foto, und
// ein zweites zu halten hiesse, 36 MB fuer niemanden aufzuheben.
const session = {
    id: null,
    filename: "",
    photo: null,
    markers: null,
    solve: null,
};

const previews = new PreviewUrls();
let markersheetUrl = null;

/** Kurzform: der geladene Kern. Beim ersten Aufruf wird das wasm geholt. */
function core() {
    return loadCore();
}

/**
 * Foto entgegennehmen, EXIF auswerten, Sitzung anlegen.
 *
 * EXIF wird aus den ORIGINALBYTES gelesen, bevor irgendetwas dekodiert ist -
 * der Canvas wirft die Metadaten weg (web/vision/exif.js).
 */
export async function uploadPhoto(file) {
    const sizeMb = file.size / (1024 * 1024);
    if (sizeMb > constants.MAX_UPLOAD_MB) {
        throw new AppError("upload_too_large", "file", {
            size_mb: sizeMb.toFixed(0),
            limit_mb: constants.MAX_UPLOAD_MB,
        });
    }

    const bytes = new Uint8Array(await file.arrayBuffer());
    const { focal35Mm, cameraModel } = readExif(bytes);
    const image = await decodeFile(file);

    previews.revokeAll();
    session.id = randomId();
    session.filename = file.name || "foto.jpg";
    session.photo = { image, focal35Mm, cameraModel };
    session.markers = null;
    session.solve = null;

    return {
        session_id: session.id,
        filename: session.filename,
        width: image.width,
        height: image.height,
        exif: { focal35_mm: focal35Mm, camera_model: cameraModel },
        defaults: {
            marker_mm: constants.MARKER_MM_NOMINAL,
            spacing_x_mm: constants.SHEET_SPACING_MM[0],
            spacing_y_mm: constants.SHEET_SPACING_MM[1],
            dpi: constants.DPI_DEFAULT,
            dpi_choices: [...constants.DPI_CHOICES],
            overlap_mm: constants.TILE_OVERLAP_MM_DEFAULT,
            printer_margin_mm: constants.PRINTER_MARGIN_MM_DEFAULT,
            page_margin_mm: constants.PAGE_MARGIN_MM_DEFAULT,
        },
    };
}

/**
 * Marker in EINEM Bild finden - ohne Sitzung, ohne Zustand. Fuer das Live-Bild.
 *
 * Die Sitzung bleibt ausdruecklich unberuehrt: der Sucher laeuft, bevor ein Foto
 * gewaehlt ist, und er soll ein bereits geladenes auch nicht wegwerfen. Zurueck
 * kommt Feld fuer Feld dieselbe Antwort wie von /api/detect.
 */
export async function detectFrame(blob) {
    const module = await core();
    // decodeFile nimmt alles, was createImageBitmap nimmt - ein Blob gehoert
    // dazu. Der Name stammt aus dem Upload, der Weg ist derselbe.
    const image = await decodeFile(blob);
    const markers = detectMarkers(module, { image });
    return {
        width: image.width,
        height: image.height,
        markers: markers.map((marker) => ({
            id: marker.id,
            // Der Kern liefert ACHT ZAHLEN hintereinander (x0,y0,x1,y1,...), der
            // Server vier Paare. Umgeformt wird hier, weil hier die Zusage
            // dieser Datei steht: die Antwort ist Feld fuer Feld die des
            // Servers. Ohne die Umformung fand der Sucher die Marker und
            // zeichnete nichts - der Prueflauf mit eingespielter Kamera hat
            // genau das gefunden.
            corners: [0, 1, 2, 3].map((corner) => [
                marker.corners[corner * 2],
                marker.corners[corner * 2 + 1],
            ]),
        })),
    };
}

/** Homographie bestimmen, Qualitaet bewerten, entzerrte Vorschau erzeugen. */
export async function solve(request, locale) {
    requireSession(request.session_id);
    const module = await core();
    const result = runSolve(module, session, solveRequest(request));

    const previewUrl = await previews.publish("rectified", result.preview);
    const detectedBlob = await drawDetection(session.photo.image, session.markers);
    previews.revoke("detected");
    const detectedUrl = URL.createObjectURL(detectedBlob);
    previews.urls.set("detected", detectedUrl);

    return solveResponse(session, result, module, previewUrl, detectedUrl, describe(locale));
}

/** Regler auf die entzerrte Vorschau anwenden, ohne neu zu entzerren. */
export async function adjust(request) {
    requireSession(request.session_id);
    const module = await core();
    const { kind, raster } = runAdjust(module, session, request);

    return {
        preview: {
            url: await previews.publish(kind, raster),
            extent_mm: { ...session.solve.extent },
            px_per_mm: session.solve.previewPxPerMm,
        },
    };
}

/**
 * Druckfertiges PDF erzeugen.
 *
 * Zurueck kommt, was api.js::exportPdf sonst aus den Kopfzeilen der Antwort
 * zusammensetzt: Blob, Seitenzahl und Seitenformat. Das Format wird auf drei
 * Nachkommastellen ausgegeben wie X-Page-Size-Mm - genau da liest man ab, ob
 * ein Blatt wirklich 210,000 x 297,000 mm gross ist (Invariante 1).
 */
export async function exportPdf(request) {
    requireSession(request.session_id);
    const module = await core();
    const result = await runExport(module, session, exportRequest(request));

    return {
        blob: new Blob([result.data], { type: "application/pdf" }),
        pages: String(result.pageCount),
        pageSize: `${result.pageSizeMm[0].toFixed(3)}x${result.pageSizeMm[1].toFixed(3)}`,
    };
}

/** Denselben Zuschnitt als Bilddatei. */
export async function exportImage(request) {
    requireSession(request.session_id);
    const module = await core();
    const result = await runExportImage(module, session, imageRequest(request));

    return {
        blob: new Blob([result.data], {
            type: result.format === "png" ? "image/png" : "image/jpeg",
        }),
        format: result.format,
        pixels: `${result.width}×${result.height}`,
        mmPerPx: result.mmPerPx,
    };
}

/**
 * Das A4-Markerblatt als Blob-URL.
 *
 * Am Server ist das ein gewoehnlicher Verweis auf /api/markersheet. Hier muss
 * das Blatt erst gebaut werden, also ist die URL ein Versprechen - header.js
 * setzt sie nach, sobald sie da ist. Die vorige wird freigegeben; ohne das
 * bliebe bei jedem Sprachwechsel ein PDF im Speicher liegen.
 */
export async function markersheet({ marker_mm, spacing_x_mm, spacing_y_mm, locale }) {
    const markerMm = Number.isFinite(marker_mm) ? marker_mm : constants.MARKER_MM_NOMINAL;
    const spacingX = Number.isFinite(spacing_x_mm) ? spacing_x_mm : constants.SHEET_SPACING_MM[0];
    const spacingY = Number.isFinite(spacing_y_mm) ? spacing_y_mm : constants.SHEET_SPACING_MM[1];

    if (markerMm <= 0.0 || spacingX <= 0.0 || spacingY <= 0.0) {
        throw new AppError("bad_marker_size", "marker_mm");
    }
    if (
        markerMm + spacingX > constants.SHEET_MM[0] ||
        markerMm + spacingY > constants.SHEET_MM[1]
    ) {
        throw new AppError("sheet_too_small", "spacing_x_mm", {
            marker_mm: markerMm.toFixed(0),
            spacing_x_mm: spacingX.toFixed(0),
            spacing_y_mm: spacingY.toFixed(0),
            sheet_w_mm: constants.SHEET_MM[0].toFixed(0),
            sheet_h_mm: constants.SHEET_MM[1].toFixed(0),
        });
    }

    // Die Modulbits kommen aus dem Kern - dort wohnt das Woerterbuch. Unter Node
    // holt tools/opencv_markers.mjs sie aus opencv.js; markersheet.js selbst
    // weiss von keinem der beiden Wege, es bekommt sie gereicht.
    const module = await core();
    const bytes = await buildMarkersheet({
        markerBits: (markerId) => module.markerBits(markerId, MODULES),
        markerMm,
        spacingMm: [spacingX, spacingY],
        locale,
    });
    if (markersheetUrl !== null) URL.revokeObjectURL(markersheetUrl);
    markersheetUrl = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
    return markersheetUrl;
}

/** Die waehlbaren Sprachen - dieselbe Antwort wie /api/locales. */
export function locales() {
    return {
        default: constants.DEFAULT_LOCALE,
        locales: constants.SUPPORTED_LOCALES.map((code) => ({
            code,
            // Der Name kommt aus dem Katalog DIESER Sprache: "Deutsch" heisst
            // auch in der englischen Oberflaeche "Deutsch".
            label: label(code),
        })),
    };
}

function label(code) {
    const key = `ui.language.${code}`;
    const text = translate(key, code);
    return text === key ? code.toUpperCase() : text;
}

/**
 * Einen AppError in die Drahtform bringen, die api.js erwartet.
 *
 * Eingebettete Satzbausteine ({key, params}) werden hier zu Text - dasselbe, was
 * i18n.plain_params am Server tut. Ohne diesen Schritt stuende ein Objekt in der
 * Meldung, und der Benutzer laese "[object Object]".
 */
export function errorPayload(error, locale) {
    if (!(error instanceof AppError)) {
        return { message: error && error.message ? String(error.message) : String(error) };
    }
    const params = {};
    for (const [name, value] of Object.entries(error.params)) {
        params[name] = plain(value, locale);
    }
    return {
        code: error.code,
        params,
        field: error.field,
        message: translate(`errors.${error.code}`, locale, params),
    };
}

function plain(value, locale) {
    if (value !== null && typeof value === "object" && typeof value.key === "string") {
        return translate(value.key, locale, value.params || {});
    }
    return value;
}

/** Der Uebersetzer, den notices.asDicts braucht. */
function describe(locale) {
    return (key, params) => translate(key, locale, params);
}

function requireSession(sessionId) {
    if (session.id === null || sessionId !== session.id) {
        throw new AppError("session_expired", "session_id");
    }
}

/** Eine Sitzungskennung in derselben Form wie uuid4().hex am Server. */
function randomId() {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return [...bytes].map((value) => value.toString(16).padStart(2, "0")).join("");
}
