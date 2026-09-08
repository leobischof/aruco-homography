# Der C++-Rechenkern. Gebaut wird er ueber ./dev.ps1 build-core, das die
# Werkzeugkette sucht und die Pfade hier hineinreicht - von Hand:
#
#   cmake -S core -B core/build -G Ninja -DCMAKE_BUILD_TYPE=Release \
#         -DOpenCV_DIR=<sdk>/build -Dpybind11_DIR=<venv>/.../pybind11 \
#         -DPython_EXECUTABLE=<venv>/Scripts/python.exe
#
# Zwei Dinge entstehen: das Python-Modul `aruco_core` (die Bindung, gegen die die
# vorhandene Testsuite mit ARUCO_CORE=cpp faehrt) und `aruco_conformance` (der
# Pruefstand gegen shared/fixtures/).
#
# DREI ZIELE, EINE QUELLE. Dieselbe Datei uebersetzt auch fuer Android (NDK) und
# fuer den Browser (Emscripten) - siehe docs/cpp-migration/stage-4-cross-targets.md
# und ./dev.ps1 build-core-wasm / build-core-android. Was je Ziel verschieden ist,
# steht unten hinter einer Fallunterscheidung und nirgends sonst; der C++-Quelltext
# selbst kennt keine Ziel-Ifdefs. Genau das ist die Behauptung, fuer die dieser
# Umzug betrieben wird.

cmake_minimum_required(VERSION 3.21)  # 3.21 wegen $<TARGET_RUNTIME_DLLS:...>
project(aruco_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Bauart" FORCE)
endif()

set(ARUCO_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
set(ARUCO_SHARED_DIR "${ARUCO_REPO_ROOT}/shared")

# --- Was dieser Bau liefert ---------------------------------------------------
# Das Python-Modul ergibt nur auf dem Rechner Sinn, auf dem die Testsuite laeuft.
# Ein Kreuzbau (NDK, Emscripten) hat kein Ziel-Python und braucht auch keines:
# dort ist die Bibliothek das Erzeugnis, und der Pruefstand ist der Beleg.
if(CMAKE_CROSSCOMPILING)
  set(ARUCO_PYTHON_DEFAULT OFF)
else()
  set(ARUCO_PYTHON_DEFAULT ON)
endif()
option(ARUCO_BUILD_PYTHON "Das Python-Modul aruco_core bauen" ${ARUCO_PYTHON_DEFAULT})
option(ARUCO_BUILD_CONFORMANCE "Den Pruefstand aruco_conformance bauen" ON)

# `geometry` ist in OpenCV 5 ein eigenes Modul: cv::contourArea wohnt dort und
# nicht mehr in imgproc.
find_package(OpenCV REQUIRED COMPONENTS core geometry imgproc objdetect)

if(ARUCO_BUILD_PYTHON)
  # pybind11 sucht dabei auch Python und legt Python_EXECUTABLE fest - dasselbe
  # venv, das die Testsuite fuehrt. Die Erzeugungsschritte unten benutzen es, damit
  # nicht zwei verschiedene Python im Spiel sind.
  # PYBIND11_FINDPYTHON: ohne das greift pybind11 zum alten FindPythonLibsNew und
  # nimmt das erstbeste Python vom PATH - hier war das die Store-Installation und
  # nicht das venv, gegen das die Testsuite laeuft. Das Modul liesse sich dann
  # gegen die falsche python313.lib binden.
  set(PYBIND11_FINDPYTHON ON)
  find_package(pybind11 CONFIG REQUIRED)
  set(ARUCO_HOST_PYTHON "${Python_EXECUTABLE}" CACHE FILEPATH "Python fuer die Erzeugungsschritte")
endif()

# Die beiden Erzeugungsschritte (Konstanten-Header, Fixture-Paket) laufen auf dem
# BAUENDEN Rechner und nicht auf dem Ziel. Im Kreuzbau gibt es kein pybind11, das
# ein Python fuende - also muss der Aufrufer eines nennen. Und zwar dasselbe venv:
# make_fixture_pack.py braucht cv2, um die PNG in rohe Bytes zu wandeln, und es
# muss dasselbe cv2 sein, das auch tests/test_conformance.py liest. Sonst stuende
# zwischen den beiden Messungen ein anderer PNG-Dekoder.
if(NOT ARUCO_HOST_PYTHON)
  message(FATAL_ERROR
    "ARUCO_HOST_PYTHON ist nicht gesetzt. Im Kreuzbau muss das venv-Python "
    "genannt werden: -DARUCO_HOST_PYTHON=<repo>/venv/Scripts/python.exe")
endif()

message(STATUS "OpenCV ${OpenCV_VERSION} aus ${OpenCV_DIR}")
message(STATUS "Ziel ${CMAKE_SYSTEM_NAME} ${CMAKE_SYSTEM_PROCESSOR} (Kreuzbau: ${CMAKE_CROSSCOMPILING})")
message(STATUS "Python fuer die Erzeugungsschritte: ${ARUCO_HOST_PYTHON}")

# --- Erzeugte Konstanten ------------------------------------------------------
# shared/constants.json ist die einzige Stelle, an der diese Zahlen stehen
# (AGENTS.md, Invariante 4). Der Header entsteht im BAUVERZEICHNIS und nicht im
# Quellbaum: eine erzeugte Datei zwischen den Quellen wird frueher oder spaeter
# eingecheckt, und dann gibt es die Konstanten zweimal.
set(ARUCO_GENERATED_DIR "${CMAKE_BINARY_DIR}/generated")
set(ARUCO_CONSTANTS_HPP "${ARUCO_GENERATED_DIR}/aruco/constants.hpp")

add_custom_command(
  OUTPUT "${ARUCO_CONSTANTS_HPP}"
  COMMAND "${ARUCO_HOST_PYTHON}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/gen_constants.py"
          "${ARUCO_SHARED_DIR}/constants.json"
          "${CMAKE_CURRENT_SOURCE_DIR}/include/aruco/constants.hpp.in"
          "${ARUCO_CONSTANTS_HPP}"
  DEPENDS "${ARUCO_SHARED_DIR}/constants.json"
          "${CMAKE_CURRENT_SOURCE_DIR}/include/aruco/constants.hpp.in"
          "${CMAKE_CURRENT_SOURCE_DIR}/tools/gen_constants.py"
  COMMENT "shared/constants.json -> aruco/constants.hpp"
  VERBATIM)

# --- Die Bibliothek -----------------------------------------------------------
add_library(aruco_core_lib STATIC
  src/detect.cpp
  "${ARUCO_CONSTANTS_HPP}")

target_include_directories(aruco_core_lib PUBLIC include "${ARUCO_GENERATED_DIR}")
target_link_libraries(aruco_core_lib PUBLIC ${OpenCV_LIBS})

if(MSVC)
  # /utf-8: die Kommentare in diesem Baum sind deutsch. Ohne das legt MSVC die
  # Codepage der Konsole zugrunde und meckert bei jedem Umlaut, der spaeter
  # einmal hineingerat.
  target_compile_options(aruco_core_lib PUBLIC /utf-8 /W3)
endif()

if(EMSCRIPTEN)
  # Emscripten uebersetzt seit 3.x OHNE Ausnahmebehandlung, wenn man nichts sagt:
  # ein `throw` wird dann zu einem abort(), und ein `catch` verschwindet. Der Kern
  # wirft aber (std::invalid_argument bei einer unbrauchbaren ImageView), OpenCV
  # wirft (CV_Assert), und der Pruefstand faengt. Ohne dieses Flag stuerbe der
  # Browser-Bau bei jedem Fehler wortlos ab, statt ihn zu melden.
  #
  # PUBLIC/INTERFACE, weil das Entfalten durch JEDEN Rahmen dazwischen muss: das
  # OpenCV fuer WASM ist mit demselben Schalter gebaut (siehe die Anleitung in
  # docs/cpp-migration/stage-4-cross-targets.md). Fehlt er auf einer Seite, endet
  # die Ausnahme im abort().
  target_compile_options(aruco_core_lib PUBLIC -fexceptions)
  target_link_options(aruco_core_lib PUBLIC -fexceptions)
endif()

# --- Das Python-Modul ---------------------------------------------------------
if(ARUCO_BUILD_PYTHON)
  pybind11_add_module(aruco_core bindings/python.cpp)
  target_link_libraries(aruco_core PRIVATE aruco_core_lib)
endif()

# --- Der Pruefstand -----------------------------------------------------------
# Das Fixture-Paket: rohe Pixel plus Grundwahrheit, mechanisch aus
# shared/fixtures/ abgeleitet. Warum nicht direkt die PNG: siehe den Kopf von
# core/tools/make_fixture_pack.py.
if(ARUCO_BUILD_CONFORMANCE)
  set(ARUCO_FIXTURE_DIR "${CMAKE_BINARY_DIR}/fixtures")
  set(ARUCO_FIXTURE_PACK "${ARUCO_FIXTURE_DIR}/fixtures.txt")

  file(GLOB ARUCO_FIXTURE_SOURCES
    "${ARUCO_SHARED_DIR}/fixtures/expected/*.json"
    "${ARUCO_SHARED_DIR}/fixtures/scenes/*.png")

  add_custom_command(
    OUTPUT "${ARUCO_FIXTURE_PACK}"
    COMMAND "${ARUCO_HOST_PYTHON}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/make_fixture_pack.py"
            "${ARUCO_SHARED_DIR}/fixtures" "${ARUCO_FIXTURE_DIR}"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/tools/make_fixture_pack.py" ${ARUCO_FIXTURE_SOURCES}
    COMMENT "shared/fixtures/ -> rohe Pixel und Grundwahrheit fuer den Pruefstand"
    VERBATIM)

  add_custom_target(aruco_fixtures ALL DEPENDS "${ARUCO_FIXTURE_PACK}")

  add_executable(aruco_conformance tests/conformance.cpp)
  target_link_libraries(aruco_conformance PRIVATE aruco_core_lib)
  add_dependencies(aruco_conformance aruco_fixtures)

  if(EMSCRIPTEN)
    # Der Pruefstand liest seine Szenen mit std::ifstream aus dem Dateisystem.
    # NODERAWFS legt Emscriptens virtuelles Dateisystem beiseite und reicht die
    # Aufrufe an Node durch - damit liest der WASM-Bau BUCHSTAEBLICH DIESELBEN
    # Bytes wie der Windows-Bau, aus derselben Datei, ohne Umweg und ohne Kopie.
    # Das ist der Grund, warum hier Node und nicht der Browser gemessen wird: im
    # Browser muesste das Paket erst hineingereicht werden, und jede Kopie ist
    # eine Stelle, an der ein Unterschied entstehen koennte, den man dann dem
    # Detektor zuschriebe.
    #
    # ALLOW_MEMORY_GROWTH: eine Szene ist 2400x1800x3 = 12,4 MiB, und der
    # Detektor legt mehrere solcher Bilder an. Der Vorgabespeicher (16 MiB)
    # reicht dafuer nicht.
    #
    # EXIT_RUNTIME: ohne das verfaellt der Rueckgabewert von main() und der
    # Pruefstand meldete auch dann Erfolg, wenn eine Ecke danebenliegt.
    #
    # STACK_SIZE: Emscripten gibt seit 3.1.27 nur 64 KiB, native Ziele geben
    # Megabytes. OpenCVs Aufrufketten sind tief.
    target_link_options(aruco_conformance PRIVATE
      -sNODERAWFS=1
      -sALLOW_MEMORY_GROWTH=1
      -sEXIT_RUNTIME=1
      -sSTACK_SIZE=8MB)

    # `.cjs` und nicht `.js`. Emscripten schreibt einen CommonJS-Lader (`require`),
    # aber im Wurzelverzeichnis dieses Repos steht seit dem Umzug des PDF-Baus eine
    # package.json mit "type": "module" - und die faerbt JEDE .js-Datei darunter zum
    # ES-Modul ein, auch eine erzeugte in core/build-wasm/. Node bricht dann ab mit
    #
    #   ReferenceError: require is not defined in ES module scope
    #
    # Die Endung `.cjs` ist die Ausnahme, die Node immer als CommonJS liest, egal
    # was darueber steht. Der Browser-Bau darunter behaelt `.js`: den laedt ein
    # <script src>, und das kuemmert package.json nicht.
    set_target_properties(aruco_conformance PROPERTIES SUFFIX ".cjs")

    # --- Und derselbe Pruefstand noch einmal, fuer einen echten Browser -------
    # Node und Chrome fahren beide V8, der Unterschied ist also klein - aber
    # "klein" ist keine Messung, und der Browser ist das ZIEL. Ein Bau, der nur
    # unter Node belegt ist, laesst offen, ob die Sandbox, die Speichergrenze
    # oder der Dateiweg im Browser etwas verschieben.
    #
    # NODERAWFS gibt es dort nicht. --preload-file legt das Fixture-Paket
    # stattdessen als .data neben den Bau; der file_packager kopiert die Bytes
    # unveraendert, es steht also weiterhin kein Dekoder zwischen den Messungen.
    #
    # MODULARIZE + INVOKE_RUN=0: die Seite bestimmt selbst, wann main() laeuft,
    # und liest den Rueckgabewert. Ohne das faengt der Lauf beim Laden des
    # Skripts an und niemand bekaeme den Ausgang zu fassen.
    #
    # EXIT_RUNTIME=0, obwohl der Node-Bau es anhat: mit angeschaltetem
    # EXIT_RUNTIME beendet callMain die Laufzeit und wirft den Rueckgabewert
    # weg, statt ihn zurueckzugeben.
    add_executable(aruco_conformance_web tests/conformance.cpp)
    target_link_libraries(aruco_conformance_web PRIVATE aruco_core_lib)
    add_dependencies(aruco_conformance_web aruco_fixtures)
    target_link_options(aruco_conformance_web PRIVATE
      "SHELL:--preload-file ${ARUCO_FIXTURE_DIR}@/fixtures"
      -sMODULARIZE=1
      -sEXPORT_NAME=createConformance
      -sEXPORTED_RUNTIME_METHODS=callMain
      -sINVOKE_RUN=0
      -sEXIT_RUNTIME=0
      -sALLOW_MEMORY_GROWTH=1
      -sSTACK_SIZE=8MB)

    # Die Seite, die ihn startet. Sie liegt im Quellbaum, weil sie Text ist und
    # kein Erzeugnis - aber sie muss neben dem .js liegen, um es zu finden.
    configure_file(tests/conformance_web.html
                   "${CMAKE_BINARY_DIR}/conformance_web.html" COPYONLY)
  endif()
endif()

# --- Laufzeit-DLLs neben die Erzeugnisse legen --------------------------------
# opencv_world500.dll steht im SDK und in keinem PATH. Sie daneben zu legen macht
# beide Erzeugnisse fuer sich lauffaehig: Windows sucht neben einer .pyd, bevor
# es den PATH befragt, und niemand muss eine Umgebungsvariable setzen, damit die
# Testsuite den Kern findet.
#
# Nur auf Windows: Android und WASM binden statisch, dort gibt es nichts
# danebenzulegen, und $<TARGET_RUNTIME_DLLS:...> waere dort leer.
if(WIN32)
  set(ARUCO_RUNTIME_TARGETS "")
  if(ARUCO_BUILD_PYTHON)
    list(APPEND ARUCO_RUNTIME_TARGETS aruco_core)
  endif()
  if(ARUCO_BUILD_CONFORMANCE)
    list(APPEND ARUCO_RUNTIME_TARGETS aruco_conformance)
  endif()
  foreach(target ${ARUCO_RUNTIME_TARGETS})
    add_custom_command(TARGET ${target} POST_BUILD
      COMMAND "${CMAKE_COMMAND}" -E copy_if_different
              "$<TARGET_RUNTIME_DLLS:${target}>" "$<TARGET_FILE_DIR:${target}>"
      COMMAND_EXPAND_LISTS)
  endforeach()
endif()

# --- Die C-Schnittstelle und die JNI-Bindung ----------------------------------
#
# ABSICHTLICH EIN GESCHLOSSENER BLOCK AM ENDE. Nichts weiter oben wurde
# angefasst: an dieser Datei arbeiten mehrere Zweige gleichzeitig, und ein
# verflochtener Umbau der Zielbeschreibungen ist beim Zusammenfuehren nicht mehr
# sicher aufzuloesen. Ein Anhang ist es. Deshalb kommen die beiden neuen Quellen
# ueber target_sources dazu und stehen nicht oben in der Quellenliste - CMake ist
# das gleichgueltig, dem naechsten Zusammenfuehren nicht.
#
# src/capi.cpp ist NICHT android-spezifisch: es ist die stabile C-Grenze, an der
# jede fremde Sprache andockt, und der Pruefstand misst mit `--capi` durch sie
# hindurch. Sie gehoert deshalb auf jedem Ziel in die Bibliothek.
target_sources(aruco_core_lib PRIVATE src/dictionary.cpp src/capi.cpp)

if(ANDROID)
  # Jede Funktion in ihren eigenen Abschnitt, damit --gc-sections beim Binden der
  # .so wegwerfen kann, was niemand aufruft. Nur fuer Android: MSVC baut ohnehin
  # mit /Gy, und Emscripten bringt seine eigene Abschnittsverwaltung mit. Ein
  # Schalter, der ueberall steht und nur an einer Stelle etwas tut, waere Zierde.
  target_compile_options(aruco_core_lib PRIVATE -ffunction-sections -fdata-sections)
endif()

# Die JNI-Bibliothek ist auf Android das Erzeugnis - dort also vorgabegemaess an.
# Auf dem Bau-Rechner ist sie AUCH baubar, und das ist kein Zufall: jni.h kommt
# aus dem JDK, nicht aus dem NDK. Damit laesst sich der Marshalling-Code auf einer
# echten JVM ausfuehren, obwohl kein Android-Geraet in Reichweite ist
# (core/tools/JniCheck.java, ./dev.ps1 check-jni). Ein Kreuzbau, den niemand
# ausfuehrt, belegt nur, dass er uebersetzt - und das ist die Frage nicht.
if(ANDROID)
  set(ARUCO_JNI_DEFAULT ON)
else()
  set(ARUCO_JNI_DEFAULT OFF)
endif()
option(ARUCO_BUILD_JNI "Die JNI-Bibliothek libaruco_core.so bauen" ${ARUCO_JNI_DEFAULT})

if(ARUCO_BUILD_JNI)
  # Der CMake-Zielname ist `aruco_jni`, die DATEI heisst `aruco_core`: zwei Ziele
  # duerfen nicht denselben CMake-Namen tragen (das Python-Modul heisst schon
  # aruco_core), aber `System.loadLibrary("aruco_core")` soll auf dem Geraet
  # genau das finden, was der Bericht nennt.
  #
  # OpenCV wird statisch hineingebunden - daneben muss nichts liegen. Eine App,
  # die zwei Bibliotheken in der richtigen Reihenfolge laden muss, hat eine
  # Fehlerquelle mehr als eine, die eine laedt.
  add_library(aruco_jni SHARED bindings/jni.cpp)
  set_target_properties(aruco_jni PROPERTIES OUTPUT_NAME aruco_core)
  target_link_libraries(aruco_jni PRIVATE aruco_core_lib)

  if(NOT ANDROID)
    # Auf dem Bau-Rechner liefert das NDK kein jni.h - es kommt aus dem JDK.
    # Gesucht wird NICHT: ein gefundenes, aber falsches JDK baute eine
    # Bibliothek, die genau die JVM nicht laedt, gegen die geprueft werden soll.
    if(NOT ARUCO_JAVA_HOME)
      message(FATAL_ERROR
        "ARUCO_BUILD_JNI ohne Android braucht ein JDK: -DARUCO_JAVA_HOME=<jdk>")
    endif()
    if(WIN32)
      set(ARUCO_JNI_PLATFORM_DIR win32)
    elseif(APPLE)
      set(ARUCO_JNI_PLATFORM_DIR darwin)
    else()
      set(ARUCO_JNI_PLATFORM_DIR linux)
    endif()
    target_include_directories(aruco_jni PRIVATE
      "${ARUCO_JAVA_HOME}/include" "${ARUCO_JAVA_HOME}/include/${ARUCO_JNI_PLATFORM_DIR}")
  endif()

  if(WIN32)
    # opencv_world500.dll daneben legen. Windows sucht Abhaengigkeiten NICHT im
    # Verzeichnis der ladenden DLL, sondern neben der Anwendung - beim Pruefen
    # ist das java.exe. Ohne die Kopie meldet die JVM "Can't find dependent
    # libraries", was nach einer fehlenden JNI-Bibliothek aussieht und keine ist.
    # (Auf Android und WASM wird statisch gebunden; dort gibt es nichts zu legen.)
    add_custom_command(TARGET aruco_jni POST_BUILD
      COMMAND "${CMAKE_COMMAND}" -E copy_if_different
              "$<TARGET_RUNTIME_DLLS:aruco_jni>" "$<TARGET_FILE_DIR:aruco_jni>"
      COMMAND_EXPAND_LISTS)
  endif()

  if(ANDROID)
    # 16-KB-Seiten. Neue Android-Geraete legen Bibliotheken mit 16-KiB-Seiten ab;
    # eine nur auf 4 KiB ausgerichtete .so laedt dort GAR NICHT - die App startet
    # und stirbt sofort, ohne dass ein Codefehler vorlaege. Das NDK r27 setzt das
    # per Vorgabe, aber "per Vorgabe" ist die Sorte Zusage, die eine
    # Werkzeugkette spaeter still zuruecknimmt. Nachgemessen mit llvm-readelf
    # (./dev.ps1 check-android-so).
    target_link_options(aruco_jni PRIVATE "-Wl,-z,max-page-size=16384")

    # Nur die sechs JNI-Einsprungpunkte gehoeren nach aussen. Ohne
    # --exclude-libs traegt die .so die Symboltabelle des statisch gebundenen
    # OpenCV mit sich - gemessen 4383 dynamische Symbole -, und weil jedes davon
    # als von aussen erreichbar gilt, darf der Linker auch nichts davon
    # wegwerfen. Mit beiden Schaltern zusammen: 12,8 MB -> 6,2 MB, 4383 -> 6
    # Symbole (docs/cpp-migration/stage-4-android.md).
    target_link_options(aruco_jni PRIVATE "-Wl,--exclude-libs,ALL" "-Wl,--gc-sections")
    target_compile_options(aruco_jni PRIVATE
      -fvisibility=hidden -ffunction-sections -fdata-sections)

    # Gestrippt, aber nur im Release-Bau: die Debug-Angaben eines statisch
    # gebundenen OpenCV nuetzen in einer Auslieferung niemandem, und ein
    # Debug-Bau soll seine Symbole behalten.
    target_link_options(aruco_jni PRIVATE "$<$<CONFIG:Release>:-Wl,-s>")
  endif()
endif()
