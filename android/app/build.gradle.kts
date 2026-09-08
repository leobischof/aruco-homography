plugins {
    id("com.android.application")
}

// Kurzer Bauplatz gegen MAX_PATH - der Grund steht in android/gradle.properties.
providers.gradleProperty("aruco.buildRoot").orNull?.let { root ->
    layout.buildDirectory.set(File("$root/${project.name}"))
}

// Das Repo liegt zwei Ebenen ueber diesem Modul (android/app -> android -> repo).
val repoRoot: File = rootProject.projectDir.parentFile

/**
 * Die Fassung kommt aus app/config.py und wird NICHT hier abgetippt (AGENTS.md,
 * Invariante 4). ./dev.ps1 build-apk liest sie dort und reicht sie herein; ohne
 * die Angabe baut Gradle trotzdem, nennt sich aber ausdruecklich "unversioned"
 * statt eine Zahl zu erfinden, die dann neben der echten steht.
 */
val arucoVersionName: String = providers.gradleProperty("aruco.versionName").getOrElse("unversioned")
val arucoVersionCode: Int = providers.gradleProperty("aruco.versionCode").getOrElse("1").toInt()

/**
 * Welche ABIs ins APK kommen.
 *
 * Vorgabe ist NUR arm64-v8a. Jedes ABI traegt ein vollstaendiges, statisch
 * gebundenes OpenCV mit sich (rund 6 MB), und arm64 ist seit Android 5 auf
 * praktisch jedem verkauften Telefon das laufende ABI - Google Play nimmt seit
 * August 2019 gar keine reinen 32-Bit-Anwendungen mehr an. Wer die anderen
 * braucht:  ./dev.ps1 build-apk -- arm64-v8a,armeabi-v7a
 */
val arucoAbis: List<String> =
    providers.gradleProperty("aruco.abis").getOrElse("arm64-v8a").split(",").map { it.trim() }

android {
    namespace = "com.bischofsnowboards.aruco"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.bischofsnowboards.aruco"

        // 24 und nicht 21: dieselbe Zahl, die ./dev.ps1 build-core-android dem
        // NDK gibt (ANDROID_PLATFORM=android-24). Zwei verschiedene Zahlen
        // ergaeben ein APK, das sich auf einem Geraet installieren laesst, auf
        // dem die .so nicht laedt.
        minSdk = 24
        targetSdk = 35

        versionCode = arucoVersionCode
        versionName = arucoVersionName

        ndk { abiFilters += arucoAbis }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildTypes {
        release {
            // Kein Schrumpfen: es gibt keine Bibliothek, die sich lohnte, und
            // R8 auf einer WebView-Huelle mit JNI-Namen ist eine Fehlerquelle
            // ohne Gegenwert. Der Platz steckt in der .so, nicht im Java.
            isMinifyEnabled = false
        }
    }

    packaging {
        jniLibs {
            // Unkomprimiert und ausgerichtet im APK ablegen. Nur so kann der
            // Linker die .so direkt aus dem APK abbilden (kein Entpacken beim
            // Installieren), und nur so greift die 16-KB-Ausrichtung, die
            // core/CMakeLists.txt beim Binden setzt. Seit AGP 8 ist das die
            // Vorgabe - hier steht es trotzdem, weil die Zusage sonst an einer
            // Vorgabe haengt, die eine kuenftige Fassung still aendern kann.
            useLegacyPackaging = false
        }
    }

    lint {
        // Der Bau soll an einem Lint-Befund nicht scheitern, aber der Bericht
        // soll entstehen: er liegt danach in build/reports/lint-results-*.html.
        abortOnError = false
    }
}

dependencies {
    // androidx.webkit bringt zwei Dinge, die die Huelle wirklich braucht und die
    // das nackte android.webkit nicht hat:
    //
    //  * WebViewAssetLoader - liefert die Oberflaeche unter einem https-Ursprung
    //    aus statt unter file://. ES-Module ueber file:// scheitern an der
    //    Ursprungspruefung ("opaque origin"), und app/static/ IST ein Baum aus
    //    ES-Modulen. Ohne das laedt die Oberflaeche schlicht nicht.
    //  * addDocumentStartJavaScript - laesst die Bruecke laufen, BEVOR das erste
    //    Modul der Seite laeuft. Damit bleibt app/static/index.html Byte fuer
    //    Byte unveraendert; ein eingefuegtes <script> waere eine zweite Fassung
    //    der Oberflaeche.
    implementation("androidx.webkit:webkit:1.12.1")

    // FileProvider - fuer die zwei Wege nach draussen (aufgenommenes Foto,
    // geteiltes PDF). Ausdruecklich genannt und nicht ueber webkit mitgezogen:
    // eine Abhaengigkeit, die man benutzt, gehoert in die Liste, sonst
    // verschwindet sie beim naechsten Fassungswechsel von webkit.
    implementation("androidx.core:core:1.13.1")
}

/**
 * Die Netzinhalte einsammeln - aus dem Repo, nicht aus einer Kopie.
 *
 * **Hier wird nichts verdoppelt.** app/static/, web/pdf/ und shared/ bleiben ihre
 * eigene einzige Quelle; dieser Schritt legt sie nur so nebeneinander, wie die
 * relativen Importe es erwarten. Eine eingecheckte Kopie unter android/assets/
 * waere eine zweite Oberflaeche, und zwei Oberflaechen driften.
 *
 * Die Verschachtelung sieht seltsam aus und ist es nicht: web/pdf/i18n.js
 * importiert "../../app/static/i18n/de.json", web/pdf/constants.js importiert
 * "../../shared/constants.json". Von www/web/pdf/ aus zeigen die beiden auf
 * www/app/static/i18n/ und www/shared/ - also muessen sie dort liegen. Die
 * Kataloge liegen deshalb zweimal im APK (einmal unter /i18n/ fuer die
 * Oberflaeche, einmal unter /app/static/i18n/ fuer den PDF-Bau); zusammen sind
 * das rund 30 KB, und der Ausweg waere ein Bundler, den dieses Projekt bewusst
 * nicht hat.
 */
val gatherWebAssets by tasks.registering(Sync::class) {
    description = "app/static/, web/pdf/, shared/ und pdf-lib in einen Assets-Baum legen"
    into(layout.buildDirectory.dir("aruco-assets"))

    into("www") { from(repoRoot.resolve("app/static")) }
    into("www/app/static/i18n") { from(repoRoot.resolve("app/static/i18n")) }
    into("www/web/pdf") {
        from(repoRoot.resolve("web/pdf")) { exclude("**/*.test.mjs") }
    }
    // Die Rechenkette. DIESELBEN Dateien, die im Browser laufen - nur core.js
    // und image.js bleiben draussen: fuer die beiden gibt es hier eine
    // Android-Fassung (core-android.js, image-android.js), und die Importkarte
    // in native/bridge-shim.js tauscht sie.
    //
    // Der Ausschluss ist nicht Sparsamkeit. web/vision/core.js laedt
    // web/vendor/core/aruco_core.wasm - 3,6 MB WebAssembly. Auf diesem Ziel
    // rechnet aber die native Bibliothek ueber JNI (Stufe 4, "Architektur"), und
    // ein zweiter Rechenkern im APK waere genau die Fassung, die niemand mehr
    // mitmisst. Liegt die Datei nicht im Paket, kann sie auch niemand aus
    // Versehen laden: eine fehlgeschlagene Importkarte gibt dann einen
    // Ladefehler statt eines stillen zweiten Kerns.
    into("www/web/vision") {
        from(repoRoot.resolve("web/vision")) {
            exclude("core.js", "image.js", "**/*.test.mjs")
        }
    }
    into("www/web") { from(repoRoot.resolve("web/constants.js")) }
    into("www/shared") { from(repoRoot.resolve("shared/constants.json")) }
    into("www/vendor") {
        from(repoRoot.resolve("node_modules/pdf-lib/dist/pdf-lib.esm.min.js"))
    }

    // Die eingefrorenen Szenen samt Grundwahrheit. 160 KB - dafuer kann das
    // Geraet den Pruefstand aus shared/fixtures/ SELBST fahren, und damit faellt
    // der Satz "Android ist ungemessen" (Stufe 4, Abschnitt 5).
    into("fixtures") { from(repoRoot.resolve("shared/fixtures")) }

    doFirst {
        val pdfLib = repoRoot.resolve("node_modules/pdf-lib/dist/pdf-lib.esm.min.js")
        if (!pdfLib.exists()) {
            throw GradleException(
                "pdf-lib fehlt: $pdfLib\n" +
                    "     Im Wurzelverzeichnis des Repos einmal 'npm install' laufen lassen."
            )
        }
    }
}

// Das Verzeichnis als Quelle - und die Abhaengigkeit AUSDRUECKLICH.
//
// AGPs `assets.srcDir()` traegt ein Verzeichnis ein, aber es uebernimmt daraus
// KEINE Aufgabenabhaengigkeit - weder von einem TaskProvider noch von einem
// Provider<File>. Beides wurde hier probiert: der Bau lief beide Male gruen
// durch, gatherWebAssets lief gar nicht, und im APK lag von der Oberflaeche
// genau nichts. Die WebView haette eine leere Seite gezeigt, und der Bau haette
// dazu geschwiegen.
//
// Deshalb steht die Abhaengigkeit hier von Hand, an den Merge-Aufgaben (eine je
// Variante). Ueber den NAMEN und nicht ueber die AGP-Klasse: der Klassenname
// wandert zwischen AGP-Fassungen, das Namensmuster nicht.
//
// Und damit dieser Fehler nicht ein drittes Mal still passiert, zaehlt
// ./dev.ps1 check-apk die Dateien im fertigen APK nach.
android.sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("aruco-assets"))

tasks.matching { it.name.startsWith("merge") && it.name.endsWith("Assets") }.configureEach {
    dependsOn(gatherWebAssets)
}
