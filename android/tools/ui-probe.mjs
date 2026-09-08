/**
 * ui-probe.mjs - ein Chromium starten, die Probe fahren, das PDF herausholen.
 *
 * **Ohne Playwright, ohne npm-Abhaengigkeit.** Der Browser wird ueber sein
 * eigenes Debug-Protokoll gesteuert (CDP): starten mit
 * `--remote-debugging-port`, den Seiten-Anschluss aus `/json/list` holen, ueber
 * einen WebSocket `Runtime.evaluate` schicken. Node 22 bringt `fetch` und
 * `WebSocket` mit, also braucht es dafuer nichts weiter. Ein Pruefwerkzeug, das
 * erst 150 MB Browser nachlaedt, ist auf einem Rechner ohne Netz keines.
 *
 * Aufruf (macht ./dev.ps1 check-android-ui):
 *
 *   node android/tools/ui-probe.mjs <chrome.exe> <url> [<pdf-ziel> [<blattweise-ziel>]]
 */

import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [chrome, url, pdfTarget, sheetsTarget] = process.argv.slice(2);
if (!chrome || !url) {
    console.error("Aufruf: node android/tools/ui-probe.mjs <chrome.exe> <url>"
        + " [<pdf-ziel> [<blattweise-ziel>]]");
    process.exit(2);
}

const port = 9222 + (process.pid % 500);
const profile = mkdtempSync(join(tmpdir(), "aruco-chrome-"));
const browser = spawn(chrome, [
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=Translate,OptimizationHints",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    url,
], { stdio: "ignore" });

const sleep = (ms) => new Promise((wait) => setTimeout(wait, ms));

/** Den Seiten-Anschluss abwarten - der Browser braucht einen Moment. */
async function pageSocket() {
    for (let attempt = 0; attempt < 80; attempt += 1) {
        try {
            const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
            const page = list.find((entry) => entry.type === "page" && entry.webSocketDebuggerUrl);
            if (page) return page.webSocketDebuggerUrl;
        } catch { /* noch nicht offen */ }
        await sleep(250);
    }
    throw new Error("Chrome antwortet nicht auf dem Debug-Port");
}

let socket = null;
let failed = false;
try {
    socket = new WebSocket(await pageSocket());
    await new Promise((ready, broke) => {
        socket.addEventListener("open", ready, { once: true });
        socket.addEventListener("error", broke, { once: true });
    });

    let nextId = 1;
    const waiting = new Map();
    // Was die Seite auf die Konsole schreibt und was sie wirft, gehoert in die
    // Ausgabe: ohne das ist ein Fehlschlag hier eine leere Zeile, und der Grund
    // steht in einem Browserfenster, das niemand sieht.
    socket.addEventListener("message", (event) => {
        const message = JSON.parse(event.data);
        if (message.method === "Runtime.consoleAPICalled") {
            const args = (message.params.args || [])
                .map((value) => value.value ?? value.description ?? value.type).join(" ");
            console.log(`  [Seite ${message.params.type}] ${args}`);
            return;
        }
        if (message.method === "Runtime.exceptionThrown") {
            console.log(`  [Seite wirft] ${message.params.exceptionDetails.text} `
                + `${message.params.exceptionDetails.exception?.description ?? ""}`);
            return;
        }
        const entry = waiting.get(message.id);
        if (entry) {
            waiting.delete(message.id);
            entry(message);
        }
    });

    function send(method, params) {
        const id = nextId++;
        return new Promise((got) => {
            waiting.set(id, got);
            socket.send(JSON.stringify({ id, method, params }));
        });
    }

    async function evaluate(expression) {
        const answer = await send("Runtime.evaluate", {
            expression, awaitPromise: true, returnByValue: true,
        });
        if (answer.result?.exceptionDetails) {
            const details = answer.result.exceptionDetails;
            throw new Error(`${details.text} ${details.exception?.description ?? ""}`);
        }
        return answer.result?.result?.value;
    }

    await evaluate("1");            // wartet, bis der Kontext steht
    await send("Runtime.enable", {});

    // Die Seite meldet sich fertig, indem sie FERTIG in die Ausgabe schreibt.
    // Zwei Minuten sind reichlich: die Entzerrung eines 300-dpi-Rasters dauert
    // Sekunden, das PDF ebenso.
    let text = "";
    for (let attempt = 0; attempt < 240; attempt += 1) {
        // Der Zugriff ist bewusst nachsichtig: gleich nach dem Wechsel gibt es
        // das Dokument noch nicht, und eine Ausnahme dafuer waere kein Befund.
        text = await evaluate("(document.getElementById('out') || {}).textContent || ''");
        if (typeof text === "string" && text.includes("FERTIG")) break;
        await sleep(500);
    }
    console.log(text);

    if (!text.includes("FERTIG")) {
        console.error("Die Probe ist nicht fertig geworden (Zeitablauf).");
        failed = true;
    } else if (text.includes("AUSNAHME") || text.includes("FEHLER")) {
        failed = true;
    }

    if (pdfTarget) {
        const base64 = await evaluate("window.__probePdfBase64 || ''");
        if (base64) {
            writeFileSync(pdfTarget, Buffer.from(base64, "base64"));
            console.log(`PDF geschrieben: ${pdfTarget}`);
        } else {
            console.error("Kein PDF in der Seite - nichts zu schreiben.");
            failed = true;
        }
    }

    // Der blattweise Export. Eigene Datei, weil er eigens nachgemessen wird:
    // dass er dieselbe Geometrie ergibt wie der Weg am Stueck, ist die ganze
    // Zusage der blattweisen Rasterung.
    if (sheetsTarget) {
        const base64 = await evaluate("window.__probeSheetsBase64 || ''");
        if (base64) {
            writeFileSync(sheetsTarget, Buffer.from(base64, "base64"));
            console.log(`PDF (blattweise) geschrieben: ${sheetsTarget}`);
        } else {
            console.error("Kein blattweises PDF in der Seite.");
            failed = true;
        }
    }
} finally {
    if (socket) socket.close();
    browser.kill();
    await sleep(400);
    try { rmSync(profile, { recursive: true, force: true }); } catch { /* egal */ }
}

process.exit(failed ? 1 : 0);
