package com.bischofsnowboards.aruco;

import android.content.res.AssetManager;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.List;

/**
 * Der Pruefstand aus shared/fixtures/ - auf dem Geraet.
 *
 * <p><b>Das ist der Satz, der hier gestrichen werden soll:</b> „Android ist ungemessen.
 * Punktschluss." (docs/cpp-migration/stage-4-cross-targets.md, Abschnitt 5). Bis jetzt war
 * vom Android-Bau nur belegt, dass er bindet - keine einzige Zahl war gemessen, weil auf
 * dem Bau-Rechner kein Android laeuft. Ein Telefon in der Hand des Benutzers kann das in
 * dreissig Sekunden erledigen, wenn die App den Pruefstand mitbringt. Die beiden
 * eingefrorenen Szenen sind zusammen 160 KB.
 *
 * <p><b>Gemessen wird gegen die GRUNDWAHRHEIT</b>, nicht gegen Windows. Stuende hier das
 * Windows-Ergebnis, erbte Android jede Schiefe jener Messung und niemand saehe es - genau
 * dieselbe Regel wie in core/tests/conformance.cpp.
 *
 * <p><b>Der eine Vorbehalt.</b> Die Szenen liegen als PNG bei und werden von Androids
 * Dekoder gelesen, nicht von dem in cv2. PNG ist verlustfrei und die Dateien tragen weder
 * Farbprofil noch Gamma-Block, es sollte also Byte fuer Byte dasselbe herauskommen -
 * „sollte" ist aber keine Messung. Deshalb meldet dieser Lauf die SHA-256 der dekodierten
 * RGB-Bytes mit. Stimmt sie mit der in docs/cpp-migration/stage-4-android.md ueberein,
 * war der Dekoder derselbe und die Eckenzahlen sind ohne Vorbehalt vergleichbar.
 */
public final class Conformance {

    /** Eine gemessene Szene. */
    public static final class Result {
        public final String scene;
        public final int markersFound;
        public final int markersExpected;
        public final double worstCornerPx;
        public final double meanCornerPx;
        public final double tolerancePx;
        public final long elapsedMs;
        public final String pixelSha256;
        public final List<String> corners = new ArrayList<>();

        Result(String scene, int markersFound, int markersExpected, double worstCornerPx,
                double meanCornerPx, double tolerancePx, long elapsedMs, String pixelSha256) {
            this.scene = scene;
            this.markersFound = markersFound;
            this.markersExpected = markersExpected;
            this.worstCornerPx = worstCornerPx;
            this.meanCornerPx = meanCornerPx;
            this.tolerancePx = tolerancePx;
            this.elapsedMs = elapsedMs;
            this.pixelSha256 = pixelSha256;
        }

        public boolean passed() {
            return markersFound == markersExpected && worstCornerPx <= tolerancePx;
        }
    }

    private Conformance() {}

    /** Beide eingefrorenen Szenen messen. */
    public static JSONObject run(AssetManager assets, boolean dumpCorners) throws Exception {
        JSONArray scenes = new JSONArray();
        boolean allPassed = true;

        for (String name : assets.list("fixtures/expected")) {
            if (!name.endsWith(".json")) {
                continue;
            }
            Result result = measure(assets, "fixtures/expected/" + name, dumpCorners);
            allPassed &= result.passed();

            JSONObject entry = new JSONObject();
            entry.put("scene", result.scene);
            entry.put("passed", result.passed());
            entry.put("markers_found", result.markersFound);
            entry.put("markers_expected", result.markersExpected);
            entry.put("worst_corner_px", result.worstCornerPx);
            entry.put("mean_corner_px", result.meanCornerPx);
            entry.put("tolerance_px", result.tolerancePx);
            entry.put("elapsed_ms", result.elapsedMs);
            entry.put("pixels_sha256_rgb", result.pixelSha256);
            if (dumpCorners) {
                entry.put("corners", new JSONArray(result.corners));
            }
            scenes.put(entry);
        }

        JSONObject report = new JSONObject();
        report.put("passed", allPassed);
        report.put("scenes", scenes);
        report.put("opencv", NativeCore.openCvVersion());
        report.put("dictionary", NativeCore.dictionaryName());
        return report;
    }

    private static Result measure(AssetManager assets, String expectedPath, boolean dumpCorners)
            throws Exception {
        JSONObject expected = new JSONObject(readText(assets, expectedPath));
        String scene = expected.getString("scene");
        double tolerance = expected.getJSONObject("tolerances").getDouble("corner_px");
        JSONObject truth = expected.getJSONObject("marker_corners_px");

        Photo photo;
        try (InputStream stream = assets.open("fixtures/" + expected.getString("image"))) {
            photo = Photo.fromAsset(stream);
        }
        String sha = sha256(photo.rgbBytes());

        // Gemessen wird MIT CLAHE - das ist die Vorgabe des Kerns und das, was
        // tests/test_conformance.py und core/tests/conformance.cpp werten.
        long started = System.nanoTime();
        double[] found = NativeCore.detectMarkers(photo.pixels, photo.width, photo.height,
                photo.stride(), NativeCore.CHANNELS_RGBA, true);
        long elapsedMs = (System.nanoTime() - started) / 1_000_000L;

        int markers = found.length / NativeCore.VALUES_PER_MARKER;
        double worst = 0.0;
        double sum = 0.0;
        int counted = 0;
        List<String> dumped = new ArrayList<>();

        for (int marker = 0; marker < markers; marker++) {
            int base = marker * NativeCore.VALUES_PER_MARKER;
            int id = (int) found[base];
            if (!truth.has(String.valueOf(id))) {
                // Ein Marker, den die Grundwahrheit nicht kennt, ist ein Fehlfund -
                // gewertet wird er ueber markersFound != markersExpected.
                continue;
            }
            JSONArray quad = truth.getJSONArray(String.valueOf(id));
            for (int corner = 0; corner < 4; corner++) {
                JSONArray point = quad.getJSONArray(corner);
                double dx = found[base + 1 + corner * 2] - point.getDouble(0);
                double dy = found[base + 2 + corner * 2] - point.getDouble(1);
                double error = Math.sqrt(dx * dx + dy * dy);
                worst = Math.max(worst, error);
                sum += error;
                counted++;
                if (dumpCorners) {
                    // Dasselbe Format wie aruco_conformance --ecken, damit
                    // core/tools/compare_corners.py die Ausgabe vom Telefon gegen die
                    // von Windows halten kann, ohne dass jemand etwas umschreibt.
                    dumped.add("ecke " + scene + " clahe " + id + " " + corner + " "
                            + found[base + 1 + corner * 2] + " " + found[base + 2 + corner * 2]
                            + " " + error);
                }
            }
        }

        Result result = new Result(scene, markers, truth.length(), worst,
                counted > 0 ? sum / counted : 0.0, tolerance, elapsedMs, sha);
        result.corners.addAll(dumped);
        return result;
    }

    private static String readText(AssetManager assets, String path) throws IOException {
        try (InputStream stream = assets.open(path)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] chunk = new byte[8192];
            int read;
            while ((read = stream.read(chunk)) > 0) {
                out.write(chunk, 0, read);
            }
            return out.toString("UTF-8");
        }
    }

    private static String sha256(byte[] data) throws NoSuchAlgorithmException {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(data);
        StringBuilder text = new StringBuilder(digest.length * 2);
        for (byte value : digest) {
            text.append(Character.forDigit((value >> 4) & 0xF, 16));
            text.append(Character.forDigit(value & 0xF, 16));
        }
        return text.toString();
    }

    /** Sammelt alle Ecken-Zeilen aller Szenen als einen Text. */
    public static String cornerDump(JSONObject report) {
        StringBuilder text = new StringBuilder();
        JSONArray scenes = report.optJSONArray("scenes");
        if (scenes == null) {
            return "";
        }
        for (int index = 0; index < scenes.length(); index++) {
            JSONArray corners = scenes.optJSONObject(index).optJSONArray("corners");
            if (corners == null) {
                continue;
            }
            for (int line = 0; line < corners.length(); line++) {
                text.append(corners.optString(line)).append('\n');
            }
        }
        return text.toString();
    }
}
