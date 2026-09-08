package com.bischofsnowboards.aruco;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.system.Os;
import android.system.OsConstants;
import android.util.Log;
import android.view.ViewGroup;
import android.webkit.ConsoleMessage;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.core.content.FileProvider;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.webkit.WebViewAssetLoader;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Die einzige Activity: eine WebView und die Wege nach draussen.
 *
 * <p><b>Die Oberflaeche bleibt unveraendert.</b> app/static/ wird Byte fuer Byte
 * ausgeliefert - kein eingefuegtes {@code <script>}, keine Android-Fassung von
 * index.html. Moeglich macht das {@code addDocumentStartJavaScript}: die Bruecke laeuft,
 * bevor das erste Modul der Seite laeuft, und ersetzt dort {@code fetch} fuer die
 * /api/-Pfade. Zwei Fassungen derselben Oberflaeche waeren die teuerste Art, dieses
 * Vorhaben zu verlieren.
 *
 * <p><b>Warum ein https-Ursprung und kein file://.</b> app/static/ ist ein Baum aus
 * ES-Modulen, und ein Modul-Import ueber file:// scheitert an der Ursprungspruefung: der
 * Ursprung einer file-URL ist „opaque", und dagegen ist jeder Import ein Verstoss gegen
 * die Same-Origin-Regel. Der {@link WebViewAssetLoader} legt dieselben Dateien unter
 * https://appassets.androidplatform.net/ ab - eine Adresse, die absichtlich nicht
 * aufloest und deshalb nie ins Netz geht.
 */
public final class MainActivity extends Activity {

    private static final String TAG = "ArUco";
    private static final String ORIGIN = "https://appassets.androidplatform.net";
    private static final int REQUEST_PICK_PHOTO = 1;
    private static final int REQUEST_TAKE_PHOTO = 2;
    private static final int REQUEST_SAVE_PDF = 3;
    private static final int REQUEST_FILE_CHOOSER = 4;

    private WebView webView;
    private WebViewAssetLoader assetLoader;
    private ExecutorService worker;

    /** Was die WebView zuletzt gewaehlt hat - ueber den eigenen Dialog oder ueber {@code <input type=file>}. */
    private Uri pickedPhotoUri;

    /** Das geladene Foto. Genau eines: die App fuehrt eine Sitzung, nicht viele. */
    private Photo photo;
    private String photoName = "foto.jpg";
    private byte[] photoJpeg;

    /**
     * Die Bilder der Rechenkette und der Kern, wie die WebView ihn sieht.
     *
     * <p>Sie liegen HIER und nicht in der WebView: ein entzerrtes Raster sind bei 300 dpi
     * zweistellige Megabyte, und die JavaScript-Grenze traegt nur Text. Die Seite bekommt
     * eine Zahl je Bild (NativeImages).
     */
    private final NativeImages images = new NativeImages();
    private final CoreBridge core = new CoreBridge(images);

    /** Der Griff auf das Foto in BGR - die Eingabe jedes Rechenschritts. */
    private int photoHandle = -1;

    /**
     * Das PDF, das die Seite gerade herueberreicht.
     *
     * <p>In Scheiben, weil ein gekacheltes Schablonen-PDF zweistellige Megabyte hat und eine
     * einzelne Base64-Zeichenkette dieser Groesse zweimal im Speicher stuende - einmal als
     * JavaScript-String, einmal als Java-String.
     */
    private ByteArrayOutputStream incomingPdf = new ByteArrayOutputStream();

    /**
     * Was Aussparung und Systemleisten dem Fenster wegnehmen - oben, rechts, unten, links,
     * in dichteunabhaengigen Punkten (dip).
     *
     * <p>Gemerkt, weil die beiden Ereignisse nicht in fester Reihenfolge kommen: die
     * Fensterraender misst das System beim ersten Layout, die Seite laedt asynchron. Wer
     * zuletzt kommt, findet den anderen Wert hier vor.
     */
    private float[] safeAreaDip = { 0f, 0f, 0f, 0f };

    /** Der Aufruf, der gerade auf einen Systemdialog wartet. */
    private long pendingCallId = -1L;
    private byte[] pendingPdf;
    private ValueCallback<Uri[]> pendingFileChooser;
    private File pendingCapture;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        worker = Executors.newSingleThreadExecutor();

        // Erst laden, dann irgendetwas anfassen: jeder Aufruf in NativeCore setzt die
        // Bibliothek voraus, und ein UnsatisfiedLinkError mitten in einem Bruecken-Aufruf
        // waere eine Fehlermeldung ohne Zusammenhang.
        try {
            NativeCore.load();
        } catch (UnsatisfiedLinkError failure) {
            Log.e(TAG, "libaruco_core.so laedt nicht", failure);
            // Weiterlaufen. Die Oberflaeche zeigt den Fehler dann dort an, wo er
            // hingehoert - eine App, die beim Start wortlos verschwindet, sagt dem
            // Bediener gar nichts.
        }

        assetLoader = new WebViewAssetLoader.Builder()
                .setDomain("appassets.androidplatform.net")
                .addPathHandler("/api/", new ApiHandler())
                .addPathHandler("/", new WwwHandler())
                .build();

        webView = new WebView(this);
        setContentView(webView, new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);       // die Oberflaeche merkt sich Sprache und Thema
        settings.setAllowFileAccess(false);        // wir liefern ueber den AssetLoader aus
        settings.setAllowContentAccess(false);
        settings.setSupportZoom(false);
        settings.setMediaPlaybackRequiresUserGesture(true);

        webView.setWebViewClient(new LocalClient());
        webView.setWebChromeClient(new LocalChromeClient());
        webView.addJavascriptInterface(new WebBridge(this), "AndroidCore");
        WebView.setWebContentsDebuggingEnabled(true);

        installBridgeShim();
        watchWindowInsets();
        webView.loadUrl(ORIGIN + "/native/index.html");
    }

    /**
     * Die Fensterraender messen und der Seite geben.
     *
     * <p><b>Warum ueberhaupt.</b> Android 15 erzwingt fuer jede App mit
     * {@code targetSdk = 35}, dass sie unter den Systemleisten zeichnet; die Abmeldung
     * ({@code setDecorFitsSystemWindows(true)}) ist abgekuendigt. Wer seinen Inhalt dann
     * nicht selbst einrueckt, legt die Kopfzeile unter die Uhr und den Fuss hinter die
     * Navigationsleiste - genau so ist es von einem Xiaomi mit Android 15 gemeldet worden.
     *
     * <p><b>Warum nicht {@code env(safe-area-inset-*)} allein.</b> Die WebView fuellt
     * daraus nur die Display-Aussparung (AwDisplayCutoutController). Die Systemleisten
     * stehen dort nicht drin, und der untere Wert - also genau der gemeldete Fehler -
     * bliebe 0. Deshalb {@code systemBars() | displayCutout()}: die Vereinigung deckt
     * Status- und Navigationsleiste UND die Aussparung ab.
     *
     * <p><b>Aeltere Geraete aendern sich nicht.</b> Auf Android 14 und darunter fuegt sich
     * das Fenster weiterhin in die Systemleisten ein; die Raender kommen hier dann als 0
     * an, das CSS addiert 0, und die App sieht aus wie bisher. Das ist Absicht: hier wird
     * ein erzwungenes Verhalten beantwortet, nicht auf jedem Geraet ein neues eingefuehrt.
     *
     * <p>Die Raender kommen in physischen Pixeln. Ein CSS-Pixel in dieser WebView ist ein
     * dip, also wird durch die Dichte geteilt - ungeteilt waeren die Abstaende auf einem
     * heutigen Telefon rund dreimal zu gross.
     */
    private void watchWindowInsets() {
        ViewCompat.setOnApplyWindowInsetsListener(webView, (view, windowInsets) -> {
            Insets edges = windowInsets.getInsets(
                    WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout());
            float density = getResources().getDisplayMetrics().density;
            safeAreaDip = new float[] {
                    edges.top / density, edges.right / density,
                    edges.bottom / density, edges.left / density };
            pushSafeArea();
            // Unveraendert weiterreichen und nicht verbrauchen: die WebView ist zwar heute
            // das einzige Kind, aber ein verbrauchter Rand ist ein Fehler, den erst das
            // naechste Kind zeigt.
            return windowInsets;
        });
    }

    /**
     * Die gemerkten Raender in die laufende Seite schreiben.
     *
     * <p>{@code Locale.US} ist nicht Zierat: mit deutscher Voreinstellung schriebe
     * {@code String.format} "24,00", und das waere in JavaScript ein zweites Argument
     * statt einer Nachkommastelle. Der Aufruf ist gegen eine Seite ohne die Bruecke
     * abgesichert ({@code &&}) - beim allerersten Aufruf steht womoeglich noch
     * {@code about:blank} im Fenster.
     */
    private void pushSafeArea() {
        if (webView == null) return;
        webView.evaluateJavascript(String.format(Locale.US,
                "window.__arucoInsets && window.__arucoInsets(%.2f,%.2f,%.2f,%.2f);",
                safeAreaDip[0], safeAreaDip[1], safeAreaDip[2], safeAreaDip[3]), null);
    }

    /**
     * Die Bruecke laeuft vor jeder Seite - auch vor der unveraenderten Oberflaeche.
     *
     * <p>{@code addDocumentStartJavaScript} ist der Grund, warum app/static/index.html
     * nicht angefasst werden muss. Kann die WebView des Geraets das nicht (sehr alte
     * Fassung), wird das gesagt statt still ein halb verdrahtetes Fenster zu zeigen: die
     * Oberflaeche liefe dann gegen einen Server, den es nicht gibt, und jede Anfrage
     * scheiterte mit einem Netzfehler, den niemand einordnen kann.
     */
    private void installBridgeShim() {
        if (!WebViewFeature.isFeatureSupported(WebViewFeature.DOCUMENT_START_SCRIPT)) {
            Log.e(TAG, "Diese WebView kann kein DOCUMENT_START_SCRIPT - die Bruecke fehlt.");
            return;
        }
        String shim = readAsset("www/native/bridge-shim.js");
        if (shim == null) {
            Log.e(TAG, "bridge-shim.js fehlt in den Assets.");
            return;
        }
        Set<String> origins = new HashSet<>();
        origins.add(ORIGIN);
        WebViewCompat.addDocumentStartJavaScript(webView, shim, origins);
    }

    // --- Auslieferung ------------------------------------------------------------

    /** Alles unter www/ - die Oberflaeche, web/pdf/, shared/ und die eigene Seite. */
    private final class WwwHandler implements WebViewAssetLoader.PathHandler {
        @Override
        public WebResourceResponse handle(String path) {
            String file = path.isEmpty() || path.endsWith("/") ? path + "index.html" : path;
            try {
                InputStream stream = getAssets().open("www/" + file);
                return new WebResourceResponse(mimeType(file), null, stream);
            } catch (IOException missing) {
                return null;  // der Loader macht daraus einen 404
            }
        }
    }

    /**
     * Die lesenden /api/-Pfade. Heute genau einer: die Rasterbilder der Rechenkette.
     *
     * <p>Nur GET kommt hier an: {@code shouldInterceptRequest} bekommt bei einem POST
     * zwar die URL, aber NICHT den Rumpf - das ist eine Luecke im WebView-API und keine
     * Nachlaessigkeit hier. Alles Schreibende geht deshalb ueber die
     * JavaScript-Bruecke (WebBridge).
     *
     * <p><b>Warum die Bilder ueberhaupt hier herauskommen.</b> Ein Vorschaubild ist ein
     * {@code <img src>}, und das Schablonen-PDF bettet dasselbe Bild als JPEG ein. Ueber
     * die JavaScript-Bruecke waeren beide Base64 - ein Drittel mehr, als Text, bei jedem
     * Reglerzug. Ueber diesen Weg sind es Binaerbytes.
     */
    private final class ApiHandler implements WebViewAssetLoader.PathHandler {
        @Override
        public WebResourceResponse handle(String path) {
            // raster/<griff>/<guete>.jpg - ein Rasterbild der Rechenkette.
            //
            // Ein GET und keine Bruecken-Methode, und das ist der Punkt: so kommen die
            // JPEG-Bytes als Binaerstrom in die Seite, nicht als Base64-Zeichenkette. Bei
            // einem Vorschaubild je Reglerzug ist das der Unterschied zwischen fluessig
            // und unbenutzbar. Die Guete steht im Pfad, weil PathHandler nur den Pfad
            // bekommt und keine Abfrageparameter - eine Luecke im WebView-API.
            if (path.startsWith("raster/")) {
                String[] parts = path.substring("raster/".length()).split("/");
                if (parts.length != 2 || !parts[1].endsWith(".jpg")) {
                    return null;
                }
                try {
                    int handle = Integer.parseInt(parts[0]);
                    int quality = Integer.parseInt(
                            parts[1].substring(0, parts[1].length() - ".jpg".length()));
                    // Das Foto selbst ist beim Laden schon kodiert worden. Ein
                    // 12-MP-Bild noch einmal zu kodieren dauert rund eine Sekunde,
                    // und das Erkennungs-Overlay fragt genau danach - auf einem
                    // Faden, der solange keine andere Anfrage bedient. Die Guete im
                    // Pfad wird dafuer ignoriert; es ist ein Bild fuer das Auge.
                    byte[] jpeg = handle == photoHandle && photoJpeg != null
                            ? photoJpeg
                            : Rasters.toJpeg(images.require(handle), quality);
                    return new WebResourceResponse("image/jpeg", null,
                            new java.io.ByteArrayInputStream(jpeg));
                } catch (RuntimeException failure) {
                    Log.w(TAG, "Rasterbild " + path + " nicht lieferbar", failure);
                    return null;
                }
            }
            return null;
        }
    }

    private static String mimeType(String path) {
        // Die Zuordnung ist kurz, weil der Baum bekannt ist. Zwei Eintraege sind
        // NICHT verhandelbar: .js muss text/javascript sein, sonst weist die WebView
        // das Modul ab, und .json muss application/json sein, sonst scheitert
        // `import ... with { type: "json" }` - und daran haengt shared/constants.json.
        if (path.endsWith(".html")) return "text/html";
        if (path.endsWith(".js") || path.endsWith(".mjs")) return "text/javascript";
        if (path.endsWith(".json")) return "application/json";
        if (path.endsWith(".css")) return "text/css";
        if (path.endsWith(".svg")) return "image/svg+xml";
        if (path.endsWith(".png")) return "image/png";
        if (path.endsWith(".jpg") || path.endsWith(".jpeg")) return "image/jpeg";
        if (path.endsWith(".ico")) return "image/x-icon";
        if (path.endsWith(".woff2")) return "font/woff2";
        if (path.endsWith(".pdf")) return "application/pdf";
        return "application/octet-stream";
    }

    private final class LocalClient extends WebViewClient {
        @Override
        public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            return assetLoader.shouldInterceptRequest(request.getUrl());
        }

        /**
         * Die Fensterraender gelten pro Dokument, nicht pro App.
         *
         * <p>Das System misst sie einmal beim ersten Layout - danach ruft es den Zuhoerer
         * nur noch, wenn sich wirklich etwas aendert (Drehung, ein- und ausgeblendete
         * Leiste). Jede Seite, die DANACH geladen wird - die Werkbank, die Oberflaeche,
         * jeder Weg zurueck - faengt aber wieder ohne die Variablen an. Ohne diese Zeile
         * bekaeme genau eine Seite der App ihre Raender, und das waere die, die beim
         * Start zufaellig gerade dran war.
         */
        @Override
        public void onPageFinished(WebView view, String url) {
            pushSafeArea();
        }

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            Uri url = request.getUrl();
            if (ORIGIN.equals(url.getScheme() + "://" + url.getAuthority())) {
                return false;  // unsere eigenen Seiten laedt die WebView selbst
            }
            // Alles andere gehoert nach draussen. Die App hat keine
            // Netzberechtigung; ein externer Link, den sie selbst zu laden versuchte,
            // ergaebe eine leere Seite statt eines Browsers.
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, url));
            } catch (Exception failure) {
                Log.w(TAG, "Kein Programm fuer " + url, failure);
            }
            return true;
        }
    }

    private final class LocalChromeClient extends WebChromeClient {
        @Override
        public boolean onConsoleMessage(ConsoleMessage message) {
            // In den Log, damit `adb logcat -s ArUco` beim Fehlersuchen ohne
            // angeschlossenen Debugger etwas hergibt.
            Log.d(TAG, message.messageLevel() + " " + message.message() + " ("
                    + message.sourceId() + ":" + message.lineNumber() + ")");
            return true;
        }

        /**
         * Das {@code <input type="file">} der unveraenderten Oberflaeche.
         *
         * <p>Ohne diese Methode tut ein Dateifeld in einer WebView schlicht nichts - kein
         * Dialog, keine Meldung. Die gewaehlte URI wird hier zusaetzlich gemerkt: die
         * Bruecke laedt das Bild daraus selbst, statt es als Base64 durch JavaScript
         * zurueckzubekommen.
         */
        @Override
        public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                FileChooserParams params) {
            if (pendingFileChooser != null) {
                pendingFileChooser.onReceiveValue(null);
            }
            pendingFileChooser = callback;
            try {
                startActivityForResult(imagePickerIntent(), REQUEST_FILE_CHOOSER);
                return true;
            } catch (Exception failure) {
                pendingFileChooser = null;
                Log.w(TAG, "Kein Dateidialog verfuegbar", failure);
                return false;
            }
        }
    }

    // --- Fotos -------------------------------------------------------------------

    private static Intent imagePickerIntent() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("image/*");
        return intent;
    }

    void pickPhoto(long callId) {
        pendingCallId = callId;
        try {
            startActivityForResult(imagePickerIntent(), REQUEST_PICK_PHOTO);
        } catch (Exception failure) {
            resolveError(callId, "Kein Dateidialog verfuegbar: " + failure.getMessage());
        }
    }

    void takePhoto(long callId) {
        pendingCallId = callId;
        try {
            File directory = new File(getCacheDir(), "captures");
            if (!directory.exists() && !directory.mkdirs()) {
                resolveError(callId, "Cache-Verzeichnis nicht anlegbar");
                return;
            }
            pendingCapture = new File(directory, "capture.jpg");
            Uri target = FileProvider.getUriForFile(this, getPackageName() + ".files",
                    pendingCapture);
            Intent intent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            intent.putExtra(MediaStore.EXTRA_OUTPUT, target);
            intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
            startActivityForResult(intent, REQUEST_TAKE_PHOTO);
        } catch (Exception failure) {
            resolveError(callId, "Keine Kamera-App gefunden: " + failure.getMessage());
        }
    }

    /** Das zuletzt gewaehlte Bild wirklich laden - egal ueber welchen Weg es gewaehlt wurde. */
    void loadPickedPhoto(long callId) {
        Uri source = pickedPhotoUri;
        if (source == null) {
            resolveError(callId, "Es wurde noch kein Bild gewaehlt.");
            return;
        }
        worker.execute(() -> {
            try {
                loadPhotoFrom(source);
                resolve(callId, photoPayload());
            } catch (Exception failure) {
                resolveError(callId, describe(failure));
            }
        });
    }

    CoreBridge core() {
        return core;
    }

    /**
     * Der Griff auf das Foto in BGR.
     *
     * <p>Die Umwandlung geschieht beim ersten Zugriff und nicht beim Laden: wer nur
     * das Markerblatt druckt, zahlt die 36 MB nicht.
     */
    int photoHandle() {
        Photo current = photo;
        if (current == null) {
            throw new IllegalStateException("Es ist kein Foto geladen.");
        }
        if (photoHandle < 0) {
            photoHandle = core.registerPhoto(current.bgr(), current.width, current.height);
        }
        return photoHandle;
    }

    /**
     * Alle Bilder vergessen - beim naechsten Foto.
     *
     * <p>Ohne das truege die App das vorige Foto samt seinen Zwischenrastern weiter, und wer
     * drei Fotos hintereinander misst, haette drei davon im Speicher. Der Griff wird
     * ungueltig gesetzt und nicht neu vergeben: eine Seite, die den alten noch benutzt,
     * bekommt eine benannte Ausnahme und kein fremdes Bild.
     */
    private void forgetRasters() {
        images.clear();
        photoHandle = -1;
    }

    /**
     * Eine Scheibe des PDFs entgegennehmen, das die Seite gerade baut.
     *
     * <p>Die Seite ruft das mehrfach und danach einmal {@link #savePdf}. Warum nicht in
     * einem Stueck: ein gekacheltes Schablonen-PDF mit eingebettetem 300-dpi-Raster sind
     * zweistellige Megabyte, als Base64 ein Drittel mehr - und eine einzelne Zeichenkette
     * dieser Groesse stuende zweimal im Speicher, einmal auf jeder Seite der Grenze.
     */
    void appendPdf(byte[] chunk) {
        incomingPdf.write(chunk, 0, chunk.length);
    }

    /** Was bisher angekommen ist, und der Beginn eines neuen Dokuments. */
    private byte[] takeIncomingPdf() {
        byte[] data = incomingPdf.toByteArray();
        incomingPdf = new ByteArrayOutputStream();
        return data;
    }

    private void loadPhotoFrom(Uri source) throws IOException {
        photo = Photo.load(getContentResolver(), source);
        photoName = displayName(source);
        forgetRasters();
        // Die Vorschau entsteht sofort und nicht auf Anfrage: /api/raster/ wird aus
        // shouldInterceptRequest bedient, und das laeuft auf einem Faden, auf dem eine
        // JPEG-Kodierung eines 12-MP-Bildes nichts zu suchen hat. Das Erkennungs-Overlay
        // fragt genau dieses Bild ab und bekommt dann diese Kopie.
        photoJpeg = photo.toJpeg(85);
    }

    private String displayName(Uri source) {
        String last = source.getLastPathSegment();
        if (last == null) {
            return "foto.jpg";
        }
        int slash = last.lastIndexOf('/');
        return slash >= 0 ? last.substring(slash + 1) : last;
    }

    void detectMarkers(long callId, boolean enhanceContrast) {
        Photo current = photo;
        if (current == null) {
            resolveError(callId, "Es ist kein Foto geladen.");
            return;
        }
        worker.execute(() -> {
            try {
                long started = System.nanoTime();
                double[] found = NativeCore.detectMarkers(current.pixels, current.width,
                        current.height, current.stride(), NativeCore.CHANNELS_RGBA,
                        enhanceContrast);
                long elapsedMs = (System.nanoTime() - started) / 1_000_000L;

                JSONArray markers = new JSONArray();
                for (int index = 0; index + NativeCore.VALUES_PER_MARKER <= found.length;
                        index += NativeCore.VALUES_PER_MARKER) {
                    JSONObject marker = new JSONObject();
                    marker.put("id", (int) found[index]);
                    JSONArray corners = new JSONArray();
                    for (int corner = 0; corner < 4; corner++) {
                        JSONArray point = new JSONArray();
                        point.put(found[index + 1 + corner * 2]);
                        point.put(found[index + 2 + corner * 2]);
                        corners.put(point);
                    }
                    marker.put("corners_px", corners);
                    markers.put(marker);
                }

                JSONObject payload = new JSONObject();
                payload.put("markers", markers);
                payload.put("elapsed_ms", elapsedMs);
                payload.put("enhance_contrast", enhanceContrast);
                payload.put("width", current.width);
                payload.put("height", current.height);
                resolve(callId, payload);
            } catch (Exception failure) {
                resolveError(callId, describe(failure));
            }
        });
    }

    void runConformance(long callId, boolean dumpCorners) {
        worker.execute(() -> {
            try {
                resolve(callId, Conformance.run(getAssets(), dumpCorners));
            } catch (Exception failure) {
                resolveError(callId, describe(failure));
            }
        });
    }

    // --- PDF nach draussen -------------------------------------------------------

    void savePdf(long callId, String filename) {
        pendingCallId = callId;
        pendingPdf = takeIncomingPdf();
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("application/pdf");
        intent.putExtra(Intent.EXTRA_TITLE, filename);
        try {
            startActivityForResult(intent, REQUEST_SAVE_PDF);
        } catch (Exception failure) {
            pendingPdf = null;
            resolveError(callId, "Kein Speicherdialog verfuegbar: " + failure.getMessage());
        }
    }

    void sharePdf(long callId, String filename) {
        byte[] data = takeIncomingPdf();
        try {
            File directory = new File(getCacheDir(), "documents");
            if (!directory.exists() && !directory.mkdirs()) {
                resolveError(callId, "Cache-Verzeichnis nicht anlegbar");
                return;
            }
            File target = new File(directory, filename);
            try (FileOutputStream out = new FileOutputStream(target)) {
                out.write(data);
            }
            Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".files", target);
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType("application/pdf");
            send.putExtra(Intent.EXTRA_STREAM, uri);
            send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(Intent.createChooser(send, filename));
            resolve(callId, new JSONObject().put("shared", true).put("filename", filename));
        } catch (Exception failure) {
            resolveError(callId, describe(failure));
        }
    }

    void navigateTo(String path) {
        runOnUiThread(() -> webView.loadUrl(ORIGIN + path));
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        long callId = pendingCallId;
        pendingCallId = -1L;

        switch (requestCode) {
            case REQUEST_FILE_CHOOSER: {
                Uri chosen = resultCode == RESULT_OK && data != null ? data.getData() : null;
                if (chosen != null) {
                    pickedPhotoUri = chosen;
                }
                ValueCallback<Uri[]> callback = pendingFileChooser;
                pendingFileChooser = null;
                if (callback != null) {
                    callback.onReceiveValue(chosen == null ? null : new Uri[] {chosen});
                }
                return;
            }
            case REQUEST_PICK_PHOTO: {
                if (resultCode != RESULT_OK || data == null || data.getData() == null) {
                    resolveError(callId, "abgebrochen");
                    return;
                }
                pickedPhotoUri = data.getData();
                loadPickedPhoto(callId);
                return;
            }
            case REQUEST_TAKE_PHOTO: {
                File captured = pendingCapture;
                pendingCapture = null;
                if (resultCode != RESULT_OK || captured == null || !captured.exists()) {
                    resolveError(callId, "abgebrochen");
                    return;
                }
                pickedPhotoUri = Uri.fromFile(captured);
                worker.execute(() -> {
                    try {
                        photo = Photo.fromBytes(readAll(captured));
                        photoName = "kamera.jpg";
                        forgetRasters();
                        photoJpeg = photo.toJpeg(85);
                        resolve(callId, photoPayload());
                    } catch (Exception failure) {
                        resolveError(callId, describe(failure));
                    }
                });
                return;
            }
            case REQUEST_SAVE_PDF: {
                byte[] pdf = pendingPdf;
                pendingPdf = null;
                if (resultCode != RESULT_OK || data == null || data.getData() == null
                        || pdf == null) {
                    resolveError(callId, "abgebrochen");
                    return;
                }
                try (OutputStream out = getContentResolver().openOutputStream(data.getData())) {
                    if (out == null) {
                        resolveError(callId, "Ziel nicht beschreibbar");
                        return;
                    }
                    out.write(pdf);
                    resolve(callId, new JSONObject().put("saved", true)
                            .put("bytes", pdf.length));
                } catch (Exception failure) {
                    resolveError(callId, describe(failure));
                }
                return;
            }
            default:
                // Nichts. Ein unbekannter Rueckgabecode gehoert uns nicht.
        }
    }

    // --- Antworten an die WebView ------------------------------------------------

    private JSONObject photoPayload() throws org.json.JSONException {
        JSONObject payload = new JSONObject();
        payload.put("filename", photoName);
        payload.put("width", photo.width);
        payload.put("height", photo.height);
        payload.put("exif_rotation_deg", photo.exifRotationDeg);
        payload.put("focal35_mm", photo.focal35Mm > 0.0 ? photo.focal35Mm : JSONObject.NULL);
        payload.put("camera_model",
                photo.cameraModel == null ? JSONObject.NULL : photo.cameraModel);
        payload.put("marker_mm_nominal", NativeCore.markerMmNominal());
        return payload;
    }

    void resolve(long callId, JSONObject payload) {
        try {
            payload.put("ok", true);
            deliver(callId, payload.toString());
        } catch (org.json.JSONException failure) {
            resolveError(callId, describe(failure));
        }
    }

    void resolveError(long callId, String message) {
        deliver(callId, "{\"ok\":false,\"error\":" + JSONObject.quote(message) + "}");
    }

    private void deliver(long callId, String json) {
        if (callId < 0) {
            return;
        }
        runOnUiThread(() -> webView.evaluateJavascript(
                "window.__arucoResolve && window.__arucoResolve(" + callId + "," + json + ")",
                null));
    }

    private static String describe(Throwable failure) {
        String message = failure.getMessage();
        return message == null || message.isEmpty()
                ? failure.getClass().getSimpleName() : message;
    }

    // --- Kleinkram ---------------------------------------------------------------

    String appVersionName() {
        try {
            PackageInfo info = getPackageManager().getPackageInfo(getPackageName(), 0);
            return info.versionName == null ? "?" : info.versionName;
        } catch (PackageManager.NameNotFoundException impossible) {
            return "?";
        }
    }

    String webViewVersion() {
        PackageInfo info = WebViewCompat.getCurrentWebViewPackage(this);
        return info == null ? "?" : info.versionName;
    }

    long systemPageSize() {
        return Os.sysconf(OsConstants._SC_PAGESIZE);
    }

    private String readAsset(String path) {
        try (InputStream stream = getAssets().open(path)) {
            byte[] data = new byte[stream.available()];
            int read = 0;
            while (read < data.length) {
                int chunk = stream.read(data, read, data.length - read);
                if (chunk < 0) {
                    break;
                }
                read += chunk;
            }
            return new String(data, 0, read, "UTF-8");
        } catch (IOException missing) {
            return null;
        }
    }

    private static byte[] readAll(File file) throws IOException {
        byte[] data = new byte[(int) file.length()];
        try (java.io.FileInputStream stream = new java.io.FileInputStream(file)) {
            int read = 0;
            while (read < data.length) {
                int chunk = stream.read(data, read, data.length - read);
                if (chunk < 0) {
                    break;
                }
                read += chunk;
            }
        }
        return data;
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
            return;
        }
        super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        worker.shutdownNow();
        webView.destroy();
        super.onDestroy();
    }
}
