/**
 * crop-geometry.js - die Rechnerei hinter dem Zuschnitt-Rechteck.
 *
 * Reine Funktionen: kein DOM, kein Canvas, kein Zustand. Das ist der Grund fuer
 * die eigene Datei - diese Regeln lassen sich damit einzeln nachrechnen, ohne
 * einen Zeiger ueber ein Bild zu ziehen.
 *
 * Die Funktionen sind einheitenblind. Aufgerufen werden sie sowohl mit
 * Millimetern (das Modell) als auch mit CSS-Pixeln (die Treffererkennung); in
 * beiden Raeumen waechst y nach UNTEN, deshalb heisst kleineres y ueberall
 * "Norden".
 */

/**
 * Kleinster sinnvoller Zuschnitt. 5 mm ist keine gegriffene Zahl, sondern die
 * Untergrenze dessen, was als Schablone noch etwas bedeutet - darunter ist der
 * Ausdruck kleiner als der Strich, mit dem man ihn nachfaehrt.
 */
export const MIN_CROP_MM = 5;

/**
 * Die acht Griffe. fx/fy sind Anteile der Rechteckseite: 0 = die x0-Kante,
 * 0.5 = die Mitte, 1 = die x1-Kante.
 *
 * Die ECKEN stehen vorn, und das ist keine Kosmetik: bei einem kleinen Rechteck
 * ueberlappen sich die 44px-Trefferflaechen aller acht Griffe. Wer zuerst
 * gefunden wird, gewinnt - und eine Ecke, die beide Achsen aendert, ist in
 * diesem Fall fast immer gemeint.
 */
export const HANDLES = [
    { id: "nw", fx: 0.0, fy: 0.0, axes: "xy", cursor: "nwse-resize" },
    { id: "ne", fx: 1.0, fy: 0.0, axes: "xy", cursor: "nesw-resize" },
    { id: "sw", fx: 0.0, fy: 1.0, axes: "xy", cursor: "nesw-resize" },
    { id: "se", fx: 1.0, fy: 1.0, axes: "xy", cursor: "nwse-resize" },
    { id: "n", fx: 0.5, fy: 0.0, axes: "y", cursor: "ns-resize" },
    { id: "s", fx: 0.5, fy: 1.0, axes: "y", cursor: "ns-resize" },
    { id: "w", fx: 0.0, fy: 0.5, axes: "x", cursor: "ew-resize" },
    { id: "e", fx: 1.0, fy: 0.5, axes: "x", cursor: "ew-resize" },
];

export function clamp(value, low, high) {
    return Math.min(Math.max(value, low), high);
}

/** x0 <= x1 und y0 <= y1, ohne die Flaeche zu veraendern. */
export function normaliseRect(rect) {
    return {
        x0: Math.min(rect.x0, rect.x1),
        y0: Math.min(rect.y0, rect.y1),
        x1: Math.max(rect.x0, rect.x1),
        y1: Math.max(rect.y0, rect.y1),
    };
}

/** Jede Kante in den abbildbaren Bereich zwingen. */
export function clampToExtent(rect, extent) {
    const normalised = normaliseRect(rect);
    return {
        x0: clamp(normalised.x0, extent.x0, extent.x1),
        y0: clamp(normalised.y0, extent.y0, extent.y1),
        x1: clamp(normalised.x1, extent.x0, extent.x1),
        y1: clamp(normalised.y1, extent.y0, extent.y1),
    };
}

/**
 * Eine Achse auf die Mindestlaenge bringen - symmetrisch um ihre Mitte und
 * danach in den Bereich geschoben.
 *
 * Symmetrisch, nicht vom Ankerpunkt aus: das passiert nur, wenn jemand ein
 * fast leeres Rechteck losgelassen hat, und dann ist die Mitte des Gemeinten
 * die bessere Vermutung als eine seiner beiden Kanten. Ist der Bereich selbst
 * schmaler als das Mindestmass, gewinnt der Bereich - lieber ein zu kleines
 * Rechteck als eines ausserhalb des Bildes.
 */
function growAxis(low, high, minimum, boundLow, boundHigh) {
    const wanted = Math.min(minimum, boundHigh - boundLow);
    if (high - low >= wanted) return [low, high];

    const centre = (low + high) / 2;
    let newLow = centre - wanted / 2;
    if (newLow < boundLow) newLow = boundLow;
    if (newLow + wanted > boundHigh) newLow = boundHigh - wanted;
    return [newLow, newLow + wanted];
}

export function growToMinimum(rect, extent, minimum = MIN_CROP_MM) {
    const [x0, x1] = growAxis(rect.x0, rect.x1, minimum, extent.x0, extent.x1);
    const [y0, y1] = growAxis(rect.y0, rect.y1, minimum, extent.y0, extent.y1);
    return { x0, y0, x1, y1 };
}

/** Die Lage eines Griffs auf einem Rechteck. */
export function handlePoint(handle, rect) {
    return {
        x: rect.x0 + handle.fx * (rect.x1 - rect.x0),
        y: rect.y0 + handle.fy * (rect.y1 - rect.y0),
    };
}

/** Der Punkt, der beim Ziehen an diesem Griff STEHEN bleibt. */
export function oppositeAnchor(handle, rect) {
    return {
        x: rect.x0 + (1 - handle.fx) * (rect.x1 - rect.x0),
        y: rect.y0 + (1 - handle.fy) * (rect.y1 - rect.y0),
    };
}

/**
 * Welcher Griff liegt nach dem Ziehen unter dem Zeiger?
 *
 * Wer eine Kante ueber ihre Gegenkante hinauszieht, dreht das Rechteck um. Der
 * gegriffene Punkt bleibt dabei am Zeiger - aber er heisst jetzt anders: aus
 * "nw" wird "ne", sobald der Zeiger rechts am Anker vorbeigeht. Ohne diese
 * Umbenennung zeigte der Zeiger den falschen Pfeil und der naechste
 * Zeichendurchgang malte den Griff woanders hin, als er angefasst wurde.
 */
function handleIdFor(axes, anchor, pointer) {
    const horizontal = pointer.x < anchor.x ? "w" : "e";
    const vertical = pointer.y < anchor.y ? "n" : "s";
    if (axes === "x") return horizontal;
    if (axes === "y") return vertical;
    return vertical + horizontal;
}

/**
 * Ein Rechteck aus festgehaltenem Anker und wanderndem Zeiger.
 *
 * `axes` sagt, welche Achsen der Griff ueberhaupt bewegt: eine Ecke beide
 * ("xy"), ein Kantengriff genau eine. Die unbewegte Achse kommt unveraendert
 * aus `base` - dem Rechteck, wie es beim Anfassen aussah.
 */
export function resizeFrom(anchor, pointer, axes, base) {
    const rect = { ...base };
    if (axes === "xy" || axes === "x") {
        rect.x0 = Math.min(anchor.x, pointer.x);
        rect.x1 = Math.max(anchor.x, pointer.x);
    }
    if (axes === "xy" || axes === "y") {
        rect.y0 = Math.min(anchor.y, pointer.y);
        rect.y1 = Math.max(anchor.y, pointer.y);
    }
    return { rect, handleId: handleIdFor(axes, anchor, pointer) };
}

/** Verschieben, Groesse unveraendert, ganz im Bereich bleibend. */
export function moveRect(rect, dx, dy, extent) {
    const width = rect.x1 - rect.x0;
    const height = rect.y1 - rect.y0;
    const x0 = clamp(rect.x0 + dx, extent.x0, Math.max(extent.x0, extent.x1 - width));
    const y0 = clamp(rect.y0 + dy, extent.y0, Math.max(extent.y0, extent.y1 - height));
    return { x0, y0, x1: x0 + width, y1: y0 + height };
}

/**
 * Was liegt unter diesem Punkt? Griff, Rechteckinneres, oder freie Flaeche.
 *
 * `half` ist die halbe Kantenlaenge der Trefferflaeche eines Griffs - deutlich
 * groesser als der gezeichnete Griff. Ein Griff, den man sehen, aber nicht
 * treffen kann, ist am Handy kein Griff.
 */
export function hitTest(point, rect, half) {
    // Der NAECHSTE Griff gewinnt, nicht der erste in der Liste.
    //
    // Solange die Trefferflaechen klein waren, kam das aufs selbe heraus - sie
    // ueberlappten kaum. Fuer einen Finger sind sie groesser (crop-rect.js), und
    // an einem schmalen Rechteck ueberdecken sich dann Ecke und Kantenmitte. Mit
    // "der erste gewinnt" haette die Reihenfolge in HANDLES entschieden, welchen
    // Griff man bekommt: nw vor n, also immer die Ecke, auch wenn der Finger
    // eindeutig auf der Kantenmitte lag. Das ist keine Wahl, das ist ein Zufall
    // mit fester Reihenfolge.
    let best = null;
    for (const handle of HANDLES) {
        const centre = handlePoint(handle, rect);
        const dx = Math.abs(point.x - centre.x);
        const dy = Math.abs(point.y - centre.y);
        if (dx > half || dy > half) continue;
        // Quadrat des Abstands - die Wurzel aendert die Reihenfolge nicht.
        const distance = dx * dx + dy * dy;
        if (best === null || distance < best.distance) best = { handle, distance };
    }
    if (best !== null) return { kind: "resize", handle: best.handle };
    const inside =
        point.x >= rect.x0 && point.x <= rect.x1 && point.y >= rect.y0 && point.y <= rect.y1;
    // "outside" und nicht "new": frueher hiess dieser Fall so, weil eine Geste
    // dort ein NEUES Rechteck aufzog. Das tut sie nicht mehr - der Name benennt
    // jetzt die Lage des Punktes und nicht mehr eine Absicht.
    return { kind: inside ? "move" : "outside", handle: null };
}

/** Zeiger auf den abbildbaren Bereich begrenzen. */
export function clampPoint(point, extent) {
    return {
        x: clamp(point.x, extent.x0, extent.x1),
        y: clamp(point.y, extent.y0, extent.y1),
    };
}
