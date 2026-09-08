/**
 * pipeline.js - die Rechenkette im Browser. Gegenstueck zu app/pipeline.py.
 *
 * Erkennung, Ausgleich, Pose, Dickenkorrektur, Entzerrung, Aufbereitung, PDF -
 * in derselben Reihenfolge wie dort, mit denselben Zwischenergebnissen. Was auf
 * dem Server eine Sitzung auf der Platte ist, ist hier ein Objekt im Speicher;
 * mehr Unterschied ist es nicht.
 *
 * Die Antwortformen sind ABSICHTLICH die des Servers, Feld fuer Feld. Nur so
 * bleibt app/static/js/ unveraendert - und nur so laesst sich der Ortsbetrieb
 * gegen den Serverbetrieb halten, indem man zwei JSON nebeneinanderlegt.
 */

import * as constants from "../constants.js";
import { buildFooterLines, buildPdf, exportOptions } from "../pdf/build.js";
import { translate } from "../pdf/i18n.js";
import { resolvePose } from "./camera.js";
import { boundingBoxMm, findContourMm } from "./contour.js";
import { withImage } from "./core.js";
import { adjust, adjustOptions, isIdentity } from "./enhance.js";
import {
    defaultCrop,
    extent,
    extrapolationFraction,
    height,
    planeExtent,
    width,
} from "./extent.js";
import { toJpegBytes } from "./image.js";
import { AppError, NoticeList } from "./notices.js";
import {
    checkOutputBudget,
    previewPxPerMm,
    pxPerMmForDpi,
    rectify,
} from "./rectify.js";
import { solve } from "./solve.js";
import { effectiveHomography } from "./thickness.js";

/** Marker im Foto finden. Das Ergebnis ueberlebt die Sitzung - es haengt nur am Foto. */
export function detectMarkers(core, photo) {
    const found = withImage(core, photo.image, (pointer) =>
        core.detectMarkers(
            pointer,
            photo.image.width,
            photo.image.height,
            photo.image.width * photo.image.channels,
            photo.image.channels,
            true,
        ),
    );
    return found.map((marker) => ({
        id: marker.id,
        corners: marker.corners,
        areaPx: core.quadArea(marker.corners),
    }));
}

/** Vom Foto zur entzerrten Vorschau samt Qualitaetsbericht. */
export function runSolve(core, session, request) {
    const started = performance.now();
    const notices = new NoticeList();

    if (session.markers === null) {
        session.markers = detectMarkers(core, session.photo);
    }

    const solution = solve(
        core,
        session.markers,
        request.marker_mm,
        request.mode,
        notices,
        [request.spacing_x_mm, request.spacing_y_mm],
    );

    const pose = resolvePose(
        core,
        solution.homography,
        session.photo.focal35Mm,
        session.photo.image.width,
        session.photo.image.height,
        request.thickness_mm,
        request.camera_height_mm,
        notices,
    );
    const corrected = effectiveHomography(solution.homography, pose, request.thickness_mm);

    const area = planeExtent(
        core,
        corrected.homography,
        session.photo.image.width,
        session.photo.image.height,
        solution.hullMm,
    );
    const crop = defaultCrop(area, solution.hullMm);

    const pxPerMm = previewPxPerMm(area);
    const preview = rectify(
        core,
        session.photo.image,
        corrected.homography,
        area,
        pxPerMm,
        solution.pxPerMm,
    );

    const result = {
        solution,
        pose,
        homographyEffective: corrected.homography,
        correctionFactor: corrected.factor,
        thicknessMm: request.thickness_mm,
        markerMm: request.marker_mm,
        extent: area,
        crop,
        previewPxPerMm: pxPerMm,
        preview,
        adjusted: null,
        notices,
        elapsedS: (performance.now() - started) / 1000.0,
    };
    session.solve = result;
    return result;
}

/**
 * Regler auf die entzerrte Vorschau anwenden - die Antwort fuer den Live-Regler.
 *
 * Gearbeitet wird auf dem bereits berechneten Vorschauraster, nicht auf einer
 * frischen Entzerrung: der Regler soll waehrend des Ziehens antworten, und eine
 * Entzerrung des vollen Fotos dauert um Groessenordnungen laenger. Erlaubt ist
 * die Abkuerzung, weil die Aufbereitung kosmetisch ist - sie taugt am kleinen
 * Bild genau wie am grossen. Verbindlich fuer den Druck ist trotzdem allein der
 * Export: der wendet dieselben Regler auf das volle Raster an.
 */
export function runAdjust(core, session, request) {
    const solved = session.solve;
    if (solved === null) throw new AppError("not_solved", "session_id");

    const options = adjustOptions(request.adjust);
    if (isIdentity(core, options)) {
        solved.adjusted = null;
        return { kind: "rectified", raster: solved.preview };
    }

    solved.adjusted = adjust(core, solved.preview, options);
    return { kind: "adjusted", raster: solved.adjusted };
}

/** Vom gewaehlten Zuschnitt zum druckfertigen PDF. */
export async function runExport(core, session, request) {
    const solved = session.solve;
    if (solved === null) throw new AppError("not_solved", "session_id");

    const locale = normaliseLocale(request.locale);
    const crop = extent(
        request.crop_mm.x0,
        request.crop_mm.y0,
        request.crop_mm.x1,
        request.crop_mm.y1,
    );
    if (width(crop) <= 0.0 || height(crop) <= 0.0) throw new AppError("empty_crop", "crop_mm");

    const pxPerMm = pxPerMmForDpi(request.dpi);
    // Aufbereiten NACH dem Entzerren und VOR allem anderen: die Homographie wurde
    // am unberuehrten Foto gemessen, ab hier aendert sich nur noch Farbe und Ton.
    const options = adjustOptions(request.adjust);

    /** Entzerren, aufbereiten, kodieren - fuer ein Rechteck in Zuschnitt-Millimetern. */
    const render = async (area) => {
        // Dieselbe Pruefung wie bisher, nur auf dem, was wirklich belegt wird.
        // Blattweise ist das ein A4-Blatt und geht ueberall durch; am Stueck ist
        // es der ganze Zuschnitt, und dann soll dieser Abbruch kommen und nicht
        // ein OutOfMemoryError im Entzerren.
        checkOutputBudget(core, area, request.dpi);
        let raster = rectify(
            core,
            session.photo.image,
            solved.homographyEffective,
            area,
            pxPerMm,
            solved.solution.pxPerMm,
        );
        if (!isIdentity(core, options)) {
            raster = adjust(core, raster, options);
        }
        return { raster, jpeg: await toJpegBytes(raster) };
    };

    // Am Stueck oder blattweise - und warum, steht in needsWholeRaster.
    let source;
    let contourMm = null;
    if (needsWholeRaster(request, options)) {
        const whole = await render(crop);
        // Gesucht wird auf dem AUFBEREITETEN Bild - also auf genau dem, das gleich
        // gedruckt wird. Millimeter kostet das nichts: die Aufbereitung faerbt
        // Pixel, sie verschiebt keine.
        contourMm = request.contour ? findContourMm(core, whole.raster, pxPerMm) : null;
        source = whole.jpeg;
    } else {
        // Die Bildquelle fuer web/pdf/build.js: ein Blatt, ein Raster. Der
        // Spitzenbedarf haengt damit am Blatt und nicht mehr am Zuschnitt - genau
        // daran ist der Export auf dem Telefon gescheitert.
        source = async (xMm, yMm, widthMm, heightMm) =>
            (await render(extent(
                crop.x0 + xMm,
                crop.y0 + yMm,
                crop.x0 + xMm + widthMm,
                crop.y0 + yMm + heightMm,
            ))).jpeg;
    }

    const options_ = exportOptions({
        dpi: request.dpi,
        layout: request.layout,
        pageFormat: request.page_format,
        orientation: request.orientation,
        overlapMm: request.overlap_mm,
        printerMarginMm: request.printer_margin_mm,
        pageMarginMm: request.page_margin_mm,
        showScalebar: request.overlays.scalebar,
        showGrid: request.overlays.grid,
        showFooter: request.overlays.footer,
        showMarks: request.overlays.marks,
        tileOverview: request.tile_overview,
        contour: request.contour,
        title: translate("pdf.document_title", locale, {
            width: width(crop).toFixed(0),
            height: height(crop).toFixed(0),
        }),
        locale,
    });

    const footer = buildFooterLines(
        footerMeta(core, session, solved, crop, request, contourMm, locale),
        locale,
    );
    return buildPdf(source, width(crop), height(crop), options_, footer, contourMm);
}

/**
 * Braucht dieser Export das ganze Raster auf einmal?
 *
 * <b>Der Regelfall ist nein</b>, und das ist der Unterschied zwischen einem
 * Export, der auf einem Telefon durchlaeuft, und einem, der es nicht tut: ein
 * Zuschnitt von 810 x 1153 mm sind bei 300 dpi 130 Megapixel und 373 MiB an
 * einem Stueck, ein A4-Blatt derselben Aufloesung sind 26 MB.
 *
 * Blattweise ist das Ergebnis Bit fuer Bit dasselbe, solange nichts ueber
 * Pixelgrenzen hinweg rechnet. Drei Dinge tun das:
 *
 *  - <b>Der Umriss</b> wird auf dem fertigen Bild gesucht. Blattweise faende er
 *    je Blatt einen eigenen und nirgends den ganzen.
 *  - <b>Lokaler Kontrast</b> ist CLAHE: Histogramme ueber ein Gitter, das ueber
 *    das GANZE Bild gelegt wird. Blattweise bekaeme jedes Blatt sein eigenes.
 *  - <b>Kantenschaerfe und Kantenzeichnung</b> greifen in die Nachbarschaft
 *    (Unschaerfemaske bzw. Canny). An der Blattkante fehlt die.
 *
 * Alle drei stehen per Vorgabe aus. Die uebrigen Regler - Helligkeit, Kontrast,
 * Saettigung, Graustufen, Umkehr, Farbbetonung, Schwelle - rechnen Pixel fuer
 * Pixel; sie sind blattweise exakt dasselbe und stehen deshalb nicht hier.
 *
 * Bei einer Einzelseite ist die Frage ohnehin gegenstandslos: dort gibt es nur
 * ein Blatt, und web/pdf/build.js fragt die Quelle dann einmal nach allem.
 */
function needsWholeRaster(request, options) {
    return (
        Boolean(request.contour) ||
        options.local_contrast > 0.0 ||
        options.edge_boost > 0.0 ||
        options.edge_overlay > 0.0
    );
}

/** Die Metadaten der Fusszeile - ein Ausdruck soll spaeter nachvollziehbar sein. */
function footerMeta(core, session, solved, crop, request, contourMm, locale) {
    const pose = solved.pose;
    let camera;
    if (pose.heightMm === null) {
        camera = translate("pdf.footer.camera_unknown", locale);
    } else {
        const tilt =
            pose.tiltDeg === null
                ? ""
                : translate("pdf.footer.camera_tilt", locale, { tilt_deg: pose.tiltDeg.toFixed(0) });
        camera = translate("pdf.footer.camera", locale, {
            height_mm: pose.heightMm.toFixed(0),
            tilt,
            source: pose.source,
        });
    }

    let objectText = translate("pdf.footer.object", locale, {
        width: width(crop).toFixed(1),
        height: height(crop).toFixed(1),
    });
    if (contourMm !== null && contourMm.length >= 2) {
        const [contourWidth, contourHeight] = boundingBoxMm(contourMm);
        objectText += translate("pdf.footer.contour", locale, {
            width: contourWidth.toFixed(1),
            height: contourHeight.toFixed(1),
        });
    }

    // Der Modus IST der Schluessel - fuer jeden gibt es pdf.footer.mode_*.
    const modeKey = solved.solution.mode;
    return {
        object_mm: objectText,
        dpi: request.dpi,
        scale: translate("pdf.footer.scale_source", locale, {
            mm_per_px: solved.solution.mmPerPx.toFixed(4),
        }),
        mode: translate(`pdf.footer.mode_${modeKey}`, locale),
        marker_ids: solved.solution.markers.map((fit) => fit.id).join(","),
        marker_mm: solved.markerMm.toFixed(1),
        rms: `${solved.solution.rmsPx.toFixed(2)} px / ${solved.solution.rmsMm.toFixed(3)} mm`,
        camera,
        thickness: `${solved.thicknessMm.toFixed(1)} mm (k=${solved.correctionFactor.toFixed(5)})`,
        extrapolation: `${(extrapolationFraction(core, crop, solved.solution.hullMm) * 100).toFixed(0)} %`,
        source: session.filename,
        timestamp: timestamp(),
    };
}

/** "2026-09-08 03:47" in der Zeitzone des Geraets - wie datetime.now() am Desktop. */
function timestamp() {
    const now = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    return (
        `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ` +
        `${pad(now.getHours())}:${pad(now.getMinutes())}`
    );
}

function normaliseLocale(value) {
    if (!value) return constants.DEFAULT_LOCALE;
    const primary = String(value).trim().toLowerCase().replace(/_/g, "-").split("-")[0];
    return constants.SUPPORTED_LOCALES.includes(primary) ? primary : constants.DEFAULT_LOCALE;
}

/** Die JSON-Form, die app/static/js/report.js und crop-rect.js erwarten. */
export function solveResponse(session, result, core, previewUrl, detectedUrl, describe) {
    const solution = result.solution;
    const pose = result.pose;

    return {
        session_id: session.id,
        mode_used: solution.mode,
        markers: solution.markers.map((fit) => ({
            id: fit.id,
            corners_px: pairs(fit.cornersPx),
            side_mm_measured: round(fit.sideMmMeasured, 3),
            residual_px: round(fit.residualPx, 3),
            rotation_deg: round(fit.rotationDeg, 2),
        })),
        rms_px: round(solution.rmsPx, 3),
        rms_mm: round(solution.rmsMm, 4),
        mm_per_px: round(solution.mmPerPx, 5),
        camera: {
            source: pose.source,
            focal_px: pose.focalPx === null ? null : round(pose.focalPx, 1),
            height_mm: pose.heightMm === null ? null : round(pose.heightMm, 1),
            nadir_mm: pose.nadirMm === null ? null : pose.nadirMm.map((value) => round(value, 1)),
            tilt_deg: pose.tiltDeg === null ? null : round(pose.tiltDeg, 1),
        },
        thickness_mm: result.thicknessMm,
        scale_correction_k: round(result.correctionFactor, 6),
        hull_mm: pairs(solution.hullMm).map(([x, y]) => [round(x, 3), round(y, 3)]),
        extent_mm: { ...result.extent },
        default_crop_mm: { ...result.crop },
        extrapolation_default: round(
            extrapolationFraction(core, result.crop, solution.hullMm),
            4,
        ),
        preview: {
            url: previewUrl,
            extent_mm: { ...result.extent },
            px_per_mm: round(result.previewPxPerMm, 5),
            detected_url: detectedUrl,
        },
        limits: {
            dpi_choices: [...constants.DPI_CHOICES],
            max_output_mpx: constants.outputBudgetMpx(),
            extrapolation_warn: constants.EXTRAPOLATION_WARN_FRAC,
        },
        elapsed_s: round(result.elapsedS, 2),
        warnings: result.notices.asDicts(describe),
    };
}

function pairs(flat) {
    const points = [];
    for (let index = 0; index < flat.length; index += 2) {
        points.push([flat[index], flat[index + 1]]);
    }
    return points;
}

/** Runden wie Pythons round(x, n) - die Oberflaeche zeigt diese Zahlen an. */
function round(value, digits) {
    const factor = 10 ** digits;
    return Math.round(value * factor) / factor;
}
