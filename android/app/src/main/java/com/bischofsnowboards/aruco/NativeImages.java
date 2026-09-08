package com.bischofsnowboards.aruco;

import android.app.ActivityManager;
import android.content.Context;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Die Bilder, die zwischen zwei Rechenschritten liegen - und wer sie freigibt.
 *
 * <p><b>Das Problem.</b> Die Rechenkette in {@code web/vision/pipeline.js} laeuft in der
 * WebView, die Pixel liegen aber hier. Ein entzerrtes Raster sind bei 300 dpi zweistellige
 * Megabyte; als Base64 durch die JavaScript-Grenze waeren es ein Drittel mehr, als Text, je
 * Reglerzug. Also bleibt das Bild hier, und JavaScript bekommt eine ZAHL.
 *
 * <p><b>Das zweite Problem, und das teurere.</b> Wer gibt es wieder frei? Im Browser tut das
 * {@code web/vision/core.js}: {@code takeRaster} kopiert das Ergebnis aus dem WASM-Haufen und
 * loescht es sofort. Hier kann es niemand kopieren - genau deshalb liegt es ja hier. Und
 * {@code pipeline.js} kennt keine Freigabe: {@code runAdjust} legt bei JEDEM Reglerzug ein
 * neues Raster an und laesst das vorige fallen. Ohne Gegenmassnahme waere das ein Leck von
 * mehreren Megabyte je Fingerbewegung, und Android beendet den Prozess, ohne dass der
 * Bediener je einen Fehler saehe.
 *
 * <p><b>Die Antwort ist eine ARENA und kein Sammler.</b> Es leben hoechstens
 * {@link #CAPACITY} Raster; kommt eines dazu, faellt das aelteste weg. Das ist keine
 * Schaetzung: {@code pipeline.js} haelt in jedem seiner drei Wege hoechstens ZWEI Raster
 * gleichzeitig - Vorschau und aufbereitete Vorschau, oder Exportraster und dessen
 * aufbereitete Fassung. Drei ist also eines mehr als der schlimmste Fall, und wer die Kette
 * erweitert, merkt es sofort: ein verdraengtes Raster gibt eine benannte Ausnahme und kein
 * falsches Bild.
 *
 * <p>Das Foto selbst wird <b>festgehalten</b> ({@link #pin}) und faellt nie weg - es ist die
 * Eingabe jedes Schritts, nicht ein Zwischenstand.
 */
final class NativeImages {

    /**
     * Wie viele Zwischenraster gleichzeitig leben duerfen.
     *
     * <p>Zwei genuegen der Kette, drei geben eine Reserve. Vier waeren bei 300 dpi schon
     * dreistellige Megabyte, ohne dass irgendein Weg sie braeuchte.
     */
    static final int CAPACITY = 3;

    /** Ein Bild im nativen Speicher: BGR, zeilenweise dicht. */
    static final class Image {
        final ByteBuffer pixels;
        final int width;
        final int height;
        final int channels;

        Image(ByteBuffer pixels, int width, int height, int channels) {
            this.pixels = pixels;
            this.width = width;
            this.height = height;
            this.channels = channels;
        }

        int stride() {
            return width * channels;
        }

        int bytes() {
            return stride() * height;
        }
    }

    private final Map<Integer, Image> images = new LinkedHashMap<>();
    private final Deque<Integer> transient_ = new ArrayDeque<>();
    private int nextHandle = 1;

    /** Ein Bild anlegen, das nie verdraengt wird - das Foto. */
    synchronized int pin(ByteBuffer pixels, int width, int height, int channels) {
        int handle = nextHandle++;
        images.put(handle, new Image(pixels, width, height, channels));
        return handle;
    }

    /**
     * Einen Ausgabepuffer der gewuenschten Groesse anlegen und eintragen.
     *
     * <p>Der Puffer entsteht HIER und nicht beim Aufrufer, weil die Arena sonst nicht
     * wuesste, was sie verdraengen darf. {@code ByteBuffer.allocateDirect} legt ihn
     * ausserhalb des Java-Haufens ab - der Kern schreibt dann ohne Kopie hinein.
     */
    synchronized int allocate(int width, int height, int channels) {
        long bytes = (long) width * height * channels;
        if (width <= 0 || height <= 0 || channels <= 0 || bytes > Integer.MAX_VALUE) {
            throw new IllegalArgumentException(
                    "Rastergroesse unbrauchbar: " + width + "x" + height + "x" + channels);
        }
        while (transient_.size() >= CAPACITY) {
            images.remove(transient_.removeFirst());
        }
        ByteBuffer buffer;
        try {
            buffer = ByteBuffer.allocateDirect((int) bytes).order(ByteOrder.nativeOrder());
        } catch (OutOfMemoryError exhausted) {
            // Mit Zahlen, nicht mit "Speicher voll": wer das liest, will wissen, ob er
            // 20 MB oder 500 MB zu viel verlangt hat. Weitergegeben als Exception, damit
            // der Aufrufer sie behandeln kann wie jeden anderen Fehlschlag auch - der
            // Prozess ist gesund, es fehlte nur dieser eine Puffer.
            throw new IllegalStateException(
                    "Raster " + width + "x" + height + " braucht " + (bytes >> 20)
                            + " MB und der Speicher gibt sie nicht her.",
                    exhausted);
        }
        int handle = nextHandle++;
        images.put(handle, new Image(buffer, width, height, channels));
        transient_.addLast(handle);
        return handle;
    }

    /**
     * Das Bild zu einem Griff.
     *
     * <p>Wirft, statt null zu liefern: ein verdraengter Griff ist ein Programmfehler in der
     * Kette, und die Meldung soll das sagen. Ein stilles null wuerde weiter unten zu einem
     * leeren Bild, und das saehe nach einem schlechten Foto aus.
     */
    synchronized Image require(int handle) {
        Image image = images.get(handle);
        if (image == null) {
            throw new IllegalArgumentException(
                    "Bild " + handle + " gibt es nicht mehr - die Arena haelt nur " + CAPACITY
                            + " Zwischenraster (NativeImages).");
        }
        return image;
    }

    /**
     * Wieviele Ausgabepixel dieses Geraet noch vertraegt.
     *
     * <p><b>Warum das nicht in shared/constants.json stehen kann.</b> Dort stehen
     * Aussagen ueber das PRODUKT - Millimeter, Papier, Schwellen -, und die gelten
     * ueberall gleich. Wieviel Speicher da ist, ist eine Aussage ueber die MASCHINE.
     * {@code MAX_OUTPUT_MPX} = 300 bedeutet auf dem Schreibtisch 900 MB Raster und ist
     * dort in Ordnung; auf einem Telefon ist es der sichere Tod, und zwar genau in dem
     * Augenblick, in dem der Bediener auf "PDF erzeugen" drueckt.
     *
     * <p><b>Sechs Byte je Ausgabepixel</b>, nicht drei: {@code runExport} in
     * web/vision/pipeline.js haelt das entzerrte Raster UND seine aufbereitete Fassung
     * gleichzeitig (die Arena verdraengt bei CAPACITY=3 noch nichts). Dazu kommen das
     * festgehaltene Foto, die JPEG-Bytes und das PDF - dafuer ist der Faktor 0,45.
     *
     * <p>Die Obergrenze ist kein Geiz, sondern eine zweite Sicherung: {@code availMem}
     * meldet auf einem grossen Geraet Gigabyte, aber ein einzelner Direktpuffer dieser
     * Groesse bringt den Prozess trotzdem in die Naehe des Low-Memory-Killers.
     */
    static double budgetMegapixels(Context context) {
        ActivityManager manager =
                (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
        if (manager == null) return FALLBACK_BUDGET_MPX;
        ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo();
        manager.getMemoryInfo(memory);

        // Zwei Grenzen, und die kleinere gilt.
        double fromFree = memory.availMem * FREE_MEMORY_SHARE / BYTES_PER_OUTPUT_PIXEL;
        double fromOne = MAX_SINGLE_RASTER_BYTES / BYTES_PER_RASTER_PIXEL;
        double megapixels = Math.min(fromFree, fromOne) / 1e6;
        return Math.max(MIN_BUDGET_MPX, Math.floor(megapixels));
    }

    /** Ein Ausgabepixel im Raster: BGR. */
    private static final double BYTES_PER_RASTER_PIXEL = 3.0;

    /** Entzerrtes Raster plus aufbereitete Fassung, je drei Kanaele. */
    private static final double BYTES_PER_OUTPUT_PIXEL = 2.0 * BYTES_PER_RASTER_PIXEL;

    /** Wieviel vom freien Speicher sich der Export nehmen darf. */
    private static final double FREE_MEMORY_SHARE = 0.45;

    /**
     * Wie gross EINE Belegung am Stueck hoechstens sein darf.
     *
     * <p><b>Diese Grenze ist der Grund, warum es sie gibt.</b> Bis zum 08.09.2026 stand
     * hier 768 MiB, gemeint als Summe fuer beide Raster - das erlaubte 134 Megapixel. Auf
     * einem Xiaomi mit Android 15 ging ein Export mit 130,44 Megapixeln deshalb durch die
     * Pruefung und scheiterte danach an genau einer Zeile: 373 MiB fuer EIN Raster gab der
     * Speicher nicht her, obwohl {@code availMem} reichlich meldete.
     *
     * <p>Ein Direktpuffer will einen zusammenhaengenden Block im nativen Haufen. Wieviel
     * insgesamt frei ist, sagt darueber wenig; deshalb wird hier die EINZELNE Belegung
     * begrenzt und nicht die Summe. 192 MiB sind rund 67 Megapixel - ein A0-Bogen bei
     * 300 dpi. Wer mehr braucht, bekommt es blattweise: die Kachelung rastert seit
     * derselben Fassung Blatt fuer Blatt (web/vision/pipeline.js), und dort ist ein
     * A4-Blatt bei 300 dpi nicht einmal ein Zehntel davon.
     */
    private static final double MAX_SINGLE_RASTER_BYTES = 192.0 * 1024 * 1024;

    /** Darunter waere die App unbrauchbar; dann lieber ehrlich scheitern. */
    private static final double MIN_BUDGET_MPX = 8.0;

    /** Wenn das System die Auskunft verweigert - vorsichtig, aber benutzbar. */
    private static final double FALLBACK_BUDGET_MPX = 24.0;

    /** Alles wegwerfen - beim naechsten Foto. Das Foto selbst eingeschlossen. */
    synchronized void clear() {
        images.clear();
        transient_.clear();
    }
}
