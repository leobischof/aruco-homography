/**
 * bridge-shim.js - der Server, den es auf dem Telefon nicht gibt.
 *
 * Diese Datei laeuft VOR jedem Skript jeder Seite dieser App
 * (WebViewCompat.addDocumentStartJavaScript). Genau dadurch bleibt
 * app/static/index.html Byte fuer Byte unveraendert: die Oberflaeche ruft weiter
 * `fetch("/api/solve")`, und was sie erreicht, ist nicht mehr uvicorn, sondern
 * der native Kern nebenan.
 *
 * **Drei Aufgaben, und keine vierte.**
 *
 *  1. Eine Importkarte legen, damit `import ... from "pdf-lib"` auch in einer
 *     Seite aufloest, die nichts davon weiss.
 *  2. `window.__aruco` bereitstellen: die Bruecke nach Java als Versprechen
 *     statt als Rueckruf.
 *  3. `fetch` fuer /api/-Pfade ersetzen.
 *
 * **Was hier NICHT passiert: rechnen.** Kein Millimeter entsteht in dieser
 * Datei. Was der native Kern kann, wird durchgereicht; was er nicht kann, gibt
 * einen ehrlichen Fehler mit Code zurueck - denselben Weg, den der Server fuer
 * fachliche Fehler nimmt (422 mit {code, params, field}), damit
 * app/static/js/api.js ihn ohne Aenderung uebersetzt. Eine zweite Rechnung in
 * JavaScript waere eine dritte Fassung derselben Messtechnik, und die driftet.
 */

(() => {
    "use strict";

    if (window.__arucoShimInstalled) return;
    window.__arucoShimInstalled = true;

    const bridge = window.AndroidCore;

    // --- 1 · Importkarte ------------------------------------------------------
    // Sie muss VOR dem ersten Modul-Import im Dokument stehen. Zu diesem
    // Zeitpunkt ist <head> noch nicht geparst, deshalb haengt sie an
    // documentElement - das gibt es ab dem ersten Augenblick.
    try {
        const map = document.createElement("script");
        map.type = "importmap";
        map.textContent = JSON.stringify({
            imports: { "pdf-lib": "/vendor/pdf-lib.esm.min.js" },
        });
        document.documentElement.appendChild(map);
    } catch (error) {
        console.error("Importkarte konnte nicht gesetzt werden", error);
    }

    // --- 2 · Die Bruecke als Versprechen --------------------------------------
    // Java antwortet ueber window.__arucoResolve(callId, payload). Ein Aufruf,
    // dessen Antwort nie kommt, bliebe sonst fuer immer haengen - deshalb die
    // Karte mit den offenen Aufrufen und nicht ein einzelner Rueckruf.
    const pending = new Map();
    let nextCallId = 1;

    window.__arucoResolve = (callId, payload) => {
        const entry = pending.get(callId);
        if (!entry) return;
        pending.delete(callId);
        if (payload && payload.ok) entry.resolve(payload);
        else entry.reject(new Error((payload && payload.error) || "Unbekannter Fehler"));
    };

    /** Eine asynchrone Bruecken-Methode aufrufen (die mit callId als erstem Argument). */
    function callAsync(method, ...args) {
        if (!bridge || typeof bridge[method] !== "function") {
            return Promise.reject(new Error(`Die Bruecke kennt "${method}" nicht.`));
        }
        const callId = nextCallId++;
        return new Promise((resolve, reject) => {
            pending.set(callId, { resolve, reject });
            try {
                bridge[method](callId, ...args);
            } catch (error) {
                pending.delete(callId);
                reject(error);
            }
        });
    }

    /** Eine sofort antwortende Bruecken-Methode aufrufen. */
    function callSync(method, ...args) {
        if (!bridge || typeof bridge[method] !== "function") {
            throw new Error(`Die Bruecke kennt "${method}" nicht.`);
        }
        const answer = JSON.parse(bridge[method](...args));
        if (!answer.ok) throw new Error(answer.error || "Unbekannter Fehler");
        return answer;
    }

    window.__aruco = {
        available: Boolean(bridge),
        callAsync,
        callSync,
        info: () => callSync("nativeInfo"),
        markerBits: (id, modules) => callSync("markerBits", id, modules).bits,
        pickPhoto: () => callAsync("pickPhoto"),
        takePhoto: () => callAsync("takePhoto"),
        loadPickedPhoto: () => callAsync("loadPickedPhoto"),
        detectMarkers: (enhance = true) => callAsync("detectMarkers", enhance),
        runConformance: (dumpCorners = false) => callAsync("runConformance", dumpCorners),
        savePdf: (bytes, filename) => callAsync("savePdf", toBase64(bytes), filename),
        sharePdf: (bytes, filename) => callAsync("sharePdf", toBase64(bytes), filename),
        navigate: (path) => bridge && bridge.navigate(path),
    };

    /**
     * Uint8Array -> Base64, in Scheiben.
     *
     * `String.fromCharCode(...bytes)` auf einem ganzen PDF wirft
     * "Maximum call stack size exceeded", sobald es ein paar hunderttausend
     * Bytes werden - das Ausbreiten legt jedes Byte als eigenes Argument auf den
     * Stapel. 8 KB je Scheibe bleibt sicher darunter.
     */
    function toBase64(bytes) {
        const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
        let binary = "";
        for (let offset = 0; offset < view.length; offset += 8192) {
            binary += String.fromCharCode.apply(null, view.subarray(offset, offset + 8192));
        }
        return btoa(binary);
    }

    // --- 3 · fetch fuer /api/ -------------------------------------------------

    const nativeFetch = window.fetch.bind(window);

    /** Antwort in der Form, die app/static/js/api.js erwartet. */
    function jsonResponse(body, status = 200) {
        return new Response(JSON.stringify(body), {
            status,
            headers: { "Content-Type": "application/json" },
        });
    }

    /**
     * Ein fachlicher Fehler, so wie der Server ihn schickt: 422 mit Code.
     *
     * Der Code wird in app/static/i18n/*.json unter `errors.<code>` gesucht -
     * also gehoert jeder Code, der hier entsteht, in BEIDE Kataloge
     * (AGENTS.md, Invariante 7; tests/test_i18n.py besteht darauf).
     */
    function appError(code, field = null, params = {}) {
        return jsonResponse({ code, params, field, message: "" }, 422);
    }

    /**
     * Was der native Kern heute nicht kann.
     *
     * Dieser eine Fehler ist der ehrlichste Teil dieser Datei. Der C++-Kern misst
     * bis heute NUR die Markerecken (core/src/detect.cpp); Ausgleich, Kamerapose,
     * Dickenkorrektur, Entzerrung und Kontur stehen weiterhin allein in
     * app/vision/ und damit in Python. Auf dem Telefon gibt es kein Python. Also
     * endet die Kette hier - sichtbar, benannt und uebersetzt, statt mit einem
     * Netzfehler, den niemand einordnen kann.
     */
    function notInNativeCore(step) {
        return appError("android_core_incomplete", null, { step });
    }

    async function handleApi(url, init) {
        const path = url.pathname;
        const method = (init && init.method ? init.method : "GET").toUpperCase();

        // Sprachen: die Liste kommt aus shared/constants.json ueber den Katalog,
        // nicht aus einer zweiten Liste hier.
        if (path === "/api/locales") {
            const constants = await import("/shared/constants.json", { with: { type: "json" } })
                .then((module) => module.default);
            const locales = [];
            for (const code of constants.SUPPORTED_LOCALES) {
                const catalogue = await nativeFetch(`/i18n/${code}.json`).then((r) => r.json());
                const label = (catalogue.ui && catalogue.ui.language
                    && catalogue.ui.language[code]) || code.toUpperCase();
                locales.push({ code, label });
            }
            return jsonResponse({ default: constants.DEFAULT_LOCALE, locales });
        }

        if (path === "/api/upload" && method === "POST") {
            // Der Rumpf wird nicht angefasst: Android hat die Datei schon, seit
            // die WebView ihren Dateidialog geoeffnet hat (onShowFileChooser).
            const photo = await window.__aruco.loadPickedPhoto();
            return jsonResponse({
                session_id: "android",
                filename: photo.filename,
                width: photo.width,
                height: photo.height,
                exif: { focal35_mm: photo.focal35_mm, camera_model: photo.camera_model },
                defaults: await uploadDefaults(),
            });
        }

        if (path === "/api/solve") return notInNativeCore("solve");
        if (path === "/api/adjust") return notInNativeCore("adjust");
        if (path === "/api/export") return notInNativeCore("export");

        // /api/preview/... und /api/markersheet bedient die native Seite bzw. der
        // abgefangene Klick weiter unten - hier durchreichen.
        return nativeFetch(url.toString(), init);
    }

    /** Die Vorgaben, die /api/upload sonst aus app/config.py mitschickt. */
    async function uploadDefaults() {
        const constants = await import("/shared/constants.json", { with: { type: "json" } })
            .then((module) => module.default);
        return {
            marker_mm: constants.MARKER_MM_NOMINAL,
            spacing_x_mm: constants.SHEET_SPACING_MM[0],
            spacing_y_mm: constants.SHEET_SPACING_MM[1],
            dpi: constants.DPI_DEFAULT,
            dpi_choices: constants.DPI_CHOICES,
            overlap_mm: constants.TILE_OVERLAP_MM_DEFAULT,
            printer_margin_mm: constants.PRINTER_MARGIN_MM_DEFAULT,
            page_margin_mm: constants.PAGE_MARGIN_MM_DEFAULT,
        };
    }

    window.fetch = function androidFetch(input, init) {
        const raw = typeof input === "string" ? input
            : input instanceof Request ? input.url : String(input);
        const url = new URL(raw, window.location.origin);
        if (url.origin === window.location.origin && url.pathname.startsWith("/api/")) {
            const options = init || (input instanceof Request
                ? { method: input.method } : undefined);
            // `reason` muss in den Parametern stehen und nicht nur in `message`:
            // app/static/js/api.js uebersetzt bevorzugt aus errors.<code> mit den
            // Parametern, und der Katalogtext traegt {reason}. Ohne den Parameter
            // staende die geschweifte Klammer woertlich auf dem Bildschirm.
            return handleApi(url, options).catch((error) => {
                const reason = String((error && error.message) || error);
                return jsonResponse({ code: "android_bridge_failed", params: { reason },
                    field: null, message: reason }, 422);
            });
        }
        return nativeFetch(input, init);
    };

    // --- Das Markerblatt ------------------------------------------------------
    // Die Oberflaeche verlinkt es als <a href="/api/markersheet?...">. Ein Server,
    // der es baut, gibt es hier nicht - gebaut wird es in dieser Seite, aus
    // web/pdf/markersheet.js und den Modulbits des nativen Kerns. Abgefangen wird
    // in der Erfassungsphase, damit kein anderer Zuhoerer vorher navigiert.
    document.addEventListener("click", (event) => {
        const link = event.target && event.target.closest
            ? event.target.closest('a[href*="/api/markersheet"]') : null;
        if (!link) return;
        event.preventDefault();
        event.stopPropagation();
        buildAndSaveMarkersheet(new URL(link.href, window.location.origin)).catch((error) => {
            console.error("Markerblatt fehlgeschlagen", error);
        });
    }, true);

    async function buildAndSaveMarkersheet(url) {
        const [{ buildMarkersheet, MODULES }, constants] = await Promise.all([
            import("/web/pdf/markersheet.js"),
            import("/shared/constants.json", { with: { type: "json" } })
                .then((module) => module.default),
        ]);

        const number = (name, fallback) => {
            const value = Number(url.searchParams.get(name));
            return Number.isFinite(value) && value > 0 ? value : fallback;
        };
        const bytes = await buildMarkersheet({
            markerBits: (id) => Uint8Array.from(window.__aruco.markerBits(id, MODULES)),
            markerMm: number("marker_mm", constants.MARKER_MM_NOMINAL),
            spacingMm: [
                number("spacing_x_mm", constants.SHEET_SPACING_MM[0]),
                number("spacing_y_mm", constants.SHEET_SPACING_MM[1]),
            ],
            locale: url.searchParams.get("locale") || document.documentElement.lang
                || constants.DEFAULT_LOCALE,
        });
        await window.__aruco.savePdf(bytes, "markerblatt_A4.pdf");
    }
})();
