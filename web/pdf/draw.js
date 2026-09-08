/**
 * draw.js - der Zeichenblock: alles, was in app/pdf/ die ReportLab-`Canvas` war.
 *
 * Warum es diese Schicht gibt: die drei portierten Module (branding, overlays,
 * markersheet) sollen sich Zeile fuer Zeile neben ihre Python-Vorlage legen
 * lassen. Waeren sie mit pdf-lib direkt geschrieben, hiesse jede Zeile anders als
 * drueben, und ein Unterschied fiele beim Nebeneinanderlegen nicht mehr auf -
 * genau der Vergleich, der diese Portierung belegt.
 *
 * Zwei Entscheidungen, die hier festgeschrieben sind:
 *
 * 1. **Alles rechnet in Millimetern.** Punkte gibt es nur INNERHALB dieser Datei,
 *    und umgerechnet wird ausschliesslich mit units.js. In app/pdf/ steht in jedem
 *    Modul ein eigenes `_pt()`; das ist dreimal dieselbe Zeile und dreimal die
 *    Gelegenheit, sie verschieden zu schreiben. Schriftgroessen und Strichbreiten
 *    bleiben in Punkt - so stehen sie in der Vorlage und in den Konstanten.
 * 2. **Gezeichnet wird mit den rohen PDF-Operatoren**, nicht mit den bequemen
 *    `page.draw*`-Helfern von pdf-lib. Die setzen bei fehlenden Angaben eigene
 *    Vorgaben (eine Fuellfarbe, wo keine gewollt ist), und was am Ende auf dem
 *    Papier steht, soll hier stehen und nicht in einer fremden Vorgabe.
 *
 * Der Zustand (Schrift, Farben, Strichbreite) wird wie bei ReportLab MITGEFUEHRT:
 * pdf-lib kennt keinen. `saveState`/`restoreState` sichern ihn zusammen mit dem
 * Grafikzustand des PDF, sonst liefe der mitgefuehrte Zustand nach einem `Q`
 * lautlos aus dem Tritt.
 */

import {
    PDFDocument,
    PDFName,
    PDFString,
    StandardFonts,
    appendBezierCurve,
    clip,
    closePath,
    concatTransformationMatrix,
    endPath,
    fill,
    fillAndStroke,
    lineTo,
    moveTo,
    popGraphicsState,
    pushGraphicsState,
    rectangle,
    rgb,
    setDashPattern,
    setFillingColor,
    setLineWidth,
    setStrokingColor,
    stroke,
} from "pdf-lib";

import { mmToPt, ptToMm } from "./units.js";

// Die beiden Schnitte, die app/pdf/ benutzt. Bewusst die PDF-Standardschriften und
// KEINE eingebettete Hausschrift: die Python-Fassung setzt Helvetica, sie ist die
// am Messschieber gepruefte Referenz, und eine andere Schrift aendert jede
// Textbreite - und damit, wo `_fit()` kuerzt und wo der Markenblock endet.
// Standardschriften brauchen ausserdem kein Dateisystem: die Metriken stecken in
// pdf-lib selbst, im Browser genauso wie unter Node.
export const HELVETICA = "Helvetica";
export const HELVETICA_BOLD = "Helvetica-Bold";

const STANDARD_FONTS = {
    [HELVETICA]: StandardFonts.Helvetica,
    [HELVETICA_BOLD]: StandardFonts.HelveticaBold,
};

/** Hex-Farbe wie "#334155" als pdf-lib-Farbe. */
export function colorFromHex(hex) {
    const value = hex.replace("#", "");
    const channel = (index) => parseInt(value.slice(index, index + 2), 16) / 255;
    return rgb(channel(0), channel(2), channel(4));
}

export function grayColor(level) {
    return rgb(level, level, level);
}

/** Farbe aus drei Anteilen 0..1 - fuer die eine Stelle, die keine Markenfarbe ist. */
export function rgbColor(red, green, blue) {
    return rgb(red, green, blue);
}

/**
 * Ein Dokument mit Seiten. Entspricht dem, was in app/pdf/ ein `Canvas` ueber
 * mehrere `showPage()` hinweg ist.
 */
export class Document {
    constructor(pdfDoc, fonts) {
        this.pdfDoc = pdfDoc;
        this.fonts = fonts;
        this.sheets = [];
    }

    static async create({ title, creator }) {
        const pdfDoc = await PDFDocument.create();
        const fonts = {};
        for (const [name, standard] of Object.entries(STANDARD_FONTS)) {
            fonts[name] = await pdfDoc.embedFont(standard);
        }
        if (title !== undefined) pdfDoc.setTitle(title);
        if (creator !== undefined) pdfDoc.setCreator(creator);
        return new Document(pdfDoc, fonts);
    }

    /** Neues Blatt in Millimetern. Entspricht Canvas(pagesize=...) + showPage(). */
    addSheet(widthMm, heightMm) {
        const page = this.pdfDoc.addPage([mmToPt(widthMm), mmToPt(heightMm)]);
        const sheet = new Sheet(this, page);
        this.sheets.push(sheet);
        return sheet;
    }

    /** JPEG-Bytes einmal ins Dokument einbetten; jedes Blatt darf sie benutzen. */
    embedJpeg(bytes) {
        return this.pdfDoc.embedJpg(bytes);
    }

    async save() {
        return this.pdfDoc.save();
    }

    /**
     * Textbreite in Millimetern - das Gegenstueck zu reportlab.stringWidth.
     *
     * Bewusst NICHT `font.widthOfTextAtSize(text, size)`. Das zieht in pdf-lib die
     * Unterschneidung (Kerning) der Buchstabenpaare ab, GEZEICHNET wird der Text
     * aber ohne sie - ein einziges `Tj` kennt keine Paare. Die Zahl passt damit
     * nicht einmal zu dem, was pdf-lib selbst aufs Papier bringt, und bei
     * rechtsbuendigem Text wandert die Zeile um den Fehlbetrag nach rechts.
     *
     * Gemessen an "Bischof Snowboards" in Helvetica-Bold 6,4 pt: 63,3664 pt statt
     * 63,6544 pt, also 0,288 pt = 0,102 mm - der Markenblock stand um genau diesen
     * Betrag daneben, bis die Textmarken beider Erzeuger nebeneinander vermessen
     * wurden.
     *
     * Einzelne Zeichen haben keinen Nachfolger und damit kein Paar; ihre Summe ist
     * die reine Glyphenbreite. Erst mal 1000 (also unskaliert) aufsummieren und
     * dann EINMAL mit der Schriftgroesse multiplizieren - so rechnet auch
     * reportlab.pdfmetrics, und die letzte Stelle stimmt damit exakt ueberein.
     */
    stringWidthMm(text, fontName, sizePt) {
        const font = this.fonts[fontName];
        let units = 0;
        for (const character of text) {
            units += font.widthOfTextAtSize(character, 1000);
        }
        return ptToMm(units * sizePt * 0.001);
    }
}

/** Ein Blatt. Alle Koordinaten in mm, Ursprung linke UNTERE Ecke. */
export class Sheet {
    constructor(document, page) {
        this.document = document;
        this.page = page;
        this.state = {
            fontName: HELVETICA,
            fontSizePt: 12,
            fillColor: rgb(0, 0, 0),
            strokeColor: rgb(0, 0, 0),
            lineWidthPt: 1,
        };
        this.stack = [];
    }

    // --- Zustand ---------------------------------------------------------------
    setFont(fontName, sizePt) {
        this.state.fontName = fontName;
        this.state.fontSizePt = sizePt;
    }

    setFillColor(color) {
        this.state.fillColor = color;
        this.page.pushOperators(setFillingColor(color));
    }

    setStrokeColor(color) {
        this.state.strokeColor = color;
        this.page.pushOperators(setStrokingColor(color));
    }

    setFillGray(level) {
        this.setFillColor(grayColor(level));
    }

    setStrokeGray(level) {
        this.setStrokeColor(grayColor(level));
    }

    setLineWidth(pointsPt) {
        this.state.lineWidthPt = pointsPt;
        this.page.pushOperators(setLineWidth(pointsPt));
    }

    /** Strichbreite, die als MASS gemeint ist (die Kontur) und nicht als Strichstaerke. */
    setLineWidthMm(millimetres) {
        this.setLineWidth(mmToPt(millimetres));
    }

    setDash(onPt, offPt) {
        this.page.pushOperators(setDashPattern([onPt, offPt], 0));
    }

    saveState() {
        this.stack.push({ ...this.state });
        this.page.pushOperators(pushGraphicsState());
    }

    restoreState() {
        this.page.pushOperators(popGraphicsState());
        this.state = this.stack.pop();
    }

    // --- Text ------------------------------------------------------------------
    stringWidthMm(text, fontName = this.state.fontName, sizePt = this.state.fontSizePt) {
        return this.document.stringWidthMm(text, fontName, sizePt);
    }

    drawString(xMm, yMm, text) {
        if (text === "") return;
        this.page.drawText(text, {
            x: mmToPt(xMm),
            y: mmToPt(yMm),
            size: this.state.fontSizePt,
            font: this.document.fonts[this.state.fontName],
            color: this.state.fillColor,
        });
    }

    drawRightString(xMm, yMm, text) {
        this.drawString(xMm - this.stringWidthMm(text), yMm, text);
    }

    drawCentredString(xMm, yMm, text) {
        this.drawString(xMm - this.stringWidthMm(text) / 2.0, yMm, text);
    }

    // --- Formen ----------------------------------------------------------------
    rect(xMm, yMm, widthMm, heightMm, { stroke: doStroke = true, fill: doFill = false } = {}) {
        if (!doStroke && !doFill) return;
        this.page.pushOperators(
            rectangle(mmToPt(xMm), mmToPt(yMm), mmToPt(widthMm), mmToPt(heightMm)),
            doStroke && doFill ? fillAndStroke() : doFill ? fill() : stroke(),
        );
    }

    line(x0Mm, y0Mm, x1Mm, y1Mm) {
        this.page.pushOperators(
            moveTo(mmToPt(x0Mm), mmToPt(y0Mm)),
            lineTo(mmToPt(x1Mm), mmToPt(y1Mm)),
            stroke(),
        );
    }

    /** Linienzug aus [x, y]-Punkten in mm. `close` schliesst ihn zum Umriss. */
    polyline(pointsMm, { close: doClose = false, stroke: doStroke = true, fill: doFill = false } = {}) {
        if (pointsMm.length < 2) return;
        const operators = [moveTo(mmToPt(pointsMm[0][0]), mmToPt(pointsMm[0][1]))];
        for (const [x, y] of pointsMm.slice(1)) {
            operators.push(lineTo(mmToPt(x), mmToPt(y)));
        }
        if (doClose) operators.push(closePath());
        operators.push(doStroke && doFill ? fillAndStroke() : doFill ? fill() : stroke());
        this.page.pushOperators(...operators);
    }

    /** Auf ein Rechteck beschneiden. Gilt bis zum naechsten restoreState(). */
    clipRect(xMm, yMm, widthMm, heightMm) {
        this.page.pushOperators(
            rectangle(mmToPt(xMm), mmToPt(yMm), mmToPt(widthMm), mmToPt(heightMm)),
            clip(),
            endPath(),
        );
    }

    /** Rohe Operatoren - fuer Aufrufer, die eine eigene Matrix brauchen. */
    pushOperators(...operators) {
        this.page.pushOperators(...operators);
    }

    /**
     * Gebackene Vektorzeichnung in ein Quadrat legen (das Logo).
     *
     * `ops` kommt aus web/pdf/assets/, ist in seinem eigenen viewBox-Raum notiert
     * und zaehlt y nach UNTEN wie SVG. Gespiegelt und skaliert wird hier, EINMAL,
     * ueber eine Matrix - nicht Punkt fuer Punkt. Der Grund ist nicht Bequemlichkeit:
     * eine Matrix nimmt auch die Strichbreiten und den Beschnitt mit, und drei
     * Groessen, die sich derselbe Faktor teilen, koennen dann nicht auseinanderlaufen.
     */
    drawVectorArt(ops, viewBox, xMm, yMm, sizeMm) {
        const [minX, minY, boxW, boxH] = viewBox;
        const scale = mmToPt(sizeMm) / boxH;

        this.saveState();
        this.pushOperators(
            concatTransformationMatrix(
                scale,
                0,
                0,
                -scale,
                mmToPt(xMm) - minX * scale,
                mmToPt(yMm + sizeMm) + minY * scale,
            ),
        );
        for (const op of ops) {
            this.pushOperators(pushGraphicsState());
            if (op.clip) {
                this.pushOperators(...pathOperators(op.clip), clip(), endPath());
            }
            if (op.fill) this.pushOperators(setFillingColor(colorFromHex(op.fill)));
            if (op.stroke) {
                this.pushOperators(
                    setStrokingColor(colorFromHex(op.stroke)),
                    setLineWidth(op.strokeWidth),
                );
            }
            this.pushOperators(
                ...pathOperators(op.d),
                op.fill && op.stroke ? fillAndStroke() : op.fill ? fill() : stroke(),
            );
            this.pushOperators(popGraphicsState());
        }
        this.restoreState();
        return (sizeMm * boxW) / boxH;
    }

    // --- Bild ------------------------------------------------------------------
    /**
     * Einen PIXELausschnitt eines eingebetteten Bildes auf ein mm-Rechteck legen.
     *
     * Kein automatisches Skalieren, kein Seitenverhaeltnis: das Rechteck ist
     * massgeblich, der Ausschnitt wird darauf gezogen. Genau das tut die
     * Python-Fassung mit `preserveAspectRatio=False` an einem herausgeschnittenen
     * Teilbild - nur wird hier das GANZE Bild einmal eingebettet und je Kachel
     * anders verschoben und beschnitten. Das Ergebnis ist dasselbe Rechteck aus
     * denselben Pixeln, die Datei aber deutlich kleiner: ein Bildstrom statt einer
     * Kopie je Blatt. Ausserdem braucht der Browser so keinen zweiten Kodierlauf
     * je Kachel - er hat EIN JPEG von der Leinwand und gibt es weiter.
     *
     * EIN gemessener Unterschied bleibt, und er gehoert hierher, weil er sonst
     * wieder gesucht wuerde: die aus beiden PDFs gelesenen Platzierungen stimmen
     * auf 0,00005 mm ueberein, die GERASTERTEN Kachelseiten aber nicht ganz. Der
     * Grund ist der Renderer, nicht die Datei - er legt Bildkanten auf ganze
     * Geraetepixel, und das gerundete Rechteck ist hier das ganze Bild statt der
     * Kachel. Nachgemessen ueber eine Zoomreihe: 189 um bei 3,9 px/mm, 91 um bei
     * 7,9, 59 um bei 15,7, 18 um bei 31,5 - der Betrag halbiert sich mit jeder
     * Verdopplung der Aufloesung und bleibt unter einem halben Geraetepixel. Ein
     * echter geometrischer Versatz waere in Millimetern konstant. Auf dem Ausdruck
     * heisst das bei 600 dpi hoechstens 0,02 mm, und die Dinge, an die man den
     * Messschieber legt - Seitengroesse, Bildrechteck, Raster, Kontrollmassstab -
     * sind Vektor und stimmen exakt.
     */
    drawImageRegion(image, pixelRect, rectMm) {
        const { x0, y0, x1, y1 } = pixelRect;
        const sourceW = x1 - x0;
        const sourceH = y1 - y0;
        const fullW = (rectMm.width * image.width) / sourceW;
        const fullH = (rectMm.height * image.height) / sourceH;
        // Pixelspalte x0 soll auf die linke, Pixelzeile y1 auf die untere Kante des
        // Rechtecks fallen. Zeilen zaehlen im Bild von OBEN, im PDF von unten.
        const originX = rectMm.x - (x0 * rectMm.width) / sourceW;
        const originY = rectMm.y - ((image.height - y1) * rectMm.height) / sourceH;

        this.saveState();
        this.clipRect(rectMm.x, rectMm.y, rectMm.width, rectMm.height);
        this.page.drawImage(image, {
            x: mmToPt(originX),
            y: mmToPt(originY),
            width: mmToPt(fullW),
            height: mmToPt(fullH),
        });
        this.restoreState();
    }

    // --- Verweis ---------------------------------------------------------------
    /** Den Bereich anklickbar machen. Entspricht canvas.linkURL(..., thickness=0). */
    linkURL(url, [x0Mm, y0Mm, x1Mm, y1Mm]) {
        const context = this.document.pdfDoc.context;
        const annotation = context.register(
            context.obj({
                Type: "Annot",
                Subtype: "Link",
                Rect: [mmToPt(x0Mm), mmToPt(y0Mm), mmToPt(x1Mm), mmToPt(y1Mm)],
                Border: [0, 0, 0],
                A: context.obj({ Type: "Action", S: "URI", URI: PDFString.of(url) }),
            }),
        );
        const existing = this.page.node.lookup(PDFName.of("Annots"));
        if (existing) {
            existing.push(annotation);
        } else {
            this.page.node.set(PDFName.of("Annots"), context.obj([annotation]));
        }
    }
}

/** Gebackene Pfadsegmente ["M",x,y] / ["L",...] / ["C",...] / ["Z"] als Operatoren. */
function pathOperators(segments) {
    const operators = [];
    for (const segment of segments) {
        const [command, ...values] = segment;
        if (command === "M") operators.push(moveTo(values[0], values[1]));
        else if (command === "L") operators.push(lineTo(values[0], values[1]));
        else if (command === "C") operators.push(appendBezierCurve(...values));
        else if (command === "Z") operators.push(closePath());
        else throw new Error(`Unbekannter Pfadbefehl: ${command}`);
    }
    return operators;
}
