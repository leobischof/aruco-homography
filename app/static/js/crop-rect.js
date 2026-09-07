/**
 * crop-rect.js - das Zuschnitt-Rechteck auf dem entzerrten Bild.
 *
 * Was hier bedienbar ist, und warum jedes Stueck davon gebraucht wird:
 *
 * - **Acht Griffe** (vier Ecken, vier Kantenmitten). Eine Ecke aendert beide
 *   Achsen, ein Kantengriff genau eine. Vorher liess sich ein bestehendes
 *   Rechteck ueberhaupt nicht mehr aendern - man musste ein neues aufziehen.
 * - **Ziehen im Inneren** verschiebt, Groesse unveraendert.
 * - **Ziehen auf freier Flaeche** zieht ein neues Rechteck auf (die alte Geste,
 *   als Rueckfall erhalten).
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

// Halbe Kantenlaenge der Trefferflaeche: 44px, der Wert von --touch-target.
// Der Griff wird kleiner GEZEICHNET, aber nicht kleiner getroffen.
const HIT_HALF_PX = 22;

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

    function commit(next, live) {
        crop = next;
        draw();
        if (onChange) onChange({ ...crop }, live);
    }

    // ---- Zeigergesten -----------------------------------------------------

    canvas.addEventListener("pointerdown", (event) => {
        if (!scene || !crop || event.button > 0) return;

        // Fokus holen, damit die Pfeiltasten unmittelbar nach dem Ziehen
        // wirken. preventScroll, weil der Sprung sonst die Buehne verschiebt.
        canvas.focus({ preventScroll: true });
        canvas.setPointerCapture(event.pointerId);

        const view = viewport();
        const point = localPoint(event);
        const hit = hitTest(point, rectToPx(crop, view), HIT_HALF_PX);
        const pointer = clampPoint(toMm(point.x, point.y, view), scene.extent);

        if (hit.kind === "resize") {
            drag = {
                pointerId: event.pointerId,
                kind: "resize",
                axes: hit.handle.axes,
                anchor: oppositeAnchor(hit.handle, crop),
                base: { ...crop },
                handleId: hit.handle.id,
            };
        } else if (hit.kind === "move") {
            drag = {
                pointerId: event.pointerId,
                kind: "move",
                grab: { x: pointer.x - crop.x0, y: pointer.y - crop.y0 },
                handleId: null,
            };
        } else {
            // Freie Flaeche: ein neues Rechteck, das im Anfassenpunkt beginnt.
            const seed = { x0: pointer.x, y0: pointer.y, x1: pointer.x, y1: pointer.y };
            drag = {
                pointerId: event.pointerId,
                kind: "resize",
                axes: "xy",
                anchor: pointer,
                base: seed,
                handleId: "se",
            };
            commit(seed, true);
        }
        event.preventDefault();
    });

    canvas.addEventListener("pointermove", (event) => {
        if (!scene || !crop) return;
        const view = viewport();
        const point = localPoint(event);

        if (!drag || drag.pointerId !== event.pointerId) {
            const hit = hitTest(point, rectToPx(crop, view), HIT_HALF_PX);
            canvas.style.cursor =
                hit.kind === "resize" ? hit.handle.cursor : hit.kind === "move" ? "move" : "crosshair";
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
            canvas.style.cursor = CURSOR_BY_ID[result.handleId] || "crosshair";
            commit(clampToExtent(result.rect, scene.extent), true);
        }
        event.preventDefault();
    });

    function endDrag(event) {
        if (!drag || drag.pointerId !== event.pointerId) return;
        drag = null;
        hoverId = null;
        if (canvas.hasPointerCapture(event.pointerId)) {
            canvas.releasePointerCapture(event.pointerId);
        }
        // Erst beim Loslassen die Mindestgroesse durchsetzen. Waehrend des
        // Ziehens waere sie im Weg: der gegriffene Griff soll am Zeiger kleben,
        // auch wenn das Rechteck kurzzeitig fast nichts umschliesst.
        commit(growToMinimum(clampToExtent(crop, scene.extent), scene.extent), false);
    }

    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);

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
        },
    };
}
