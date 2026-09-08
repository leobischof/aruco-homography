/**
 * live-overlay.js - was im Sucher ueber das Kamerabild gemalt wird.
 *
 * Getrennt von live.js, weil es zwei Sachen sind: dort der Strom, der Takt und
 * der Ausloeser, hier die Farbe. Zusammen waren sie ueber dreihundert Zeilen
 * Code, und die Naht zwischen beiden ist ohnehin scharf - dieses Modul kennt
 * weder Kamera noch Netz. Es bekommt eine Buehne und eine Antwort und malt.
 *
 * Die Farben kommen per getComputedStyle aus tokens.css und werden beim
 * Themenwechsel NEU gelesen. Ein Canvas loest var() nicht auf; wer die Werte
 * einmal liest und behaelt, malt nach dem Umschalten mit den Farben des anderen
 * Themas. Dieselbe Falle steht in crop-rect.js beschrieben - es ist dieselbe.
 */

import { onThemeChange, readCssThemeVar } from "./theme.js";

/** Laenge der gezeichneten Achsen, als Anteil der mittleren Markerkante. */
const AXIS_SHARE = 0.7;

/** Wieviele Rasterschritte ueber die Markerhuelle hinaus gezeichnet wird. */
const GRID_MARGIN_STEPS = 1;

/** In soviele Stuecke wird eine Rasterlinie zerlegt.
 *
 *  Eine Homographie bildet Geraden auf Geraden ab, zwei Endpunkte wuerden also
 *  genuegen. Bei sehr flachem Blick laeuft eine Linie aber nahe am Horizont, und
 *  dann liegt der eine Endpunkt rechnerisch hinter der Kamera. Zerlegt bleibt der
 *  Fehler oertlich, statt einen Strich quer durchs Bild zu ziehen. */
const GRID_SEGMENTS = 8;

function readColours() {
    return {
        outline: readCssThemeVar("--hull-stroke", "canvastext"),
        halo: readCssThemeVar("--crop-halo", "canvas"),
        axisX: readCssThemeVar("--marker-axis-x", "red"),
        axisY: readCssThemeVar("--marker-axis-y", "orange"),
        grid: readCssThemeVar("--hull-stroke", "canvastext"),
        label: readCssThemeVar("--crop-handle", "canvas"),
        labelInk: readCssThemeVar("--foreground", "canvastext"),
    };
}

/**
 * Ein Maler fuer genau dieses Canvas.
 *
 * `paint` bekommt die Buehne - aus live.js: wo das Video im Canvas wirklich
 * liegt und wie das Erkennungsbild darauf abgebildet wird - und das, was zu
 * sehen ist. Ohne Ebene zeichnet jeder Marker sein eigenes Kreuz; mit Ebene
 * traegt deren Ursprung das gemeinsame, und die Marker bekommen keins.
 */
export function createOverlay(canvas) {
    const context = canvas.getContext("2d");
    let colours = readColours();
    const stopThemeWatch = onThemeChange(() => { colours = readColours(); });

    function toStage(corner, view) {
        return { x: view.left + corner[0] * view.scale, y: view.top + corner[1] * view.scale };
    }

    // ---- Zeichnen ----------------------------------------------------------

    function paint(view, { markers, plane, gridMm }) {
        const ratio = window.devicePixelRatio || 1;
        const backingWidth = Math.max(1, Math.round(view.width * ratio));
        const backingHeight = Math.max(1, Math.round(view.height * ratio));
        if (canvas.width !== backingWidth) canvas.width = backingWidth;
        if (canvas.height !== backingHeight) canvas.height = backingHeight;

        context.setTransform(backingWidth / view.width, 0, 0, backingHeight / view.height, 0, 0);
        context.clearRect(0, 0, view.width, view.height);
        // Das Raster zuerst: es liegt auf der Flaeche, die Marker liegen darauf.
        if (plane) drawPlane(plane, view, gridMm);
        for (const marker of markers) drawMarker(marker, view, plane === null);
    }


    /**
     * Die Ebene, wie sie im Bild liegt: das 50-mm-Raster und ihr Ursprung.
     *
     * Der Rasterschritt ist NICHT hier gewaehlt - er kommt mit der Antwort
     * (`grid_mm`) und ist derselbe, den der Ausdruck aufdruckt. Genau darum geht
     * es: was hier auf dem Werkstueck liegt, liegt spaeter auch auf dem Papier.
     *
     * Gezeichnet wird ueber die Markerhuelle hinaus, aber nur um einen Schritt.
     * Weiter draussen wird die Homographie fortgeschrieben statt gemessen, und
     * ein Raster ueber das ganze Bild behauptete eine Genauigkeit, die dort
     * niemand geprueft hat.
     */
    function drawPlane(found, view, step) {
        const hull = found.hull_mm || [];
        // Ohne Rasterschritt wird KEIN Raster gezeichnet - eine hier erfundene
        // Zahl waere ein zweiter Massstab neben dem, den der Ausdruck aufdruckt,
        // und ein falsches Raster ist schlimmer als keines. Der Schritt kommt
        // mit der Antwort (`grid_mm`), damit er nur einmal auf der Welt steht.
        if (hull.length === 0 || !(step > 0)) return;

        const xs = hull.map((point) => point[0]);
        const ys = hull.map((point) => point[1]);
        const margin = step * GRID_MARGIN_STEPS;
        const x0 = Math.floor((Math.min(...xs) - margin) / step) * step;
        const x1 = Math.ceil((Math.max(...xs) + margin) / step) * step;
        const y0 = Math.floor((Math.min(...ys) - margin) / step) * step;
        const y1 = Math.ceil((Math.max(...ys) + margin) / step) * step;

        context.lineWidth = 1.5;
        context.strokeStyle = colours.grid;
        for (let x = x0; x <= x1 + 1e-6; x += step) gridLine(found, view, [x, y0], [x, y1]);
        for (let y = y0; y <= y1 + 1e-6; y += step) gridLine(found, view, [x0, y], [x1, y]);

        // Der Ursprung der Ebene, in denselben Farben wie die Marker-Achsen: es
        // ist dasselbe Koordinatensystem, nur das gemeinsame statt das eines
        // einzelnen Markers.
        const origin = planePoint(found, view, 0, 0);
        drawAxis(origin, planePoint(found, view, step, 0), Infinity, colours.axisX);
        drawAxis(origin, planePoint(found, view, 0, step), Infinity, colours.axisY);
    }

    /** Ein Punkt der Ebene (mm) an seiner Stelle auf der Buehne. */
    function planePoint(found, view, xMm, yMm) {
        const h = found.homography;
        const w = h[6] * xMm + h[7] * yMm + h[8];
        const px = (h[0] * xMm + h[1] * yMm + h[2]) / w;
        const py = (h[3] * xMm + h[4] * yMm + h[5]) / w;
        return toStage([px, py], view);
    }

    function gridLine(found, view, from, to) {
        context.beginPath();
        for (let piece = 0; piece <= GRID_SEGMENTS; piece += 1) {
            const share = piece / GRID_SEGMENTS;
            const point = planePoint(
                found,
                view,
                from[0] + (to[0] - from[0]) * share,
                from[1] + (to[1] - from[1]) * share,
            );
            if (piece === 0) context.moveTo(point.x, point.y);
            else context.lineTo(point.x, point.y);
        }
        context.stroke();
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
    function drawMarker(marker, view, withAxes) {
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

        // Im Ebenen-Modus haben die Achsen schon einen Ort: den Ursprung der
        // Ebene. Sie hier zu wiederholen ergaebe vier weitere Kreuze, die
        // dasselbe sagen, und verdeckte das Raster.
        if (withAxes) {
            const edge = (edgeLength(points[0], points[1]) + edgeLength(points[0], points[3])) / 2;
            const length = edge * AXIS_SHARE;
            drawAxis(points[0], points[1], length, colours.axisX);
            drawAxis(points[0], points[3], length, colours.axisY);
        }
        drawId(marker.id, points);
    }

    function edgeLength(from, to) {
        return Math.hypot(to.x - from.x, to.y - from.y);
    }

    /** `length` ist die gewuenschte Laenge in Buehnenpixeln; Infinity heisst
     *  "genau bis `towards`" - so weit, wie die Ebene es vorgibt. */
    function drawAxis(origin, towards, length, colour) {
        const span = edgeLength(origin, towards) || 1;
        const reach = Number.isFinite(length) ? length / span : 1;
        const end = {
            x: origin.x + (towards.x - origin.x) * reach,
            y: origin.y + (towards.y - origin.y) * reach,
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
        const head = Math.max(6, edgeLength(origin, end) * 0.22);
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

    /**
     * Was unten steht. Im Ebenen-Modus sind das die zwei Zahlen, um die es geht.
     *
     * Der Restfehler steht neben dem Massstab, weil ein Massstab ohne ihn eine
     * Behauptung ist: dieselben 1,3 mm/px koennen aus einer sauberen Lage
     * kommen oder aus einer verkanteten Flaeche, und nur die zweite Zahl
     * unterscheidet das.
     */
    return {
        paint,
        destroy: stopThemeWatch,
    };
}
