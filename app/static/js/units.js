/**
 * units.js - die eine Umrechnungszahl, die diese Schicht selbst kennen muss.
 *
 * **Warum sie hier steht und nicht in shared/constants.json.** Die Regel des
 * Projekts ist klar (AGENTS.md, Invariante 4): eine Konstante gibt es einmal,
 * und zwar dort. Diese Schicht kommt aber nicht heran. `app/static/js/` wird auf
 * dem Server unter `/js/` ausgeliefert, im Browser-Bau unter `/app/static/js/`
 * und im APK noch einmal woanders - ein Import von `shared/constants.json`
 * traefe in jedem der drei Faelle einen anderen relativen Pfad. Alles andere,
 * was diese Schicht an Zahlen braucht, kommt deshalb ueber die Antwort mit
 * (`defaults`, `limits`); nur die Zoll-Definition kommt in keiner Antwort vor,
 * weil sie keine Einstellung ist.
 *
 * Was hier zaehlt: sie steht **einmal**. Vorher lag dieselbe 25,4 in
 * crop-info.js, und der Bildexport haette daneben eine zweite gebraucht.
 * Zwei Zahlen, die dasselbe bedeuten, laufen irgendwann auseinander - und ein
 * Zoll, der an einer Stelle anders lang ist als an der anderen, faellt genau
 * dort auf, wo es weh tut: in den Millimetern.
 */

/** Millimeter je Zoll. Definition, kein Messwert. */
export const MM_PER_INCH = 25.4;
