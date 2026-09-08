package com.bischofsnowboards.aruco;

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
        ByteBuffer buffer =
                ByteBuffer.allocateDirect((int) bytes).order(ByteOrder.nativeOrder());
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

    /** Alles wegwerfen - beim naechsten Foto. Das Foto selbst eingeschlossen. */
    synchronized void clear() {
        images.clear();
        transient_.clear();
    }
}
