package com.bischofsnowboards.aruco;

import android.graphics.Bitmap;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;

/**
 * Ein Rasterbild des Kerns als JPEG - die eine Uebersetzung, die Android beisteuert.
 *
 * <p><b>Warum das hier steht und nicht im Kern.</b> {@code core/} fasst {@code imgcodecs}
 * nicht an (aruco/types.hpp): rohe Pixel herein, rohe Pixel heraus. Das Kodieren gehoert auf
 * jedes Ziel einzeln - im Browser macht es die Leinwand, auf dem Rechner Pillow, hier
 * {@code Bitmap.compress}. Ein PNG- oder JPEG-Kodierer im Kern waere auf jedem Ziel ein
 * zweiter neben dem, den die Plattform ohnehin mitbringt.
 *
 * <p><b>Wozu ueberhaupt.</b> {@code web/pdf/build.js} bettet das entzerrte Bild als JPEG in
 * das PDF ein und nimmt dafuer JPEG-Bytes entgegen. Und die Vorschau in der Oberflaeche ist
 * ein {@code <img>}, also auch ein JPEG. Beide Wege enden hier.
 *
 * <p><b>Was es kostet.</b> {@code Bitmap} kann nur ARGB_8888, der Kern liefert BGR - also
 * entsteht zwischendurch eine Kopie mit vier Bytes je Pixel. Bei einem 300-dpi-Raster von
 * einem halben Meter Kantenlaenge sind das ueber achtzig Megabyte, einmal, waehrend der
 * Kodierung. Das ist der Preis dafuer, dass das PDF ein eingebettetes Bild traegt, und er
 * faellt auf jedem Ziel an; auf dem Rechner zahlt ihn Pillow.
 */
final class Rasters {

    private Rasters() {}

    /**
     * Ein BGR-Raster als JPEG.
     *
     * @param quality 1..100 - kommt aus {@code shared/constants.json} und wird von der
     *     JavaScript-Seite durchgereicht, damit die Zahl nicht ein zweites Mal hier steht
     *     (Invariante 4)
     */
    static byte[] toJpeg(NativeImages.Image image, int quality) {
        if (image.channels != NativeCore.CHANNELS_BGR) {
            throw new IllegalArgumentException(
                    "Nur BGR laesst sich kodieren, nicht " + image.channels + " Kanaele");
        }

        int[] argb = new int[image.width * image.height];
        ByteBuffer source = image.pixels.duplicate();
        source.rewind();
        byte[] row = new byte[image.stride()];
        for (int line = 0, target = 0; line < image.height; line++) {
            source.get(row);
            for (int pixel = 0, read = 0; pixel < image.width; pixel++, read += 3) {
                // 0xFF000000 | R<<16 | G<<8 | B - die Reihenfolge, die setPixels erwartet.
                argb[target++] = 0xFF000000
                        | ((row[read + 2] & 0xFF) << 16)
                        | ((row[read + 1] & 0xFF) << 8)
                        | (row[read] & 0xFF);
            }
        }

        Bitmap bitmap = Bitmap.createBitmap(argb, image.width, image.height,
                Bitmap.Config.ARGB_8888);
        try {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            bitmap.compress(Bitmap.CompressFormat.JPEG, quality, out);
            return out.toByteArray();
        } finally {
            bitmap.recycle();
        }
    }
}
