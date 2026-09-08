/**
 * file-picker.js - die Dateiwahl, die sich uebersetzen laesst.
 *
 * Ein <input type="file"> beschriftet sich SELBST, und zwar in der Sprache des
 * Browsers: "Datei auswaehlen" und "Keine ausgewaehlt" standen auch dann auf
 * Deutsch da, wenn die Oberflaeche englisch lief. Kein Attribut aendert das -
 * die Beschriftung gehoert dem Browser, nicht dem Dokument. Der einzige Ausweg
 * ist, das native Bedienelement nicht mehr zu zeigen.
 *
 * Also wird die Eingabe unsichtbar gemacht und ein <label> davorgestellt, dessen
 * Text aus dem Katalog kommt. Drei Dinge muessen dabei erhalten bleiben, sonst
 * ist die Uebersetzung mit einer Verschlechterung bezahlt:
 *
 * 1. **Tastatur.** Die Eingabe wird geklippt (.sr-only), NICHT display:none -
 *    das naehme sie aus der Tabulatorreihenfolge. Den Fokusring zeigt das Label,
 *    weil die Eingabe selbst nichts mehr anzeigt (forms.css).
 * 2. **Ziehen und Fallenlassen.** Das leistet ein natives Dateifeld von allein -
 *    aber nur auf seiner eigenen Flaeche, und die ist jetzt einen Pixel gross.
 *    Deshalb nimmt das Label den Wurf hier selbst entgegen.
 * 3. **Der Dateiname.** Er traegt kein data-i18n: applyTranslations() wuerde ihn
 *    beim naechsten Sprachwechsel durch den Katalogtext ersetzen. Stattdessen
 *    zeichnet diese Datei ihn neu, wenn die Sprache wechselt.
 *
 * ZWEI FELDER, EINE WAHL. Neben dem gewoehnlichen Dateifeld steht eines mit
 * `capture` - das oeffnet die Kamera statt eines Dateiblatts (index.html sagt,
 * warum das nicht ein Feld sein kann). Fuer alles danach sind sie dasselbe: es
 * kommt eine Datei heraus, und die geht denselben Weg. Deshalb kennt der
 * Aufrufer den Unterschied nicht - er bekommt `onFile`, wie vorher auch.
 */

import { onLocaleChange, t } from "./i18n.js";

export function createFilePicker({ input, cameraInput, dropZone, nameOutput, onFile }) {
    let chosen = null;
    const fields = [input, cameraInput].filter(Boolean);

    function renderName() {
        nameOutput.textContent = chosen ? chosen.name : t("ui.steps.upload.no_file");
    }

    function accept(file, from) {
        if (!file) return;

        // Die Wahl liegt bei genau EINEM Feld. Ohne das Leeren des anderen
        // truege es weiter die vorige Datei - unsichtbar, aber das ist der
        // Zustand, den ein Hilfsmittel vorliest, und er waere dann falsch.
        for (const field of fields) {
            if (field !== from) field.value = "";
        }

        chosen = file;
        renderName();
        onFile(file);
    }

    for (const field of fields) {
        field.addEventListener("change", () => accept(field.files[0], field));
    }

    // preventDefault auf BEIDEN Ereignissen: ohne das auf dragover kommt es nie
    // zu einem drop, und ohne das auf drop oeffnet der Browser das Foto einfach
    // im Tab - die Seite waere weg, samt Sitzung.
    dropZone.addEventListener("dragover", (event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = "copy";
        dropZone.classList.add("dragging");
    });

    dropZone.addEventListener("dragleave", (event) => {
        // Wer von der Flaeche auf ihre eigene Beschriftung faehrt, verlaesst sie
        // nicht - ohne diese Pruefung flackerte der Rahmen bei jedem Kind.
        if (!dropZone.contains(event.relatedTarget)) dropZone.classList.remove("dragging");
    });

    dropZone.addEventListener("drop", (event) => {
        event.preventDefault();
        dropZone.classList.remove("dragging");

        const file = event.dataTransfer.files[0];
        if (!file) return;

        // Die unsichtbare Eingabe mitfuehren: sie zeigt nichts mehr an, traegt
        // aber weiterhin den Zustand, den Hilfsmittel vorlesen.
        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;

        accept(file, input);
    });

    onLocaleChange(renderName);
    renderName();

    return { renderName };
}
