package com.bischofsnowboards.aruco;

import java.nio.ByteBuffer;

/**
 * Der Rechenkern, wie Java ihn sieht - die Java-Seite von core/bindings/jni.cpp.
 *
 * <p><b>Diese Klasse kennt Android nicht.</b> Kein Import aus {@code android.*}, keine Bitmap,
 * kein Context. Das ist Absicht und keine Sparsamkeit: genau dadurch laesst sie sich auf dem
 * Bau-Rechner uebersetzen und gegen die Windows-DLL desselben Quelltextes ausfuehren
 * (core/tools/JniCheck.java, {@code ./dev.ps1 check-jni}). Auf einem Rechner ohne Geraet und ohne
 * Emulator ist das der einzige Weg, den Marshalling-Code wirklich LAUFEN zu lassen statt ihn nur
 * zu uebersetzen. Was Android beisteuert - eine Bitmap zu dekodieren - steht in
 * {@link PhotoDecoder}.
 *
 * <p><b>Alles statisch.</b> Der Kern haelt keinen Zustand: derselbe Puffer ergibt dieselben Ecken.
 * Eine Instanz waere ein Versprechen auf Zustand, das niemand einloest.
 */
public final class NativeCore {

    /** Ein Byte je Pixel, Graustufen. */
    public static final int CHANNELS_GRAY = 1;

    /** Drei Bytes je Pixel in der Reihenfolge, die OpenCV und {@code app/vision/} benutzen. */
    public static final int CHANNELS_BGR = 3;

    /**
     * Vier Bytes je Pixel, RGBA - das, was {@code Bitmap.copyPixelsToBuffer} bei ARGB_8888
     * liefert. Die Umwandlung nach BGR macht die JNI-Schicht; eine Bitmap-Konfiguration in BGR
     * gibt es auf Android nicht.
     */
    public static final int CHANNELS_RGBA = 4;

    /** Werte je Marker in der Rueckgabe von {@link #detectMarkers}: ID + vier Ecken als x,y. */
    public static final int VALUES_PER_MARKER = 9;

    private NativeCore() {}

    /**
     * Die Bibliothek laden. Einmal je Prozess, vor dem ersten Aufruf.
     *
     * <p>Nicht in einem {@code static}-Block: dort geworfen wuerde daraus ein
     * {@code ExceptionInInitializerError} beim ersten Zugriff auf irgendein Feld dieser Klasse -
     * eine Meldung, die den Grund (die .so fehlt fuer diese ABI) nicht mehr nennt.
     */
    public static void load() {
        System.loadLibrary("aruco_core");
    }

    /** Die OpenCV-Fassung, gegen die gebunden wurde. */
    public static native String openCvVersion();

    /** Der Name des Woerterbuchs, erzeugt aus shared/constants.json. */
    public static native String dictionaryName();

    /** Die nominelle Markerkante in Millimetern, aus shared/constants.json. */
    public static native double markerMmNominal();

    /** Wie viele Marker das eingestellte Woerterbuch kennt. */
    public static native int dictionarySize();

    /**
     * Alle Marker im Bild finden, nach ID sortiert.
     *
     * @param pixels ein <b>direkter</b> ByteBuffer ({@link ByteBuffer#allocateDirect}). Ein
     *     Heap-Puffer wird abgewiesen: er muesste fuer den Aufruf kopiert oder der
     *     Speicherbereiniger angehalten werden, und ein 12-MP-Foto sind 48 MB.
     * @param stride Bytes je Zeile, nicht Pixel.
     * @param channels {@link #CHANNELS_GRAY}, {@link #CHANNELS_BGR} oder {@link #CHANNELS_RGBA}.
     * @param enhanceContrast CLAHE vor die Erkennung legen. Kein Schoenheitsschalter - er ist an
     *     der eingefrorenen Szene messbar besser (0,140 statt 0,160 px groesster Eckfehler).
     * @return je Marker neun Werte: ID, dann TL, TR, BR, BL als x, y. Leer, wenn nichts gefunden
     *     wurde - das ist kein Fehler, sondern ein schlechtes Foto.
     * @throws IllegalArgumentException wenn der Puffer nicht direkt oder zu klein ist
     * @throws RuntimeException wenn OpenCV an diesem Bild scheitert
     */
    public static native double[] detectMarkers(
            ByteBuffer pixels,
            int width,
            int height,
            int stride,
            int channels,
            boolean enhanceContrast);

    /**
     * Die Modulbits eines Markers, zeilenweise, ein Byte je Modul (0 = schwarz).
     *
     * <p>Damit zeichnet web/pdf/markersheet.js das Markerblatt auf dem Geraet. Jenes Modul nimmt
     * die Bits bewusst von aussen entgegen - unter Node liefert sie opencv.js, hier der native
     * Kern. Ein zweites OpenCV in der WebView waeren 13 MB WASM fuer vier feste Zeichnungen.
     *
     * @param modules Kantenlaenge in Modulen <b>einschliesslich</b> Rand; fuer ein
     *     4x4-Woerterbuch mit einem Modul Rand sind das 6.
     */
    public static native byte[] markerBits(int markerId, int modules);
}
