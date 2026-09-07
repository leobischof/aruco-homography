/**
 * report.js - der Qualitaetsbericht und die Warnungen aus /api/solve.
 *
 * Der Bericht sagt in drei Toenen, wie weit man dem Ergebnis trauen darf. Die
 * Toene kommen aus tokens.css (--tone-good / --tone-warn / --tone-bad) und sind
 * bewusst nicht --primary/--action/--destructive: als Textfarbe erreichen die
 * auf Weiss 3,42:1 / 1,65:1 / 4,77:1, zwei davon sind unlesbar
 * (design-system.md 3.8).
 *
 * Bemerkenswert an dieser Datei ist, was NICHT darin steht: keine Schwelle. Ob
 * der Restfehler zu gross ist, hat der Server schon entschieden und als Warnung
 * `high_residual` mitgeschickt. Eine zweite Schwelle hier waere eine zweite
 * Wahrheit - und sie waere die, die beim naechsten Mal vergessen wird
 * (AGENTS.md, Invariante 4: config.py ist die einzige Stelle fuer Konstanten).
 */

import { describeNotice } from "./api.js";
import { formatNumber, t } from "./i18n.js";

function card(keyText, valueText, tone) {
    const element = document.createElement("div");
    element.className = tone ? `report-card ${tone}` : "report-card";

    const key = document.createElement("div");
    key.className = "report-key";
    key.textContent = keyText;

    const value = document.createElement("div");
    value.className = "report-value";
    value.textContent = valueText;

    element.append(key, value);
    return element;
}

/** "0: 67,0 mm, 1: 67,1 mm" - die zurueckgerechneten Markerkanten. */
function measuredSides(markers) {
    if (!markers || markers.length === 0) return t("ui.common.empty");
    return markers
        .map((marker) =>
            t("ui.steps.report.value_side", {
                marker_id: marker.id,
                side_mm: formatNumber(marker.side_mm_measured, 1),
            })
        )
        .join(", ");
}

function cameraText(camera) {
    if (!camera || camera.height_mm === null || camera.height_mm === undefined) {
        return t("ui.steps.report.value_camera_unknown");
    }
    const tilt =
        camera.tilt_deg === null || camera.tilt_deg === undefined
            ? t("ui.steps.report.value_tilt_unknown")
            : t("ui.steps.report.value_tilt", { tilt_deg: formatNumber(camera.tilt_deg, 0) });
    return t("ui.steps.report.value_camera", {
        height_mm: formatNumber(camera.height_mm, 0),
        tilt,
    });
}

function thicknessText(data) {
    if (!data.thickness_mm) return t("ui.steps.report.value_thickness_none");
    return t("ui.steps.report.value_thickness", {
        thickness_mm: formatNumber(data.thickness_mm, 1),
        factor: formatNumber(data.scale_correction_k, 4),
    });
}

export function renderReport(reportRoot, warningsRoot, data) {
    const warnings = data.warnings || [];
    // Der Server hat die Schwelle schon angewandt - hier wird sie nur gelesen.
    const residualTone = warnings.some((notice) => notice.code === "high_residual")
        ? "warn"
        : "good";

    const modeKey =
        data.mode_used === "sheet"
            ? "ui.steps.report.value_mode_sheet"
            : "ui.steps.report.value_mode_free";

    reportRoot.replaceChildren(
        card(
            t("ui.steps.report.card_residual"),
            t("ui.steps.report.value_residual", {
                rms_px: formatNumber(data.rms_px, 2),
                rms_mm: formatNumber(data.rms_mm, 2),
            }),
            residualTone
        ),
        card(
            t("ui.steps.report.card_markers"),
            t("ui.steps.report.value_markers", {
                count: data.markers.length,
                mode: t(modeKey),
            })
        ),
        card(t("ui.steps.report.card_sides"), measuredSides(data.markers)),
        card(
            t("ui.steps.report.card_source_resolution"),
            t("ui.steps.report.value_source_resolution", {
                mm_per_px: formatNumber(data.mm_per_px, 4),
            })
        ),
        card(t("ui.steps.report.card_camera"), cameraText(data.camera)),
        card(t("ui.steps.report.card_thickness"), thicknessText(data))
    );

    warningsRoot.replaceChildren(
        ...warnings.map((notice) => {
            const element = document.createElement("div");
            element.className = notice.severity === "info" ? "notice notice-info" : "notice";
            element.textContent = describeNotice(notice);
            return element;
        })
    );
}
