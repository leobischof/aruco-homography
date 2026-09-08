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

    // ---------------------------------------------------------------------------------------
    // Der Rest der Messkette
    //
    // Dieselbe Liste wie in aruco/capi.h und in core/bindings/web.cpp, in derselben
    // Reihenfolge und mit denselben Namen. Bis hierher konnte diese Klasse nur Markerecken;
    // ab hier kann sie messen.
    //
    // ZWEI FORMEN, und der Unterschied ist der Speicher:
    //
    //   * Zahlen gehen als {@code double[]}. Punktlisten sind flach: x, y, x, y, ... Eine
    //     Homographie sind neun Werte, zeilenweise. Das darf kopiert werden.
    //   * Bilder gehen als DIREKTER ByteBuffer, in beide Richtungen - auch die Ausgabe. Der
    //     Aufrufer stellt sie, weil ihre Groesse vorher feststeht ({@link #outputSize}); was
    //     niemandem gehoert, kann niemand vergessen freizugeben. Ein Rasterbild als
    //     {@code byte[]} waeren bei 300 dpi zweistellige Megabyte je Aufruf, kopiert, auf dem
    //     Java-Haufen.
    // ---------------------------------------------------------------------------------------

    /** Homographie aus genau vier Punktpaaren (je acht Zahlen). */
    public static native double[] homographyFromQuad(double[] planeXy8, double[] imageXy8);

    /** Homographie aus vielen Punktpaaren, robust (LMEDS). Braucht mehr als vier Punkte. */
    public static native double[] homographyLmeds(double[] planeXy, double[] imageXy);

    /** Nichtlinearer Ausgleich des Reprojektionsfehlers ueber die acht freien Parameter. */
    public static native double[] refineHomography(
            double[] start9, double[] planeXy, double[] imageXy);

    /**
     * Frei-Modus: Homographie und Markerversaetze gemeinsam schaetzen.
     *
     * <p>Die Marker muessen <b>absteigend nach Bildflaeche</b> sortiert sein - der erste ist der
     * Anker. Sortiert wird in der Huelle, weil nur sie die Marker-IDs kennt.
     *
     * @param cornersXy vier Ecken je Marker, also acht Zahlen je Marker
     * @return neun Zahlen Homographie, danach je Marker <b>ausser dem ersten</b> zwei Zahlen
     *     Versatz. Bei einem einzigen Marker sind es genau neun.
     */
    public static native double[] fitFree(double[] cornersXy, double markerMm);

    /**
     * Zerlegt H = K [r1 r2 t].
     *
     * @return vier Zahlen: Hoehe_mm, Lotpunkt_x_mm, Lotpunkt_y_mm, Neigung_grad. Ob das
     *     plausibel ist, entscheidet die Huelle und nicht der Kern.
     */
    public static native double[] poseFromHomography(
            double[] homography9, double focalPx, int width, int height);

    /** Bounding-Box des abbildbaren Ebenenbereichs: x0, y0, x1, y1 in Ebenen-mm. */
    public static native double[] planeExtent(
            double[] homography9, int width, int height, double[] hullXy);

    /** Konvexe Huelle, flach als x, y, x, y, ... */
    public static native double[] convexHull(double[] pointsXy);

    /** Flaeche des Schnitts zweier <b>konvexer</b> Polygone. */
    public static native double convexIntersectionArea(double[] firstXy, double[] secondXy);

    /** Lokaler Abbildungsmassstab Ebene -&gt; Bild. Daraus wird mm_per_px der Fusszeile. */
    public static native double localPxPerMm(double[] homography9, double xMm, double yMm);

    /** Bildflaeche eines Markervierecks (acht Zahlen). Danach wird im Frei-Modus sortiert. */
    public static native double quadArea(double[] quadXy8);

    /**
     * Rastergroesse in Pixeln fuer einen Zuschnitt.
     *
     * <p>Die Methode, mit der der Ausgabepuffer fuer {@link #rectify} bemessen wird:
     * {@code breite * hoehe * 3} Bytes.
     *
     * @return zwei Werte: Breite, Hoehe
     */
    public static native int[] outputSize(
            double x0, double y0, double x1, double y1, double pxPerMm);

    /**
     * Entzerrt den Zuschnitt in ein Raster mit genau {@code pxPerMm} Pixeln je Millimeter.
     *
     * @param source BGR-Pixel, direkter ByteBuffer
     * @param target direkter ByteBuffer mit mindestens {@link #outputSize} mal drei Bytes
     * @param sourcePxPerMm 0, solange die Quellaufloesung unbekannt ist - dann wird
     *     interpoliert statt flaechengemittelt
     * @return Anzahl geschriebener Bytes
     * @throws IllegalArgumentException wenn ein Puffer nicht direkt oder zu klein ist
     */
    public static native int rectify(
            java.nio.ByteBuffer source,
            int width,
            int height,
            int stride,
            int channels,
            double[] homography9,
            double x0,
            double y0,
            double x1,
            double y1,
            double pxPerMm,
            double sourcePxPerMm,
            java.nio.ByteBuffer target);

    /**
     * Kosmetische Aufbereitung eines entzerrten BGR-Bildes.
     *
     * <p>Die Regler stehen einzeln und nicht als Feld: in einer Reihe gleichartiger
     * {@code double} faellt ein verrutschter Wert niemandem auf - das Ergebnis saehe nur ein
     * bisschen anders aus. Die Reihenfolge ist dieselbe wie in der Python-Bindung.
     *
     * <p>Die Ausgabe ist <b>immer</b> {@code breite * hoehe * 3} Bytes, auch bei
     * {@code grayscale}: Invariante 6 - kein Regler aendert die Bildgroesse.
     *
     * @param colorEmphasis ein Schluessel aus ADJUST_EMPHASIS_HUES, {@code "none"} oder null
     * @return Anzahl geschriebener Bytes
     */
    public static native int adjust(
            java.nio.ByteBuffer source,
            int width,
            int height,
            int stride,
            int channels,
            boolean grayscale,
            boolean invert,
            double brightness,
            double contrast,
            double saturation,
            double localContrast,
            double edgeBoost,
            double edgeOverlay,
            String colorEmphasis,
            double emphasisStrength,
            double threshold,
            java.nio.ByteBuffer target);

    /**
     * True, wenn keine einzige Stufe der Aufbereitung etwas zu tun haette.
     *
     * <p>Der Kern entscheidet das und nicht die Huelle: die Bedingung haengt an denselben
     * Wachklauseln wie die Stufen selbst.
     */
    public static native boolean isIdentity(
            boolean grayscale,
            boolean invert,
            double brightness,
            double contrast,
            double saturation,
            double localContrast,
            double edgeBoost,
            double edgeOverlay,
            String colorEmphasis,
            double emphasisStrength,
            double threshold);

    /**
     * Groesste plausible Aussenkontur im <b>entzerrten</b> BGR-Bild, in Ebenen-mm.
     *
     * <p>Eine Schnitthilfe, kein Messwerkzeug. Ein leeres Feld heisst "nichts Plausibles
     * gefunden" - das ist kein Fehler, das PDF entsteht dann ohne Linie.
     *
     * @return flach als x, y, x, y, ...
     */
    public static native double[] findContourMm(
            java.nio.ByteBuffer source,
            int width,
            int height,
            int stride,
            int channels,
            double pxPerMm);
}
