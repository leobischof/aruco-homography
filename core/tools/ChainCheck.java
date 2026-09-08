import com.bischofsnowboards.aruco.NativeCore;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.StringTokenizer;

/**
 * Der Pruefstand fuer die GANZE Messkette durch JNI - auf einer echten JVM.
 *
 * <p>{@link JniCheck} misst eine Funktion: {@code detectMarkers}. Diese Klasse misst die
 * uebrigen fuenfzehn - Homographie, Ausgleich, Kamerapose, Ausdehnung, Geometrie, Entzerrung,
 * Aufbereitung, Umriss. Ohne sie waeren genau die Funktionen ungeprueft, wegen derer diese
 * Schicht ueberhaupt erweitert wurde.
 *
 * <p><b>Wogegen gemessen wird, und warum es zwei Antworten gibt.</b>
 * core/tools/make_chain_reference.py schreibt zu jeder Szene zwei Sollwertbloecke:
 *
 * <ul>
 *   <li>{@code cpp.*} - <b>derselbe</b> C++-Kern, nur durch die pybind11-Bindung statt durch
 *       JNI. Dazwischen liegt nichts als das Umpacken, also muss das Ergebnis BITGENAU gleich
 *       sein. Jede Abweichung ist ein Marshalling-Fehler und nichts sonst. Das ist die
 *       gewertete Pruefung, und ihre Toleranz ist null.
 *   <li>{@code py.*} - die Python-Referenz. Sie rechnet den nichtlinearen Ausgleich mit einem
 *       anderen Verfahren (scipy gegen cv::LevMarq) und kann deshalb gar nicht bitgleich sein.
 *       Der Unterschied wird BERICHTET, in Millimetern, und nicht gewertet.
 * </ul>
 *
 * <p><b>Warum Pruefsummen fuer die Bilder.</b> Ein Rasterbild passt in keine Zahlenliste, und
 * ein Mittelwert waere gegen fast jede Verschiebung blind. SHA-256 ist entweder gleich oder
 * nicht - und genau diese Aussage will man ueber ein Bild haben, das gleich gedruckt wird.
 *
 * <p><b>Die Eingaben stehen in der Datei</b> und werden nicht auf beiden Seiten neu erkannt.
 * Sonst pruefte dieser Vergleich den Detektor noch einmal mit, und ein Fehlschlag liesse
 * offen, wo er entstand.
 */
final class ChainCheck {

    /** Eine Szene aus der Referenzdatei: benannte Zahlenfelder und benannte Woerter. */
    private static final class Reference {
        String name;
        final Map<String, double[]> numbers = new LinkedHashMap<>();
        final Map<String, String> words = new LinkedHashMap<>();

        double[] get(String key) {
            double[] values = numbers.get(key);
            if (values == null) {
                throw new IllegalStateException("Referenz ohne '" + key + "' (Szene " + name + ")");
            }
            return values;
        }

        double one(String key) {
            return get(key)[0];
        }
    }

    private boolean failed = false;

    /**
     * Alle Szenen durchrechnen.
     *
     * @param chain die Referenzdatei aus make_chain_reference.py
     * @param fixtures das Fixture-Paket - daneben liegen die rohen Pixel
     * @return true, wenn jede Funktion bitgenau geliefert hat
     */
    boolean run(Path chain, Path fixtures) throws IOException {
        Map<String, byte[]> pixels = new LinkedHashMap<>();
        for (Reference scene : read(chain)) {
            double[] size = scene.get("in.image_size");
            int width = (int) size[0];
            int height = (int) size[1];
            int channels = (int) size[2];

            byte[] raw = pixels.computeIfAbsent(scene.name, name -> readRaw(fixtures, name));
            long expected = (long) width * height * channels;
            if (raw.length != expected) {
                fail("Rohbild " + scene.name + ": " + raw.length + " Bytes statt " + expected);
                continue;
            }

            System.out.printf("Kette %s (%dx%d)%n", scene.name, width, height);
            checkScene(scene, raw, width, height, channels);
            System.out.println();
        }
        return !failed;
    }

    // --- Die Kette, Schritt fuer Schritt ---------------------------------------------------

    private void checkScene(Reference scene, byte[] raw, int width, int height, int channels) {
        double[] plane = scene.get("in.plane");
        double[] image = scene.get("in.corners");
        double markerMm = scene.one("in.marker_mm");
        double focalPx = scene.one("in.focal_px");

        // 1 - Markerflaeche. Danach wird im Frei-Modus sortiert; eine falsche
        // Flaeche vertauschte den Anker und damit den Ursprung der Ebene.
        double[] ids = scene.get("in.ids");
        double[] areas = new double[ids.length];
        for (int index = 0; index < ids.length; index++) {
            areas[index] = NativeCore.quadArea(slice(image, index * 8, 8));
        }
        exact(scene, "quad_area", areas);

        // 2 - Homographie aus vier Punkten, aus vielen Punkten, ausgeglichen.
        exact(scene, "h_quad",
                NativeCore.homographyFromQuad(slice(plane, 0, 8), slice(image, 0, 8)));
        exact(scene, "h_lmeds", NativeCore.homographyLmeds(plane, image));

        // Der Ausgleich bekommt den Startwert AUS DER DATEI und nicht den eben
        // gerechneten: sonst schleppte ein Fehler in h_lmeds sich weiter, und
        // der Bericht naennte zwei kaputte Funktionen statt einer.
        double[] refined = NativeCore.refineHomography(
                scene.get("cpp.h_lmeds"), plane, image);
        exact(scene, "h_refined", refined);

        // 3 - Frei-Modus. Die Reihenfolge steht in der Datei, weil sie in
        // solve.py wohnt und nicht im Kern.
        double[] order = scene.get("cpp.free_order");
        double[] freeCorners = new double[order.length * 8];
        for (int index = 0; index < order.length; index++) {
            int source = indexOf(ids, order[index]);
            System.arraycopy(image, source * 8, freeCorners, index * 8, 8);
        }
        exact(scene, "fit_free", NativeCore.fitFree(freeCorners, markerMm));
        exact(scene, "fit_scattered", NativeCore.fitScattered(freeCorners, markerMm));

        // 4 - Kamerapose.
        exact(scene, "pose",
                NativeCore.poseFromHomography(scene.get("cpp.h_refined"), focalPx, width, height));

        // 5 - Huelle, Ausdehnung, Massstab.
        double[] hull = NativeCore.convexHull(plane);
        exact(scene, "hull", hull);
        exact(scene, "extent", NativeCore.planeExtent(
                scene.get("cpp.h_refined"), width, height, scene.get("cpp.hull")));

        double[] centroid = scene.get("cpp.hull_centroid");
        exact(scene, "local_px_per_mm", new double[] {
                NativeCore.localPxPerMm(scene.get("cpp.h_refined"), centroid[0], centroid[1])});

        double[] crop = scene.get("cpp.crop");
        double[] rect = {crop[0], crop[1], crop[2], crop[1], crop[2], crop[3], crop[0], crop[3]};
        exact(scene, "intersection", new double[] {
                NativeCore.convexIntersectionArea(rect, scene.get("cpp.hull"))});

        // 6 - Rastergroessen. Die Zahl, mit der der Ausgabepuffer bemessen wird:
        // ein Fehler hier waere ein zu kleiner Puffer und kein falsches Bild.
        double previewPxPerMm = scene.one("cpp.preview_px_per_mm");
        double[] area = scene.get("cpp.extent");
        int[] previewSize =
                NativeCore.outputSize(area[0], area[1], area[2], area[3], previewPxPerMm);
        exact(scene, "preview_size", new double[] {previewSize[0], previewSize[1]});

        double exportPxPerMm = scene.one("in.export_dpi") / 25.4;
        int[] exportSize =
                NativeCore.outputSize(crop[0], crop[1], crop[2], crop[3], exportPxPerMm);
        exact(scene, "export_size", new double[] {exportSize[0], exportSize[1]});

        // 7 - Entzerren. Der Aufrufer stellt beide Puffer; die Ausgabegroesse
        // kommt aus outputSize und wird nicht geraten.
        ByteBuffer source = direct(raw);
        ByteBuffer rectified = ByteBuffer.allocateDirect(previewSize[0] * previewSize[1] * 3)
                .order(ByteOrder.nativeOrder());
        int written = NativeCore.rectify(source, width, height, width * channels, channels,
                scene.get("cpp.h_refined"), area[0], area[1], area[2], area[3], previewPxPerMm,
                scene.one("cpp.local_px_per_mm"), rectified);
        if (written != previewSize[0] * previewSize[1] * 3) {
            fail("rectify schrieb " + written + " Bytes, erwartet "
                    + (previewSize[0] * previewSize[1] * 3));
            return;
        }
        digest(scene, "rectify_sha", rectified, written);

        // 7b - Derselbe Weg noch einmal, eng um die Markerhuelle. Zwei Gruende:
        // dieser Ausschnitt geht durch den ANDEREN Interpolationszweig
        // (Lanczos statt INTER_AREA), und nur auf ihm findet der Umriss unten
        // ueberhaupt etwas. Eine Bindung, die nur die leere Antwort sieht, ist
        // nicht geprueft.
        double[] close = scene.get("cpp.close_crop");
        double closePxPerMm = scene.one("cpp.close_px_per_mm");
        double[] closeSizeWanted = scene.get("cpp.close_size");
        int[] closeSize = NativeCore.outputSize(close[0], close[1], close[2], close[3],
                closePxPerMm);
        exact(scene, "close_size", new double[] {closeSize[0], closeSize[1]});
        if (closeSize[0] != (int) closeSizeWanted[0] || closeSize[1] != (int) closeSizeWanted[1]) {
            return;
        }

        int closeBytes = closeSize[0] * closeSize[1] * 3;
        ByteBuffer closeRaster =
                ByteBuffer.allocateDirect(closeBytes).order(ByteOrder.nativeOrder());
        int closeWritten = NativeCore.rectify(source, width, height, width * channels, channels,
                scene.get("cpp.h_refined"), close[0], close[1], close[2], close[3], closePxPerMm,
                scene.one("cpp.local_px_per_mm"), closeRaster);
        if (closeWritten != closeBytes) {
            fail("rectify (nah) schrieb " + closeWritten + " Bytes, erwartet " + closeBytes);
            return;
        }
        digest(scene, "close_sha", closeRaster, closeWritten);

        // 8 - Aufbereiten. Erst die Abkuerzungsfrage, dann die Regler selbst.
        double[] sliders = scene.get("in.adjust");
        String emphasis = scene.words.get("in.color_emphasis");
        double[] identity = scene.get("cpp.is_identity");
        boolean neutralSays = NativeCore.isIdentity(
                false, false, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "none", 0.0, 0.0);
        boolean chosenSays = NativeCore.isIdentity(
                sliders[0] != 0.0, sliders[1] != 0.0, sliders[2], sliders[3], sliders[4],
                sliders[5], sliders[6], sliders[7], emphasis, sliders[8], sliders[9]);
        exact(scene, "is_identity",
                new double[] {neutralSays ? 1.0 : 0.0, chosenSays ? 1.0 : 0.0});

        ByteBuffer adjusted =
                ByteBuffer.allocateDirect(closeBytes).order(ByteOrder.nativeOrder());
        int adjustedBytes = NativeCore.adjust(closeRaster, closeSize[0], closeSize[1],
                closeSize[0] * 3, 3, sliders[0] != 0.0, sliders[1] != 0.0, sliders[2],
                sliders[3], sliders[4], sliders[5], sliders[6], sliders[7], emphasis, sliders[8],
                sliders[9], adjusted);
        if (adjustedBytes != closeBytes) {
            fail("adjust schrieb " + adjustedBytes + " Bytes, erwartet " + closeBytes
                    + " - Invariante 6 verlangt dieselbe Bildgroesse");
            return;
        }
        digest(scene, "adjust_sha", adjusted, adjustedBytes);

        // 9 - Umriss, auf genau dem Bild, das gedruckt wuerde.
        exact(scene, "contour", NativeCore.findContourMm(adjusted, closeSize[0], closeSize[1],
                closeSize[0] * 3, 3, closePxPerMm));

        // Und die zweite Frage: wie weit liegt das von der Python-Referenz weg?
        reportAgainstPython(scene);
    }

    // --- Vergleichen ------------------------------------------------------------------------

    /**
     * Bitgenau gegen {@code cpp.<name>} - und gegen nichts anderes.
     *
     * <p>Keine Toleranz, mit Absicht: hinter beiden Wegen steckt dieselbe Funktion in
     * core/src/. Ein Unterschied in der letzten Stelle waere kein Rundungsfehler, sondern ein
     * verlorener oder vertauschter Wert im Umpacken.
     */
    private void exact(Reference scene, String name, double[] got) {
        double[] want = scene.get("cpp." + name);
        if (got == null) {
            fail(name + ": die JNI-Schicht gab null zurueck");
            return;
        }
        if (got.length != want.length) {
            fail(name + ": " + got.length + " Werte statt " + want.length);
            return;
        }
        int differing = 0;
        double worst = 0.0;
        for (int index = 0; index < got.length; index++) {
            if (Double.compare(got[index], want[index]) != 0) {
                differing++;
                worst = Math.max(worst, Math.abs(got[index] - want[index]));
            }
        }
        if (differing > 0) {
            fail(String.format(Locale.ROOT, "%s: %d von %d Werten verschieden (groesster "
                    + "Abstand %.3e)", name, differing, got.length, worst));
            return;
        }
        System.out.printf("  [ok] %-18s %d Werte identisch%n", name, got.length);
    }

    /** Dasselbe fuer ein Bild: SHA-256 gegen {@code cpp.<name>}. */
    private void digest(Reference scene, String name, ByteBuffer buffer, int length) {
        byte[] bytes = new byte[length];
        ByteBuffer view = buffer.duplicate();
        view.rewind();
        view.get(bytes);

        String got;
        try {
            got = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(impossible);
        }
        String want = scene.words.get("cpp." + name);
        if (!got.equals(want)) {
            fail(name + ": " + got.substring(0, 16) + "... statt " + want.substring(0, 16)
                    + "... - das Rasterbild ist NICHT dasselbe");
            return;
        }
        System.out.printf("  [ok] %-18s %d Bytes, SHA-256 %s...%n", name, length,
                got.substring(0, 16));
    }

    /**
     * Der Abstand zur Python-Referenz, in der Einheit, in der er weh tut.
     *
     * <p>Nicht gewertet: die beiden Kerne rechnen den nichtlinearen Ausgleich mit
     * verschiedenen Verfahren, und ein Unterschied ist deshalb erwartet. Berichtet, weil das
     * die Zahl ist, nach der jemand fragt, der wissen will, ob die App dasselbe misst wie der
     * Rechner.
     */
    private void reportAgainstPython(Reference scene) {
        System.out.printf(Locale.ROOT, "  gegen die Python-Referenz:%n");
        System.out.printf(Locale.ROOT, "    Ausdehnung   %.3e mm%n",
                worstDifference(scene, "extent"));
        System.out.printf(Locale.ROOT, "    Kamerahoehe  %.3e mm%n",
                Math.abs(scene.get("cpp.pose")[0] - scene.get("py.pose")[0]));
        System.out.printf(Locale.ROOT, "    Massstab     %.3e px/mm%n",
                worstDifference(scene, "local_px_per_mm"));
        System.out.printf(Locale.ROOT, "    Zuschnitt    %.3e mm%n",
                worstDifference(scene, "crop"));
        double[] cppSize = scene.get("cpp.export_size");
        double[] pySize = scene.get("py.export_size");
        System.out.printf(Locale.ROOT, "    Rastergroesse bei %.0f dpi: %.0fx%.0f gegen "
                + "%.0fx%.0f px%n", scene.one("in.export_dpi"), cppSize[0], cppSize[1],
                pySize[0], pySize[1]);
    }

    private static double worstDifference(Reference scene, String name) {
        double[] cpp = scene.get("cpp." + name);
        double[] py = scene.get("py." + name);
        double worst = 0.0;
        for (int index = 0; index < Math.min(cpp.length, py.length); index++) {
            worst = Math.max(worst, Math.abs(cpp[index] - py[index]));
        }
        return worst;
    }

    // --- Kleinkram --------------------------------------------------------------------------

    private void fail(String message) {
        System.out.println("  [x] " + message);
        failed = true;
    }

    private static double[] slice(double[] values, int offset, int length) {
        double[] part = new double[length];
        System.arraycopy(values, offset, part, 0, length);
        return part;
    }

    private static int indexOf(double[] values, double wanted) {
        for (int index = 0; index < values.length; index++) {
            if (values[index] == wanted) {
                return index;
            }
        }
        throw new IllegalStateException("Marker " + wanted + " steht nicht in in.ids");
    }

    private static ByteBuffer direct(byte[] bytes) {
        ByteBuffer buffer = ByteBuffer.allocateDirect(bytes.length).order(ByteOrder.nativeOrder());
        buffer.put(bytes);
        buffer.rewind();
        return buffer;
    }

    private static byte[] readRaw(Path fixtures, String scene) {
        try {
            return Files.readAllBytes(fixtures.getParent().resolve(scene + ".raw"));
        } catch (IOException failure) {
            throw new IllegalStateException("Rohbild nicht lesbar: " + scene, failure);
        }
    }

    // --- Die Referenzdatei lesen ---------------------------------------------------------

    private static List<Reference> read(Path path) throws IOException {
        StringTokenizer tokens =
                new StringTokenizer(Files.readString(path, StandardCharsets.US_ASCII));
        if (!"scenes".equals(tokens.nextToken())) {
            throw new IllegalStateException("Referenzdatei: 'scenes' erwartet");
        }
        int count = Integer.parseInt(tokens.nextToken());

        List<Reference> scenes = new ArrayList<>(count);
        for (int index = 0; index < count; index++) {
            if (!"scene".equals(tokens.nextToken())) {
                throw new IllegalStateException("Referenzdatei: 'scene' erwartet");
            }
            Reference scene = new Reference();
            scene.name = tokens.nextToken();
            while (true) {
                String kind = tokens.nextToken();
                if ("end".equals(kind)) {
                    break;
                }
                String key = tokens.nextToken();
                if ("s".equals(kind)) {
                    scene.words.put(key, tokens.nextToken());
                    continue;
                }
                if (!"d".equals(kind)) {
                    throw new IllegalStateException("Referenzdatei: 'd', 's' oder 'end' "
                            + "erwartet, '" + kind + "' gelesen");
                }
                double[] values = new double[Integer.parseInt(tokens.nextToken())];
                for (int value = 0; value < values.length; value++) {
                    values[value] = Double.parseDouble(tokens.nextToken());
                }
                scene.numbers.put(key, values);
            }
            scenes.add(scene);
        }
        return scenes;
    }
}
