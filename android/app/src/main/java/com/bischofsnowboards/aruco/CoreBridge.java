package com.bischofsnowboards.aruco;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.nio.ByteBuffer;

/**
 * Der Rechenkern, wie die WebView ihn sieht: ein Aufruf, ein Name, JSON hin und zurueck.
 *
 * <p><b>Ein Einsprungpunkt statt siebzehn.</b> Jede {@code @JavascriptInterface}-Methode ist
 * ein Loch in der Sandbox, und siebzehn Loecher sind siebzehn Stellen, an denen eine
 * Signatur von der JavaScript-Seite abweichen kann - ohne Uebersetzer, der es merkt. Hier
 * gibt es {@link WebBridge#core}, und die Zuordnung Name -&gt; Funktion steht an genau einer
 * Stelle: {@link #call}.
 *
 * <p><b>Warum JSON und nicht Base64-Zahlen.</b> Durch diese Grenze gehen Homographien
 * (neun Werte), Punktlisten (Dutzende) und Konturen (wenige hundert) - nie ein Bild. Beide
 * Seiten schreiben Fliesskommazahlen in der kuerzesten Darstellung, die exakt zurueckliest
 * ({@code Double.toString} hier, {@code JSON.stringify} dort), also ueberlebt jedes Bit den
 * Weg. Nachgemessen wird das nicht hier, sondern in {@code core/tools/ChainCheck.java}: dort
 * laeuft dieselbe JNI-Schicht gegen denselben Kern durch pybind11, bitgenau.
 *
 * <p><b>Bilder gehen NICHT durch diese Grenze.</b> Sie liegen in {@link NativeImages} und
 * werden mit einer Zahl benannt. Ein entzerrtes Raster als Text waere bei 300 dpi
 * zweistellige Megabyte je Reglerzug.
 *
 * <p><b>Synchron, mit Absicht.</b> {@code web/vision/pipeline.js} ist eine gewoehnliche
 * Funktionskette ohne {@code await} zwischen den Rechenschritten - und soll es bleiben, weil
 * genau dieselbe Kette im Browser laeuft. Ein Aufruf ueber diese Bruecke blockiert deshalb
 * den JavaScript-Faden. Das ist der Grund, warum {@link MainActivity} die ganze Kette auf
 * einem Arbeitsfaden anstoesst und nicht auf dem der Oberflaeche.
 */
final class CoreBridge {

    private final NativeImages images;

    CoreBridge(NativeImages images) {
        this.images = images;
    }

    /**
     * Eine Kernfunktion aufrufen.
     *
     * @param method der Name aus {@code web/vision/core-android.js} - dieselbe Schreibweise
     *     wie in {@code core/bindings/web.cpp}, damit beide Bindungen sich lesen wie eine
     * @param arguments ein JSON-Feld mit den Argumenten in der Reihenfolge der Signatur
     * @return das Ergebnis als JSON-Wert (Zahl, Feld oder Objekt)
     */
    Object call(String method, JSONArray arguments) throws JSONException {
        switch (method) {
            case "detectMarkers":
                return detectMarkers(arguments);
            case "homographyFromQuad":
                return numbers(NativeCore.homographyFromQuad(
                        doubles(arguments, 0), doubles(arguments, 1)));
            case "homographyLmeds":
                return numbers(NativeCore.homographyLmeds(
                        doubles(arguments, 0), doubles(arguments, 1)));
            case "refineHomography":
                return numbers(NativeCore.refineHomography(
                        doubles(arguments, 0), doubles(arguments, 1), doubles(arguments, 2)));
            case "fitFree":
                return fitFree(arguments);
            case "poseFromHomography":
                return pose(arguments);
            case "planeExtent":
                return numbers(NativeCore.planeExtent(doubles(arguments, 0),
                        arguments.getInt(1), arguments.getInt(2), doubles(arguments, 3)));
            case "convexHull":
                return numbers(NativeCore.convexHull(doubles(arguments, 0)));
            case "convexIntersectionArea":
                return NativeCore.convexIntersectionArea(
                        doubles(arguments, 0), doubles(arguments, 1));
            case "localPxPerMm":
                return NativeCore.localPxPerMm(
                        doubles(arguments, 0), arguments.getDouble(1), arguments.getDouble(2));
            case "quadArea":
                return NativeCore.quadArea(doubles(arguments, 0));
            case "outputSize":
                return outputSize(arguments);
            case "rectify":
                return rectify(arguments);
            case "adjust":
                return adjust(arguments);
            case "isIdentity":
                return isIdentity(arguments.getJSONObject(0));
            case "findContourMm":
                return findContourMm(arguments);
            case "markerBits":
                return markerBits(arguments);
            default:
                throw new IllegalArgumentException("Der Kern kennt \"" + method + "\" nicht.");
        }
    }

    // --- Die Funktionen mit eigener Antwortform ---------------------------------------

    /** Wie {@code core/bindings/web.cpp}: eine Liste aus {id, corners}. */
    private JSONArray detectMarkers(JSONArray arguments) throws JSONException {
        NativeImages.Image image = images.require(arguments.getInt(0));
        double[] found = NativeCore.detectMarkers(image.pixels, image.width, image.height,
                image.stride(), image.channels, arguments.getBoolean(5));

        JSONArray markers = new JSONArray();
        for (int index = 0; index + NativeCore.VALUES_PER_MARKER <= found.length;
                index += NativeCore.VALUES_PER_MARKER) {
            JSONObject marker = new JSONObject();
            marker.put("id", (int) found[index]);
            JSONArray corners = new JSONArray();
            for (int value = 1; value < NativeCore.VALUES_PER_MARKER; value++) {
                corners.put(found[index + value]);
            }
            marker.put("corners", corners);
            markers.put(marker);
        }
        return markers;
    }

    /** {homography, offsets} - die JNI-Schicht liefert beides in einem Feld. */
    private JSONObject fitFree(JSONArray arguments) throws JSONException {
        double[] flat = NativeCore.fitFree(doubles(arguments, 0), arguments.getDouble(1));
        JSONObject result = new JSONObject();
        JSONArray homography = new JSONArray();
        for (int index = 0; index < 9; index++) {
            homography.put(flat[index]);
        }
        JSONArray offsets = new JSONArray();
        for (int index = 9; index < flat.length; index++) {
            offsets.put(flat[index]);
        }
        result.put("homography", homography);
        result.put("offsets", offsets);
        return result;
    }

    /** {heightMm, nadirMm, tiltDeg} - dieselben Namen wie in web.cpp. */
    private JSONObject pose(JSONArray arguments) throws JSONException {
        double[] values = NativeCore.poseFromHomography(doubles(arguments, 0),
                arguments.getDouble(1), arguments.getInt(2), arguments.getInt(3));
        JSONObject result = new JSONObject();
        result.put("heightMm", values[0]);
        result.put("nadirMm", new JSONArray().put(values[1]).put(values[2]));
        result.put("tiltDeg", values[3]);
        return result;
    }

    /** {width, height} - dieselben Namen wie in web.cpp. */
    private JSONObject outputSize(JSONArray arguments) throws JSONException {
        int[] size = NativeCore.outputSize(arguments.getDouble(0), arguments.getDouble(1),
                arguments.getDouble(2), arguments.getDouble(3), arguments.getDouble(4));
        return new JSONObject().put("width", size[0]).put("height", size[1]);
    }

    /**
     * Entzerren. Zurueck kommt der GRIFF auf das Ergebnis, nicht das Ergebnis.
     *
     * <p>Die Ausgabegroesse wird vorher erfragt und der Puffer danach angelegt - genau die
     * Reihenfolge, die {@code aruco/capi.h} verlangt und die verhindert, dass irgendwo ein
     * Bild angelegt wird, das niemandem gehoert.
     */
    private JSONObject rectify(JSONArray arguments) throws JSONException {
        NativeImages.Image source = images.require(arguments.getInt(0));
        double[] homography = doubles(arguments, 5);
        double x0 = arguments.getDouble(6);
        double y0 = arguments.getDouble(7);
        double x1 = arguments.getDouble(8);
        double y1 = arguments.getDouble(9);
        double pxPerMm = arguments.getDouble(10);
        double sourcePxPerMm = arguments.getDouble(11);

        int[] size = NativeCore.outputSize(x0, y0, x1, y1, pxPerMm);
        int handle = images.allocate(size[0], size[1], 3);
        NativeImages.Image target = images.require(handle);
        NativeCore.rectify(source.pixels, source.width, source.height, source.stride(),
                source.channels, homography, x0, y0, x1, y1, pxPerMm, sourcePxPerMm,
                target.pixels);
        return raster(handle, target);
    }

    private JSONObject adjust(JSONArray arguments) throws JSONException {
        NativeImages.Image source = images.require(arguments.getInt(0));
        JSONObject options = arguments.getJSONObject(5);

        int handle = images.allocate(source.width, source.height, 3);
        NativeImages.Image target = images.require(handle);
        NativeCore.adjust(source.pixels, source.width, source.height, source.stride(),
                source.channels, flag(options, "grayscale"), flag(options, "invert"),
                field(options, "brightness"), field(options, "contrast"),
                field(options, "saturation"), field(options, "localContrast"),
                field(options, "edgeBoost"), field(options, "edgeOverlay"),
                emphasis(options), field(options, "emphasisStrength"),
                field(options, "threshold"), target.pixels);
        return raster(handle, target);
    }

    private boolean isIdentity(JSONObject options) {
        return NativeCore.isIdentity(flag(options, "grayscale"), flag(options, "invert"),
                field(options, "brightness"), field(options, "contrast"),
                field(options, "saturation"), field(options, "localContrast"),
                field(options, "edgeBoost"), field(options, "edgeOverlay"), emphasis(options),
                field(options, "emphasisStrength"), field(options, "threshold"));
    }

    /** Der Umriss, oder JSON-null. Leer heisst "nichts Plausibles" und ist kein Fehler. */
    private Object findContourMm(JSONArray arguments) throws JSONException {
        NativeImages.Image image = images.require(arguments.getInt(0));
        double[] polygon = NativeCore.findContourMm(image.pixels, image.width, image.height,
                image.stride(), image.channels, arguments.getDouble(5));
        return polygon.length == 0 ? JSONObject.NULL : numbers(polygon);
    }

    private JSONArray markerBits(JSONArray arguments) throws JSONException {
        byte[] bits = NativeCore.markerBits(arguments.getInt(0), arguments.getInt(1));
        JSONArray values = new JSONArray();
        for (byte bit : bits) {
            values.put(bit & 0xFF);
        }
        return values;
    }

    // --- Umpacken ---------------------------------------------------------------------

    /** Der Griff plus die Masse - genau das, was {@code takeRaster} weitergibt. */
    private static JSONObject raster(int handle, NativeImages.Image image) throws JSONException {
        return new JSONObject()
                .put("handle", handle)
                .put("width", image.width)
                .put("height", image.height)
                .put("channels", image.channels);
    }

    private static double[] doubles(JSONArray arguments, int index) throws JSONException {
        JSONArray values = arguments.getJSONArray(index);
        double[] flat = new double[values.length()];
        for (int value = 0; value < flat.length; value++) {
            flat[value] = values.getDouble(value);
        }
        return flat;
    }

    private static JSONArray numbers(double[] values) throws JSONException {
        JSONArray array = new JSONArray();
        for (double value : values) {
            array.put(value);
        }
        return array;
    }

    private static boolean flag(JSONObject options, String name) {
        return options.optBoolean(name, false);
    }

    private static double field(JSONObject options, String name) {
        return options.optDouble(name, 0.0);
    }

    /**
     * Der Name der Farbbetonung.
     *
     * <p>Fehlt er, ist es {@code "none"} und nicht der leere Name: ein leerer faende keine
     * Farbe, die Betonung bliebe stumm aus, und der naechste Leser suchte den Fehler in der
     * Farbtabelle. Dieselbe Ueberlegung steht in {@code core/src/capi_support.cpp}.
     */
    private static String emphasis(JSONObject options) {
        String value = options.optString("colorEmphasis", "none");
        return value.isEmpty() ? "none" : value;
    }

    /** Ein Foto als BGR eintragen - die Form, die jede Kernfunktion versteht. */
    int registerPhoto(ByteBuffer bgr, int width, int height) {
        return images.pin(bgr, width, height, NativeCore.CHANNELS_BGR);
    }
}
