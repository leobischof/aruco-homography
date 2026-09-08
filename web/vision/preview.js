/**
 * preview.js - die Bilder, die die Seite zeigt, und ihre Lebensdauer.
 *
 * Am Server sind das JPEG-Dateien in einem Temp-Verzeichnis, die eine URL
 * bekommen; hier sind es Blobs mit einer `blob:`-URL. Der Unterschied, den man
 * kennen muss: eine Blob-URL haelt ihren Blob am Leben, bis sie ausdruecklich
 * zurueckgegeben wird. Wer bei jedem Reglerzug eine neue erzeugt und die alte
 * stehen laesst, sammelt in einer Minute hunderte Megabyte an - die Sorte Leck,
 * die niemand sieht, weil das Bild ja richtig aussieht.
 *
 * Deshalb gibt es diese Datei: **eine Stelle, die weiss, welche URL gerade
 * gilt, und die vorige freigibt.**
 */

import { toJpegBlob } from "./image.js";

export class PreviewUrls {
    constructor() {
        this.urls = new Map();
    }

    /** Ein Raster als Bild-URL. Die vorige URL derselben Art wird freigegeben. */
    async publish(kind, raster) {
        const blob = await toJpegBlob(raster);
        const url = URL.createObjectURL(blob);
        this.revoke(kind);
        this.urls.set(kind, url);
        return url;
    }

    revoke(kind) {
        const previous = this.urls.get(kind);
        if (previous !== undefined) {
            URL.revokeObjectURL(previous);
            this.urls.delete(kind);
        }
    }

    revokeAll() {
        for (const kind of [...this.urls.keys()]) this.revoke(kind);
    }
}

/**
 * Erkennungs-Overlay: Umriss, Startecke und ID - wie draw_detection in
 * app/vision/detect.py.
 *
 * Rein kosmetisch. Es geht nichts von hier in eine Messung, und deshalb darf es
 * auch mit den Mitteln der Leinwand gezeichnet werden statt mit denen des Kerns:
 * das Bild dient dem Auge, das pruefen will, ob der Detektor die richtigen
 * Vierecke gefunden hat.
 */
export async function drawDetection(photoRaster, markers) {
    const blob = await toJpegBlob(photoRaster);
    const bitmap = await createImageBitmap(blob);
    try {
        const canvas = document.createElement("canvas");
        canvas.width = photoRaster.width;
        canvas.height = photoRaster.height;
        const context = canvas.getContext("2d");
        context.drawImage(bitmap, 0, 0);

        const thickness = Math.max(1, Math.round(Math.min(canvas.width, canvas.height) / 400));
        context.lineWidth = thickness;
        context.strokeStyle = "rgb(0, 220, 0)";
        context.fillStyle = "rgb(0, 220, 0)";
        context.font = `${thickness * 16}px sans-serif`;
        context.textAlign = "center";

        for (const marker of markers) {
            const points = marker.corners;
            context.beginPath();
            context.moveTo(points[0], points[1]);
            for (let corner = 1; corner < 4; corner += 1) {
                context.lineTo(points[corner * 2], points[corner * 2 + 1]);
            }
            context.closePath();
            context.stroke();

            // Die Startecke rot: nur an ihr sieht man, ob die Reihenfolge stimmt,
            // und eine vertauschte Reihenfolge spiegelte die Homographie.
            context.beginPath();
            context.arc(points[0], points[1], thickness * 3, 0, Math.PI * 2);
            context.fillStyle = "rgb(255, 0, 0)";
            context.fill();

            context.fillStyle = "rgb(0, 220, 0)";
            const centreX = (points[0] + points[2] + points[4] + points[6]) / 4;
            const centreY = (points[1] + points[3] + points[5] + points[7]) / 4;
            context.fillText(String(marker.id), centreX, centreY);
        }

        return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
    } finally {
        bitmap.close();
    }
}
