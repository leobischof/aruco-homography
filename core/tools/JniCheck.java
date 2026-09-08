import com.bischofsnowboards.aruco.NativeCore;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.StringTokenizer;
import java.util.TreeMap;

/**
 * Der Pruefstand fuer die JNI-Schicht - auf dem BAU-Rechner, auf einer echten JVM.
 *
 * <p><b>Warum es das gibt.</b> Auf diesem Rechner laeuft kein Android: kein Geraet am USB, kein
 * Emulator, kein System-Abbild (docs/cpp-migration/stage-4-cross-targets.md, Abschnitt 5). Ein
 * Kreuzbau, den niemand ausfuehrt, belegt nur, dass er uebersetzt - und das ist die Frage nicht.
 * jni.h kommt aber aus dem JDK und nicht aus dem NDK, und eine JVM gibt es hier. Also wird genau
 * dieselbe jni.cpp gegen dieselbe capi.cpp als Windows-DLL gebaut und von einem echten
 * Java-Prozess aufgerufen. Damit ist das Umpacken zwischen Java und C++ GEMESSEN und nicht
 * behauptet; ungeprueft bleibt danach Androids Linker und die WebView - nicht mehr diese Schicht.
 *
 * <p><b>Was er prueft.</b> Vier Dinge, und jedes davon kann fuer sich schiefgehen:
 *
 * <ol>
 *   <li>Die Konstanten kommen wirklich aus shared/constants.json durch.
 *   <li>{@code detectMarkers} liefert dieselben Ecken wie der C++-Pruefstand - Bit fuer Bit. Die
 *       Ausgabe hat dasselbe Format wie {@code aruco_conformance --ecken}, also vergleicht
 *       core/tools/compare_corners.py die beiden ohne weiteres Zutun.
 *   <li>Der RGBA-Weg - der, den Android wirklich geht - liefert dasselbe wie der BGR-Weg. Das ist
 *       die einzige Stelle, an der die JNI-Schicht selbst rechnet (cvtColor), und ein vertauschter
 *       Kanal saehe in jeder Einzelzahl plausibel aus.
 *   <li>Ein falsch uebergebener Puffer wird abgewiesen und reisst den Prozess NICHT ab. Auf
 *       Android ist genau das der teure Fall: eine C++-Ausnahme durch einen JNI-Rahmen beendet
 *       die App wortlos.
 * </ol>
 *
 * <p>Aufruf: {@code java -Djava.library.path=<dir> JniCheck <fixtures.txt> [--ecken]}
 */
public final class JniCheck {

    /** Eine Szene aus dem Fixture-Paket: rohe Pixel plus Grundwahrheit. */
    private static final class Scene {
        String name;
        String raw;
        int width;
        int height;
        int channels;
        double tolerancePx;
        final Map<Integer, double[]> corners = new TreeMap<>();
    }

    private static boolean failed = false;

    public static void main(String[] args) throws IOException {
        if (args.length < 1) {
            System.err.println(
                    "Aufruf: JniCheck <pfad/zu/fixtures.txt> [--ecken] [--bits] [--kette <datei>]");
            System.exit(2);
        }
        boolean dumpCorners = false;
        boolean dumpBits = false;
        Path chain = null;
        for (int index = 1; index < args.length; index++) {
            if ("--ecken".equals(args[index])) {
                dumpCorners = true;
            } else if ("--bits".equals(args[index])) {
                dumpBits = true;
            } else if ("--kette".equals(args[index]) && index + 1 < args.length) {
                chain = Path.of(args[++index]).toAbsolutePath();
            } else {
                System.err.println("Unbekannter Schalter: " + args[index]);
                System.exit(2);
            }
        }

        NativeCore.load();

        Path manifest = Path.of(args[0]).toAbsolutePath();
        Path directory = manifest.getParent();

        reportConstants();
        checkMarkerBits(dumpBits);
        checkRejectsHeapBuffer();

        for (Scene scene : readManifest(manifest)) {
            System.out.printf("Szene %s (%dx%d, %d Kanaele)%n", scene.name, scene.width,
                    scene.height, scene.channels);
            byte[] pixels = Files.readAllBytes(directory.resolve(scene.raw));
            long expected = (long) scene.width * scene.height * scene.channels;
            if (pixels.length != expected) {
                fail("Rohbild " + scene.raw + ": " + pixels.length + " Bytes statt " + expected);
                continue;
            }

            // Der gewertete Lauf: BGR, mit CLAHE - genau das, was aruco_conformance misst.
            double[] bgr = detect(pixels, scene, scene.channels, true);
            compare(scene, bgr, "clahe", dumpCorners);

            // Der Gegenlauf ohne CLAHE. Nicht gewertet, aber er belegt, dass der Schalter
            // ueberhaupt greift: waeren beide Zeilen gleich, liefe er ins Leere.
            double[] grey = detect(pixels, scene, scene.channels, false);
            compare(scene, grey, "grau", dumpCorners);

            // Und derselbe Inhalt als RGBA - der Weg, den die App auf dem Geraet nimmt.
            if (scene.channels == NativeCore.CHANNELS_BGR) {
                double[] rgba = detect(toRgba(pixels), scene, NativeCore.CHANNELS_RGBA, true);
                if (!sameNumbers(bgr, rgba)) {
                    fail("RGBA liefert andere Ecken als BGR - die Kanalumwandlung in jni.cpp "
                            + "ist falsch.");
                } else {
                    System.out.printf("  [ok] RGBA == BGR ueber %d Werte%n", rgba.length);
                }
            }
            System.out.println();
        }

        // Und die uebrigen fuenfzehn Funktionen. Ohne diesen Block waere genau
        // das ungeprueft, wofuer die Schicht erweitert wurde: eine Bindung, die
        // uebersetzt, misst noch nichts (core/tools/ChainCheck.java).
        if (chain != null) {
            System.out.println("--- Die ganze Kette gegen denselben Kern durch pybind11 ---");
            System.out.println();
            if (!new ChainCheck().run(chain, manifest)) {
                failed = true;
            }
        }

        if (failed) {
            System.out.println("FEHLGESCHLAGEN - die JNI-Schicht stimmt nicht.");
            System.exit(1);
        }
        System.out.println(chain == null
                ? "BESTANDEN - die JNI-Schicht liefert die Ecken der Grundwahrheit."
                : "BESTANDEN - die JNI-Schicht liefert die Ecken der Grundwahrheit und die "
                        + "ganze Kette bitgenau.");
    }

    private static void reportConstants() {
        System.out.println("OpenCV        " + NativeCore.openCvVersion());
        System.out.println("Woerterbuch   " + NativeCore.dictionaryName()
                + " (" + NativeCore.dictionarySize() + " Marker)");
        System.out.println("Markerkante   " + NativeCore.markerMmNominal() + " mm");
        System.out.println();
    }

    /**
     * Die Modulbits - die Vorlage fuer das Markerblatt.
     *
     * <p>Geprueft wird hier die Form (Groesse, schwarzer Rand). Das MUSTER prueft
     * core/tools/compare_marker_bits.py: {@code --bits} schreibt jede Zeile als Hex, und
     * jenes Werkzeug haelt sie gegen dieselben Bits aus cv2. Ein schwarzer Rand allein
     * genuegt nicht - er ist symmetrisch, ein vertauschtes Raster kaeme durch. Und ein
     * vertauschtes Raster ergaebe ein Blatt, das auf dem Bildschirm normal aussieht und das
     * kein Detektor je findet.
     */
    private static void checkMarkerBits(boolean dumpBits) {
        final int modules = 6;
        for (int markerId = 0; markerId < 4; markerId++) {
            byte[] bits = NativeCore.markerBits(markerId, modules);
            if (bits.length != modules * modules) {
                fail("markerBits(" + markerId + ") gab " + bits.length + " statt "
                        + (modules * modules) + " Bytes");
                return;
            }
            for (int index = 0; index < modules; index++) {
                if (bits[index] != 0 || bits[(modules - 1) * modules + index] != 0) {
                    fail("markerBits(" + markerId + "): der Rand ist nicht schwarz");
                    return;
                }
            }
            if (dumpBits) {
                StringBuilder hex = new StringBuilder(bits.length * 2);
                for (byte value : bits) {
                    hex.append(Character.forDigit((value >> 4) & 0xF, 16));
                    hex.append(Character.forDigit(value & 0xF, 16));
                }
                System.out.println("bits " + markerId + " " + modules + " " + hex);
            }
        }
        System.out.println("  [ok] markerBits: 4 Marker, je " + (modules * modules)
                + " Module, Rand schwarz");
    }

    /**
     * Ein Heap-ByteBuffer muss eine IllegalArgumentException geben - und der Prozess muss
     * weiterlaufen. Das ist die Zusage, an der auf Android alles haengt: eine C++-Ausnahme, die
     * sich durch einen JNI-Rahmen entfaltet, beendet die App ohne Meldung.
     */
    private static void checkRejectsHeapBuffer() {
        try {
            NativeCore.detectMarkers(ByteBuffer.allocate(64), 4, 4, 4, 1, false);
            fail("Ein Heap-ByteBuffer wurde angenommen - GetDirectBufferAddress haette NULL "
                    + "liefern muessen.");
        } catch (IllegalArgumentException expected) {
            System.out.println("  [ok] Heap-Puffer abgewiesen: " + expected.getMessage());
        }
        try {
            ByteBuffer tooSmall = ByteBuffer.allocateDirect(8);
            NativeCore.detectMarkers(tooSmall, 100, 100, 100, 1, false);
            fail("Ein zu kleiner Puffer wurde angenommen.");
        } catch (IllegalArgumentException expected) {
            System.out.println("  [ok] Zu kleiner Puffer abgewiesen: " + expected.getMessage());
        }
        System.out.println();
    }

    private static double[] detect(byte[] pixels, Scene scene, int channels, boolean clahe) {
        ByteBuffer buffer = ByteBuffer.allocateDirect(pixels.length).order(ByteOrder.nativeOrder());
        buffer.put(pixels);
        buffer.rewind();
        return NativeCore.detectMarkers(buffer, scene.width, scene.height,
                scene.width * channels, channels, clahe);
    }

    /** BGR -> RGBA, so wie eine Android-Bitmap es liefern wuerde (Alpha voll deckend). */
    private static byte[] toRgba(byte[] bgr) {
        byte[] rgba = new byte[bgr.length / 3 * 4];
        for (int pixel = 0, source = 0, target = 0; source < bgr.length; pixel++) {
            rgba[target++] = bgr[source + 2];  // R
            rgba[target++] = bgr[source + 1];  // G
            rgba[target++] = bgr[source];      // B
            rgba[target++] = (byte) 0xFF;      // A
            source += 3;
        }
        return rgba;
    }

    private static boolean sameNumbers(double[] left, double[] right) {
        if (left.length != right.length) {
            return false;
        }
        for (int index = 0; index < left.length; index++) {
            if (Double.compare(left[index], right[index]) != 0) {
                return false;
            }
        }
        return true;
    }

    /**
     * Die gefundenen Ecken gegen die Grundwahrheit halten - dieselbe Rechnung und dasselbe
     * Ausgabeformat wie core/tests/conformance.cpp, damit compare_corners.py beide lesen kann.
     */
    private static void compare(Scene scene, double[] found, String mode, boolean dumpCorners) {
        int markers = found.length / NativeCore.VALUES_PER_MARKER;
        boolean scored = "clahe".equals(mode);
        if (markers != scene.corners.size()) {
            System.out.printf("  [x] %d Marker gefunden, %d erwartet%n", markers,
                    scene.corners.size());
            if (scored) {
                failed = true;
            }
            return;
        }

        double worst = 0.0;
        double sum = 0.0;
        int counted = 0;
        for (int marker = 0; marker < markers; marker++) {
            int base = marker * NativeCore.VALUES_PER_MARKER;
            int id = (int) found[base];
            double[] truth = scene.corners.get(id);
            if (truth == null) {
                System.out.printf("  [x] Marker %d steht nicht in der Grundwahrheit%n", id);
                if (scored) {
                    failed = true;
                }
                continue;
            }

            double markerWorst = 0.0;
            for (int corner = 0; corner < 4; corner++) {
                double x = found[base + 1 + corner * 2];
                double y = found[base + 2 + corner * 2];
                double dx = x - truth[corner * 2];
                double dy = y - truth[corner * 2 + 1];
                double error = Math.sqrt(dx * dx + dy * dy);
                markerWorst = Math.max(markerWorst, error);
                sum += error;
                counted++;
                if (dumpCorners) {
                    // %.17g gibt es in Java nicht - %.17s waere etwas anderes. Der
                    // aequivalente Weg ist Double.toString: es schreibt die kuerzeste
                    // Darstellung, die exakt zurueckliest, und genau darauf kommt es an.
                    System.out.printf(Locale.ROOT, "ecke %s %s %d %d %s %s %s%n", scene.name,
                            mode, id, corner, Double.toString(x), Double.toString(y),
                            Double.toString(error));
                }
            }
            worst = Math.max(worst, markerWorst);
            boolean held = markerWorst <= scene.tolerancePx;
            System.out.printf(Locale.ROOT, "  %s Marker %d: groesster Eckfehler %.4f px "
                    + "(Toleranz %.4f px)%n", held ? "[ok]" : "[x] ", id, markerWorst,
                    scene.tolerancePx);
            if (!held && scored) {
                failed = true;
            }
        }
        System.out.printf(Locale.ROOT, "       %s: Mittel %.4f px, groesster %.4f px ueber %d "
                + "Ecken%n", mode, counted > 0 ? sum / counted : 0.0, worst, counted);
    }

    private static void fail(String message) {
        System.out.println("  [x] " + message);
        failed = true;
    }

    // --- Das Fixture-Paket lesen (dasselbe Format wie core/tests/conformance.cpp) ------------

    private static List<Scene> readManifest(Path manifest) throws IOException {
        StringTokenizer tokens = new StringTokenizer(
                Files.readString(manifest, StandardCharsets.US_ASCII));
        expect(tokens, "scenes");
        int count = Integer.parseInt(tokens.nextToken());

        List<Scene> scenes = new ArrayList<>();
        Map<String, Scene> byName = new LinkedHashMap<>();
        for (int index = 0; index < count; index++) {
            Scene scene = new Scene();
            expect(tokens, "scene");
            scene.name = tokens.nextToken();
            expect(tokens, "raw");
            scene.raw = tokens.nextToken();
            expect(tokens, "size");
            scene.width = Integer.parseInt(tokens.nextToken());
            scene.height = Integer.parseInt(tokens.nextToken());
            scene.channels = Integer.parseInt(tokens.nextToken());
            expect(tokens, "tol_corner_px");
            scene.tolerancePx = Double.parseDouble(tokens.nextToken());

            expect(tokens, "markers");
            int markers = Integer.parseInt(tokens.nextToken());
            for (int marker = 0; marker < markers; marker++) {
                expect(tokens, "marker");
                int id = Integer.parseInt(tokens.nextToken());
                double[] values = new double[8];
                for (int value = 0; value < 8; value++) {
                    values[value] = Double.parseDouble(tokens.nextToken());
                }
                scene.corners.put(id, values);
            }
            scenes.add(scene);
            byName.put(scene.name, scene);
        }
        return scenes;
    }

    private static void expect(StringTokenizer tokens, String word) {
        String token = tokens.nextToken();
        if (!word.equals(token)) {
            throw new IllegalStateException(
                    "Fixture-Paket: '" + word + "' erwartet, '" + token + "' gelesen");
        }
    }

    private JniCheck() {}
}
