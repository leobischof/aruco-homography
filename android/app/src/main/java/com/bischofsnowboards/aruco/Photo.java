package com.bischofsnowboards.aruco;

import android.content.ContentResolver;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Matrix;
import android.media.ExifInterface;
import android.net.Uri;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

/**
 * Ein geladenes Foto - das Gegenstueck zu {@code app/vision/detect.py::load_photo}.
 *
 * <p><b>Die EXIF-Drehung wird angewandt, bevor irgendjemand misst.</b> Das ist keine
 * Kosmetik: ein Handy schreibt das Bild fast immer in Sensor-Ausrichtung und legt die
 * Drehung als EXIF-Marke daneben. {@code BitmapFactory} folgt dieser Marke NICHT. Wer sie
 * ignoriert, sucht die Marker in einem um 90 Grad gedrehten Bild - und findet sie
 * entweder gar nicht oder mit vertauschten Achsen. Die Python-Seite macht dasselbe
 * ({@code ImageOps.exif_transpose}); waeren die beiden hier verschieden, laege der
 * Unterschied zwischen den Kernen nicht im Detektor, sondern im Laden.
 *
 * <p><b>Warum ein direkter ByteBuffer.</b> Der Kern liest die Pixel an Ort und Stelle
 * (aruco/types.hpp). {@code Bitmap.copyPixelsToBuffer} schreibt genau einmal in einen
 * Puffer ausserhalb des Java-Haufens; danach kostet der Aufruf nach C++ keine Kopie und
 * haelt den Speicherbereiniger nicht an.
 */
public final class Photo {

    /** RGBA, zeilenweise dicht - genau das, was ARGB_8888 in einen Puffer schreibt. */
    public final ByteBuffer pixels;

    public final int width;
    public final int height;

    /** Die 35-mm-Brennweite aus EXIF, oder 0, wenn die Kamera keine schreibt. */
    public final double focal35Mm;

    /** Das Kameramodell aus EXIF, oder null. */
    public final String cameraModel;

    /** Wie das Bild gedreht werden musste, in Grad - nur fuer den Bericht. */
    public final int exifRotationDeg;

    private Photo(ByteBuffer pixels, int width, int height, double focal35Mm, String cameraModel,
            int exifRotationDeg) {
        this.pixels = pixels;
        this.width = width;
        this.height = height;
        this.focal35Mm = focal35Mm;
        this.cameraModel = cameraModel;
        this.exifRotationDeg = exifRotationDeg;
    }

    /** Bytes je Zeile. Nach {@code copyPixelsToBuffer} ist das genau {@code width * 4}. */
    public int stride() {
        return width * 4;
    }

    /**
     * Ein Foto aus einer content-URI laden.
     *
     * <p>Der Strom wird ZWEIMAL geoeffnet - einmal fuer EXIF, einmal fuer die Pixel. Ein
     * einzelner Durchlauf ginge nur ueber einen zurueckspulbaren Strom, und den gibt ein
     * ContentProvider nicht zu. Die Alternative waere, die ganze Datei in den Speicher zu
     * lesen; bei 12 MP HEIC sind das mehrere Megabyte ohne Gegenwert.
     */
    public static Photo load(ContentResolver resolver, Uri uri) throws IOException {
        double focal35 = 0.0;
        String model = null;
        int orientation = ExifInterface.ORIENTATION_NORMAL;
        try (InputStream stream = resolver.openInputStream(uri)) {
            if (stream != null) {
                ExifInterface exif = new ExifInterface(stream);
                focal35 = exif.getAttributeDouble(
                        ExifInterface.TAG_FOCAL_LENGTH_IN_35MM_FILM, 0.0);
                model = exif.getAttribute(ExifInterface.TAG_MODEL);
                orientation = exif.getAttributeInt(
                        ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
            }
        } catch (IOException | RuntimeException ignored) {
            // Ein defekter EXIF-Block ist kein Fehlerfall. Das Bild ist trotzdem
            // brauchbar - es fehlt dann nur die Brennweite, und dafuer gibt es in der
            // Oberflaeche das Eingabefeld fuer den Kameraabstand.
        }

        Bitmap bitmap;
        try (InputStream stream = resolver.openInputStream(uri)) {
            if (stream == null) {
                throw new IOException("Der Anbieter gab keinen Datenstrom her: " + uri);
            }
            BitmapFactory.Options options = new BitmapFactory.Options();
            options.inPreferredConfig = Bitmap.Config.ARGB_8888;
            // inScaled sonst skaliert Android das Bild anhand der Bildschirmdichte -
            // stillschweigend, und die Millimeter waeren dahin.
            options.inScaled = false;
            bitmap = BitmapFactory.decodeStream(stream, null, options);
        }
        if (bitmap == null) {
            throw new IOException("Bild nicht lesbar: " + uri);
        }
        return fromBitmap(bitmap, orientation, focal35, model);
    }

    /** Dasselbe aus rohen Bytes - dafuer, was die Kamera-App in den Cache gelegt hat. */
    public static Photo fromBytes(byte[] data) throws IOException {
        double focal35 = 0.0;
        String model = null;
        int orientation = ExifInterface.ORIENTATION_NORMAL;
        try {
            ExifInterface exif = new ExifInterface(new java.io.ByteArrayInputStream(data));
            focal35 = exif.getAttributeDouble(ExifInterface.TAG_FOCAL_LENGTH_IN_35MM_FILM, 0.0);
            model = exif.getAttribute(ExifInterface.TAG_MODEL);
            orientation = exif.getAttributeInt(
                    ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
        } catch (IOException | RuntimeException ignored) {
            // siehe load()
        }

        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inPreferredConfig = Bitmap.Config.ARGB_8888;
        options.inScaled = false;
        Bitmap bitmap = BitmapFactory.decodeByteArray(data, 0, data.length, options);
        if (bitmap == null) {
            throw new IOException("Bild nicht lesbar (" + data.length + " Bytes)");
        }
        return fromBitmap(bitmap, orientation, focal35, model);
    }

    /**
     * Ein PNG oder JPEG aus den Assets - fuer den Pruefstand auf dem Geraet.
     *
     * <p>Ohne EXIF und ohne Drehung: die eingefrorenen Szenen aus shared/fixtures/ tragen
     * keine, und eine angewandte Drehung waere hier ein Fehler und keine Korrektur.
     */
    public static Photo fromAsset(InputStream stream) throws IOException {
        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inPreferredConfig = Bitmap.Config.ARGB_8888;
        options.inScaled = false;
        Bitmap bitmap = BitmapFactory.decodeStream(stream, null, options);
        if (bitmap == null) {
            throw new IOException("Szene nicht lesbar");
        }
        return fromBitmap(bitmap, ExifInterface.ORIENTATION_NORMAL, 0.0, null);
    }

    private static Photo fromBitmap(Bitmap bitmap, int orientation, double focal35, String model) {
        Bitmap upright = applyExifOrientation(bitmap, orientation);
        if (upright != bitmap) {
            bitmap.recycle();
        }

        int width = upright.getWidth();
        int height = upright.getHeight();
        ByteBuffer buffer = ByteBuffer.allocateDirect(width * height * 4)
                .order(ByteOrder.nativeOrder());
        upright.copyPixelsToBuffer(buffer);
        buffer.rewind();
        upright.recycle();

        return new Photo(buffer, width, height, focal35, model, rotationDegrees(orientation));
    }

    private static int rotationDegrees(int orientation) {
        switch (orientation) {
            case ExifInterface.ORIENTATION_ROTATE_90:
            case ExifInterface.ORIENTATION_TRANSPOSE:
                return 90;
            case ExifInterface.ORIENTATION_ROTATE_180:
            case ExifInterface.ORIENTATION_FLIP_VERTICAL:
                return 180;
            case ExifInterface.ORIENTATION_ROTATE_270:
            case ExifInterface.ORIENTATION_TRANSVERSE:
                return 270;
            default:
                return 0;
        }
    }

    /**
     * Alle acht EXIF-Ausrichtungen aufloesen, nicht nur die drei Drehungen.
     *
     * <p>Die gespiegelten Faelle sind selten und genau deshalb gefaehrlich: eine Spiegelung
     * dreht die Eckenreihenfolge des Markers um (TL, TR, BR, BL wird zu TR, TL, BL, BR),
     * und die Homographie waere dann ebenfalls gespiegelt - ein Ergebnis, das plausibel
     * aussieht und in der Breite stimmt.
     */
    private static Bitmap applyExifOrientation(Bitmap bitmap, int orientation) {
        Matrix matrix = new Matrix();
        switch (orientation) {
            case ExifInterface.ORIENTATION_FLIP_HORIZONTAL:
                matrix.setScale(-1f, 1f);
                break;
            case ExifInterface.ORIENTATION_ROTATE_180:
                matrix.setRotate(180f);
                break;
            case ExifInterface.ORIENTATION_FLIP_VERTICAL:
                matrix.setRotate(180f);
                matrix.postScale(-1f, 1f);
                break;
            case ExifInterface.ORIENTATION_TRANSPOSE:
                matrix.setRotate(90f);
                matrix.postScale(-1f, 1f);
                break;
            case ExifInterface.ORIENTATION_ROTATE_90:
                matrix.setRotate(90f);
                break;
            case ExifInterface.ORIENTATION_TRANSVERSE:
                matrix.setRotate(-90f);
                matrix.postScale(-1f, 1f);
                break;
            case ExifInterface.ORIENTATION_ROTATE_270:
                matrix.setRotate(-90f);
                break;
            default:
                return bitmap;
        }
        // filter = false. Alle acht EXIF-Faelle sind Vielfache von 90 Grad und
        // Spiegelungen; dabei faellt jedes Zielpixel genau auf ein Quellpixel. Eine
        // bilineare Filterung haette hier nichts zu interpolieren und waere trotzdem
        // eine Stelle, an der sich Pixelwerte aendern koennten.
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.getWidth(), bitmap.getHeight(), matrix,
                false);
    }

    /** Die Pixel als RGB (ohne Alpha) - fuer die Pruefsumme des Pruefstands. */
    public byte[] rgbBytes() {
        byte[] rgb = new byte[width * height * 3];
        ByteBuffer source = pixels.duplicate();
        source.rewind();
        for (int target = 0; target < rgb.length; target += 3) {
            rgb[target] = source.get();
            rgb[target + 1] = source.get();
            rgb[target + 2] = source.get();
            source.get();  // Alpha weg
        }
        return rgb;
    }

    /** Als JPEG kodieren - fuer die Vorschau in der Oberflaeche. */
    public byte[] toJpeg(int quality) {
        Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        ByteBuffer source = pixels.duplicate();
        source.rewind();
        bitmap.copyPixelsFromBuffer(source);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        bitmap.compress(Bitmap.CompressFormat.JPEG, quality, out);
        bitmap.recycle();
        return out.toByteArray();
    }
}
