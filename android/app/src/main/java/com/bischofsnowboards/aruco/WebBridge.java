package com.bischofsnowboards.aruco;

import android.util.Base64;
import android.webkit.JavascriptInterface;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Die Bruecke: was die WebView vom Geraet erfragen darf, und sonst nichts.
 *
 * <p><b>Jede Methode hier ist ein Loch in der Sandbox.</b> Alles, was mit
 * {@code @JavascriptInterface} gekennzeichnet ist, kann jedes Skript aufrufen, das in
 * dieser WebView laeuft. Deshalb ist die Liste kurz, jede Methode nimmt nur einfache
 * Werte, und keine nimmt einen Pfad entgegen - Dateien werden ueber Systemdialoge
 * gewaehlt, nicht ueber Zeichenketten aus JavaScript.
 *
 * <p><b>Zwei Sorten Methode.</b> Was sofort antwortet, gibt JSON zurueck. Was dauert oder
 * auf den Benutzer wartet, bekommt eine {@code callId} und meldet sich spaeter ueber
 * {@link MainActivity#resolve}. Der Grund ist nicht Eleganz: ein Aufruf ueber diese
 * Bruecke blockiert den JavaScript-Faden der Seite, bis er zurueckkehrt. Eine Erkennung
 * auf einem 12-MP-Foto dauert Sekunden - synchron aufgerufen stuende die Oberflaeche so
 * lange, ohne Wartezeichen und ohne Reaktion.
 */
public final class WebBridge {

    private final MainActivity activity;

    WebBridge(MainActivity activity) {
        this.activity = activity;
    }

    /**
     * Was der Kern und das Geraet ueber sich sagen.
     *
     * <p>Die Konstanten kommen aus dem NATIVEN Kern und damit aus shared/constants.json -
     * nicht aus einer zweiten Liste in JavaScript (AGENTS.md, Invariante 4). Zeigte die
     * Oberflaeche eine andere Markerkante an als der Kern benutzt, waere das ein Fehler in
     * Millimetern, und man saehe ihn erst am Ausdruck.
     */
    @JavascriptInterface
    public String nativeInfo() {
        try {
            JSONObject info = new JSONObject();
            info.put("opencv", NativeCore.openCvVersion());
            info.put("dictionary", NativeCore.dictionaryName());
            info.put("dictionary_size", NativeCore.dictionarySize());
            info.put("marker_mm_nominal", NativeCore.markerMmNominal());
            info.put("abi", android.os.Build.SUPPORTED_ABIS.length > 0
                    ? android.os.Build.SUPPORTED_ABIS[0] : "?");
            info.put("device", android.os.Build.MANUFACTURER + " " + android.os.Build.MODEL);
            info.put("android", android.os.Build.VERSION.RELEASE);
            info.put("sdk", android.os.Build.VERSION.SDK_INT);
            info.put("app_version", activity.appVersionName());
            info.put("webview", activity.webViewVersion());
            // Die Seitengroesse des Systems. Auf einem 16-KB-Geraet steht hier 16384 -
            // und genau dort laedt eine nur auf 4 KB ausgerichtete .so nicht.
            info.put("page_size", activity.systemPageSize());
            return ok(info);
        } catch (Exception failure) {
            return error(failure);
        }
    }

    /**
     * Die Modulbits eines Markers, als Zahlenfeld fuer web/pdf/markersheet.js.
     *
     * <p>Synchron, weil es 36 Bytes sind und der Aufruf Mikrosekunden dauert. Das
     * Markerblatt braucht vier davon.
     */
    @JavascriptInterface
    public String markerBits(int markerId, int modules) {
        try {
            byte[] bits = NativeCore.markerBits(markerId, modules);
            JSONArray values = new JSONArray();
            for (byte bit : bits) {
                values.put(bit & 0xFF);
            }
            JSONObject payload = new JSONObject();
            payload.put("bits", values);
            return ok(payload);
        } catch (Exception failure) {
            return error(failure);
        }
    }

    /** Einen Systemdialog zur Fotowahl oeffnen. Antwort ueber {@code callId}. */
    @JavascriptInterface
    public void pickPhoto(long callId) {
        activity.pickPhoto(callId);
    }

    /** Die Kamera-App des Systems bitten, ein Foto zu machen. Antwort ueber {@code callId}. */
    @JavascriptInterface
    public void takePhoto(long callId) {
        activity.takePhoto(callId);
    }

    /**
     * Das Bild laden, das die WebView selbst gewaehlt hat.
     *
     * <p>Dafuer gibt es diesen zweiten Weg neben {@link #pickPhoto}: die unveraenderte
     * Oberflaeche hat ein {@code <input type="file">}, und dessen Dialog oeffnet Android
     * ueber {@code onShowFileChooser} - nicht die Bruecke. Die URI liegt danach im
     * Java-Teil, das {@code File}-Objekt in JavaScript. Statt die Bytes als Base64
     * zurueckzureichen (bei 12 MP rund 48 MB Text), laedt die native Seite aus der URI,
     * die sie ohnehin schon hat.
     */
    @JavascriptInterface
    public void loadPickedPhoto(long callId) {
        activity.loadPickedPhoto(callId);
    }

    /**
     * Das zuletzt gewaehlte Foto durch den nativen Detektor schicken.
     *
     * <p>Kein Bildinhalt geht durch diese Bruecke. Das Foto liegt seit
     * {@link #pickPhoto} als direkter Puffer im Java-Teil; ein 12-MP-Bild als
     * Base64-Zeichenkette durch die JavaScript-Grenze zu schieben waere rund 48 MB Text.
     */
    @JavascriptInterface
    public void detectMarkers(long callId, boolean enhanceContrast) {
        activity.detectMarkers(callId, enhanceContrast);
    }

    /** Den Pruefstand aus shared/fixtures/ auf diesem Geraet laufen lassen. */
    @JavascriptInterface
    public void runConformance(long callId, boolean dumpCorners) {
        activity.runConformance(callId, dumpCorners);
    }

    /**
     * Ein PDF speichern. Der Benutzer waehlt den Ort im Systemdialog.
     *
     * <p>Die Bytes kommen als Base64 - ein A4-Markerblatt sind wenige Dutzend Kilobyte,
     * das traegt die Bruecke ohne weiteres. Fuer ein gekacheltes Schablonen-PDF mit
     * eingebettetem Raster gilt das nicht mehr; wenn dieser Weg spaeter dafuer gebraucht
     * wird, gehoert das Bild vorher auf die native Seite und nicht durch diese Grenze.
     */
    @JavascriptInterface
    public void savePdf(long callId, String base64, String filename) {
        try {
            activity.savePdf(callId, Base64.decode(base64, Base64.DEFAULT), filename);
        } catch (IllegalArgumentException failure) {
            activity.resolveError(callId, "Base64 nicht lesbar: " + failure.getMessage());
        }
    }

    /** Dasselbe, aber zum Teilen (Drucken, Mail, Cloud) statt zum Ablegen. */
    @JavascriptInterface
    public void sharePdf(long callId, String base64, String filename) {
        try {
            activity.sharePdf(callId, Base64.decode(base64, Base64.DEFAULT), filename);
        } catch (IllegalArgumentException failure) {
            activity.resolveError(callId, "Base64 nicht lesbar: " + failure.getMessage());
        }
    }

    /** Zu einer anderen Seite der App wechseln (die Oberflaeche, oder zurueck). */
    @JavascriptInterface
    public void navigate(String path) {
        activity.navigateTo(path);
    }

    // --- Antwortform -------------------------------------------------------------
    // Immer {ok: bool, ...} - eine Antwort ohne Rahmen zwaenge jeden Aufrufer, zwischen
    // "Ergebnis" und "Fehlermeldung" selbst zu unterscheiden, und irgendeiner tut es
    // dann nicht.

    static String ok(JSONObject payload) throws org.json.JSONException {
        payload.put("ok", true);
        return payload.toString();
    }

    static String error(Throwable failure) {
        String message = failure.getMessage();
        if (message == null || message.isEmpty()) {
            message = failure.getClass().getSimpleName();
        }
        // Von Hand gebaut und nicht ueber JSONObject: wer hier eine Ausnahme faengt, will
        // nicht, dass das Verpacken der Meldung eine zweite wirft.
        return "{\"ok\":false,\"error\":" + JSONObject.quote(message) + "}";
    }
}
