/**
 * units.js - Millimeter nach Punkt und zurueck. Die EINE Stelle.
 *
 * PDF rechnet in Punkt (1/72 Zoll), das Produkt rechnet in Millimetern. Genau
 * eine Umrechnung darf es geben: 1 mm = 72/25,4 pt = 2,834645669 pt. Die Pruefung
 * verlangt 0,01 mm Genauigkeit, das sind 0,028 pt - weit ueber der Aufloesung von
 * `double`, aber nicht ueber der eines zweiten, leicht anderen Faktors irgendwo im
 * Code. Deshalb steht der Faktor hier und wird nirgends abgeschrieben.
 *
 * Der Faktor selbst wird NICHT exportiert. Wer ihn braucht, braucht in Wahrheit
 * mmToPt oder ptToMm - und eine Multiplikation von Hand ist genau die zweite
 * Stelle, die es nicht geben soll.
 */

import { MM_PER_INCH } from "./constants.js";

const PT_PER_INCH = 72.0;
const PT_PER_MM = PT_PER_INCH / MM_PER_INCH;

/** Millimeter in PDF-Punkte. */
export function mmToPt(millimetres) {
    return Number(millimetres) * PT_PER_MM;
}

/** PDF-Punkte in Millimeter. */
export function ptToMm(points) {
    return Number(points) / PT_PER_MM;
}
