/**
 * bridge-shim.js - der Server, den es auf dem Telefon nicht gibt.
 *
 * Diese Datei laeuft VOR jedem Skript jeder Seite dieser App
 * (WebViewCompat.addDocumentStartJavaScript). Genau dadurch bleibt
 * app/static/index.html Byte fuer Byte unveraendert.
 *
 * **FUENF AUFGABEN, und keine sechste.**
 *
 *  1. `window.ARUCO_TRANSPORT = "local"` setzen. Das ist die ganze Umschaltung:
 *     app/static/js/api.js kennt zwei Betriebsarten, und in der oertlichen holt
 *     es sich `web/vision/local.js` und rechnet in der Seite. Dieselbe Zeile
 *     setzt web/index.html fuer den Browser-Bau. Kein zweiter Aufruf, kein
 *     zweites Schema, keine zweite Fassung der Oberflaeche.
 *
 *  2. Eine Importkarte legen - und zwar fuer DREI Dinge. `pdf-lib` liegt hier
 *     woanders als in node_modules. Und `web/vision/core.js` und
 *     `web/vision/image.js` werden gegen ihre Android-Fassungen getauscht: die
 *     eine erreicht den Kern ueber JNI statt ueber WebAssembly, die andere holt
 *     die Bildbytes aus Java statt aus einer Leinwand. **Das sind die einzigen
 *     beiden Dateien unter web/vision/, die auf diesem Ziel anders sind.**
 *     Alles darueber - solve.js, rectify.js, extent.js, contour.js, camera.js,
 *     enhance.js, pipeline.js, local.js - ist dieselbe Datei wie im Browser.
 *
 *  3. `window.__aruco` bereitstellen: die Bruecke nach Java als Versprechen
 *     statt als Rueckruf, und der synchrone Weg in den Rechenkern.
 *
 *  4. Das fertige PDF nach draussen bringen. In einer WebView tut ein
 *     `<a download>` von allein nichts - siehe unten.
 *
 *  5. Den sicheren Bereich durchreichen. Java misst, was Aussparung und
 *     Systemleisten dem Fenster wegnehmen, und ruft `window.__arucoInsets`;
 *     die vier Zahlen landen als CSS-Variablen auf `:root`. Die Stilvorlagen
 *     rechnen damit - dieselben Variablen, die im Browser aus `env()` kommen.
 *     Rechnen tut auch hier niemand: die Zahlen kommen fertig aus Java.
 *
 * **Was hier NICHT passiert: rechnen.** Kein Millimeter entsteht in dieser
 * Datei. Sie schaltet um, sie packt um, und sie reicht durch.
 */

(() => {
    "use strict";

    if (window.__arucoShimInstalled) return;
    window.__arucoShimInstalled = true;

    const bridge = window.AndroidCore;

    // --- 1 · Die Betriebsart --------------------------------------------------
    // Vor jedem Modul der Seite, also bevor api.js sie liest. Danach ist sie
    // fest; api.js liest sie einmal beim Laden.
    window.ARUCO_TRANSPORT = "local";

    // Und gleich daneben: wieviele Ausgabepixel dieses Geraet vertraegt.
    // web/constants.js::outputBudgetMpx() liest das und senkt die Obergrenze;
    // fehlt der Wert, gilt die Produktgrenze aus shared/constants.json.
    //
    // Hier und nicht spaeter, weil rectify.js die Zahl beim ERSTEN Export
    // braucht - und weil es hier nichts kostet: die Bruecke antwortet synchron.
    // Scheitert der Aufruf, bleibt die Produktgrenze stehen; das ist die
    // Lage von gestern und nicht schlimmer als sie.
    try {
        const budget = JSON.parse(bridge.nativeInfo()).max_output_mpx;
        if (Number.isFinite(budget) && budget > 0) {
            window.ARUCO_MAX_OUTPUT_MPX = budget;
        }
    } catch (error) {
        console.error("Speicherbudget nicht ermittelbar", error);
    }

    // --- 2 · Importkarte ------------------------------------------------------
    // Sie muss VOR dem ersten Modul-Import im Dokument stehen. Zu diesem
    // Zeitpunkt ist <head> noch nicht geparst, deshalb haengt sie an
    // documentElement - das gibt es ab dem ersten Augenblick.
    //
    // Die beiden Schluessel mit Schraegstrich sind URL-Schluessel: die
    // Importkarte loest sie gegen den Ursprung der Seite auf und vergleicht
    // danach die AUFGELOESTEN Adressen. `import ... from "./core.js"` in
    // web/vision/local.js zeigt damit auf core-android.js, ohne dass jene Datei
    // etwas davon wuesste.
    //
    // Greift die Karte nicht, laedt die Seite das echte core.js, sucht das
    // `.wasm` - das absichtlich nicht im APK liegt - und bricht mit einem
    // Ladefehler ab. Ein lautes Scheitern ist hier richtig: die stille
    // Alternative waere ein zweiter Rechenkern im Gepaeck.
    try {
        const map = document.createElement("script");
        map.type = "importmap";
        map.textContent = JSON.stringify({
            imports: {
                "pdf-lib": "/vendor/pdf-lib.esm.min.js",
                "/web/vision/core.js": "/web/vision/core-android.js",
                "/web/vision/image.js": "/web/vision/image-android.js",
            },
        });
        document.documentElement.appendChild(map);
    } catch (error) {
        console.error("Importkarte konnte nicht gesetzt werden", error);
    }

    // --- 3 · Die Bruecke ------------------------------------------------------
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

        /**
         * Eine Funktion des Rechenkerns. Synchron, wie WebAssembly im Browser -
         * web/vision/pipeline.js ist eine gewoehnliche Funktionskette ohne
         * `await` zwischen den Rechenschritten, und das soll sie bleiben, weil
         * genau dieselbe Datei im Browser laeuft.
         */
        core: (method, args) => callSync("core", method, JSON.stringify(args)).value,

        /** Der Griff auf das geladene Foto - die Eingabe jedes Rechenschritts. */
        photoHandle: () => callSync("photoHandle").handle,

        pickPhoto: () => callAsync("pickPhoto"),
        takePhoto: () => callAsync("takePhoto"),
        loadPickedPhoto: () => callAsync("loadPickedPhoto"),
        detectMarkers: (enhance = true) => callAsync("detectMarkers", enhance),

        /**
         * Ein Einzelbild des Suchers hinuebergeben und den Griff darauf holen.
         *
         * Ueber denselben Scheibenkanal wie saveFile/sharePdf - ein zweiter waere
         * eine zweite Stelle, an der sich Java und JavaScript ueber die Form
         * einigen muessten. Bei rund 60 KB je Bild ist es genau eine Scheibe.
         */
        decodeFrame: (bytes) => sendBytes(bytes).then(() => callAsync("decodeFrame")),

        /** Dasselbe Bild wieder hergeben. Synchron: es ist ein Map-Eintrag. */
        releaseFrame: (handle) => callSync("releaseFrame", handle),
        runConformance: (dumpCorners = false) => callAsync("runConformance", dumpCorners),
        saveFile: (bytes, filename) =>
            sendBytes(bytes).then(() => callAsync("saveFile", filename)),
        sharePdf: (bytes, filename) =>
            sendBytes(bytes).then(() => callAsync("sharePdf", filename)),
        navigate: (path) => bridge && bridge.navigate(path),
    };

    /**
     * Eine Datei in Scheiben nach Java schieben.
     *
     * Drei Groessenordnungen, ein Weg: das A4-Markerblatt sind wenige Dutzend
     * Kilobyte, ein gekacheltes Schablonen-PDF mit eingebettetem 300-dpi-Raster
     * zweistellige Megabyte, derselbe Zuschnitt als PNG noch einmal mehr. Am
     * Stueck stuende die Base64-Zeichenkette zweimal im Speicher - einmal hier,
     * einmal als Java-String -, und zwar genau in dem Augenblick, in dem das
     * Rasterbild noch daneben liegt.
     *
     * 192 KB je Scheibe sind 256 KB Text: klein genug, dass es nicht ins Gewicht
     * faellt, und ein Vielfaches von 3, damit keine Scheibe mit
     * Base64-Fuellzeichen endet. Ohne das ergaeben zwei aneinandergehaengte
     * Scheiben beim Dekodieren Unsinn.
     */
    const CHUNK_BYTES = 192 * 1024;

    async function sendBytes(bytes) {
        const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
        for (let offset = 0; offset < view.length; offset += CHUNK_BYTES) {
            callSync("appendBytes", toBase64(view.subarray(offset, offset + CHUNK_BYTES)));
        }
    }

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

    // --- 4 · Die fertige Datei nach draussen ----------------------------------
    //
    // In der oertlichen Betriebsart entsteht jede Datei in der Seite und wird ueber
    // eine `blob:`-Adresse angeboten - das Markerblatt in header.js als Verweis in
    // der Seite, die Schablone in main.js als Anker, den niemand einhaengt. Seit
    // dem Bildexport ist nicht mehr jede davon ein PDF; welcher Typ es ist, sagt
    // die Endung im Dateinamen, und die Java-Seite liest sie.
    //
    // Beides tut in einer WebView von allein NICHTS: es gibt keinen Downloadordner
    // und keinen PDF-Betrachter dahinter. Und die Java-Seite kann eine
    // blob:-Adresse nicht lesen - sie gilt nur im Fenster, das sie vergeben hat.
    // Also wird sie HIER gelesen und der Inhalt herueberreicht.
    //
    // Zwei Abfangstellen, weil es zwei Wege gibt: ein Klick des Benutzers auf
    // einen Anker IM Dokument (der steigt bis hierher auf), und `link.click()`
    // auf einem Anker, den niemand eingehaengt hat (der steigt NIRGENDWOHIN auf -
    // ein losgeloester Knoten hat keinen Aufstiegsweg). Der zweite Fall ist der
    // Export, und wer nur die erste Stelle baut, bekommt einen Knopf, der still
    // nichts tut.

    document.addEventListener("click", (event) => {
        const link = event.target && event.target.closest
            ? event.target.closest("a[href^='blob:']") : null;
        if (!link) return;
        event.preventDefault();
        event.stopPropagation();
        deliver(link.href, link.getAttribute("download") || "dokument.pdf");
    }, true);

    const nativeClick = HTMLElement.prototype.click;
    HTMLElement.prototype.click = function arucoClick() {
        if (this instanceof HTMLAnchorElement && typeof this.href === "string"
            && this.href.startsWith("blob:")) {
            deliver(this.href, this.getAttribute("download") || "dokument.pdf");
            return;
        }
        return nativeClick.call(this);
    };

    // --- 5 · Der sichere Bereich ----------------------------------------------
    //
    // Seit Android 15 zeichnet jede App mit targetSdk 35 UNTER den Systemleisten,
    // und die Abmeldung davon ist abgekuendigt. Ohne die vier Zahlen hier stuende
    // die Kopfzeile hinter der Uhr und der Fuss hinter der Navigationsleiste -
    // genau so ist es auf einem Xiaomi mit Android 15 gemeldet worden.
    //
    // **Warum nicht env(safe-area-inset-*) allein?** Die WebView fuellt daraus
    // nur die Display-Aussparung (AwDisplayCutoutController). Die Systemleisten
    // stehen dort NICHT drin - der untere Wert, also genau der gemeldete Fehler,
    // bliebe 0. Java misst deshalb systemBars() | displayCutout() und ruft hier
    // an. Die Stilvorlagen sehen keinen Unterschied: sie lesen dieselben vier
    // Namen, die in tokens.css aus env() kommen, und ein Inline-Stil auf :root
    // schlaegt die Regel dort.
    //
    // Die Werte kommen bereits in dichteunabhaengigen Punkten (dip) - also in
    // dem, was in dieser Seite ein CSS-Pixel ist. In physischen Pixeln waeren
    // sie auf einem Telefon rund dreimal zu gross.
    window.__arucoInsets = (top, right, bottom, left) => {
        const root = document.documentElement;
        // Reihenfolge wie in CSS: oben, rechts, unten, links.
        const values = [top, right, bottom, left];
        ["--safe-top", "--safe-right", "--safe-bottom", "--safe-left"]
            .forEach((name, index) => {
                const value = Number(values[index]);
                // Unsinn (NaN, negativ) fuehrt zu 0 statt zu einem kaputten
                // calc(): eine Seite ohne Abstand ist ertraeglich, eine Seite
                // ohne Innenabstand ueberhaupt nicht.
                root.style.setProperty(
                    name, (Number.isFinite(value) && value > 0 ? value : 0) + "px");
            });
    };

    /** Den Inhalt einer blob:-Adresse holen und dem System uebergeben. */
    function deliver(url, filename) {
        fetch(url)
            .then((response) => response.arrayBuffer())
            .then((buffer) => window.__aruco.saveFile(new Uint8Array(buffer), filename))
            .catch((error) => console.error("Datei konnte nicht uebergeben werden", error));
    }
})();
