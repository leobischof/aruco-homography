/**
 * live.js - der Sucher: Marker im laufenden Bild finden, bevor ein Foto entsteht.
 *
 * Wozu. Ob die vier Marker im Bild sind, ob keiner angeschnitten ist und ob das
 * Blatt flach genug liegt, sieht man erst NACH dem Entzerren - bis dahin sind
 * Foto, Hochladen und Rechnen schon passiert. Bei schlechtem Licht oder zu
 * flachem Winkel ist das ein Weg von zwanzig Sekunden, um zu erfahren, dass man
 * naeher hingehen muss. Der Sucher sagt es sofort.
 *
 * Was hier NICHT passiert: gemessen wird nichts. Dieser Schritt beantwortet
 * genau eine Frage - "sind die Marker da und wie liegen sie?" - und uebergibt
 * dann an den gewohnten Weg.
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

import { detectFrame } from "./api.js";
import { t } from "./i18n.js";
import { onThemeChange, readCssThemeVar } from "./theme.js";

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

/** Laenge der gezeichneten Achsen, als Anteil der mittleren Markerkante. */
const AXIS_SHARE = 0.7;

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

function readColours() {
    return {
        outline: readCssThemeVar("--hull-stroke", "canvastext"),
        halo: readCssThemeVar("--crop-halo", "canvas"),
        axisX: readCssThemeVar("--marker-axis-x", "red"),
        axisY: readCssThemeVar("--marker-axis-y", "orange"),
        label: readCssThemeVar("--crop-handle", "canvas"),
        labelInk: readCssThemeVar("--foreground", "canvastext"),
    };
}

export function createLiveView({ dialog, video, canvas, status, shutter, closeButton,
        onPhoto, onError }) {
    const context = canvas.getContext("2d");
    const shot = document.createElement("canvas");

    let stream = null;
    let running = false;
    let detecting = false;
    let lastRun = 0;
    let markers = [];
    let frameWidth = 0;
    let colours = readColours();

    const stopThemeWatch = onThemeChange(() => { colours = readColours(); });

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

    async function detect() {
        detecting = true;
        try {
            const found = await detectFrame(await grab(FRAME_MAX_PX, FRAME_QUALITY));
            markers = found.markers || [];
            frameWidth = found.width || 0;
            showCount();
        } catch (error) {
            // Ein einzelnes verlorenes Bild ist kein Fehler des Benutzers - der
            // naechste Versuch kommt in 120 ms. Nur der Zaehler sagt die
            // Wahrheit: nichts gefunden.
            markers = [];
            showCount();
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

    function toStage(corner, view) {
        return { x: view.left + corner[0] * view.scale, y: view.top + corner[1] * view.scale };
    }

    // ---- Zeichnen ----------------------------------------------------------

    function draw() {
        const view = stage();
        if (!view) return;

        const ratio = window.devicePixelRatio || 1;
        const backingWidth = Math.max(1, Math.round(view.width * ratio));
        const backingHeight = Math.max(1, Math.round(view.height * ratio));
        if (canvas.width !== backingWidth) canvas.width = backingWidth;
        if (canvas.height !== backingHeight) canvas.height = backingHeight;

        context.setTransform(backingWidth / view.width, 0, 0, backingHeight / view.height, 0, 0);
        context.clearRect(0, 0, view.width, view.height);
        for (const marker of markers) drawMarker(marker, view);
    }

    /**
     * Ein Marker: Umriss, sein eigenes Koordinatensystem, seine Nummer.
     *
     * Die Eckenreihenfolge des Erkenners ist TL, TR, BR, BL im System DES
     * MARKERS. Daraus folgt das Kreuz ohne jede Rechnung: x zeigt von Ecke 0
     * nach Ecke 1, y von Ecke 0 nach Ecke 3. Genau diese Reihenfolge traegt der
     * Massstab spaeter - ein verdrehter Marker ist damit schon hier zu sehen und
     * nicht erst am Ausdruck.
     */
    function drawMarker(marker, view) {
        const points = marker.corners.map((corner) => toStage(corner, view));

        // Umriss zweimal: dunkle Naht, helle Kernlinie. Dieselbe Physik wie beim
        // Zuschnitt-Rechteck (crop-rect.js) - eine einzelne Linie ist ueber
        // einem Kamerabild irgendwann genau so hell wie ihr Untergrund.
        context.beginPath();
        points.forEach((point, index) => {
            if (index === 0) context.moveTo(point.x, point.y);
            else context.lineTo(point.x, point.y);
        });
        context.closePath();
        context.strokeStyle = colours.halo;
        context.lineWidth = 5;
        context.stroke();
        context.strokeStyle = colours.outline;
        context.lineWidth = 2;
        context.stroke();

        const edge = (edgeLength(points[0], points[1]) + edgeLength(points[0], points[3])) / 2;
        const length = edge * AXIS_SHARE;
        drawAxis(points[0], points[1], length, colours.axisX);
        drawAxis(points[0], points[3], length, colours.axisY);
        drawId(marker.id, points);
    }

    function edgeLength(from, to) {
        return Math.hypot(to.x - from.x, to.y - from.y);
    }

    function drawAxis(origin, towards, length, colour) {
        const span = edgeLength(origin, towards) || 1;
        const end = {
            x: origin.x + ((towards.x - origin.x) / span) * length,
            y: origin.y + ((towards.y - origin.y) / span) * length,
        };
        context.beginPath();
        context.moveTo(origin.x, origin.y);
        context.lineTo(end.x, end.y);
        context.strokeStyle = colours.halo;
        context.lineWidth = 6;
        context.stroke();
        context.strokeStyle = colour;
        context.lineWidth = 3;
        context.stroke();

        // Die Spitze sagt, wohin die Achse zeigt. Ohne sie sind zwei Striche nur
        // ein Kreuz, und das hat keine Richtung.
        const angle = Math.atan2(end.y - origin.y, end.x - origin.x);
        const head = Math.max(6, length * 0.22);
        context.beginPath();
        context.moveTo(end.x, end.y);
        context.lineTo(end.x - head * Math.cos(angle - 0.4), end.y - head * Math.sin(angle - 0.4));
        context.lineTo(end.x - head * Math.cos(angle + 0.4), end.y - head * Math.sin(angle + 0.4));
        context.closePath();
        context.fillStyle = colour;
        context.fill();
    }

    function drawId(id, points) {
        const centre = points.reduce(
            (sum, point) => ({ x: sum.x + point.x / 4, y: sum.y + point.y / 4 }),
            { x: 0, y: 0 },
        );
        const text = String(id);
        context.font = "600 15px system-ui, sans-serif";
        context.textAlign = "center";
        context.textBaseline = "middle";
        const width = context.measureText(text).width;

        // Traeger unter der Nummer: eine Ziffer auf einem Kamerabild ist sonst
        // mal lesbar und mal nicht.
        context.fillStyle = colours.label;
        context.beginPath();
        context.roundRect(centre.x - width / 2 - 5, centre.y - 11, width + 10, 22, 5);
        context.fill();
        context.strokeStyle = colours.outline;
        context.lineWidth = 1.5;
        context.stroke();
        context.fillStyle = colours.labelInk;
        context.fillText(text, centre.x, centre.y);
    }

    function showCount() {
        status.textContent = markers.length
            ? t("ui.live.found", { count: markers.length })
            : t("ui.live.searching");
    }

    // ---- Der Lauf ----------------------------------------------------------

    function tick() {
        if (!running) return;
        if (!detecting && performance.now() - lastRun >= INTERVAL_MS && video.videoWidth) {
            void detect();
        }
        draw();
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
        frameWidth = 0;
        showCount();
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
            stopThemeWatch();
        },
    };
}
