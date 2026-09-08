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
            // Wieviele Ausgabepixel dieses Geraet vertraegt. Die Seite senkt damit
            // ihre eigene Obergrenze (bridge-shim.js -> web/constants.js), damit der
            // Export mit einer verstaendlichen Meldung abbricht statt mit einem
            // OutOfMemoryError mitten im Entzerren.
            info.put("max_output_mpx", NativeImages.budgetMegapixels(activity));
            return ok(info);
        } catch (Throwable failure) {
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
        } catch (Throwable failure) {
            return error(failure);
        }
    }

    /**
     * Eine Funktion des Rechenkerns aufrufen. Die ganze Messkette geht hier durch.
     *
     * <p><b>Ein Loch statt siebzehn.</b> Jede Methode dieser Klasse ist von jedem Skript in
     * dieser WebView aus erreichbar. Die siebzehn Kernfunktionen einzeln zu oeffnen waeren
     * siebzehn Signaturen, die zur JavaScript-Seite passen muessen und die kein Uebersetzer
     * vergleicht. Die Zuordnung Name -&gt; Funktion steht deshalb an einer Stelle:
     * {@link CoreBridge#call}.
     *
     * <p><b>Synchron, und das ist Absicht.</b> {@code web/vision/pipeline.js} ist eine
     * gewoehnliche Funktionskette ohne {@code await} zwischen den Rechenschritten - und muss
     * es bleiben, weil genau dieselbe Datei im Browser laeuft. Der Aufruf blockiert also den
     * JavaScript-Faden der Seite, so wie WebAssembly es im Browser auch tut. Die Oberflaeche
     * des Systems bleibt bedienbar: diese Methode laeuft auf Androids JavaBridge-Faden und
     * nicht auf dem der Anzeige.
     *
     * <p><b>Bilder gehen hier NICHT durch.</b> Sie liegen in {@link NativeImages} und heissen
     * nach aussen nur noch eine Zahl.
     *
     * @param method der Name, wie ihn {@code core/bindings/web.cpp} vergibt
     * @param arguments die Argumente als JSON-Feld, in der Reihenfolge der Signatur
     */
    @JavascriptInterface
    public String core(String method, String arguments) {
        try {
            Object value = activity.core().call(method, new JSONArray(arguments));
            JSONObject payload = new JSONObject();
            payload.put("value", value);
            return ok(payload);
        } catch (Throwable failure) {
            return error(failure);
        }
    }

    /** Der Griff auf das geladene Foto - die Eingabe jedes Rechenschritts. */
    @JavascriptInterface
    public String photoHandle() {
        try {
            return ok(new JSONObject().put("handle", activity.photoHandle()));
        } catch (Throwable failure) {
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

    /**
     * Ein Einzelbild des Suchers uebernehmen - erst {@link #appendBytes}, dann dies.
     *
     * <p>Antwort ueber {@code callId}: dekodiert wird mit {@code BitmapFactory} auf dem
     * Arbeitsfaden. Zurueck kommt nur der Griff samt Groesse - Bildinhalt geht durch
     * diese Bruecke nie.
     *
     * <p>Nicht zu verwechseln mit {@link #loadPickedPhoto}: das ist das GEWAEHLTE Foto
     * und die Eingabe der ganzen Kette; dies hier ist ein fluechtiges Bild, das nach der
     * Erkennung wieder verschwindet. Sitzung und Foto bleiben unberuehrt.
     */
    @JavascriptInterface
    public void decodeFrame(long callId) {
        activity.decodeFrame(callId);
    }

    /**
     * Ein Einzelbild wieder hergeben.
     *
     * <p>Synchron, weil es ein Eintrag aus einer Map ist. Ein unbekannter Griff ist kein
     * Fehler - siehe {@code NativeImages.releaseFrame}.
     */
    @JavascriptInterface
    public String releaseFrame(int handle) {
        try {
            activity.releaseFrame(handle);
            return ok(new JSONObject());
        } catch (Throwable failure) {
            return error(failure);
        }
    }

    /** Den Pruefstand aus shared/fixtures/ auf diesem Geraet laufen lassen. */
    @JavascriptInterface
    public void runConformance(long callId, boolean dumpCorners) {
        activity.runConformance(callId, dumpCorners);
    }

    /**
     * Eine Scheibe der Datei herueberreichen. Danach {@link #saveFile} oder
     * {@link #sharePdf}.
     *
     * <p><b>In Scheiben und nicht am Stueck.</b> Ein A4-Markerblatt sind wenige Dutzend
     * Kilobyte - das ginge auch in einem Zug. Ein gekacheltes Schablonen-PDF mit
     * eingebettetem 300-dpi-Raster sind zweistellige Megabyte, als Base64 ein Drittel mehr,
     * und eine einzelne Zeichenkette dieser Groesse stuende zweimal im Speicher: einmal als
     * JavaScript-String, einmal als Java-String, waehrend gleichzeitig das Rasterbild noch
     * liegt. Zwei Wege - einer fuer kleine, einer fuer grosse Dokumente - waeren ein Weg zu
     * viel, also gehen beide durch diesen.
     */
    @JavascriptInterface
    public String appendBytes(String base64) {
        try {
            activity.appendBytes(Base64.decode(base64, Base64.DEFAULT));
            return ok(new JSONObject());
        } catch (Throwable failure) {
            return error(failure);
        }
    }

    /**
     * Die herübergereichte Datei speichern. Der Benutzer waehlt den Ort im Systemdialog.
     *
     * <p>Der Typ folgt der Endung im Dateinamen - ein PDF hier, ein JPEG oder PNG dort.
     * Fest verdrahtet war er, solange es nur PDFs gab; ein PNG unter
     * {@code application/pdf} anzubieten waere eine Datei, die kein Betrachter oeffnet.
     */
    @JavascriptInterface
    public void saveFile(long callId, String filename) {
        activity.saveFile(callId, filename);
    }

    /** Dasselbe, aber zum Teilen (Drucken, Mail, Cloud) statt zum Ablegen. */
    @JavascriptInterface
    public void sharePdf(long callId, String filename) {
        activity.sharePdf(callId, filename);
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

    /**
     * Ein Fehlschlag als Antwort statt als geworfene Ausnahme.
     *
     * <p><b>Gefangen wird Throwable und nicht Exception</b>, und das ist hier keine
     * Nachlaessigkeit, sondern der Punkt. Ein Exportraster sind bei 300 dpi dreistellige
     * Megabyte; reicht der Speicher nicht, wirft {@code ByteBuffer.allocateDirect} einen
     * {@link OutOfMemoryError} - und der ist ein {@code Error}, kein {@code Exception}.
     * Mit dem engeren Fang stieg er aus der @JavascriptInterface-Methode heraus, die
     * WebView verschluckte ihn und schrieb ihren eigenen Satz in die Seite:
     *
     * <pre>Error invoking core: Java exception was raised during method invocation</pre>
     *
     * <p>Der Bediener sah damit, DASS etwas schiefging, und nie WAS. Genau die Sorte
     * Meldung, die einen Fehler unauffindbar macht - am 08.09.2026 auf einem echten
     * Telefon passiert.
     *
     * <p>Weiterlaufen darf die App danach: ein fehlgeschlagenes allocateDirect hat
     * nichts halb geschrieben, und die Arena in {@link NativeImages} ist unveraendert.
     */
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
