"use strict";

// Zustand der Sitzung. Alles, was der Server geliefert hat, steht hier einmal.
const state = {
  sessionId: null,
  solve: null,        // Antwort von /api/solve
  crop: null,         // {x0, y0, x1, y1} in mm
};

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");

// --- Transport ---------------------------------------------------------------

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) throw payload;
  return payload;
}

function busy(text) {
  $("busy-text").textContent = text;
  show("busy");
}

function showError(error) {
  const message = error && error.message ? error.message : String(error);
  const field = error && error.field ? ` (Feld: ${error.field})` : "";
  alert(message + field);
}

// --- 1: Upload ---------------------------------------------------------------

$("file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  busy("Lade Foto…");
  try {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch("/api/upload", { method: "POST", body: form });
    const payload = await response.json();
    if (!response.ok) throw payload;

    state.sessionId = payload.session_id;
    const focal = payload.exif.focal35_mm;
    $("upload-info").innerHTML =
      `<b>${payload.filename}</b> - ${payload.width} x ${payload.height} px<br>` +
      (focal
        ? `EXIF-Brennweite ${focal} mm (KB-Aequivalent) - Kamerahoehe kann automatisch bestimmt werden.`
        : "Keine EXIF-Brennweite gefunden - fuer eine Dickenkorrektur bitte den Kameraabstand eintragen.");
    show("upload-info");
    show("step-params");
    applyDefaults(payload.defaults);
  } catch (error) {
    showError(error);
  } finally {
    hide("busy");
  }
});

// Die Vorgabewerte kommen vom Server (app/config.py ist die einzige Quelle).
function applyDefaults(defaults) {
  const select = $("dpi");
  select.innerHTML = "";
  for (const dpi of defaults.dpi_choices) {
    const option = document.createElement("option");
    option.value = dpi;
    option.textContent = `${dpi} dpi`;
    option.selected = dpi === defaults.dpi;
    select.appendChild(option);
  }

  $("marker-mm").value = defaults.marker_mm;
  $("spacing-x").value = defaults.spacing_x_mm;
  $("spacing-y").value = defaults.spacing_y_mm;
  $("overlap").value = defaults.overlap_mm;
  updateModeFields();
}

// Im Frei-Modus sind die Abstaende bedeutungslos - dann verschwinden sie auch.
function updateModeFields() {
  const isSheet = $("mode").value === "sheet";
  for (const element of document.querySelectorAll(".sheet-only")) {
    element.classList.toggle("hidden", !isSheet);
  }
}

$("mode").addEventListener("change", updateModeFields);

// Das gedruckte Blatt soll dieselben Masse haben, die oben eingetragen sind.
function updateSheetLink() {
  const marker = parseFloat($("marker-mm").value);
  const spacingX = parseFloat($("spacing-x").value);
  const spacingY = parseFloat($("spacing-y").value);
  if (![marker, spacingX, spacingY].every(Number.isFinite)) return;
  $("sheet-link").href =
    `/api/markersheet?marker_mm=${marker}&spacing_x_mm=${spacingX}&spacing_y_mm=${spacingY}`;
}
for (const id of ["marker-mm", "spacing-x", "spacing-y"]) {
  $(id).addEventListener("change", updateSheetLink);
}

// --- 2: Entzerren ------------------------------------------------------------

$("solve").addEventListener("click", async () => {
  busy("Suche Marker und rechne…");
  try {
    const cameraHeight = parseFloat($("camera-height").value);
    state.solve = await postJson("/api/solve", {
      session_id: state.sessionId,
      marker_mm: parseFloat($("marker-mm").value),
      mode: $("mode").value,
      thickness_mm: parseFloat($("thickness").value) || 0,
      camera_height_mm: Number.isFinite(cameraHeight) ? cameraHeight : null,
      spacing_x_mm: parseFloat($("spacing-x").value),
      spacing_y_mm: parseFloat($("spacing-y").value),
    });

    renderReport(state.solve);
    setCrop(state.solve.default_crop_mm);
    $("preview").src = state.solve.preview.url;
    $("preview").onload = drawOverlay;
    show("step-report");
    show("step-crop");
    show("step-export");
  } catch (error) {
    showError(error);
  } finally {
    hide("busy");
  }
});

// --- 3: Qualitaetsbericht ----------------------------------------------------

function card(key, value, tone) {
  return `<div class="card ${tone || ""}"><div class="k">${key}</div><div class="v">${value}</div></div>`;
}

function renderReport(data) {
  const camera = data.camera;
  const rmsTone = data.rms_mm > 1.0 ? "warn" : "good";
  const markerText = data.markers
    .map((m) => `${m.id}: ${m.side_mm_measured.toFixed(1)} mm`)
    .join(" | ");

  $("report").innerHTML =
    card("Restfehler", `${data.rms_px.toFixed(2)} px / ${data.rms_mm.toFixed(2)} mm`, rmsTone) +
    card("Marker", `${data.markers.length} (${data.mode_used === "sheet" ? "Blatt" : "frei"})`) +
    card("Gemessene Kanten", markerText || "-") +
    card("Aufloesung Quelle", `${data.mm_per_px.toFixed(4)} mm/px`) +
    card(
      "Kamera",
      camera.height_mm
        ? `${camera.height_mm.toFixed(0)} mm, ${camera.tilt_deg !== null ? camera.tilt_deg.toFixed(0) + " Grad" : "Neigung n/a"}`
        : "unbekannt"
    ) +
    card(
      "Dickenkorrektur",
      data.thickness_mm ? `${data.thickness_mm} mm, k=${data.scale_correction_k.toFixed(4)}` : "keine"
    );

  $("warnings").innerHTML = (data.warnings || [])
    .map((w) => `<div class="note ${w.severity === "info" ? "info" : ""}">${w.message}</div>`)
    .join("");
}

// --- 4: Zuschnitt ------------------------------------------------------------

const overlay = $("overlay");

function previewGeometry() {
  const extent = state.solve.preview.extent_mm;
  const image = $("preview");
  return {
    extent,
    scaleX: image.clientWidth / (extent.x1 - extent.x0),
    scaleY: image.clientHeight / (extent.y1 - extent.y0),
  };
}

function mmToCanvas(x, y) {
  const g = previewGeometry();
  return [(x - g.extent.x0) * g.scaleX, (y - g.extent.y0) * g.scaleY];
}

function canvasToMm(px, py) {
  const g = previewGeometry();
  return [g.extent.x0 + px / g.scaleX, g.extent.y0 + py / g.scaleY];
}

function setCrop(crop) {
  state.crop = { ...crop };
  for (const key of ["x0", "y0", "x1", "y1"]) $(key).value = crop[key].toFixed(1);
  drawOverlay();
  updateCropInfo();
}

for (const key of ["x0", "y0", "x1", "y1"]) {
  $(key).addEventListener("change", () => {
    const crop = {};
    for (const k of ["x0", "y0", "x1", "y1"]) crop[k] = parseFloat($(k).value);
    if (Object.values(crop).every(Number.isFinite)) setCrop(normalise(crop));
  });
}

function normalise(crop) {
  return {
    x0: Math.min(crop.x0, crop.x1),
    y0: Math.min(crop.y0, crop.y1),
    x1: Math.max(crop.x0, crop.x1),
    y1: Math.max(crop.y0, crop.y1),
  };
}

let dragStart = null;

overlay.addEventListener("pointerdown", (event) => {
  overlay.setPointerCapture(event.pointerId);
  dragStart = localPoint(event);
});

overlay.addEventListener("pointermove", (event) => {
  if (!dragStart) return;
  const now = localPoint(event);
  const [x0, y0] = canvasToMm(dragStart[0], dragStart[1]);
  const [x1, y1] = canvasToMm(now[0], now[1]);
  state.crop = normalise({ x0, y0, x1, y1 });
  drawOverlay();
  updateCropInfo();
});

overlay.addEventListener("pointerup", () => {
  dragStart = null;
  if (state.crop) setCrop(state.crop);
});

function localPoint(event) {
  const rect = overlay.getBoundingClientRect();
  return [event.clientX - rect.left, event.clientY - rect.top];
}

function drawOverlay() {
  if (!state.solve) return;
  const image = $("preview");
  overlay.width = image.clientWidth;
  overlay.height = image.clientHeight;

  const context = overlay.getContext("2d");
  context.clearRect(0, 0, overlay.width, overlay.height);

  // Marker-Huelle: innerhalb davon ist die Homographie gemessen, ausserhalb geraten.
  const hull = state.solve.hull_mm;
  if (hull && hull.length > 2) {
    context.beginPath();
    hull.forEach((point, index) => {
      const [x, y] = mmToCanvas(point[0], point[1]);
      index === 0 ? context.moveTo(x, y) : context.lineTo(x, y);
    });
    context.closePath();
    context.fillStyle = "rgba(78, 201, 122, .14)";
    context.strokeStyle = "rgba(78, 201, 122, .8)";
    context.lineWidth = 1.5;
    context.fill();
    context.stroke();
  }

  if (!state.crop) return;
  const [cx0, cy0] = mmToCanvas(state.crop.x0, state.crop.y0);
  const [cx1, cy1] = mmToCanvas(state.crop.x1, state.crop.y1);
  context.strokeStyle = "#4da3ff";
  context.lineWidth = 2;
  context.setLineDash([6, 4]);
  context.strokeRect(cx0, cy0, cx1 - cx0, cy1 - cy0);
  context.setLineDash([]);
}

// Extrapolationsanteil: Rasterabtastung gegen die Huelle. Genau genug fuer die
// Anzeige; der exakte Wert kommt vom Server in die PDF-Fusszeile.
function extrapolationFraction() {
  const hull = state.solve.hull_mm;
  if (!hull || hull.length < 3 || !state.crop) return 0;

  const steps = 40;
  let outside = 0;
  for (let i = 0; i < steps; i++) {
    for (let j = 0; j < steps; j++) {
      const x = state.crop.x0 + ((i + 0.5) / steps) * (state.crop.x1 - state.crop.x0);
      const y = state.crop.y0 + ((j + 0.5) / steps) * (state.crop.y1 - state.crop.y0);
      if (!pointInPolygon(x, y, hull)) outside++;
    }
  }
  return outside / (steps * steps);
}

function pointInPolygon(x, y, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function updateCropInfo() {
  if (!state.crop || !state.solve) return;
  const width = state.crop.x1 - state.crop.x0;
  const height = state.crop.y1 - state.crop.y0;
  const dpi = parseInt($("dpi").value || "300", 10);
  const pixels = (width * dpi) / 25.4;
  const pixelsY = (height * dpi) / 25.4;
  const megapixels = (pixels * pixelsY) / 1e6;
  const fraction = extrapolationFraction();
  const limit = state.solve.limits.extrapolation_warn;

  $("crop-info").innerHTML =
    `<b>${width.toFixed(1)} x ${height.toFixed(1)} mm</b> - ` +
    `${Math.round(pixels)} x ${Math.round(pixelsY)} px bei ${dpi} dpi (${megapixels.toFixed(1)} MPixel)` +
    (megapixels > state.solve.limits.max_output_mpx
      ? ` <span style="color:var(--bad)">- ueber der Grenze von ${state.solve.limits.max_output_mpx} MPixel</span>`
      : "") +
    `<br>Extrapolation ausserhalb der Marker-Huelle: <b>${(fraction * 100).toFixed(0)} %</b>` +
    (fraction > limit ? ' <span style="color:var(--warn)">- dort wird die Entzerrung unsicher</span>' : "");
}

$("dpi").addEventListener("change", updateCropInfo);
window.addEventListener("resize", () => {
  drawOverlay();
});

// --- 5: Export ---------------------------------------------------------------

$("export").addEventListener("click", async () => {
  busy("Erzeuge PDF…");
  try {
    const response = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        crop_mm: state.crop,
        dpi: parseInt($("dpi").value, 10),
        layout: $("layout").value,
        page_format: $("page-format").value,
        overlap_mm: parseFloat($("overlap").value) || 0,
        overlays: {
          scalebar: $("ov-scalebar").checked,
          grid: $("ov-grid").checked,
          footer: $("ov-footer").checked,
          marks: $("ov-marks").checked,
        },
        tile_overview: $("ov-overview").checked,
        contour: $("ov-contour").checked,
        filename: "schablone.pdf",
      }),
    });

    if (!response.ok) throw await response.json();

    const pageSize = response.headers.get("X-Page-Size-Mm");
    const pages = response.headers.get("X-Pages");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = "schablone.pdf";
    link.click();
    URL.revokeObjectURL(url);

    $("export-info").innerHTML =
      `PDF erzeugt: <b>${pages}</b> Seite(n), Seitenformat <b>${pageSize} mm</b>. ` +
      "Beim Drucken unbedingt <b>100 % / keine Skalierung</b> waehlen und danach den " +
      "aufgedruckten 100-mm-Massstab nachmessen.";
  } catch (error) {
    showError(error);
  } finally {
    hide("busy");
  }
});
