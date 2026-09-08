/**
 * live.js - der Sucher: Marker im laufenden Bild finden, bevor ein Foto entsteht.
 *
 * Wozu. Ob die vier Marker im Bild sind, ob keiner angeschnitten ist und ob das
 * Blatt flach genug liegt, sieht man erst NACH dem Entzerren - bis dahin sind
 * Foto, Hochladen und Rechnen schon passiert. Bei schlechtem Licht oder zu
 * flachem Winkel ist das ein Weg von zwanzig Sekunden, um zu erfahren, dass man
 * naeher hingehen muss. Der Sucher sagt es sofort.
 *
 * Zwei Betriebsarten, und die zweite ist der eigentliche Grund fuer die erste:
 *
 *   **Marker** - Umriss, Nummer und das Koordinatensystem jedes Markers. Sagt,
 *   ob die Erkennung ueberhaupt greift.
 *
 *   **Ebene** - dieselben Marker, aber daraus gerechnet: das 50-mm-Raster der
 *   Ebene liegt im Bild auf dem Werkstueck, dazu Massstab und Restfehler. Wer
 *   nur wissen will, wie gross etwas ist, liest es hier ab und macht gar kein
 *   Foto. Ein Raster, das sich beim Kippen verzieht, sagt ausserdem sofort, dass
 *   die Flaeche nicht eben ist - das sieht man an keiner Zahl.
 *
 * Was hier NICHT passiert: nichts wird festgehalten. Weder Sitzung noch Foto -
 * beide Aufrufe (api.js: detectFrame, measureFrame) rechnen und vergessen.
 *
 * Drei Entscheidungen, die den Rest der Datei erklaeren:
 *
 * 1. **Erkannt wird auf einem VERKLEINERTEN Einzelbild** (laengste Kante
 *    FRAME_MAX_PX). Ein Marker, der auf 960 px nicht mehr gefunden wird, ist im
 *    Sucher ohnehin zu klein; und die volle Aufloesung zehnmal in der Sekunde
 *    durch die Erkennung zu schicken kostet mehr, als der Sucher hergibt.
 * 2. **Es laeuft immer nur EINE Erkennung.** Kommt das naechste Bild, bevor die
 *    vorige Antwort da ist, wird es uebersprungen. Ohne diese Sperre stauen sich
 *    die Anfragen, und was man sieht, gehoert zu einem Bild von vor zwei
 *    Sekunden.
 * 3. **Gezeichnet wird bei jedem Bildschirmbild, erkannt nur alle
 *    INTERVAL_MS.** Das Overlay klebt damit am Video, auch waehrend die
 *    Erkennung noch laeuft.
 *
 * Der Aufruf geht durch api.js und weiss deshalb nicht, ob im Hintergrund ein
 * Server oder das WebAssembly der Seite antwortet.
 */

import { detectFrame, measureFrame } from "./api.js";
import { formatNumber, t } from "./i18n.js";
import { createOverlay } from "./live-overlay.js";

/** Laengste Kante des Bildes, das in die Erkennung geht. */
const FRAME_MAX_PX = 960;

/** Qualitaet dieses Bildes. Marker sind harte Kanten - JPEG-Artefakte an einer
 *  Schwarz-Weiss-Kante stoeren die Erkennung nicht, und 0,6 ist rund ein
 *  Drittel der Bytes von 0,92. */
const FRAME_QUALITY = 0.6;

/** Abstand zwischen zwei Erkennungen. */
const INTERVAL_MS = 120;

/** Was die Aufnahme wert ist - hier zaehlt jedes Detail, es wird gemessen. */
const PHOTO_QUALITY = 0.92;

/** Aufloesung, um die der Strom gebeten wird. Was kommt, entscheidet das Geraet. */
const WANTED_PX = 4096;

/** Die messende Betriebsart. Die andere heisst "markers" und ist alles, was
 *  nicht diese ist - beide Zeichenketten stehen als Werte im Markup. */
const MODE_PLANE = "plane";

/**
 * Warnungen, nach denen die Ebene NICHT gezeichnet wird.
 *
 * Eine geloeste Lage ist nicht dasselbe wie eine brauchbare. Auf dem Telefon
 * gemeldet: zwei fast deckungsgleiche Marker, Restfehler 64,47 px - und der
 * Sucher legte trotzdem ein Raster ueber das Bild, das quer ueber den Schirm
 * schoss, neben einem Massstab mit vier Nachkommastellen. Beides war falsch,
 * und das Raster war das Schlimmere: eine Zahl kann man anzweifeln, ein Raster
 * sieht aus wie eine Messung.
 *
 * Es ist dieselbe Regel, die fuer den Rasterschritt schon gilt: fehlt er, wird
 * nichts gezeichnet. **Ein falsches Raster ist schlimmer als keines.**
 *
 * Die zwei Codes und warum genau sie:
 *
 *   `high_residual`     Das Modell passt nicht einmal auf die Punkte, aus denen
 *                       es gerechnet wurde (RMS_WARN_PX = 2 px). Meist liegen
 *                       die Marker nicht dort, wo die gewaehlte Betriebsart sie
 *                       vermutet - lose auf dem Tisch statt auf dem Blatt.
 *   `collinear_markers` Quer zur Markerlinie stuetzt sich die Homographie
 *                       kaum ab; genau dort schiesst das Raster davon. Zwei
 *                       Marker loesen das immer aus.
 *
 * Nicht dabei: `single_marker`, `marker_size_deviation`, `marker_rotation`.
 * Die sagen etwas ueber die Aufnahme, nicht darueber, dass die Abbildung selbst
 * unbrauchbar waere - und der Sucher soll nicht bei jeder Kleinigkeit blind
 * werden.
 */
const PLANE_BREAKERS = new Set(["high_residual", "collinear_markers"]);

/** Traegt diese Loesung eine Warnung, die sie unbrauchbar macht? */
function planeIsUsable(warnings) {
    return !(warnings || []).some((notice) => PLANE_BREAKERS.has(notice.code));
}

/** Gibt es an diesem Ort ueberhaupt eine Kamera-Schnittstelle?
 *
 * `navigator.mediaDevices` fehlt in JEDEM unsicheren Ursprung - eine Seite, die
 * ueber file:// geoeffnet wurde, hat es schlicht nicht. Der Knopf zum Sucher
 * wird dann gar nicht erst gezeigt: ein Knopf, der nur eine Fehlermeldung
 * erzeugen kann, ist schlimmer als kein Knopf.
 */
export function liveAvailable() {
    return Boolean(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

export function createLiveView({ dialog, video, canvas, status, modeSelect, shutter,
        closeButton, getParams, onPhoto, onError }) {
    const overlay = createOverlay(canvas);
    const shot = document.createElement("canvas");

    let stream = null;
    let running = false;
    let detecting = false;
    let lastRun = 0;
    let markers = [];
    let plane = null;
    let usable = false;
    let gridMm = 0;
    let frameWidth = 0;

    // ---- Bilder aus dem Strom holen ---------------------------------------

    /**
     * Ein Einzelbild als JPEG.
     *
     * Ueber ein Canvas und nicht ueber ImageCapture.takePhoto(): letzteres gibt
     * es in Chromium, aber nicht ueberall, und es liefert auf manchem Geraet ein
     * Bild aus einem ANDEREN Moment als das, was der Sucher gerade zeigt. Was
     * man sieht, soll das sein, was man bekommt.
     */
    function grab(maxPx, quality) {
        const width = video.videoWidth;
        const height = video.videoHeight;
        const scale = Math.min(1, maxPx / Math.max(width, height, 1));
        shot.width = Math.max(1, Math.round(width * scale));
        shot.height = Math.max(1, Math.round(height * scale));
        shot.getContext("2d").drawImage(video, 0, 0, shot.width, shot.height);
        return new Promise((resolve, reject) => {
            shot.toBlob(
                (blob) => (blob ? resolve(blob) : reject(new Error("Kein Einzelbild"))),
                "image/jpeg",
                quality,
            );
        });
    }

    async function look() {
        detecting = true;
        const wantsPlane = modeSelect.value === MODE_PLANE;
        try {
            const frame = await grab(FRAME_MAX_PX, FRAME_QUALITY);
            const found = wantsPlane
                ? await measureFrame(frame, getParams())
                : await detectFrame(frame);
            markers = found.markers || [];
            frameWidth = found.width || 0;
            plane = wantsPlane ? found.plane || null : null;
            usable = Boolean(plane) && planeIsUsable(found.warnings);
            gridMm = found.grid_mm || gridMm;
            tellState();
        } catch (error) {
            // Ein einzelnes verlorenes Bild ist kein Fehler des Benutzers - der
            // naechste Versuch kommt in 120 ms. Nur die Meldung sagt die
            // Wahrheit: nichts gefunden.
            markers = [];
            plane = null;
            usable = false;
            tellState();
        } finally {
            detecting = false;
            lastRun = performance.now();
        }
    }

    // ---- Abbildung Einzelbild -> Buehne ------------------------------------

    /**
     * Wo im Canvas das Video wirklich liegt.
     *
     * `object-fit: contain` laesst oben/unten oder links/rechts einen Streifen
     * frei, und der ist nicht Teil des Bildes. Wer das uebergeht, zeichnet die
     * Marker um genau diesen Streifen versetzt.
     */
    function stage() {
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        const videoWidth = video.videoWidth;
        const videoHeight = video.videoHeight;
        if (!width || !height || !videoWidth || !videoHeight) return null;

        const fit = Math.min(width / videoWidth, height / videoHeight);
        return {
            width,
            height,
            left: (width - videoWidth * fit) / 2,
            top: (height - videoHeight * fit) / 2,
            // Vom ERKENNUNGSBILD auf die Buehne: die Ecken kommen in dessen
            // Pixeln zurueck, und das ist das verkleinerte, nicht das Video.
            scale: fit * (frameWidth > 0 ? videoWidth / frameWidth : 1),
        };
    }

    function tellState() {
        if (plane && !usable) {
            // Der Massstab steht hier mit Absicht NICHT. Er waere die
            // ueberzeugendste Zahl auf dem Schirm und die falscheste: dieselbe
            // Rechnung, die 64 px danebenliegt, hat ihn erzeugt.
            status.textContent = t("ui.live.plane_unusable", {
                rms_px: formatNumber(plane.rms_px, 2),
                count: markers.length,
            });
            return;
        }
        if (plane) {
            status.textContent = t("ui.live.plane", {
                mm_per_px: formatNumber(plane.mm_per_px, 4),
                rms_px: formatNumber(plane.rms_px, 2),
                count: markers.length,
            });
            return;
        }
        status.textContent = markers.length
            ? t("ui.live.found", { count: markers.length })
            : t("ui.live.searching");
    }

    // ---- Der Lauf ----------------------------------------------------------

    function tick() {
        if (!running) return;
        if (!detecting && performance.now() - lastRun >= INTERVAL_MS && video.videoWidth) {
            void look();
        }
        const view = stage();
        // `plane: null` und nicht ein zweiter Schalter im Overlay: dort gibt es
        // schon genau einen Fall "keine Ebene, also kein Raster", und ein
        // zweiter Weg dorthin waere ein zweiter Ort zum Danebengreifen.
        if (view) overlay.paint(view, { markers, plane: usable ? plane : null, gridMm });
        requestAnimationFrame(tick);
    }

    async function open() {
        if (stream) return;
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                // "environment" ist die Kamera auf der Rueckseite - die, die auf
                // das Werkstueck zeigt. `ideal` und nicht `exact`: ein Geraet mit
                // nur einer Kamera soll den Sucher trotzdem oeffnen.
                video: {
                    facingMode: { ideal: "environment" },
                    width: { ideal: WANTED_PX },
                    height: { ideal: WANTED_PX },
                },
                audio: false,
            });
        } catch (error) {
            onError(error);
            return;
        }

        video.srcObject = stream;
        try {
            await video.play();
        } catch (error) {
            // Manche Umgebung verlangt eine Nutzergeste fuer play(). Der Knopf
            // ist eine - trotzdem nicht daran haengenbleiben.
        }

        markers = [];
        plane = null;
        usable = false;
        frameWidth = 0;
        tellState();
        dialog.showModal();
        running = true;
        lastRun = 0;
        requestAnimationFrame(tick);
    }

    /**
     * Zumachen - und den Strom wirklich freigeben.
     *
     * Ohne `track.stop()` bleibt die Kamera an, samt Leuchte am Geraet und samt
     * Stromverbrauch. Das Video-Element loszulassen genuegt nicht: der Strom
     * gehoert nicht ihm.
     */
    function close() {
        running = false;
        if (stream) {
            for (const track of stream.getTracks()) track.stop();
            stream = null;
        }
        video.srcObject = null;
        if (dialog.open) dialog.close();
    }

    async function capture() {
        try {
            const blob = await grab(WANTED_PX, PHOTO_QUALITY);
            const file = new File([blob], t("ui.live.filename"), { type: "image/jpeg" });
            close();
            onPhoto(file);
        } catch (error) {
            onError(error);
        }
    }

    // Beim Umschalten sofort neu rechnen, statt bis zum naechsten Takt das
    // Overlay der anderen Betriebsart stehen zu lassen.
    modeSelect.addEventListener("change", () => {
        markers = [];
        plane = null;
        usable = false;
        lastRun = 0;
        tellState();
    });

    shutter.addEventListener("click", capture);
    closeButton.addEventListener("click", close);
    // Die Esc-Taste schliesst einen <dialog> von selbst - ohne diesen Horcher
    // liefe die Kamera danach weiter.
    dialog.addEventListener("close", close);

    return {
        open,
        close,
        destroy() {
            close();
            overlay.destroy();
        },
    };
}
