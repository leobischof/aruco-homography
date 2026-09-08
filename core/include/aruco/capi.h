/* Die C-Schnittstelle des Rechenkerns - die Grenze, an der eine FREMDE Sprache
 * andockt.
 *
 * Warum C und nicht das C++ aus detect.hpp: eine C++-Schnittstelle ist keine
 * stabile ABI. `std::vector` sieht unter MSVC anders aus als unter clang, ein
 * geworfenes `std::invalid_argument` entfaltet sich nicht durch einen
 * JVM-Rahmen, und der Name einer C++-Funktion haengt an der Namensverzierung des
 * Uebersetzers. Die JNI-Schicht daneben (core/bindings/jni.cpp) koennte damit
 * leben, weil sie im selben Bau steckt - aber jede spaetere Bindung koennte es
 * nicht, und die JNI-Schicht ist nicht der einzige geplante Aufrufer.
 *
 * Drei Regeln, die diese Datei einhaelt und die jede Erweiterung einhalten muss:
 *
 *  1. **Keine Ausnahme verlaesst diesen Kopf.** Jede Funktion faengt alles und
 *     gibt einen negativen Code plus Klartext zurueck. Eine Ausnahme, die durch
 *     die JNI-Grenze laeuft, beendet auf Android den ganzen Prozess.
 *  2. **Kein Besitz wechselt die Seite.** Der Aufrufer stellt jeden Puffer, der
 *     Kern schreibt hinein. Es gibt nichts freizugeben, also gibt es auch nichts
 *     zu vergessen.
 *  3. **Nichts aus imgcodecs.** Wie in aruco/types.hpp: rohe Pixel herein, Zahlen
 *     heraus. Das Dekodieren gehoert auf jedes Ziel einzeln - auf Android macht
 *     es die Plattform (BitmapFactory), im Browser die Leinwand.
 */

#ifndef ARUCO_CAPI_H
#define ARUCO_CAPI_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Rueckgabewerte. Alles >= 0 ist ein Ergebnis (meist eine Anzahl), alles < 0 ein
 * Fehler - dann steht der Klartext im `error`-Puffer. */
#define ARUCO_OK 0
#define ARUCO_ERR_ARGUMENT (-1)  /* Der Aufrufer hat Unsinn uebergeben. */
#define ARUCO_ERR_CAPACITY (-2)  /* Der Ausgabepuffer ist zu klein. */
#define ARUCO_ERR_INTERNAL (-3)  /* OpenCV oder der Kern haben geworfen. */

/* Ein erkannter Marker in flacher Form.
 *
 * Die acht Werte sind TL.x TL.y TR.x TR.y BR.x BR.y BL.x BL.y - genau die
 * Reihenfolge aus aruco/types.hpp und damit die von cv::aruco. Eine andere
 * Reihenfolge spiegelte die Homographie, und das Ergebnis saehe plausibel aus.
 *
 * `double` und nicht `float`, weil die Messung ab der Erkennung in doppelter
 * Genauigkeit weiterrechnet - genau wie die Python-Seite. */
typedef struct aruco_marker {
    int32_t id;
    double corners[8];
} aruco_marker;

/* Alle Marker im Bild finden.
 *
 * `data`      zeilenweise dichte uint8-Pixel, dem Kern NICHT gehoerend.
 * `stride`    Bytes je Zeile (nicht Pixel).
 * `channels`  1 = grau, 3 = BGR.
 * `enhance_contrast`  0/1 - legt CLAHE vor die Erkennung (siehe detect.hpp).
 * `out`       Feld fuer die Ergebnisse, mindestens `out_capacity` Eintraege.
 * `error`     Puffer fuer den Klartext; darf NULL sein.
 *
 * Rueckgabe: Anzahl der geschriebenen Marker (>= 0), sonst ein negativer Code.
 * Reicht `out_capacity` nicht, ist das ARUCO_ERR_CAPACITY und NICHT eine stille
 * Kuerzung: ein fehlender Marker verzoege die Homographie, ohne dass irgendwo
 * etwas rot wuerde. Wie gross der Puffer sein muss, sagt aruco_dictionary_size().
 */
int32_t aruco_detect_markers(const uint8_t* data, int32_t width, int32_t height, int32_t stride,
                             int32_t channels, int32_t enhance_contrast, aruco_marker* out,
                             int32_t out_capacity, char* error, int32_t error_capacity);

/* Die Modulbits eines Markers, zeilenweise, ein Byte je Modul (0 = schwarz).
 *
 * Das braucht das Markerblatt: web/pdf/markersheet.js zeichnet jedes Modul als
 * Vektorrechteck und bekommt die Bits von aussen. Unter Node liefert sie
 * opencv.js (tools/opencv_markers.mjs), auf Android diese Funktion - dieselbe
 * Grenze, dieselbe Form, damit auf beiden Wegen dasselbe Blatt entsteht.
 *
 * `modules` ist die Kantenlaenge IN MODULEN einschliesslich Rand; fuer ein
 * 4x4-Woerterbuch mit einem Modul Rand sind das 6. Geschrieben werden
 * `modules * modules` Bytes.
 *
 * Rueckgabe: Anzahl geschriebener Bytes (>= 0), sonst ein negativer Code. */
int32_t aruco_marker_bits(int32_t marker_id, int32_t modules, uint8_t* out, int32_t out_capacity,
                          char* error, int32_t error_capacity);

/* Wie viele Marker das eingestellte Woerterbuch kennt.
 *
 * Damit ist der Ausgabepuffer von aruco_detect_markers exakt zu bemessen: mehr
 * verschiedene IDs kann es nicht geben, und der Kern raeumt Doppelerkennungen
 * selbst weg. Ein Aufrufer, der das benutzt, kann ARUCO_ERR_CAPACITY nicht
 * bekommen und muss die Erkennung nicht zweimal laufen lassen, um die Anzahl zu
 * erfahren - auf einem 12-MP-Foto waere das die teuerste Zeile der App. */
int32_t aruco_dictionary_size(void);

/* Der Name des Woerterbuchs, erzeugt aus shared/constants.json. Nicht freigeben:
 * der Zeiger zeigt auf statischen Speicher und lebt so lange wie die
 * Bibliothek. */
const char* aruco_dictionary_name(void);

/* Die nominelle Markerkante in Millimetern, aus shared/constants.json.
 *
 * Die Huelle braucht sie fuer die Vorgabe im Eingabefeld. Sie hier zu holen statt
 * sie abzutippen ist Invariante 4: eine Konstante hat genau eine Stelle - und
 * eine abgetippte waere eine, die in Millimetern driftet. */
double aruco_marker_mm_nominal(void);

/* Die OpenCV-Fassung, gegen die gebunden wurde ("5.0.0").
 *
 * Nicht Zierde: die Typkennungen haben sich zwischen 4.x und 5.0 verschoben, und
 * ein Bericht vom Geraet, der die Fassung nicht nennt, laesst genau die Frage
 * offen, die man dann stellen wuerde. */
const char* aruco_opencv_version(void);

/* ===========================================================================
 * Die ganze Messkette
 * ===========================================================================
 *
 * Bis hierher konnte diese Schnittstelle genau eines: Markerecken. Alles
 * darunter ist der Rest der Messung - Homographie, Ausgleich, Kamerapose,
 * Ausdehnung, Entzerrung, Aufbereitung, Umriss. Es ist dieselbe Liste, die
 * core/bindings/web.cpp dem Browser gibt, in derselben Reihenfolge und mit
 * denselben Namen; wer beide nebeneinanderlegt, soll dieselbe Kette sehen.
 *
 * VIER REGELN, die jede dieser Funktionen einhaelt.
 *
 * 1. **Der Rueckgabewert ist der Zustand, nie das Ergebnis.** >= 0 heisst
 *    gelungen (und ist meistens eine Anzahl), < 0 ist einer der Codes oben.
 *    Ein Ergebnis, das selbst eine Zahl ist, kommt deshalb ueber einen
 *    Ausgabezeiger und nicht als Rueckgabewert: sonst waere ein legitimes
 *    -0,5 mm/px von einem Fehlercode nicht zu unterscheiden.
 *
 * 2. **Punkte sind flach: x,y,x,y,...** Genau die Form, in der sie durch jede
 *    Bindung wandern (Float64Array, double[], numpy (N,2)) - und die einzige,
 *    bei der ein Vertauschen von x und y auffiele, weil sie ueberall gleich
 *    aussieht. Eine Homographie sind neun Zahlen, zeilenweise.
 *
 * 3. **Kein Besitz wechselt die Seite - auch nicht bei Bildern.** Das ist der
 *    Punkt, an dem diese Schnittstelle sich von der embind-Fassung
 *    unterscheidet, und der Unterschied ist Absicht. Im Browser gibt `rectify`
 *    ein Objekt zurueck, das der Aufrufer `delete()`n muss; wer das in einer
 *    Schleife ueber mehrere Fotos vergisst, verliert den Tab. Hier gibt es
 *    nichts freizugeben, weil nichts angelegt wird: der Aufrufer stellt den
 *    Puffer, der Kern schreibt hinein.
 *
 *    Moeglich ist das nur, weil die AUSGABEGROESSE VOR DEM AUFRUF FESTSTEHT:
 *
 *      aruco_rectify  ->  aruco_output_size(...) * 3 Bytes
 *      aruco_adjust   ->  width * height * 3 Bytes (die Groesse aendert sich
 *                         nie; Invariante 6 - die Aufbereitung ist kosmetisch)
 *
 *    Beide Funktionen weisen einen zu kleinen Puffer mit ARUCO_ERR_CAPACITY ab
 *    und schreiben nichts. Eine stille Kuerzung waere hier besonders teuer: ein
 *    halb gefuelltes Rasterbild sieht aus wie ein Fehler der Kamera.
 *
 *    Was das kostet, steht auch hier: der Kern legt das Rasterbild intern
 *    einmal an und kopiert es dann in den Puffer des Aufrufers, die Spitze ist
 *    also das Doppelte der Ausgabe. Der Ausweg - `aruco::rectify` mit einem
 *    Ausgabepuffer statt eines Rueckgabewerts - beruehrte alle drei Bindungen
 *    und ist bewusst nicht Teil dieser Aenderung. Ein Leck haette in derselben
 *    Schleife ein VIELFACHES gekostet, und niemand haette es gesehen.
 *
 * 4. **Nichts aus imgcodecs** (wie oben). Rohe Pixel herein, rohe Pixel oder
 *    Zahlen heraus. Auf Android dekodiert BitmapFactory und kodiert
 *    Bitmap.compress; im Browser die Leinwand.
 */

/* --- Homographie und Ausgleich -------------------------------------------- */

/* Homographie aus GENAU VIER Punktpaaren (getPerspectiveTransform).
 *
 * `plane_xy8` und `image_xy8` sind je acht Zahlen (vier Punkte), `out9` nimmt
 * die Homographie zeilenweise auf. Rueckgabe ARUCO_OK oder ein Fehlercode. */
int32_t aruco_homography_from_quad(const double* plane_xy8, const double* image_xy8,
                                   double* out9, char* error, int32_t error_capacity);

/* Homographie aus vielen Punktpaaren, robust (findHomography, LMEDS).
 *
 * `count` zaehlt PUNKTE, nicht Zahlen: beide Felder sind 2*count lang. LMEDS
 * braucht mehr als vier Punkte; mit genau vieren gehoert
 * aruco_homography_from_quad benutzt. */
int32_t aruco_homography_lmeds(const double* plane_xy, const double* image_xy, int32_t count,
                               double* out9, char* error, int32_t error_capacity);

/* Nichtlinearer Ausgleich des Reprojektionsfehlers ueber die acht freien
 * Parameter. `start9` ist die Ausgangshomographie, `out9` die ausgeglichene. */
int32_t aruco_refine_homography(const double* start9, const double* plane_xy,
                                const double* image_xy, int32_t count, double* out9,
                                char* error, int32_t error_capacity);

/* Frei-Modus: Homographie und Markerversaetze gemeinsam schaetzen.
 *
 * `corners_xy` sind vier Ecken je Marker, also 8 * marker_count Zahlen. Die
 * Marker muessen ABSTEIGEND NACH BILDFLAECHE sortiert sein - der erste ist der
 * Anker und legt Ursprung und Massstab der Ebene fest. Sortiert wird in der
 * Huelle, weil nur sie die Marker-IDs kennt, die hinterher wieder zugeordnet
 * werden muessen.
 *
 * `out9` nimmt die Homographie, `out_offsets_xy` die Versaetze der uebrigen
 * Marker: marker_count - 1 Punkte, in derselben Reihenfolge. `capacity_points`
 * zaehlt Punkte.
 *
 * Rueckgabe: Anzahl geschriebener Versatz-PUNKTE (>= 0), sonst ein Fehlercode.
 * Bei genau einem Marker ist das 0 und kein Fehler. */
int32_t aruco_fit_free(const double* corners_xy, int32_t marker_count, double marker_mm,
                       double* out9, double* out_offsets_xy, int32_t capacity_points,
                       char* error, int32_t error_capacity);

/* --- Kamera und Ausdehnung ------------------------------------------------ */

/* Zerlegt H = K [r1 r2 t] und schreibt VIER Zahlen nach `out4`:
 * Hoehe_mm, Lotpunkt_x_mm, Lotpunkt_y_mm, Neigung_grad.
 *
 * Ob das Ergebnis plausibel ist, entscheidet die Huelle (CAM_HEIGHT_MIN_MM /
 * MAX_MM aus shared/constants.json) und nicht diese Funktion: sie rechnet, sie
 * urteilt nicht. */
int32_t aruco_pose_from_homography(const double* homography9, double focal_px, int32_t width,
                                   int32_t height, double* out4, char* error,
                                   int32_t error_capacity);

/* Bounding-Box des abbildbaren Ebenenbereichs als x0, y0, x1, y1 in `out4`.
 *
 * `hull_xy` ist die konvexe Huelle der gemessenen Marker in Ebenen-mm; sie
 * begrenzt, wie weit ueber den gemessenen Bereich hinaus fortgeschrieben wird
 * (EXTENT_HULL_FACTOR). `hull_count` zaehlt Punkte. */
int32_t aruco_plane_extent(const double* homography9, int32_t width, int32_t height,
                           const double* hull_xy, int32_t hull_count, double* out4,
                           char* error, int32_t error_capacity);

/* --- Geometrie ------------------------------------------------------------ */

/* Konvexe Huelle. `count` und `capacity_points` zaehlen Punkte; die Huelle hat
 * nie mehr Punkte als die Eingabe, ein Puffer mit `count` Punkten reicht also
 * immer. Rueckgabe: Anzahl geschriebener Punkte. */
int32_t aruco_convex_hull(const double* points_xy, int32_t count, double* out_xy,
                          int32_t capacity_points, char* error, int32_t error_capacity);

/* Flaeche des Schnitts zweier KONVEXER Polygone, in `out_area`. */
int32_t aruco_convex_intersection_area(const double* first_xy, int32_t first_count,
                                       const double* second_xy, int32_t second_count,
                                       double* out_area, char* error, int32_t error_capacity);

/* Lokaler Abbildungsmassstab Ebene -> Bild an einer Stelle, in `out_px_per_mm`.
 * Aus ihm wird mm_per_px der Fusszeile, und damit ist er kein Nebenwert. */
int32_t aruco_local_px_per_mm(const double* homography9, double x_mm, double y_mm,
                              double* out_px_per_mm, char* error, int32_t error_capacity);

/* Bildflaeche eines Markervierecks (acht Zahlen), in `out_area`. Danach werden
 * die Marker im Frei-Modus sortiert. */
int32_t aruco_quad_area(const double* quad_xy8, double* out_area, char* error,
                        int32_t error_capacity);

/* --- Entzerren und Aufbereiten -------------------------------------------- */

/* Rastergroesse in Pixeln fuer einen Zuschnitt bei gegebener Aufloesung.
 *
 * Die Funktion, mit der ein Aufrufer den Puffer fuer aruco_rectify bemisst:
 * `*out_width * *out_height * 3` Bytes. Sie rundet wie Pythons round() und ist
 * damit dieselbe Zahl wie am Server. */
int32_t aruco_output_size(double x0, double y0, double x1, double y1, double px_per_mm,
                          int32_t* out_width, int32_t* out_height, char* error,
                          int32_t error_capacity);

/* Entzerrt den Zuschnitt in ein Raster mit genau `px_per_mm` Pixeln je
 * Millimeter. Erwartet ein BGR-Bild (channels == 3).
 *
 * `source_px_per_mm` ist 0, solange niemand die Quellaufloesung kennt - dann
 * wird interpoliert (Lanczos) statt flaechengemittelt (INTER_AREA). Beim
 * Verkleinern ist der Unterschied sichtbar.
 *
 * `out` muss aruco_output_size(...) * 3 Bytes fassen; `out_capacity` ist die
 * Groesse in BYTES. Rueckgabe: Anzahl geschriebener Bytes (>= 0), sonst ein
 * Fehlercode. Reicht der Puffer nicht, wird NICHTS geschrieben. */
int32_t aruco_rectify(const uint8_t* data, int32_t width, int32_t height, int32_t stride,
                      int32_t channels, const double* homography9, double x0, double y0,
                      double x1, double y1, double px_per_mm, double source_px_per_mm,
                      uint8_t* out, int32_t out_capacity, char* error, int32_t error_capacity);

/* Die Reglerstellung der Bildaufbereitung.
 *
 * Ein Struct und keine zwoelf Einzelargumente: die Liste waechst, und ein
 * verrutschtes Argument in einer Reihe gleichartiger `double` faellt niemandem
 * auf - das Ergebnis saehe nur ein bisschen anders aus. Ein Struct nach C-ABI
 * ist ausserdem das, was jede Fremdsprache ohne Weiteres nachbilden kann.
 *
 * `color_emphasis` darf NULL sein und heisst dann "none". Der Zeiger muss nur
 * fuer die Dauer des Aufrufs gelten; der Kern kopiert. */
typedef struct aruco_adjust_options {
    int32_t grayscale;         /* 0/1 */
    int32_t invert;            /* 0/1 */
    double brightness;         /* -1..1 */
    double contrast;           /* -1..1 */
    double saturation;         /* -1..1 */
    double local_contrast;     /* 0..1 */
    double edge_boost;         /* 0..1 */
    double edge_overlay;       /* 0..1 */
    double emphasis_strength;  /* 0..1 */
    double threshold;          /* 0..1, 0 = aus */
    const char* color_emphasis;
} aruco_adjust_options;

/* Kosmetische Aufbereitung eines entzerrten BGR-Bildes.
 *
 * Die Ausgabe ist IMMER width * height * 3 Bytes - auch bei `grayscale`, das
 * nach BGR zurueckwandelt. Invariante 6: kein Regler aendert die Bildgroesse,
 * und keiner verschiebt ein Pixel.
 *
 * `options` darf NULL sein (alles neutral). Rueckgabe: geschriebene Bytes. */
int32_t aruco_adjust(const uint8_t* data, int32_t width, int32_t height, int32_t stride,
                     int32_t channels, const aruco_adjust_options* options, uint8_t* out,
                     int32_t out_capacity, char* error, int32_t error_capacity);

/* 1, wenn keine einzige Stufe der Aufbereitung etwas zu tun haette; 0 sonst.
 *
 * Die Entscheidung gehoert hierher und nicht in die Huelle: sie haengt an
 * denselben Wachklauseln wie die Stufen selbst, und zwei Fassungen davon
 * liefen auseinander, ohne dass ein Ergebnis falsch wuerde - nur die
 * Abkuerzung griffe nicht mehr. */
int32_t aruco_is_identity(const aruco_adjust_options* options, char* error,
                          int32_t error_capacity);

/* Groesste plausible Aussenkontur im ENTZERRTEN BGR-Bild, in Ebenen-mm.
 *
 * Eine Schnitthilfe, kein Messwerkzeug: sie steht und faellt mit dem Kontrast
 * zwischen Objekt und Untergrund. Findet sich nichts Plausibles, ist die
 * Rueckgabe 0 - das ist KEIN Fehler, und das PDF entsteht dann ohne Linie.
 * Lieber keine Linie als eine falsche.
 *
 * `capacity_points` zaehlt Punkte. Eine Kontur hat selten mehr als ein paar
 * hundert; wer sich nicht festlegen will, nimmt die Bildbreite plus Hoehe -
 * mehr Punkte kann ein Umriss auf einem Pixelraster nicht haben. */
int32_t aruco_find_contour_mm(const uint8_t* data, int32_t width, int32_t height,
                              int32_t stride, int32_t channels, double px_per_mm,
                              double* out_xy, int32_t capacity_points, char* error,
                              int32_t error_capacity);

#ifdef __cplusplus
}  /* extern "C" */
#endif

#endif /* ARUCO_CAPI_H */
