/**
 * crop-rect.js - das Zuschnitt-Rechteck auf dem entzerrten Bild.
 *
 * Was hier bedienbar ist, und warum jedes Stueck davon gebraucht wird:
 *
 * - **Acht Griffe** (vier Ecken, vier Kantenmitten). Eine Ecke aendert beide
 *   Achsen, ein Kantengriff genau eine. Vorher liess sich ein bestehendes
 *   Rechteck ueberhaupt nicht mehr aendern - man musste ein neues aufziehen.
 * - **Ziehen im Inneren** verschiebt, Groesse unveraendert.
 * - **Freie Flaeche tut nichts.** Ein Zeiger ausserhalb des Rechtecks wird
 *   ignoriert - kein Aufziehen, kein Neuzeichnen, kein Fokus, kein Scrollen.
 * - **Tastatur:** Pfeile verschieben um 1 mm, mit Shift um 10 mm.
 *
 * Drei Dinge, die diese Datei anders macht als ihre Vorgaengerin:
 *
 * 1. **Pointer Events mit setPointerCapture.** Ein Finger, der beim Ziehen den
 *    Rand des Canvas verlaesst, verliert damit die Geste nicht mehr. Zusammen
 *    mit `touch-action: none` (crop.css) scrollt die Seite dabei auch nicht weg.
 * 2. **Der Speicher des Canvas wird mit devicePixelRatio bemessen.** Ohne das
 *    ist das Overlay auf jedem Handy und jedem HiDPI-Schirm weichgezeichnet -
 *    und eine unscharfe Linie ueber einer Schnittkante ist genau die falsche
 *    Stelle fuer Unschaerfe.
 * 3. **Die Farben kommen per getComputedStyle aus tokens.css** und werden beim
 *    Themenwechsel NEU gelesen. Ein Canvas loest var() nicht auf; wer die Werte
 *    einmal liest und behaelt, malt nach dem Umschalten mit den Farben des
 *    anderen Themas.
 */

import {
    HANDLES,
    clampPoint,
    clampToExtent,
    growToMinimum,
    handlePoint,
    hitTest,
    moveRect,
    normaliseRect,
    oppositeAnchor,
    resizeFrom,
} from "./crop-geometry.js";
import { onThemeChange, readCssThemeVar } from "./theme.js";

// Gezeichnete Griffgroessen in CSS-Pixeln. Ecken sind Quadrate, Kantengriffe
// Balken laengs ihrer Kante - die Form sagt schon, welche Achse sie bewegen.
const CORNER_PX = 12;
const BAR_LONG_PX = 18;
const BAR_SHORT_PX = 8;

// Halbe Kantenlaenge der Trefferflaeche. Der Griff wird kleiner GEZEICHNET, aber
// nicht kleiner getroffen - und wie viel groesser, entscheidet der ZEIGER.
//
// Ein Mauszeiger ist ein Pixel und sieht, wo er steht; 44 px (der Wert von
// --touch-target) sind dafuer reichlich. Ein Finger ist rund einen Zentimeter
// breit, verdeckt genau die Stelle, die er treffen soll, und der Bediener zielt
// nach dem Gedaechtnis. Vom Telefon gemeldet: "make the hitboxes bigger".
//
// 60 px sind rund 12 mm auf einem heutigen Telefon - etwas mehr als eine
// Fingerkuppe, und damit die Groesse, ab der man nicht mehr zielen muss.
const HIT_HALF_MOUSE_PX = 22;
const HIT_HALF_TOUCH_PX = 30;

// Unter diese halbe Kantenlaenge wird nie geschrumpft: ein winziges Rechteck
// haette sonst Griffe, die niemand mehr trifft - und gerade dort will man es
// wieder groesser ziehen.
const HIT_HALF_MIN_PX = 12;

const NUDGE_MM = 1;
const NUDGE_SHIFT_MM = 10;

const CURSOR_BY_ID = Object.fromEntries(HANDLES.map((handle) => [handle.id, handle.cursor]));

/**
 * Die Tokenfarben des Overlays. Ausweichwerte sind CSS-Systemfarben und keine
 * Hexwerte: sie greifen nur, wenn tokens.css gar nicht geladen ist, und folgen
 * dann immerhin noch der Helligkeit des Systems.
 */
function readColours() {
    return {
        hullFill: readCssThemeVar("--hull-fill", "transparent"),
        hullStroke: readCssThemeVar("--hull-stroke", "canvastext"),
        cropStroke: readCssThemeVar("--crop-stroke", "canvastext"),
        cropFill: readCssThemeVar("--crop-fill", "transparent"),
        cropHalo: readCssThemeVar("--crop-halo", "canvastext"),
        cropDim: readCssThemeVar("--crop-dim", "transparent"),
        handle: readCssThemeVar("--crop-handle", "canvas"),
        handleStroke: readCssThemeVar("--crop-handle-stroke", "canvastext"),
        handleHover: readCssThemeVar("--crop-handle-hover", "canvas"),
        handleActive: readCssThemeVar("--crop-handle-active", "canvas"),
    };
}

export function createCropRect({ canvas, onChange }) {
    const context = canvas.getContext("2d");

    let scene = null; // {extent, hull}
    let crop = null;
    let drag = null;
    let hoverId = null;
    let colours = readColours();

    // ---- Abbildung mm <-> CSS-Pixel ---------------------------------------
    // Das Canvas liegt per CSS deckungsgleich auf dem Bild, und das Bild zeigt
    // genau den Bereich `extent`. Damit ist die Abbildung eine reine Streckung.

    function viewport() {
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        const extent = scene.extent;
        return {
            width,
            height,
            extent,
            scaleX: width / (extent.x1 - extent.x0),
            scaleY: height / (extent.y1 - extent.y0),
        };
    }

    function toPx(x, y, view) {
        return { x: (x - view.extent.x0) * view.scaleX, y: (y - view.extent.y0) * view.scaleY };
    }

    function toMm(px, py, view) {
        return { x: view.extent.x0 + px / view.scaleX, y: view.extent.y0 + py / view.scaleY };
    }

    function rectToPx(rect, view) {
        const start = toPx(rect.x0, rect.y0, view);
        const end = toPx(rect.x1, rect.y1, view);
        return { x0: start.x, y0: start.y, x1: end.x, y1: end.y };
    }

    function localPoint(event) {
        const bounds = canvas.getBoundingClientRect();
        return { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
    }

    /**
     * Wie gross die Trefferflaeche fuer DIESEN Zeiger an DIESEM Rechteck ist.
     *
     * Zwei Groessen und eine Schranke:
     *
     * 1. Maus und Stift bekommen die kleine Flaeche. Bei 60 px liesse sich das
     *    Rechteck mit der Maus kaum noch VERSCHIEBEN - an einem schmalen
     *    Zuschnitt waere alles ein Griff.
     * 2. Alles andere - Finger, unbekannter Zeigertyp - bekommt die grosse.
     *    Im Zweifel lieber zu grosszuegig: ein Griff, der zu leicht kommt, ist
     *    ein Aergernis, einer der nicht kommt ist ein Fehler.
     * 3. Ein Viertel der Kantenlaenge als Obergrenze, damit in der Mitte etwas
     *    zum Verschieben uebrig bleibt. Ohne sie waere ein 60-px-Rechteck
     *    vollstaendig von Griffen bedeckt.
     */
    function hitHalfFor(event, rectPx) {
        const half = event.pointerType === "mouse" || event.pointerType === "pen"
            ? HIT_HALF_MOUSE_PX
            : HIT_HALF_TOUCH_PX;
        const width = Math.abs(rectPx.x1 - rectPx.x0);
        const height = Math.abs(rectPx.y1 - rectPx.y0);
        return Math.max(HIT_HALF_MIN_PX, Math.min(half, width / 4, height / 4));
    }

    function commit(next, live) {
        crop = next;
        draw();
        if (onChange) onChange({ ...crop }, live);
    }

    // ---- Zeigergesten -----------------------------------------------------

    canvas.addEventListener("pointerdown", (event) => {
        if (!scene || !crop || event.button > 0) return;

        const view = viewport();
        const point = localPoint(event);
        const rectPx = rectToPx(crop, view);
        const hit = hitTest(point, rectPx, hitHalfFor(event, rectPx));

        // AUSSERHALB DES RECHTECKS PASSIERT NICHTS. Kein neues Rechteck, kein
        // Pointer-Capture, kein Neuzeichnen - und vor allem nichts davon
        // versehentlich vorher: die Trefferpruefung steht deshalb ueber allem
        // anderen.
        //
        // Frueher zog eine Geste hier ein neues Rechteck auf. Am Finger ist das
        // die falsche Vorgabe: wer das Bild antippt, um es anzusehen, hatte
        // danach einen Zuschnitt von null Millimetern und musste von vorn
        // anfangen - ein Fehlgriff kostete die ganze bisherige Einstellung. Der
        // Weg zu einem frischen Rechteck ist jetzt ein Knopf, der so heisst
        // ("Zuschnitt zuruecksetzen"), und der ist absichtlich schwerer zu
        // treffen als die halbe Bildflaeche.
        if (hit.kind !== "resize" && hit.kind !== "move") {
            // Das einzige, was hier doch geschieht, und es ist eine
            // Unterdrueckung: ein <canvas tabindex="0"> bekommt sonst vom
            // Browser den Fokus, und das Hereinholen der Buehne in den
            // Sichtbereich scrollt die Seite. Auf dem Telefon waere genau das
            // die sichtbare "Reaktion", die es hier nicht geben soll.
            // preventDefault auf pointerdown verhindert das folgende
            // mousedown, und damit den Fokus.
            event.preventDefault();
            return;
        }

        // ERST den Griff merken, DANN Fokus und Zeigerfang.
        //
        // Die Reihenfolge ist der Punkt. Bis hierher standen focus() und
        // setPointerCapture() davor, und beide koennen werfen: setPointerCapture
        // ist laut Spezifikation ein NotFoundError, wenn der Zeiger in diesem
        // Augenblick nicht (mehr) aktiv ist. Eine Ausnahme in einem Zuhoerer
        // schluckt der Browser - `drag` blieb dann null, und der Griff war
        // lautlos tot. Genau so sieht "die Griffe gehen nicht" aus, und genau
        // das kann ein Prueflauf im Browser nicht zeigen, weil dort nichts
        // wirft.
        //
        // Jetzt ist beides Beiwerk: der Fang macht das Ziehen bequemer, indem
        // die Bewegungen auch dann noch hier ankommen, wenn der Finger die
        // Buehne verlaesst. Ohne ihn zieht man weiter, solange man auf der
        // Flaeche bleibt - und beim Loslassen faengt der Horcher am Fenster
        // (siehe endDrag) auf, was das Canvas dann nicht mehr sieht.
        const pointer = clampPoint(toMm(point.x, point.y, view), scene.extent);
        drag = hit.kind === "resize"
            ? {
                pointerId: event.pointerId,
                kind: "resize",
                axes: hit.handle.axes,
                anchor: oppositeAnchor(hit.handle, crop),
                base: { ...crop },
                handleId: hit.handle.id,
            }
            : {
                pointerId: event.pointerId,
                kind: "move",
                grab: { x: pointer.x - crop.x0, y: pointer.y - crop.y0 },
                handleId: null,
            };

        try {
            // Fokus, damit die Pfeiltasten unmittelbar nach dem Ziehen wirken.
            // preventScroll, weil der Sprung sonst die Buehne verschiebt.
            canvas.focus({ preventScroll: true });
            canvas.setPointerCapture(event.pointerId);
        } catch (error) {
            // Kein Abbruch: der Griff steht schon. Gemeldet wird es trotzdem -
            // ein stiller Fehlschlag hier ist genau der, der uns die Zeit
            // gekostet hat.
            console.warn("Zeigerfang nicht bekommen, Ziehen laeuft trotzdem", error);
        }
        event.preventDefault();
    });

    canvas.addEventListener("pointermove", (event) => {
        if (!scene || !crop) return;
        const view = viewport();
        const point = localPoint(event);

        if (!drag || drag.pointerId !== event.pointerId) {
            const rectPx = rectToPx(crop, view);
            const hit = hitTest(point, rectPx, hitHalfFor(event, rectPx));
            // Kein Fadenkreuz mehr ueber der freien Flaeche: es versprach eine
            // Geste, die es dort nicht mehr gibt.
            canvas.style.cursor =
                hit.kind === "resize" ? hit.handle.cursor : hit.kind === "move" ? "move" : "default";
            const nextHover = hit.kind === "resize" ? hit.handle.id : null;
            if (nextHover !== hoverId) {
                hoverId = nextHover;
                draw();
            }
            return;
        }

        const pointer = clampPoint(toMm(point.x, point.y, view), scene.extent);
        if (drag.kind === "move") {
            const dx = pointer.x - drag.grab.x - crop.x0;
            const dy = pointer.y - drag.grab.y - crop.y0;
            commit(moveRect(crop, dx, dy, scene.extent), true);
        } else {
            const result = resizeFrom(drag.anchor, pointer, drag.axes, drag.base);
            drag.handleId = result.handleId;
            canvas.style.cursor = CURSOR_BY_ID[result.handleId] || "default";
            commit(clampToExtent(result.rect, scene.extent), true);
        }
        event.preventDefault();
    });

    function endDrag(event) {
        if (!drag || drag.pointerId !== event.pointerId) return;
        drag = null;
        hoverId = null;
        try {
            if (canvas.hasPointerCapture(event.pointerId)) {
                canvas.releasePointerCapture(event.pointerId);
            }
        } catch (error) {
            // Freigeben ist Aufraeumen. Eine Ausnahme daraus darf nicht das
            // Uebernehmen des Rechtecks verhindern, das gleich darunter steht.
            console.warn("Zeigerfang nicht freigegeben", error);
        }
        // Erst beim Loslassen die Mindestgroesse durchsetzen. Waehrend des
        // Ziehens waere sie im Weg: der gegriffene Griff soll am Zeiger kleben,
        // auch wenn das Rechteck kurzzeitig fast nichts umschliesst.
        commit(growToMinimum(clampToExtent(crop, scene.extent), scene.extent), false);
    }

    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);

    // Dieselben zwei am FENSTER, und nicht doppelt gemoppelt: ohne Zeigerfang
    // bekommt das Canvas kein pointerup mehr, sobald der Finger es verlassen
    // hat - das Rechteck haette dann fuer immer einen gegriffenen Griff. Mit
    // Fang laufen die Ereignisse ohnehin ueber das Canvas und blubbern hierher,
    // wo endDrag sie am schon geleerten `drag` erkennt und nichts mehr tut.
    window.addEventListener("pointerup", endDrag);
    window.addEventListener("pointercancel", endDrag);

    // ---- Tastatur ---------------------------------------------------------

    canvas.addEventListener("keydown", (event) => {
        if (!scene || !crop) return;
        const step = event.shiftKey ? NUDGE_SHIFT_MM : NUDGE_MM;
        let dx = 0;
        let dy = 0;
        switch (event.key) {
            case "ArrowLeft": dx = -step; break;
            case "ArrowRight": dx = step; break;
            case "ArrowUp": dy = -step; break;
            case "ArrowDown": dy = step; break;
            default: return;
        }
        commit(moveRect(crop, dx, dy, scene.extent), false);
        event.preventDefault();
    });

    // ---- Zeichnen ---------------------------------------------------------

    function draw() {
        if (!scene) return;
        const view = viewport();
        if (!view.width || !view.height) return;

        // Der Speicher des Canvas laeuft in Geraetepixeln, gezeichnet wird in
        // CSS-Pixeln. Der Streckungsfaktor wird aus den gerundeten
        // Speichermassen zurueckgerechnet, statt devicePixelRatio direkt zu
        // nehmen - sonst verschiebt der Rundungsrest die Linien um Bruchteile.
        const ratio = window.devicePixelRatio || 1;
        const backingWidth = Math.max(1, Math.round(view.width * ratio));
        const backingHeight = Math.max(1, Math.round(view.height * ratio));
        if (canvas.width !== backingWidth) canvas.width = backingWidth;
        if (canvas.height !== backingHeight) canvas.height = backingHeight;

        context.setTransform(backingWidth / view.width, 0, 0, backingHeight / view.height, 0, 0);
        context.clearRect(0, 0, view.width, view.height);

        drawHull(view);
        if (!crop) return;
        const rect = rectToPx(crop, view);
        drawOutside(view, rect);
        drawRect(rect);
        drawHandles(view, rect);
    }

    /**
     * Die Marker-Huelle: das Vieleck durch die vier Markermittelpunkte. Innen ist
     * die Homographie GEMESSEN, ausserhalb wird sie fortgeschrieben. Das ist eine
     * Aussage ueber Verlaesslichkeit, kein Zierat - sie muss sichtbar bleiben,
     * auch innerhalb des Zuschnitts.
     */
    function drawHull(view) {
        const hull = scene.hull;
        if (!hull || hull.length < 3) return;

        context.beginPath();
        hull.forEach((point, index) => {
            const place = toPx(point[0], point[1], view);
            if (index === 0) context.moveTo(place.x, place.y);
            else context.lineTo(place.x, place.y);
        });
        context.closePath();
        context.fillStyle = colours.hullFill;
        context.fill();
        context.strokeStyle = colours.hullStroke;
        context.lineWidth = 1.5;
        context.stroke();
    }

    /** Was nicht mitkommt, wird abgedunkelt - vier Rechtecke um den Zuschnitt. */
    function drawOutside(view, rect) {
        context.fillStyle = colours.cropDim;
        context.fillRect(0, 0, view.width, rect.y0);
        context.fillRect(0, rect.y1, view.width, view.height - rect.y1);
        context.fillRect(0, rect.y0, rect.x0, rect.y1 - rect.y0);
        context.fillRect(rect.x1, rect.y0, view.width - rect.x1, rect.y1 - rect.y0);
    }

    /**
     * Das Rechteck selbst: dunkle Naht, darauf die helle Kernlinie.
     *
     * Eine einzelne Linie auf einem Foto ist irgendwann genau so hell wie das,
     * worueber sie laeuft. Das Paar aus hell und dunkel ist es nie - dieselbe
     * Physik, die AGENTS.md (Invariante 5) fuer das Raster im PDF verlangt, dort
     * nur mit umgekehrten Rollen.
     */
    function drawRect(rect) {
        const width = rect.x1 - rect.x0;
        const height = rect.y1 - rect.y0;

        context.fillStyle = colours.cropFill;
        context.fillRect(rect.x0, rect.y0, width, height);

        context.strokeStyle = colours.cropHalo;
        context.lineWidth = 4;
        context.strokeRect(rect.x0, rect.y0, width, height);

        context.strokeStyle = colours.cropStroke;
        context.lineWidth = 1.5;
        context.strokeRect(rect.x0, rect.y0, width, height);
    }

    function drawHandles(view, rect) {
        const activeId = drag && drag.kind === "resize" ? drag.handleId : null;
        for (const handle of HANDLES) {
            const centre = handlePoint(handle, rect);
            const isCorner = handle.axes === "xy";
            const width = isCorner ? CORNER_PX : handle.axes === "y" ? BAR_LONG_PX : BAR_SHORT_PX;
            const height = isCorner ? CORNER_PX : handle.axes === "y" ? BAR_SHORT_PX : BAR_LONG_PX;

            // Der GEZEICHNETE Griff wird in die Buehne hineingeschoben, damit er
            // ganz sichtbar bleibt, wenn das Rechteck den Bildrand beruehrt - und
            // das tut es im Ausgangszustand, weil der Vorgabezuschnitt den ganzen
            // Bereich fuellt. Ein Canvas beschneidet sein eigenes Malen; ein Griff
            // auf der Kante waere sonst zur Haelfte weg.
            //
            // Die TREFFERFLAeche wandert bewusst nicht mit: sie ist 44px gross und
            // liegt um die echte Ecke, deckt den verschobenen Griff also mit ab.
            const x = Math.min(Math.max(centre.x, width / 2), view.width - width / 2);
            const y = Math.min(Math.max(centre.y, height / 2), view.height - height / 2);

            context.fillStyle =
                handle.id === activeId
                    ? colours.handleActive
                    : handle.id === hoverId
                      ? colours.handleHover
                      : colours.handle;
            context.fillRect(x - width / 2, y - height / 2, width, height);
            context.strokeStyle = colours.handleStroke;
            context.lineWidth = 1.5;
            context.strokeRect(x - width / 2, y - height / 2, width, height);
        }
    }

    // ---- Aussenseite ------------------------------------------------------

    // Das Bild bestimmt die Groesse der Buehne, und die aendert sich beim
    // Umbrechen des Layouts ohne jedes Fensterereignis - deshalb ein Beobachter
    // am Canvas selbst und nicht window.onresize.
    const observer = new ResizeObserver(() => draw());
    observer.observe(canvas);
    const stopThemeWatch = onThemeChange(() => {
        colours = readColours();
        draw();
    });

    return {
        /** Neue Szene: abbildbarer Bereich, Marker-Huelle, Ausgangszuschnitt. */
        setScene({ extent, hull, crop: initial }) {
            scene = { extent, hull: hull || [] };
            commit(growToMinimum(clampToExtent(initial, extent), extent), false);
        },
        /** Zuschnitt von aussen setzen (die vier Zahlenfelder). */
        setCrop(next) {
            if (!scene) return;
            commit(clampToExtent(normaliseRect(next), scene.extent), false);
        },
        getCrop() {
            return crop ? { ...crop } : null;
        },
        redraw: draw,
        destroy() {
            observer.disconnect();
            stopThemeWatch();
            // Die zwei am Fenster ueberleben das Canvas sonst: sie haengen an
            // window und nicht am Element, das mit ihm verschwindet.
            window.removeEventListener("pointerup", endDrag);
            window.removeEventListener("pointercancel", endDrag);
        },
    };
}
